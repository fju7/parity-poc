-- Employer benchmark sessions: stores results from the PEPM benchmarking tool
CREATE TABLE IF NOT EXISTS employer_benchmark_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT,
  industry TEXT NOT NULL,
  company_size TEXT NOT NULL,
  state TEXT NOT NULL,
  pepm_input NUMERIC NOT NULL,
  pepm_median NUMERIC,
  percentile NUMERIC,
  dollar_gap_annual NUMERIC,
  result_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE employer_benchmark_sessions ENABLE ROW LEVEL SECURITY;

-- Allow inserts from anon (public benchmarking tool, no auth required)
CREATE POLICY "Allow anonymous inserts on employer_benchmark_sessions"
  ON employer_benchmark_sessions FOR INSERT
  WITH CHECK (true);

-- Allow service role full access
CREATE POLICY "Service role full access on employer_benchmark_sessions"
  ON employer_benchmark_sessions FOR ALL
  USING (auth.role() = 'service_role');
