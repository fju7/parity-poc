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

Not on this register because they touch no `signal_*` table: the noindex of
signal.civicscale.ai (`d75c178`), the removal of the appeal letter's Signal
section (`13ca102`), and the backend's move to an anon-key reader
(`backend/signal_reader.py`).

## How to check the freeze held

Row and column counts of every `signal_*` table, compared with the day of the
freeze, should differ only by the three rows in 079. Policies will differ (078).
