-- ============================================================
-- MIGRATION 001: Unified Auth Architecture
-- Run in Supabase SQL Editor
-- ============================================================

-- 1. Companies (the core organizational unit)
CREATE TABLE IF NOT EXISTS companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  type text NOT NULL CHECK (type IN ('employer', 'broker', 'provider')),
  industry text,
  state text,
  size_band text,
  stripe_customer_id text,
  created_at timestamptz DEFAULT now(),
  created_by_email text
);

-- 2. Company users (people who belong to a company)
CREATE TABLE IF NOT EXISTS company_users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  email text NOT NULL,
  full_name text,
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'suspended')),
  invited_by_email text,
  created_at timestamptz DEFAULT now(),
  last_login_at timestamptz,
  UNIQUE(company_id, email)
);

-- 3. Sessions (UUID token-based, replaces email-only localStorage)
CREATE TABLE IF NOT EXISTS sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  company_id uuid REFERENCES companies(id) ON DELETE CASCADE,
  product text NOT NULL CHECK (product IN ('employer', 'broker', 'provider', 'health')),
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz NOT NULL,
  last_active_at timestamptz DEFAULT now(),
  user_agent text,
  ip_address text
);

-- 4. Company invitations
CREATE TABLE IF NOT EXISTS company_invitations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  invited_email text NOT NULL,
  invited_by_email text NOT NULL,
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
  token uuid NOT NULL DEFAULT gen_random_uuid(),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired')),
  created_at timestamptz DEFAULT now(),
  expires_at timestamptz DEFAULT (now() + interval '7 days'),
  UNIQUE(token)
);

-- 5. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_sessions_email ON sessions(email);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_company_users_email ON company_users(email);
CREATE INDEX IF NOT EXISTS idx_company_users_company ON company_users(company_id);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON company_invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON company_invitations(invited_email);

