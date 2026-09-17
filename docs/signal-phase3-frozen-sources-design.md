# Phase 3 — frozen sources and the scheduled re-check

**Status: APPROVED 2026-09-14 with amendments (IDENTITY_ONLY published with marker and counted as a quality metric; binding_lost wording; retracted visually distinct; cadence accepted; end-to-end topic = mmr-vaccine-autism). Being built.** Ruling: a published topic
freezes a reproducible record of what every claim rested on; a scheduled
re-check compares *bindings*, not bytes; retraction and amendment are a fifth
check with their own verdict; divergence surfaces to readers on the page,
not only to the operator. The letter half of Phase 3 was blocked on the
attorney review of the 12 candidate rows
(`docs/appeal-citation-candidates-review-2026-09.md`) — **closed 2026-09-17 by Fred's
ruling (letters are evidence-and-argument only; no citations); the letter half is re-scoped,
not blocked. See `docs/legal-review/README.md`.**

Builds on `docs/verification-gates-phase1-design.md` (the gates) and
migration 078 (`status = 'published'` is the only thing that shows a topic).

## 1. `publish_topic.py <slug>` — the frozen record

Publishing a topic is one deliberate act that does four things in order and
refuses at the first that fails:

1. **Gate every source.** For each `signal_sources` row of the topic:
   `identify(url)` (provenance `RESOLVED_FROM_HELD` when parsed from the
   stored URL; a source whose URL yields no identifier is `UNVERIFIABLE`) →
   `resolve` → `fetch` → `bind(HEADING)` with the stored title. A source
   **survives** only if it resolves `EXISTS`, fetches bytes (full text,
   abstract or registry record — the kind is recorded), and HEADING is ok
   or abstains with a mandatory kind available downstream.
2. **Gate every claim.** For each `signal_claims` row and each surviving
   source linked to it in `signal_claim_sources`: `bind(FIGURE)` of the
   claim text against the fetched document, `bind(SPAN)` when
   `source_context` carries a quotation. The claim's **support level** is
   the best any linked surviving source gives it:
   | level | meaning | published? |
   |---|---|---|
   | `FIGURE_BOUND` | the claim carries figures and every one is in a surviving source's text | yes |
   | `SPAN_BOUND` | a quoted passage is in a surviving source verbatim | yes |
   | `IDENTITY_ONLY` | no figure and no quotation; the source is the named document, the wording is unchecked (R1) | yes, **marked** — see §4 — and **counted on the topic line** beside the flagged count. Recorded as a **quality metric expected to trend down**, not a permanent category: a claim with no figure and no quotable span is usually a claim that needs rewriting, not a source that cannot be checked. |
   | `UNSUPPORTED` | every linked source failed a gate, or a figure is in none of them | **no** — withheld at publication, listed in the record |
   Withholding at publication is not "silently dropping": the record lists
   every withheld claim with the binding that failed, and the page states
   how many were withheld (§4).
3. **Write the record**, then the documents it rests on:
   * `backend/data/verify/published/<slug>/<publish_id>.json` and
     `latest.json` (`publish_id` = UTC timestamp + short git sha):
     ```
     topic          slug, title, issue_id
     published_at   ISO UTC
     published_by   operator login + machine, the git sha of the tree, and the command line
     gate_version   verify package __version__ + `git log -1 --format=%h -- backend/verify`
     sources[]      source_id, url, title, identifier{system,value,provenance},
                    resolution{exists, heading, canonical, registry, checked_at},
                    document{sha256, route, kind, retrieved_at, chars, text_layer} | null,
                    bindings[] {kind, ok, abstained, evidence, reason},
                    survives: bool, withheld_reason
     claims[]       claim_id, claim_text, category, figures[], quotation,
                    per_source[] {source_id, bindings[] {kind, ok, abstained, evidence, reason}},
                    support: FIGURE_BOUND | SPAN_BOUND | IDENTITY_ONLY | UNSUPPORTED,
                    supported_by[] source_ids
     summary        sources total / survived / by verdict; claims total / by level
     ```
     "Every binding result per claim, not just ok/not-ok": `per_source[]`
     holds each kind that ran, what it returned, its evidence and reason.
   * `backend/data/verify/docs/<sha256[:2]>/<sha256>.txt.gz` — the fetched
     text, content-addressed, one copy per distinct bytes. This is what
     makes the record evidence rather than a date: "what did claim N rest
     on, on the day" is answerable from the record and the bytes it names,
     offline, forever. Committed to the repository (a topic is ~1–2 MB
     gzipped).
   * a row in `topic_publications` (§6) so the site can read the same
     record.
4. **Flip `signal_issues.status` to `'published'`** with the service key —
   the one column on one row that 078 made load-bearing — and record the
   flip in `docs/signal-corpus-freeze.md` (one status value on one row of a
   frozen table; the corpus content is untouched, and everything the reader
   sees comes from the record's `supported_by` / `survives` filters, not from
   the corpus rows alone).

`publish_topic.py` is the **only** path to `status = 'published'`; the
freeze register lists every flip. It exits non-zero and flips nothing if any
step above fails, if the gate version cannot be determined, or if the
working tree is dirty under `backend/verify/` (the record must name a
committed gate).

## 2. `recheck_topic.py <slug>` — bindings, not bytes

For every published topic, against `latest.json`: re-resolve, re-fetch and
re-run **exactly the bindings the record holds** — same source, same claim,
same kind, same assertion text. Then classify, per source and per claim:

| outcome | definition | reader marker | operator alert |
|---|---|---|---|
| `rerendered` | bytes differ (new sha256) but every recorded binding still returns what it returned | none | none — logged only |
| `binding_lost` | a binding that was `ok` at publication is not `ok` now (or an abstaining HEADING's mandatory kind now fails) | **yes** (§4) | yes |
| `status_changed` | the fifth check (§3) reports retraction, correction, withdrawal, trial-status change or amendment | **yes** (§4) | yes |
| `unreachable` | resolve returned `UNCHECKED`, or fetch got nothing (timeout, 4xx/5xx, paywall wall, PDF with no text layer) | **yes, worded as access** (§4) — after two consecutive misses (≥ 2 weeks apart), never on the first | yes, on the first, as ops |
| `unchanged` | same bytes, same bindings | none | none |

Rules that keep the check un-mutable:
* A changed hash alone is never an outcome. eCFR regenerates XML; publishers
  re-render PDFs; Europe PMC re-encodes. The recorded binding results are the
  comparison; bytes are only stored so a person can diff them later.
* `unreachable` is an access fact, not a truth fact. It never demotes a
  claim's support level; it produces its own marker in its own words.
* `binding_lost` demotes the claim's support level in the **re-check
  record**, not in the publication record, which is immutable. The page
  shows the publication level and the re-check outcome side by side.
* A re-check never un-publishes and never edits a claim. Un-publishing is a
  person flipping the column back, recorded in the freeze register.
* Outputs: `backend/data/verify/rechecks/<slug>/<run_id>.json` (full), a
  row in `topic_rechecks` (§6) with the flagged items the page renders, and
  a non-zero exit on any `binding_lost` or `status_changed` so the scheduled
  job fails where the operator is already told.

## 3. The fifth check — status: retraction, correction, amendment

The four binding kinds read the document. A retracted paper's text is
unchanged; all four pass. So status is **its own check, its own script
(`status_check.py`), its own verdict, its own row in the record** — if it is
not separate it does not exist.

| system | query | verdicts |
|---|---|---|
| doi | CrossRef `works/{doi}`: `update-to[]` (type `retraction`, `correction`, `erratum`, `expression_of_concern`, `withdrawal`; Crossref carries Retraction Watch data here since 2023) and `relation.is-retracted-by` / `has-erratum`; `content-version`; `deposited` | `retracted`, `corrected`, `withdrawn`, `concern`, `unchanged`, `unknown` |
| pmid / pmcid | Europe PMC `search … resultType=core`: `commentCorrectionList` (`Retraction in`, `Erratum in`, `Expression of concern in`, `Retracted and republished`), `pubTypeList` (`Retracted Publication`, `Retraction of Publication`, `Published Erratum`) | same |
| nct | ClinicalTrials.gov v2 `statusModule`: `overallStatus` vs frozen (WITHDRAWN, TERMINATED, SUSPENDED), `whyStopped`, `lastUpdatePostDate` > frozen, `resultsFirstPostDate` newly present | `trial_status_changed`, `record_updated`, `unchanged` |
| cfr | eCFR `api/versioner/v1/versions/title-{T}.json?section={S}`: any version `date` > the frozen `as_of` | `amended`, `unchanged` |
| orc / oac | the section page's `Effective:` / `Latest Legislation` fields vs frozen | `amended`, `unchanged` |
| cms_iom | the section's `(Rev. NNNN, Issued: …)` transmittal line vs frozen | `reissued`, `unchanged` |
| ncci | manual year vs frozen | `reissued`, `unchanged` |

`unknown` (the query failed) is recorded as `unknown`, never as `unchanged`
— the errata.py lesson: an absence reported by something not in a position
to observe it is the recurring error.

**Cadence, and why:**
* **Status check: weekly** (Mondays 12:00 UTC, before the Signal checks at
  12:30). One metadata call per source, no fetch, no PDF: ~35 calls and
  under a minute per topic. Retraction is the rarest and highest-impact
  event; registries propagate a retraction within days; weekly bounds a
  reader's exposure to seven days at negligible cost. Could be daily at the
  same cost — weekly is proposed because the propagation lag makes daily
  mostly redundant, and because a weekly cadence matches the existing
  golden-set and source-verification jobs so one failure surface is read at
  one time.
* **Binding re-check: monthly** (first week, after the eCFR's
  first-of-month point-in-time text exists). Re-fetches every document,
  including manual PDFs — minutes per topic and the only check that can see
  link rot, a re-rendered PDF that lost its text layer, or a silently
  revised page. Law text changes are rare and dated (the status check sees
  the date first); literature full text does not change without a
  correction (the status check sees that first). Monthly is therefore a
  floor under the weekly check, not the front line — and a re-fetch every
  week of every PDF is how a check becomes noise and gets muted.
* Both on demand via `workflow_dispatch`; both in
  `.github/workflows/verify-gates.yml` alongside the live-registry diff,
  for the reason that file gives.

## 4. Divergence surfaces to readers — draft wording

Placement: on the claim card (`ClaimCard.jsx`), beneath the claim text, and
on the source entry in the Sources panel; plus one line at the top of the
topic page. Nothing is removed; nothing is re-scored. Dates are the
re-check's, in the reader's locale; "we" is Parity Signal.

**Topic line (always, once published)** — two facts stated separately, so the header never contradicts a marker beneath it ("0 of 29 sources flagged" above a RETRACTED block read as a contradiction):
> Sources checked and frozen on 14 Sep 2026 · 1 source retracted before publication · 0 sources newly flagged since 14 Sep 2026 (last re-check 6 Oct 2026) · 41 of 97 claims source-confirmed only (wording not machine-checked) — see markers below. *What this means →*

**Support marker — `IDENTITY_ONLY` (at publication):**
> Source confirmed; wording not machine-checked. We verified that the cited document is the one named and fetched its text. This claim carries no figure or quotation we could match against it, so its wording rests on the extraction, not on a check.

**`binding_lost`** (we observed only that our matcher no longer finds the figure; we do not know why):
> Re-checked 6 Oct 2026: we could no longer match the figure this claim was published on (HR 0.80; 95% CI 0.72–0.90) in the cited source. The claim is shown as it was published. That may mean the source changed, or that our reading of it did — either way, treat the figure as unconfirmed until we have re-read the source ourselves.

**Retracted — two meanings, two markers (ruling of 2026-09-14; drafts, awaiting approval).** A retracted work can be the *subject* of a claim ("the Wakefield case series enrolled 12 children") or the claimed *support* for one. They cannot render identically: the subject case is information, the support case is doubt. Which applies is decided deterministically per claim-source link: the claim names the source (its first author's surname or a distinctive title word appears in the claim text) → subject; otherwise → support.

*Subject — a grey information note, the same weight as the IDENTITY_ONLY note:*
> **About a retracted paper.** The study this claim describes — Wakefield et al., *The Lancet*, 1998 — was retracted by the journal on 6 Feb 2010 (Crossref). The claim reports what that paper did or said; its retraction is part of the record, not a doubt about this claim.

*Support — the red-bordered warning block, distinct from every amber note:*
> **Retracted source.** This claim rests on a paper the journal retracted on 6 Feb 2010 (Crossref). The claim is shown as published and marked; it should not be relied on until we have reviewed the retraction.

On the mmr record after CHRONOLOGY, no surviving claim rests on Wakefield as support — the one surviving Wakefield-linked claim is the subject case. Rendered side by side: `docs/mmr-vaccine-autism-markers-side-by-side-2026-09-14.png`.

**`status_changed` — retracted, observed by a re-check after publication** (the support wording above, with the observation date; visually the red block):
> Retracted. Crossref records a retraction of this source dated 30 Sep 2026. This claim rested on it when published on 14 Sep 2026. We have not removed the claim; we have marked it, and it should not be relied on until we have reviewed the retraction.

**`status_changed` — corrected (erratum), bindings still hold:**
> Corrected. The publisher issued a correction to this source on 30 Sep 2026. The figure this claim cites is still present in the corrected text; we have not yet reviewed what the correction changed.

**`status_changed` — corrected, and a binding was lost:** the `binding_lost` wording, with "the publisher issued a correction on 30 Sep 2026" as the first sentence.

**`status_changed` — trial status:**
> Trial status changed. ClinicalTrials.gov now lists NCT01234567 as Terminated (reason given: "sponsor decision"), updated 30 Sep 2026; it was Active, not recruiting when this page was published on 14 Sep 2026.

**`status_changed` — law amended (provision cited in a letter or on a page):**
> Amended. Ohio Revised Code § 3901.381 was amended effective 1 Oct 2026, after we checked it on 14 Sep 2026. The text we matched may no longer be current.

**`unreachable` (after two consecutive misses):**
> Could not re-check. We were unable to retrieve this source on 6 Oct 2026 or 13 Oct 2026 (the publisher's page returned an error). This says nothing about the claim — it says we could not confirm it again. Last confirmed 14 Sep 2026.

**Never shown:** `rerendered`, `unchanged`, and any hash.

## 5. The end-to-end run — one topic

Cheapest to redo, by sources × claims from the 2026-09-14 snapshot:

| slug | sources | resolve to nothing / wrong doc | claims |
|---|---|---|---|
| **health-impacts-of-climate-change** | 30 | 5 / 0 | 119 |
| mmr-vaccine-autism | 35 | 2 / 2 | 128 |
| mrna-vaccine-myocarditis | 32 | 1 / 4 | 130 |

**Ruled: mmr-vaccine-autism**, not climate — climate would publish almost
nothing, which proves the gate refuses and nothing about whether it admits.
mmr's source set holds Wakefield 1998 (Lancet, retracted 2010) — twice, under
two source types — and the 2010 retraction notice itself as a third source:
a real retraction for `status_check.py` to exercise on its first run. The run
reports: sources in / survived / by verdict; claims in / by support level;
what the status check says about Wakefield specifically; what the page would
show; and the record and documents it froze. **The run does not flip
`status`**; the operator decides that after reading what survives.

## 6. Storage — outside the freeze

Two tables, not `signal_*`, no foreign keys to frozen tables (migration
080, applied by the operator after the `select count(*) from signal_issues`
project check):

```
topic_publications  slug, publish_id, published_at, published_by, gate_version,
                    record jsonb (the full §1 record), supported_claim_ids uuid[],
                    surviving_source_ids uuid[]            -- public read; service writes
topic_rechecks      slug, run_id, run_at, kind ('status' | 'bindings'),
                    outcomes jsonb, flags jsonb (per claim_id / source_id: outcome,
                    wording key, dates), exit_ok bool       -- public read; service writes
```
The SPA and every backend consumer read the topic through the reader and
then filter claims and sources by the latest publication's arrays and
overlay the latest re-check's flags. `status = 'published'` opens the door;
the record says what stands inside it.

## 6a. The publishability gate — verification is necessary and not sufficient

> **A topic is publishable when what verified still says what the topic means.**

The gates decide what *can* be shown. They do not decide whether what
remains is still the topic — a filter can keep 59 of 128 claims and drop the
two strongest studies on the way, and every surviving claim will be true to
its source while the page no longer says what the topic means. So before
any flip:

1. `publish_topic.py` writes the record (as now, no flip).
2. A **survival read** is produced from the record: the surviving claims
   grouped by what they assert; the withheld claims each with why; the
   named studies lost and what tier of evidence they were; and the answer
   to the one question — does the surviving set still carry the central
   finding with its strongest evidence? (First instance:
   `docs/mmr-vaccine-autism-survival-read-2026-09-14.md`.)
3. **One person reads it** and rules. The ruling and the reader's name are
   recorded in the freeze register beside the flip. No flip without both.

This is a Phase 3 gate for every topic, not a one-off for mmr. It is the
generalisation of the ruling of 2026-09-14: "59 of 128 claims survived —
that is not a verified version of the topic, it is a different analysis that
a filter selected and no person reviewed. The gates are not in question; the
coherence of what remains is."

## 6b. The generic-URL adapter and per-registry rate limits (built 2026-09-14)

* `verify/generic.py`: a document with no registry identifier is fetched
  and HEADING-bound against its `<title>` / `<h1>` / `og:title` (a PDF's
  first lines), same abstention rule, same four kinds downstream.
  `registry = "generic_fetch"` on the Resolution and on the record's
  `resolution.generic_fetch = true`, so a reader and the record can tell a
  generic fetch from a registry resolution; the status check returns
  `no_registry` for it — nothing can report a bare URL retracted, and the
  monthly binding re-check is its only watch. On mmr it recovered six of
  the ten institutional sources; two stored URLs are 404 (the Omnibus
  decision, the FDA BLA page), one is a JavaScript shell (UnitedHealthcare),
  one timed out (Anthem).
* `verify/http.py`: per-host requests-per-second limits (Europe PMC 3, Crossref
  and doi.org 5, ClinicalTrials.gov 0.8, eCFR and codes.ohio.gov 2, cms.gov
  1, anything else 2), enforced before every call including retries, and
  **recorded on every publication and re-check record** as `rate_limits_rps`
  — so a divergence report can be read against the call rate that produced it.

## 7. What is deliberately not automatic

Publishing, un-publishing, and acting on a flag are all a person's. The
scripts produce records and markers; they never change what a reader sees
except by adding a marker. A retraction marks the claim; it does not remove
it — that is what "changes are deliberate" means, and it is why every marker
carries both dates.

## 8. Built 2026-09-14 — status

| piece | where | state |
|---|---|---|
| status check (§3) | `verify/status.py` | built; Wakefield 1998 → `retracted` (Crossref reverse `filter=updates`, Europe PMC); the 2010 notice → `retraction_notice`; Cochrane pub4 → `superseded` |
| publish record (§1) | `verify/publish.py`, `scripts/publish_topic.py` | built; refuses a dirty gate tree; `--flip` required to touch status |
| mmr-vaccine-autism run (§5) | `data/verify/published/mmr-vaccine-autism/` | frozen at gate `782ad56`: 17/35 sources survive; 35 FIGURE_BOUND / 24 IDENTITY_ONLY (18.8%) / 69 UNSUPPORTED; **not flipped** |
| re-check (§2) | `verify/recheck.py`, `scripts/recheck_topic.py` | built; first status run 17 unchanged; first bindings run 17 unchanged / 59 claims unchanged / 0 flags after adding retry-with-backoff (a throttled Europe PMC had read as 15 unreachable — an access fact, and one 429 is not link rot) |
| storage (§6) | `migrations/080_topic_publications.sql` | file; awaiting the operator (repo-rooted session, `apply_migration`) |
| page (§4) | `frontend/src/components/signal/RecordMarkers.jsx`; `SignalApp` filters claims and sources by the record; `IssueDashboard`, `ClaimCard` | built; no record ⇒ *Not yet published*; `retracted` is a red-bordered block, the rest amber, `unreachable` grey |
| consumers | `signal_intelligence`, `signal_qa`, `signal_profiles`, `signal_metrics` | filter claims (and Q&A sources) by the record via `signal_reader.published_claim_ids` / `latest_publication`; no record ⇒ no claims |
| jobs | `.github/workflows/verify-gates.yml` | weekly `recheck-status` (Mon 12:00 UTC), monthly `recheck-bindings` (first Mon 13:00 UTC), both on dispatch |
| not built | a generic-URL adapter (agency, court and payer documents are `UNVERIFIABLE` today); `topic_rechecks` writes need 080 |
