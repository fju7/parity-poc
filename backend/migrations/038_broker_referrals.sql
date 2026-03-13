-- Migration 038: Broker referral tracking
CREATE TABLE IF NOT EXISTS broker_referrals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  referrer_email TEXT NOT NULL,
  referral_code TEXT NOT NULL UNIQUE,
  referred_email TEXT,
  referred_company_id UUID REFERENCES companies(id),
  status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'signed_up', 'active'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  converted_at TIMESTAMPTZ
);

ALTER TABLE broker_referrals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on broker_referrals"
  ON broker_referrals FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_broker_referrals_code ON broker_referrals(referral_code);
CREATE INDEX IF NOT EXISTS idx_broker_referrals_referrer ON broker_referrals(referrer_company_id);
