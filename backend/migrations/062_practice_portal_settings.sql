-- Migration 062: practice_portal_settings — per-practice portal configuration
-- Session BL-9

CREATE TABLE IF NOT EXISTS practice_portal_settings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    practice_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    portal_enabled boolean DEFAULT false,
    portal_contact_email text,
    show_denial_summary boolean DEFAULT true,
    show_payer_performance boolean DEFAULT true,
    show_appeal_roi boolean DEFAULT false,
    show_generate_report boolean DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(billing_company_id, practice_id)
);

ALTER TABLE practice_portal_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "practice_portal_settings_service_role"
    ON practice_portal_settings FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');
