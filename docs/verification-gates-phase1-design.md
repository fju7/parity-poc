# Phase 1 — resolve / fetch / bind, for both registries

**Status: APPROVED 2026-09-14 with four amendments (§§ 4a, 5a, 5b, 8), now being built — literature adapter first, law second.** Phase 0 (`f0bb63e`) removed every
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

A binding is `ok` only if every kind that applies is `ok`. HEADING applies
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
