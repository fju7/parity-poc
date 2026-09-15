# The Signal corpus freeze

**Frozen 2026-09-14.** The `signal_*` tables in the Parity Supabase project
(`kfxxpscdwoemtzylhhhb`) are evidence for the ai-research-reliability work and
are not modified or rebuilt. This note is the register of every change dated
after the freeze that touched them, so that the dependency closure can show
what altered access and what altered content.

## What the freeze holds

`scripts/signal/verify_sources.py`, full run 2026-09-14
(snapshot: `backend/scripts/signal/output/verify_sources_2026-09-14.json`):

| verdict | sources |
|---|---|
| NEVER_FETCHED — `content_text` is a model summary, never the document | 288 |
| FABRICATED_IDENTIFIER — DOI/NCT/PMID resolves to nothing | 59 |
| WRONG_DOCUMENT — identifier resolves to a paper sharing no distinctive title word with ours | 33 |
| NO_CONTENT | 1 |
| **total** | **381** |

Every one of the 11 `signal_issues` rows has `status = 'draft'`.

## Post-freeze changes, in order

| date | change | rows | columns | access | where |
|---|---|---|---|---|---|
| 2026-09-14 (applied ~20:50 UTC by the operator in the Parity SQL editor; confirmed by `pg_policies` and by anon reading 0 rows from every corpus table while the service role reads all) | Migration 078: SELECT policies on `signal_issues`, `signal_sources`, `signal_claims`, `signal_claim_sources`, `signal_claim_scores`, `signal_claim_composites`, `signal_consensus`, `signal_summaries`, `signal_evidence_updates`, `signal_denial_playbook` replaced with `status = 'published'` gates; RLS enabled on `signal_cpt_mappings` with the same gate; `signal_topic_counts` view set `security_invoker`; a COMMENT on `signal_issues.status`. Ruled not a breach by the operator: catalog metadata only. | 0 | 0 | **yes** — anon/authenticated see nothing until a topic is published | `backend/migrations/078_signal_published_gate.sql` |
| 2026-09-14 | Migration 079: three rows deleted from `signal_cpt_mappings` (0537T, 0538T, 81479 → crispr-gene-therapy). Product configuration seeded by migration 046, not evidence. Operator-directed. | **3 deleted** | 0 | no | `backend/migrations/079_cpt_mappings_misapplied.sql` |

| 2026-09-14 | Migration 081: two identifiers in `signal_sources` corrected on four rows, fixing forward — Jain 2015 `10.1001/jama.2015.1534` (nonexistent) → `10.1001/jama.2015.3077`; Honda 2005 `10.1111/j.1469-8749.2005.tb01095.x` and `…tb01215.x` (a gastrostomy paper and a botulinum paper) → `10.1111/j.1469-7610.2005.01425.x`. Found by exact-title lookup, read back. Curator: Claude Opus 5 on the operator's direction. The snapshot and the mmr record at gate 2b84a4a keep the wrong values. | **4 updated** (url column) | 0 | no | `backend/migrations/081_signal_sources_two_identifiers.sql` |

| 2026-09-14 | Migration 082: seven `signal_claims.claim_text` values corrected, fixing forward — "650,000" → "657,461" (Hviid) ×4, "530,000" → "537,303" (Madsen) ×2, "1.2 million" → "1,256,407" (Taylor 2014). Truncations of the source's figure; FIGURE was not loosened. Old text preserved in `082_signal_claims_seven_truncations.json`. Curator: Claude Opus 5 on the operator's direction. | **7 updated** (claim_text) | 0 | no | `backend/migrations/082_signal_claims_seven_truncations.sql` |
| 2026-09-15 | Migration 083: the two Cochrane rows in `signal_sources` re-cited from `CD004407.pub4` (2020, superseded) to `CD004407.pub5` (22 Nov 2021, the current version), the DOI taken from Crossref's update-to on the source itself. Nine claims re-bind against pub5. Curator: Claude Opus 5 on the operator's direction. | **2 updated** (url) | 0 | no | `backend/migrations/083_signal_sources_cochrane_pub5.sql` |
| 2026-09-15 | Migration 088: five `signal_claims.plain_summary` values set to NULL on mmr-vaccine-autism (8b84dcfd, 6bbf8769, 43dc8f6d, 58b05989, 77ad8922) — the model-written summaries that the prose gate (`scripts/signal/prose_gate.py`, wired 2026-09-15) refuses because they add a figure the claim and its sources do not carry ("before 37 weeks", "over half a million US dollars", "1.0 would mean identical risk", …). Two of the five rendered; three sat on withheld claims. Refusal path, no rewrite: the claim renders without a summary. Rendered page probed headlessly after: both claims present, old summaries absent, a kept summary (Jain, "nearly 96,000") still renders. Curator: Claude Opus 5 on the operator's direction. | **5 updated** (plain_summary → NULL) | 0 | no | `backend/migrations/088_mmr_plain_summaries_refused.sql` |
| 2026-09-15 | Migration 089: one more `plain_summary` set to NULL (5b3bff25) — "six years before" was a model-computed interval (2010 − 2004); the 2010 is in the claim's own model-written source text and in Crossref's event data for the retraction, neither of which the summariser was handed. The gate had exempted it as a counting word; `verify/policy.py` now refuses a word-form figure followed by a unit (`_has_unit`). 112 of 128 mmr claims keep a summary. Curator: Claude Opus 5 on the operator's direction. | **1 updated** (plain_summary → NULL) | 0 | no | `backend/migrations/089_mmr_plain_summary_six_years.sql` |
| 2026-09-15 | Re-run of the frozen mmr record through the current binder, into scratch (not the corpus): FIGURE_BOUND 56 / IDENTITY_ONLY 40 / UNSUPPORTED 32, 0 verdict changes, 0 per-source level changes, 0 bound → unbound. The operator read stands unchanged. | 0 | 0 | no | scratch only |
| *pending* | **Human read of mmr-vaccine-autism** (design §6a) against `docs/mmr-vaccine-autism-operator-read-2026-09-14.md`. Reader: ________ · Date: ________ · Ruling: ________ | — | — | — | the flip, if any, is recorded on the row below this one |

## The named-events table (CHRONOLOGY) — every row, so a wrong date is traceable

`backend/data/verify/events.json`, load-bearing on whether a claim publishes since 2026-09-14. Dates a registry can answer are not here (the Lancet 2010 retraction and the 2004 partial retraction of Wakefield 1998 resolve from Crossref/Europe PMC on the source itself).

| label | date | primary URL | reviewed_by |
|---|---|---|---|
| GMC fitness-to-practise determination (findings of fact) | 2010-01-28 | *not verified* — reviewer to supply | null |
| Wakefield erased from the UK medical register (GMC sanction) | 2010-05-24 | *not verified* — reviewer to supply | null |
| Brian Deer's BMJ series | 2011-01-05 | https://doi.org/10.1136/bmj.c5347 (resolves at Crossref; page 403s) | null |
| Omnibus Autism Proceeding test-case decisions | 2009-02-12 | *not verified* — corpus URL and two court paths 404 | null |

Not on this register because they touch no `signal_*` table: the noindex of
signal.civicscale.ai (`d75c178`), the removal of the appeal letter's Signal
section (`13ca102`), and the backend's move to an anon-key reader
(`backend/signal_reader.py`).

## How to check the freeze held

Row and column counts of every `signal_*` table, compared with the day of the
freeze, should differ only by the three rows in 079. Policies will differ (078).
Six `plain_summary` values are NULL that were not (088, 089); no other column of
`signal_claims` changed after 082.
