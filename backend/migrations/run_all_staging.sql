-- === 000_core_tables.sql ===
-- Migration 000: Core tables extracted from production Supabase
-- These tables were created manually before the migration system was established.
-- They must exist before any other migrations run.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS provider_profiles (id uuid NOT NULL DEFAULT uuid_generate_v4(), company_id uuid, practice_name text NOT NULL, specialty text, npi text, zip_code text, created_at timestamptz DEFAULT now(), practice_address text, billing_contact text);

CREATE TABLE IF NOT EXISTS provider_contracts (id uuid NOT NULL DEFAULT uuid_generate_v4(), company_id uuid, payer_name text NOT NULL, rates jsonb NOT NULL DEFAULT '[]'::jsonb, created_at timestamptz DEFAULT now());

CREATE TABLE IF NOT EXISTS provider_analyses (id uuid NOT NULL DEFAULT uuid_generate_v4(), company_id uuid, payer_name text, production_date text, total_billed numeric, total_paid numeric, underpayment numeric, adherence_rate numeric, result_json jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz DEFAULT now());

CREATE TABLE IF NOT EXISTS provider_audits (id uuid NOT NULL DEFAULT gen_random_uuid(), company_id uuid, practice_name text NOT NULL, practice_specialty text, num_providers int4 DEFAULT 1, billing_company text, contact_email text NOT NULL, payer_list jsonb DEFAULT '[]'::jsonb, analysis_ids jsonb DEFAULT '[]'::jsonb, status text DEFAULT 'submitted'::text, admin_notes text, created_at timestamptz DEFAULT now(), delivered_at timestamptz, follow_up_sent bool DEFAULT false, remittance_data jsonb DEFAULT '[]'::jsonb, archived bool DEFAULT false, report_token uuid);

CREATE TABLE IF NOT EXISTS provider_appeals (id uuid NOT NULL DEFAULT gen_random_uuid(), company_id uuid NOT NULL, subscription_id uuid, audit_id uuid, claim_id text NOT NULL DEFAULT ''::text, payer_name text NOT NULL DEFAULT ''::text, denial_code text NOT NULL DEFAULT ''::text, cpt_code text NOT NULL DEFAULT ''::text, amount numeric DEFAULT 0.00, letter_text text, letter_html text, appeal_strength text, cms_references jsonb DEFAULT '[]'::jsonb, status text NOT NULL DEFAULT 'drafted'::text, appeal_generated_at timestamptz DEFAULT now(), outcome_amount numeric, notes text, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());

CREATE TABLE IF NOT EXISTS provider_subscriptions (id uuid NOT NULL DEFAULT gen_random_uuid(), practice_name text NOT NULL, practice_specialty text DEFAULT ''::text, num_providers int4 DEFAULT 1, billing_company text DEFAULT ''::text, contact_email text NOT NULL, company_id uuid, payer_data jsonb DEFAULT '[]'::jsonb, remittance_data jsonb DEFAULT '[]'::jsonb, source_audit_id uuid, stripe_customer_id text, stripe_subscription_id text, status text NOT NULL DEFAULT 'active'::text, monthly_analyses jsonb DEFAULT '[]'::jsonb, created_at timestamptz DEFAULT now(), canceled_at timestamptz, trend_narrative text, trend_narrative_updated_at timestamptz);

CREATE TABLE IF NOT EXISTS provider_appeal_outcomes (id uuid NOT NULL DEFAULT gen_random_uuid(), appeal_id uuid, claim_id text, cpt_code text, denial_code text, payer text, signal_topic_slug text, appeal_submitted_at timestamptz, outcome text, outcome_recorded_at timestamptz, notes text, created_at timestamptz DEFAULT now());

CREATE TABLE IF NOT EXISTS signal_subscriptions (id uuid NOT NULL DEFAULT gen_random_uuid(), user_id uuid, tier text NOT NULL DEFAULT 'free'::text, billing_period text, stripe_customer_id text, stripe_subscription_id text, status text NOT NULL DEFAULT 'active'::text, current_period_start timestamptz, current_period_end timestamptz, created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now(), qa_questions_used int4 DEFAULT 0, qa_reset_at timestamptz DEFAULT now(), topic_requests_used int4 DEFAULT 0, topic_requests_reset_at timestamptz DEFAULT now(), cancel_at_period_end bool DEFAULT false);

CREATE TABLE IF NOT EXISTS signal_topic_subscriptions (id uuid NOT NULL DEFAULT gen_random_uuid(), user_id uuid, issue_id uuid, subscribed_at timestamptz DEFAULT now(), unsubscribed_at timestamptz, status text NOT NULL DEFAULT 'active'::text);

CREATE TABLE IF NOT EXISTS signal_notification_preferences (user_id uuid NOT NULL, method text NOT NULL DEFAULT 'push'::text, frequency text NOT NULL DEFAULT 'immediate'::text, major_shifts_only bool DEFAULT false, updated_at timestamptz DEFAULT now());

CREATE TABLE IF NOT EXISTS signal_notifications (id uuid NOT NULL DEFAULT gen_random_uuid(), user_id uuid, update_id uuid, title text NOT NULL, body text NOT NULL, deep_link text, delivery_method text NOT NULL, delivered_at timestamptz, read_at timestamptz, created_at timestamptz DEFAULT now());

-- === 001_unified_auth.sql ===
-- ============================================================
-- MIGRATION 001: Unified Auth Architecture
-- Run in Supabase SQL Editor
-- ============================================================

-- 1. Companies (the core organizational unit)
CREATE TABLE IF NOT EXISTS companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  type text NOT NULL CHECK (type IN ('employer', 'broker', 'provider')),
  industry text,
  state text,
  size_band text,
  stripe_customer_id text,
  created_at timestamptz DEFAULT now(),
  created_by_email text
);

-- 2. Company users (people who belong to a company)
CREATE TABLE IF NOT EXISTS company_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  email text NOT NULL,
  full_name text,
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'suspended')),
  invited_by_email text,
  created_at timestamptz DEFAULT now(),
  last_login_at timestamptz,
  UNIQUE(company_id, email)
);

-- 3. Sessions (UUID token-based, replaces email-only localStorage)
CREATE TABLE IF NOT EXISTS sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  company_id uuid REFERENCES companies(id) ON DELETE CASCADE,
  product text NOT NULL CHECK (product IN ('employer', 'broker', 'provider', 'health')),
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz NOT NULL,
  last_active_at timestamptz DEFAULT now(),
  user_agent text,
  ip_address text
);

-- 4. Company invitations
CREATE TABLE IF NOT EXISTS company_invitations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  invited_email text NOT NULL,
  invited_by_email text NOT NULL,
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
  token uuid NOT NULL DEFAULT gen_random_uuid(),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired')),
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz DEFAULT (now() + interval '7 days'),
  UNIQUE(token)
);

-- 5. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_email ON sessions(email);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_company_users_email ON company_users(email);
CREATE INDEX IF NOT EXISTS idx_company_users_company ON company_users(company_id);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON company_invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON company_invitations(invited_email);


-- === 002_employer_trial.sql ===
-- MIGRATION 002: Employer trial and simplified pricing
-- Run in Supabase SQL Editor

ALTER TABLE companies ADD COLUMN IF NOT EXISTS plan text DEFAULT 'free'
  CHECK (plan IN ('free', 'trial', 'pro', 'read_only', 'cancelled'));
ALTER TABLE companies ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS stripe_customer_id text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS stripe_subscription_id text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS plan_locked_until timestamptz;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS trial_started_at timestamptz;

-- === 002_rate_versioning.sql ===
-- 002_rate_versioning.sql
-- Historical CMS rate data versioning infrastructure.
-- Run in Supabase SQL Editor.

-- Enable uuid-ossp if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- 1. Rate schedule version registry
-- =========================================================================

CREATE TABLE IF NOT EXISTS rate_schedule_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_type   TEXT NOT NULL CHECK (schedule_type IN ('PFS', 'OPPS', 'CLFS')),
    vintage_year    INTEGER NOT NULL,
    vintage_quarter INTEGER,  -- NULL for annual schedules (PFS, OPPS); 1-4 for quarterly (CLFS)
    effective_date  DATE NOT NULL,
    expiry_date     DATE,     -- NULL means "current / no successor loaded yet"
    is_current      BOOLEAN NOT NULL DEFAULT FALSE,
    source_file     TEXT,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_count       INTEGER,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_rsv_type_effective
    ON rate_schedule_versions (schedule_type, effective_date);

CREATE INDEX IF NOT EXISTS idx_rsv_current
    ON rate_schedule_versions (schedule_type) WHERE is_current = TRUE;

-- =========================================================================
-- 2. PFS historical rates
-- =========================================================================

CREATE TABLE IF NOT EXISTS pfs_rates_historical (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_id          UUID NOT NULL REFERENCES rate_schedule_versions(id) ON DELETE CASCADE,
    hcpcs_code          TEXT NOT NULL,
    carrier             TEXT NOT NULL,
    locality_code       TEXT NOT NULL,
    nonfacility_amount  NUMERIC(10,2),
    facility_amount     NUMERIC(10,2)
);

CREATE INDEX IF NOT EXISTS idx_pfs_hist_version_code
    ON pfs_rates_historical (version_id, hcpcs_code);

CREATE INDEX IF NOT EXISTS idx_pfs_hist_code
    ON pfs_rates_historical (hcpcs_code);

-- =========================================================================
-- 3. OPPS historical rates
-- =========================================================================

CREATE TABLE IF NOT EXISTS opps_rates_historical (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_id      UUID NOT NULL REFERENCES rate_schedule_versions(id) ON DELETE CASCADE,
    hcpcs_code      TEXT NOT NULL,
    payment_rate    NUMERIC(10,2),
    description     TEXT
);

CREATE INDEX IF NOT EXISTS idx_opps_hist_version_code
    ON opps_rates_historical (version_id, hcpcs_code);

-- =========================================================================
-- 4. CLFS historical rates
-- =========================================================================

CREATE TABLE IF NOT EXISTS clfs_rates_historical (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_id      UUID NOT NULL REFERENCES rate_schedule_versions(id) ON DELETE CASCADE,
    hcpcs_code      TEXT NOT NULL,
    payment_rate    NUMERIC(10,2),
    description     TEXT
);

CREATE INDEX IF NOT EXISTS idx_clfs_hist_version_code
    ON clfs_rates_historical (version_id, hcpcs_code);

-- =========================================================================
-- 5. Seed current 2026 versions into registry
-- =========================================================================

INSERT INTO rate_schedule_versions (schedule_type, vintage_year, vintage_quarter, effective_date, expiry_date, is_current, source_file, notes)
VALUES
    ('PFS',  2026, NULL, '2026-01-01', NULL, TRUE, 'cy2026-carrier-files-nonqp-updated-12-29-2025.zip', 'CMS PFS 2026 — loaded from in-memory CSV at startup'),
    ('OPPS', 2026, NULL, '2026-01-01', NULL, TRUE, 'opps_rates.csv',                                    'CMS OPPS 2026 — loaded from in-memory CSV at startup'),
    ('CLFS', 2026, 1,    '2026-01-01', NULL, TRUE, 'clfs_rates.csv',                                    'CMS CLFS 2026 Q1 — loaded from in-memory CSV at startup');

-- === 003_provider_profiles.sql ===
-- Parity Provider: provider_profiles table
-- Run this in Supabase SQL Editor

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS provider_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  practice_name TEXT NOT NULL,
  specialty TEXT,
  npi TEXT,
  zip_code TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies
ALTER TABLE provider_profiles ENABLE ROW LEVEL SECURITY;

-- removed: user_id superseded by company_id in 000_core_tables.sql; policies replaced in migration 032
-- CREATE POLICY "Users can read own profile"
--   ON provider_profiles FOR SELECT
--   USING (auth.uid() = user_id);

-- CREATE POLICY "Users can insert own profile"
--   ON provider_profiles FOR INSERT
--   WITH CHECK (auth.uid() = user_id);

-- CREATE POLICY "Users can update own profile"
--   ON provider_profiles FOR UPDATE
--   USING (auth.uid() = user_id);

-- === 004_provider_contracts.sql ===
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

-- === 005_signal_tables.sql ===
-- 005_signal_tables.sql
-- Parity Signal: claim intelligence schema for AI-powered evidence scoring.
-- Run in Supabase SQL Editor.
-- IMPORTANT: Does not modify any existing tables.

-- =========================================================================
-- 1. Core content tables
-- =========================================================================

CREATE TABLE IF NOT EXISTS signal_issues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  title TEXT NOT NULL,
  url TEXT,
  source_type TEXT NOT NULL,              -- clinical_trial, fda, cms, pricing, public_reporting
  publication_date DATE,
  retrieved_at TIMESTAMPTZ DEFAULT now(),
  content_text TEXT,                       -- full text or structured summary
  metadata JSONB                           -- flexible additional metadata
);

CREATE TABLE IF NOT EXISTS signal_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  claim_text TEXT NOT NULL,
  category TEXT NOT NULL,                  -- efficacy, safety, cardiovascular, pricing, regulatory, emerging
  specificity TEXT,                         -- quantitative, qualitative, mixed
  extracted_at TIMESTAMPTZ DEFAULT now(),
  extraction_model TEXT
);

CREATE TABLE IF NOT EXISTS signal_claim_sources (
  claim_id UUID REFERENCES signal_claims(id),
  source_id UUID REFERENCES signal_sources(id),
  source_context TEXT,                     -- specific passage
  PRIMARY KEY (claim_id, source_id)
);

CREATE TABLE IF NOT EXISTS signal_claim_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID REFERENCES signal_claims(id),
  dimension TEXT NOT NULL,                 -- source_quality, data_support, reproducibility, consensus, recency, rigor
  score INTEGER CHECK (score BETWEEN 1 AND 5),
  rationale TEXT,
  scored_at TIMESTAMPTZ DEFAULT now(),
  scoring_model TEXT
);

CREATE TABLE IF NOT EXISTS signal_claim_composites (
  claim_id UUID PRIMARY KEY REFERENCES signal_claims(id),
  composite_score NUMERIC(3,2),
  evidence_category TEXT,                  -- strong, moderate, mixed, weak
  weights_used JSONB,
  scored_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_consensus (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  category TEXT NOT NULL,
  consensus_status TEXT NOT NULL,           -- consensus, debated, uncertain
  summary_text TEXT,
  supporting_claim_ids JSONB,
  arguments_for TEXT,                       -- for debated claims
  arguments_against TEXT,                   -- for debated claims
  mapped_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  version INTEGER DEFAULT 1,
  summary_json JSONB,
  summary_text TEXT,
  generated_at TIMESTAMPTZ DEFAULT now(),
  generation_model TEXT
);

-- =========================================================================
-- 2. Subscription and tier management
-- =========================================================================

CREATE TABLE IF NOT EXISTS signal_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  tier TEXT NOT NULL DEFAULT 'free',           -- free, standard, premium
  billing_period TEXT,                          -- monthly, annual (null for free)
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  status TEXT NOT NULL DEFAULT 'active',        -- active, canceled, past_due, trialing
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_topic_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  issue_id UUID REFERENCES signal_issues(id),
  subscribed_at TIMESTAMPTZ DEFAULT now(),
  unsubscribed_at TIMESTAMPTZ,                 -- null if currently active
  status TEXT NOT NULL DEFAULT 'active',        -- active, swapped, canceled
  UNIQUE(user_id, issue_id)
);

-- =========================================================================
-- 3. Evidence updates and notifications
-- =========================================================================

CREATE TABLE IF NOT EXISTS signal_evidence_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  claim_id UUID REFERENCES signal_claims(id),
  change_type TEXT NOT NULL,                   -- score_shift, consensus_change, new_claim, new_source
  previous_score NUMERIC(3,2),
  new_score NUMERIC(3,2),
  previous_category TEXT,
  new_category TEXT,
  change_description TEXT,
  source_id UUID REFERENCES signal_sources(id),
  detected_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_notification_preferences (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id),
  method TEXT NOT NULL DEFAULT 'push',         -- push, sms, email
  frequency TEXT NOT NULL DEFAULT 'immediate',
  major_shifts_only BOOLEAN DEFAULT false,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  update_id UUID REFERENCES signal_evidence_updates(id),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  deep_link TEXT,
  delivery_method TEXT NOT NULL,
  delivered_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =========================================================================
-- 4. Topic requests (Premium feature)
-- =========================================================================

CREATE TABLE IF NOT EXISTS signal_topic_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  topic_name TEXT NOT NULL,
  description TEXT,
  reference_urls JSONB,
  status TEXT NOT NULL DEFAULT 'submitted',
  published_issue_id UUID REFERENCES signal_issues(id),
  submitted_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

-- =========================================================================
-- 5. Event capture and analytics
-- =========================================================================

CREATE TABLE IF NOT EXISTS signal_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  event_type TEXT NOT NULL,
  event_data JSONB,
  device_type TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_events_type_date
  ON signal_events(event_type, created_at);

CREATE INDEX IF NOT EXISTS idx_signal_events_user
  ON signal_events(user_id, created_at);

-- =========================================================================
-- 6. Platform metrics cache
-- =========================================================================

CREATE TABLE IF NOT EXISTS signal_platform_metrics (
  metric_key TEXT PRIMARY KEY,
  metric_value NUMERIC,
  display_label TEXT,
  display_order INTEGER,
  visible BOOLEAN DEFAULT false,
  refreshed_at TIMESTAMPTZ DEFAULT now()
);

-- =========================================================================
-- 7. Analytical Paths (Phase 1 — create table now for readiness)
-- =========================================================================

CREATE TABLE IF NOT EXISTS signal_analytical_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  weights JSONB NOT NULL,
  trade_off_summary TEXT,
  source_type_association TEXT,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- === 006_signal_public_read.sql ===
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

-- === 007_signal_topic_requests.sql ===
-- Migration 007: Create signal_topic_requests table
-- Allows premium users to request new topics for Parity Signal

CREATE TABLE IF NOT EXISTS signal_topic_requests (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid NOT NULL,
  topic_name text NOT NULL,
  description text NOT NULL,
  reference_urls text[] DEFAULT '{}',
  status text DEFAULT 'submitted',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE signal_topic_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own requests"
  ON signal_topic_requests FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own requests"
  ON signal_topic_requests FOR SELECT
  USING (auth.uid() = user_id);

-- === 008_benchmark_observations.sql ===
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

-- === 009_enable_rls_all_tables.sql ===
-- 009_enable_rls_all_tables.sql
-- Enable RLS on all 12 public tables that currently lack it.
-- Run in Supabase SQL Editor.
--
-- Groups:
--   A. User-data tables (4) — user-scoped policies + service_role access
--   B. Analytics/event tables (4) — service_role write, scoped or public read
--   C. Reference data tables (4) — service_role write, public read

-- =========================================================================
-- A. USER-DATA TABLES
-- =========================================================================

-- -------------------------------------------------------------------------
-- A1. signal_subscriptions (user_id, Stripe IDs, tier, billing)
-- Users read own; backend manages via Stripe webhooks (service_role)
-- -------------------------------------------------------------------------
ALTER TABLE signal_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own subscription"
  ON signal_subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on subscriptions"
  ON signal_subscriptions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- A2. signal_topic_subscriptions (user_id, issue_id, status)
-- Users manage own topic subscriptions; backend also accesses
-- -------------------------------------------------------------------------
ALTER TABLE signal_topic_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own topic subscriptions"
  ON signal_topic_subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own topic subscriptions"
  ON signal_topic_subscriptions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own topic subscriptions"
  ON signal_topic_subscriptions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on topic subscriptions"
  ON signal_topic_subscriptions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- A3. signal_notification_preferences (PK = user_id)
-- Users manage own preferences; backend reads for delivery
-- -------------------------------------------------------------------------
ALTER TABLE signal_notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own notification preferences"
  ON signal_notification_preferences FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notification preferences"
  ON signal_notification_preferences FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notification preferences"
  ON signal_notification_preferences FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on notification preferences"
  ON signal_notification_preferences FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- A4. signal_notifications (user_id, delivery, read status)
-- Backend creates; users read own and mark as read
-- -------------------------------------------------------------------------
ALTER TABLE signal_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own notifications"
  ON signal_notifications FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications"
  ON signal_notifications FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on notifications"
  ON signal_notifications FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);


-- =========================================================================
-- B. ANALYTICS / EVENT TABLES
-- =========================================================================

-- -------------------------------------------------------------------------
-- B1. signal_events (nullable user_id, event tracking)
-- Authenticated users insert own events; service_role full access
-- No public reads — analytics are backend-only
-- -------------------------------------------------------------------------
ALTER TABLE signal_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can insert events"
  ON signal_events FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Service role full access on events"
  ON signal_events FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- B2. signal_evidence_updates (change log for public signal data)
-- Public read (these describe changes to publicly visible claims);
-- only service_role writes
-- -------------------------------------------------------------------------
ALTER TABLE signal_evidence_updates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read evidence updates"
  ON signal_evidence_updates FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on evidence updates"
  ON signal_evidence_updates FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- B3. signal_platform_metrics (public dashboard stats)
-- Public read; service_role writes
-- -------------------------------------------------------------------------
ALTER TABLE signal_platform_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read platform metrics"
  ON signal_platform_metrics FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on platform metrics"
  ON signal_platform_metrics FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- B4. signal_analytical_profiles (scoring weight profiles)
-- Public read (used by frontend evidence display); service_role writes
-- -------------------------------------------------------------------------
ALTER TABLE signal_analytical_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read analytical profiles"
  ON signal_analytical_profiles FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on analytical profiles"
  ON signal_analytical_profiles FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);


-- =========================================================================
-- C. REFERENCE DATA TABLES (CMS rate history)
-- =========================================================================

-- -------------------------------------------------------------------------
-- C1. rate_schedule_versions (version registry)
-- -------------------------------------------------------------------------
ALTER TABLE rate_schedule_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read rate schedule versions"
  ON rate_schedule_versions FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on rate schedule versions"
  ON rate_schedule_versions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- C2. pfs_rates_historical
-- -------------------------------------------------------------------------
ALTER TABLE pfs_rates_historical ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read pfs rates historical"
  ON pfs_rates_historical FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on pfs rates historical"
  ON pfs_rates_historical FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- C3. opps_rates_historical
-- -------------------------------------------------------------------------
ALTER TABLE opps_rates_historical ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read opps rates historical"
  ON opps_rates_historical FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on opps rates historical"
  ON opps_rates_historical FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- C4. clfs_rates_historical
-- -------------------------------------------------------------------------
ALTER TABLE clfs_rates_historical ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read clfs rates historical"
  ON clfs_rates_historical FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on clfs rates historical"
  ON clfs_rates_historical FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- === 010_claim_plain_summary.sql ===
-- Add plain-language summary column to signal_claims
ALTER TABLE signal_claims ADD COLUMN IF NOT EXISTS plain_summary TEXT;

-- === 011_four_tier_subscriptions.sql ===
-- 011_four_tier_subscriptions.sql
-- Add usage tracking columns to signal_subscriptions and update
-- signal_topic_requests for the four-tier subscription model.
-- Run in Supabase SQL Editor.

-- Usage tracking columns on signal_subscriptions
ALTER TABLE signal_subscriptions
  ADD COLUMN IF NOT EXISTS qa_questions_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS qa_reset_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS topic_requests_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS topic_requests_reset_at TIMESTAMPTZ DEFAULT NOW();

-- Add new columns to signal_topic_requests for Claude-parsed fields
-- (table already exists from migration 007)
ALTER TABLE signal_topic_requests
  ADD COLUMN IF NOT EXISTS raw_request TEXT,
  ADD COLUMN IF NOT EXISTS parsed_title TEXT,
  ADD COLUMN IF NOT EXISTS parsed_description TEXT,
  ADD COLUMN IF NOT EXISTS parsed_slug TEXT,
  ADD COLUMN IF NOT EXISTS clarification_message TEXT,
  ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
  ADD COLUMN IF NOT EXISTS issue_id UUID REFERENCES signal_issues(id),
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Update status check constraint to include new statuses
-- Drop old constraint if it exists, then add new one
ALTER TABLE signal_topic_requests DROP CONSTRAINT IF EXISTS signal_topic_requests_status_check;
ALTER TABLE signal_topic_requests
  ADD CONSTRAINT signal_topic_requests_status_check
  CHECK (status IN ('submitted', 'pending', 'clarification_needed', 'approved', 'processing', 'completed', 'rejected'));

-- === 012_provider_audits.sql ===
-- Migration 012: provider_audits table for multi-payer batch audit workflow
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS provider_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    practice_name TEXT NOT NULL,
    practice_specialty TEXT,
    num_providers INTEGER DEFAULT 1,
    billing_company TEXT,
    contact_email TEXT NOT NULL,
    payer_list JSONB DEFAULT '[]'::jsonb,
    -- Array of {payer_name, fee_schedule_method, fee_schedule_data, code_count}
    analysis_ids JSONB DEFAULT '[]'::jsonb,
    -- Array of provider_analyses UUIDs
    status TEXT DEFAULT 'submitted' CHECK (status IN ('submitted', 'processing', 'review', 'delivered')),
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    follow_up_sent BOOLEAN DEFAULT false
);

-- Enable RLS
ALTER TABLE provider_audits ENABLE ROW LEVEL SECURITY;

-- Service role full access
CREATE POLICY "service_role_full_access" ON provider_audits
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- removed: user_id superseded by company_id in 000_core_tables.sql; policies replaced in migration 032
-- CREATE POLICY "users_read_own_audits" ON provider_audits
--     FOR SELECT
--     USING (
--         auth.uid() = user_id
--         OR contact_email = (SELECT email FROM auth.users WHERE id = auth.uid())
--     );

-- CREATE POLICY "users_insert_own_audits" ON provider_audits
--     FOR INSERT
--     WITH CHECK (auth.uid() = user_id);

-- Index for common queries
-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_audits_user_id ON provider_audits(user_id);
CREATE INDEX IF NOT EXISTS idx_provider_audits_status ON provider_audits(status);
CREATE INDEX IF NOT EXISTS idx_provider_audits_contact_email ON provider_audits(contact_email);

-- === 013_audit_remittance_data.sql ===
-- Migration 013: Add remittance_data column to provider_audits
-- Stores parsed 835 line items so admin can run analysis without re-uploading
-- Run in Supabase SQL Editor

ALTER TABLE provider_audits
    ADD COLUMN IF NOT EXISTS remittance_data JSONB DEFAULT '[]'::jsonb;
-- Array of {filename, payer_name, claims: [{cpt_code, billed_amount, paid_amount, units, adjustments, claim_id}]}

COMMENT ON COLUMN provider_audits.remittance_data IS 'Parsed 835 line items grouped by file, stored at submission for admin analysis';

-- Also update payer_list comment to reflect that fee_schedule_data is now included
COMMENT ON COLUMN provider_audits.payer_list IS 'Array of {payer_name, fee_schedule_method, fee_schedule_data: {cpt: rate}, code_count}';

-- === 014_audit_archived.sql ===
-- Migration 014: Add archived column to provider_audits
-- Run in Supabase SQL Editor

ALTER TABLE provider_audits ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT false;

-- === 015_audit_report_token.sql ===
ALTER TABLE provider_audits ADD COLUMN IF NOT EXISTS report_token UUID;
CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_report_token ON provider_audits (report_token) WHERE report_token IS NOT NULL;

-- === 016_provider_subscriptions.sql ===
-- Migration 016: Provider Subscriptions table
-- Stores audit-to-subscription conversions for ongoing monitoring ($300/month)

CREATE TABLE IF NOT EXISTS provider_subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    practice_name TEXT NOT NULL,
    practice_specialty TEXT DEFAULT '',
    num_providers INTEGER DEFAULT 1,
    billing_company TEXT DEFAULT '',
    contact_email TEXT NOT NULL,
    user_id UUID,
    payer_data JSONB DEFAULT '[]'::jsonb,
    remittance_data JSONB DEFAULT '[]'::jsonb,
    source_audit_id UUID REFERENCES provider_audits(id),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due')),
    monthly_analyses JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    canceled_at TIMESTAMPTZ
);

-- Indexes
-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_user_id ON provider_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_contact_email ON provider_subscriptions(contact_email);
CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_source_audit ON provider_subscriptions(source_audit_id);
CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_stripe_sub ON provider_subscriptions(stripe_subscription_id);

-- Enable RLS
ALTER TABLE provider_subscriptions ENABLE ROW LEVEL SECURITY;

-- Service role: full access
CREATE POLICY "service_role_full_access" ON provider_subscriptions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- removed: user_id superseded by company_id in 000_core_tables.sql; policies replaced in migration 032
-- CREATE POLICY "users_read_own_subscriptions" ON provider_subscriptions
--     FOR SELECT
--     USING (
--         auth.uid() = user_id
--         OR contact_email = (SELECT email FROM auth.users WHERE id = auth.uid())
--     );

-- === 017_subscription_trend_columns.sql ===
-- Add cached AI trend narrative to provider_subscriptions
ALTER TABLE provider_subscriptions
  ADD COLUMN IF NOT EXISTS trend_narrative TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS trend_narrative_updated_at TIMESTAMPTZ DEFAULT NULL;

-- === 018_provider_appeals.sql ===
-- Create provider_appeals table for tracking appeal letters
CREATE TABLE IF NOT EXISTS provider_appeals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  subscription_id UUID REFERENCES provider_subscriptions(id),
  audit_id UUID REFERENCES provider_audits(id),
  claim_id TEXT NOT NULL DEFAULT '',
  payer_name TEXT NOT NULL DEFAULT '',
  denial_code TEXT NOT NULL DEFAULT '',
  cpt_code TEXT NOT NULL DEFAULT '',
  amount DECIMAL(12,2) DEFAULT 0.00,
  letter_text TEXT,
  letter_html TEXT,
  appeal_strength TEXT,
  cms_references JSONB DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'drafted',
  appeal_generated_at TIMESTAMPTZ DEFAULT NOW(),
  outcome_amount DECIMAL(12,2),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups by user
-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_appeals_user_id ON provider_appeals(user_id);

-- Index for subscription-based queries
CREATE INDEX IF NOT EXISTS idx_provider_appeals_subscription_id ON provider_appeals(subscription_id);

-- Index for audit-based queries
CREATE INDEX IF NOT EXISTS idx_provider_appeals_audit_id ON provider_appeals(audit_id);

-- Enable RLS
ALTER TABLE provider_appeals ENABLE ROW LEVEL SECURITY;

-- removed: user_id superseded by company_id in 000_core_tables.sql; policies replaced in migration 032
-- CREATE POLICY "Users can view own appeals" ON provider_appeals
--   FOR SELECT USING (auth.uid() = user_id);

-- CREATE POLICY "Users can insert own appeals" ON provider_appeals
--   FOR INSERT WITH CHECK (auth.uid() = user_id);

-- CREATE POLICY "Users can update own appeals" ON provider_appeals
--   FOR UPDATE USING (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "Service role full access" ON provider_appeals
  FOR ALL USING (auth.role() = 'service_role');

-- === 019_employer_benchmark_sessions.sql ===
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

-- === 020_employer_claims_uploads.sql ===
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

-- === 021_employer_scorecard_sessions.sql ===
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

-- === 022_employer_subscriptions.sql ===
-- Employer subscriptions: manages employer tier and Stripe billing
CREATE TABLE IF NOT EXISTS employer_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  company_name TEXT,
  employee_count INTEGER,
  tier TEXT NOT NULL,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  status TEXT DEFAULT 'active',
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE employer_subscriptions ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role full access on employer_subscriptions"
  ON employer_subscriptions FOR ALL
  USING (auth.role() = 'service_role');

-- === 023_employer_trends_cache.sql ===
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

-- === 024_broker_portal.sql ===
-- Migration 024: Broker Portal
-- Tables for broker accounts, employer links, and custom OTP codes

-- ============================================================
-- 1. broker_accounts — registered broker profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS broker_accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    firm_name   TEXT NOT NULL,
    contact_name TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE broker_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on broker_accounts"
    ON broker_accounts FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================
-- 2. broker_employer_links — many-to-many between brokers and employers
-- ============================================================
CREATE TABLE IF NOT EXISTS broker_employer_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    broker_email    TEXT NOT NULL REFERENCES broker_accounts(email) ON DELETE CASCADE,
    employer_email  TEXT NOT NULL,
    linked_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(broker_email, employer_email)
);

-- RLS
ALTER TABLE broker_employer_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on broker_employer_links"
    ON broker_employer_links FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================
-- 3. otp_codes — custom OTP for broker auth (not Supabase auth)
-- ============================================================
CREATE TABLE IF NOT EXISTS otp_codes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    code        TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE otp_codes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on otp_codes"
    ON otp_codes FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Index for quick lookup
CREATE INDEX IF NOT EXISTS idx_otp_codes_email_code ON otp_codes(email, code);

-- Index for broker links lookup
CREATE INDEX IF NOT EXISTS idx_broker_employer_links_broker ON broker_employer_links(broker_email);
CREATE INDEX IF NOT EXISTS idx_broker_employer_links_employer ON broker_employer_links(employer_email);

-- === 025_broker_auth_migration.sql ===
-- Migration 025 (broker auth): Add broker schema to unified auth system
-- Data migration steps removed -- they depended on pre-migration broker_accounts
-- columns (plan, stripe_customer_id, etc.) that do not exist in a fresh database.

-- ============================================================
-- Step 1: Add broker-specific columns to companies
-- ============================================================
ALTER TABLE companies ADD COLUMN IF NOT EXISTS broker_client_limit int DEFAULT 10;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS broker_commission_rate numeric DEFAULT 0.20;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS phone text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS referral_code text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS logo_url text;

-- ============================================================
-- Step 2: Create broker_commissions table
-- ============================================================
CREATE TABLE IF NOT EXISTS broker_commissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_company_id uuid REFERENCES companies(id),
  employer_company_id uuid REFERENCES companies(id),
  referral_date timestamptz DEFAULT now(),
  commission_rate numeric DEFAULT 0.20,
  commission_months int DEFAULT 12,
  first_paid_month timestamptz,
  status text DEFAULT 'pending'
    CHECK (status IN ('pending', 'active', 'completed', 'cancelled')),
  created_at timestamptz DEFAULT now()
);

ALTER TABLE broker_commissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on broker_commissions"
  ON broker_commissions FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- ============================================================
-- Step 3: Add referral tracking columns to company_invitations
-- ============================================================
ALTER TABLE company_invitations ADD COLUMN IF NOT EXISTS invitation_type text DEFAULT 'team_invite';
ALTER TABLE company_invitations ADD COLUMN IF NOT EXISTS referring_company_id uuid REFERENCES companies(id);

-- ============================================================
-- Step 4: Indexes for broker_commissions
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_broker_commissions_broker ON broker_commissions(broker_company_id);
CREATE INDEX IF NOT EXISTS idx_broker_commissions_employer ON broker_commissions(employer_company_id);
CREATE INDEX IF NOT EXISTS idx_broker_commissions_status ON broker_commissions(status);

-- === 025_broker_client_benchmarks.sql ===
-- Migration 025: Broker client benchmarks and onboarding support
-- Run in Supabase SQL Editor

-- 1. Broker client benchmarks table
create table if not exists broker_client_benchmarks (
  id uuid primary key default gen_random_uuid(),
  broker_email text not null,
  employer_email text,
  company_name text not null,
  employee_count int,
  industry text,
  state text,
  carrier text,
  estimated_pepm float,
  benchmark_result jsonb,
  share_token uuid not null default gen_random_uuid(),
  share_token_created_at timestamptz not null default now(),
  view_count int not null default 0,
  first_viewed_at timestamptz,
  created_at timestamptz not null default now()
);

alter table broker_client_benchmarks enable row level security;

create policy "service role full access"
  on broker_client_benchmarks
  for all to service_role
  using (true) with check (true);

-- Allow public read via share token (no auth required)
create policy "public read by share token"
  on broker_client_benchmarks
  for select to anon
  using (true);

-- 2. Update broker_employer_links for onboarding flow
alter table broker_employer_links
  add column if not exists status text not null default 'onboarded',
  add column if not exists company_name text,
  add column if not exists employee_count_range text,
  add column if not exists industry text,
  add column if not exists state text,
  add column if not exists carrier text;

-- === 025_unified_auth_backfill.sql ===
-- Migration 025 (backfill): Add company_id to tables created after 001
-- These ALTERs were originally in 001_unified_auth.sql but depend on
-- tables created in migrations 020-024. Moved here to fix fresh-database ordering.

-- Add company_id to existing tables
ALTER TABLE employer_subscriptions ADD COLUMN IF NOT EXISTS company_id uuid REFERENCES companies(id);
ALTER TABLE employer_claims_uploads ADD COLUMN IF NOT EXISTS company_id uuid REFERENCES companies(id);
ALTER TABLE broker_employer_links ADD COLUMN IF NOT EXISTS employer_company_id uuid REFERENCES companies(id);

-- Add product column to otp_codes
ALTER TABLE otp_codes ADD COLUMN IF NOT EXISTS product text DEFAULT 'broker';

-- === 026_broker_signup.sql ===
-- Migration 026: Add broker signup columns
-- Run this in Supabase SQL Editor

alter table broker_accounts
  add column if not exists name text,
  add column if not exists phone text,
  add column if not exists status text not null default 'active',
  add column if not exists created_at timestamptz not null default now();

-- Note: firm_name and contact_name columns already exist in broker_accounts.
-- The signup endpoint uses contact_name for the broker's name.

-- === 027_broker_portfolio.sql ===
-- Migration 027: Add broker portfolio columns
-- Run this in Supabase SQL Editor

alter table broker_employer_links
  add column if not exists renewal_month date,
  add column if not exists broker_notes text;

alter table broker_accounts
  add column if not exists logo_url text;

-- === 028_deletion_requests.sql ===
-- 028: Deletion requests table for GDPR/privacy compliance
CREATE TABLE IF NOT EXISTS deletion_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id UUID REFERENCES companies(id),
  requested_by UUID REFERENCES company_users(id),
  requested_at TIMESTAMPTZ DEFAULT now(),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed'))
);

-- === 029_signal_analytical_profiles_seed.sql ===
-- 029: Seed analytical profiles for Parity Signal
-- Populates signal_analytical_profiles with 3 named profiles,
-- each with different scoring weights and trade-off summaries.

INSERT INTO signal_analytical_profiles (name, description, weights, trade_off_summary, source_type_association, is_default)
VALUES
  (
    'Balanced',
    'Default scoring — equal consideration across all evidence dimensions.',
    '{"source_quality": 0.25, "data_support": 0.20, "reproducibility": 0.20, "consensus": 0.15, "recency": 0.10, "rigor": 0.10}',
    'The default view weights all evidence dimensions proportionally. No single factor dominates — you see the full picture as-is.',
    NULL,
    true
  ),
  (
    'Regulatory',
    'Heavily weights source quality and consensus — FDA/CMS/official sources dominate conclusions.',
    '{"source_quality": 0.40, "data_support": 0.10, "reproducibility": 0.10, "consensus": 0.30, "recency": 0.05, "rigor": 0.05}',
    'This view prioritizes official regulatory sources (FDA, CMS, EMA) and established scientific consensus. Claims backed by authoritative sources rank higher, even if newer studies suggest different conclusions. Use this lens when regulatory positioning or compliance matters most.',
    'fda,cms,regulatory',
    false
  ),
  (
    'Clinical',
    'Heavily weights reproducibility and rigor — peer-reviewed trials and methodological quality dominate.',
    '{"source_quality": 0.10, "data_support": 0.15, "reproducibility": 0.30, "consensus": 0.05, "recency": 0.05, "rigor": 0.35}',
    'This view prioritizes claims supported by reproducible, methodologically rigorous studies — primarily RCTs and systematic reviews. A single well-designed trial can outweigh multiple lower-quality sources. Use this lens when clinical decision-making or formulary evaluation is the goal.',
    'clinical_trial,systematic_review',
    false
  ),
  (
    'Patient',
    'Heavily weights recency and data support — what is known now, practically, for real-world decisions.',
    '{"source_quality": 0.10, "data_support": 0.35, "reproducibility": 0.10, "consensus": 0.10, "recency": 0.30, "rigor": 0.05}',
    'This view prioritizes the most recent evidence and breadth of real-world data support. Newer findings and practical outcomes rank higher than historical consensus. Use this lens when making time-sensitive decisions or evaluating emerging treatments where the latest data matters most.',
    'real_world,observational',
    false
  )
ON CONFLICT DO NOTHING;

-- === 030_pharmacy_nadac.sql ===
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

-- === 031_provider_profiles_company_id.sql ===
-- Migration 031: Rename provider_profiles.user_id → company_id
-- The column was referencing auth.users(id) but actually stores companies.id values.
-- Run this in Supabase SQL Editor.
-- Wrapped in DO blocks so this is safe on fresh databases where user_id never existed.

-- 1. Drop old foreign key constraint (references auth.users)
ALTER TABLE provider_profiles
  DROP CONSTRAINT IF EXISTS provider_profiles_user_id_fkey;

-- 2. Delete orphaned rows and rename column (only if user_id exists)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_profiles' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_profiles
    WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_profiles RENAME COLUMN user_id TO company_id;
  END IF;
END $$;

-- 3. Add new foreign key referencing companies(id)
ALTER TABLE provider_profiles
  ADD CONSTRAINT provider_profiles_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- 4. Update unique constraint / index if one exists on user_id
ALTER TABLE provider_profiles DROP CONSTRAINT IF EXISTS provider_profiles_user_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS provider_profiles_company_id_key ON provider_profiles (company_id);

-- 5. Drop old RLS policies that reference user_id and recreate with company_id
DROP POLICY IF EXISTS "Users can read own profile" ON provider_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON provider_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON provider_profiles;

-- RLS policies now use service_role key from backend, so simple permissive policies:
CREATE POLICY "Service role full access" ON provider_profiles
  FOR ALL USING (true) WITH CHECK (true);

-- === 032_provider_tables_company_id.sql ===
-- Migration 032: Fix provider_contracts, provider_analyses, provider_audits,
-- provider_appeals, provider_subscriptions — rename user_id → company_id
-- Same fix as migration 031 did for provider_profiles.
-- Wrapped in DO blocks so this is safe on fresh databases where user_id never existed.
-- Run this in Supabase SQL Editor.

-- =========================================================================
-- provider_contracts
-- =========================================================================
ALTER TABLE provider_contracts DROP CONSTRAINT IF EXISTS provider_contracts_user_id_fkey;
ALTER TABLE provider_contracts DROP CONSTRAINT IF EXISTS provider_contracts_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_contracts' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_contracts WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_contracts RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_contracts
  ADD CONSTRAINT provider_contracts_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS: drop auth.uid()-based policies, allow service role
DROP POLICY IF EXISTS "Users can read own contracts" ON provider_contracts;
DROP POLICY IF EXISTS "Users can insert own contracts" ON provider_contracts;
DROP POLICY IF EXISTS "Users can update own contracts" ON provider_contracts;
DROP POLICY IF EXISTS "Service role full access" ON provider_contracts;
CREATE POLICY "Service role full access" ON provider_contracts
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_analyses
-- =========================================================================
ALTER TABLE provider_analyses DROP CONSTRAINT IF EXISTS provider_analyses_user_id_fkey;
ALTER TABLE provider_analyses DROP CONSTRAINT IF EXISTS provider_analyses_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_analyses' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_analyses WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_analyses RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_analyses
  ADD CONSTRAINT provider_analyses_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS
DROP POLICY IF EXISTS "Users can read own analyses" ON provider_analyses;
DROP POLICY IF EXISTS "Users can insert own analyses" ON provider_analyses;
DROP POLICY IF EXISTS "Service role full access" ON provider_analyses;
CREATE POLICY "Service role full access" ON provider_analyses
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_audits
-- =========================================================================
ALTER TABLE provider_audits DROP CONSTRAINT IF EXISTS provider_audits_user_id_fkey;
ALTER TABLE provider_audits DROP CONSTRAINT IF EXISTS provider_audits_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_audits' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_audits WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_audits RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_audits
  ADD CONSTRAINT provider_audits_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS
DROP POLICY IF EXISTS "service_role_full_access" ON provider_audits;
DROP POLICY IF EXISTS "users_read_own_audits" ON provider_audits;
DROP POLICY IF EXISTS "users_insert_own_audits" ON provider_audits;
DROP POLICY IF EXISTS "Service role full access" ON provider_audits;
CREATE POLICY "Service role full access" ON provider_audits
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_appeals
-- =========================================================================
ALTER TABLE provider_appeals DROP CONSTRAINT IF EXISTS provider_appeals_user_id_fkey;
ALTER TABLE provider_appeals DROP CONSTRAINT IF EXISTS provider_appeals_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_appeals' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_appeals WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_appeals RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_appeals
  ADD CONSTRAINT provider_appeals_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS
DROP POLICY IF EXISTS "Users can view own appeals" ON provider_appeals;
DROP POLICY IF EXISTS "Users can insert own appeals" ON provider_appeals;
DROP POLICY IF EXISTS "Users can update own appeals" ON provider_appeals;
DROP POLICY IF EXISTS "Service role full access" ON provider_appeals;
CREATE POLICY "Service role full access" ON provider_appeals
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_subscriptions (user_id has no FK, just rename)
-- =========================================================================
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_subscriptions' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_subscriptions WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_subscriptions RENAME COLUMN user_id TO company_id;
  END IF;
END $$;

-- Fix RLS
DROP POLICY IF EXISTS "service_role_full_access" ON provider_subscriptions;
DROP POLICY IF EXISTS "users_read_own_subscriptions" ON provider_subscriptions;
DROP POLICY IF EXISTS "Service role full access" ON provider_subscriptions;
CREATE POLICY "Service role full access" ON provider_subscriptions
  FOR ALL USING (true) WITH CHECK (true);

-- === 033_health_sbc_uploads.sql ===
-- Migration 033: health_sbc_uploads table for Parity Health SBC analysis
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS health_sbc_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT,
  plan_name TEXT,
  plan_year TEXT,
  sbc_data JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for session lookup
CREATE INDEX IF NOT EXISTS idx_health_sbc_uploads_session
  ON health_sbc_uploads (session_id);

-- RLS: allow service role full access
ALTER TABLE health_sbc_uploads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON health_sbc_uploads
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- === 036_provider_benchmark_observations.sql ===
-- Migration 036: Provider benchmark observations table
-- Captures anonymized denial rate and underpayment observations from 835 analyses
-- No PHI, no user_id — used to build proprietary benchmarks over time

CREATE TABLE IF NOT EXISTS provider_benchmark_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    observed_at TIMESTAMPTZ DEFAULT NOW(),

    -- What was analyzed (no PHI, no practice name, no user ID)
    cpt_code TEXT NOT NULL,
    payer_category TEXT,     -- "Medicare", "BCBS", "Aetna", "Commercial", etc.
    specialty TEXT,          -- from provider_profiles if available

    -- Observation data
    was_denied BOOLEAN NOT NULL,
    was_underpaid BOOLEAN NOT NULL,
    paid_as_pct_of_contracted FLOAT,  -- e.g. 0.92 = paid at 92% of contract
    denial_code TEXT,                 -- CO-16, CO-45, etc.

    -- Geographic context (coarse — no ZIP, just region)
    region TEXT,   -- "Northeast", "South", "Midwest", "West", "Unknown"

    -- Metadata
    line_count_in_analysis INT  -- how many lines were in the full 835
                                -- (context for statistical weight)
);

CREATE INDEX IF NOT EXISTS idx_pbo_cpt_code
    ON provider_benchmark_observations(cpt_code);
CREATE INDEX IF NOT EXISTS idx_pbo_observed_at
    ON provider_benchmark_observations(observed_at);

-- No RLS needed — this table has no PHI and no user_id.
-- Service role key writes; no user reads directly.

-- === 037_signal_cancel_at_period_end.sql ===
-- Migration 037: Add cancel_at_period_end to signal_subscriptions
ALTER TABLE signal_subscriptions
  ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE;

-- === 038_broker_referrals.sql ===
-- Migration 038: Broker referral tracking
CREATE TABLE IF NOT EXISTS broker_referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  referrer_email TEXT NOT NULL,
  referral_code TEXT NOT NULL UNIQUE,
  referred_email TEXT,
  referred_company_id UUID REFERENCES companies(id),
  status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'signed_up', 'active'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  converted_at TIMESTAMPTZ
);

ALTER TABLE broker_referrals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on broker_referrals"
  ON broker_referrals FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_broker_referrals_code ON broker_referrals(referral_code);
CREATE INDEX IF NOT EXISTS idx_broker_referrals_referrer ON broker_referrals(referrer_company_id);

-- === 039_pharmacy_asp.sql ===
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

-- === 040_provider_profile_address_contact.sql ===
-- Migration 040: Add practice_address and billing_contact to provider_profiles
-- Run in Supabase SQL Editor

ALTER TABLE provider_profiles
  ADD COLUMN IF NOT EXISTS practice_address TEXT,
  ADD COLUMN IF NOT EXISTS billing_contact TEXT;

-- === 041_data_versions.sql ===
-- Migration 041: data_versions table
-- Tracks freshness and metadata for all reference data sources

CREATE TABLE IF NOT EXISTS data_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  data_source text NOT NULL,
  version_label text,
  effective_from date,
  effective_to date,
  loaded_at timestamptz DEFAULT now(),
  next_update_due date,
  record_count integer,
  notes text
);

-- === 042_signal_events.sql ===
-- Migration 042: signal_events table
-- Privacy-first analytics — session_id only, no user_id linkage
--
-- For existing databases with old schema (user_id, device_type columns):
--   UPDATE signal_events SET user_id = NULL WHERE user_id IS NOT NULL;
--   ALTER TABLE signal_events DROP COLUMN IF EXISTS user_id;
--   ALTER TABLE signal_events DROP COLUMN IF EXISTS device_type;
--   ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS session_id text NOT NULL DEFAULT '';
--   ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS topic_slug text;
--   ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS element_id text;

CREATE TABLE IF NOT EXISTS signal_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id text NOT NULL,
  topic_slug text,
  event_type text NOT NULL,
  element_id text,
  event_data jsonb,
  created_at timestamptz DEFAULT now()
);

-- Ensure columns exist if table was created by an earlier migration (005)
ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS topic_slug text;
ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS session_id text;
ALTER TABLE signal_events ADD COLUMN IF NOT EXISTS element_id text;

CREATE INDEX IF NOT EXISTS idx_signal_events_type ON signal_events(event_type);
CREATE INDEX IF NOT EXISTS idx_signal_events_topic ON signal_events(topic_slug);
CREATE INDEX IF NOT EXISTS idx_signal_events_created ON signal_events(created_at);

-- RLS: service role only write
ALTER TABLE signal_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on signal_events"
  ON signal_events FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- === 043_claim_type_consensus_type.sql ===
-- Migration 043: Add claim_type and consensus_type to signal_claims
-- Foundation for methodology framework — every claim needs a type classification

ALTER TABLE signal_claims
  ADD COLUMN IF NOT EXISTS claim_type text
    CHECK (claim_type IS NULL OR claim_type IN (
      'efficacy', 'safety', 'institutional', 'values_embedded', 'foundational_values'
    ));

ALTER TABLE signal_claims
  ADD COLUMN IF NOT EXISTS consensus_type text
    CHECK (consensus_type IS NULL OR consensus_type IN (
      'strong_consensus', 'active_debate', 'manufactured_controversy', 'genuine_uncertainty'
    ));

-- === 043_signal_claim_classification.sql ===
-- 043_signal_claim_classification.sql
-- Add claim_type and consensus_type columns to signal_claims.
-- These classify each claim before scoring (Session S — methodology framework).

ALTER TABLE signal_claims
  ADD COLUMN IF NOT EXISTS claim_type TEXT,
  ADD COLUMN IF NOT EXISTS consensus_type TEXT;

-- Valid claim_type values
ALTER TABLE signal_claims
  ADD CONSTRAINT chk_claim_type CHECK (
    claim_type IS NULL OR claim_type IN (
      'efficacy',
      'safety',
      'institutional',
      'values_embedded',
      'foundational_values'
    )
  );

-- Valid consensus_type values
ALTER TABLE signal_claims
  ADD CONSTRAINT chk_consensus_type CHECK (
    consensus_type IS NULL OR consensus_type IN (
      'strong_consensus',
      'active_debate',
      'manufactured_controversy',
      'genuine_uncertainty'
    )
  );

-- === 044_signal_quality_review.sql ===
-- 044_signal_quality_review.sql
-- Add quality_review_status to signal_issues for topic review gate.
-- Topics must be approved before appearing publicly.

ALTER TABLE signal_issues
  ADD COLUMN IF NOT EXISTS quality_review_status TEXT DEFAULT 'pending';

ALTER TABLE signal_issues
  ADD CONSTRAINT chk_quality_review_status CHECK (
    quality_review_status IS NULL OR quality_review_status IN (
      'pending', 'approved', 'rejected'
    )
  );

-- Mark breast cancer topic as approved (existing topic)
UPDATE signal_issues
  SET quality_review_status = 'approved'
  WHERE slug = 'breast-cancer-therapies';

-- Reload PostgREST schema cache
SELECT pg_notify('pgrst', 'reload schema');

-- === 045_signal_cpt_mappings.sql ===
-- 045_signal_cpt_mappings.sql
-- CPT code to Signal topic mapping table.
-- Enables the Signal Intelligence API to connect billing codes to evidence.

CREATE TABLE IF NOT EXISTS signal_cpt_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cpt_code TEXT NOT NULL,
  topic_slug TEXT NOT NULL,
  relevance_score NUMERIC(3,2) CHECK (relevance_score >= 0 AND relevance_score <= 1),
  mapping_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_cpt_mappings_code
  ON signal_cpt_mappings(cpt_code);

CREATE INDEX IF NOT EXISTS idx_signal_cpt_mappings_slug
  ON signal_cpt_mappings(topic_slug);

-- === 046_seed_cpt_mappings.sql ===
-- 046_seed_cpt_mappings.sql
-- Seed CPT code to Signal topic mappings for the 20 highest-volume
-- Medicare CPT codes that map to existing Signal topics.

-- GLP-1 drugs (obesity/diabetes management)
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('99213', 'glp1-drugs', 0.70, 'Office visit level 3 — common for GLP-1 prescribing and management'),
('99214', 'glp1-drugs', 0.75, 'Office visit level 4 — complex medication management including GLP-1 titration'),
('99215', 'glp1-drugs', 0.65, 'Office visit level 5 — complex obesity/diabetes management'),
('96372', 'glp1-drugs', 0.90, 'Therapeutic injection, subcutaneous — GLP-1 agonist administration'),
('99211', 'glp1-drugs', 0.50, 'Office visit level 1 — nurse-led GLP-1 follow-up'),
('83036', 'glp1-drugs', 0.80, 'Hemoglobin A1c — primary monitoring for GLP-1 diabetes treatment'),
('80053', 'glp1-drugs', 0.60, 'Comprehensive metabolic panel — baseline/monitoring for GLP-1 therapy');

-- Breast cancer therapies
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('96413', 'breast-cancer-therapies', 0.95, 'Chemotherapy IV infusion first hour — CDK4/6 inhibitors, ADCs'),
('96415', 'breast-cancer-therapies', 0.90, 'Chemotherapy IV infusion each additional hour'),
('96417', 'breast-cancer-therapies', 0.85, 'Chemotherapy IV infusion each additional sequential infusion'),
('77263', 'breast-cancer-therapies', 0.80, 'Radiation treatment planning, complex — breast cancer RT'),
('19301', 'breast-cancer-therapies', 0.85, 'Mastectomy, partial — breast-conserving surgery'),
('38525', 'breast-cancer-therapies', 0.75, 'Biopsy or excision of lymph nodes — sentinel node biopsy'),
('88305', 'breast-cancer-therapies', 0.70, 'Surgical pathology level 4 — breast tissue examination');

-- Diet and breast cancer
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('97802', 'diet-and-breast-cancer-risk-prevention-and-recurrence', 0.85, 'Medical nutrition therapy initial — dietary counseling for cancer prevention'),
('97803', 'diet-and-breast-cancer-risk-prevention-and-recurrence', 0.85, 'Medical nutrition therapy subsequent — ongoing dietary management'),
('99401', 'diet-and-breast-cancer-risk-prevention-and-recurrence', 0.70, 'Preventive counseling 15 min — lifestyle/diet modification');

-- CAR-T cell therapy
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('0537T', 'car-t-cell-therapy', 0.95, 'CAR-T cell therapy, harvesting'),
('0538T', 'car-t-cell-therapy', 0.95, 'CAR-T cell therapy, preparation/infusion'),
('96413', 'car-t-cell-therapy', 0.70, 'Chemotherapy IV infusion — lymphodepleting conditioning'),
('36511', 'car-t-cell-therapy', 0.80, 'Therapeutic apheresis — T-cell collection');

-- CRISPR gene therapy
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('0537T', 'crispr-gene-therapy', 0.75, 'Cell therapy harvesting — applicable to gene-modified cell therapies'),
('0538T', 'crispr-gene-therapy', 0.75, 'Cell therapy preparation — applicable to gene-modified cell therapies'),
('81479', 'crispr-gene-therapy', 0.80, 'Unlisted molecular pathology procedure — genomic analysis for gene therapy eligibility');

-- MMR vaccine
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('90707', 'mmr-vaccine-autism', 0.95, 'MMR vaccine — measles, mumps, rubella live virus'),
('90710', 'mmr-vaccine-autism', 0.90, 'MMRV vaccine — measles, mumps, rubella, varicella'),
('90460', 'mmr-vaccine-autism', 0.70, 'Immunization admin first component — vaccine administration');

-- mRNA vaccine myocarditis
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('91300', 'mrna-vaccine-myocarditis', 0.95, 'Pfizer-BioNTech COVID-19 vaccine'),
('91301', 'mrna-vaccine-myocarditis', 0.95, 'Moderna COVID-19 vaccine'),
('93306', 'mrna-vaccine-myocarditis', 0.80, 'Echocardiography, complete — cardiac evaluation post-vaccine'),
('93000', 'mrna-vaccine-myocarditis', 0.75, 'Electrocardiogram, 12-lead — myocarditis screening'),
('93017', 'mrna-vaccine-myocarditis', 0.70, 'Cardiovascular stress test — cardiac follow-up');

-- Social media and teen mental health
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('90837', 'social-media-teen-mental-health', 0.80, 'Psychotherapy 60 min — adolescent mental health treatment'),
('90834', 'social-media-teen-mental-health', 0.80, 'Psychotherapy 45 min — adolescent mental health treatment'),
('90847', 'social-media-teen-mental-health', 0.75, 'Family psychotherapy with patient — social media impact counseling'),
('96127', 'social-media-teen-mental-health', 0.85, 'Brief emotional/behavioral assessment — PHQ-A, screen time assessment'),
('99213', 'social-media-teen-mental-health', 0.55, 'Office visit level 3 — adolescent wellness/mental health visit');

-- Health impacts of climate change
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('99281', 'health-impacts-of-climate-change', 0.60, 'ED visit level 1 — heat-related illness'),
('99283', 'health-impacts-of-climate-change', 0.65, 'ED visit level 3 — respiratory exacerbation from air quality'),
('94010', 'health-impacts-of-climate-change', 0.70, 'Spirometry — pulmonary function testing for climate-related respiratory');

-- === 047_payer_coverage_policy_sources.sql ===
-- 047_payer_coverage_policy_sources.sql
-- Add payer coverage policy test sources to mmr-vaccine-autism topic.

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT
  id,
  'UnitedHealthcare Coverage Policy: Childhood Immunizations',
  'https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/childhood-immunizations.pdf',
  'payer_coverage_policy',
  '2025-01-15',
  'UnitedHealthcare covers all ACIP-recommended childhood immunizations including MMR vaccine without prior authorization. Coverage applies to all plan types. No medical necessity review required for standard immunization schedule.',
  '{"slug": "uhc-childhood-immunizations", "payer": "UnitedHealthcare", "policy_type": "medical", "key_findings": ["MMR vaccine covered without prior auth", "ACIP schedule followed for all plan types", "No exemptions for non-medical reasons"]}'::jsonb
FROM signal_issues WHERE slug = 'mmr-vaccine-autism';

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT
  id,
  'Aetna Clinical Policy Bulletin: Vaccines and Toxoids',
  'https://www.aetna.com/cpb/medical/data/1_99/0070.html',
  'payer_coverage_policy',
  '2025-03-01',
  'Aetna considers all ACIP-recommended vaccines medically necessary. MMR vaccine is covered for all age-appropriate members. Aetna does not consider the discredited Wakefield study or anti-vaccine claims as valid basis for coverage denial or alternative scheduling.',
  '{"slug": "aetna-vaccines-toxoids", "payer": "Aetna", "policy_type": "clinical_policy_bulletin", "key_findings": ["MMR covered as medically necessary", "ACIP schedule is the coverage standard", "Wakefield study explicitly discredited in policy"]}'::jsonb
FROM signal_issues WHERE slug = 'mmr-vaccine-autism';

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT
  id,
  'Anthem Blue Cross: Preventive Care and Immunization Coverage',
  'https://www.anthem.com/preventive-care',
  'payer_coverage_policy',
  '2024-09-15',
  'Anthem covers preventive immunizations at 100% with no cost sharing when administered by in-network providers, in accordance with ACIP recommendations. MMR vaccination is included in standard preventive benefits for children and adults without prior immunity.',
  '{"slug": "anthem-preventive-immunizations", "payer": "Anthem Blue Cross", "policy_type": "preventive_care", "key_findings": ["100% coverage for ACIP-recommended vaccines", "No cost sharing for in-network administration", "MMR included in standard preventive benefits"]}'::jsonb
FROM signal_issues WHERE slug = 'mmr-vaccine-autism';

-- === 048_provider_appeal_outcomes.sql ===
-- 048_provider_appeal_outcomes.sql
-- Track appeal outcomes to build the data flywheel.

CREATE TABLE IF NOT EXISTS provider_appeal_outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appeal_id UUID REFERENCES provider_appeals(id),
  claim_id TEXT,
  cpt_code TEXT,
  denial_code TEXT,
  payer TEXT,
  signal_topic_slug TEXT,
  appeal_submitted_at TIMESTAMPTZ,
  outcome TEXT CHECK (outcome IN ('pending', 'won', 'lost', 'partial')),
  outcome_recorded_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_appeal_outcomes_appeal
  ON provider_appeal_outcomes(appeal_id);

CREATE INDEX IF NOT EXISTS idx_appeal_outcomes_outcome
  ON provider_appeal_outcomes(outcome);

-- === 049_platform_cases.sql ===
-- 049_platform_cases.sql
-- Unified case tracking for Provider appeals and Health disputes.

CREATE TABLE IF NOT EXISTS platform_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product TEXT NOT NULL,
  user_id UUID,
  case_type TEXT,
  cpt_code TEXT,
  denial_code TEXT,
  payer TEXT,
  signal_topic_slug TEXT,
  signal_score FLOAT,
  description TEXT,
  status TEXT DEFAULT 'open' CHECK (status IN ('open','won','lost','partial','withdrawn')),
  opened_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  reminder_sent_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_platform_cases_product ON platform_cases(product);
CREATE INDEX IF NOT EXISTS idx_platform_cases_user ON platform_cases(user_id);
CREATE INDEX IF NOT EXISTS idx_platform_cases_status ON platform_cases(status);
CREATE INDEX IF NOT EXISTS idx_platform_cases_opened ON platform_cases(opened_at);

-- === 050_provider_appeal_letters.sql ===
-- Migration 050: provider_appeal_letters table
-- Persists generated appeal letters for reuse

CREATE TABLE IF NOT EXISTS provider_appeal_letters (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID,
  payer TEXT NOT NULL,
  denial_code TEXT NOT NULL,
  cpt_code TEXT,
  letter_text TEXT NOT NULL,
  signal_score FLOAT,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_appeal_letters_lookup
  ON provider_appeal_letters (user_id, payer, denial_code, cpt_code);

-- === 051_add_expired_plan.sql ===
-- MIGRATION 051: Add 'expired' to companies.plan CHECK constraint
-- Run in Supabase SQL Editor

ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_plan_check;
ALTER TABLE companies ADD CONSTRAINT companies_plan_check
  CHECK (plan IN ('free', 'trial', 'pro', 'read_only', 'cancelled', 'expired'));

-- === 052_sent_trial_reminder.sql ===
-- Migration 052: Add sent_trial_reminder flag to companies table
-- Prevents duplicate trial expiry reminder emails
ALTER TABLE companies ADD COLUMN IF NOT EXISTS sent_trial_reminder BOOLEAN DEFAULT FALSE;

