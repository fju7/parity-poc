-- Employer claims uploads: stores results from claims file analysis
CREATE TABLE IF NOT EXISTS employer_claims_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT,
  filename_original TEXT,
  total_claims INTEGER,
  total_paid NUMERIC,
  total_excess_2x NUMERIC,
  top_flagged_cpt TEXT,
  top_flagged_excess NUMERIC,
  column_mapping_json JSONB,
  results_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE employer_claims_uploads ENABLE ROW LEVEL SECURITY;

-- Allow inserts from anon (public tool, no auth required)
CREATE POLICY "Allow anonymous inserts on employer_claims_uploads"
  ON employer_claims_uploads FOR INSERT
  WITH CHECK (true);

-- Allow service role full access
CREATE POLICY "Service role full access on employer_claims_uploads"
  ON employer_claims_uploads FOR ALL
  USING (auth.role() = 'service_role');
