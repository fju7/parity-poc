# Phase 3 — frozen sources and the scheduled re-check

**Status: APPROVED 2026-09-14 with amendments (IDENTITY_ONLY published with marker and counted as a quality metric; binding_lost wording; retracted visually distinct; cadence accepted; end-to-end topic = mmr-vaccine-autism). Being built.** Ruling: a published topic
freezes a reproducible record of what every claim rested on; a scheduled
re-check compares *bindings*, not bytes; retraction and amendment are a fifth
check with their own verdict; divergence surfaces to readers on the page,
not only to the operator. The letter half of Phase 3 is blocked on the
attorney review of the 12 candidate rows
(`docs/appeal-citation-candidates-review-2026-09.md`).

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

**Topic line (always, once published):**
> Sources checked and frozen on 14 Sep 2026 · re-checked 6 Oct 2026 · 2 of 27 sources flagged · 41 of 96 claims source-confirmed only (wording not machine-checked) — see markers below. *What this means →*

**Support marker — `IDENTITY_ONLY` (at publication):**
> Source confirmed; wording not machine-checked. We verified that the cited document is the one named and fetched its text. This claim carries no figure or quotation we could match against it, so its wording rests on the extraction, not on a check.

**`binding_lost`** (we observed only that our matcher no longer finds the figure; we do not know why):
> Re-checked 6 Oct 2026: we could no longer match the figure this claim was published on (HR 0.80; 95% CI 0.72–0.90) in the cited source. The claim is shown as it was published. That may mean the source changed, or that our reading of it did — either way, treat the figure as unconfirmed until we have re-read the source ourselves.

**`status_changed` — retracted** (visually distinct from every other marker: a solid red-bordered block with a "RETRACTED" caption, not the amber note the others use — "we could not confirm this" and "the source was withdrawn" are different in kind):
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

## 7. What is deliberately not automatic

Publishing, un-publishing, and acting on a flag are all a person's. The
scripts produce records and markers; they never change what a reader sees
except by adding a marker. A retraction marks the claim; it does not remove
it — that is what "changes are deliberate" means, and it is why every marker
carries both dates.
