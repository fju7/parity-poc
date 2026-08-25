-- Migration: authoritative per-topic counts for Parity Signal
--
-- WHY THIS EXISTS
-- ---------------
-- /api/signal/topics and /api/signal/admin/review-topics used to count claims
-- and sources by selecting every matching row and counting them in Python:
--
--     sb.table("signal_claims").select("id, issue_id").in_("issue_id", ids)
--
-- PostgREST caps the number of rows it will return (Supabase default: 1000).
-- Once the corpus passed 1000 claims the query silently returned a truncated
-- page, so every topic after the cut-off was under-counted. The landing page
-- claim counts summed to exactly 1000 while the topic pages, which load their
-- claims per-issue, showed the true totals.
--
-- This view does the counting in Postgres, where no row cap applies. It also
-- exposes scored_count (claims that actually have a composite score), which
-- previously could not be derived per-topic because signal_claim_composites is
-- keyed on claim_id and carries no issue_id.
--
-- Run via the Supabase SQL editor or CLI. Idempotent.

CREATE OR REPLACE VIEW signal_topic_counts AS
SELECT
  i.id AS issue_id,
  (
    SELECT COUNT(*)
    FROM signal_claims c
    WHERE c.issue_id = i.id
  ) AS claim_count,
  (
    SELECT COUNT(*)
    FROM signal_claims c
    JOIN signal_claim_composites comp ON comp.claim_id = c.id
    WHERE c.issue_id = i.id
  ) AS scored_count,
  (
    SELECT COUNT(*)
    FROM signal_sources s
    WHERE s.issue_id = i.id
  ) AS source_count
FROM signal_issues i;

COMMENT ON VIEW signal_topic_counts IS
  'Per-topic claim, scored-claim, and source totals. Counted in Postgres so the '
  'PostgREST row cap cannot truncate them. Read by /api/signal/topics, '
  '/api/signal/metrics, and /api/signal/admin/review-topics.';

-- The signal_* tables are already public-read (migration 006). Match that here
-- so the view is reachable by the anon key as well as the service key.
GRANT SELECT ON signal_topic_counts TO anon, authenticated, service_role;
