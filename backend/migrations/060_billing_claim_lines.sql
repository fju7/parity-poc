-- Migration 060: billing_claim_lines — denormalized claim lines for cross-file recovery tracking
-- Session BL-7r

CREATE TABLE IF NOT EXISTS billing_claim_lines (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    practice_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    job_id uuid NOT NULL REFERENCES billing_835_jobs(id) ON DELETE CASCADE,
    analysis_id uuid REFERENCES provider_analyses(id) ON DELETE SET NULL,
    payer_name text,
    claim_number text,
    cpt_code text,
    date_of_service date,
    adjudication_date date,
    billed_amount numeric(12,2),
    paid_amount numeric(12,2),
    status text,
    denial_codes text[],
    created_at timestamptz DEFAULT now()
);

ALTER TABLE billing_claim_lines ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_claim_lines_service_role"
    ON billing_claim_lines FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_claim_lines_match
    ON billing_claim_lines(practice_id, claim_number, cpt_code, date_of_service);

CREATE INDEX IF NOT EXISTS idx_claim_lines_company
    ON billing_claim_lines(billing_company_id, created_at DESC);
