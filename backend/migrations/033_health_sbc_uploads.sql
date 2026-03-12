-- Migration 033: health_sbc_uploads table for Parity Health SBC analysis
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS health_sbc_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT,
  plan_name TEXT,
  plan_year TEXT,
  sbc_data JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for session lookup
CREATE INDEX IF NOT EXISTS idx_health_sbc_uploads_session
  ON health_sbc_uploads (session_id);

-- RLS: allow service role full access
ALTER TABLE health_sbc_uploads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_all" ON health_sbc_uploads
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
