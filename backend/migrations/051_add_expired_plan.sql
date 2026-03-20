-- MIGRATION 051: Add 'expired' to companies.plan CHECK constraint
-- Run in Supabase SQL Editor

ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_plan_check;
ALTER TABLE companies ADD CONSTRAINT companies_plan_check
  CHECK (plan IN ('free', 'trial', 'pro', 'read_only', 'cancelled', 'expired'));
