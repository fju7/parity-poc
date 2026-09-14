# Phase 1 — resolve / fetch / bind, for both registries

**Status: DESIGN. Nothing here is built.** Phase 0 (`f0bb63e`) removed every
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

Closure: a shared `resolve`/`bind(HEADING)` module that WHU consumed would
enter WHU's dependency closure, on which the ai-research-reliability baseline
is scoped. What the closure would gain: nothing WHU does not already call
(Handle, CrossRef, Europe PMC, ClinicalTrials.gov) — only a package boundary,
and a blocking verdict where today there is a warning. Whether WHU consumes it
or keeps its own copy is a separate ruling; Phase 1 does not require it.

## 9. Acceptance — how to know it works, before it is trusted

Golden sets, both already in hand:

* law: the 19 provisions from the 2026-09-14 inventory with their known
  verdicts (12 wrong, 7 right) — every wrong one must fail `bind`, every right
  one pass, and ORC 3901.38 must fail on FIGURE after passing HEADING.
* literature: the 381-source `verify_sources_2026-09-14.json` snapshot — the
  59 FABRICATED_IDENTIFIER and 33 WRONG_DOCUMENT verdicts must reproduce
  exactly under the new `resolve`/`bind(HEADING)`.

A gate that cannot reproduce the errors already found is not measuring them.

## 10. Build order (Phase 2 onward; nothing in Phase 1)

1. `resolve` + `bind(HEADING)` for the literature systems, wrapping
   `verify_sources.py` — golden set 381 must reproduce.
2. `resolve` + `fetch` + `bind(HEADING, FIGURE, APPLICABILITY)` for `cfr`,
   `orc`, `oac`, `cms_iom`, `ncci` — golden set 19 must reproduce.
3. Invert `citation_gate` to allow-list mode with an empty list; behaviour
   unchanged; then the curated candidate table for Ohio × 7 denial codes.
4. `publish_topic.py` and the corpus rebuild, one topic, with the gate.
