# Parity Employer — Build Plan
**Product:** Self-insured employer claims analytics
**Route:** civicscale.ai/billing/employer (product page + demo) / civicscale.ai/employer (app)
**Status:** Live with demo data — real employer pipeline is Phase 2
**Last updated:** March 4, 2026

---

## What Exists Today

### Routes
- `/billing/employer` — Public product page (no login required)
- `/billing/employer/demo` — Interactive demo with sample data (Midwest Manufacturing Co.)
- `/billing` — Billing products landing page (links to Employer, Provider, Health)
- `/employer` — Authenticated app (minimal — most functionality in demo currently)

### Frontend Components (frontend/src/components/)
- Product page: `EmployerProductPage.jsx` — AI differentiation copy, "How We're Different" cards (vs. Benefits Consultant, vs. TPA Reports, vs. Other Analytics), "What You Need" section, roadmap transparency
- Demo: `EmployerDemo.jsx` — Pre-loaded sample company with dashboard screens
- Demo screens: Executive Summary, Category Deep Dive, Provider Analysis, Savings Report

### Backend Endpoints (backend/routers/)
- `POST /api/employer/analyze` — Claims file upload + analysis
- `GET /api/employer/analyses` — Analysis history

### Demo Data (Midwest Manufacturing Co. — fictional)
- 500 covered lives
- Self-insured with Cigna TPA
- $7.5M annual claims
- ~200 pre-loaded claims across categories with benchmark variances
- Provider outlier examples
- Category-level drill-down with savings quantification

### Database Tables (Supabase)
- `employer_organizations` — Company profile
- `employer_analyses` — Analysis results
- User auth via Supabase magic link

---

## Known Issues — Fix Before New Features

### P0: Supabase security (check RLS on employer tables)

### P1: Demo-to-app transition
- Demo is compelling but the authenticated app path is thin
- Users who click "Get Started" after the demo need a clear onboarding flow
- Currently: magic link → upload claims file → analysis
- Needs: better onboarding that sets expectations about data format requirements

---

## Phase 1 Remaining — Limited Scope

Employer is deliberately the lowest-priority product in Phase 1. The demo validates the concept. Real employer contracts are a Phase 2 sales activity that depends on the Head of Commercial hire.

### Task 1.1: Claims Upload Format Documentation
**Priority:** Low — needed before first real employer, not before
**Files to create:**
- `frontend/src/components/EmployerDataGuide.jsx` — Data format guide showing exactly what file format, columns, and data the employer needs to provide
- Supported formats: CSV with columns (claim_id, date_of_service, cpt_code, billed_amount, allowed_amount, paid_amount, provider_name, provider_npi, diagnosis_code, member_id_hash)

**Acceptance criteria:**
- Accessible from the employer app onboarding flow
- Downloadable sample CSV template
- Clear explanation of each required field

**Verify:** Download template, fill with sample data, upload, confirm analysis runs

### Task 1.2: Employer Onboarding Flow Polish
**Priority:** Low — nice-to-have for Phase 1
**Files to modify:**
- `frontend/src/components/EmployerApp.jsx` — Add step-by-step onboarding: (1) Company profile, (2) Download data template, (3) Upload claims file, (4) View analysis

**Verify:** New user completes onboarding in under 5 minutes

---

## Phase 2 — The Real Build (Requires Head of Commercial)

Phase 2 is when Employer becomes a revenue product. All of these tasks depend on having a commercial lead who is selling to self-insured employers and benefits brokers.

### Task 2.1: First 3–5 Employer Contracts
- NOT a code task — commercial activity
- Head of Commercial identifies targets, runs demos, negotiates contracts
- Claude Code supports by fixing bugs from real-data testing

### Task 2.2: TPA Claims Feed Integration
**Files to create:**
- `backend/routers/employer_tpa.py` — Integration with TPA data feeds (Cigna, Aetna, UHC, BCBS formats)
- Each TPA has different file format — need adapter pattern

**Complexity:** High — TPA data formats are not standardized. Each integration is custom.

### Task 2.3: EOB Aggregation at Portfolio Scale
**Files to create:**
- `backend/routers/employer_eob.py` — Process consumer EOB data at employer level
- Cross-reference individual EOBs with claims data for complete picture

### Task 2.4: Employer Dashboard Enhancements
- Multi-period comparison (Q1 vs Q2, year-over-year)
- Provider scorecard (which providers in the network have highest anomaly rates)
- Savings projection (if identified errors are corrected, estimated annual savings)
- Exportable reports (PDF executive summary for benefits committee)

### Task 2.5: Benchmark Observations Integration
- Feed employer claims data into the benchmark observations database
- With employer consent, these become the highest-volume data source
- 500 employees × 12 months × 5 claims avg = 30,000 observations per employer per year

---

## Phase 2 Validation Gate

- **3–5 employer contracts** signed (Head of Commercial responsibility)
- **$500K annualized ARR** from employer product
- **TPA integration** with at least 1 major TPA (Cigna or UHC most likely)
- **Employer clients** report actionable findings in first analysis

---

## Strategic Note

Employer is the highest-revenue product in the Year 3 model ($1.44M from just 20 contracts at $72K ACV). But it's the product most dependent on a commercial hire — self-insured employers buy through benefits brokers and procurement processes that require a human sales relationship. The demo is built specifically to support that sales conversation. The Head of Commercial will use the demo as the primary sales tool.
