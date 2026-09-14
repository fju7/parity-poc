-- Migration 080: the frozen publication record and the re-check results,
-- where the site can read them. Phase 3 design §6. Not signal_*; no
-- foreign key to any frozen table (REFERENCES would install triggers on it).
-- Public read (the page renders from these), service-role writes only.
-- Idempotent.

CREATE TABLE IF NOT EXISTS topic_publications (
  slug                  TEXT NOT NULL,
  publish_id            TEXT NOT NULL,
  published_at          TIMESTAMPTZ NOT NULL,
  published_by          JSONB NOT NULL,
  gate_version          JSONB NOT NULL,
  record                JSONB NOT NULL,
  supported_claim_ids   UUID[] NOT NULL DEFAULT '{}',
  surviving_source_ids  UUID[] NOT NULL DEFAULT '{}',
  flipped               BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (slug, publish_id)
);
CREATE INDEX IF NOT EXISTS topic_publications_latest_idx ON topic_publications (slug, published_at DESC);

CREATE TABLE IF NOT EXISTS topic_rechecks (
  slug        TEXT NOT NULL,
  run_id      TEXT NOT NULL,
  run_at      TIMESTAMPTZ NOT NULL,
  kind        TEXT NOT NULL CHECK (kind IN ('status', 'bindings')),
  outcomes    JSONB NOT NULL,
  flags       JSONB NOT NULL DEFAULT '[]',
  exit_ok     BOOLEAN NOT NULL,
  PRIMARY KEY (slug, run_id)
);
CREATE INDEX IF NOT EXISTS topic_rechecks_latest_idx ON topic_rechecks (slug, run_at DESC);

COMMENT ON TABLE topic_publications IS
  'The frozen record written by scripts/publish_topic.py: what every claim of a published '
  'topic rested on, on the day. The page filters claims and sources by the arrays here; '
  'signal_issues.status opens the door, this says what stands inside it.';
COMMENT ON TABLE topic_rechecks IS
  'Results of the weekly status check and the monthly binding re-check. flags[] carries the '
  'per-claim / per-source markers the page renders; nothing here un-publishes anything.';

ALTER TABLE topic_publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic_rechecks ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON topic_publications, topic_rechecks FROM PUBLIC, anon, authenticated;
GRANT SELECT ON topic_publications, topic_rechecks TO anon, authenticated;
GRANT ALL ON topic_publications, topic_rechecks TO service_role;
DROP POLICY IF EXISTS "Public read topic_publications" ON topic_publications;
CREATE POLICY "Public read topic_publications" ON topic_publications FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS "Public read topic_rechecks" ON topic_rechecks;
CREATE POLICY "Public read topic_rechecks" ON topic_rechecks FOR SELECT TO anon, authenticated USING (true);
