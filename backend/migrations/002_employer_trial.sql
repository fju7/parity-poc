-- MIGRATION 002: Employer trial and simplified pricing
-- Run in Supabase SQL Editor

ALTER TABLE companies ADD COLUMN IF NOT EXISTS plan text DEFAULT 'free'
  CHECK (plan IN ('free', 'trial', 'pro', 'read_only', 'cancelled'));
ALTER TABLE companies ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS stripe_customer_id text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS stripe_subscription_id text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS plan_locked_until timestamptz;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS trial_started_at timestamptz;
