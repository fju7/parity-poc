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
- Auth: Email OTP (8-digit codes for employer, 6-digit for broker)
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
- Route: /parity-health
- Backend: backend/routers/health_analyze.py, eob_parse.py, ai_parse.py
- Frontend: src/components/ParityHealth*.jsx

### Parity Provider
- Route: /billing/provider, /audit
- Backend: backend/routers/provider_*.py
- Frontend: src/components/Provider*.jsx
- Demo: /billing/provider/demo (ProviderDemoPage.jsx)
- Key feature: 835 EDI parsing via utils/parse_835.py

### Parity Employer
- Route: /billing/employer/*
- Backend: backend/routers/employer_*.py
- Frontend: src/components/Employer*.jsx
- Demo: /billing/employer/demo (EmployerDemoPage.jsx — 7 tabs)
- Key features: benchmark, claims check (835/CSV/Excel), scorecard,
  RBP calculator, carrier contract parser, trend engine
- Pricing: value-tiered based on identified excess spend
  Starter $149/mo (<$200K), Growth $349/mo ($200K-$750K),
  Scale $699/mo (>$750K)
- Guarantee: if identified savings don't exceed annual subscription
  cost, refund the difference

### Broker Portal
- Route: /broker/login, /broker/dashboard
- Backend: backend/routers/broker.py
- Frontend: src/components/Broker*.jsx
- Free for brokers — they add employer clients, run benchmarks,
  share read-only reports. Employers pay subscriptions.
- Shared reports: /employer/shared-report/:shareToken (no auth required)
- Three dashboard tabs: Book of Business, Renewals, Prospects
- Renewal prep reports: /broker/renewal-prep/:companySlug (print-optimized)
- CAA guide: /broker/caa-guide (carrier-specific claims data request instructions)
- Prospect benchmarking: segment-based assessment without PEPM data

### Parity Signal
- Route: /signal/*
- Backend: backend/routers/signal_*.py
- Separate product — AI-powered claim intelligence

## Key backend files
- backend/routers/employer_shared.py — shared utilities, rate limiting,
  EMPLOYER_PRICE_TIERS, _check_subscription(), assign_pricing_tier()
- backend/routers/employer_benchmark.py — benchmark endpoint
- backend/routers/employer_claims.py — claims check, RBP calculator,
  contract parser, free tier enforcement (1 free claims check/90 days)
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
- frontend/src/components/EmployerSharedReport.jsx — public shared
  report page (no auth)

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

## Migrations
Numbered sequentially: backend/migrations/001_*.sql through 028_*.sql
Next migration number: 029
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

## Standing instructions for every session
1. Read this file at the start of every session
2. Verify all file paths before issuing commands
3. Never create feature branches — work on main
4. After completing tasks, update this CLAUDE.md to reflect
   any new files, endpoints, tables, or architectural changes
5. Commit and push CLAUDE.md updates with the rest of the changes
6. Output any migration SQL clearly for Fred to run manually
7. Never ask Fred to create Stripe products or price IDs manually
