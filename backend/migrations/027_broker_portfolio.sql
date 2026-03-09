-- Migration 027: Add broker portfolio columns
-- Run this in Supabase SQL Editor

alter table broker_employer_links
  add column if not exists renewal_month date,
  add column if not exists broker_notes text;

alter table broker_accounts
  add column if not exists logo_url text;
