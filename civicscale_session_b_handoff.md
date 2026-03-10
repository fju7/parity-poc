# CivicScale Session Handoff Document
**Last updated:** March 10, 2026  
**Repo:** https://github.com/fju7/parity-poc  
**Local path:** `/Users/fredugast/Desktop/AI Projects/Parity Medical/parity-poc-repo`  
**Rules:** python3/pip3 only · commit directly to main · no feature branches

---

## SESSION STATUS

| Session | Status | Summary |
|---------|--------|---------|
| A | ✅ Complete | Unified auth architecture |
| B | ✅ Complete | Broker auth migration + website redesign strategy |
| C | ✅ Complete | Provider auth migration |
| D | ✅ Complete | Account pages polish |
| E-Signal | ✅ Complete | Analytical profiles build-out |
| E-Health | ✅ Complete | CPT labels + denial appeals |
| E-Pharmacy | ✅ Complete | Pharmacy benefit benchmarking |
| F | 🔜 Next | Website redesign + investor page |
| G | Queued | Go live |

---

## COMPLETED SESSIONS SUMMARY

### Session A — Unified Auth ✅
- Tables: `companies`, `company_users`, `sessions`, `company_invitations`
- Migration `001_unified_auth.sql` — run ✅
- `backend/routers/auth.py` — full unified auth module with `get_current_user()` helper
- Frontend: `AuthContext.jsx` (`useAuth()` hook), `AuthGate.jsx`, `EmployerSignupPage.jsx`, `EmployerDashboard.jsx`, `EmployerAccountPage.jsx`, `AcceptInvitePage.jsx`
- localStorage key: `cs_session_token` · API auth: `Authorization: Bearer {token}`

### Session B — Broker Auth Migration ✅
- Migrated broker auth from localStorage to unified `sessions` + `companies` tables
- Broker firms = `companies` with `type = 'broker'`
- Multi-broker firm support, broker-controlled employer invitation flow
- Broker commission: 20% recurring 12 months on employer referrals

### Session C — Provider Auth Migration ✅
- `provider_shared.py` — replaced `_get_authenticated_user` with `get_current_user()`, added `_AuthUser` wrapper
- `provider_audit.py` — 4 new endpoints: `/my-profile`, `/save-profile`, `/my-analyses`, `/analysis/{id}`
- `provider_appeals.py`, `provider_subscription.py` — removed `await` from auth calls
- Frontend: `ProviderApp.jsx`, `AuditAccount.jsx`, `ProviderAuditAdmin.jsx`, `ProviderAuditReport.jsx`, `AuditStandalone.jsx` — all migrated to `useAuth()`

### Session D — Account Pages Polish ✅
- `auth.py` — added `POST /api/auth/deletion-request` (admin role + company name confirmation, emails to user + `admin@civicscale.ai`)
- `EmployerAccountPage.jsx` — fixed billing portal URL, real deletion modal
- `BrokerAccountPage.jsx` — AuthGate wrap, role management, deletion modal
- Migration `028_deletion_requests.sql` — run ✅

### Session E-Signal — Analytical Profiles ✅
- `backend/routers/signal_profiles.py` — `GET /api/signal/profiles` (cached 10min), `POST /api/signal/profiles/score?profile_id=&issue_id=` (returns scores + `divergences` array)
- Migration `029_signal_analytical_profiles_seed.sql` — seeds 4 profiles: Balanced (default), Regulatory (source_quality 40%, consensus 30%), Clinical (rigor 35%, reproducibility 30%), Patient (data_support 35%, recency 30%)
- Frontend: `ProfileSelector.jsx` (premium-gated, 4 profile cards, divergence section), `IssueDashboard.jsx` (ProfileSelector integrated), `ClaimCard.jsx` (`divergent` prop adds amber border)
- Migration run ✅ · Render redeployed ✅

### Session E-Health — CPT Labels + Denial Appeals ✅
- `frontend/src/lib/cptLabel.js` — shared utility with 70+ CPT codes, used by both `EmployerClaimsCheck` and `ReportView`
- `ReportView.jsx` — CPT plain-English labels with fallback (REVENUE codes excluded)
- `backend/routers/health_analyze.py` — two new endpoints:
  - `POST /api/health/analyze-denial` — AI-powered denial letter analysis → structured JSON
  - `POST /api/health/generate-appeal` — generates formal appeal letter
- `DenialUploadView.jsx` — paste/upload denial text at `/parity-health/denial`
- `DenialReportView.jsx` — analysis display with weakness highlight, appeal letter generation, copy/print
- `UploadView.jsx` — "Received a denial? Analyze it here →" entry point added
- `main.jsx` — detects `health.civicscale.ai` hostname and renders Parity Health app directly
- `health.civicscale.ai` — live in Vercel ✅

### Session E-Pharmacy — Pharmacy Benefit Benchmarking ✅
- `backend/routers/employer_pharmacy.py` — `POST /api/employer/pharmacy/analyze`
  - Three-stage parsing: 835 EDI (N4 qualifier for NDC) → CSV/Excel auto-detect → AI extraction fallback
  - NADAC benchmarking: NDC lookup in `pharmacy_nadac` table, spread calculation, flags spreads >20%
  - Returns: summary, top_drugs, generic_opportunity, specialty_drugs, benchmarks, pbm_spread_estimate
- Migration `030_pharmacy_nadac.sql` — run ✅ (`pharmacy_nadac` + `pharmacy_benchmarks` tables)
- `backend/scripts/load_nadac.py` — CMS NADAC CSV loader
- NADAC data loaded from `nadac-national-average-drug-acquisition-cost-02-25-2026.csv` ✅
- `frontend/src/components/EmployerPharmacy.jsx` at `/billing/employer/pharmacy`
  - Summary stats, top drugs table with NADAC/spread, generic opportunities, specialty drug spend
  - PBM spread placeholder card (Option B hook for future session)
  - "What This Means" callout
- Tab toggle: Medical Claims ↔ Pharmacy Claims added to both pages
- Synthetic test CSV: `backend/data/sample/Midwest_Manufacturing_Pharmacy_Dec2024.csv` (55 claims)

**NADAC loader note:** The CMS Datastore API endpoint is broken. Always load NADAC via direct CSV:
```
curl -o /tmp/nadac.csv "https://download.medicaid.gov/data/nadac-national-average-drug-acquisition-cost-02-25-2026.csv"
SUPABASE_URL=https://kfxxpscdwoemtzylhhhb.supabase.co SUPABASE_SERVICE_ROLE_KEY=YOUR_KEY python3 /tmp/load_nadac.py
```
CMS publishes updates weekly at `download.medicaid.gov/data/nadac-national-average-drug-acquisition-cost-MM-DD-YYYY.csv`

---

## SESSION F — NEXT: Website Redesign + Investor Page

**Design in Claude.ai first, then hand off to Claude Code.**

All prerequisite product sessions are complete. Every product surface is real and demonstrable:
- Parity Employer — medical claims benchmarking + pharmacy benchmarking
- Parity Provider — contract integrity audit, denial appeals, PDF report generation
- Parity Health — bill analysis + denial appeals at `health.civicscale.ai`
- Parity Signal — multi-dimensional claim scoring with 4 operational analytical profiles

### What to build

**`civicscale.ai` homepage redesign**
- Mission statement, employer/broker two-path routing, Signal footer attribution, investor nav link
- Consistent CTA language and design conventions across all products

**`investors.civicscale.ai` subdomain**
- Full platform story page, public-facing, single long-scroll
- Signal analytical profiles ARE built and operational — investor copy can state this honestly

### Subdomain architecture
```
civicscale.ai              → Main site: Employer + Broker + mission
provider.civicscale.ai     → Standalone Provider entry point
health.civicscale.ai       → Parity Health consumer app (live ✅)
investors.civicscale.ai    → Investor-facing narrative site
```

### CTA conventions (apply everywhere)
| Element | Standard |
|---------|----------|
| Primary CTA | "Start Free Trial" (employer) / "Get Started Free" (broker) |
| Trust line | "No credit card required for first 30 days · Cancel anytime" |
| Secondary CTA | Always "See a Demo" |
| Value prop format | 3 outcome bullets, not feature bullets |
| Tone | Direct, data-confident — never salesy |

### Product audience map
| Product | Who buys | Their goal | Their adversary |
|---------|----------|------------|-----------------|
| Parity Employer | HR/benefits directors | Reduce cost, benchmark, understand carrier data | Their carrier |
| Parity Provider | Practice managers, billing directors, CFOs | Get paid correctly, fight denials | Their payers/carriers |
| Parity Health | Individual consumers | Understand bills, appeal denials | Their insurer + provider |
| Parity Signal | Enterprise, researchers, policy orgs | Systemic intelligence | Opacity itself |

### Investor narrative
CivicScale is not a healthcare company. It is an information asymmetry engine deployed in healthcare first because the conditions there are uniquely favorable: a public reference price exists (Medicare), data is available due to price transparency regulations, the problem is visceral, and regulatory tailwinds (CAA, No Surprises Act) are forcing data into the open.

The real thesis: **any market where a discoverable truth exists but powerful intermediaries profit from hiding it is a Parity Signal market.**

What makes Parity Signal genuinely differentiated: it doesn't just find the gap between what things cost and what institutions claim they cost. It scores claims across multiple dimensions with recorded weights, tracks divergent arguments on contested claims, and supports named analytical profiles that make competing conclusions legible — showing not just what is true but how different weightings of the same evidence produce different conclusions, and what it would take to change a decision.

Signal doesn't just find the gap — it models the decision-making machinery that produces the gap, making it possible to close it, appeal it, or engineer around it.

---

## SESSION G — QUEUED: Go Live

- Swap Stripe test keys for live keys in Render env vars
- Verify all webhooks fire correctly in live mode
- Smoke test all checkout flows
- Half-session — mostly env var swaps and verification

---

## INFRASTRUCTURE

- **Frontend:** React/Vite → Vercel (auto-deploys main)
- **Backend:** FastAPI Python 3.11 → Render at `parity-poc-api.onrender.com`
- **Database:** Supabase (paid plan) · URL: `https://kfxxpscdwoemtzylhhhb.supabase.co`
- **Payments:** Stripe (test mode)
- **Email:** Resend (`noreply@civicscale.ai`)

## ENVIRONMENT VARIABLES (Render)
```
ANTHROPIC_API_KEY · SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY
STRIPE_SECRET_KEY · STRIPE_WEBHOOK_SECRET · STRIPE_EMPLOYER_WEBHOOK_SECRET
STRIPE_PRICE_BROKER_PRO · STRIPE_PRICE_EMPLOYER_PRO
RESEND_API_KEY · CRON_SECRET=notify-deliver-2026
```
Obsolete (remove): `STRIPE_PRICE_EMPLOYER_STARTER/GROWTH/SCALE`

## STRIPE WEBHOOKS
1. Provider: `https://parity-poc-api.onrender.com/api/provider/subscription/webhook`
2. Signal: `https://parity-poc-api.onrender.com/api/signal/stripe/webhooks`
3. Employer/Broker: `https://parity-poc-api.onrender.com/api/employer/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`
   - Secret: `STRIPE_EMPLOYER_WEBHOOK_SECRET`

## MIGRATIONS RUN
| File | Status |
|------|--------|
| `001_unified_auth.sql` | ✅ |
| `002_employer_trial.sql` | ✅ |
| `005_signal_tables.sql` | ✅ |
| `006_signal_public_read.sql` | ✅ |
| `007_signal_topic_requests.sql` | ✅ |
| `028_deletion_requests.sql` | ✅ |
| `029_signal_analytical_profiles_seed.sql` | ✅ |
| `030_pharmacy_nadac.sql` | ✅ |

---

## PRODUCT DETAILS

### Parity Employer
- 30-day free trial (card required) → $99/mo locked 24 months · read-only after cancellation
- `STRIPE_PRICE_EMPLOYER_PRO`
- Level 2 claims analytics requires 835 EDI format
- Pharmacy benchmarking: any format via AI extraction, NADAC benchmarks loaded ✅
- Shared utility: `frontend/src/lib/cptLabel.js` (70+ CPT codes)
- Sample 835: `backend/data/sample/Midwest_Manufacturing_Dec2024.835`
- Sample pharmacy CSV: `backend/data/sample/Midwest_Manufacturing_Pharmacy_Dec2024.csv`

### Parity Broker
- Starter free (10 clients) / Pro $99/mo · `STRIPE_PRICE_BROKER_PRO`
- 20% commission 12 months on employer referrals (starts first paid month)
- Data commitment: "We will never contact your clients directly"

### Parity Provider
- Full product: contract integrity audit, denial pattern analysis, appeal letter generation (PDF via ReportLab), billing performance scorecard, trend tracking
- `backend/routers/`: `provider.py`, `provider_audit.py`, `provider_appeals.py`, `provider_shared.py`, `provider_subscription.py`, `provider_trends.py`
- No real users yet

### Parity Health
- Live at `health.civicscale.ai` ✅
- Bill analysis: PDF/image upload → AI extraction → Medicare benchmark report
- Denial appeals: upload/paste denial letter → structured analysis → appeal letter generator
- All anonymous — no auth required
- `backend/routers/health_analyze.py`

### Parity Signal
- Multi-dimensional claim scoring: `source_quality`, `data_support`, `reproducibility`, `consensus`, `recency`, `rigor`
- 4 analytical profiles operational: Balanced (default), Regulatory, Clinical, Patient
- Divergence highlighting when profiles reach different conclusions on same claim
- Premium-gated profile selector
- Q&A endpoint, topic requests, subscription tiers: free/standard/premium

---

## UNIFIED AUTH DECISIONS
| Decision | Choice |
|----------|--------|
| Session tokens | UUID in `sessions` table, 30-day expiry |
| Company types | employer / broker / provider |
| localStorage key | `cs_session_token` |
| API auth header | `Authorization: Bearer {token}` |
| Role model | admin / member / viewer |
| Invitations | Admin-only, no auto domain matching |

---

## TECH STACK
- Python3 / pip3 (never python/pip)
- FastAPI backend on Render
- React/Vite frontend on Vercel
- Supabase PostgreSQL
- Stripe (test mode — Session G swaps to live)
- Resend email
- Anthropic Claude API for AI features
- No feature branches — commit directly to main
