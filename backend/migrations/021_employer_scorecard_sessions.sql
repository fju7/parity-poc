-- Employer scorecard sessions: stores plan grading results
CREATE TABLE IF NOT EXISTS employer_scorecard_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT,
  plan_name TEXT,
  network_type TEXT,
  grade TEXT,
  score NUMERIC,
  savings_estimate_per_ee NUMERIC,
  parsed_plan_json JSONB,
  scored_criteria_json JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE employer_scorecard_sessions ENABLE ROW LEVEL SECURITY;

-- Allow inserts from anon (public tool, no auth required)
CREATE POLICY "Allow anonymous inserts on employer_scorecard_sessions"
  ON employer_scorecard_sessions FOR INSERT
  WITH CHECK (true);

-- Allow service role full access
CREATE POLICY "Service role full access on employer_scorecard_sessions"
  ON employer_scorecard_sessions FOR ALL
  USING (auth.role() = 'service_role');
