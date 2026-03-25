-- Migration 055: Parity Billing — four new billing company tables
-- Session BL-1b

-- 1. billing_companies — top-level billing/RCM company entity
CREATE TABLE IF NOT EXISTS billing_companies (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name text NOT NULL,
    logo_url text,
    contact_email text NOT NULL,
    subscription_tier text DEFAULT 'trial',
    stripe_customer_id text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE billing_companies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_companies_service_role"
    ON billing_companies
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 2. billing_company_users — users within a billing company
CREATE TABLE IF NOT EXISTS billing_company_users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role text DEFAULT 'analyst',
    assigned_practices uuid[] DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE billing_company_users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_company_users_service_role"
    ON billing_company_users
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 3. billing_company_practices — links billing companies to practices
CREATE TABLE IF NOT EXISTS billing_company_practices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    practice_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    active boolean DEFAULT true,
    added_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE billing_company_practices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_company_practices_service_role"
    ON billing_company_practices
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- 4. billing_company_subscriptions — Stripe subscriptions for billing companies
CREATE TABLE IF NOT EXISTS billing_company_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    stripe_sub_id text,
    tier text DEFAULT 'trial',
    practice_count_limit integer DEFAULT 10,
    status text DEFAULT 'active',
    trial_ends_at timestamptz,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE billing_company_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_company_subscriptions_service_role"
    ON billing_company_subscriptions
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
