-- Migration 026: Add broker signup columns
-- Run this in Supabase SQL Editor

alter table broker_accounts
  add column if not exists name text,
  add column if not exists phone text,
  add column if not exists status text not null default 'active',
  add column if not exists created_at timestamptz not null default now();

-- Note: firm_name and contact_name columns already exist in broker_accounts.
-- The signup endpoint uses contact_name for the broker's name.
