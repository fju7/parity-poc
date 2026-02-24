-- Parity: profiles table for authenticated users
-- Run this in the Supabase SQL Editor

create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  email text,
  full_name text,              -- deprecated, kept for backward compat
  first_name text,
  last_name text,
  date_of_birth text,
  mailing_address text,       -- deprecated, kept for backward compat
  street_address text,
  city text,
  state text,
  zip_code text,
  phone text,
  created_at timestamptz default now()
);

-- Enable Row Level Security
alter table public.profiles enable row level security;

-- Users can read their own profile
create policy "Users can read own profile"
  on public.profiles for select
  using (auth.uid() = id);

-- Users can insert their own profile
create policy "Users can insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

-- Users can update their own profile
create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);
