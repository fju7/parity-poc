-- 011_four_tier_subscriptions.sql
-- Add usage tracking columns to signal_subscriptions and update
-- signal_topic_requests for the four-tier subscription model.
-- Run in Supabase SQL Editor.

-- Usage tracking columns on signal_subscriptions
ALTER TABLE signal_subscriptions
  ADD COLUMN IF NOT EXISTS qa_questions_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS qa_reset_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS topic_requests_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS topic_requests_reset_at TIMESTAMPTZ DEFAULT NOW();

-- Add new columns to signal_topic_requests for Claude-parsed fields
-- (table already exists from migration 007)
ALTER TABLE signal_topic_requests
  ADD COLUMN IF NOT EXISTS raw_request TEXT,
  ADD COLUMN IF NOT EXISTS parsed_title TEXT,
  ADD COLUMN IF NOT EXISTS parsed_description TEXT,
  ADD COLUMN IF NOT EXISTS parsed_slug TEXT,
  ADD COLUMN IF NOT EXISTS clarification_message TEXT,
  ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
  ADD COLUMN IF NOT EXISTS issue_id UUID REFERENCES signal_issues(id),
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Update status check constraint to include new statuses
-- Drop old constraint if it exists, then add new one
ALTER TABLE signal_topic_requests DROP CONSTRAINT IF EXISTS signal_topic_requests_status_check;
ALTER TABLE signal_topic_requests
  ADD CONSTRAINT signal_topic_requests_status_check
  CHECK (status IN ('submitted', 'pending', 'clarification_needed', 'approved', 'processing', 'completed', 'rejected'));
