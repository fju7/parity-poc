# Parity Health — Build Plan
**Product:** Consumer medical bill analysis
**Route:** civicscale.ai/parity-health
**Status:** Live — Phase 1 in progress
**Last updated:** March 4, 2026

---

## What Exists Today

### Routes
- `/parity-health` — Main bill analysis app (upload, paste, photo, analysis, history)
- `/parity-health/login` — Magic link authentication

### Frontend Components (frontend/src/components/)
- `ParityHealthApp.jsx` — Main app shell, routing, auth state
- `BillUpload.jsx` — PDF upload flow
- `TextInput.jsx` — Paste claim text from insurance portal
- `ImageUpload.jsx` — Photo/screenshot upload (JPG, PNG, HEIC)
- `ConfirmationScreen.jsx` — Extracted data review before analysis
- `BillAnalysis.jsx` — Analysis results display with benchmark comparison
- `BillHistory.jsx` — Dashboard of past analyses
- `ItemizedBillLetter.jsx` — Generates itemized bill request letter
- `EOBDetection.jsx` — Identifies and extracts EOB data

### Backend Endpoints (backend/routers/)
- `POST /api/health/analyze` — PDF bill analysis (existing flow)
- `POST /api/health/analyze-text` — Pasted text extraction via Claude
- `POST /api/health/analyze-image` — Image extraction via Claude vision
- `POST /api/health/analyze-confirmed` — User-confirmed line items → benchmark analysis
- `POST /api/health/save-observation` — Saves anonymized benchmark observation

### Backend Logic (backend/routers/)
- `health_analyze.py` — Main analysis router
- `benchmark_observations.py` — Anonymized data capture (CPT, amount, insurer, region, specialty)

### Database Tables (Supabase)
- `bill_analyses` — Stored analysis results
- `benchmark_observations` — Anonymized commercial rate data points
- User auth via Supabase magic link

### Benchmark Data (loaded at startup)
- CMS PFS: 841K rates (national + geographic adjustment via 43K ZIP→locality mappings)
- CMS OPPS: 7.3K outpatient rates
- CMS CLFS: 2K lab codes
- NCCI edits: 2.2M edit pairs
- MUE limits: 15K limits

### Integrations
- Anthropic Claude API (bill extraction, image vision, analysis narrative)
- Supabase (auth, storage, benchmark observations)

---

## Known Issues — Fix Before New Features

### P0: Render deploy failure (RESOLVED)
- Transient build timeout on benchmark_observations commit
- Next deploy succeeded — backend responding normally

### P0: Supabase security warnings (4 errors)
- **Action:** Check Security Advisor for specific warnings
- **Likely cause:** Tables without RLS or overly permissive policies
- **Fix:** Enable RLS on any unprotected tables, tighten policies where needed
- **Verify:** Security Advisor shows 0 errors after fix

---

## Phase 1 Remaining — In Dependency Order

### Task 1.1: Turquoise Health Commercial Rate Integration
**Priority:** High — transforms analysis quality from Medicare proxy to actual commercial rates
**Files to create/modify:**
- `backend/data/turquoise/` — Rate data storage (format TBD based on Turquoise API/data feed)
- `backend/routers/health_analyze.py` — Add Turquoise lookup alongside CMS benchmarks
- Display: Show commercial rate alongside Medicare rate when available

**Acceptance criteria:**
- For CPT codes where Turquoise data exists, show: "Medicare benchmark: $X | Commercial benchmark (Turquoise): $Y"
- Fall back to Medicare-only when Turquoise data not available
- Data vintage label shows Turquoise data date

**Dependency:** Turquoise Health data access agreement (external — Fred to negotiate)

**Verify:** Run analysis on a common CPT code (e.g., 99213) and confirm both Medicare and commercial benchmarks appear

### Task 1.2: Attorney Referral Capture
**Priority:** Medium — Phase 2 revenue stream, but capture mechanism needed in Phase 1
**Files to create/modify:**
- `frontend/src/components/AttorneyReferral.jsx` — Modal/section shown when analysis flags potential legal issues
- `backend/routers/health_referral.py` — Store referral interest
- Supabase table: `attorney_referrals` (user_id, analysis_id, issue_type, created_at)

**Acceptance criteria:**
- When analysis flags billing errors above a threshold (e.g., >$500 total overcharge), show option: "This may warrant professional review. Want us to connect you with a medical billing attorney?"
- Capture interest with one click (no form)
- Admin can view referral requests

**Verify:** Trigger a high-overcharge analysis, confirm referral option appears, click it, confirm row in `attorney_referrals`

### Task 1.3: Parity Health Monetization
**Priority:** Medium — needs to happen before Phase 2
**Decisions needed (Fred):**
- Per-analysis pricing vs. subscription?
- Free tier limit (e.g., 3 analyses/month)?
- Price point?

**Files to create/modify (once decisions made):**
- `backend/routers/health_stripe.py` — Checkout, portal, tier check (pattern from Signal)
- `frontend/src/components/HealthPricing.jsx` — Pricing display
- `frontend/src/components/HealthTierGate.jsx` — Enforce limits
- Supabase table: `health_subscriptions`

**Verify:** Free user hits limit, sees upgrade prompt, completes Stripe checkout, can analyze again

---

## Phase 2 — Documented, Not Yet

- Fair Health benchmark integration (non-profit aggregator, widely cited in legal proceedings)
- Intelligence Engine Tier 3: clinical appropriateness scoring
- Community benchmark display (requires 100+ observations per metro per CPT)
- Attorney referral network build-out (25+ firms, geographic coverage)
- Advanced anomaly scoring with provider-level pattern detection
- Integration with Turquoise Health MRF data for hospital-specific rates

---

## Benchmark Observations Flywheel Status

**Current state:** Collecting. First observation recorded (CPT 88305, $57.57, Cigna, Tampa).

**Privacy thresholds (enforced in code):**
- 5+ observations → show any benchmark for CPT+region
- 10+ observations → show insurer-specific benchmarks  
- 20+ observations → show percentile ranges
- Individual observations never exposed via any API

**Phase 1 goal:** Accumulate observations. Medicare remains primary benchmark.
**Phase 2 trigger:** 100+ observations per metro per CPT → display community benchmarks alongside Medicare.
