-- Parity Provider: contract integrity tables
-- Run this in Supabase SQL Editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Provider contract rates (uploaded from Excel template)
CREATE TABLE IF NOT EXISTS provider_contracts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  payer_name TEXT NOT NULL,
  rates JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_contracts_user
--   ON provider_contracts(user_id);

-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_contracts_user_payer
--   ON provider_contracts(user_id, payer_name);

-- RLS policies
ALTER TABLE provider_contracts ENABLE ROW LEVEL SECURITY;

-- removed: user_id superseded by company_id in 000_core_tables.sql; policies replaced in migration 032
-- CREATE POLICY "Users can read own contracts"
--   ON provider_contracts FOR SELECT
--   USING (auth.uid() = user_id);

-- CREATE POLICY "Users can insert own contracts"
--   ON provider_contracts FOR INSERT
--   WITH CHECK (auth.uid() = user_id);

-- CREATE POLICY "Users can update own contracts"
--   ON provider_contracts FOR UPDATE
--   USING (auth.uid() = user_id);


-- Provider analysis results (from 835 remittance analysis)
CREATE TABLE IF NOT EXISTS provider_analyses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  payer_name TEXT,
  production_date TEXT,
  total_billed NUMERIC(12, 2),
  total_paid NUMERIC(12, 2),
  underpayment NUMERIC(12, 2),
  adherence_rate NUMERIC(5, 2),
  result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_analyses_user
--   ON provider_analyses(user_id);

-- RLS policies
ALTER TABLE provider_analyses ENABLE ROW LEVEL SECURITY;

-- removed: user_id superseded by company_id in 000_core_tables.sql; policies replaced in migration 032
-- CREATE POLICY "Users can read own analyses"
--   ON provider_analyses FOR SELECT
--   USING (auth.uid() = user_id);

-- CREATE POLICY "Users can insert own analyses"
--   ON provider_analyses FOR INSERT
--   WITH CHECK (auth.uid() = user_id);
