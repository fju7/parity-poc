-- Migration 032: Fix provider_contracts, provider_analyses, provider_audits,
-- provider_appeals, provider_subscriptions — rename user_id → company_id
-- Same fix as migration 031 did for provider_profiles.
-- Wrapped in DO blocks so this is safe on fresh databases where user_id never existed.
-- Run this in Supabase SQL Editor.

-- =========================================================================
-- provider_contracts
-- =========================================================================
ALTER TABLE provider_contracts DROP CONSTRAINT IF EXISTS provider_contracts_user_id_fkey;
ALTER TABLE provider_contracts DROP CONSTRAINT IF EXISTS provider_contracts_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_contracts' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_contracts WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_contracts RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_contracts
  ADD CONSTRAINT provider_contracts_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS: drop auth.uid()-based policies, allow service role
DROP POLICY IF EXISTS "Users can read own contracts" ON provider_contracts;
DROP POLICY IF EXISTS "Users can insert own contracts" ON provider_contracts;
DROP POLICY IF EXISTS "Users can update own contracts" ON provider_contracts;
DROP POLICY IF EXISTS "Service role full access" ON provider_contracts;
CREATE POLICY "Service role full access" ON provider_contracts
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_analyses
-- =========================================================================
ALTER TABLE provider_analyses DROP CONSTRAINT IF EXISTS provider_analyses_user_id_fkey;
ALTER TABLE provider_analyses DROP CONSTRAINT IF EXISTS provider_analyses_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_analyses' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_analyses WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_analyses RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_analyses
  ADD CONSTRAINT provider_analyses_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS
DROP POLICY IF EXISTS "Users can read own analyses" ON provider_analyses;
DROP POLICY IF EXISTS "Users can insert own analyses" ON provider_analyses;
DROP POLICY IF EXISTS "Service role full access" ON provider_analyses;
CREATE POLICY "Service role full access" ON provider_analyses
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_audits
-- =========================================================================
ALTER TABLE provider_audits DROP CONSTRAINT IF EXISTS provider_audits_user_id_fkey;
ALTER TABLE provider_audits DROP CONSTRAINT IF EXISTS provider_audits_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_audits' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_audits WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_audits RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_audits
  ADD CONSTRAINT provider_audits_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS
DROP POLICY IF EXISTS "service_role_full_access" ON provider_audits;
DROP POLICY IF EXISTS "users_read_own_audits" ON provider_audits;
DROP POLICY IF EXISTS "users_insert_own_audits" ON provider_audits;
DROP POLICY IF EXISTS "Service role full access" ON provider_audits;
CREATE POLICY "Service role full access" ON provider_audits
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_appeals
-- =========================================================================
ALTER TABLE provider_appeals DROP CONSTRAINT IF EXISTS provider_appeals_user_id_fkey;
ALTER TABLE provider_appeals DROP CONSTRAINT IF EXISTS provider_appeals_user_id_key;
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_appeals' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_appeals WHERE user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_appeals RENAME COLUMN user_id TO company_id;
  END IF;
END $$;
ALTER TABLE provider_appeals
  ADD CONSTRAINT provider_appeals_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- Fix RLS
DROP POLICY IF EXISTS "Users can view own appeals" ON provider_appeals;
DROP POLICY IF EXISTS "Users can insert own appeals" ON provider_appeals;
DROP POLICY IF EXISTS "Users can update own appeals" ON provider_appeals;
DROP POLICY IF EXISTS "Service role full access" ON provider_appeals;
CREATE POLICY "Service role full access" ON provider_appeals
  FOR ALL USING (true) WITH CHECK (true);

-- =========================================================================
-- provider_subscriptions (user_id has no FK, just rename)
-- =========================================================================
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'provider_subscriptions' AND column_name = 'user_id'
  ) THEN
    DELETE FROM provider_subscriptions WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM companies);
    ALTER TABLE provider_subscriptions RENAME COLUMN user_id TO company_id;
  END IF;
END $$;

-- Fix RLS
DROP POLICY IF EXISTS "service_role_full_access" ON provider_subscriptions;
DROP POLICY IF EXISTS "users_read_own_subscriptions" ON provider_subscriptions;
DROP POLICY IF EXISTS "Service role full access" ON provider_subscriptions;
CREATE POLICY "Service role full access" ON provider_subscriptions
  FOR ALL USING (true) WITH CHECK (true);
