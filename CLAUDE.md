# CivicScale Platform — Parity Engine Monorepo

## Overview

This monorepo contains the **CivicScale** platform — a benchmark intelligence system with multiple product verticals all sharing a single React frontend and FastAPI backend. The platform is live at **civicscale.ai**.

### Brand Architecture

- **CivicScale** — parent infrastructure company (civicscale.ai). Builds the benchmark intelligence platform.
- **Parity** — the benchmark intelligence engine powering all verticals.
- **Parity Health** — consumer medical bill analysis tool (first vertical). Route: `/parity-health/*`
- **Parity Provider** — provider-facing reimbursement monitoring and audit tool. Route: `/provider/*`
- **Parity Employer** — employer benefits analytics dashboard. Route: `/employer/*`
- **Parity Signal** — AI-powered claim intelligence for public issues (e.g., GLP-1 drugs). Route: `/signal/*`

The CivicScale homepage (`/`) serves as the platform landing page. Legal pages (`/terms`, `/privacy`) and an investor page (`/investors`) are also top-level routes.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite 7 + Tailwind CSS 4 |
| Routing | React Router v7 (BrowserRouter) |
| PDF Parsing | PDF.js (Mozilla, browser-side only) |
| Charts | Recharts |
| Spreadsheet Parsing | xlsx (SheetJS) |
| Backend API | Python 3.11 + FastAPI |
| Data Processing | Pandas + openpyxl |
| AI | Anthropic Claude API (`anthropic` Python SDK) |
| Database | Supabase (PostgreSQL) with Row Level Security |
| Auth | Supabase Auth (magic link via Resend, email OTP) |
| Payments | Stripe (Signal subscriptions, Provider monitoring) |
| Email Delivery | Resend |
| Rate Database | CMS Medicare PFS + OPPS + CLFS (CSV flat files) |
| Frontend Hosting | Vercel |
| Backend Hosting | Render.com |
| Testing | Vitest + jsdom (frontend) |
| Linting | ESLint 9 (flat config) |

---

## Directory Structure

```
parity-poc/
├── CLAUDE.md                           ← this file
├── PARITY_SIGNAL_HANDOFF.md            ← Signal product design doc
├── README.md
├── supabase-schema.sql                 ← base profiles table schema
├── .gitignore
│
├── frontend/                           ← React SPA (Vite)
│   ├── src/
│   │   ├── main.jsx                    ← top-level router (all product routes)
│   │   ├── App.jsx                     ← Parity Health app (/parity-health/*)
│   │   ├── ProviderApp.jsx             ← Parity Provider app (/provider/*)
│   │   ├── SignalApp.jsx               ← Parity Signal app (/signal/*)
│   │   ├── index.css                   ← Tailwind import + print styles
│   │   ├── components/
│   │   │   ├── CivicScaleHomepage.jsx  ← platform landing page (/)
│   │   │   ├── CivicScaleHomepage.css  ← (exception: custom CSS for homepage)
│   │   │   ├── UploadView.jsx          ← bill upload (drag-drop + sample bill)
│   │   │   ├── ProcessingView.jsx      ← animated processing status
│   │   │   ├── ReportView.jsx          ← bill analysis report
│   │   │   ├── SignInView.jsx          ← Parity Health auth
│   │   │   ├── ConsentView.jsx         ← HIPAA-style consent
│   │   │   ├── OnboardingView.jsx      ← user profile collection
│   │   │   ├── ManualEntryView.jsx     ← manual CPT code entry
│   │   │   ├── PasteTextView.jsx       ← paste bill text
│   │   │   ├── ImageUploadView.jsx     ← image-based bill upload
│   │   │   ├── AIParseModal.jsx        ← AI-assisted bill parsing
│   │   │   ├── EOBDetectedView.jsx     ← EOB detection handling
│   │   │   ├── BillHistoryView.jsx     ← saved bill history
│   │   │   ├── ErrorView.jsx           ← error states
│   │   │   ├── AppHeader.jsx           ← Parity Health header
│   │   │   ├── Toast.jsx               ← toast notifications
│   │   │   ├── EmployerDashboard.jsx   ← employer analytics
│   │   │   ├── EmployerLandingPage.jsx ← employer marketing
│   │   │   ├── EmployerLoginPage.jsx   ← employer auth
│   │   │   ├── ProviderAuditPage.jsx   ← provider audit workflow
│   │   │   ├── ProviderAuditReport.jsx ← audit report display
│   │   │   ├── ProviderAuditAdmin.jsx  ← admin audit management
│   │   │   ├── PublicAuditReport.jsx   ← shareable audit report (/report/:token)
│   │   │   ├── AuditAccount.jsx        ← audit account management
│   │   │   ├── AuditStandalone.jsx     ← standalone audit entry (/audit)
│   │   │   ├── BillingLanding.jsx      ← billing products hub (/billing)
│   │   │   ├── InvestorsPage.jsx       ← investor deck page
│   │   │   ├── TermsPage.jsx           ← terms of service
│   │   │   ├── PrivacyPage.jsx         ← privacy policy
│   │   │   └── EmailOtpInput.jsx       ← email OTP component
│   │   ├── components/signal/          ← Signal-specific components
│   │   │   ├── SignalLanding.jsx       ← Signal homepage
│   │   │   ├── SignalHeader.jsx        ← Signal navigation
│   │   │   ├── SignalFooter.jsx        ← Signal footer
│   │   │   ├── SignalLogin.jsx         ← Signal auth
│   │   │   ├── IssueDashboard.jsx      ← topic dashboard with claims
│   │   │   ├── ClaimCard.jsx           ← individual claim display
│   │   │   ├── ClaimDetail.jsx         ← expanded claim view
│   │   │   ├── CategoryTabs.jsx        ← swipeable category tabs
│   │   │   ├── ScoreBadge.jsx          ← evidence score badge
│   │   │   ├── EvidenceBadge.jsx       ← evidence category badge
│   │   │   ├── EvidenceQA.jsx          ← evidence-grounded Q&A
│   │   │   ├── ConsensusIndicator.jsx  ← consensus status display
│   │   │   ├── SourceCard.jsx          ← source citation card
│   │   │   ├── GlossaryText.jsx        ← inline glossary
│   │   │   ├── WeightAdjuster.jsx      ← analytical paths weight UI
│   │   │   ├── TierGate.jsx            ← subscription tier gating
│   │   │   ├── TopicRequestForm.jsx    ← premium topic request
│   │   │   ├── PricingView.jsx         ← subscription pricing page
│   │   │   ├── AccountView.jsx         ← user account management
│   │   │   ├── MethodologyView.jsx     ← scoring methodology page
│   │   │   └── AdminRequestsDashboard.jsx ← admin topic requests
│   │   ├── modules/
│   │   │   ├── extractBillData.js      ← PDF extraction (browser-side)
│   │   │   ├── extractBillData.test.js ← extraction tests
│   │   │   ├── scoreAnomalies.js       ← anomaly scoring engine
│   │   │   ├── scoreAnomalies.test.js  ← scoring tests
│   │   │   ├── eobExtractor.js         ← EOB detection
│   │   │   ├── codingIntelligence.js   ← coding validation client
│   │   │   └── nppesLookup.js          ← NPPES provider lookup
│   │   ├── lib/
│   │   │   ├── supabase.js             ← Supabase client singleton
│   │   │   ├── localBillStore.js       ← localStorage bill persistence
│   │   │   ├── redirectOrigin.js       ← auth redirect helper
│   │   │   └── signalAnalytics.js      ← Signal event tracking
│   │   └── test-setup.js              ← Vitest setup
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── eslint.config.js
│   ├── vercel.json                     ← SPA rewrites for Vercel
│   ├── .env.example
│   └── .env.production
│
├── backend/                            ← FastAPI Python API
│   ├── main.py                         ← app entry point, CORS, router registration
│   ├── supabase_client.py              ← shared Supabase service-role client
│   ├── requirements.txt
│   ├── runtime.txt                     ← Python 3.11.9
│   ├── render.yaml                     ← Render.com deployment config
│   ├── .env.example
│   ├── routers/
│   │   ├── benchmark.py                ← POST /api/benchmark (CMS rate lookup)
│   │   ├── ai_parse.py                 ← AI-assisted bill parsing
│   │   ├── eob_parse.py                ← EOB document parsing
│   │   ├── coding_intelligence.py      ← CPT coding validation
│   │   ├── health_analyze.py           ← bill analysis orchestration
│   │   ├── employer.py                 ← /api/employer/* endpoints
│   │   ├── provider.py                 ← /api/provider/* (meta-router)
│   │   ├── provider_audit.py           ← audit CRUD, analysis, reports
│   │   ├── provider_appeals.py         ← appeal letter generation
│   │   ├── provider_subscription.py    ← provider Stripe integration
│   │   ├── provider_trends.py          ← trend computation helpers
│   │   ├── provider_shared.py          ← shared constants, models
│   │   ├── benchmark_observations.py   ← benchmark data observations
│   │   ├── signal_events.py            ← Signal event capture
│   │   ├── signal_stripe.py            ← Signal Stripe integration
│   │   ├── signal_metrics.py           ← Signal platform metrics
│   │   ├── signal_qa.py                ← Signal evidence-grounded Q&A
│   │   ├── signal_topic_request.py     ← Signal topic requests
│   │   └── signal_notify_deliver.py    ← Signal notification delivery
│   ├── utils/
│   │   ├── rate_versioning.py          ← historical rate version support
│   │   └── parse_835.py                ← ANSI 835 remittance parser
│   ├── data/
│   │   ├── pfs_rates.csv               ← CMS PFS rates (~841K rows)
│   │   ├── opps_rates.csv              ← CMS OPPS rates (~7.3K rows)
│   │   ├── clfs_rates.csv              ← CMS CLFS rates (~2K rows)
│   │   └── zip_locality.csv            ← ZIP-to-locality crosswalk (~43K rows)
│   ├── scripts/
│   │   ├── process_pfs.py              ← CMS PFS data processor
│   │   ├── process_opps.py             ← CMS OPPS data processor
│   │   ├── process_clfs.py             ← CMS CLFS data processor
│   │   ├── load_historical_rates.py    ← historical rate loader
│   │   ├── load_coding_data.py         ← coding intelligence data
│   │   ├── seed_employer_data.py       ← employer demo data seeder
│   │   ├── seed_provider_demo.py       ← provider demo data seeder
│   │   ├── signal/                     ← Signal pipeline scripts
│   │   │   ├── run_pipeline.py         ← full pipeline orchestrator
│   │   │   ├── run_full_topic.py       ← single topic pipeline
│   │   │   ├── 00_discover_sources.py  ← web source discovery
│   │   │   ├── collect_sources.py      ← source collection
│   │   │   ├── extract_claims.py       ← AI claim extraction
│   │   │   ├── score_claims.py         ← AI evidence scoring
│   │   │   ├── map_consensus.py        ← consensus mapping
│   │   │   ├── generate_summary.py     ← summary generation
│   │   │   ├── generate_notifications.py ← notification generation
│   │   │   ├── detect_changes.py       ← evidence change detection
│   │   │   └── topic_config.py         ← topic configuration
│   │   └── README_rate_versioning.md
│   ├── migrations/                     ← Supabase SQL migrations (002–018)
│   └── static/
│       └── contract_rates_template.xlsx ← provider rate upload template
│
├── docs/                               ← design docs and build plans
│   ├── build-plans/                    ← detailed build specifications
│   └── *.md                            ← various spec documents
│
└── data/                               ← raw data (NOT committed to git)
    ├── cms-pfs/                        ← raw CMS PFS downloads
    ├── cms-opps/                       ← raw CMS OPPS downloads
    ├── cms-clfs/                       ← raw CMS CLFS downloads
    ├── signal/sources/                 ← Signal source data
    └── test-bills/                     ← real test bills (NEVER in git)
```

---

## Critical Rules (Never Violate These)

1. **No PHI to server.** The `/api/benchmark` endpoint accepts only: `zipCode`, `lineItems` array of `{code, codeType, billedAmount}`, and optionally `serviceDate`. No names, dates of birth, diagnosis codes, insurance IDs, or provider addresses. Ever. The patient's PDF is parsed entirely in the browser.

2. **No test bills in git.** The `data/test-bills/` directory is in `.gitignore`. Real medical bills must never be committed.

3. **Raw CMS files not committed.** `data/cms-pfs/`, `data/cms-opps/`, `data/cms-clfs/` contain large downloads — `.gitignore`d. Only processed CSVs in `backend/data/` are committed.

4. **Brand colors.** Primary navy `#1B3A5C`, accent teal `#0D7377`, clean white backgrounds, Arial font family. Amber `#F59E0B` for warnings, red `#EF4444` for severe anomaly flags (>3x benchmark).

5. **Tailwind only.** Do not write custom CSS except for the CivicScale homepage (`CivicScaleHomepage.css`), the Investors page (`InvestorsPage.css`), print styles, and scrollbar-hide utilities in `index.css`.

6. **No PHI in Supabase.** Employer user IDs are SHA-256 hashed before storage. Provider data is tied to `user_id` only — no patient-identifiable information.

7. **Work on main branch.** This repo uses a single-branch workflow. Commit and push directly to main unless instructed otherwise.

---

## Architecture Notes

### Frontend Routing

The app uses React Router v7 with a flat route structure in `main.jsx`:

| Route Pattern | Component | Description |
|---|---|---|
| `/` | `CivicScaleHomepage` | Platform landing page |
| `/parity-health/*` | `App` (health) | Consumer bill analysis tool |
| `/provider/*` | `ProviderApp` | Provider reimbursement dashboard |
| `/signal/*` | `SignalApp` | Claim intelligence platform |
| `/employer/*` | Employer pages | Employer benefits analytics |
| `/billing/*` | Billing landing + product pages | Product marketing pages |
| `/audit`, `/audit/account` | Audit pages | Standalone audit entry |
| `/report/:token` | `PublicAuditReport` | Shareable audit reports |
| `/terms`, `/privacy`, `/investors` | Legal/marketing pages | Static content |

### Backend API Routes

All routers are registered in `backend/main.py`:

| Prefix | Router | Description |
|---|---|---|
| `/api/benchmark` | `benchmark.py` | CMS rate lookup (POST) |
| `/api/ai-parse` | `ai_parse.py` | AI bill text parsing |
| `/api/eob-parse` | `eob_parse.py` | EOB document parsing |
| `/api/employer/*` | `employer.py` | Employer dashboard |
| `/api/provider/*` | `provider.py` | Provider hub (audit, appeals, subscriptions) |
| `/api/signal/*` | Signal routers | Events, Stripe, metrics, Q&A, topics, notifications |
| `/api/health-analyze` | `health_analyze.py` | Bill analysis |
| `/api/benchmark-observations` | `benchmark_observations.py` | Benchmark data |

### Data Flow — Parity Health (Bill Analysis)

1. User drops PDF in browser
2. `extractBillData.js` parses PDF using PDF.js (no server call)
3. Extracted CPT codes + ZIP sent to `POST /api/benchmark`
4. Backend looks up rates: ZIP → locality via `zip_locality.csv`, then locality → rates via `pfs_rates.csv` / `opps_rates.csv` / `clfs_rates.csv`
5. Optional: `codingIntelligence.js` runs coding validation checks
6. `scoreAnomalies.js` computes anomaly scores (billed ÷ benchmark)
7. Report rendered with flagged items

### Data Flow — Parity Signal

1. Pipeline scripts (`backend/scripts/signal/`) discover sources, extract claims via Claude API, score evidence, map consensus, generate summaries
2. All data stored in Supabase (`signal_*` tables)
3. Frontend fetches from Supabase directly (RLS-enabled public read)
4. Stripe integration handles subscriptions with four tiers: free, basic, standard, premium

### Database (Supabase)

- Base schema in `supabase-schema.sql` (profiles table)
- Migrations in `backend/migrations/002-018.sql` (run manually in Supabase SQL Editor)
- Row Level Security enabled on all tables (migration 009)
- Key table groups:
  - `profiles` — user profiles
  - `provider_*` — provider profiles, contracts, audits, appeals, subscriptions
  - `signal_*` — issues, sources, claims, scores, consensus, subscriptions, events
  - `employer_*` — employer codes, contributions
  - `benchmark_*` — rate observations and versioning

### Authentication

- **Supabase Auth** with magic links (Resend) and email OTP
- Frontend client in `frontend/src/lib/supabase.js`
- Backend service-role client in `backend/supabase_client.py`
- Provider and Signal apps have their own auth flows
- Employer uses code-based access (no Supabase auth)

### External Services

| Service | Purpose | Config |
|---|---|---|
| Supabase | Database + Auth | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (backend), `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (frontend) |
| Stripe | Payments | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, various `STRIPE_PRICE_*` keys |
| Anthropic Claude | AI parsing + Signal pipeline | `ANTHROPIC_API_KEY` (implicit in anthropic SDK) |
| Resend | Email delivery | `RESEND_API_KEY` |
| NPPES API | Provider NPI lookup | No key needed (public API) |

---

## Development Commands

```bash
# Frontend
cd frontend
npm install
npm run dev          # starts on http://localhost:5173
npm run build        # production build
npm run lint         # ESLint
npx vitest           # run tests
npx vitest run       # run tests once (CI mode)

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload  # starts on http://localhost:8000

# Data processing (run from backend/ with venv active)
python scripts/process_pfs.py      # process CMS PFS carrier files
python scripts/process_opps.py     # process CMS OPPS rates
python scripts/process_clfs.py     # process CMS CLFS rates

# Signal pipeline (run from backend/ with venv active)
python scripts/signal/run_pipeline.py      # full pipeline
python scripts/signal/run_full_topic.py    # single topic
```

### Environment Variables

Copy `.env.example` files in both `frontend/` and `backend/` to `.env` and fill in values. See `.env.example` files for the full list. Key variables:

- **Frontend:** `VITE_API_URL`, `VITE_SITE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- **Backend:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `RESEND_API_KEY`, `CRON_SECRET`

Production frontend env is in `frontend/.env.production` (API URL: `https://parity-poc-api.onrender.com`).

---

## Deployment

| Component | Platform | Config |
|---|---|---|
| Frontend | Vercel | `frontend/vercel.json` — SPA rewrites for all routes |
| Backend | Render.com | `backend/render.yaml` — Python 3.11.9, uvicorn |
| Database | Supabase | Hosted PostgreSQL with RLS |

Production URLs:
- Frontend: `https://civicscale.ai` (Vercel)
- Backend API: `https://parity-poc-api.onrender.com` (Render)
- CORS allows: `localhost:5173`, `civicscale.ai`, `www.civicscale.ai`, any `*.vercel.app` preview

---

## CMS Rate Data

The backend serves three CMS rate datasets, loaded into Pandas DataFrames at startup:

| File | Rows | Source | Columns |
|---|---|---|---|
| `pfs_rates.csv` | ~841K | CMS Physician Fee Schedule 2026 | `cpt_code, carrier, locality_code, nonfacility_amount, facility_amount` |
| `opps_rates.csv` | ~7.3K | CMS OPPS 2026 | `apc_code, hcpcs_code, payment_rate, description` |
| `clfs_rates.csv` | ~2K | CMS CLFS 2026 Q1 | `hcpcs_code, payment_rate, description` |
| `zip_locality.csv` | ~43K | CMS ZIP-to-locality crosswalk | `zip_code, carrier, locality_code, state` |

**Lookup logic:** ZIP code → `zip_locality.csv` → `(carrier, locality_code)` → `pfs_rates.csv` → geographically adjusted rate.

Rate versioning is supported via `utils/rate_versioning.py` for historical bill dates.

---

## Testing

Frontend tests use Vitest with jsdom environment:

```bash
cd frontend
npx vitest run                    # run all tests
npx vitest run src/modules/       # run module tests only
```

Test files follow `*.test.js` naming convention alongside source files.

---

## Parity Signal — Design Principles

Signal has its own detailed design document in `PARITY_SIGNAL_HANDOFF.md`. Key architectural constraints:

1. **Score claims, not articles.** Extract individual assertions and score each one.
2. **No truth/false declarations.** Score evidence strength with transparent methodology.
3. **Per-dimension scores required.** Six dimensions (source quality, data support, reproducibility, consensus, recency, rigor) stored separately — never just composites. Required for Analytical Paths feature.
4. **All weights disclosed.** Default weights are published in methodology.
5. **Mobile-first design.** Signal is phone-optimized (unlike billing products which are laptop-first).
6. **Event capture from day one.** Every interaction logged via `signal_events` table.

---

## What NOT to Do

- Do not send PHI (names, DOB, diagnoses, insurance IDs) to any backend endpoint
- Do not commit real medical bills or raw CMS data files to git
- Do not write custom CSS — use Tailwind utilities (exceptions: homepage, investors page, print styles)
- Do not hardcode Signal scoring weights — they must be configurable JSONB
- Do not store only composite scores in Signal — per-dimension scores are required
- Do not skip event capture in Signal features
- Do not design Signal UI for desktop first — it is mobile-first
- Do not build Phase 1 features (Turquoise Health API, user accounts for Health, employer claims feeds) unless explicitly approved
