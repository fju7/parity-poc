-- Migration 057: Billing schema updates for BL-2
-- Session BL-2b

-- 1. Allow 'billing' in companies.type CHECK constraint
ALTER TABLE companies DROP CONSTRAINT companies_type_check;
ALTER TABLE companies ADD CONSTRAINT companies_type_check
  CHECK (type IN ('employer', 'broker', 'provider', 'health', 'signal', 'billing'));

-- 2. billing_company_users: drop auth.users FK requirement, add email-based columns
ALTER TABLE billing_company_users ALTER COLUMN user_id DROP NOT NULL;

ALTER TABLE billing_company_users
  ADD COLUMN IF NOT EXISTS email text,
  ADD COLUMN IF NOT EXISTS full_name text,
  ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';
