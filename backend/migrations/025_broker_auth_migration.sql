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
