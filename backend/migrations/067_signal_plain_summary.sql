-- Migration 067: Plain Summary layer for Signal topics
-- Adds accessible plain-language summary + approval workflow to signal_issues

ALTER TABLE signal_issues ADD COLUMN IF NOT EXISTS plain_summary TEXT;
ALTER TABLE signal_issues ADD COLUMN IF NOT EXISTS plain_summary_status TEXT DEFAULT 'pending';
-- Values: 'pending' | 'generated' | 'approved'
