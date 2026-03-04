# Parity Provider — Build Plan
**Product:** Physician practice contract integrity, denial intelligence, revenue optimization
**Route:** civicscale.ai/billing/provider (product page + demo) / civicscale.ai/provider (app)
**Status:** Live with demo data — Phase 1 validation in progress
**Last updated:** March 4, 2026

---

## What Exists Today

### Routes
- `/billing/provider` — Public product page (no login required)
- `/billing/provider/demo` — Interactive demo with sample data (Lakeside Internal Medicine)
- `/provider` — Authenticated app for real practice data
- `/provider/login` — Magic link authentication + onboarding

### Frontend Components (frontend/src/components/)
- Product page: `ProviderProductPage.jsx` — AI differentiation copy, "How We're Different" cards, "What You Need" section, roadmap transparency
- Demo: `ProviderDemo.jsx` — Pre-loaded sample practice (6 physicians, 3 payers, 60 denials)
- App: `ProviderApp.jsx` — Main app shell
- `ProviderDashboard.jsx` — Analysis history, practice overview
- `ProviderUpload.jsx` — Contract rates template (Excel) + 835 file upload
- `ProviderAnalysis.jsx` — Contract integrity results
- `ProviderDenialIntelligence.jsx` — AI-powered denial analysis
- `ProviderContractorScorecard.jsx` — Billing contractor performance
- `ProviderRevenueGap.jsx` — Revenue gap estimation

### Backend Endpoints (backend/routers/)
- `POST /api/provider/analyze` — 835 file parsing + contract integrity analysis
- `POST /api/provider/denial-intelligence` — AI denial pattern analysis
- `POST /api/provider/contractor-scorecard` — AI contractor performance scoring
- `POST /api/provider/revenue-gap` — AI revenue gap estimation
- `GET /api/provider/analyses` — Analysis history for practice

### Backend Logic
- `provider_analyze.py` — Custom Python EDI 835 parser, contract rate comparison
- Phase 1B AI features all use Anthropic Claude API

### Database Tables (Supabase)
- `provider_practices` — Practice profile (name, specialty, payers)
- `provider_analyses` — Stored analysis results
- `provider_contract_rates` — Uploaded contracted rates
- User auth via Supabase magic link

### Demo Data
- Lakeside Internal Medicine & Cardiology (fictional)
- 6 physicians, 3 payer contracts (BCBS, Aetna, UHC)
- $4.2M annual revenue, 11.2% denial rate
- 60 pre-loaded denials with payer patterns
- Fee schedule showing payer rate comparisons for top 20 CPT codes
- 3-month seeded history with clickable historical reports

---

## Known Issues — Fix Before New Features

### P0: Supabase security (same as Health — check RLS on provider tables)

### P1: Demo vs. app routing clarity
- Verify that `/billing/provider` (product page) → `/billing/provider/demo` (demo) → `/provider` (real app) flow is clear to users
- Demo should have persistent banner: "This is sample data. Sign up to analyze your own practice."

---

## Phase 1 Remaining — CRITICAL PATH: Validation

### Task 1.1: Real Practice Validation (3–5 practices)
**Priority:** Highest — this is the Phase 1 gate for Provider
**This is NOT a code task — it's an outreach + testing task:**
- Fred to identify 3–5 warm contacts at physician practices
- Each practice uploads real 835 files and contract rates
- Claude Code supports by fixing any bugs that surface during real-data testing

**What Claude Code should be ready for:**
- 835 format variations (different clearinghouses format EDI differently)
- Edge cases in denial codes (non-standard CAS segments)
- Contract rate format variations (practices store rates differently)
- Performance issues on large files (some practices have 1,000+ lines per 835)

**Verify:** 3 practices complete end-to-end flow: upload 835 → upload contracts → view integrity analysis → view denial intelligence → view contractor scorecard

### Task 1.2: Multi-Month Trend Analysis (Phase 1 stretch / Phase 2 early)
**Priority:** Medium — enhances value for validated practices
**Files to create/modify:**
- `backend/routers/provider_trends.py` — Query 3+ months of analyses, generate AI narrative
- `frontend/src/components/ProviderTrends.jsx` — Trend visualization (denial rate over time, underpayment trends by payer, E&M distribution shifts)

**Acceptance criteria:**
- Practice with 3+ monthly 835 uploads sees trend dashboard
- AI narrative explains: "Your CO-45 denial rate with UHC increased from 8% to 14% over the last 3 months, concentrated in 99214 codes. This suggests a policy change or new review threshold."
- Charts: denial rate by payer by month, underpayment total by payer by month

**Verify:** Upload 3 months of 835 data for a practice, confirm trend charts render and AI narrative is clinically coherent

### Task 1.3: Full Appeal Letter Generator with Outcome Tracking
**Priority:** Medium — high value for practices, but needs validation data first
**Files to create/modify:**
- `backend/routers/provider_appeals.py` — Generate appeal letter from denial + clinical context
- `frontend/src/components/ProviderAppealLetter.jsx` — Display, edit, download appeal
- Supabase table: `provider_appeals` (practice_id, denial_id, letter_text, status, outcome, submitted_at, resolved_at)

**Acceptance criteria:**
- From denial intelligence view, user clicks "Draft Appeal" on a specific denial
- AI generates appeal letter citing: specific CMS guideline, contracted rate, clinical documentation reference, specific analytical choice payer made
- User can edit, download as PDF, mark as submitted
- After resolution, user logs outcome (paid, partially paid, denied again)

**Verify:** Select a CO-45 denial, generate appeal, confirm letter cites correct CMS guideline and denial-specific language, download PDF

---

## Phase 2 — Documented, Not Yet

- Multi-payer dashboard (compare performance across 3+ payers simultaneously)
- Credentialing gap detection
- Appeal outcome analytics (win rate by denial type, by payer, by appeal language)
- Revenue recovery tracker with dollar amounts
- PM system integration (Kareo, Athena, Epic) — requires API partnerships
- Pre-submission claim scrubbing (flag high-risk claims before they go to payer)

---

## Validation Success Criteria

Provider is the product most dependent on real-world validation. The demo proves the concept. Real 835 data proves the product. The validation gate:

- **3 practices** complete the full flow with real data
- **Zero critical bugs** in 835 parsing across different clearinghouse formats
- **Denial intelligence** correctly identifies at least 1 actionable pattern per practice
- **Contractor scorecard** produces results that the practice billing manager agrees with
- **One appeal letter** generated and submitted by a practice (outcome tracked)
