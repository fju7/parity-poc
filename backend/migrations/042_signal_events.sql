-- Migration 042: signal_events table
-- Privacy-first analytics — session_id only, no user_id linkage

CREATE TABLE IF NOT EXISTS signal_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id text NOT NULL,
  topic_slug text,
  event_type text NOT NULL,
  element_id text,
  event_data jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_events_type ON signal_events(event_type);
CREATE INDEX IF NOT EXISTS idx_signal_events_topic ON signal_events(topic_slug);
CREATE INDEX IF NOT EXISTS idx_signal_events_created ON signal_events(created_at);

-- RLS: service role only write
ALTER TABLE signal_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on signal_events"
  ON signal_events FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
