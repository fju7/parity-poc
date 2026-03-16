-- Migration 041: data_versions table
-- Tracks freshness and metadata for all reference data sources

CREATE TABLE IF NOT EXISTS data_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  data_source text NOT NULL,
  version_label text,
  effective_from date,
  effective_to date,
  loaded_at timestamptz DEFAULT now(),
  next_update_due date,
  record_count integer,
  notes text
);
