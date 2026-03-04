-- Benchmark Observations: Crowdsourced Commercial Rate Database
-- Stores anonymized billing data points from completed bill analyses.
-- No user_id, no patient info, no provider names, no exact dates, no full ZIP codes.

CREATE TABLE benchmark_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cpt_code TEXT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  amount_type TEXT NOT NULL CHECK (amount_type IN (
    'billed_amount', 'allowed_amount', 'patient_responsibility',
    'deductible_applied', 'plan_paid'
  )),
  insurer TEXT,
  insurer_raw TEXT,
  region TEXT NOT NULL,
  state_code TEXT,
  zip3 TEXT,
  provider_specialty TEXT,
  network_status TEXT DEFAULT 'unknown' CHECK (network_status IN (
    'in_network', 'out_of_network', 'unknown'
  )),
  facility_type TEXT DEFAULT 'unknown' CHECK (facility_type IN (
    'office', 'hospital_outpatient', 'hospital_inpatient',
    'asc', 'er', 'urgent_care', 'telehealth', 'unknown'
  )),
  service_month TEXT,
  confidence TEXT DEFAULT 'medium' CHECK (confidence IN ('high', 'medium', 'low')),
  input_method TEXT NOT NULL CHECK (input_method IN (
    'pdf_upload', 'paste_text', 'image_upload', 'manual_entry', 'sample_bill'
  )),
  is_outlier BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common benchmark queries
CREATE INDEX idx_bench_cpt_region ON benchmark_observations(cpt_code, region);
CREATE INDEX idx_bench_cpt_insurer ON benchmark_observations(cpt_code, insurer);
CREATE INDEX idx_bench_cpt_state ON benchmark_observations(cpt_code, state_code);
CREATE INDEX idx_bench_region_specialty ON benchmark_observations(region, provider_specialty);
CREATE INDEX idx_bench_created ON benchmark_observations(created_at);
CREATE INDEX idx_bench_confidence ON benchmark_observations(confidence) WHERE confidence != 'low';

-- Row Level Security
ALTER TABLE benchmark_observations ENABLE ROW LEVEL SECURITY;

-- Backend service can insert
CREATE POLICY "service_insert" ON benchmark_observations
  FOR INSERT TO service_role WITH CHECK (true);

-- No direct SELECT for anonymous or authenticated users
-- All reads go through aggregate views or backend API
