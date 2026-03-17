-- 045_signal_cpt_mappings.sql
-- CPT code to Signal topic mapping table.
-- Enables the Signal Intelligence API to connect billing codes to evidence.

CREATE TABLE IF NOT EXISTS signal_cpt_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cpt_code TEXT NOT NULL,
  topic_slug TEXT NOT NULL,
  relevance_score NUMERIC(3,2) CHECK (relevance_score >= 0 AND relevance_score <= 1),
  mapping_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_cpt_mappings_code
  ON signal_cpt_mappings(cpt_code);

CREATE INDEX IF NOT EXISTS idx_signal_cpt_mappings_slug
  ON signal_cpt_mappings(topic_slug);
