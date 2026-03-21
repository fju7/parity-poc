-- Migration 012: provider_audits table for multi-payer batch audit workflow
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS provider_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    practice_name TEXT NOT NULL,
    practice_specialty TEXT,
    num_providers INTEGER DEFAULT 1,
    billing_company TEXT,
    contact_email TEXT NOT NULL,
    payer_list JSONB DEFAULT '[]'::jsonb,
    -- Array of {payer_name, fee_schedule_method, fee_schedule_data, code_count}
    analysis_ids JSONB DEFAULT '[]'::jsonb,
    -- Array of provider_analyses UUIDs
    status TEXT DEFAULT 'submitted' CHECK (status IN ('submitted', 'processing', 'review', 'delivered')),
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    follow_up_sent BOOLEAN DEFAULT false
);

-- Enable RLS
ALTER TABLE provider_audits ENABLE ROW LEVEL SECURITY;

-- Service role full access
CREATE POLICY "service_role_full_access" ON provider_audits
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Authenticated users can read their own audits
CREATE POLICY "users_read_own_audits" ON provider_audits
    FOR SELECT
    USING (
        auth.uid() = user_id
        OR contact_email = (SELECT email FROM auth.users WHERE id = auth.uid())
    );

-- Authenticated users can insert their own audits
CREATE POLICY "users_insert_own_audits" ON provider_audits
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Index for common queries
-- removed: user_id superseded by company_id in 000_core_tables.sql
-- CREATE INDEX IF NOT EXISTS idx_provider_audits_user_id ON provider_audits(user_id);
CREATE INDEX IF NOT EXISTS idx_provider_audits_status ON provider_audits(status);
CREATE INDEX IF NOT EXISTS idx_provider_audits_contact_email ON provider_audits(contact_email);
