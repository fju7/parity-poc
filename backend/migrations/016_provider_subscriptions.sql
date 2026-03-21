-- Migration 016: Provider Subscriptions table
-- Stores audit-to-subscription conversions for ongoing monitoring ($300/month)

CREATE TABLE IF NOT EXISTS provider_subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    practice_name TEXT NOT NULL,
    practice_specialty TEXT DEFAULT '',
    num_providers INTEGER DEFAULT 1,
    billing_company TEXT DEFAULT '',
    contact_email TEXT NOT NULL,
    user_id UUID,
    payer_data JSONB DEFAULT '[]'::jsonb,
    remittance_data JSONB DEFAULT '[]'::jsonb,
    source_audit_id UUID REFERENCES provider_audits(id),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due')),
    monthly_analyses JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    canceled_at TIMESTAMPTZ
);

-- Indexes
-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_user_id ON provider_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_contact_email ON provider_subscriptions(contact_email);
CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_source_audit ON provider_subscriptions(source_audit_id);
CREATE INDEX IF NOT EXISTS idx_provider_subscriptions_stripe_sub ON provider_subscriptions(stripe_subscription_id);

-- Enable RLS
ALTER TABLE provider_subscriptions ENABLE ROW LEVEL SECURITY;

-- Service role: full access
CREATE POLICY "service_role_full_access" ON provider_subscriptions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Authenticated users: read own rows (by user_id or contact_email)
CREATE POLICY "users_read_own_subscriptions" ON provider_subscriptions
    FOR SELECT
    USING (
        auth.uid() = user_id
        OR contact_email = (SELECT email FROM auth.users WHERE id = auth.uid())
    );
