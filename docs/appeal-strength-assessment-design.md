# Appeal-strength assessment — design (APPEALS-2)

**Status: DESIGN ONLY, 2026-09-17. Nothing here is built.** Fred's ruling, 2026-09-17: we owe the
user an honest evaluation of whether the evidence and arguments are strong enough to justify the
expense of escalating, with appropriate disclaimers. That is evidence assessment, not legal advice.

Scope, as ruled. **IN:** whether the denial's stated reason is consistent with the record; whether
the clinical/documentary evidence the appeal relies on is present and specific; whether the payer's
own policy language (as the payer words it) covers the service; payer procedural errors visible in
their own letters; claim amount; appeal deadlines as the payer states them; what escalation
typically costs. **OUT:** likelihood of winning litigation, what any statute or regulation
requires, whether the user should sue, any characterisation of legal rights or obligations.

This replaces the model-authored `appeal_strength` / `appeal_strength_reason` /
`escalation_path` fields that APPEALS-3 retired (they asked the model for the user's judgment and
defined "strength" as "legal/regulatory basis"). `appeal_strength` (high/medium/low, still emitted
by the provider prompt today) is a verdict without legs and should retire when this ships.

---

## 1. Shape: factors, each standing on held text

An assessment is a list of **factors**. Each factor is one question about the appeal, answered
in one of exactly three states, and every answer names the document text it rests on:

```
factor:
  id:            F3
  question:      "Is the evidence the letter relies on actually present and specific?"
  state:         SUPPORTED | NOT_SUPPORTED | UNASSESSABLE
  finding:       one or two sentences, in the user's documents' own words where possible
  rests_on:      [ {document, locator, retrieved_at, quote} ... ]   # >= 1 for any non-UNASSESSABLE state
  would_change:  what evidence, if the user supplied it, would move this factor (see §6)
```

`rests_on` uses the binding discipline Signal already uses (`verify/policy.py`,
`verify/types.Document`): a document the system HOLDS (the denial letter text, the payer's policy
text, the retrieved evidence record, the practice's contract excerpt, a clinical note the user
uploaded), a **locator** (character offset span in the held text, or the reference key for a
retrieved record, or the page/line for an uploaded PDF), the **retrieved_at** timestamp, and the
verbatim **quote**. The quote is what the user checks against their own copy. No factor may rest
on the model's recollection, on the shape of the data ("there is no policy text, so the policy
probably does not cover it"), or on another factor.

**UNASSESSABLE is a first-class state, not a weak one.** It is reported when the factor's
question cannot be answered from held text — because the document is not held (no policy text was
supplied), because the held text is unreadable (image PDF with no text layer;
`Held.has_unreadable_document()`), or because the question needs a fact the record does not
contain. It says *why* and *what would make it assessable*. It never defaults to "weak", and it is
never inferred from the data's shape (the standing rule).

### The factors

| id | question | rests on (held text) | states |
|---|---|---|---|
| F1 | **Denial reason vs. record.** Does the denial's stated reason describe this claim? (e.g. CO-97 "bundled" on two codes the record shows at different sites; "duplicate" on two different dates; "missing information" naming an item that is on the claim) | denial letter / remittance text (reason, code, cited criterion); claim data; uploaded notes | SUPPORTED = record contradicts the reason, quoted both sides · NOT_SUPPORTED = record is consistent with the reason · UNASSESSABLE = no record text to compare |
| F2 | **Payer's own policy language.** Does the payer's medical policy / plan terms / fee schedule, *as the payer words it*, cover this service and indication? | the payer's policy text (fetched from the payer's published URL or uploaded), plan terms, contract/fee-schedule excerpt | SUPPORTED = policy text lists this indication/code, quoted · NOT_SUPPORTED = policy text excludes it, quoted · UNASSESSABLE = the policy the denial names is not held |
| F3 | **Evidence present and specific.** Is the clinical/documentary evidence the letter relies on actually held, and does it address this diagnosis, stage and service (not a neighbouring one)? | retrieved evidence records (title, indication, PMID/DOI, verified per `verify/evidence.py`); uploaded clinical notes with dates | SUPPORTED = ≥1 verified record whose stated indication matches the diagnosis given, quoted · NOT_SUPPORTED = evidence held but off-indication (the letter already says so) · UNASSESSABLE = no evidence retrieved / no notes supplied |
| F4 | **Documentation named vs. documentation held.** Does every document the letter says is attached or on file exist in what the user uploaded? | the letter's own "attached"/"on file" statements; the upload manifest | SUPPORTED = each named document is present · NOT_SUPPORTED = letter names documents the user has not supplied, listed · UNASSESSABLE = no manifest |
| F5 | **Payer procedural facts visible in the payer's own letter.** Code mismatch between denial code and stated reason; contradictory reasons; a clinical denial with no reviewer specialty stated; a step the payer says it takes (peer-to-peer, criteria disclosure) that its letter shows it did not take | denial letter text only | SUPPORTED = a discrepancy is present, both spans quoted · NOT_SUPPORTED = none found in the held text · UNASSESSABLE = denial text not held (image only) |
| F6 | **Amount at issue.** Billed amount; paid amount; contracted amount when held; the difference | remittance / EOB / contract excerpt | always a fact, never a judgment; UNASSESSABLE only if no amount is in the record |
| F7 | **Deadlines as the payer states them.** The payer's own words for the appeal window and any expedited path; days remaining computed from the denial's date *as stated in the denial* | denial letter text (`appeal_rights`, `appeal_deadline_hint` verbatim — the extraction already forbids relabelling) | fact; UNASSESSABLE if the denial states none |
| F8 | **Appeal history.** Level reached (first-level sent / decided), dates, outcome, amount recovered | `provider_appeals.status`, `provider_appeal_outcomes`; Health: on-device history (`appeal_drafted`, letter text) | fact; UNASSESSABLE if the user has not recorded outcomes |
| F9 | **What escalation typically costs.** Ranges for the next steps the payer's letter names (external review fee where the payer's letter states one; independent review organisation cost where published; attorney consultation ranges) — each with its published source and date | a curated, sourced cost table (does not exist yet — §7) | fact with source; UNASSESSABLE for any step with no sourced figure |

Nothing in F1–F9 asks whether a law was followed, whether a right exists, or what a tribunal would
do. F5 is deliberately limited to what the payer's own letter shows about the payer's own process.

## 2. No verdict-shaped aggregate that hides its legs

The assessment has **no score, grade, colour, or high/medium/low line**. The output order is
fixed: factors first (F1–F5, then F6–F9 facts), each with its state, finding, quotes and
"would change" line; only then an optional **summary**, which is generated by code — not the
model — from the factor states, and reads like this:

> Of five assessable questions about this appeal, the record supports three (F1, F3, F5) and does
> not support one (F4: two documents the letter names are not in what you uploaded); one could not
> be assessed (F2: the policy the denial cites, EHP.LAB.0142, is not on file). Amount at issue
> $3,500.00. Appeal window as the denial states it: 180 days from the notice date. This summary is a
> count of the factors above and nothing more.

The precedent is Fred's §6a reaction to the Signal page-level support aggregate: an aggregate that
answers a question the reader is not asking is worse than none. A count of factor states answers
only "how many of these questions could be answered, and which way", which is the question the
reader is asking. It is generated from the factor list so it cannot say anything the factors do
not.

## 3. Honest absence

When fewer than two of F1–F5 are assessable, the assessment leads with a **"too thin to assess"**
block instead of the summary, listing what is missing and which factor each missing document
would unlock:

> This record is too thin to assess. Held: the denial letter and the claim. Not held: the payer's
> medical policy EHP.LAB.0142 (would allow F2), any clinical note or pathology report (F1, F3, F4),
> the ordering provider's letter of medical necessity (F4). The letter can still be sent; the
> assessment cannot say more than the denial letter itself says.

F6–F9 are still shown as facts when available.

## 4. Economics as facts

Presented in one block, each line a fact with its source; no recommendation, no ratio, no
"worth it":

- **Amount at issue**: billed $X; paid $Y (remittance dated …); contracted $Z (contract excerpt,
  page …) — the difference $D. *Source: the user's documents.*
- **Already spent** (when the user records it): internal-appeal time or fees the user entered;
  provider letter fees if recorded. *Source: user entry, dated.* UNASSESSABLE if not recorded —
  the system does not estimate it.
- **Typical cost of the next steps the payer's letter names**: e.g. "External review: the denial
  letter states no fee; [state's independent review programme page, retrieved YYYY-MM-DD] states
  the consumer pays $0 / up to $25." "Attorney consultation: published ranges from [named,
  dated source]." Each figure carries its source and retrieval date and is UNASSESSABLE when
  none is held. The table is curated and reviewed by a person (like `candidates.json` was meant
  to be), stored under `backend/data/verify/escalation_costs.json` with `source_url`,
  `retrieved_at`, `reviewed_by`, and re-checked on a schedule like Signal's sources.

The word "recommend" does not appear. Nothing compares amount to cost for the user; both are on
the page and the arithmetic is theirs.

## 5. Disclaimers — exact wording and placement

Placed **at the top of the assessment, before the first factor**, as body text in the same type
size as the factors (not a footer, not a tooltip), and repeated once at the end of the economics
block:

> **What this is.** This assessment compares the appeal letter and the documents you provided
> against each other and against the payer's own written policy where you supplied it. It is not
> legal advice, it does not predict how the payer, an external reviewer, or anyone else will
> decide, and it does not tell you what to do next. Every finding below quotes the document it
> rests on so you can check it against your own copy. Where a question could not be answered from
> your documents, it says so. The decision to appeal further, and whether to spend money doing it,
> is yours.

On the economics block:

> **About these figures.** Amounts are taken from your documents and the payer's letter. Cost
> ranges for further steps come from the published sources named beside them, on the dates shown;
> they are not quotes for your case. Nothing here weighs one number against another for you.

Neither paragraph uses "rights", "entitled", "law", "statute", "regulation", or "attorney" beyond
the phrase "not legal advice" — and the LEGAL_REGISTER gate (APPEALS-3) runs over the assessment
text too, so a factor finding that drifts into the register is refused like a letter would be.

## 6. Falsifiability — what would change each factor

Every factor carries a `would_change` line generated from its state:

| factor | if SUPPORTED, what would reverse it | if NOT_SUPPORTED / UNASSESSABLE, what would move it |
|---|---|---|
| F1 | a payer document showing the record does match the denial reason (e.g. the same site on both codes in the operative note) | the operative/encounter note for the date of service; the corrected claim |
| F2 | the payer's policy text at a version dated on or before the date of service that excludes the indication | the policy the denial names (its identifier is quoted), or the plan's benefit terms |
| F3 | a retraction or correction to a cited record (Signal's re-check watches these); a note showing a different stage/diagnosis than the one given | a verified record whose stated indication matches the diagnosis and stage; the pathology report |
| F4 | — | the documents the letter names, uploaded |
| F5 | a fuller payer letter (e.g. the reviewer's specialty stated elsewhere) | the complete denial letter with all pages |
| F6–F9 | corrected amounts / dates / outcome entries from the user's documents | the missing document or entry, named |

The user can act on any line by supplying the named document; the assessment re-runs and the
factor's `rests_on` shows the new quote.

## 7. What the system already holds, and what it does not

**Held today (file:line, checked 2026-09-17):**
- Denial letter text and its structured extraction, verbatim-bound — `backend/routers/health_analyze.py:555-611` (`DENIAL_SYSTEM_PROMPT`: `specific_criterion`, `weakness`, `appeal_rights`, deadlines "in the denial's own literal words", `payer_guideline_id`, `reviewer_entity`, `billed_amount`, `denial_category`); gated at `routers.health_analyze::analyze_denial` (policy.py: every verbatim field binds to the denial text). **Feeds F1, F5, F6, F7.**
- Retrieved, registry-verified clinical evidence with stated indication — `backend/utils/evidence_retrieval.py` (PubMed records with title/year/study type; CMS NCD/LCD/MolDX with title/URL/effective date), verified by `verify/evidence.py` + `verify/literature.py` (APPEALS-3). **Feeds F3.** Off-indication records are already flagged (`review_flags`) — the F3 NOT_SUPPORTED state exists in embryo.
- The letter's own attachment statements — `health_analyze.py` `_build_reviewer_checklist` (`:1204`) already lists what the letter claims accompanies it. **Feeds F4** (needs a manifest to compare against — not held).
- Amounts and codes — provider: `GenerateAppealRequest` (`provider_shared.py:304-318`: `billed_amount`, `cpt_code`, `denial_code`), contracted rates when a fee schedule is on file (`provider_appeals.py` `_lookup_contracted_rates`). Health: `billed_amount` from the denial. **Feeds F6** (paid amount is NOT held on the health side).
- Appeal history — provider: `provider_appeals.status` (drafted/sent/won/lost/pending/partial), `outcome_amount`, `recovered_amount`, `resolution_date`, `notes` (`provider_appeals.py` `update_appeal_status`), and `provider_appeal_outcomes` (migration 048: `appeal_submitted_at`, `outcome`, `outcome_recorded_at`). Health: on-device `appeal_drafted`, letter text, `referred_to_attorney` (never set true anywhere — `localBillStore.js:64,151`). **Feeds F8**, partially.
- The binding machinery — `verify/policy.py` (`Held`, `Finding`, `Verdict`), `verify/types.Document/Identifier/Resolution`, `verify/text.agreement`, `Held.has_unreadable_document()` (image PDFs → UNASSESSABLE, not guessed).

**Not held today (would need):**
- **The payer's policy text.** The denial names it (`payer_guideline_id`, e.g. EHP.LAB.0142) but nothing fetches or accepts it. F2 is UNASSESSABLE on every appeal until a policy document can be uploaded or fetched from the payer's published URL and held as a `Document` with text layer and retrieval date.
- **Clinical documentation and an upload manifest** (notes, operative reports, pathology, prior authorisation) — the provider path receives none (APPEALS-3 item 10 report); the health path defers them to the ordering provider. F1, F3 (clinical half), F4 depend on this.
- **Paid amount and remittance text on the health side**; **appeal level** on both sides (no first/second/external distinction is modelled; `provider_appeals.status` has no level).
- **What the user has already spent** — no field anywhere; the system must not estimate it.
- **A sourced escalation-cost table** — does not exist; F9 is UNASSESSABLE until it is curated and reviewed.
- **A persistence home for assessments** — factor lists with `rests_on` bindings need a table (or the on-device store on the health side) with the same append-only posture as `provider_appeals.verification`.
- **A user-facing surface** — none of this renders today; `escalation_path` was generated for months and never displayed (APPEALS-1 §5).

**Order of work if approved (not started):** hold the payer's policy text (upload + fetch) → hold
an upload manifest → compute F1–F8 as code-authored factors over held text with the existing
binding functions (the model may *draft* a finding sentence, but every quote and state is
code-checked against `rests_on`, and the LEGAL_REGISTER gate runs over it) → curate the cost
table → render factors-first with the two disclaimers → retire `appeal_strength`.
