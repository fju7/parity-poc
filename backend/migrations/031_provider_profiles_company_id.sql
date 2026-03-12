-- Migration 031: Rename provider_profiles.user_id → company_id
-- The column was referencing auth.users(id) but actually stores companies.id values.
-- Run this in Supabase SQL Editor.

-- 1. Drop old foreign key constraint (references auth.users)
ALTER TABLE provider_profiles
  DROP CONSTRAINT IF EXISTS provider_profiles_user_id_fkey;

-- 2. Delete orphaned rows (old Supabase Auth user IDs not in companies)
DELETE FROM provider_profiles
WHERE user_id NOT IN (SELECT id FROM companies);

-- 3. Rename column
ALTER TABLE provider_profiles
  RENAME COLUMN user_id TO company_id;

-- 4. Add new foreign key referencing companies(id)
ALTER TABLE provider_profiles
  ADD CONSTRAINT provider_profiles_company_id_fkey
  FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;

-- 4. Update unique constraint / index if one exists on user_id
DROP INDEX IF EXISTS provider_profiles_user_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS provider_profiles_company_id_key ON provider_profiles (company_id);

-- 5. Drop old RLS policies that reference user_id and recreate with company_id
DROP POLICY IF EXISTS "Users can read own profile" ON provider_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON provider_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON provider_profiles;

-- RLS policies now use service_role key from backend, so simple permissive policies:
CREATE POLICY "Service role full access" ON provider_profiles
  FOR ALL USING (true) WITH CHECK (true);
