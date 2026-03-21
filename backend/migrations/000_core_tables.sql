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
