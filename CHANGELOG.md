# Changelog

## Session W+ — 2026-03-17

### W+0 — Platform Cases Table
- Migration 049: platform_cases table (unified case tracking for Provider appeals + Health disputes)
- Backend: platform_cases router with create, list, resolve, and send-reminders endpoints

### W+1 — Provider: Track This Appeal
- "Track this appeal" prompt in appeal modal auto-creates platform_case with all context
- Confirmation: "Appeal tracked. You'll be reminded to record the outcome in 30 days."

### W+2 — Provider: Open Appeals Queue
- OpenAppealsQueue component at top of Appeals tab shows platform_cases with status=open
- Outcome buttons: Won / Lost / Partial / Withdrawn
- Amber "Follow up" badge on cases > 30 days old

### W+3 — Health: Track This Issue
- FlaggedItemDetail component replaces inline expanded row in ReportView
- Recommended next action per flag type (overbilling, network, coding)
- Signal clinical note when CPT has coverage (score >= 3.5)
- "Track it" button creates platform_case with product=health

### W+4 — Health: Open Issues Queue
- HealthOpenIssues component at /open-issues in Health app nav
- Shows open platform_cases for health product
- "Resolved" and "Dropped" buttons with follow-up badge at 14 days

### W+5 — Reminder Endpoint
- POST /api/platform/send-case-reminders — finds stale open cases, sends emails
- Provider: 30 days, Health: 14 days
- Email via Resend with product-specific messaging and deep links

### W+6 — Signal Flywheel: Both Products
- Admin analytics now shows Provider Cases and Health Disputes from platform_cases
- Per-topic: total, open, won, lost, win/resolution rate, top codes
- Legacy appeal outcomes section preserved

## Session W — 2026-03-17

### W1 — Employer Claims: Clinical Context Cards
- SignalContextCard component added to flagged procedures in EmployerClaimsCheck
- Collapsible card shows topic title, score, key claims with consensus badges, link to Signal
- Only shown when Signal coverage exists (coverage != 'none')

### W2 — Employer Action Plan: Signal Recommendations
- SignalActionPlanCards component fetches Signal evidence for top flagged CPTs
- When score >= 3.5, adds "Clinical appropriateness question" recommendation with link to Signal topic
- Indigo-themed cards appear after existing action plan steps

### W3 — Broker Renewal: Signal Evidence Context
- RenewalPrepReport talking points enhanced with Signal evidence for high-cost CPTs
- Shows score, strength assessment, and active debate warnings
- Signal talking points appear with indigo accent below standard talking points

### W4 — Broker CAA Letter: Evidence-Informed Questions
- SignalCAAAppendix component fetches Signal evidence for common high-volume CPTs
- "Signal Intelligence: Evidence-Informed Questions" section with per-topic clinical criteria questions
- Includes top 2 claims and link to evidence dashboard for each topic

### W5 — Data Flywheel: Appeal Outcomes in Admin Analytics
- Backend: appeal outcomes aggregation added to /admin/analytics endpoint
- Per-topic: total appeals, won, lost, win rate, top denial codes
- Frontend: "Appeal Outcomes (Data Flywheel)" section in AdminAnalytics
- Hidden when no outcomes recorded

## Session V — 2026-03-17

### V0 — Fix Signal Intelligence API
- Verdict now pulls from signal_summaries (topic-specific text, not generic score description)
- Analytical paths deduplicated by name — no more duplicate entries

### V1 — Evidence-Grounded Appeal Letters
- Appeal letter generation now calls Signal Intelligence API for evidence
- New prompt section: "Supporting Clinical Evidence from Signal Intelligence"
- Top 3 challenging evidence claims with scores cited in letter
- Signal evidence panel added to appeal modal in frontend (indigo card with scores)

### V2 — Denial Pattern Analysis with Signal Intelligence
- Denial pattern table now shows Signal score column for each CPT code
- Red flag (⚑) when denial rate is high AND Signal score is high (systematic underpayment)
- New "Systematic Underpayment Flags" section highlights flagged denials with links to Signal topics

### V3 — Appeal Outcome Tracking
- Migration 048: provider_appeal_outcomes table (appeal_id, cpt_code, denial_code, payer, signal_topic_slug, outcome)
- Outcome recording writes to provider_appeal_outcomes when appeal status set to won/lost
- "Record Outcome" buttons (Won/Lost) added to appeal modal
- Signal topic slug auto-populated via CPT mapping for data flywheel

## Session U — 2026-03-17

### U0 — Classify All Remaining Topics
- Classified 6 topics (975 claims total), all written directly to production DB
- PostgREST cache refreshed — direct writes now work for claim_type/consensus_type
- All 9 Signal topics now have full claim_type and consensus_type classifications

### U1 — Signal Intelligence API
- New router: backend/routers/signal_intelligence.py
- GET /api/signal/evidence-for-code — CPT code to Signal evidence lookup
- GET /api/signal/denial-intelligence — denial code challenge evidence
- Registered in main.py

### U2 — CPT Code to Signal Topic Mapping
- Migration 045: signal_cpt_mappings table (cpt_code, topic_slug, relevance_score)
- Migration 046: seeded 40 CPT mappings across all 9 topics
- Covers high-volume Medicare CPT codes mapped to relevant Signal topics

### U3 — Payer Coverage Policy Source Type
- Added 'payer_coverage_policy' to SourceCard type labels/colors (indigo badge)
- Migration 047: 3 test payer coverage policy sources for mmr-vaccine-autism
- No schema change needed — source_type is a free text field

## Session T — 2026-03-17

### T0 — Staging Verified
- Staging branch current, breast cancer topic with 207 claims confirmed
- Production classification SQL ready at backend/scripts/signal/output/

### T1 — MMR Vaccine and Autism (Category B: manufactured controversy)
- Full pipeline: 32 sources, 128 claims, 6 categories, 33 min
- Classification: institutional 58 (45%), efficacy 39 (30%), safety 25 (20%), values_embedded 6 (5%)
- Consensus: strong_consensus 125 (98%), active_debate 2 (2%), manufactured_controversy 1 (1%)
- Topic score: 3.77 — correctly reflects overwhelming scientific consensus
- Quality review: PASS

### T2 — mRNA Vaccines and Myocarditis (genuine safety signal)
- Full pipeline: 32 sources, 130 claims, 6 categories, 34 min
- Classification: safety 75 (58%), institutional 48 (37%), values_embedded 5 (4%), efficacy 2 (2%)
- Consensus: strong_consensus 84 (65%), active_debate 42 (32%), genuine_uncertainty 4 (3%)
- Topic score: 3.63 — correctly reflects genuine scientific complexity
- Quality review: PASS

### T3 — Quality Review Gate
- Migration 044: added quality_review_status column to signal_issues (pending|approved|rejected)
- Backend: /api/signal/topics now filters to approved topics only
- Backend: new /api/signal/admin/review-topics and /api/signal/admin/review-topic endpoints
- Frontend: AdminReviewDashboard component at /signal/admin/review
- Breast cancer topic marked as approved in migration

## Session S — 2026-03-17

### S1 — Add claim_type and consensus_type to signal_claims
- Migration 043: added `claim_type` (efficacy|safety|institutional|values_embedded|foundational_values) and `consensus_type` (strong_consensus|active_debate|manufactured_controversy|genuine_uncertainty) columns with CHECK constraints
- Applied to staging Supabase; production pending

### S2 — Classification Pipeline Step
- Created `classify_claims.py` — Claude-powered claim classification script
- Updated `run_pipeline.py`: inserted Classify Claims as new step 3, pipeline now 8 steps (was 7)
- Classified all 207 breast cancer claims:
  - claim_type: efficacy 113 (55%), institutional 73 (35%), safety 12 (6%), values_embedded 9 (4%)
  - consensus_type: strong_consensus 158 (76%), active_debate 37 (18%), genuine_uncertainty 12 (6%)
- Classifications applied via SQL script (PostgREST schema cache workaround)

### S3 — Institutional Conduct Scoring Prompt
- Added `INSTITUTIONAL_SCORE_SYSTEM_PROMPT` to `score_claims.py` with three-part assessment: factual record, public record evidence, interpretive dispute
- `score_batch()` routes institutional claims to specialized prompt automatically
- Institutional claims batched separately per category for correct prompt routing

### S4 — Layer 3 UI: claim_type Badges and consensus_type Indicators
- ClaimCard: added color-coded claim_type badges (blue=efficacy, red=safety, purple=institutional, amber=values_embedded, gray=foundational_values)
- ClaimCard: added consensus_type icons (green lock=strong_consensus, orange arrows=active_debate, red flag=manufactured_controversy, gray ?=genuine_uncertainty)
- Key Debates panel: now shows individual debated claims (active_debate + manufactured_controversy) as expandable ClaimCards
- Frontend build: clean, no errors

## Session R — 2026-03-16

### R0 — Session Q Promoted to Production
- Merged staging to main: broker/employer Stripe Origin fix + OTP branding
- No frontend rebuild needed (changes were backend-only)

### R1 — Employer Stripe Flow Verified
- PASS: POST /api/employer/start-trial with Origin: staging-employer.civicscale.ai
- Stripe session success_url: https://staging-employer.civicscale.ai/dashboard?trial_started=true
- Stripe session cancel_url: https://staging-employer.civicscale.ai/dashboard

### R2 — OTP Branding Verification
- All 5 products already have correct branding after Session Q fix:
  Employer="Parity Employer", Broker="Parity Broker", Provider="Parity Provider",
  Health="Parity Health" (separate handler), Signal uses Supabase Auth (no OTP)

### R3 — Historical Rate Tables (BLOCKED)
- Load scripts exist and are ready (load_historical_rates.py, process_pfs.py)
- CMS data files for 2024/2025 not present locally — must be downloaded from CMS.gov
- Files are ~100MB ZIPs requiring manual download from CMS website
- Fred action: download CY2024 and CY2025 PFS carrier files from CMS.gov

### R4 — Provider PDF Formatting
- Reduced margins (0.75"→0.6" sides, 0.75"→0.5" top/bottom) for more content area
- Section headings reduced from 14px to 12px with tighter spacing
- Header and stat box widths now use computed page_w for consistent alignment
- Denial benchmark table widths use proportional page_w fractions

### R5 — Investors Page Layout
- Added box-sizing: border-box to all elements in investors page
- Hero padding reduced on mobile (140px→100px top, 48px→24px sides)
- CTA heading font reduced on mobile (32px→24px)
- Prevents horizontal overflow on narrow viewports

### Files Changed
- `backend/routers/provider_audit.py` — PDF margin and spacing improvements
- `frontend/src/components/InvestorsPage.css` — mobile layout fixes + box-sizing
- `CHANGELOG.md` — Session R

## Session Q — 2026-03-16

### Q0 — Staging Backend Verification
- Confirmed staging backend running Session P code (admin/analytics returns 401, stats returns 200)

### Q1 — P2-P4 Promoted to Production
- Merged staging to main, rebuilt frontend, pushed to production
- Production now has: EOB line item fix, service date fix, admin analytics, CORS hotfix

### Q2 — Broker/Employer Hardcoded URL Fix
- broker.py `/subscribe` and employer_subscription.py `/start-trial` had
  hardcoded production URLs for Stripe success/cancel redirects
- Fixed: both now derive redirect URL from request `Origin` header
- Staging calls from `staging-broker.civicscale.ai` correctly redirect back to staging

### Q3 — Stripe Trial Flow Audit
- Code audit confirms: all 4 products use 30-day trial, card required
- Broker and Employer now use dynamic Origin-based URLs (Q2 fix)
- Provider and Health already used dynamic `frontend_url` — correct
- Full browser-based test requires Fred to verify manually after staging redeploy

### Q4 — OTP Email Branding Fix
- Changed broker product name from "Parity Employer Broker Portal" to "Parity Broker"
  in both OTP email template and team invitation email template
- OTP branding was already product-specific (employer→"Parity Employer", etc.)
- Each login page already sends correct product identifier

### Q5 — signal_events Privacy Cleanup
- Production has 301 rows with real user_id values — Fred action required to scrub
- Updated migration 042 with ALTER instructions for existing databases
- Updated ARCHITECTURE.md: user_id and device_type columns removed from design

### Files Changed
- `backend/routers/broker.py` — dynamic Origin-based Stripe redirect URLs
- `backend/routers/employer_subscription.py` — same
- `backend/routers/auth.py` — "Parity Broker" branding fix (OTP + invitations)
- `backend/migrations/042_signal_events.sql` — added migration notes for old schema
- `ARCHITECTURE.md` — privacy compliance note
- `CHANGELOG.md` — Session Q

## Session P — 2026-03-16

### P0 — Migration 042 Production
- `signal_events` table exists in production with old schema (user_id, device_type)
- Fred action: run ALTER TABLE statements to add session_id, topic_slug, element_id columns

### P1 — Session O Promoted to Production
- Merged staging to main (fast-forward, no conflicts)
- Built and pushed production frontend dist
- Production now has: Layer 3 nav, all 7 panels, centralized API URL, staging subdomain routing

### P2 — Health EOB Line Items Fix
- **Bug 1 (line items not showing):** Frontend filter `li.cpt_code || li.revenue_code`
  dropped items without procedure codes. Fixed to include items with description only
  (`li.cpt_code || li.revenue_code || li.description`). Applied to both text and image flows.
- **Bug 2 (wrong service date year):** AI extraction prompt didn't distinguish
  date of service from patient DOB. Added explicit instruction: "Extract the DATE
  OF SERVICE, not the patient's date of birth."

### P3 — Admin Analytics Dashboard
- New component: `frontend/src/components/signal/AdminAnalytics.jsx`
- Route: `/admin/analytics` on signal subdomain
- Auth-gated to admin user ID `4c62234e-86cc-4b8d-a782-c54fe1d11eb0`
- Backend: `GET /api/signal/admin/analytics` — aggregates from signal_events
- Shows: total events, unique sessions, questions asked, per-topic breakdown,
  most-expanded sections, event type distribution
- Added 90-day retention policy note to ARCHITECTURE.md

### P4 — Stripe Free Trial Flow Audit
- All 4 products use 30-day trial, card required upfront
- **Issue found:** broker.py and employer_subscription.py `start-trial`
  endpoints hardcode production URLs (`broker.civicscale.ai`,
  `employer.civicscale.ai`) — staging checkout will redirect to production
- Provider and Health use dynamic `frontend_url` env var — correct
- Signal has no trial period

### Files Changed
- `frontend/src/App.jsx` — EOB line item filter fix (both text and image paths)
- `backend/routers/health_analyze.py` — service date extraction prompt fix
- `frontend/src/components/signal/AdminAnalytics.jsx` — new admin analytics dashboard
- `frontend/src/SignalApp.jsx` — admin/analytics route
- `backend/routers/signal_events.py` — admin analytics endpoint
- `ARCHITECTURE.md` — 90-day retention policy note
- `CHANGELOG.md` — Session P

## Session O — 2026-03-16

### O0 — Staging Alias Script
- Created `scripts/update_staging_aliases.sh` — runs `npx vercel alias`
  for all 6 staging subdomains in one command

### O1 — Layer 3 Navigation Rail
- 7-tab navigation rail below Layer 2: Overview, All Claims, Analytical
  Paths, Key Debates, Evidence Roadmap, Sources, Methodology
- Each tab renders its own panel with real data
- Overview panel: stats grid + category score cards + Ask the Evidence
- All Claims panel: filterable (All/Strong/Moderate/Mixed/Weak) claim
  list with category tabs, fully interactive ClaimCards

### O2 — Analytical Paths Panel
- Moved ProfileSelector and WeightAdjuster into dedicated panel
- Added explanatory card: "How Analytical Paths Work"

### O3 — User Analytics Infrastructure
- Migration 042: `signal_events` table (session_id, topic_slug,
  event_type, element_id, event_data) — privacy-first, no user_id
- Updated `signal_events.py` endpoint: always returns 200, uses
  session_id not user_id, supports new event types
- Updated `signalAnalytics.js`: per-session random UUID (not persistent),
  `recordDepth()` helper, topic_slug and element_id parameters

### O4 — Evidence Roadmap and Sources Panels
- Evidence Roadmap: three-tier dot notation derived from consensus
  status (consensus=green "Data available", debated=amber "Actively
  studied", uncertain=gray "Not yet studied")
- Sources panel: full source list with title, date, type badge,
  clickable links, filterable by source_type

### O5 — Key Debates and Methodology Panels
- Key Debates: shows all debated/uncertain categories with affected
  claim count, or green "No active debates" card
- Methodology: version history, claim classification explanation,
  evidence category legend, limitations list, "Dispute a methodological
  choice" link that pre-fills Ask the Evidence

### Files Changed
- `scripts/update_staging_aliases.sh` — new
- `frontend/src/components/signal/IssueDashboard.jsx` — Layer 3 nav + 7 panels
- `frontend/src/lib/signalAnalytics.js` — privacy-first session analytics
- `backend/routers/signal_events.py` — updated schema + event types
- `backend/migrations/042_signal_events.sql` — new migration
- `CHANGELOG.md` — Session O

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
