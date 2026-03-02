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
