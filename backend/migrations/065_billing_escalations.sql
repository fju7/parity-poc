-- Migration 065: billing_escalations + billing_escalation_practices
-- Session BL-11 — cross-practice escalation tracking

CREATE TABLE IF NOT EXISTS billing_escalations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    payer_name text NOT NULL,
    denial_code text NOT NULL,
    denial_description text,
    status text NOT NULL DEFAULT 'open',
    affected_practice_count integer,
    total_denied_amount numeric(12,2),
    evidence_summary jsonb,
    resolution_notes text,
    recovered_amount numeric(12,2),
    created_by_email text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS billing_escalation_practices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    escalation_id uuid NOT NULL REFERENCES billing_escalations(id) ON DELETE CASCADE,
    practice_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    denied_amount numeric(12,2),
    claim_count integer,
    sample_claim_numbers text[],
    created_at timestamptz DEFAULT now(),
    UNIQUE(escalation_id, practice_id)
);

ALTER TABLE billing_escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_escalation_practices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_escalations_service_role"
    ON billing_escalations FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "billing_escalation_practices_service_role"
    ON billing_escalation_practices FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_escalations_company
    ON billing_escalations(billing_company_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_escalation_practices_escalation
    ON billing_escalation_practices(escalation_id);
