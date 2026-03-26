-- Migration 059: analyst_practice_assignments — role-scoped practice visibility
-- Session BL-6
-- Uses billing_company_users(id) as FK since we use email-based auth, not auth.users

CREATE TABLE IF NOT EXISTS analyst_practice_assignments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_company_id uuid NOT NULL REFERENCES billing_companies(id) ON DELETE CASCADE,
    analyst_user_id uuid NOT NULL REFERENCES billing_company_users(id) ON DELETE CASCADE,
    practice_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    assigned_by_email text,
    created_at timestamptz DEFAULT now(),
    UNIQUE(analyst_user_id, practice_id)
);

ALTER TABLE analyst_practice_assignments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "analyst_assignments_service_role"
    ON analyst_practice_assignments
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_analyst_assignments_user
    ON analyst_practice_assignments(analyst_user_id, billing_company_id);
