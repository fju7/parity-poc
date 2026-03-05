-- Migration 014: Add archived column to provider_audits
-- Run in Supabase SQL Editor

ALTER TABLE provider_audits ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT false;
