-- Migration 058: billing_835_jobs — batch 835 ingestion job tracking
-- Session BL-3b

CREATE TABLE IF NOT EXISTS billing_835_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    practice_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    filename text NOT NULL,
    status text DEFAULT 'queued',
    file_content text,
    result_json jsonb,
    error_message text,
    line_count integer,
    denial_rate numeric(5,2),
    total_billed numeric(12,2),
    uploaded_by_email text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

ALTER TABLE billing_835_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "billing_835_jobs_service_role"
    ON billing_835_jobs
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Index for fast lookups by billing company
CREATE INDEX IF NOT EXISTS idx_billing_835_jobs_company
    ON billing_835_jobs(billing_company_id, created_at DESC);
