-- Migration 024: Broker Portal
-- Tables for broker accounts, employer links, and custom OTP codes

-- ============================================================
-- 1. broker_accounts — registered broker profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS broker_accounts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    firm_name   TEXT NOT NULL,
    contact_name TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE broker_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on broker_accounts"
    ON broker_accounts FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================
-- 2. broker_employer_links — many-to-many between brokers and employers
-- ============================================================
CREATE TABLE IF NOT EXISTS broker_employer_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    broker_email    TEXT NOT NULL REFERENCES broker_accounts(email) ON DELETE CASCADE,
    employer_email  TEXT NOT NULL,
    linked_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE(broker_email, employer_email)
);

-- RLS
ALTER TABLE broker_employer_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on broker_employer_links"
    ON broker_employer_links FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================
-- 3. otp_codes — custom OTP for broker auth (not Supabase auth)
-- ============================================================
CREATE TABLE IF NOT EXISTS otp_codes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    code        TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE otp_codes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on otp_codes"
    ON otp_codes FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Index for quick lookup
CREATE INDEX IF NOT EXISTS idx_otp_codes_email_code ON otp_codes(email, code);

-- Index for broker links lookup
CREATE INDEX IF NOT EXISTS idx_broker_employer_links_broker ON broker_employer_links(broker_email);
CREATE INDEX IF NOT EXISTS idx_broker_employer_links_employer ON broker_employer_links(employer_email);
