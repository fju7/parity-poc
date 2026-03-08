-- Employer subscriptions: manages employer tier and Stripe billing
CREATE TABLE IF NOT EXISTS employer_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  company_name TEXT,
  employee_count INTEGER,
  tier TEXT NOT NULL,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  status TEXT DEFAULT 'active',
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE employer_subscriptions ENABLE ROW LEVEL SECURITY;

-- Allow service role full access
CREATE POLICY "Service role full access on employer_subscriptions"
  ON employer_subscriptions FOR ALL
  USING (auth.role() = 'service_role');
