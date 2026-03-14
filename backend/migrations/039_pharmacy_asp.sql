-- Migration 039: pharmacy_asp table for Medicare Part B ASP drug pricing
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS pharmacy_asp (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  hcpcs_code text NOT NULL,
  short_description text,
  dosage text,
  payment_limit numeric,
  effective_quarter text,
  loaded_at timestamptz DEFAULT now()
);

-- Index for fast HCPCS lookups
CREATE INDEX IF NOT EXISTS idx_pharmacy_asp_hcpcs ON pharmacy_asp (hcpcs_code);

-- RLS
ALTER TABLE pharmacy_asp ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role full access on pharmacy_asp"
  ON pharmacy_asp FOR ALL
  USING (true)
  WITH CHECK (true);
