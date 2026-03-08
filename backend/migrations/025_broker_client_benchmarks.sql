-- Migration 025: Broker client benchmarks and onboarding support
-- Run in Supabase SQL Editor

-- 1. Broker client benchmarks table
create table if not exists broker_client_benchmarks (
  id uuid primary key default gen_random_uuid(),
  broker_email text not null,
  employer_email text,
  company_name text not null,
  employee_count int,
  industry text,
  state text,
  carrier text,
  estimated_pepm float,
  benchmark_result jsonb,
  share_token uuid not null default gen_random_uuid(),
  share_token_created_at timestamptz not null default now(),
  view_count int not null default 0,
  first_viewed_at timestamptz,
  created_at timestamptz not null default now()
);

alter table broker_client_benchmarks enable row level security;

create policy "service role full access"
  on broker_client_benchmarks
  for all to service_role
  using (true) with check (true);

-- Allow public read via share token (no auth required)
create policy "public read by share token"
  on broker_client_benchmarks
  for select to anon
  using (true);

-- 2. Update broker_employer_links for onboarding flow
alter table broker_employer_links
  add column if not exists status text not null default 'onboarded',
  add column if not exists company_name text,
  add column if not exists employee_count_range text,
  add column if not exists industry text,
  add column if not exists state text,
  add column if not exists carrier text;
