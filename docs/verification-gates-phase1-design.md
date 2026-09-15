# Phase 1 — resolve / fetch / bind, for both registries

**Status: APPROVED 2026-09-14 with four amendments (§§ 4a, 5a, 5b, 8). BUILT the same day: `backend/verify/` — see §11 for what was built and what the golden sets said.** Phase 0 (`f0bb63e`) removed every
clinical and legal assertion the system could not support. Phase 1 is the
mechanism by which an assertion becomes supportable, so that Phase 2 can
invert `utils/citation_gate.py` from a blocklist to an allow-list and Phase 3
can republish Signal topics one at a time.

The rule the design serves, in one line:

> A surface may state a fact about a document only if the system resolved the
> document's identifier, fetched the document's bytes, and found the fact in
> them. No model decides any of the three.

## 1. What went wrong, so the design answers it

Two registries, one failure shape, seen four times on 2026-09-14:

| registry | what was cited | what it was |
|---|---|---|
| literature | 220 DOIs in the Signal corpus | 27% resolve to a different paper, 27% to nothing; 380/381 sources never fetched (`verify_sources.py`) |
| law | OAC 3901-1-54, in 7 of 10 appeal letters, as the health-claims settlement rule | the property-and-casualty rule |
| law | ORC 3901.38, in 5 letters, as the 30-day prompt-pay rule | the *definitions* section; the deadline is § 3901.381, interest § 3901.389 |
| law | 42 CFR 410.32(a), hardcoded in the prompt as the federal medical-necessity standard | the rule that diagnostic tests be ordered by the treating physician; Medicare only |

The identifier was plausible, the register was authoritative, and nothing
checked that the identifier named the thing the sentence said it did. The ORC
3901.38 case matters for the design: its heading ("Prompt payments to health
care providers definitions") *shares words* with the claim ("prompt pay"), so a
heading check alone passes it. Only a check that the number "thirty days" is
in the section's text catches it. Binding needs more than one kind.

## 2. The interface (one; two adapters)

```
Identifier   system     doi | pmid | pmcid | nct | cfr | usc | orc | oac | state_code | cms_iom | ncci
             value      normalised ("10.1056/nejmoa2032183", "3901.381", "42:424.5(a)(6)", "100-04:1:80.3.2")
             raw        as it appeared in the text
             provenance RESOLVED_FROM_HELD  parsed from a URL / document we already hold
                        TYPED              written by a person or a model, from memory
                        SEARCHED           returned by a lookup on a title or a phrase

resolve(Identifier) -> Resolution
             exists     EXISTS | NONEXISTENT | UNCHECKED      (UNCHECKED is never a pass)
             registry   which registry answered, and its own id for the record
             heading    what the registry says the thing is (title / section heading)
             canonical  the URL a reader would follow
             checked_at

fetch(Resolution) -> Document
             sha256, path, content_type, retrieved_at, final_url
             text_layer DECLARED_SOUND | DECLARED_DEFECTIVE | UNEXTRACTED   (a PDF with no text is not "absent")
             (content-addressed: one copy per distinct bytes; a changed document is a new hash, both kept)

bind(Assertion, Document) -> Binding
             kind       HEADING | FIGURE | SPAN | APPLICABILITY
             ok         true | false
             evidence   the matched heading words / the numbers found / the span offsets / the rule that applied
             reason     when false, which check failed and what the document had instead
```

Three verbs, each a pure function of its inputs, each deterministic. Every
result is written to a store keyed by (identifier, sha256), so a verdict is
re-readable and a re-run is a diff, not an argument.

## 3. The registries

### 3a. Literature (Signal; WHU already does most of this)

| system | resolve | heading | fetch |
|---|---|---|---|
| doi | Handle System `doi.org/api/handles/{doi}` (every RA, not just CrossRef) → then CrossRef `works/{doi}` | CrossRef `title[0]`, container, published | Unpaywall OA location → Europe PMC full-text XML (`{PMCID}/fullTextXML`) → publisher URL on the operator's machine |
| pmid / pmcid | Europe PMC REST `search?query=EXT_ID:…` / `PMCID:…` | `title` | Europe PMC XML when `inEPMC = Y` |
| nct | ClinicalTrials.gov v2 `studies/{NCT}?fields=protocolSection.identificationModule,…` | `officialTitle || briefTitle || acronym` — all three, because our titles are the acronym | the registry record itself (JSON), incl. `resultsSection` for figures |

All of this exists: `scripts/signal/verify_sources.py` (resolve + heading),
`scripts/whatholdsup/acquire_sources.py` + `source_store.py` (fetch, identity,
substance), `find_access.py` (OA routes, provenance discipline). Phase 1 puts
them behind the one interface; it does not rewrite them.

### 3b. Law (appeal letters; nothing exists today)

| system | resolve | heading | fetch | notes |
|---|---|---|---|---|
| cfr | eCFR versioner API `api/versioner/v1/full/{date}/title-{T}.xml?section={S}` (needs `Accept-Encoding: gzip`) | `<HEAD>` of the section | the same call; XML → text | versioned by date; cite the date fetched |
| usc | `uscode.house.gov` / govinfo `USCODE` API | section heading | same | |
| orc / oac | `codes.ohio.gov/ohio-revised-code/section-{N}`, `/ohio-administrative-code/rule-{N}` | the page's section title | HTML → text | one adapter per state; Ohio first because that is where the letters are |
| cms_iom | `cms.gov/…/downloads/clm104c{NN}.pdf` per chapter | TOC-parsed heading for the section number (`pdftotext`) | the chapter PDF, section sliced by heading | 100-04 ch.1 § 80.3.1 is "Incomplete or Invalid Claims Processing Terminology"; duplicates are § 120 |
| ncci | `cms.gov/files/document/{NN}-chapter{N}-ncci-medicare-policy-manual-{YEAR}-final.pdf` | chapter section letter heading | same | annual; cite the year |

Law is the easy registry: free, stable URLs, machine-retrievable, no licence,
no paywall, and a section either has a heading or it does not.

## 4. Binding — four kinds, and why one is not enough

| kind | test (deterministic) | what it catches | source of the test |
|---|---|---|---|
| HEADING | distinctive content words of the assertion's characterisation ∩ the registry heading; zero shared = WRONG_DOCUMENT; boilerplate stripped (trial / phase / randomized / section / code …) | OAC 3901-1-54 "property/casualty"; ORC 3902.11 "coordination of benefits"; a DOI that names a different paper | `verify_sources.title_agreement`, `errata.resolves_to_us` |
| FIGURE | every number in the assertion (30 days, 45 days, 18%, HR 0.80, 95% CI 0.72–0.90, P<0.001) is present in the document text, after typography normalisation (middle dot, en dash, unicode minus, thin space) | ORC 3901.38 cited for "thirty days" (heading passes, figure fails); PALOMA-3 "p=0.0221" (paper says 0.09) | `canary.py`, `registry_figures.py` |
| SPAN | a quoted passage is in the text verbatim, widened to sentence boundaries with an envelope, so "8%" is never bound to a document that says "8% to 20%" | altered quotations; a quote attributed to the wrong document | `spancheck.py` B2, `autobind.py` |
| APPLICABILITY (law only) | a rule table, not a lookup: 42 CFR parts 400–498, the IOM manuals and NCCI bind only to a Medicare/Medicaid payer; a state code binds only to the practice's state; a definitions section (heading contains "definitions") binds only to a definition | 42 CFR 424.5(a)(6) in a letter to Anthem commercial; an Ohio statute in a Texas letter | new; small |

### 4a. FIGURE normalisation — where true citations would wrongly fail

Law and papers write the same number many ways, and a gate that misses one
refuses a true citation: "thirty days" / "30 days" / "30 calendar days" /
"thirty (30) days"; "18%" / "18 per cent" / "eighteen per cent" / "eighteen
percent"; "0·561" (Lancet middle dot) / "0.561"; "0.72–0.90" (en dash) /
"0.72-0.90"; "P<0.001" / "P < 0·001"; "1,961" / "1961". So FIGURE compares
**canonical numeric values**, not strings: both the assertion and the document
are reduced to the set of numbers they contain, where a number may be written
in digits (with thousands separators, decimals in point or middle dot,
percent signs, unicode minus, ranges split into their bounds) **or in words**
(cardinals one … ninety-nine, hundred / thousand / million composition,
"eighteen per cent", "thirty-nine", "two and a half" → 2.5), and hyphenated
day/percent forms ("30-day", "18-percent"). A figure in the assertion is
found when its canonical value is in the document's set. Units are not
compared — "30 days" and "30 per cent" both canonicalise to 30 — because
the failure this guards against is a number that is not there at all, and a
unit mismatch with the number present is a defect of a different, rarer
kind. The word-number parser is deliberately small and tested on the exact
forms above; a form it does not parse is a false refusal, which is the safe
direction, and is added to the parser when met.

### 4c. CHRONOLOGY — the fifth binding kind (added 2026-09-14)

A source cannot support a claim about an event that postdates it. The
existence → ordering mechanism from this document's own taxonomy, made a
binding kind: the dates a claim references — an explicit date in the text,
the registry's own dated events for the source (a paper cannot support a
claim about its own retraction), or a named event from the curated table
`backend/data/verify/events.json` (phrase, date, source, curator) — are
compared with the source's publication date from the registry, and a claim
that postdates its source is **IMPOSSIBLE**: the link is refused whatever
HEADING and FIGURE say, and IDENTITY_ONLY is not available to it. Reference
negative: the three GMC / struck-off claims on the mmr record, true statements
the 1998 paper cannot contain. Dates leave FIGURE's remit — "in 2004" is a
when, not a quantity the document must state. **Law is not judged:** the
registries expose the current version's effective date and a partial version
list, not enactment, so "before it existed" cannot be shown and the check
says cannot-be-judged rather than refuse.

### 4b. HEADING abstains (added 2026-09-14)

HEADING has a third outcome. After boilerplate removal, if fewer than **N = 2**
distinctive words remain on either side, HEADING returns `cannot_discriminate`
— not ok — and FIGURE or SPAN becomes **mandatory** for that source: an
abstaining HEADING with a passing mandatory kind binds; with a failing one, or
with nothing mandatory in the assertion, it refuses. Containment ("MONARCH 3"
inside the registry's acronym field) is decisive whatever the count.

Why: every boilerplate addition (oncology today; cardiology and diabetes
tomorrow) weakens HEADING by leaving fewer words to compare, and nothing
noticed. Abstention converts the weakening into a statement about what the
check could not determine.

How N was chosen: from the golden sets. The positive with the fewest
distinctive words and no figure or quotation to fall back on is 45 CFR
147.200 — "summary of benefits and coverage" → {summary, benefits}, exactly
two. At N = 3 it would abstain and, with nothing mandatory, be refused: a
false negative. At N = 2 every positive still binds (0/12, 0/8) and four
law negatives route through abstention (headings "Rules", "Purpose of
sections", "Coverage of preventive health services", "Incomplete or Invalid
Claims Processing Terminology") — all still refused, on HEADING with the
reason "cannot_discriminate … cannot be bound". No positive abstains.

A binding is `ok` only if every kind that applies is `ok` (with the abstention rule above). HEADING applies
always; FIGURE whenever the assertion carries a number; SPAN whenever it
quotes; APPLICABILITY for law. R1 from the WHU bindings spec governs: a
binding asserts presence or absence of text, never that the sentence is *true*.

## 5. Where the gates sit

### Letters (Phase 2)

```
request (denial_code, state, payer_type)
  → candidate provisions        a curated table per (denial_code, state): the provisions counsel would
                                actually use. Human-written, few, reviewed. Not a search.
  → resolve → fetch → bind(HEADING, APPLICABILITY)       → the ALLOW-LIST for this letter
  → the model receives each allowed provision as {citation, heading, fetched excerpt}
    and is told: cite only these, quote from the excerpt
  → generation
  → citation_gate.find_citations(letter)                  (exists today: f0bb63e)
      every citation ∈ allow-list, else refuse
      every number attached to a citation: bind(FIGURE) against that provision's text, else refuse
  → one regeneration with the violations named; then no letter (502)
```
### 5a. What these gates do and do not deliver — the residual

The gates verify that a cited provision **says what the letter claims** and
**applies** to the payer and state at hand. They do **not** verify that it is
the **right provision to cite for that denial** — that it is apposite, that
counsel would reach for it, that a better one does not exist. That judgement
lives in the human-curated candidate table and nothing checks it. So the
table carries, per row: `curator` (who chose it), `curated_on` (date),
`rationale` (why this provision for this denial code, in a sentence), and
`reviewed_by` / `reviewed_on` when a second person has looked. Downstream,
"verified" means *resolved, fetched and bound*; it never means *apposite*,
and no surface may say otherwise.

### 5b. Graceful geographic degradation is a product property

An unsupported state — no adapter, or an adapter with an empty candidate
table — yields an empty allow-list and therefore a letter that cites nothing
and states obligations in plain words: exactly what Phase 0 produces today.
The product works everywhere on day one and strengthens state by state as
adapters and curated rows are added. This is the intended behaviour, not a
gap; a letter that cites nothing is complete, and a letter that cites the
wrong state's law is not.

When the allow-list is empty — today, and for any state without an adapter —
the letter cites nothing and says obligations in plain words, which is what
Phase 0 already produces. The gate's default never changes; only the list grows.

### Signal (Phase 3)

```
for every source of a topic:
    resolve (EXISTS) → fetch (bytes, not a summary) → bind(HEADING)  → verdict OK
content_text := fetched text                                          (the corpus rebuild)
claims re-extracted from fetched text only; every figure in a claim: bind(FIGURE) against its source
topic may be set status = 'published' ONLY by publish_topic.py, which runs the above and refuses on any non-OK
```
`status = 'published'` is never set by hand and never by a script that did not
just run the gate. Migration 078 makes that column the only thing that shows a
topic; this is what earns the flip.

### Marketing copy (Phase 4)

Every sentence in the Phase 0 inventory (`ReportView`, `SignalLanding`,
`MethodologyView`, the homepage meta, the email footer) is rewritten to
describe the mechanism above, once it exists — "indexes peer-reviewed trials"
becomes true only when fetch has run.

## 6. The model's role, precisely

A model may **propose**: which provision might bear on a denial; which
paragraph of a paper a sentence came from; which figure a claim rests on. The
machine **decides** every proposal by string comparison against fetched bytes
and drops what it cannot find, recording nothing. This is `modelbind.py`'s
division of labour and it is the only one that has held.

No model is called inside `resolve`, `fetch`, or `bind`. Not for
normalisation, not for "fuzzy" matching, not to summarise a long section.

## 7. Storage

* Documents: content-addressed files (`sha256[:2]/sha256.ext`), one copy per
  distinct bytes, superseded and also-held tracked — `source_store.py`'s
  model, which has survived five identity incidents.
* Verdicts: one row per (identifier, sha256, kind), append-only, with the
  run id and the registry's answer. **Not in the `signal_*` namespace** and
  **not a foreign key to a frozen table** (a REFERENCES installs triggers on
  the referenced table). Latest row per identifier is what a gate reads.
* Runs: every run of the gate records what it resolved, fetched and bound,
  and exits non-zero on any non-OK — the `verify_sources.py` discipline.

## 8. What WHU already has, and the closure

WHU has `resolve` (identifier from held URL only: `find_access.py`), `fetch`
(`acquire_sources.py`), identity and substance (`source_store.identifies`,
`substance`), FIGURE and SPAN binding (`spancheck.py`, `registry_figures.py`),
and a corrections check that already does HEADING for DOIs (`errata.resolves_to_us`)
— but reports a wrong-document result as `UNCHECKED` → WARN, not BLOCK. The
one thing WHU lacks is exactly what Signal lacked: **an identifier-level gate
that blocks**. `source_store.identifies()` accepts bytes that contain the
record's own DOI string, so a wrong DOI fetched via doi.org returns the wrong
paper *containing that DOI* and passes identity; the defence is downstream at
B1/B2.

Closure — **ruled 2026-09-14: package boundary YES, verdict severity NO.**
Extracting resolve / fetch / identity / FIGURE / SPAN behind the shared
interface adds nothing to WHU's dependency closure that WHU does not already
call (Handle, CrossRef, Europe PMC, ClinicalTrials.gov). But turning
`errata.resolves_to_us` from WARN to BLOCKING would change what WHU
publishes, and WHU is the reliability baseline — that is altering the
apparatus mid-study. So: the boundary is built; WHU's own modules and every
one of its verdict severities stay exactly as they are until the operator's
reviewer signs off on the severity change. The shared package must not be
imported by anything under `scripts/whatholdsup/` before that sign-off.

## 9. Acceptance — how to know it works, before it is trusted

Reproducing the errors already found is necessary and **not sufficient**: a
gate that refuses everything reproduces every one of them. Acceptance
requires both directions, and each failure on the kind it should fail on.

* law — **negative controls**: the 12 wrong provisions from the 2026-09-14
  inventory, each asserted to fail on a named kind: ORC 3901.38 *passes*
  HEADING and *fails* FIGURE ("thirty days" is not in the definitions
  section); OAC 3901-1-54 passes HEADING and fails APPLICABILITY (property /
  casualty scope); ORC 3902.11 / .13 / .14 / .01 and 3923.021 fail HEADING;
  42 CFR 410.32(a) and 424.5(a)(6) fail APPLICABILITY against a commercial
  payer; 45 CFR 147.130 fails HEADING; IOM 100-04 ch.1 § 80.3.1 fails HEADING
  ("Incomplete or Invalid Claims Processing Terminology" is not duplicates);
  "Ohio Department of Insurance claims processing regulations" fails
  `resolve` (no identifier). **Positive controls**: ORC 3901.20, ORC 3922.01,
  45 CFR 147.200, IOM ch.1 § 80.3.2 and ch.12 § 30.6.6 and NCCI ch.I § D
  (against a Medicare payer), plus the two provisions the letters *should*
  have cited — ORC 3901.381 ("thirty days" / "forty-five days") and ORC
  3901.389 ("eighteen per cent") — must pass every applicable kind. The last
  two are what test word-number normalisation.
* literature — **negative controls**: the 381-source
  `verify_sources_2026-09-14.json` snapshot; the 59 FABRICATED_IDENTIFIER and
  33 WRONG_DOCUMENT verdicts must reproduce exactly. **Positive controls**:
  the snapshot has none — all 381 fail — so a hand-verified known-good set of
  ~12 real sources (mixed DOI / NCT / PMID, at least one open-access with full
  text fetched and at least one abstract-only) that the gate must admit,
  checked by a person against the registry before it is used as a control.

**How the positive controls were confirmed — the record.** Law: all eight
were checked against the primary source *before the gate existed*, during the
2026-09-14 citation audit, with a different tool (WebFetch of codes.ohio.gov
and the eCFR; `pdftotext` on the CMS and NCCI PDFs) and read by a person —
independent of anything the package returns. Literature: the twelve
identifiers were typed from memory and first admitted by reading the
heading the gate's own `resolve()` printed — a human read, but of the gate's
output, with the gate's `ok` as the criterion; that process admitted the
wrong MONALEESA-7 PMID until FIGURE removed it, so it could not be trusted
for the other eleven either. Every one was therefore re-verified outside the
package in the title→identifier direction (exact-title or
intervention/condition search on Europe PMC and ClinicalTrials.gov v2
returning the identifier in the set, title read back). All twelve matched;
the note in `golden_literature.json` records this. The rule going forward:
a control is admitted only after a title→identifier lookup a person has
read, never on the gate's own ok.

Report the **false-negative rate on both** (known-good refused) alongside
the reproduction, and treat the two sets as the calibration set for the
boilerplate lists and thresholds — they are small, and a new false negative
found in use is added to the set, not tuned away.

## 10. Build order (Phase 2 onward; nothing in Phase 1)

1. `resolve` + `bind(HEADING)` for the literature systems, wrapping
   `verify_sources.py` — golden set 381 must reproduce.
2. `resolve` + `fetch` + `bind(HEADING, FIGURE, APPLICABILITY)` for `cfr`,
   `orc`, `oac`, `cms_iom`, `ncci` — golden set 19 must reproduce.
3. Invert `citation_gate` to allow-list mode with an empty list; behaviour
   unchanged; then the curated candidate table for Ohio × 7 denial codes.
4. `publish_topic.py` and the corpus rebuild, one topic, with the gate.

## 11. Built 2026-09-14 — `backend/verify/`

| file | what |
|---|---|
| `types.py` | `Identifier`, `Resolution`, `Document`, `Binding`, `Context`, the enums |
| `numbers.py` | FIGURE normalisation (§4a): digits, thousands, middle-dot decimals, percent, ranges, unicode minus, word-numbers with hundred/thousand composition and fractions; adjectival forms ("two-sided") excluded; an ASCII hyphen before a number kept as a dash too (the manual's modifier "-25") |
| `text.py` | `agreement()` — the distinctive-word HEADING test with a literature boilerplate list and a law one |
| `bind.py` | the four kinds; `bind_all()` |
| `literature.py` | `identify / resolve / fetch` for DOI (Handle → CrossRef), PMID/PMCID (Europe PMC), NCT (ClinicalTrials.gov v2, three titles); fetch = Europe PMC full-text XML where held, else the abstract, else the trial record |
| `law.py` | `identify / resolve / fetch` for CFR (eCFR versioner API, paragraph-sliced), ORC/OAC (codes.ohio.gov, section + chapter heading), CMS IOM chapters and the NCCI manual (PDF, `pdftotext`, section-sliced) |
| `http.py` | one getter, record/replay cache; the golden sets replay from `tests/verify/fixtures/http` (90 responses recorded live 2026-09-14) |
| `__main__.py` | `python -m verify "<cite or id>" --assert "…"` — prints what each gate found, for a person to read |

**Acceptance, both directions, as amended (§9):**

* Literature — negatives: all 59 FABRICATED_IDENTIFIER and all 33 WRONG_DOCUMENT
  of the 381 reproduce source for source, **and seven more** are refused that
  the 2026-09-14 run passed on the word "cancer" (pinned by id in
  `test_golden_literature.py`; each read and each a different document,
  including the EPIC-alcohol → lipid-nanoparticle case from
  `verify_sources.py`'s own docstring). Positives: 12 real sources (4 DOI,
  3 PMID, 1 PMCID, 4 NCT; 5 open-access full texts fetched, 2 abstract-only,
  4 trial records) — **false-negative rate 0/12**. One negative control sits
  beside them: `pmid:31562796`, typed from memory while assembling the set,
  resolved to a lung-cancer trial and passed HEADING until "advanced" and
  "cancer" stopped counting as distinctive. The set caught its own author.
* Law — negatives: the 12 wrong citations each fail on the named kind
  (3901.38 passes HEADING, fails FIGURE; 3901-1-54 passes HEADING, fails
  APPLICABILITY; 424.5(a)(6) passes HEADING on its paragraph, fails
  APPLICABILITY; the unnumbered one fails at resolve). Positives: 8 —
  **false-negative rate 0/8**, including "thirty days" / "forty-five days"
  (3901.381) and "eighteen per cent" (3901.389) through word-number
  normalisation. Two context negatives: the right manual section against a
  commercial payer, the right Ohio section for a Texas practice — both
  refused on APPLICABILITY.

Three calibrations made by the sets, recorded so they are not mistaken for
tuning: oncology-generic words added to the literature boilerplate; for law,
a paragraph citation's own words and the Ohio chapter title count as heading
candidates ("Basic conditions" and "Definitions" identify nothing alone);
an ASCII hyphen before a number is a dash as well as a sign.

**Kept honest over time:** `.github/workflows/verify-gates.yml` runs the
golden sets against the recording on every push to the package (with
`poppler-utils` installed so the manual adapters run rather than skip, and a
step that fails if any entry skipped), and monthly runs
`scripts/verify_live_registries.py` against the live registries with the
cache bypassed, failing on any divergence between live and recorded — a
changed heading, a changed document, an identifier that stopped resolving,
a flipped binding.

## 12. Phase 2, built 2026-09-14 — the candidate table and the inverted gate

* `backend/data/verify/candidates.json` — the curated table, with the §5a
  columns (`curator`, `curated_on`, `rationale`, `reviewed_by`,
  `reviewed_on`). Twelve rows for Ohio: nine commercial across all seven
  denial codes (3901.381 for every code — the pay-or-deny clock is the only
  Ohio obligation most of them can state; 3901.389 interest for CO-45;
  3922.01 external review and 3901.20 for CO-50), three Medicare (IOM ch.1
  § 80.3.2 for CO-16, NCCI ch.I § D for CO-97, IOM ch.12 § 30.6.6 for CO-4).
  **Every row is a draft** (`curator: "Claude Opus 5 (draft)"`, `reviewed_by:
  null`). A test proves each would bind if reviewed; nothing else about them
  is checked — the rationale column is the apposite-ness judgement, and it
  needs a reviewer's name before it counts.
* `backend/verify/allowlist.py` — `build(state, payer_type, denial_code)`:
  reviewed rows only → resolve → fetch → bind(HEADING, APPLICABILITY) with
  the row's own characterisation and `may_assert`; failures are kept with
  their reason. `prompt_block()` is what the model is handed when the list
  is not empty — citation string, registry heading, what may be asserted,
  a 900-character excerpt.
* `utils/citation_gate.check_letter(text, allowed)` — inverted: a citation
  is a violation unless it resolves to an allowed provision **and** every
  number in the sentence that cites it FIGURE-binds to that provision's
  fetched text. `provider_appeals._gated_letter` builds the list per letter
  from the practice's state (parsed from its address) and the payer type
  (Medicare/Medicaid from the payer name, commercial otherwise). With an
  empty list the behaviour is the blocklist's, exactly.
* **Production today:** every allow-list is empty (all rows drafts), every
  letter cites nothing, the prompt's absolute rule applies. The first
  reviewed row is the first citation any letter may carry, and it carries
  it only with numbers the statute contains.

**Not built, by ruling:** nothing under `scripts/whatholdsup/` imports this
package (a test enforces it); `publish_topic.py` and the corpus rebuild are
Phase 3.
