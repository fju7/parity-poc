# CivicScale / Parity — Claude Code Project Context

## Repo
- GitHub: https://github.com/fju7/parity-poc
- Local: /Users/fredugast/Desktop/AI Projects/Parity Medical/parity-poc-repo
- Branch rule: ALWAYS work on main branch. Never create feature branches.
  Claude Code's default branch behavior creates feature branches — always
  merge back to main and push before finishing.

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
- backend/routers/broker.py — broker portal endpoints
- backend/routers/provider_audit.py — 835 parsing endpoint
- backend/utils/parse_835.py — pure Python 835 EDI parser
- backend/data/employer_benchmarks/benchmark_compiled.json — runtime
  benchmark lookup data
- backend/data/sample/Midwest_Manufacturing_Dec2024.835 — sample 835 EDI
  remittance file (970 claims, ~$623K paid, Dec 2024, Cigna/Midwest Mfg)
- backend/data/sample/generate_835.py — script that generated the sample 835
- backend/main.py — FastAPI app, router registration, lifespan

## Key frontend files
- frontend/src/main.jsx — all routes (66 lines)
- frontend/src/components/EmployerDemoPage.jsx — 7-tab demo
  (Getting Started animated wizard, Benchmark, Claims, Scorecard,
  RBP Calculator, Contract Parser, Monitoring Dashboard)
- frontend/src/components/BrokerDashboard.jsx — broker portal
- frontend/src/components/EmployerSharedReport.jsx — public shared
  report page (no auth)

## Supabase tables (key ones)
- employer_benchmark_sessions — benchmark results
- employer_claims_uploads — claims check sessions + results_json
- employer_scorecard_sessions — scorecard results
- employer_subscriptions — active subscriptions by email
- employer_trends_cache — cached trend computations
- broker_accounts — broker login records
- broker_employer_links — broker→employer relationships
- broker_client_benchmarks — broker-run benchmarks with share tokens
- otp_codes — OTP codes for broker auth (6-digit, 10-min expiry)

## Migrations
Numbered sequentially: backend/migrations/001_*.sql through 025_*.sql
Next migration number: 026
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

## Standing instructions for every session
1. Read this file at the start of every session
2. Verify all file paths before issuing commands
3. Never create feature branches — work on main
4. After completing tasks, update this CLAUDE.md to reflect
   any new files, endpoints, tables, or architectural changes
5. Commit and push CLAUDE.md updates with the rest of the changes
6. Output any migration SQL clearly for Fred to run manually
7. Never ask Fred to create Stripe products or price IDs manually
