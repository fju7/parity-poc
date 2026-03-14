-- Migration 040: Add practice_address and billing_contact to provider_profiles
-- Run in Supabase SQL Editor

ALTER TABLE provider_profiles
  ADD COLUMN IF NOT EXISTS practice_address TEXT,
  ADD COLUMN IF NOT EXISTS billing_contact TEXT;
