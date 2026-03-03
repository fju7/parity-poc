-- Migration 007: Create signal_topic_requests table
-- Allows premium users to request new topics for Parity Signal

CREATE TABLE IF NOT EXISTS signal_topic_requests (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid NOT NULL,
  topic_name text NOT NULL,
  description text NOT NULL,
  reference_urls text[] DEFAULT '{}',
  status text DEFAULT 'submitted',
  created_at timestamptz DEFAULT now()
);

ALTER TABLE signal_topic_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own requests"
  ON signal_topic_requests FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own requests"
  ON signal_topic_requests FOR SELECT
  USING (auth.uid() = user_id);
