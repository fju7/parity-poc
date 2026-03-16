# Changelog

## Session N — 2026-03-16

### Signal Progressive Disclosure UX — Layers 1 & 2
Five changes to the Signal topic page (IssueDashboard.jsx + EvidenceQA.jsx):

**Change 1 — Layer 1: Score Ring + Verdict**
- 44x44px color-coded score ring at top of every topic (green 4+, amber 3-4, red <3)
- First two sentences of consensus summary as the verdict
- Secondary context line from issue description

**Change 2 — Layer 2: Score Bars**
- Per-category score bars below the verdict
- Name (120px) + progress bar (flex, 6px, color-coded) + score/5
- Clickable — scrolls to section. Arrow appears on hover
- Label: "Click any category to explore the evidence"

**Change 3 — Section Toggles**
- SummaryThemeSection now shows source count + score as metadata
- Chevron rotates right/down (not up/down)
- "Go deeper on this section" link at bottom of expanded content
- Clicking Go deeper selects that category and scrolls to Ask the Evidence

**Change 4 — Ask the Evidence UX**
- 4 suggested question chips above input (shown when no messages yet)
- Prominent "X of Y questions remaining" counter (turns red when <=2)
- Chips are clickable and pre-fill the input
- Added anonymization note: "Questions help us improve Signal."

**Change 5 — Contested Topic Banner**
- Amber banner for topics with `topic_type: "contested"` or `has_values_dimension: true`
- Shows "Empirical + Values" badge
- Inactive until a contested topic is added to the database

### Files Changed
- `frontend/src/components/signal/IssueDashboard.jsx` — Layer 1 score ring, Layer 2 score bars, section toggle metadata, contested banner
- `frontend/src/components/signal/EvidenceQA.jsx` — question chips, remaining count, anonymization note
- `CHANGELOG.md` — Session N entry

## Session M3 — 2026-03-16

### Staging Environment Setup
- Created `staging` branch from main, pushed to GitHub (`origin/staging`)
- Updated CLAUDE.md with "Development Workflow — Staging First" section
  (effective Session N onward: all dev on staging, Fred promotes to main)
- Created `backend/.env.staging` locally (not committed) with staging
  Supabase placeholders, shared Stripe/Anthropic/Resend keys
- Added `.env.staging` to `.gitignore`
- Created `backend/scripts/staging_setup.sh` documenting manual steps
  for Supabase, Render, and Vercel staging configuration

### Historical Rate Loader Investigation
- Verified `load_historical_rates.py` exists at `backend/scripts/`
- Script requires CMS carrier ZIP files for each prior year as input
- Historical tables (pfs/opps/clfs_rates_historical) exist but are empty
- CMS data files for 2024 and 2025 not present in repo — Fred action
  required to download from CMS.gov before loader can run

### Files Changed
- `CLAUDE.md` — added staging workflow section
- `.gitignore` — added `.env.staging`
- `backend/.env.staging` — created locally (not committed)
- `backend/scripts/staging_setup.sh` — new staging setup documentation
- `CHANGELOG.md` — added Session M3

## Session M2 — 2026-03-16

### Architecture Documentation (Item 1)
- Created `ARCHITECTURE.md` documenting:
  - Four-tier data architecture (in-memory CSV → historical Supabase → current Supabase → user data)
  - Data update schedule for all sources
  - Five products and their production URLs
  - Auth system (OTP flow, session tokens, company types)
  - Stripe integration (products, webhooks, trial logic)
  - All environment variables with descriptions

### Historical Rate Lookup Fix (Item 2)
- **Problem:** `lookup_rate()` always used current-year (2026) rates regardless of
  date of service on uploaded documents — a 2024 bill compared against 2026 rates
- **Finding:** `lookup_rate_historical()` already existed in benchmark.py with full
  PFS→OPPS→CLFS chain and graceful fallback. Historical tables
  (pfs_rates_historical, opps_rates_historical, clfs_rates_historical) exist but
  are empty (0 rows). rate_schedule_versions has 6 seed entries for 2026.
- **Fix:** Updated `lookup_rate()` to accept optional `date_of_service` parameter.
  When date falls in a prior year, delegates to `lookup_rate_historical()`.
  Falls back to current rates with warning: "Historical rates for [year] not
  available — using current CMS rates as approximation."
- Updated all 7 call sites across 4 files:
  - `employer_claims.py` (4 sites) — passes `service_date` from 835/CSV data
  - `broker.py` (1 site) — passes `service_date` from 835/CSV data
  - `provider_audit.py` (1 site) — updated tuple unpacking
  - `provider_shared.py` (1 site) — updated tuple unpacking
- Added `rate_year_note` to claims check API response (employer + broker)
- Added rate year note banner to `EmployerClaimsCheck.jsx` UI
- Return value of `lookup_rate()` changed from 4-tuple to 5-tuple:
  `(rate, source, locality, vintage, rate_note)`

### Files Changed
- `ARCHITECTURE.md` — new, comprehensive architecture documentation
- `backend/routers/benchmark.py` — `lookup_rate()` now accepts `date_of_service`, delegates to historical when prior year
- `backend/routers/employer_claims.py` — passes service_date to lookup_rate, adds rate_year_note to response
- `backend/routers/broker.py` — passes service_date to lookup_rate, adds rate_year_note to response
- `backend/routers/provider_audit.py` — updated lookup_rate tuple unpacking
- `backend/routers/provider_shared.py` — updated lookup_rate tuple unpacking
- `frontend/src/components/EmployerClaimsCheck.jsx` — rate year note banner

## Session M — 2026-03-16

### Smoke Test Verifications (Item 1)
All 5 checks passed with no fixes needed:
- 1a: No remaining `$149` text in employer frontend
- 1b: BrokerConnectCard admin email includes requester name, email, company, and benchmark data
- 1c: Provider saved-rates endpoint returns all saved payers for an account
- 1d: Health UploadView has text paste textarea with Analyze button
- 1e: Signal SummaryThemeSection and DebateItem both have `bg-white` contrast fix

### Data Freshness Audit (Item 2)
Audited all reference data tables in Supabase:
- `pharmacy_nadac`: 24,866 rows, effective dates 2021-02-01 to 2022-02-09
- `ncci_edits`: 2,210,396 rows, effective dates 1996-01-01 to 2026-01-01
- `provider_benchmark_observations`: 99 rows, all from 2026-03-14
- No tables found for: mue_values, asp_pricing, clfs_rates, pfs_rates, opps_rates

### Migration 041: data_versions table (Item 3)
- Created migration file: `backend/migrations/041_data_versions.sql`
- Table tracks: data_source, version_label, effective_from/to, loaded_at, next_update_due, record_count, notes
- Fred action required: run migration + INSERT statements in Supabase SQL Editor

### Staging Environment (Item 4)
- Deferred: CLAUDE.md forbids branch creation, and CivicScale_Staging_Setup_Guide.docx not found in repo
- Awaiting Fred's confirmation before creating staging branch

### NADAC Loader Fix (Item 5 — follow-up)
- Root cause: `load_nadac.py` used stale dataset UUID `dfa2ab14-...` pointing to
  an unlisted 2021-2022 archive — all 24,866 rows in `pharmacy_nadac` capped at
  effective_date 2022-02-09
- Fix: updated UUID to `fbb83258-...` (NADAC 2026 dataset from catalog.data.gov),
  added server-side date filter (`as_of_date > 2026-03-01`) to fetch only the
  latest weekly snapshot (~30K rows) instead of paginating all 1.9M rows
- Expected after reload: ~30,000 rows with effective_date through 2026-02-18
- Fred action: run reload command manually after deploying

### Files Changed
- `CLAUDE.md` — added Session M notes, updated migration list (next: 042)
- `CHANGELOG.md` — created, updated with NADAC fix
- `backend/migrations/041_data_versions.sql` — new migration
- `backend/scripts/load_nadac.py` — updated NADAC API UUID + date filter
