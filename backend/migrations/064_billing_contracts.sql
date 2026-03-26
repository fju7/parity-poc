-- Migration 064: billing_contracts — contract library for billing companies
-- Session BL-10

CREATE TABLE IF NOT EXISTS billing_contracts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    practice_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    payer_name text NOT NULL,
    effective_date date,
    expiry_date date,
    version integer NOT NULL DEFAULT 1,
    is_current boolean NOT NULL DEFAULT true,
    file_content text,
    filename text,
    file_size integer,
    analysis_result jsonb,
    analyzed_at timestamptz,
    uploaded_by_email text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE billing_contracts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_contracts_service_role"
    ON billing_contracts FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_billing_contracts_company
    ON billing_contracts(billing_company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_billing_contracts_practice
    ON billing_contracts(practice_id, payer_name, is_current);
