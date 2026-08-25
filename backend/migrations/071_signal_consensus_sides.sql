-- Migration: record WHICH claims sit on each side of a debated category.
--
-- WHY
-- ---
-- signal_consensus already stores arguments_for and arguments_against as prose,
-- and supporting_claim_ids as "the 3-8 most informative claims for this
-- assessment" — deliberately a mixed set, per the generator prompt in
-- backend/scripts/signal/map_consensus.py. Nothing records which side any claim
-- is on, so the UI can assert that a debate exists but cannot show the evidence
-- each side actually rests on.
--
-- These two columns close that gap. The model already receives every claim in
-- the category and already writes both arguments; it is simply never asked to
-- cite ids per side.
--
-- Additive and inert: both columns are nullable with no default, so existing
-- rows are untouched and the frontend falls back to the current prose-only
-- rendering wherever they are null. They populate only when map_consensus.py
-- is re-run for a topic.
--
-- Idempotent. Run via the Supabase SQL editor or CLI.

ALTER TABLE signal_consensus
  ADD COLUMN IF NOT EXISTS for_claim_ids JSONB,
  ADD COLUMN IF NOT EXISTS against_claim_ids JSONB;

COMMENT ON COLUMN signal_consensus.for_claim_ids IS
  'Claim ids cited by arguments_for, as a JSON array of uuid strings. NULL when '
  'the category is not debated or predates migration 071.';

COMMENT ON COLUMN signal_consensus.against_claim_ids IS
  'Claim ids cited by arguments_against, as a JSON array of uuid strings. NULL '
  'when the category is not debated or predates migration 071.';

-- signal_consensus is already public-read (migration 006) and RLS is already
-- enabled on it; adding columns inherits both. No grant changes needed.
