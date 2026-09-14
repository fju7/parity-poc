-- Migration 078: a Signal topic is visible only when status = 'published'.
--
-- WHY THIS EXISTS
-- ---------------
-- signal_issues has carried a `status` column since migration 005, default
-- 'draft'. On 2026-09-14 every one of the 11 topics is 'draft', and nothing
-- reads the column: the SPA, /api/signal/topics, evidence-for-code,
-- denial-intelligence, the Q&A endpoint and the appeal-letter path all
-- served every topic to anyone. Meanwhile scripts/signal/verify_sources.py
-- had established that 92 of the corpus's 381 source identifiers resolve to
-- nothing or to a different paper.
--
-- This makes the flag load-bearing at the only layer every consumer shares:
-- the database. Row-level security on signal_issues admits a row to anon and
-- authenticated only when status = 'published'; every corpus table that
-- hangs off an issue admits a row only when its issue does. A topic is
-- published by flipping one column on one row, and unpublished the same way.
--
-- WHAT THIS DOES NOT COVER, AND HOW THAT IS CLOSED
-- ------------------------------------------------
-- service_role bypasses RLS by design, and the backend reads with the
-- service key. So the backend now reads the corpus through an anon-key
-- client (backend/signal_reader.py), which these policies DO govern, and a
-- static test (tests/signal/test_signal_reads_are_gated.py) fails the build
-- if a router reads a corpus table any other way. Pipeline scripts and the
-- /admin endpoints keep the service key: they need to see drafts.
--
-- THE FREEZE
-- ----------
-- The Signal corpus is frozen as evidence for the ai-research-reliability
-- work. This migration alters no row and no column of any signal_* table.
-- It replaces SELECT policies -- catalog metadata -- and enables RLS on one
-- table (signal_cpt_mappings) that never had it. Ruled not a breach of the
-- freeze by the operator on 2026-09-14; recorded in
-- docs/signal-corpus-freeze.md so the closure shows an access change dated
-- after the freeze that altered no content.
--
-- Idempotent.

-- ---------------------------------------------------------------------------
-- signal_issues: the root
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public read signal_issues" ON signal_issues;
DROP POLICY IF EXISTS "Published read signal_issues" ON signal_issues;
CREATE POLICY "Published read signal_issues"
  ON signal_issues FOR SELECT TO anon, authenticated
  USING (status = 'published');

-- ---------------------------------------------------------------------------
-- tables keyed by issue_id
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public read signal_sources" ON signal_sources;
DROP POLICY IF EXISTS "Published read signal_sources" ON signal_sources;
CREATE POLICY "Published read signal_sources"
  ON signal_sources FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.id = signal_sources.issue_id AND i.status = 'published'));

DROP POLICY IF EXISTS "Public read signal_claims" ON signal_claims;
DROP POLICY IF EXISTS "Published read signal_claims" ON signal_claims;
CREATE POLICY "Published read signal_claims"
  ON signal_claims FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.id = signal_claims.issue_id AND i.status = 'published'));

DROP POLICY IF EXISTS "Public read signal_consensus" ON signal_consensus;
DROP POLICY IF EXISTS "Published read signal_consensus" ON signal_consensus;
CREATE POLICY "Published read signal_consensus"
  ON signal_consensus FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.id = signal_consensus.issue_id AND i.status = 'published'));

DROP POLICY IF EXISTS "Public read signal_summaries" ON signal_summaries;
DROP POLICY IF EXISTS "Published read signal_summaries" ON signal_summaries;
CREATE POLICY "Published read signal_summaries"
  ON signal_summaries FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.id = signal_summaries.issue_id AND i.status = 'published'));

DROP POLICY IF EXISTS "Public read evidence updates" ON signal_evidence_updates;
DROP POLICY IF EXISTS "Published read signal_evidence_updates" ON signal_evidence_updates;
CREATE POLICY "Published read signal_evidence_updates"
  ON signal_evidence_updates FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.id = signal_evidence_updates.issue_id AND i.status = 'published'));

-- ---------------------------------------------------------------------------
-- tables keyed by claim_id (one hop further)
-- ---------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public read signal_claim_sources" ON signal_claim_sources;
DROP POLICY IF EXISTS "Published read signal_claim_sources" ON signal_claim_sources;
CREATE POLICY "Published read signal_claim_sources"
  ON signal_claim_sources FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_claims c JOIN signal_issues i ON i.id = c.issue_id
                 WHERE c.id = signal_claim_sources.claim_id AND i.status = 'published'));

DROP POLICY IF EXISTS "Public read signal_claim_scores" ON signal_claim_scores;
DROP POLICY IF EXISTS "Published read signal_claim_scores" ON signal_claim_scores;
CREATE POLICY "Published read signal_claim_scores"
  ON signal_claim_scores FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_claims c JOIN signal_issues i ON i.id = c.issue_id
                 WHERE c.id = signal_claim_scores.claim_id AND i.status = 'published'));

DROP POLICY IF EXISTS "Public read signal_claim_composites" ON signal_claim_composites;
DROP POLICY IF EXISTS "Published read signal_claim_composites" ON signal_claim_composites;
CREATE POLICY "Published read signal_claim_composites"
  ON signal_claim_composites FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_claims c JOIN signal_issues i ON i.id = c.issue_id
                 WHERE c.id = signal_claim_composites.claim_id AND i.status = 'published'));

-- ---------------------------------------------------------------------------
-- tables keyed by topic slug: the CPT bridge into the billing products
-- ---------------------------------------------------------------------------
-- signal_cpt_mappings (045) never had RLS: it was open to every role.
-- (From the anon key it reads as EMPTY today, not as permission denied, so
-- RLS was switched on later with no policy; the GRANT below is belt and
-- braces so the new policy has a privilege to filter.)
ALTER TABLE signal_cpt_mappings ENABLE ROW LEVEL SECURITY;
GRANT SELECT ON signal_cpt_mappings TO anon, authenticated;
DROP POLICY IF EXISTS "Published read signal_cpt_mappings" ON signal_cpt_mappings;
CREATE POLICY "Published read signal_cpt_mappings"
  ON signal_cpt_mappings FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.slug = signal_cpt_mappings.topic_slug AND i.status = 'published'));
DROP POLICY IF EXISTS "Service role full access on signal_cpt_mappings" ON signal_cpt_mappings;
CREATE POLICY "Service role full access on signal_cpt_mappings"
  ON signal_cpt_mappings FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "public_read" ON signal_denial_playbook;
DROP POLICY IF EXISTS "Published read signal_denial_playbook" ON signal_denial_playbook;
CREATE POLICY "Published read signal_denial_playbook"
  ON signal_denial_playbook FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.slug = signal_denial_playbook.signal_topic_slug AND i.status = 'published'));

-- ---------------------------------------------------------------------------
-- the view the landing page counts from
-- ---------------------------------------------------------------------------
-- A view runs with its owner's privileges unless told otherwise, which would
-- let anon count draft topics through it while the tables underneath say no.
ALTER VIEW signal_topic_counts SET (security_invoker = on);

-- ---------------------------------------------------------------------------
-- the freeze: nothing above touches a row or a column
-- ---------------------------------------------------------------------------
COMMENT ON COLUMN signal_issues.status IS
  'draft | published. Since migration 078 (2026-09-14) this is the ONLY thing '
  'that makes a topic and everything under it visible to anon/authenticated. '
  'Flip one row to publish; flip it back to withdraw.';
