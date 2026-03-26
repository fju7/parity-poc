# CivicScale / Parity — Claude Code Project Context

## Repo
- GitHub: https://github.com/fju7/parity-poc
- Local: /Users/fredugast/Desktop/AI Projects/Parity Medical/parity-poc-repo
## CRITICAL BRANCH AND PUSH RULES — READ FIRST

NEVER create feature branches. ALWAYS push directly to main.

Claude Code's default behavior creates feature branches like `claude/review-changes-xxx`. This is FORBIDDEN in this repo. Every single commit must go directly to `origin/main`.

The correct git workflow for EVERY task is:
1. Make your changes
2. `git add <files>`
3. `git commit -m "descriptive message"`
4. `git push origin main`

That's it. No branch creation. No pull requests. No feature branches.

If you find yourself on a feature branch, immediately:
1. `git checkout main`
2. `git merge <feature-branch>`
3. `git push origin main`

NEVER end a session without confirming `git log --oneline -1` shows your commit on main AND `git push origin main` succeeded with actual objects transferred (not "Everything up-to-date" after a failed push).

Verify your push worked by checking the output says something like:
`226ecfd..abc1234  main -> main`
If it says "Everything up-to-date" without that line, the push failed.

## Stack
- Frontend: React/Vite → Vercel (auto-deploys from main)
- Backend: FastAPI Python 3.11 → Render (parity-poc-api.onrender.com)
- Database: Supabase (PostgreSQL + RLS)
- Payments: Stripe (test mode sk_test_...)
- Email: Resend
- Auth: Email OTP (8-digit codes for employer/provider/health, 6-digit for broker)
- AI: Anthropic Claude API (ANTHROPIC_API_KEY)
- File storage: Supabase storage

## Python rules
- Always use `python3` not `python`
- Always use `pip3` not `pip`
- Always use `--break-system-packages` flag with pip3

## Stripe rules
- Claude Code creates Stripe products and price IDs programmatically
  via the Stripe API — never ask Fred to create them manually
- Fred only needs to manually add environment variables in Render
- Current employer price IDs are in employer_shared.py EMPLOYER_PRICE_TIERS

## Products
Three live products + one in development:

### Parity Health (consumer)
- Route: /parity-health, health.civicscale.ai
- Backend: backend/routers/health_analyze.py, health_auth.py, eob_parse.py, ai_parse.py
- Frontend: src/App.jsx (main app), src/components/ParityHealth*.jsx,
  HealthLoginPage.jsx, HealthSignupPage.jsx
- Auth: /health/login (HealthLoginPage), /health/signup (HealthSignupPage)
  Individual consumer auth via health_users table (not company-based)
  Token stored in localStorage as health_token
- Pricing: $9.95/mo or $29/yr with 30-day free trial, 3 free analyses
- Stripe: STRIPE_PRICE_HEALTH_MONTHLY, STRIPE_PRICE_HEALTH_YEARLY env vars
  Webhook: POST /api/health/auth/webhook (needs STRIPE_HEALTH_WEBHOOK_SECRET)
- Stripe setup script: backend/scripts/create_health_stripe.py

### Parity Provider
- Route: /billing/provider, /audit, /provider/*, provider.civicscale.ai
- Backend: backend/routers/provider_*.py
- Frontend: src/ProviderApp.jsx (dashboard), src/components/Provider*.jsx
- Auth: /provider/login (ProviderLoginPage), /provider/signup (ProviderSignupPage)
- Dashboard: /provider/dashboard (ProviderApp.jsx — dark theme, 5 tabs)
- Account: /provider/account (ProviderAccountPage.jsx — team, billing, data)
- Demo: /billing/provider/demo (ProviderDemoPage.jsx)
- Key feature: 835 EDI parsing via utils/parse_835.py

### Parity Employer
- Route: /billing/employer/*, employer.civicscale.ai
- Backend: backend/routers/employer_*.py
- Frontend: src/components/Employer*.jsx
- Demo: /billing/employer/demo (EmployerDemoPage.jsx — 7 tabs)
- Key features: benchmark, claims check (835/CSV/Excel), scorecard,
  RBP calculator, carrier contract parser, trend engine
- Pricing: $99/month with 30-day free trial (card required upfront)
  Legacy value-tiered prices still in EMPLOYER_PRICE_TIERS for existing subs
- Guarantee: if identified savings don't exceed annual subscription
  cost, refund the difference

### Broker Portal
- Route: /broker/*, broker.civicscale.ai
- Backend: backend/routers/broker.py
- Frontend: src/components/Broker*.jsx
- $99/month with 30-day free trial (card required upfront)
- Brokers add employer clients, run benchmarks,
  share read-only reports.
- Shared reports: /employer/shared-report/:shareToken (no auth required)
- Three dashboard tabs: Book of Business, Renewals, Prospects
- Renewal prep reports: /broker/renewal-prep/:companySlug (print-optimized)
- CAA guide: /broker/caa-guide (carrier-specific claims data request instructions)
- Prospect benchmarking: segment-based assessment without PEPM data

### Parity Signal
- Route: /signal/*, signal.civicscale.ai
- Backend: backend/routers/signal_*.py
- Separate product — AI-powered claim intelligence
- Key feature: Analytical Profiles — 4 named scoring profiles (Balanced,
  Regulatory, Clinical, Patient) with divergence highlighting (premium-only)
- Backend: signal_profiles.py (GET /profiles, POST /profiles/score)
- Frontend: ProfileSelector.jsx integrated into IssueDashboard

## Key backend files
- backend/routers/employer_shared.py — shared utilities, rate limiting,
  EMPLOYER_PRICE_TIERS, _check_subscription(), assign_pricing_tier()
- backend/routers/employer_benchmark.py — benchmark endpoint
- backend/routers/employer_claims.py — claims check, RBP calculator,
  contract parser, free tier enforcement (1 free claims check/90 days)
- backend/routers/employer_pharmacy.py — pharmacy claims analysis,
  NADAC benchmarking, PBM spread estimation, generic opportunity detection
- backend/routers/employer_trends.py — month-over-month trend engine
- backend/routers/employer_subscription.py — Stripe checkout + webhook
- backend/routers/employer_scorecard.py — AI-powered SBC scoring with
  broker-protective _grade_interpretation() framing
- backend/routers/employer_shared_report.py — public shared report endpoint
  with first-view broker notification
- backend/routers/broker.py — broker portal endpoints (OTP auth, client
  management, onboard, bulk onboard, share links, notifications, renewal
  pipeline, renewal prep, prospect benchmarks, cron renewal reminders)
- backend/routers/provider_audit.py — 835 parsing endpoint
- backend/utils/parse_835.py — pure Python 835 EDI parser
- backend/utils/email.py — shared Resend email helper (send_email)
- backend/data/employer_benchmarks/benchmark_compiled.json — runtime
  benchmark lookup data
- backend/data/employer_benchmarks/industry_mapping.py — MEPS-IC industry
  name mapping with resolve_industry() helper
- backend/main.py — FastAPI app, router registration, lifespan
- backend/data/sample/Midwest_Manufacturing_Dec2024.835 — sample 835 EDI
  file (970 claims, ~$623K paid) for demo video
- backend/data/sample/Midwest_Manufacturing_SBC_2025.pdf — sample SBC PDF
  (Cigna PPO, produces C+ scorecard grade) for demo video
- backend/data/sample/generate_835.py — reproducible 835 generator script
- backend/data/sample/generate_sbc_pdf.py — reproducible SBC PDF generator

## Key frontend files
- frontend/src/main.jsx — all routes
- frontend/src/components/EmployerDemoPage.jsx — 7-tab demo
  (Getting Started animated wizard, Benchmark, Claims, Scorecard,
  RBP Calculator, Contract Parser, Monitoring Dashboard)
- frontend/src/components/BrokerDashboard.jsx — broker portal (3 tabs:
  Book of Business, Renewals, Prospects)
- frontend/src/components/RenewalPrepReport.jsx — print-optimized renewal
  report at /broker/renewal-prep/:companySlug
- frontend/src/components/CAABrokerGuide.jsx — CAA claims data guide
  with carrier-specific request instructions
- frontend/src/components/EmployerScorecard.jsx — plan scorecard with
  broker-protective interpretation text
- frontend/src/components/EmployerPharmacy.jsx — pharmacy claims analysis
  page with NADAC benchmarking, generic opportunity, specialty spend,
  PBM spread placeholder
- frontend/src/components/EmployerSharedReport.jsx — public shared
  report page (no auth)
- frontend/src/ProviderApp.jsx — provider dashboard (5 tabs: Dashboard,
  Contract Integrity, Coding Analysis, Trends, Appeals)
- frontend/src/components/ProviderAccountPage.jsx — provider account
  settings (practice info, subscription, team, data deletion)

## Supabase tables (key ones)
- companies — unified company records (employer/broker/provider)
- company_users — users within companies (email, role, status)
- company_invitations — pending team invitations with tokens
- sessions — auth sessions (UUID tokens, cs_session_token)
- deletion_requests — data deletion requests (company_id, status)
- employer_benchmark_sessions — benchmark results
- employer_claims_uploads — claims check sessions + results_json
- employer_scorecard_sessions — scorecard results
- employer_subscriptions — active subscriptions by email
- employer_trends_cache — cached trend computations
- broker_accounts — broker login records
- broker_employer_links — broker→employer relationships
  (includes reminder_sent_90d boolean for cron dedup)
- broker_client_benchmarks — broker-run benchmarks with share tokens
- broker_prospect_benchmarks — prospect assessments (not linked clients)
- otp_codes — OTP codes for auth (8-digit employer/provider, 6-digit broker)
- pharmacy_nadac — NADAC drug pricing reference (ndc_code, nadac_per_unit)
- pharmacy_benchmarks — pharmacy analysis results (company_id, analysis_json)
- health_users — individual consumer accounts (email, full_name)
- health_subscriptions — health Stripe subscriptions (health_user_id, plan, status)

## Migrations
Numbered sequentially: backend/migrations/001_*.sql through 050_*.sql
All migrations through 056 have been run on production.
Next migration number: 057
Always output migration SQL clearly for Fred to run in Supabase dashboard.
Fred runs migrations manually in Supabase SQL Editor.

## Environment variables (Render)
- ANTHROPIC_API_KEY
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_EMPLOYER_STARTER
- STRIPE_PRICE_EMPLOYER_GROWTH
- STRIPE_PRICE_EMPLOYER_SCALE
- STRIPE_PRICE_EMPLOYER (new $99/mo flat price)
- STRIPE_PRICE_BROKER_PRO
- STRIPE_PRICE_PROVIDER_MONTHLY
- STRIPE_PRICE_HEALTH_MONTHLY — Parity Health $9.95/mo price ID
- STRIPE_PRICE_HEALTH_YEARLY — Parity Health $29/yr price ID
- STRIPE_HEALTH_WEBHOOK_SECRET — webhook secret for health subscriptions
- RESEND_API_KEY
- CRON_SECRET — protects POST /api/broker/send-renewal-reminders

## Broker Portal — Phase 2 Complete
Features built in this phase:
- Renewal Timeline Tracker — three-column pipeline view (90d/91-180d/180d+)
  with checklist status per client
- Renewal Prep Report — print-optimized white report at
  /broker/renewal-prep/:companySlug with benchmark, claims, scorecard
  sections and auto-generated talking points
- Prospect Benchmarking Tool — Prospects tab in broker dashboard,
  segment-based benchmark without PEPM, talking points, Add as Client flow
- Email notifications — welcome, shared report viewed, renewal reminder
  (cron), bulk onboard complete (via backend/utils/email.py)
- CAA Claims Data Guide — broker guide at /broker/caa-guide with carrier
  cards and request template
- Scorecard broker-protective framing — _grade_interpretation() positions
  broker as solution, not problem
- Industry benchmark fix — 9 MEPS industries now correctly mapped via
  industry_mapping.py, industry-specific percentiles (p10-p90),
  50-state + DC cost indices
- Ordinal suffix fix — percentile displays show 1st/2nd/3rd correctly
  throughout (EmployerBenchmark, BrokerDashboard)

### Infrastructure
- Cron endpoint: POST /api/broker/send-renewal-reminders (daily 8am,
  protected by X-Cron-Secret header, CRON_SECRET env var)
- New Supabase tables: broker_prospect_benchmarks
- New column: broker_employer_links.reminder_sent_90d (boolean)

## Session D — Account Pages Polish (Complete)
- EmployerAccountPage: team management (role change, removal, invite),
  billing portal (fixed URL), plan status (via EmployerTrialBanner),
  data deletion request (modal with company name confirmation)
- BrokerAccountPage: wrapped with AuthGate, added role change/removal
  for team members, role selector on invite, data deletion request modal
- POST /api/auth/deletion-request — records request in deletion_requests
  table, sends confirmation email to user, internal notification to
  admin@civicscale.ai. Requires admin role + company name confirmation.
- Migration 028: deletion_requests table

## Session E-Signal — Analytical Profiles (Complete)
- 4 analytical profiles seeded: Balanced (default), Regulatory, Clinical, Patient
- Backend: signal_profiles.py with GET /api/signal/profiles and
  POST /api/signal/profiles/score?profile_id=&issue_id=
- Frontend: ProfileSelector.jsx — profile selector dropdown in IssueDashboard
  with trade-off summary callouts and divergence highlighting
- ClaimCard.jsx — divergent prop adds amber border + badge for claims
  where profile and default scoring reach different evidence categories
- Premium-only feature: gated by userTier === "premium" check
- Migration 029: seed data for signal_analytical_profiles table

## Session E-Health — Parity Health Enhancements (Complete)
- Extracted cptLabel() into shared utility: frontend/src/lib/cptLabel.js
  (exports cptLabel, cptDescription; ~70+ CPT codes)
- EmployerClaimsCheck.jsx now imports from shared lib instead of inline
- ReportView.jsx shows CPT plain-English labels (skips REVENUE codes)
- Denial/EOB analysis flow:
  - Backend: health_analyze.py added POST /api/health/analyze-denial
    (DENIAL_SYSTEM_PROMPT → structured JSON) and POST /api/health/generate-appeal
    (APPEAL_SYSTEM_PROMPT → formal letter text)
  - Frontend: DenialUploadView.jsx (text paste + file upload for denial letters)
  - Frontend: DenialReportView.jsx (denial type badge, weakness highlight,
    supporting docs checklist, appeal deadline, appeal letter generation
    with copy/print)
  - UploadView.jsx: "Received a denial? Analyze it here →" entry point
  - App.jsx: denial-upload and denial-report views wired into viewFromPath,
    new state (denialAnalysis, denialOriginalText), navigate to /parity-health/denial
- Subdomain routing: health.civicscale.ai
  - main.jsx: hostname detection renders ParityHealthLandingPage + App
    directly when on health.civicscale.ai (no /parity-health prefix needed)
  - App.jsx viewFromPath: handles paths with or without /parity-health prefix
  - Fred action: add health.civicscale.ai as domain in Vercel project settings

## Session F — Broker & Employer Subdomain Routing (Complete)
- Added broker.civicscale.ai and employer.civicscale.ai subdomain routing
  - main.jsx: isBrokerSubdomain/isEmployerSubdomain hostname detection
  - Broker subdomain: clean paths (/dashboard, /account, /login, /signup,
    /caa-guide, /renewal-prep/:companySlug) with backward-compat redirects
    from /broker/* paths
  - Employer subdomain: clean paths (/dashboard, /account, /login, /signup,
    /benchmark, /claims-check, /scorecard, /subscribe, /contract-parse,
    /rbp-calculator, /pharmacy, /demo, /accept-invite) with backward-compat
    redirects from /billing/employer/* paths
- Backend URL updates:
  - broker.py: Stripe checkout/portal URLs → broker.civicscale.ai
  - employer_subscription.py: Stripe checkout/portal/email URLs → employer.civicscale.ai
  - employer_shared_report.py: broker dashboard email link → broker.civicscale.ai
- CORS: added broker.civicscale.ai and employer.civicscale.ai to allowed_origins
- Vercel config (vercel.json): added rewrites for both subdomains,
  added redirects from civicscale.ai/broker/* → broker.civicscale.ai/*
  and civicscale.ai/billing/employer/* → employer.civicscale.ai/*
- Fred action: add broker.civicscale.ai and employer.civicscale.ai as
  domains in Vercel project settings

## Session I — Subdomain Migration + Landing Page Cleanup (Complete)
- Added signal.civicscale.ai subdomain: Vercel rewrites/redirects, CORS,
  main.jsx isSignalSubdomain routing to SignalApp
- CivicScale homepage: removed Start Free Trial/Demo CTAs from hero,
  linked all products to subdomains (external <a> tags), updated product
  cards with correct trial language, Health card shows pricing
- Employer product page: signup/login → employer.civicscale.ai, removed
  "No credit card required"
- Broker landing page: removed Referral Flywheel section, stronger data
  protection language, "30-day free trial, cancel anytime"
- Broker signup page: dark theme matching other product signup pages
- Provider product page: removed "No credit card required", links to
  provider.civicscale.ai
- Health landing page: nav updated (Sign In, Start Free Trial, CivicScale
  link), pricing text replaces "Free — no account required"
- Signal: dark theme (#0a1628) for SignalApp, SignalHeader, SignalFooter,
  SignalLanding. Added CivicScale link in nav. Added "engine behind Parity"
  section explaining Signal as decision-engineering engine.
- Fred action: add signal.civicscale.ai as domain in Vercel project settings

## Session E-Pharmacy — Pharmacy Benefit Benchmarking (Complete)
- New backend router: employer_pharmacy.py with POST /api/employer/pharmacy/analyze
  - Two-stage parsing: 835 EDI (N4 qualifier for NDC) → CSV/Excel auto-detect → AI extraction
  - Benchmarks against NADAC (National Average Drug Acquisition Cost)
  - Returns: summary, top_drugs, generic_opportunity, specialty_drugs, benchmarks,
    pbm_spread_estimate (null if NADAC unavailable), therapeutic_alternatives (null, future hook)
  - Saves results to pharmacy_benchmarks table
- Migration 030: pharmacy_nadac + pharmacy_benchmarks tables
- NADAC loader script: backend/scripts/load_nadac.py (manual run, downloads from CMS API)
- Frontend: EmployerPharmacy.jsx at /billing/employer/pharmacy
  - Same dark UI design as EmployerClaimsCheck
  - Tab toggle between Medical Claims and Pharmacy Claims on both pages
  - Upload → processing → results with 4 sections:
    Summary stats, Top Drugs by Cost (NADAC benchmark + spread),
    Generic Substitution Opportunities, Specialty Drug Spend
  - PBM Spread placeholder card when data unavailable
  - "What This Means" callout with generic rate and specialty spend benchmarks
- Synthetic test file: backend/data/sample/Midwest_Manufacturing_Pharmacy_Dec2024.csv
  (55 rows, mix of brand/generic/specialty, realistic NDC codes and pricing)

## Supabase tables (additional)
- health_sbc_uploads — SBC PDF analysis results (session_id, plan_name,
  plan_year, sbc_data jsonb)

## Session F-Health — Denial Appeal + SBC Analysis (Complete)
- Feature 1: Denial appeal letter flow enhanced
  - DenialReportView.jsx: collapsible "Fight This Denial" section with
    teal accent, optional Patient Name/Provider Name/Claim Number fields,
    "Drafting your appeal letter..." loading state, improved letter display
    with white background + readable font, Copy Letter with "Copied!"
    confirmation, Download as PDF via window.print(), disclaimer note
- Feature 2: SBC upload and analysis
  - Backend: POST /api/health/analyze-sbc in health_analyze.py — accepts
    PDF upload, uses Claude vision to extract plan design elements,
    saves to health_sbc_uploads table
  - Backend: analyze-text and analyze-image accept optional sbc_data field
    to include plan design in Claude prompt for personalized analysis
  - Frontend: SBC upload card on UploadView and InputSelectionView —
    PDF upload with "Reading your plan..." loading, compact plan summary
    card (plan name, deductible, OOP max, PCP copay, coinsurance) with
    green "Plan Loaded" badge and × to clear
  - Frontend: ReportView PlanResponsibilitySection — "What You Should Owe"
    section estimating patient responsibility using SBC data (deductible,
    copays, coinsurance breakdown, OOP max cap)
  - SBC state persists across bill analyses in same session
  - Migration 033: health_sbc_uploads table

## Session G-Health — Unified Intelligent Upload Zone (Complete)
- Rebuilt Parity Health upload experience with single intelligent drop zone
- New backend endpoint: POST /api/health/classify-document in health_analyze.py
  - Accepts PDF upload, uses Claude vision to classify as medical_bill, eob,
    denial_letter, sbc, or unknown
  - Returns JSON: {document_type, confidence, reason}
  - Rejects .txt/.edi/.837/.835 with friendly message (no Claude call)
- Frontend: UploadView.jsx rebuilt — single drop zone replaces old bill+SBC
  dual zones. Drops trigger classification → auto-route to correct pipeline:
  - medical_bill/eob → handleFileSelect (standard bill analysis)
  - sbc → SBC analysis (plan loader) with replace dialog if plan already loaded
  - denial_letter → handleDenialClassified (extracts PDF text → denial analysis)
  - unknown → falls back to bill analysis
- Frontend: InputSelectionView.jsx rebuilt — same classification on PDF upload
  card, SBC plan summary moved above input options
- Frontend: App.jsx — new handleDenialClassified callback: extracts text from
  classified denial PDF, calls /api/health/analyze-denial, routes to denial-report
- SBC plan summary card now displayed ABOVE the drop zone (not below)
- "Replace your current plan summary?" amber dialog when second SBC dropped
- "Identifying document..." spinner during classification
- Classification errors fall back gracefully to bill analysis pipeline

## Session G-Health-2 — Multi-Format Upload Support (Complete)
- New backend endpoints in health_analyze.py:
  - POST /api/health/extract-docx — extracts paragraph text from .docx files
    using python-docx, returns {text} for text analysis pipeline
  - POST /api/health/extract-table — reads .xlsx (openpyxl) or .csv (pandas),
    converts to column:value text representation, returns {text}
- Frontend file routing in UploadView + InputSelectionView:
  - TXT → file.text() → onTextSubmit (handlePasteSubmit)
  - DOCX → POST extract-docx → onTextSubmit
  - XLSX/CSV → POST extract-table → onTextSubmit
  - Images (JPG, PNG, WebP, HEIC, HEIF, TIFF, BMP) → onFileSelect
  - PDF → classify-document → route by type
  - EDI/837/835 → friendly rejection
- Added python-docx>=1.1.0 to requirements.txt
- UploadView is now the single default view (replaces InputSelectionView)

## Session I-Signal — QA Classification Layer (Complete)
- Enhanced QA_SYSTEM_PROMPT in signal_qa.py with 4-step classification layer
  executed before weighting analysis when disagreements exist:
  - Step 1: Disagreement Type Classification (Weighting/Completeness/Factual)
  - Step 2: Evidence Item Classification (Shared/Asymmetric/Contested tags)
  - Step 3: Weight Delta Statements ("If weight shifts from X→Y, conclusion
    changes from A→B")
  - Step 4: Contested Fact Handling — flags genuine uncertainty vs motivated
    denial, classifies resolution pathway (Empirical/Definitional/Disclosure/
    Methodological), names specific studies/institutions for resolution
- Layer skipped when no meaningful disagreements exist in the evidence

## Session J — Provider Improvements (Complete)
- Appeal Letter Quality Upgrade: Rewrote APPEAL_SYSTEM_PROMPT in
  provider_appeals.py to produce attorney-quality letters with specific
  regulatory citations (CMS IOM, 42 CFR, AMA CPT guidelines) for each
  denial code (CO-16, CO-45, CO-97, CO-4, CO-50, OA-18, PR-1).
  Added escalation_path and attach_documentation to JSON response.
- CPT Denial Rate Benchmarking: Added CPT_DENIAL_BENCHMARKS (35 CPT codes)
  and DENIAL_BENCHMARK_DATA_NOTE to provider_shared.py. Sources: CAQH
  Index 2024, Change Healthcare RCM Report 2024, CMS Medicare FFS data.
  analyze-contract now returns denial_benchmarks array comparing practice
  rates to industry averages. PDF audit report includes benchmark table.
- One-Page Summary PDF: POST /api/provider/summary-report generates a
  branded single-page PDF for practice owner handout with stat boxes,
  top issues, denial benchmark table, and priority actions.
  GET /api/provider/summary-report/{analysis_id} convenience wrapper
  auto-builds from stored analysis.
- Landing Page ROI Framing: Rewrote ProviderProductPage.jsx hero with
  "See the money your payers owe you. In 5 minutes." headline, three
  proof points (11% denial rate, $42K median underpayment, 5 min),
  "How It Works" 3-step section, demo-section anchor link.
- Benchmark Observation Capture: New provider_benchmark_observations
  table (migration 036) captures anonymized CPT-level denial/underpayment
  data from every 835 analysis. _save_benchmark_observations() helper
  normalizes payer category and derives region from ZIP. No PHI stored.

## Signal Stripe Upgrade + Cancel Fix (Complete)
- Existing subscribers clicking upgrade/downgrade now redirect to Stripe
  Customer Portal instead of calling stripe.Subscription.modify() directly.
  Webhooks handle DB updates on plan change.
- New POST /api/signal/stripe/cancel endpoint: cancels subscription at
  period end via Stripe, sets status to "canceling" with cancel_at_period_end
  flag, queues deletion request (best-effort).
- PricingView.jsx: handles portal_url response, shows success message on
  portal return (?portal_return=1).
- AccountView.jsx: cancel + data deletion section with confirmation modal
  for paid users. "canceling" status style added.
- Migration 037: cancel_at_period_end BOOLEAN column on signal_subscriptions.

## Session J-Broker — Broker Improvements (Complete)
Four broker prompts implemented:

### Prompt 1 — CAA Letter Generator
- POST /api/broker/clients/{employer_email}/caa-letter in broker.py
  - AI-generated CAA Section 204 data request letter using client data
  - Falls back to static template with statutory citations if AI fails
- BrokerDashboard.jsx: CAA Data Request Letter section in client detail panel

### Prompt 2 — Renewal Command Center
- BrokerDashboard.jsx renewals tab rebuilt:
  - Stats banner: urgent count (red), fully prepped (green), needs attention (amber)
  - Green "ahead of schedule" banner when urgentCount === 0
  - Inline renewal prep drawer: benchmark/claims/scorecard summary, talking points,
    Generate Full Report (new tab), Generate CAA Letter button
  - RenewalColumn: `urgent` prop adds pulsing red dot for clients ≤30 days
  - "Prepare Renewal Report" now opens inline drawer instead of navigating

### Prompt 3 — Broker "Wow" Demo
- New component: frontend/src/components/BrokerDemoPage.jsx
  - 4-step guided walkthrough: Book of Business → Findings → Renewal Report → CAA Letter
  - All data inline (no API calls), Midwest Manufacturing featured client
  - Step 3: timer animation counting down from 3:00:00 to 0:00:15
  - Step 4: full CAA letter with "Sign Up to Use This" CTA
- Route: /demo on broker.civicscale.ai subdomain
- BrokerLandingPage.jsx: "See a live demo first →" link added below hero CTA

### Prompt 4 — Broker Referral System
- Migration 038: broker_referrals table (referrer_company_id, referral_code,
  referred_email, status, converted_at)
- Backend endpoints in broker.py:
  - GET /api/broker/referral — get or create referral code + stats
  - POST /api/broker/referral/send — send referral email to colleague via Resend
  - GET /api/broker/referral/stats — full referral history
- auth.py: CreateCompanyRequest now accepts optional referral_code field;
  on broker signup, updates matching broker_referrals row to "signed_up"
- BrokerAccountPage.jsx: "Share Parity Broker" section with referral URL
  copy box, stats, send-email form, email preview toggle
- BrokerSignupPage.jsx: reads ?ref= param, shows welcome message,
  passes referral_code to company creation API

## Session J-Employer — Employer Improvements (Complete)
- Benchmark upgrade: AI narrative via _call_claude (JSON format), renewal
  talking points, print stylesheet in EmployerBenchmark.jsx
- Messy data recovery: 422 interception with column mapping UI in
  EmployerClaimsCheck.jsx, TPA format guide (HealthSmart, Meritain,
  Trustmark, Cigna ASO, Aetna ASO, BCBS)
- Action plans: AI-generated 3-step action plans in claims check
  (employer_claims.py), scorecard (employer_scorecard.py), and benchmark
  (employer_benchmark.py). Displayed as numbered teal cards in frontend.
- Broker connection: BrokerConnectCard.jsx — reusable card with "Share
  with broker" mailto link and "Find me a broker" request form.
  POST /api/employer/broker-connect in employer_claims.py sends admin
  notification + employer confirmation via Resend. Card appears on
  EmployerBenchmark (when no broker_ref param) and EmployerClaimsCheck
  (when total_excess_2x > 0).

## Session K — Full-Platform Regression Fix (Complete)
Based on fix brief from full regression testing (March 14, 2026).

### Wave 1 — Systemic Issues
- Employer routing: 13 backward-compat redirects in main.jsx for /billing/employer/* → clean paths
- Free trial: replaced 1-per-90-days claims check gate with 30-day unlimited trial
  (employer_claims.py checks first upload date, unlimited use for 30 days)
- Broker renewal-prep: added /broker/renewal-prep/:companySlug route rendering
  RenewalPrepReport directly (Navigate can't substitute route params)
- CORS: confirmed broker.civicscale.ai already in allowed_origins (no change needed)

### Wave 2 — Core Feature Fixes
- 2A: Client email required in broker single + bulk add forms (BrokerDashboard.jsx)
- 2B: BrokerConnectCard added to EmployerScorecard results
- 2C: Fixed NADAC API URL in load_nadac.py (broken UUID), improved with
  NDC dedup and early pagination stop
- 2D: Provider rate persistence — GET /api/provider/saved-rates endpoint
  in provider_audit.py, loadSavedRates() in ProviderApp.jsx on mount,
  saved_at date shown in payer list
- 2E: Appeal auto-population — Health DENIAL_SYSTEM_PROMPT extracts
  patient_name, provider_name, claim_number, date_of_service, payer_name;
  DenialReportView pre-populates fields. Provider DENIAL_SYSTEM_PROMPT
  returns affected_cpts and sample_date_of_service per denial type;
  ProviderAuditReport passes them to appeal generation.

### Wave 3 — Quick Fixes
- Signal IssueDashboard: title and debates heading → text-white for dark bg contrast
- Signal landing: "Start Free Trial" CTA in hero (hidden when logged in)
- Signal pricing: fixed "Current Plan" showing for logged-out users
- Signal OTP email: added "signal" → "Parity Signal" to product_names in auth.py
- Broker dashboard: benchmark results (PEPM, percentile, savings) in client detail panel
  via benchmark/benchmark_date fields added to client summary endpoint
- Broker renewals: fixed unicode escape "91\u2013180 days" → "91–180 days"
- Employer benchmark nav: /billing/employer links → /dashboard, /claims-check
- Employer product page: free benchmark CTA moved above the fold
- Provider product page: added PARITY PROVIDER branding badge in hero
- Health upload: added text paste input with textarea on UploadView.jsx

### Fred Action Items
- Run load_nadac.py against production Supabase to populate NADAC drug pricing data
- Redeploy backend on Render to pick up all backend changes

## Session L — Smoke Test Fixes (Complete)
Based on Session K smoke test results (March 14, 2026).

### Priority 1 — High Severity
- 1A: NADAC NDC leading zero fix — zfill(11) on all NDC codes before lookup
  in employer_pharmacy.py (input parsing, NADAC lookup, and CSV/Excel reader)
- 1B: Provider appeal letter auto-population — backend auto-populates
  practice_name, NPI, provider_name from provider_profiles table;
  looks up contracted rates from provider_contracts for cited CPT codes
- 1D: BrokerConnectCard share button — added window.open fallback for mailto
- 1E: BrokerConnectCard connect email — added requester_name field to form
  and BrokerConnectRequest model; admin email now includes name

### Priority 2 — Medium Severity
- 2A: Signal expandable sections contrast — added bg-white to
  SummaryThemeSection and DebateItem wrapper divs
- 2B: All $149/mo references → $99/mo across EmployerRBPCalculator,
  EmployerContractParser, EmployerDemoPage
- Comprehensive /billing/employer/* link cleanup across all employer
  components → clean subdomain paths (/dashboard, /claims-check, etc.)

### Notes
- Text paste input (2C) was already implemented in Session K Wave 3
- Frontend dist committed separately

### Fred Action Items
- Redeploy backend on Render to pick up NADAC fix, appeal auto-pop, broker connect changes

## Session M2 — Architecture Docs + Historical Rate Lookup (Complete)

### Item 1 — Architecture Documentation
- Created ARCHITECTURE.md: four-tier data model, update schedule,
  products/URLs, auth system, Stripe integration, env vars

### Item 2 — Historical Rate Lookup Fix
- lookup_rate() now accepts optional date_of_service parameter
- Prior-year dates delegate to lookup_rate_historical() (Supabase)
- Falls back to current rates with warning if historical data not loaded
- Return value changed from 4-tuple to 5-tuple (added rate_note)
- Updated all 7 call sites: employer_claims.py (4), broker.py (1),
  provider_audit.py (1), provider_shared.py (1)
- Claims check response includes rate_year_note field
- EmployerClaimsCheck.jsx shows rate year note banner
- Historical tables exist but are empty — graceful fallback confirmed

## Session M — Smoke Tests + Data Freshness Audit (Complete)

### Item 1 — Smoke Test Verifications (all passed)
- 1a: No remaining $149 text in employer frontend — PASS
- 1b: BrokerConnectCard admin email includes requester_name, email,
  company, industry, state, size, PEPM, percentile, gap, excess — PASS
- 1c: Provider saved-rates returns ALL payers for account, not just
  most recent — PASS
- 1d: Health UploadView has text paste textarea with Analyze button — PASS
- 1e: Signal SummaryThemeSection and DebateItem both have bg-white — PASS

### Item 2 — Data Freshness Audit
Reference data tables found in Supabase:
- pharmacy_nadac: 24,866 rows, effective_date 2021-02-01 to 2022-02-09
- ncci_edits: 2,210,396 rows, effective_date 1996-01-01 to 2026-01-01
- provider_benchmark_observations: 99 rows, observed_at 2026-03-14
Tables NOT found: mue_values, asp_pricing, clfs_rates, pfs_rates,
  opps_rates, medicare_rates, fee_schedule_rates

### Item 3 — Migration 041: data_versions table
- Migration file: backend/migrations/041_data_versions.sql
- Tracks data_source, version_label, effective_from/to, loaded_at,
  next_update_due, record_count, notes
- Fred action: run migration 041 + INSERT statements in Supabase SQL Editor

### Item 4 — Staging environment
- Deferred: CLAUDE.md forbids branch creation, CivicScale_Staging_Setup_Guide.docx
  not found in repo. Awaiting Fred's confirmation to proceed.

## Session AE — Phase 2 Wrap-up (Complete)

### AE-1: Modifier Analysis Callout in Contract Integrity
- Backend: provider_audit.py analyze-contract now computes modifier_analysis
  when denied line items have modifier codes — returns denied_with_modifiers
  count, pct_with_modifiers, total_billed_value, top_modifiers array
- Frontend: ProviderApp.jsx shows amber callout with modifier breakdown
  when modifier_analysis is present in results
- Line items table: added Modifiers column showing modifier codes per line,
  highlighted amber for denied items with modifiers

### AE-2: Slow-Pay Detection
- Backend: provider_audit.py calculates avg_days_to_pay from date_of_service
  to adjudication_date across all enriched lines (0-365 day sanity bound)
- avg_days_to_pay added to summary response and payer_performance_history insert
- Trends endpoint now includes avg_days_to_pay in data points
- Frontend: KPI tile for "Avg Days to Pay" with <30 benchmark
- Frontend: Red slow-pay alert callout when avg >30 days, with stronger
  language (state prompt-pay law reference) when >45 days

### AE-3: PDF Storage in Supabase Storage
- Created provider-reports storage bucket (private, 10MB limit, PDF only)
- GET /summary-report/{analysis_id} now checks Supabase Storage cache first
- On cache miss: generates PDF, uploads to provider-reports/{analysis_id}/summary.pdf,
  then serves the response
- On cache hit: serves cached PDF directly (skips DB lookup and generation)

### AE-4: Stripe Live Mode
- Deferred — awaiting Fred's explicit go-ahead. Stripe remains in TEST MODE.

### Supabase Storage Buckets
- provider-reports: private bucket for cached provider PDF reports (10MB limit, PDF only)

## Session BL-2 — Parity Billing: Onboarding & Practice Management (Complete)

### Backend (billing.py)
- POST /api/billing/send-otp — OTP via existing otp_codes infrastructure
- POST /api/billing/verify-otp — verify OTP, create session, return billing company
- POST /api/billing/register — create billing_companies + billing_company_users
  (admin) + billing_company_subscriptions (trial, 30 days, 10 practices). Send
  welcome email. Also creates companies (type='billing') + company_users for
  standard auth flow compatibility.
- GET /api/billing/me — returns user + billing company + subscription
- GET /api/billing/practices — list active practices for billing company
- POST /api/billing/practices — admin only, creates/links practice. Enforces
  practice_count_limit. Creates companies record (account_type='practice') if
  needed, or links existing.
- PATCH /api/billing/practices/{practice_id} — admin only, soft-deactivate
- POST /api/billing/users/invite — admin only, creates billing_company_users +
  company_users records, sends invite email
- GET /api/billing/users — admin only, list billing company users

### Auth changes
- auth.py: added "billing" to PRODUCT_NAMES, allowed products, and company types
- main.py: added billing.civicscale.ai + staging-billing.civicscale.ai to CORS

### Frontend
- BillingApp.jsx: OTP sign-in flow, registration form (company name + email),
  dashboard with header (product name + company name + sign out), 5-tab nav
  (Practices active, Portfolio Dashboard/Reports/Team/Settings as placeholders),
  practices table with Add Practice form, deactivate button
- main.jsx: isBillingSubdomain routing for billing.civicscale.ai
- vercel.json: SPA rewrites for billing/staging-billing subdomains

### Migration 057
- billing_company_users: make user_id nullable, add email/full_name/status columns

### Fred Action Items
- Run migration 057 in Supabase SQL Editor
- Add billing.civicscale.ai as domain in Vercel project settings
- Redeploy backend on Render to pick up billing endpoints + CORS changes

## Session BL-3 — Parity Billing: Batch 835 Ingestion at Scale (Complete)

### Backend (billing.py) — ingestion endpoints
- POST /api/billing/ingest/upload — multipart form (practice_id + files[]),
  max 20 files, validates practice ownership, queues billing_835_jobs rows
- POST /api/billing/ingest/process/{job_id} — parse 835 via utils/parse_835.py,
  compute line_count/denial_rate/total_billed, store result_json, insert
  provider_analyses with billing_company_id (for BL-4 portfolio rollup)
- POST /api/billing/ingest/process-all — process all queued jobs sequentially,
  returns {processed, errors}
- GET /api/billing/ingest/jobs — list all jobs for billing company (DESC),
  includes practice_name via companies join
- GET /api/billing/ingest/jobs/{job_id} — single job with full result_json

### Frontend (BillingApp.jsx)
- 835 Ingestion tab (replaced Reports placeholder)
- Practice dropdown from GET /api/billing/practices
- Multi-file drop zone (.835/.txt/.edi), file list with remove buttons
- Upload & Queue button → auto-calls process-all → refreshes job list
- Job queue table: Filename | Practice | Status | Lines | Denial Rate |
  Total Billed | Uploaded
- Status badges: grey QUEUED, blue PROCESSING, green COMPLETE, red ERROR
- Auto-refresh every 5s while any job is queued/processing
- Click COMPLETE row → inline result summary (payer, claims, lines, billed,
  paid, denial rate, denied lines, production date)

### Migration 058: billing_835_jobs table
- id, billing_company_id, practice_id, filename, status, file_content,
  result_json, error_message, line_count, denial_rate, total_billed,
  uploaded_by_email, created_at, updated_at
- RLS enabled, service role full access
- Index on (billing_company_id, created_at DESC)

## Session BL-4 — Parity Billing: Portfolio Dashboard (Complete)

### Backend (billing_portfolio.py)
- GET /api/billing/portfolio/summary — aggregated KPIs across all practices
  (total_billed, total_paid, total_lines, overall_denial_rate, practice_count,
  payer_count), filtered by billing_company_id + days param
- GET /api/billing/portfolio/practices — per-practice rollup with denial_rate,
  line_count, analysis_count, last_upload, joined to companies for names
- GET /api/billing/portfolio/payers — per-payer rollup across all practices
  with total_billed, denial_rate, practice_count
- GET /api/billing/portfolio/denial-reasons — top 10 CARC denial codes by
  frequency with descriptions and total amounts, extracted from result_json
  line_items adjustments
- All endpoints accept ?days= query param (default 90)
- Registered in main.py with prefix /api/billing/portfolio

### Frontend (BillingApp.jsx)
- Portfolio Dashboard is now the default/first tab
- Row 1: 4 KPI tiles (Total Billed, Denial Rate, Active Practices, Payers)
- Row 2: Practice Breakdown table (sortable by billed/denial rate)
- Row 3: Side-by-side Payer Performance + Top Denial Reasons tables
- Date range filter (30/90/180 days) at top right, affects all sections
- Loading skeletons while fetching; empty state if no analyses yet
- No new migrations needed — uses existing provider_analyses.billing_company_id

## Session BL-5 — Parity Billing: Cross-Practice Payer Benchmarking (Complete)

### Backend (billing_portfolio.py) — 3 new endpoints
- GET /api/billing/portfolio/payer-benchmark — payer adherence rates across
  all practices, optional ?specialty= filter, ?days= param. Adherence =
  paid_lines / total_lines. Default sort: ascending (worst payers first)
- GET /api/billing/portfolio/payer-anomalies — compares each payer's
  adherence in current 90d vs prior 90d window. Returns payers where
  adherence dropped >10 percentage points. Returns current_rate, prior_rate,
  delta, practice_count
- GET /api/billing/portfolio/specialties — distinct specialty values from
  provider_profiles for practices linked to the billing company

### Frontend (BillingApp.jsx)
- "Coming soon" placeholder removed from Portfolio tab (now only on Team)
- Payer Benchmarking section added below existing portfolio content
- Specialty filter dropdown (populated from provider_profiles)
- Anomaly alert banner (amber, dismissible) when payers show decline
- Sortable benchmark table: Payer Name | Adherence Rate | Practices |
  Claims | Total Billed | Status (Good/Review/Watch badges)
- Anomaly rows highlighted amber with DECLINING badge + delta indicator
- No new migrations needed

### Specialty filter status
- Specialty column exists on provider_profiles (not companies)
- Filter is LIVE — queries provider_profiles.specialty for practices
  linked via billing_company_practices
- Practices without provider_profiles rows simply have no specialty data

## Session BL-6 — Practice Comparison + Analyst Assignment (Complete)

### New file: backend/routers/billing_team.py
- GET /api/billing/team/analysts — list all billing_company_users with
  assigned_practices array (joined to analyst_practice_assignments)
- POST /api/billing/team/assignments — admin only, replaces all practice
  assignments for an analyst (delete existing, insert new)

### New endpoint in billing_portfolio.py
- GET /api/billing/portfolio/comparison — compare two practices side-by-side
  with portfolio average. Returns denial_rate, total_billed, line_count,
  top_payer, top_denial_reason for each practice + portfolio avg

### Role scoping (billing_portfolio.py)
- _get_scoped_practice_ids(bc_id, bc_user_id, bc_role, sb): returns
  analyst's assigned practice_ids from analyst_practice_assignments,
  or None for admin (no filter applied)
- _scoped_analyses_query(): applies practice filter to provider_analyses
- All 7 existing portfolio endpoints + comparison now respect analyst scoping
- billing_company_users role values: "admin", "analyst", "viewer"

### Frontend (BillingApp.jsx)
- Practice Comparison section in Portfolio tab: two practice dropdowns,
  4-column comparison table (Metric | Practice A | Practice B | Portfolio Avg),
  delta indicators (green/red arrows vs portfolio average)
- Team tab: replaces "coming soon" with analyst assignment UI
  - Admin view: user table, inline multi-select checkboxes for practices,
    save button with success toast
  - Analyst view: read-only message ("Contact your administrator...")
- billingRole state tracked from GET /api/billing/me response

### Migration 059: analyst_practice_assignments table
- analyst_user_id FK → billing_company_users(id) (not auth.users)
- UNIQUE(analyst_user_id, practice_id)
- Index on (analyst_user_id, billing_company_id)

## Migrations status
All migrations through 056 have been run on production.
Migrations 057, 058, 059 pending.
Next migration number: 060

## Standing instructions for every session
1. Read this file at the start of every session
2. Verify all file paths before issuing commands
3. Never create feature branches — work on main
4. After completing tasks, update this CLAUDE.md to reflect
   any new files, endpoints, tables, or architectural changes
5. Commit and push CLAUDE.md updates with the rest of the changes
6. Output any migration SQL clearly for Fred to run manually
7. Never ask Fred to create Stripe products or price IDs manually

## Quality Standards — Verification and Testing

### File and Path Verification

- Before referencing any file, directory, or path, verify it exists using the bash tool. Never assume a path is correct based on convention or prior knowledge. If a file cannot be found at the expected location, search for it with find before proceeding. Do not proceed with a file operation on an assumed path.
- Before referencing any environment variable, database table, column name, or API endpoint, verify it exists in the actual codebase or database. Run a SQL query or grep the codebase rather than assuming.
- Never guess at Supabase table names, column names, or schema structure. Always query information_schema or the actual table to confirm before writing any SQL or backend code that depends on it.

### Testing After Every Change

- After every code change, define the expected behavior in plain language before running any tests. Then verify that actual behavior matches expected behavior — not just that the code ran without errors.
- After every backend change, check Render logs for the specific endpoint that was modified. Confirm the response code and response body match what is expected. A 200 response is not sufficient — verify the response contains the correct data.
- After every frontend change, open the affected page in a browser and manually verify the changed behavior. Describe what you see. Do not rely on a successful build as evidence that the feature works.
- After any database migration, run a SELECT query to confirm the table or column was created correctly before writing any code that depends on it.
- After any data loader script is run, query the database to confirm the expected number of records were loaded and that the data format is correct. Do not assume the loader succeeded because it ran without errors.

### Change Scope and Isolation

- Make one change at a time and test it before making the next change. Do not batch multiple unrelated changes into a single commit if they can be separated. This makes it dramatically easier to identify which change caused a regression.
- Before making any change, describe what the change is intended to do, what files will be modified, and how success will be verified. State this explicitly before writing any code.

### Error Diagnosis

- When a feature returns an error, read the full error message before attempting a fix. Do not guess at the cause. If the error is in Render logs, read the relevant log lines. If the error is in the browser console, read the exact error message and call stack.
- When a fix is attempted and the same error persists, do not apply the same fix again with minor variations. Stop and diagnose from first principles — read the code path end to end and identify where the actual divergence from expected behavior occurs.
- When a browser console error references a minified file (e.g. index-BaqC8vEB.js:428), identify which React component or function corresponds to the call stack description and read that source file. Do not attempt to debug minified output.
- When an API endpoint returns unexpected results, add a temporary debug log at the point where data enters the function and at the point where it is returned. Read the log output before attempting any fix. Remove all debug logs before the final commit.

### Database Safety

- Before writing any SQL that modifies data (INSERT, UPDATE, DELETE, ALTER), write and run a SELECT query first to confirm the target rows or schema exist and look as expected.
- Never drop or truncate a table without explicit confirmation from Fred.
- Never run a migration that could destroy existing data without first confirming what data is in the affected table and getting explicit approval.

### Code Quality

- Never hardcode a URL, environment variable value, or credential in source code. Always use environment variables. If an environment variable is missing from Render, note it explicitly and ask Fred to add it rather than using a hardcoded fallback.
- When the same error occurs twice, do not apply the same fix twice. Escalate to Fred with a description of what was tried and what the result was.

## Common Mistakes to Avoid

- In React components, ALL useState and useEffect hooks must be
  declared at the top of the component function, before any conditional
  returns. This is React's Rules of Hooks. Violating this causes
  React error #520 and a blank page. Similarly, all JSX rendered in
  the return must guard against null/undefined property access —
  use optional chaining (?.) and fallback values (|| "") for any
  data that comes from API responses or props.
- NEVER report a fix as done without verifying the source file actually
  changed. After any edit, always run grep or cat to confirm the change
  is in the file before committing.
- frontend/dist/ is NOT committed to git — Vercel builds from source
  automatically. Never run `git add -f frontend/dist/` or commit dist
  files. The .gitignore already excludes frontend/dist/.
- Always verify fixes are in the actual source files, not in a worktree
  or temporary location. Check `git diff` before committing.
- After fixing a frontend bug, verify with:
  `grep -n "[the fixed string]" [the file path]`
  before committing.
- The /api/version endpoint on the backend confirms what code is
  deployed. Use `curl <backend-url>/api/version` to verify backend
  deployments match the expected commit hash.
- To verify frontend deployment: check the Network tab in browser
  DevTools for the actual API calls being made, or check the
  `<meta name="parity-version">` tag in the page source.
- Never use git worktrees. Always work directly in the main repo
  directory. Do not create worktrees under .claude/worktrees/ or
  anywhere else.
- Never create files in worktree directories. All migration files,
  scripts, and other new files must be created directly in the repo
  (e.g. backend/migrations/, backend/scripts/), never under
  .claude/worktrees/.
- Before merging branches, always check for untracked files that
  would be overwritten and remove them first.

## Development Workflow — Staging First (Effective Session N onward)

ALL development happens on the staging branch. Never commit directly to main.

Starting every session:
  git checkout staging
  git pull origin staging

Staging URLs (once configured):
  Backend: parity-poc-api-staging.onrender.com
  Health: staging-health.civicscale.ai
  Employer: staging-employer.civicscale.ai
  Broker: staging-broker.civicscale.ai
  Provider: staging-provider.civicscale.ai
  Signal: staging-signal.civicscale.ai

Promoting to production (Fred does this after testing, not Claude Code):
  git checkout main
  git pull origin main
  git merge staging
  git push origin main

Never merge staging to main during a Claude Code session.
Always stop at pushing to staging.
