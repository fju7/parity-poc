-- Migration: Enable anonymous public read access on all signal_ tables
-- These tables contain publicly curated evidence data, no PHI
-- Run via Supabase SQL Editor or CLI

-- Enable RLS on all signal tables (idempotent)
ALTER TABLE signal_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_claim_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_claim_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_claim_composites ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_consensus ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_summaries ENABLE ROW LEVEL SECURITY;

-- Public SELECT policies (anon + authenticated)
CREATE POLICY "Public read signal_issues"
  ON signal_issues FOR SELECT USING (true);

CREATE POLICY "Public read signal_sources"
  ON signal_sources FOR SELECT USING (true);

CREATE POLICY "Public read signal_claims"
  ON signal_claims FOR SELECT USING (true);

CREATE POLICY "Public read signal_claim_sources"
  ON signal_claim_sources FOR SELECT USING (true);

CREATE POLICY "Public read signal_claim_scores"
  ON signal_claim_scores FOR SELECT USING (true);

CREATE POLICY "Public read signal_claim_composites"
  ON signal_claim_composites FOR SELECT USING (true);

CREATE POLICY "Public read signal_consensus"
  ON signal_consensus FOR SELECT USING (true);

CREATE POLICY "Public read signal_summaries"
  ON signal_summaries FOR SELECT USING (true);
