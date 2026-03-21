-- Migration 003: Broker Auth Migration
-- Migrates broker_accounts → companies + company_users unified auth system
-- Run this in Supabase SQL Editor AFTER deploying the backend code

-- ============================================================
-- Step 1: Add broker-specific columns to companies
-- ============================================================
ALTER TABLE companies ADD COLUMN IF NOT EXISTS broker_client_limit int DEFAULT 10;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS broker_commission_rate numeric DEFAULT 0.20;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS phone text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS referral_code text;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS logo_url text;

-- ============================================================
-- Step 2: Migrate broker_accounts → companies (type = 'broker')
-- Each unique firm_name becomes a company
-- ============================================================
INSERT INTO companies (id, name, type, plan, stripe_customer_id, stripe_subscription_id, created_at, phone, referral_code)
SELECT
  gen_random_uuid(),
  ba.firm_name,
  'broker',
  COALESCE(ba.plan, 'starter'),
  ba.stripe_customer_id,
  ba.stripe_subscription_id,
  ba.created_at,
  ba.phone,
  ba.referral_code
FROM broker_accounts ba
WHERE ba.is_active = true
ON CONFLICT DO NOTHING;

-- ============================================================
-- Step 3: Migrate broker users → company_users as admins
-- ============================================================
INSERT INTO company_users (id, company_id, email, full_name, role, status, created_at)
SELECT
  gen_random_uuid(),
  c.id,
  ba.email,
  COALESCE(ba.contact_name, ba.name, ba.email),
  'admin',
  'active',
  ba.created_at
FROM broker_accounts ba
JOIN companies c ON c.name = ba.firm_name AND c.type = 'broker'
WHERE ba.is_active = true
ON CONFLICT DO NOTHING;

-- ============================================================
-- Step 4: Create broker_commissions table
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
-- Step 5: Add referral tracking column to company_invitations
-- ============================================================
ALTER TABLE company_invitations ADD COLUMN IF NOT EXISTS invitation_type text DEFAULT 'team_invite';
ALTER TABLE company_invitations ADD COLUMN IF NOT EXISTS referring_company_id uuid REFERENCES companies(id);

-- ============================================================
-- Step 6: Indexes for broker_commissions
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_broker_commissions_broker ON broker_commissions(broker_company_id);
CREATE INDEX IF NOT EXISTS idx_broker_commissions_employer ON broker_commissions(employer_company_id);
CREATE INDEX IF NOT EXISTS idx_broker_commissions_status ON broker_commissions(status);

-- ============================================================
-- Verification queries (run after migration to spot-check)
-- ============================================================
-- SELECT count(*) FROM companies WHERE type = 'broker';
-- SELECT count(*) FROM company_users cu JOIN companies c ON cu.company_id = c.id WHERE c.type = 'broker';
-- SELECT c.name, cu.email, cu.role FROM companies c JOIN company_users cu ON cu.company_id = c.id WHERE c.type = 'broker' LIMIT 10;
