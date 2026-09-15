# Shared assertion policy — Phase A: inventory and classification

**Status: REPORT for operator review, 2026-09-15. Nothing built.** Project check
passed (`get_project_url` = kfxxpscdwoemtzylhhhb, Parity); `select count(1) from
signal_issues` = **11**.

Scope guards honoured: no What Holds Up behaviour is proposed for change (WHU is
observed in §A.7 only); the frozen 381-source corpus was read, never written.

Method: an AST walk over `backend/` (venv, tests excluded) for every
`*.messages.create` / `.stream` call, then every function that transitively
reaches one, then every call site of those, with the `_call_claude` name
collision resolved by each file's import table rather than by name. Two
false positives from the name-only pass were removed by reading the imports
(`claim_review.analyze_837` calls `utils.parse_837`, the pure parser, not the
router endpoint of the same name; `auth.py:242` is Twilio — see §A.0).

---

## A. Complete surface inventory

### A.0 Corrections to the starting list

Verified as stated: `check_letter` is called from `provider_appeals.py:285` and
`:294` and nowhere else. `provider_audit.py` has exactly 8 `_call_claude` and 3
`_call_claude_text` sites. `provider_shared.py:1031`, `employer_pharmacy.py:182`,
`employer_benchmark.py:138`, `signal_qa.py:280`, `billing_contracts.py` (2),
`eob_parse.py` (2), `ai_parse.py` (1), `health_analyze.py` (3 direct + 1 wrapper)
all confirmed.

**Not a model surface:** `auth.py:242` is `TwilioClient(...).messages.create(...)`
sending an SMS OTP. It shares the Anthropic SDK's method name and nothing else.
It needs no tier; it is simply not in the population. (The discovering test in
Phase B must resolve the receiver, or keep an explicit not-a-model list, or it
will trip on this forever.)

**Missing from the starting list (routers):** `employer_claims.py` (2 direct SDK
calls + 5 wrapper sites), `employer_shared.py:109` (a third `_call_claude`),
`employer_scorecard.py` (2), `employer_trends.py`, `provider_trends.py`,
`provider_subscription.py:542/:561` (admin path that re-runs analysis + trends),
`broker.py` (3, including the CAA letter), `signal_metrics.py:592`,
`signal_topic_request.py:158`, and the two Health classifiers. **Missing
(scripts):** nine Signal pipeline scripts under `backend/scripts/signal/`, which
write model output into `signal_*` draft rows and, for notifications, into
subscriber email.

### A.1 Provider

| # | file:line | function | emits | goes to |
|---|---|---|---|---|
| P1 | provider_appeals.py:282, :290 (`_gated_letter`) | appeal letter | `letter_text`, `letter_html`, **`cms_references`, `appeal_strength_reason`, `escalation_path`, `attach_documentation`** | API response; PDF (`_generate_appeal_pdf`); `provider_appeals` (letter_text, letter_html, cms_references); `provider_appeal_letters` |
| P2 | provider_audit.py:495 (pdf), :523 (text), :580 (image) | fee-schedule extraction | `rates[] {cpt, rate, description}`, payer_name, effective_date | API → saved by the UI to `provider_contracts` (:315); later drives underpayment math |
| P3 | provider_audit.py:792 (`analyze_contract`) | scorecard narrative | prose restating clean-claim / denial / adherence rates | `provider_analyses.result_json.scorecard.narrative` (:991); API |
| P4 | provider_audit.py:1184 (`_run_coding_analysis_from_835`), :1333 (`analyze_coding`) | E&M coding-gap narrative | prose restating dollar gap, codes | `provider_analyses.result_json`; API |
| P5 | provider_audit.py:1455 (`parse_837` CSV fallback) | tabular claim extraction | `lines[] {cpt_code, units, billed_amount, service_date}` | feeds P4; API |
| P6 | provider_audit.py:1509 (`analyze_denials`); provider_shared.py:1031 (`_run_analysis_for_payer`, reached from provider_audit.py:3130 and provider_subscription.py:542) | `DENIAL_SYSTEM_PROMPT` | per-CARC `plain_language`, `recommended_action`, **`appeal_letter_template`** (a letter), `appeal_worthiness`, **`total_recoverable_value`, `preventable_denial_rate` (model-computed)**, `pattern_summary` | API; `provider_analyses.result_json.denial_intel`; enriched with `signal_denial_playbook` rows (anon reader) |
| P7 | provider_audit.py:1692, :1713, :1728 (`generate_audit_report`) | exec summary, recommended actions, billing assessment | prose restating amounts and percentages | audit PDF only |
| P8 | provider_trends.py:356 (`_generate_trend_narrative`) | trend narrative | prose restating month totals, "projected annual impact" | trends cache; monthly email via provider_subscription admin path |

### A.2 Billing

| # | file:line | function | emits | goes to |
|---|---|---|---|---|
| B1 | billing_contracts.py:313 (`analyze_contract`), :387 (`analyze_all_contracts`) | fee-schedule extraction (same prompt as P2) | `rates[]` | `billing_contracts.analysis_result`; API |

**B1 is broken and has never emitted anything.** Both sites call
`_call_claude(file_b64, "application/pdf", FEE_SCHEDULE_EXTRACTION_PROMPT)`
positionally, but `provider_shared._call_claude` is
`(system_prompt, user_content, max_tokens)`. The PDF base64 becomes the system
prompt, the string `"application/pdf"` the user message, and the prompt text
`max_tokens`. The API call raises, `_call_claude` swallows it and returns
`None`, and the caller stores `{"extraction": None, "rates_extracted": 0}`.
The tests (`test_billing_contracts.py`) cover only the 401 paths, so nothing
noticed. Listed for the tiering because it *will* emit retrieved numbers the
moment the arguments are fixed.

### A.3 Employer

| # | file:line | function | emits | goes to |
|---|---|---|---|---|
| E1 | employer_benchmark.py:138 | benchmark narrative + 3 talking points | prose restating PEPM / percentile / dollar gap; "what typically drives costs at this percentile for this industry and state" (free-form claims) | API; `employer_benchmark_sessions.result_json` |
| E2 | employer_claims.py:224 (`COLUMN_MAPPING_PROMPT`) | column-name mapping | header → field mapping | in-process only (drives pandas); sample rows go to the API |
| E3 | employer_claims.py:384 (narrative), :407/:416 (action plan) | claims-check narrative, 3-step plan | prose restating totals, excess vs 2× Medicare, top CPT | API; `employer_claims_uploads.results_json` |
| E4 | employer_claims.py:1154 (`_parse_contract_pdf`, direct SDK, `CONTRACT_PARSE_PROMPT`); :1106/:1116 narratives | contract-rate extraction | negotiated rates per procedure | API |
| E5 | employer_claims.py:668 (`employer_rbp_calculate`) | RBP narrative | prose restating computed savings | API |
| E6 | employer_pharmacy.py:182 (Stage-3 fallback) | pharmacy line extraction | NDC, HCPCS, drug names, amounts, days supply | `pharmacy_benchmarks.analysis_json`; API |
| E7 | employer_scorecard.py:167 (`SBC_EXTRACTION_PROMPT`), :258 (action plan) | plan-design extraction; 3-step plan | deductibles, OOP max, copays, coinsurance | `employer_scorecard_sessions.parsed_plan_json`; API |
| E8 | employer_trends.py:229 (via `employer_claims._generate_narrative`) | trend narrative | prose restating PEPM deltas | `employer_trends_cache`; API |

### A.4 Broker

| # | file:line | function | emits | goes to |
|---|---|---|---|---|
| K1 | broker.py:2096 (column mapping), :2218 (narrative) | as E2 / E3 | as E2 / E3 | `broker_client_benchmarks`; API; shared read-only reports |
| K2 | broker.py:2317 | as E7 | as E7 | `broker_client_benchmarks`; API |
| K3 | broker.py:2482 (`generate_caa_letter`, `CAA_LETTER_SYSTEM_PROMPT` at :2402) **plus the static fallback template at :2497 that bypasses the model** | CAA §204 data-request letter | a letter a broker sends to a carrier | API (`{"letter": ...}`) |

**K3 is the live failure the provider gate was built after, still running in
another product.** The prompt *instructs* the model to cite "Section 204 of
Division BB of the CAA 2021, codified at 29 U.S.C. § 1185i", "ERISA
§ 404(a)(1)", "DOL guidance from November 2021 and EBSA Field Assistance
Bulletin 2021-04", and a "30-business-day response deadline citing the
carrier's contractual obligation". I resolved the first one against the
primary source (law.cornell.edu, 2026-09-15): **29 U.S.C. § 1185i is
"Protecting patients and improving the accuracy of provider directory
information."** It is not the pharmacy-benefit reporting section. The same
wrong citation is repeated verbatim in the code-written fallback letter and in
`BrokerLandingPage.jsx` / `BrokerDemoPage.jsx`. I did not resolve the FAB or the
30-day figure; they are TYPED and unverified. Every one carries the tone of
counsel and goes to a third party.

### A.5 Health

| # | file:line | function | emits | goes to |
|---|---|---|---|---|
| H1 | health_analyze.py:214 (`analyze_text`), :273 (`analyze_image`); ai_parse.py:164; eob_parse.py:179, :234 | bill / EOB extraction | line items (CPT, revenue code, billed amount, POS, dates), totals, claim/member ids | report view; benchmark math is in code (`benchmark.py`) |
| H2 | health_analyze.py:472 (`analyze_sbc`) | plan-design extraction | deductible, OOP max, copays, coinsurance | `health_sbc_uploads.sbc_data`; report |
| H3 | health_analyze.py:621 (`analyze_denial`, `DENIAL_SYSTEM_PROMPT`) | denial analysis | `specific_criterion`, `payer_guideline_id`, `carc_rarc_code`, `appeal_rights[]`, `appeal_submission{}`, deadlines, `billed_amount`, `weakness`, PHI fields | API (not stored); feeds H4 |
| H4 | health_analyze.py:1461 (`_generate_appeal_result`) | patient appeal letter | letter body with `[E#]` keys; References appended by code | API; PDF (`generate_appeal_pdf`); **not stored** |
| H5 | health_analyze.py:1979, :2042 (classify) | document type | `{document_type, confidence, reason}` | routing only |

### A.6 Signal — live endpoints

| # | file:line | function | emits | goes to |
|---|---|---|---|---|
| S1 | signal_qa.py:280 (`ask_question`) | Q&A answer | prose citing "specific claims and their evidence scores"; context handed in includes claims, consensus and **sources** | API only (not stored) |
| S2 | signal_metrics.py:592 (`generate_plain_summary`, admin) | plain-language summary; "include specific numbers where they matter" | mechanism / evidence / limitations / watch | **`signal_issues.plain_summary` written directly, including on a published row** — the publish record (`verify.publish`) covers sources and claims, not this column |
| S3 | signal_topic_request.py:158 | topic parse | title / slug / description | `signal_topic_requests` |

### A.7 Signal — pipeline scripts (write to draft rows; `verify.publish` is the gate between them and readers)

| # | script | emits | note |
|---|---|---|---|
| S4 | scripts/signal/00_discover_sources.py:201 | **URLs / DOIs / NCT ids from the model's memory** — the mechanism that produced the 59 FABRICATED_IDENTIFIER rows | still wired: `signal_topic_request.admin_approve` → `run_full_topic.py` → step 0 |
| S5 | extract_claims.py:96, classify_claims.py:114, score_claims.py:123, map_consensus.py:169, generate_summary.py:93 | claims with figures; consensus `arguments_for/against` (can name studies and figures); narrative + glossary | claims are gated at publish (FIGURE vs fetched text); **consensus text, summaries and glossary are not** |
| S6 | generate_notifications.py:90 | notification prose with figures | delivered to subscribers by `signal_notify_deliver.py` via Resend |
| S7 | golden_set.py:347 | regression measurement | tooling, not a surface |

**WHU (observe only):** the only model call in WHU's orbit is
`scripts/signal/factcheck_draft.py:689/:692` — the draft fact-check gate, which
uses the model as a checker in five roles. It lives under `scripts/signal/`,
not `scripts/whatholdsup/`, so the boundary test that "nothing under
scripts/whatholdsup imports verify" would not see it; it imports nothing from
`verify` either way. Nothing here proposes touching it. `sweep_sources.py` makes
no model call at all ("No model, no API key, no cost").

---

## B. Classification: surface × assertion class

Legend — **can emit?** / **checked by?** &nbsp; `—` cannot emit by construction; `P` prompt prose only; `C` code; `✗` nothing.

| surface | identifiers | legal provisions | named sources | retrieved / restated numbers |
|---|---|---|---|---|
| P1 provider letter | can (nothing forbids a PMID) / ✗ | can / **C** `check_letter` on letter_text+html only; `escalation_path`, `appeal_strength_reason`, `cms_references`, `attach_documentation` **unchecked** | can / P ("do not name a specific act or manual by its formal title") | restates billed_amount, contracted rate; hardcoded "30 calendar days"; **recites the AMA CPT descriptor from memory** / ✗ |
| P2 fee schedule | — | — | — | **extracted** / ✗ (P: "do not invent or estimate rates") |
| P3, P4, P7, P8 provider narratives | can / ✗ | can ("state prompt-pay law") / ✗ | can / ✗ | restated from input JSON / ✗ (P: "be specific about dollar amounts") |
| P5 CSV fallback | — | — | — | extracted / ✗ |
| P6 denial intel | can / ✗ | **can — `appeal_letter_template` is an ungated letter**, stored and returned, not rendered by the UI | can / ✗ | **computed by the model** (`total_recoverable_value`, `preventable_denial_rate`); CARC meanings recited / ✗ |
| B1 billing contracts | — | — | — | extracted / ✗ (and currently never emitted, see A.2) |
| E1 benchmark | can / ✗ | can / ✗ | can (industry claims) / ✗ | restated / ✗ |
| E2, K1a column mapping | — | — | — | — |
| E3, E5, E8, K1b narratives | can / ✗ | can / ✗ | can / ✗ | restated / ✗ |
| E4 contract parse | — | — | — | extracted / ✗ |
| E6 pharmacy | — | — | — | extracted (NDC, amounts) / ✗ |
| E7, K2 SBC | — | — | — | extracted / ✗ |
| K3 CAA letter | — | **required by the prompt; hardcoded; one verified wrong** / ✗ | required (DOL, EBSA FAB) / ✗ | "30 business days" hardcoded / ✗ |
| H1 bill / EOB | — | — | — | extracted / ✗ |
| H2 SBC | — | — | — | extracted / ✗ |
| H3 denial analysis | can (`payer_guideline_id`) / ✗ | can (`specific_criterion`) / ✗ | **`appeal_rights` — the named failure mode** / P only ("ONLY as the denial LITERALLY states them") | extracted deadlines, billed_amount / P only ("never convert 72 hours") |
| H4 patient letter | **withheld** (PH-4a.3) / **C** `_validate_evidence_claims` refuses PMID/PMA/DOI/et al./journal shapes | can / **P only — `check_letter` is never called here** | can / P ×2 (regulatory status, appeal_rights) | restated / soft flag only (`review_flags`), never a refusal |
| H5 classify | — | — | — | — |
| S1 Q&A | can (sources are in the context) / ✗ | — | can / ✗ | restated / ✗ |
| S2 plain summary | can / ✗ | — | can / ✗ | restated / ✗ |
| S3 topic parse | — | — | — | — |
| S4 discover sources | **required** / C at publish only (`verify.publish` resolve) | — | — | — |
| S5 claims | can / C at publish | — | — | figures / **C at publish for claims only**; consensus / summary / glossary ✗ |
| S6 notifications | can / ✗ | — | — | restated / ✗ |

**Your belief about retrieved numbers is confirmed, and it is wider than the
three modules you named.** No surface anywhere in `backend/routers/` checks a
model-emitted number against the document or input it came from. `verify.bind_figure`
exists and is used in exactly two places: the provider allow-list sentence
check (`citation_gate.check_letter`, live only when the allow-list is non-empty,
which today it never is) and the Signal publish record. Every extraction surface
(P2, P5, B1, E4, E6, E7, K2, H1, H2, H3) and every narrative surface (P3, P4,
P7, P8, E1, E3, E5, E8, K1b, S1, S2, S6) is unchecked.

### A fifth class — and a distinction inside the fourth

**Fifth: coded-vocabulary descriptors.** A code the system already holds
(CPT/HCPCS, CARC/RARC, ICD-10, NDC, APC) whose *meaning* the model supplies from
memory. `provider_appeals` prompt line ~50: `CPT Code: {cpt_code} — [full AMA CPT
description of this code]`. `DENIAL_SYSTEM_PROMPT` (provider_shared:409):
`plain_language` per CARC. `PHARMACY_EXTRACTION_PROMPT`: `generic_name`,
`therapeutic_class`. These are neither identifiers (the code is correct — we gave
it) nor named sources; they are lookups the model is asked to perform instead of
a table. They are checkable against tables the repo already holds
(`frontend/src/lib/cptLabel.js`, the CMS rate files' descriptions, NADAC drug
names) and the failure is invisible to the reader: a plausible descriptor for the
wrong code. Health PH's 783xx note is the same shape from the other direction.

**Inside "retrieved numbers", two provenances that need different checks:**
*extracted* (from a document the user uploaded — the check is FIGURE against
that document's text, and for images there is no text to check against) and
*restated* (from a JSON the system computed and handed to the model — the check
is FIGURE against the prompt input, trivially deterministic, and this is the
most common shape in the repo by surface count). P6 adds a third, worst case:
*model-computed* — `total_recoverable_value` is arithmetic the model does.
That is not a class to gate; it is a task to take away.

---

## C. Tier assignment

Principles applied: Tier 1 wherever the surface has no legitimate need to emit
the class; Tier 2 only where it must; gates sit at the **response boundary**
(the assembled dict / the DB insert), not around `_call_claude`, because (a) K3's
static fallback and provider's `cms_references` both reach the user without
passing the model-call wrapper, and (b) `_call_claude` is three different
functions.

### Tier 1 — WITHHOLD (the material is never given to the model; output asserted absent)

| surface | class | reasoning |
|---|---|---|
| H4 patient letter | identifiers | Already so (PH-4a.3): `_format_reference_plain` is identifier-free, `_format_reference` is code-only and appended after. Keep; this is the pattern the policy leads with. |
| all narrative surfaces (P3, P4, P7, P8, E1, E3, E5, E8, K1b, S2, S6) | identifiers, legal provisions, named sources | None of these has any reason to cite anything. The prompt hands them numbers; the output should carry a "no citation shapes present" assertion (`find_citations` + literature `identify` + a named-source lexicon → must be empty). Cheap, no allow-list needed. |
| P6 denial intel | legal provisions, named sources | Drop `appeal_letter_template` from the prompt. It is a letter the UI does not render, that the gate does not see, that is stored in `provider_analyses`. Nothing depends on it. |
| P6 denial intel | model-computed numbers | Take `total_recoverable_value` and `preventable_denial_rate` out of the model's job; compute in code (the inputs are already summed in `_run_analysis_for_payer`). |
| P1 provider letter | coded descriptors | Hand the CPT descriptor in `prompt_data` from a held table; strip the "[full AMA CPT description]" instruction. |
| P6 | coded descriptors | Same for CARC `plain_language`: a held CARC table, model writes the *advice* only. |
| S4 discover sources | identifiers | The model may propose **titles**; identifiers come only from a registry search (`Provenance.SEARCHED`), resolved by `verify.literature` before a row is written. Never a DOI from memory. This closes the mechanism behind the 59, at the point it happens, instead of at publish. |
| E2, K1a column mapping | (PHI, not an assertion class) | Not a tier item, but noted: `sample_rows` (5 rows) go to the API and the prompt promises "we will NOT store" `member_id`. Header-only mapping would withhold it. |

### Tier 2 — GATE (the surface must emit the class; deterministic check on output)

| surface | class | check | reasoning |
|---|---|---|---|
| P1 provider letter | legal provisions | `check_letter` — **extend to all six emitted fields**, not two | Reference implementation. The four ungated fields are the same register ("external review under…"). |
| P1 | restated numbers | FIGURE vs `prompt_data` (billed_amount, contracted rate); the "30 calendar days" is prompt-hardcoded → flag as TYPED | |
| **K3 CAA letter** | legal provisions, named sources | `check_letter` with an allow-list, **on the response dict, so the static fallback is gated too**; remove the hardcoded citations from prompt and template | Must cite to function — a data-request letter that names its authority is the product. But `verify.law` has **no USC adapter** (`_ADAPTERS` = cfr, orc, oac, cms_iom, ncci; `types.LAW` lists usc but nothing resolves it). Until one exists the allow-list is empty and, exactly as §5b intends, the letter cites nothing and says "the CAA's plan-sponsor transparency provisions" in words. That is a *better* letter than one citing the provider-directory statute. |
| K3 | restated numbers | "30 business days" is TYPED in the prompt → either a held, sourced figure or plain words | |
| H4 patient letter | legal provisions | call `check_letter(body, allowed=None)` — zero cost, the prompt already forbids statutes; today nothing enforces it | Fail semantics must match provider: refuse, don't return with `needs_revision` (see §E). |
| H4 | named sources | lexicon extractor (ERISA, ACA, DOL, EBSA, CMS, NCCN, ASCO, ESMO, NICE, FDA, "Breakthrough", "Priority Review", "external review", "independent review organization"…) → each hit must SPAN-bind to the denial text (`req.text`, held) or to an `[E#]` item's stored fields | This is the appeal_rights failure mode in code form. |
| H4 | restated numbers | FIGURE vs (denial analysis JSON ∪ evidence model_block); promote from soft flag to refusal for figures found in neither | |
| H3 denial analysis | named sources, legal, numbers | every "verbatim" field (`appeal_rights[]`, `specific_criterion`, `appeal_deadline_hint`, `appeal_submission.*`, `payer_guideline_id`, `billed_amount`) SPAN/FIGURE-binds to `req.text` | The prompt says "literally", "verbatim", "never convert" four times; `bind_span` exists and is unused for it. |
| P2, B1, E4, E6, E7, K2, H1, H2 extraction | retrieved numbers | FIGURE per extracted value vs the source text (pasted text; PDF via `law._pdftotext`, which exists); **image inputs have no text layer → `UNCHECKED`, never a pass** → surfaced to the user as "read from image, not verified" rather than silently accepted | Extraction is the job; withholding is impossible. The image case is honest degradation, not a gap to paper over. |
| P5 CSV fallback | retrieved numbers | FIGURE vs the 8000-char sample | |
| all narratives (P3, P4, P7, P8, E1, E3, E5, E8, K1b, S1, S2, S6) | restated numbers | FIGURE vs the exact input handed to the model | Same binder as the letters; the "document" is our own JSON. A number the input doesn't contain is a number the model made. |
| S1 Q&A | identifiers, numbers | identifiers must `identify()` to a source in the context; figures FIGURE-bind to the context | |
| S2 plain summary | numbers, named sources | FIGURE vs the claims block; and bring the column under the publish record — today it is written straight onto a published row | |
| S5 consensus / summary / glossary | numbers, named sources | extend `verify.publish` to these rows (FIGURE vs the claims each rests on) | The publish gate covers what the pipeline extracted, not what it wrote about the extraction. |

### EXEMPT — with reasons

| surface | reason |
|---|---|
| `auth.py:242` | Not a model. Twilio. Excluded from the population, not exempted from the policy. |
| E2, K1a column mapping | Emits column names only, consumed by pandas; no assertion class can appear. (A wrong mapping shows up as wrong numbers downstream, which the number gate on E3/K1b then catches against the input — but that is a data-quality matter, not an assertion.) |
| H5 classify | Emits an enum + confidence + one-line reason that drives routing; never shown as fact. |
| S3 topic parse | Emits a title/slug/description for an admin queue; the topic's facts are produced later by gated steps. |
| S7 golden_set, factcheck_draft | Measurement tooling; WHU is out of scope by the plan of record. |

No surface is unassigned.

---

## D. The shared entry point

`backend/verify` is already one interface with **two registry adapters**
(literature, law) plus generic URLs, and **five binding kinds**. What is
missing is not a third adapter; it is (1) an **extractor** per assertion class
that finds candidates in free text (the citation gate's `find_citations` is the
only one that exists), (2) a **registry of (surface, class) → tier** that a test
can compare against the AST inventory, and (3) one function that runs at a
response boundary.

Proposed shape (`backend/verify/policy.py`; names illustrative):

```
class AssertionClass(str, Enum):
    IDENTIFIER        # doi / pmid / pmcid / nct / url
    LEGAL_PROVISION   # cfr / usc / orc / oac / cms_iom / ncci / §
    NAMED_SOURCE      # agency, program, statute NAME, guideline body, regulatory status
    FIGURE            # numbers: extracted, restated (provenance recorded)
    CODED_DESCRIPTOR  # meaning of a CPT / CARC / ICD / NDC we already hold

class Tier(str, Enum): WITHHOLD, GATE, EXEMPT

POLICY: dict[str, dict[AssertionClass, Tier]]     # surface id → class → tier
    # e.g. "provider.appeal_letter": {LEGAL_PROVISION: GATE, IDENTIFIER: WITHHOLD, ...}
    # A (surface, class) absent from POLICY is what the discovering test refuses.

@dataclass
class Held:                        # everything the system handed the model or holds about the request
    allowed:   list[Allowed] = ()  # verify.allowlist — legal provisions this letter may cite
    evidence:  dict = {}           # [E#] → item (H4)
    documents: list[Document] = () # source text the numbers must be in (uploads, denial text, context)
    inputs:    dict = {}           # the JSON we computed and handed over (narratives)
    tables:    dict = {}           # coded-vocabulary lookups

@dataclass
class Finding:
    cls: AssertionClass; text: str; field: str; span: tuple[int, int]
    ok: bool; mode: Literal["absent", "bound"]; reason: str; binding: Binding | None

def check(surface: str, output: str | dict, held: Held) -> Verdict
    # walks every string field of `output` (so cms_references and escalation_path are seen),
    # for each class in POLICY[surface]:
    #   WITHHOLD → extract(cls, text); any hit is a Finding(ok=False, mode="absent")
    #              AND extract(cls, prompt_payload) must be empty (input-side assertion,
    #              the _assert_no_phi shape, so "withheld" is checked, not assumed)
    #   GATE     → extract(cls, text); each candidate binds against `held` via the
    #              existing verbs (law.identify+allowlist / literature.identify+resolve /
    #              numbers.figures+bind_figure / bind_span / table lookup)
    #   EXEMPT   → nothing
    # Verdict.ok is False on any Finding.ok=False; UNCHECKED is never ok.
```

Per-class **extractors** (`verify/extract.py`): `LEGAL_PROVISION` = the
existing `citation_gate.find_citations`; `IDENTIFIER` = `literature.identify`
run over every token plus health's `_FAB_*` shapes; `FIGURE` =
`numbers.stated_figures`; `NAMED_SOURCE` = a lexicon (new; small, reviewed,
grows like the candidate table); `CODED_DESCRIPTOR` = the code pattern next to
descriptive text (new). Each is a pure function of the text.

Three consequences of this shape, stated so they can be disagreed with:

1. **Provenance rides on every Finding.** The provider prompt had six
   hardcoded provisions; the broker prompt has three today. The output gate
   cannot tell a model-typed citation from a prompt-typed one, and it does not
   need to — both are TYPED, both are refused unless allow-listed. But a **lint
   over every `*_PROMPT` constant and every f-string template** with the same
   extractors is the cheapest control in this whole design and catches the
   broker prompt at commit time. It belongs in the discovering test.
2. **Fail semantics are part of the policy, not the surface.** Provider refuses
   (502) and stores nothing; Health returns the letter with `needs_revision: true`
   and a checklist; extraction surfaces return `None` and callers substitute
   silence; B1 stores `None` as a result. One `Verdict` type forces one answer
   per tier: GATE fails closed; a WITHHOLD violation is a bug, logged loudly and
   also failed closed; UNCHECKED (image with no text layer) is surfaced to the
   user as such and never counted as verified.
3. **The discovering test is the AST walk in this report compared to
   `POLICY`**, with import resolution (not name matching) and an explicit
   not-a-model list for the Twilio call. A `messages.create` reachable from a
   router or a pipeline script whose surface id is not in `POLICY` fails the
   build.

**Should `citation_gate` / `allowlist` be absorbed? No — not in Phase B.**
`check_letter` + `allowlist.build` is the reference implementation, it has the
12 Ohio negatives and 9 positives in `tests/verify/golden_law.json` and
`test_citation_gate.py` behind it, and its sentence-level FIGURE rule (strip
every citation string, then bind the rest of the sentence) is subtle enough that
a re-implementation would regress silently. The policy module should **call**
`check_letter(text, held.allowed)` as the `LEGAL_PROVISION` binder for the letter
surfaces and adopt its `Citation` findings as `Finding`s. If, later, the policy
module's own legal binder reproduces `check_letter`'s verdicts on the golden set
exactly (a test, not an assertion), the gate can delegate the other way. Until
that test exists, leave it alone.

---

## E. Also reported

### E.1 Same-named constants and functions across products, different rule sets

AST scan of `backend/routers` + `backend/utils`, top-level names defined in more
than one module with **different** bodies, restricted to those that shape model
output:

| name | modules | why it matters |
|---|---|---|
| `APPEAL_SYSTEM_PROMPT` | provider_appeals.py:27 / health_analyze.py:659 | the divergence you named: gated register vs identifier-withheld register, no shared rule text |
| `DENIAL_SYSTEM_PROMPT` | provider_shared.py:409 / health_analyze.py:555 | Health's carries the "assert no external regulatory status / appeal_rights verbatim" rules; Provider's carries none and additionally drafts an ungated letter |
| `SYSTEM_PROMPT` | eob_parse.py:111 / ai_parse.py:79 / health_analyze.py:129 | three bill/EOB extraction prompts, three field sets, three "never guess" phrasings |
| `_call_claude` | provider_shared.py:110 / employer_shared.py:101 / health_analyze.py:281 | three wrappers: provider's silently wraps a non-JSON HTML reply as `{letter_html, letter_text}` (a letter can enter the pipeline without ever having been JSON); employer's returns None; health's returns the raw response. `billing_contracts` imports provider's and calls it with employer-style positional arguments (A.2). |
| `generate_appeal`, `analyze_contract`, `_generate_trend_narrative`, `_compute_and_cache_trends` | provider / health, billing / provider, employer / provider | same job, no shared code path, so a fix lands in one |

Identical-body duplicates (`_get_claude`, `_generate_otp`, `logout`, OTP
constants…) are plain copy-paste, not policy divergence.

### E.2 Rules duplicated *within* `health_analyze.py`

Counting a rule as duplicated when the same requirement is stated in two or more
prose locations (a prompt sentence and the code that enforces it is not
duplication; that is the design):

1. Reservation-of-rights sentence — comment :652–657 and the appeal-rights bullet (the one you cited).
2. "Do NOT assert external regulatory status (FDA / NCCN / …)" — `DENIAL_SYSTEM_PROMPT`, `APPEAL_SYSTEM_PROMPT`, `APPEAL_EVIDENCE_INSTRUCTIONS` (three statements).
3. "Deadline in the denial's literal words, never convert 72 hours" — three field descriptions in `DENIAL_SYSTEM_PROMPT` and again in `APPEAL_SYSTEM_PROMPT` (four).
4. Provider title: never default to "Dr." — `DENIAL_SYSTEM_PROMPT` and `APPEAL_SYSTEM_PROMPT`.
5. `appeal_rights` only as the denial states them — `DENIAL_SYSTEM_PROMPT` and `APPEAL_SYSTEM_PROMPT`.
6. The four identifier tokens — hand-written into the `APPEAL_SYSTEM_PROMPT` sentence *and* the `IDENTIFIER_TOKENS` dict at :744; the prompt is not generated from the dict, so they can drift.
7. "Do not write bibliographic details yourself" — `APPEAL_EVIDENCE_INSTRUCTIONS` and the user-message preface at :1449.
8. "Only within the source's stated indication" — `APPEAL_SYSTEM_PROMPT` once, `APPEAL_EVIDENCE_INSTRUCTIONS` three times.

Eight; five of them are the DENIAL-prompt/APPEAL-prompt pair restating one rule —
the same-file miniature of the cross-product mechanism in E.1. The remaining
prose→code pairs (`__LETTER_DATE__`, dashes, `_FAB_*` regexes) are correct
design, not duplication. Cross-file: the "there is deliberately no Signal
material" rationale is a near-identical comment in both `provider_appeals.py`
and `health_analyze.py`.

### E.3 Rules that are prose in one product and code in another

A correction first: `sweep_sources.py:75` is a docstring, but the rule it
describes *is* code in the same file — `resolve_candidate` (:391) turns a
candidate into an identifier only after Europe PMC / Crossref confirms it and
`errata.resolves_to_us` agrees. WHU has the rule in both forms. The products
where it is prose **only** are `00_discover_sources.py` ("Every source must be
REAL — do not fabricate citations, DOIs") and `signal_qa`. Health has it as
prose plus a *shape* refusal (`_FAB_*` regexes), which is weaker than resolution
but is code.

| rule | code | prose only | absent / inverted |
|---|---|---|---|
| Never synthesise an identifier | WHU `sweep_sources.resolve_candidate`; Signal `verify.publish`; Health `_validate_evidence_claims` (shape only) | Signal `00_discover_sources`, `signal_qa` | — |
| No section number unless allow-listed | Provider `citation_gate` | Health `APPEAL_SYSTEM_PROMPT` (appeal-rights bullet) | **Broker K3 — inverted: the prompt requires citations** |
| Every figure must be in the document | Provider allow-list sentences (`bind_figure`, live only with rows); Signal publish (claims) | Health ("no statistic not in the summaries", soft flag); `FEE_SCHEDULE_EXTRACTION_PROMPT` ("do not invent or estimate rates"); every narrative ("be specific about dollar amounts") | Signal consensus/summary/glossary; S2 |
| Verbatim — do not convert units, do not relabel | — | Health, four times | Provider ("30 calendar days" hardcoded) |
| Regulatory / guideline status only if a cited item states it | — | Health, twice | everywhere else (E1 industry claims; P6 advice) |
| Unverified is a failure, not a warning | `verify` (UNCHECKED never a pass); `golden_set`; `factcheck_draft`; Provider 502 | — | **Health** (hard failure → letter still returned with `needs_revision`); extraction surfaces (`None` → silence); B1 (`None` stored) |
| Model proposes, code decides | WHU `modelbind`; Health PH-4a.3; Signal publish | design doc §6 | Employer / Broker / Billing entirely; P6 (model computes totals) |
| A source cannot support an event that postdates it | `verify.chronology` (Signal publish, allow-list) | WHU `factcheck_draft` RECENCY (model role) | — |
| PHI never reaches the model | Health `_deidentify_for_model`, `evidence_retrieval._assert_no_phi` | — | **Provider P1 sends `patient_name`; E2/K1a send five raw sample rows** |
| A citation hardcoded in a prompt is a TYPED assertion | — (the provider prompt was cleaned by hand on 2026-09-14) | — | Broker K3 prompt and fallback template; `BrokerLandingPage`/`BrokerDemoPage` copy |

### E.4 Negative-control material already frozen, for Phase B

- 12 wrong Ohio provisions: `backend/tests/verify/golden_law.json` → `negatives` (12), with 9 positives and 2 context negatives; the strings also appear in `tests/test_citation_gate.py:19–33`.
- 59 fabricated DOIs: `backend/scripts/signal/output/verify_sources_2026-09-14.json` (381 rows; 59 `FABRICATED_IDENTIFIER`, 33 `WRONG_DOCUMENT`, 288 `NEVER_FETCHED`, 1 `NO_CONTENT`), tracked in git.
- MONALEESA-7 PMID: `backend/tests/verify/golden_literature.json` → `known_bad[0]` (`pmid:31562796`, resolves to a nivolumab NSCLC paper; HEADING passed, FIGURE refused).
- New, from this pass: **29 U.S.C. § 1185i** cited as CAA §204 — a live production negative for the `usc` system and the K3 surface, resolved against the primary source today.
- Not yet frozen: a named-source negative (an `appeal_rights` item relabelled "ACA independent external review"), and a coded-descriptor negative (a plausible descriptor on the wrong CPT). Both are needed before the two new classes can claim a discovering test.
