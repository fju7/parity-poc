-- Migration 053: Signal Denial Playbook + Provider Denial Patterns
-- Created: 2026-03-23

-- 1. signal_denial_playbook — pre-computed evidence lookups for denial codes + CPT combos
CREATE TABLE IF NOT EXISTS signal_denial_playbook (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    denial_code TEXT NOT NULL,
    cpt_code TEXT NOT NULL,
    appeal_strength TEXT NOT NULL DEFAULT 'weak',
    payer_analytical_path TEXT,
    challenging_evidence_summary TEXT,
    recommended_claims JSONB DEFAULT '[]',
    signal_topic_slug TEXT,
    signal_issue_id UUID REFERENCES signal_issues(id) ON DELETE SET NULL,
    last_updated TIMESTAMPTZ DEFAULT now(),
    UNIQUE(denial_code, cpt_code)
);

-- 2. provider_denial_patterns — aggregated denial frequency tracking
CREATE TABLE IF NOT EXISTS provider_denial_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    denial_code TEXT NOT NULL,
    cpt_code TEXT NOT NULL,
    payer TEXT,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    total_value_at_risk NUMERIC(12,2) NOT NULL DEFAULT 0,
    first_seen TIMESTAMPTZ DEFAULT now(),
    last_seen TIMESTAMPTZ DEFAULT now(),
    signal_coverage BOOLEAN NOT NULL DEFAULT false,
    topic_request_created BOOLEAN NOT NULL DEFAULT false,
    UNIQUE(denial_code, cpt_code, payer)
);

-- 3. RLS policies

-- signal_denial_playbook: service_role full access, public SELECT
ALTER TABLE signal_denial_playbook ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access" ON signal_denial_playbook
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "public_read" ON signal_denial_playbook
    FOR SELECT TO anon, authenticated USING (true);

-- provider_denial_patterns: service_role full access only
ALTER TABLE provider_denial_patterns ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access" ON provider_denial_patterns
    FOR ALL TO service_role USING (true) WITH CHECK (true);
