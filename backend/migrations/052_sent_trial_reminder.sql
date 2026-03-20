-- Migration 052: Add sent_trial_reminder flag to companies table
-- Prevents duplicate trial expiry reminder emails
ALTER TABLE companies ADD COLUMN IF NOT EXISTS sent_trial_reminder BOOLEAN DEFAULT FALSE;
