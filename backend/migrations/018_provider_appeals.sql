-- Create provider_appeals table for tracking appeal letters
CREATE TABLE IF NOT EXISTS provider_appeals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  subscription_id UUID REFERENCES provider_subscriptions(id),
  audit_id UUID REFERENCES provider_audits(id),
  claim_id TEXT NOT NULL DEFAULT '',
  payer_name TEXT NOT NULL DEFAULT '',
  denial_code TEXT NOT NULL DEFAULT '',
  cpt_code TEXT NOT NULL DEFAULT '',
  amount DECIMAL(12,2) DEFAULT 0.00,
  letter_text TEXT,
  letter_html TEXT,
  appeal_strength TEXT,
  cms_references JSONB DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'drafted',
  appeal_generated_at TIMESTAMPTZ DEFAULT NOW(),
  outcome_amount DECIMAL(12,2),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups by user
CREATE INDEX IF NOT EXISTS idx_provider_appeals_user_id ON provider_appeals(user_id);

-- Index for subscription-based queries
CREATE INDEX IF NOT EXISTS idx_provider_appeals_subscription_id ON provider_appeals(subscription_id);

-- Index for audit-based queries
CREATE INDEX IF NOT EXISTS idx_provider_appeals_audit_id ON provider_appeals(audit_id);

-- Enable RLS
ALTER TABLE provider_appeals ENABLE ROW LEVEL SECURITY;

-- RLS policy: users can only see their own appeals
CREATE POLICY "Users can view own appeals" ON provider_appeals
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own appeals" ON provider_appeals
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own appeals" ON provider_appeals
  FOR UPDATE USING (auth.uid() = user_id);

-- Service role bypass for backend operations
CREATE POLICY "Service role full access" ON provider_appeals
  FOR ALL USING (auth.role() = 'service_role');
