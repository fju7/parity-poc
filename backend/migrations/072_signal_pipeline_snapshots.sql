-- Migration: store the change-detection baseline in Postgres, not on a laptop.
--
-- WHY
-- ---
-- detect_changes.py (pipeline step 7) compares the current state of a topic
-- against a snapshot of the previous run and writes any differences to
-- signal_evidence_updates. That table and that script are the changelog.
--
-- The snapshot was written to backend/data/signal/pipeline_snapshot_{slug}.json
-- — a path that is gitignored and therefore exists only on whichever machine
-- last ran the pipeline. Anywhere else (a fresh clone, CI, a second laptop,
-- a server) the script finds no snapshot, concludes it is the first run,
-- writes the baseline and exits without detecting anything.
--
-- The result: signal_evidence_updates has stayed empty, and the landing page
-- has been publishing "0 Updates This Month" — accurately.
--
-- This table gives the baseline the same durability as the data it describes.
-- One row per run per topic; the newest row is the comparison baseline.
-- History is kept rather than overwritten so a run can be audited or replayed.
--
-- Idempotent. Run via the Supabase SQL editor or CLI.

CREATE TABLE IF NOT EXISTS signal_pipeline_snapshots (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id    UUID NOT NULL REFERENCES signal_issues(id) ON DELETE CASCADE,
  issue_slug  TEXT NOT NULL,
  state_json  JSONB NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The only hot query: "newest snapshot for this topic".
CREATE INDEX IF NOT EXISTS signal_pipeline_snapshots_slug_time_idx
  ON signal_pipeline_snapshots (issue_slug, captured_at DESC);

COMMENT ON TABLE signal_pipeline_snapshots IS
  'Per-run state snapshots for a Signal topic. detect_changes.py reads the '
  'newest row as its comparison baseline and appends a new row after each run. '
  'Replaces a gitignored local JSON file that made change detection unusable '
  'from any machine other than the one that last ran the pipeline.';

-- Written and read only by the pipeline via the service key. Unlike the
-- signal_* content tables (public-read per migration 006), this holds internal
-- pipeline state with no reader-facing value, so it is service-role only.
ALTER TABLE signal_pipeline_snapshots ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON signal_pipeline_snapshots FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, DELETE ON signal_pipeline_snapshots TO service_role;
