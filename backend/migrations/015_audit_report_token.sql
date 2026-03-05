ALTER TABLE provider_audits ADD COLUMN IF NOT EXISTS report_token UUID;
CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_report_token ON provider_audits (report_token) WHERE report_token IS NOT NULL;
