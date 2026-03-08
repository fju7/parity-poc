-- Employer trends cache: stores computed trend data to avoid recomputation
CREATE TABLE IF NOT EXISTS employer_trends_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id TEXT NOT NULL UNIQUE,
  trend_data JSONB NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE employer_trends_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service role full access"
  ON employer_trends_cache
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
