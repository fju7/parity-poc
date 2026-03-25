-- Migration 057: Add email/full_name/status columns to billing_company_users
-- Session BL-2b
-- The existing user_id FK references auth.users which we don't use.
-- We use email-based auth like all other products.

ALTER TABLE billing_company_users ALTER COLUMN user_id DROP NOT NULL;

ALTER TABLE billing_company_users
  ADD COLUMN IF NOT EXISTS email text,
  ADD COLUMN IF NOT EXISTS full_name text,
  ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';
