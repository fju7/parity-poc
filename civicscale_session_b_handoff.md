# CivicScale Claude Code Handoff — Session B: Broker Auth Migration
**Date:** March 10, 2026  
**Repo:** https://github.com/fju7/parity-poc  
**Local path:** `/Users/fredugast/Desktop/AI Projects/Parity Medical/parity-poc-repo`  
**Rules:** python3/pip3 only · commit directly to main · no feature branches

---

## MISSION

Migrate the Broker Portal from its current email-only localStorage auth to the unified auth system (companies + company_users + sessions tables) built in Session A. After this migration, broker firms become first-class `companies` with `type = 'broker'`, multiple brokers at the same firm share a book of business, and broker commission tracking for employer referrals is wired up.

---

## UNIFIED AUTH SYSTEM — WHAT ALREADY EXISTS (Session A)

Do not rebuild any of this. It is live and working.

### Database tables (already in Supabase):
- `companies` — core org unit. Columns include: `id`, `name`, `type` (employer/broker/provider), `plan`, `stripe_customer_id`, `stripe_subscription_id`, `trial_ends_at`, `trial_started_at`, `plan_locked_until`, `created_at`
- `company_users` — people in companies. Columns: `id`, `company_id`, `email`, `role` (admin/member/viewer), `name`, `created_at`
- `sessions` — UUID tokens. Columns: `id` (UUID token), `company_user_id`, `expires_at`, `created_at`
- `company_invitations` — invite tokens. Columns: `id`, `company_id`, `email`, `role`, `token`, `expires_at`, `invited_by`, `accepted_at`

### Backend (already deployed):
- `backend/routers/auth.py` — full unified auth router
- `get_current_user(authorization, sb)` — shared auth helper, import this in any router
- Endpoints: `/api/auth/send-otp`, `/api/auth/verify-otp`, `/api/auth/me`, `/api/auth/logout`, `/api/auth/company`, `/api/auth/invite`, `/api/auth/accept-invite`

### Frontend (already deployed):
- `frontend/src/context/AuthContext.jsx` — `useAuth()` hook. Provides: `token, user, company, login, logout, isAdmin, isMember, isAuthenticated, refetch`
- `frontend/src/components/AuthGate.jsx` — wraps protected pages, handles OTP inline
- `frontend/src/components/EmployerSignupPage.jsx` — reference implementation of the full signup flow
- `frontend/src/components/EmployerDashboard.jsx` — reference implementation of a protected dashboard

### localStorage key:
- `cs_session_token` — single key used across all products

---

## CURRENT BROKER AUTH STATE (what needs to be replaced)

The broker portal currently uses a **separate, old auth system**:
- Email stored directly in `localStorage` (key unknown — check `BrokerLoginPage.jsx` and `BrokerSignupPage.jsx`)
- `broker_accounts` table in Supabase — separate from `companies`
- Plan field on `broker_accounts`: `starter` | `pro` | `pro_cancelling`
- Stripe price: `STRIPE_PRICE_BROKER_PRO` (already in Render env vars)

### Files to inspect before touching anything:
- `frontend/src/components/BrokerSignupPage.jsx`
- `frontend/src/components/BrokerLoginPage.jsx`
- `frontend/src/components/BrokerDashboard.jsx`
- `frontend/src/components/BrokerAccountPage.jsx`
- `frontend/src/components/CAABrokerGuide.jsx`
- `frontend/src/components/RenewalPrepReport.jsx`
- `backend/routers/broker.py` (or wherever broker API routes live — verify filename)
- Any Stripe webhook handler that references `broker_accounts`

Read all of these files before writing any code.

---

## WHAT TO BUILD — SESSION B SCOPE

### 1. Database migration: `003_broker_auth_migration.sql`

Create this file at `backend/migrations/003_broker_auth_migration.sql`. Do NOT run it — Fred will paste it into Supabase SQL Editor manually.

```sql
-- Broker firms become companies with type = 'broker'
-- Migrate existing broker_accounts rows into companies + company_users

-- Step 1: Insert broker firms into companies
INSERT INTO companies (id, name, type, plan, stripe_customer_id, stripe_subscription_id, created_at)
SELECT 
  gen_random_uuid(),
  firm_name,           -- adjust column name to match actual broker_accounts schema
  'broker',
  plan,                -- map starter/pro/pro_cancelling
  stripe_customer_id,  -- adjust to match actual column name
  stripe_subscription_id, -- adjust to match actual column name
  created_at
FROM broker_accounts;

-- Step 2: Insert broker users into company_users as admins
INSERT INTO company_users (id, company_id, email, role, name, created_at)
SELECT
  gen_random_uuid(),
  c.id,
  ba.email,            -- adjust to match actual column name
  'admin',
  ba.contact_name,     -- adjust to match actual column name, or use email if no name field
  ba.created_at
FROM broker_accounts ba
JOIN companies c ON c.name = ba.firm_name AND c.type = 'broker';

-- Step 3: Add broker-specific columns to companies (if not already present)
ALTER TABLE companies ADD COLUMN IF NOT EXISTS broker_client_limit int DEFAULT 10;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS broker_commission_rate numeric DEFAULT 0.20;
```

**IMPORTANT:** Before writing this migration, read the actual `broker_accounts` table schema by looking at any existing migration files or the broker router to determine the real column names. Adjust the SQL above to match actual column names. Do not guess.

### 2. Add commission tracking table

Add to `003_broker_auth_migration.sql`:

```sql
CREATE TABLE IF NOT EXISTS broker_commissions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  broker_company_id uuid REFERENCES companies(id),
  employer_company_id uuid REFERENCES companies(id),
  referral_date timestamptz DEFAULT now(),
  commission_rate numeric DEFAULT 0.20,
  commission_months int DEFAULT 12,
  first_paid_month timestamptz,      -- null until employer converts to paid
  status text DEFAULT 'pending'      -- pending / active / completed / cancelled
    CHECK (status IN ('pending', 'active', 'completed', 'cancelled')),
  created_at timestamptz DEFAULT now()
);
```

### 3. Backend — broker router migration

In `backend/routers/broker.py` (or equivalent):

- Replace any `broker_accounts` auth checks with `get_current_user(authorization, sb)` from `auth.py`
- Any endpoint that currently checks "is this a valid broker session" should now validate via the unified sessions table
- Any endpoint that queries `broker_accounts` for plan/stripe info should now query `companies` where `type = 'broker'`
- Keep all existing broker business logic (book of business, renewals, prospects, CAA guide) — only swap the auth layer

Pattern to follow (import and use this in broker router):
```python
from .auth import get_current_user

@router.get("/api/broker/dashboard")
async def broker_dashboard(
    authorization: str = Header(None),
    sb = Depends(get_supabase)
):
    user = await get_current_user(authorization, sb)
    if user["company"]["type"] != "broker":
        raise HTTPException(status_code=403, detail="Broker access only")
    # ... rest of handler
```

### 4. Frontend — broker signup flow

Replace `BrokerSignupPage.jsx` with a flow that mirrors `EmployerSignupPage.jsx`:

**Flow:**
1. Enter email → send OTP (`/api/auth/send-otp`)
2. Enter OTP → verify (`/api/auth/verify-otp`)
   - If existing broker firm found → auto-login → redirect to `/broker/dashboard`
   - If new user (`needs_company: true`) → show firm setup form
3. Firm setup: Firm name, contact name, phone (optional)
   - POST to `/api/auth/company` with `{ name: firmName, type: 'broker' }`
   - This creates the company + sets current user as admin + auto-creates session
4. Auto-login → redirect to `/broker/dashboard`

**Route:** Keep at `/broker/signup`

### 5. Frontend — broker login flow

Replace `BrokerLoginPage.jsx`:

**Flow:**
1. Enter email → send OTP
2. Enter OTP → verify → auto-login → redirect to dashboard
   - If `needs_company: true` → redirect to `/broker/signup` to complete firm setup

**Route:** Keep at `/broker/login`

### 6. Frontend — broker dashboard auth

In `BrokerDashboard.jsx`:
- Replace any localStorage email reads with `useAuth()` hook
- Wrap with `<AuthGate>` or equivalent so unauthenticated users see the OTP login inline
- All API calls should pass `Authorization: Bearer ${token}` header (token from `useAuth()`)
- Plan/upgrade state should come from `company.plan` (from auth context) not `broker_accounts`

### 7. Frontend — broker account page

In `BrokerAccountPage.jsx`:
- Replace old auth with `useAuth()` hook
- Show: firm name, admin email, team members (if multi-broker), plan, billing portal link
- Team management: if `isAdmin`, show invite form — POST to `/api/auth/invite` with `{ email, role: 'member' }`

### 8. Broker → Employer "Invite Client" button

Add an "Invite Client" button to the broker dashboard (Book of Business tab). When clicked:
- Opens a modal: enter employer contact email
- POST to a new endpoint `/api/broker/invite-employer` with `{ email }` and broker auth header
- Backend creates a `company_invitations` row with `type = 'employer_referral'` and records the referring broker's `company_id`
- Sends invite email via Resend to the employer contact

This is the mechanism that triggers commission tracking. When the invited employer signs up and converts to paid, a `broker_commissions` row becomes `active`.

### 9. Commission tracking — backend wiring

In the Stripe webhook handler (wherever `checkout.session.completed` for employers is handled):
- After employer converts to paid, check `company_invitations` for a matching employer referral from a broker
- If found, update `broker_commissions` row: set `status = 'active'`, `first_paid_month = now()`

---

## FILES TO LEAVE UNTOUCHED

- `backend/routers/auth.py` — do not modify
- `frontend/src/context/AuthContext.jsx` — do not modify
- `frontend/src/components/AuthGate.jsx` — do not modify
- `frontend/src/components/AcceptInvitePage.jsx` — do not modify
- All employer components — do not touch
- All provider components — do not touch
- `backend/migrations/001_unified_auth.sql` — do not touch
- `backend/migrations/002_employer_trial.sql` — do not touch

---

## AFTER CLAUDE CODE COMPLETES — FRED'S STEPS

1. Merge feature branch: (Claude Code will provide exact merge command)
2. Run `003_broker_auth_migration.sql` in Supabase SQL Editor
3. Verify existing broker accounts migrated correctly (spot check companies + company_users tables)
4. Test full broker signup flow at `/broker/signup`
5. Test broker login at `/broker/login`
6. Test "Invite Client" button on dashboard
7. Trigger manual Render deploy if not auto-deployed

---

## ENVIRONMENT VARIABLES (no new ones needed for Session B)

All required env vars are already in Render:
- `STRIPE_PRICE_BROKER_PRO` ✅
- `STRIPE_EMPLOYER_WEBHOOK_SECRET` ✅
- `RESEND_API_KEY` ✅

---

## STRATEGIC CONTEXT (for Claude Code awareness)

- Broker portal is the primary acquisition channel — this migration is high priority
- "We will never contact your clients directly" — employer invites must come from the broker, not CivicScale
- Broker commission: 20% recurring for 12 months, starts at employer's first paid month
- Broker freemium: Starter (free, ≤10 clients) / Pro ($99/mo, unlimited)
- Existing broker users should experience zero disruption — migration must be non-breaking

---

## TECH STACK REMINDER

- Python3 / pip3 (never python / pip)
- FastAPI backend on Render (`parity-poc-api.onrender.com`)
- React/Vite frontend on Vercel (auto-deploys main)
- Supabase PostgreSQL
- Stripe (test mode)
- Resend email (`noreply@civicscale.ai`)
- No feature branches — commit directly to main
