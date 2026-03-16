# CivicScale / Parity — Architecture

## Data Architecture

### Four-tier model

```
┌─────────────────────────────────────────────────────────────────────┐
│ Tier 1 — In-memory CSV (fast path, current year only)              │
│  PFS rates · OPPS rates · CLFS rates · ZIP-locality crosswalk      │
│  Loaded once at startup into pandas DataFrames                     │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 2 — Supabase historical tables (prior years, on-demand)       │
│  pfs_rates_historical · opps_rates_historical ·                    │
│  clfs_rates_historical · rate_schedule_versions                    │
│  Queried only when date_of_service falls in a prior rate year      │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 3 — Supabase current tables (frequently updated datasets)     │
│  pharmacy_nadac · pharmacy_asp                                     │
│  Refreshed weekly/quarterly via loader scripts                     │
├─────────────────────────────────────────────────────────────────────┤
│ Tier 4 — Supabase always (all user/session/subscription data)      │
│  companies · sessions · otp_codes · employer_* · broker_* ·        │
│  provider_* · health_* · signal_* · deletion_requests              │
│  Never stored in CSV. Always read/write via Supabase REST API.     │
└─────────────────────────────────────────────────────────────────────┘
```

### Tier 1 — In-memory CSV files

Loaded at app startup by `benchmark.py:load_data()`. Serves all current-year
rate lookups with zero network latency.

| File | Path | Rows | Size | Source | Vintage |
|------|------|------|------|--------|---------|
| PFS rates | `backend/data/pfs_rates.csv` | 841,262 | 23 MB | CMS Physician Fee Schedule | CY 2026 (updated 12/29/2025) |
| OPPS rates | `backend/data/opps_rates.csv` | 7,312 | 315 KB | CMS Outpatient Prospective Payment System | 2026 |
| CLFS rates | `backend/data/clfs_rates.csv` | 2,006 | 73 KB | CMS Clinical Laboratory Fee Schedule | 2026 Q1 |
| ZIP-locality | `backend/data/zip_locality.csv` | 42,956 | 755 KB | CMS ZIP5 crosswalk | APR 2026 |

**Lookup chain** (`benchmark.py:lookup_rate()`): PFS → OPPS → CLFS. First match wins.

**Regeneration scripts** (run manually when CMS publishes new year):
- `backend/scripts/process_pfs.py` — reads CMS carrier ZIP + ZIP5 Excel, outputs `pfs_rates.csv` and `zip_locality.csv`
- `backend/scripts/process_opps.py` — reads CMS OPPS Addendum B, outputs `opps_rates.csv`
- `backend/scripts/process_clfs.py` — reads CMS CLFS file, outputs `clfs_rates.csv`

### Tier 2 — Supabase historical tables

Created by migration 002. Queried by `benchmark.py:lookup_rate_historical()`
when a claim's date of service falls in a prior rate year.

| Table | Schema | Purpose |
|-------|--------|---------|
| `rate_schedule_versions` | id, schedule_type, vintage_year, vintage_quarter, effective_date, expiry_date, is_current, source_file, loaded_at, row_count | Registry of all loaded rate vintages |
| `pfs_rates_historical` | version_id (FK), hcpcs_code, carrier, locality_code, nonfacility_amount, facility_amount | Prior-year PFS rates (~841K rows per year) |
| `opps_rates_historical` | version_id (FK), hcpcs_code, payment_rate, description | Prior-year OPPS rates (~7K rows per year) |
| `clfs_rates_historical` | version_id (FK), hcpcs_code, payment_rate, description | Prior-year CLFS rates (~2K rows per quarter) |

**Loader:** `backend/scripts/load_historical_rates.py` — bulk loads a CSV into the
appropriate historical table with version tracking. See `backend/scripts/README_rate_versioning.md`.

**Current status:** Tables exist but are empty. When date_of_service falls in a prior
year and no historical data is loaded, the system falls back to current-year rates
with a warning: "Historical rates for [year] not available — using current CMS rates
as approximation."

### Tier 3 — Supabase current tables

| Table | Rows | Loader Script | Source | Update Frequency |
|-------|------|---------------|--------|------------------|
| `pharmacy_nadac` | ~30,000 | `backend/scripts/load_nadac.py` | CMS Medicaid.gov NADAC 2026 (UUID `fbb83258-...`) | Weekly |
| `pharmacy_asp` | ~531 | `backend/scripts/load_asp.py` | CMS Medicare Part B ASP quarterly ZIP | Quarterly |

### Tier 4 — Supabase always

All user data, authentication, subscriptions, analysis results, and operational
state lives exclusively in Supabase (PostgreSQL + RLS). Key tables:

**Auth & identity:** companies, company_users, company_invitations, sessions, otp_codes, health_users, broker_accounts
**Subscriptions:** employer_subscriptions, health_subscriptions, signal_subscriptions, provider_subscriptions
**Analysis results:** employer_benchmark_sessions, employer_claims_uploads, employer_scorecard_sessions, employer_trends_cache, pharmacy_benchmarks, broker_client_benchmarks, broker_prospect_benchmarks
**Provider:** provider_contracts, provider_benchmark_observations, provider_profiles
**Operational:** deletion_requests, broker_employer_links, broker_referrals, health_sbc_uploads
**Analytics:** signal_events (privacy-first, session_id only — user_id column removed for privacy compliance, 90-day retention policy, device_type column removed)

---

## Data Update Schedule

| Data Source | Current Vintage | Update Frequency | Mechanism | Next Action |
|-------------|----------------|------------------|-----------|-------------|
| PFS rates CSV | CY 2026 | Annual (Jan) | Re-run `process_pfs.py` with new CMS carrier ZIP | January 2027 |
| OPPS rates CSV | 2026 | Annual (Jan) | Re-run `process_opps.py` | January 2027 |
| CLFS rates CSV | 2026 Q1 | Quarterly | Re-run `process_clfs.py` | Q2 2026 |
| ZIP-locality CSV | APR 2026 | Annual | Re-run `process_pfs.py` (bundled) | April 2027 |
| NADAC (Supabase) | 2026-03-11 | Weekly | Run `load_nadac.py` | Weekly |
| ASP (Supabase) | Q1 2026 | Quarterly | Run `load_asp.py` with new CMS ZIP | Q2 2026 |
| NCCI edits (Supabase) | Through 2026-01-01 | Quarterly | Manual load | Q2 2026 |
| Historical rates | Not loaded | As needed | Run `load_historical_rates.py` per year | When prior-year accuracy needed |

---

## Products and URLs

| Product | Production URL | Subdomain | Backend Router(s) |
|---------|---------------|-----------|-------------------|
| Parity Employer | employer.civicscale.ai | ✓ | employer_benchmark, employer_claims, employer_scorecard, employer_pharmacy, employer_trends, employer_subscription |
| Parity Broker | broker.civicscale.ai | ✓ | broker |
| Parity Provider | provider.civicscale.ai | ✓ | provider_audit, provider_shared, provider_subscription, provider_appeals |
| Parity Health | health.civicscale.ai | ✓ | health_analyze, health_auth |
| Parity Signal | signal.civicscale.ai | ✓ | signal_qa, signal_profiles, signal_stripe |
| CivicScale homepage | civicscale.ai | — | — |

Frontend: React/Vite → Vercel (auto-deploys from main)
Backend: FastAPI Python 3.11 → Render (parity-poc-api.onrender.com)
Database: Supabase (PostgreSQL + RLS)

---

## Authentication System

### OTP flow (Employer, Broker, Provider, Health)

```
Client                    Backend                    Supabase
  │                         │                          │
  ├─ POST /auth/send-otp ──►│                          │
  │   { email, product }    │── INSERT otp_codes ─────►│
  │                         │── Send email (Resend) ──►│
  │                         │                          │
  ├─ POST /auth/verify-otp─►│                          │
  │   { email, code }       │── SELECT otp_codes ─────►│
  │                         │── DELETE otp_code ──────►│
  │                         │── INSERT sessions ──────►│
  │◄── { token } ──────────│                          │
  │                         │                          │
  ├─ GET /auth/me ─────────►│                          │
  │   Authorization: token  │── SELECT sessions ──────►│
  │◄── { email, company } ──│                          │
```

- **OTP length:** 8 digits for all B2B products (employer, broker, provider, health)
- **OTP expiry:** 10 minutes
- **Session token:** UUID stored in `sessions` table, 30-day expiry
- **Session refresh:** `last_active_at` updated on every `/auth/me` call
- **Client storage:** `cs_session_token` (employer/broker/provider) or `health_token` (health) in localStorage

### Signal auth
Signal uses Supabase Auth directly (not the custom OTP system). Tokens are
Supabase JWTs validated via `sb.auth.get_user(token)`.

### Company types
The `companies` table has a `type` column: `"employer"`, `"broker"`, or `"provider"`.
Health users are individual consumers stored in `health_users` (no company affiliation).
Signal users are in Supabase Auth (no company affiliation).

---

## Stripe Integration

### Products and pricing

| Product | Price | Env Var | Trial | Card Required |
|---------|-------|---------|-------|---------------|
| Employer | $99/mo | `STRIPE_PRICE_EMPLOYER` | 30 days | Yes |
| Broker | $99/mo | `STRIPE_PRICE_BROKER_PRO` | 30 days | Yes |
| Provider | per-practice | `STRIPE_PRICE_PROVIDER_MONTHLY` | 30 days | Yes |
| Health Monthly | $9.95/mo | `STRIPE_PRICE_HEALTH_MONTHLY` | 30 days | Yes |
| Health Yearly | $29/yr | `STRIPE_PRICE_HEALTH_YEARLY` | 30 days | Yes |
| Signal Standard | varies | `STRIPE_PRICE_STANDARD_MONTHLY/ANNUAL` | — | Yes |
| Signal Premium | varies | `STRIPE_PRICE_PREMIUM_MONTHLY/ANNUAL` | — | Yes |
| Signal Professional | varies | `STRIPE_PRICE_PROFESSIONAL_MONTHLY/ANNUAL` | — | Yes |

Legacy employer tiers (existing subscribers): `STRIPE_PRICE_EMPLOYER_STARTER`, `_GROWTH`, `_SCALE`

### Webhook endpoints

| Endpoint | Handler | Secret Env Var | Products |
|----------|---------|----------------|----------|
| `POST /api/employer/subscription/webhook` | employer_subscription.py | `STRIPE_WEBHOOK_SECRET` | Employer, Broker |
| `POST /api/health/auth/webhook` | health_auth.py | `STRIPE_HEALTH_WEBHOOK_SECRET` | Health |
| `POST /api/provider/subscription/webhook` | provider_subscription.py | `STRIPE_WEBHOOK_SECRET` | Provider |
| `POST /api/signal/stripe/webhooks` | signal_stripe.py | `STRIPE_SIGNAL_WEBHOOK_SECRET` | Signal |

### Webhook events handled
- `checkout.session.completed` — create subscription record, start trial
- `customer.subscription.updated` — plan changes, trial-to-paid conversion
- `customer.subscription.deleted` — mark canceled
- `invoice.payment_failed` — mark past_due

### Trial logic
All products use Stripe's `trial_period_days: 30`. Card is collected at checkout
but not charged until trial ends. Employer also has a savings guarantee: if
identified savings don't exceed annual subscription cost, refund the difference.

---

## Environment Variables

### Required (Render)

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for server-side API calls |
| `ANTHROPIC_API_KEY` | Claude API key for AI features |
| `STRIPE_SECRET_KEY` | Stripe API secret (test or production) |
| `STRIPE_WEBHOOK_SECRET` | Webhook secret for employer + provider webhooks |
| `STRIPE_HEALTH_WEBHOOK_SECRET` | Webhook secret for health subscriptions |
| `STRIPE_SIGNAL_WEBHOOK_SECRET` | Webhook secret for Signal subscriptions |
| `RESEND_API_KEY` | Resend email delivery API key |
| `CRON_SECRET` | Shared secret protecting `POST /api/broker/send-renewal-reminders` |

### Stripe price IDs (Render)

| Variable | Product |
|----------|---------|
| `STRIPE_PRICE_EMPLOYER` | Employer $99/mo flat |
| `STRIPE_PRICE_EMPLOYER_STARTER` | Legacy employer tier |
| `STRIPE_PRICE_EMPLOYER_GROWTH` | Legacy employer tier |
| `STRIPE_PRICE_EMPLOYER_SCALE` | Legacy employer tier |
| `STRIPE_PRICE_BROKER_PRO` | Broker $99/mo |
| `STRIPE_PRICE_PROVIDER_MONTHLY` | Provider monthly |
| `STRIPE_PRICE_HEALTH_MONTHLY` | Health $9.95/mo |
| `STRIPE_PRICE_HEALTH_YEARLY` | Health $29/yr |
| `STRIPE_PRICE_STANDARD_MONTHLY` | Signal standard monthly |
| `STRIPE_PRICE_STANDARD_ANNUAL` | Signal standard annual |
| `STRIPE_PRICE_PREMIUM_MONTHLY` | Signal premium monthly |
| `STRIPE_PRICE_PREMIUM_ANNUAL` | Signal premium annual |
| `STRIPE_PRICE_PROFESSIONAL_MONTHLY` | Signal professional monthly |
| `STRIPE_PRICE_PROFESSIONAL_ANNUAL` | Signal professional annual |

### Optional

| Variable | Purpose | Default |
|----------|---------|---------|
| `CORS_ORIGINS` | Comma-separated allowed origins | Production subdomains |
| `FRONTEND_URL` | Base URL for redirect links | `https://civicscale.ai` |
| `SIGNAL_URL` | Signal-specific frontend URL | `https://signal.civicscale.ai` |
