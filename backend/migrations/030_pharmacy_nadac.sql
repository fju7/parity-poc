-- Migration 030: Pharmacy NADAC reference data and benchmark results tables

CREATE TABLE IF NOT EXISTS pharmacy_nadac (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ndc_code TEXT NOT NULL,
  drug_name TEXT NOT NULL,
  nadac_per_unit NUMERIC(10,4),
  pricing_unit TEXT,
  otc_or_rx TEXT,
  effective_date DATE,
  loaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pharmacy_nadac_ndc ON pharmacy_nadac(ndc_code);

CREATE TABLE IF NOT EXISTS pharmacy_benchmarks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id),
  uploaded_at TIMESTAMPTZ DEFAULT now(),
  file_name TEXT,
  total_claims INTEGER,
  total_billed NUMERIC(12,2),
  total_plan_paid NUMERIC(12,2),
  generic_rate NUMERIC(5,2),
  specialty_spend_pct NUMERIC(5,2),
  analysis_json JSONB,
  pbm_spread NUMERIC(12,2) DEFAULT NULL,
  therapeutic_alternatives JSONB DEFAULT NULL
);
