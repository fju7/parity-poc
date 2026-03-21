-- Migration 025 (backfill): Add company_id to tables created after 001
-- These ALTERs were originally in 001_unified_auth.sql but depend on
-- tables created in migrations 020-024. Moved here to fix fresh-database ordering.

-- Add company_id to existing tables
ALTER TABLE employer_subscriptions ADD COLUMN IF NOT EXISTS company_id uuid REFERENCES companies(id);
ALTER TABLE employer_claims_uploads ADD COLUMN IF NOT EXISTS company_id uuid REFERENCES companies(id);
ALTER TABLE broker_employer_links ADD COLUMN IF NOT EXISTS employer_company_id uuid REFERENCES companies(id);

-- Add product column to otp_codes
ALTER TABLE otp_codes ADD COLUMN IF NOT EXISTS product text DEFAULT 'broker';
