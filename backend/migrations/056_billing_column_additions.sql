-- Migration 056: Parity Billing — column additions to existing tables
-- Session BL-1c
-- Depends on: 055_billing_company_tables.sql (billing_companies must exist for FK)

-- 1. Add account_type to companies table to distinguish practice vs billing
ALTER TABLE companies ADD COLUMN IF NOT EXISTS account_type text NOT NULL DEFAULT 'practice';

-- 2. Add billing_company_id FK to provider_analyses
ALTER TABLE provider_analyses ADD COLUMN IF NOT EXISTS billing_company_id uuid REFERENCES billing_companies(id);

-- 3. Add billing_company_id FK to provider_contracts
ALTER TABLE provider_contracts ADD COLUMN IF NOT EXISTS billing_company_id uuid REFERENCES billing_companies(id);
