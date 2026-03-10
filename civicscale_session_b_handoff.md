# CivicScale Session Handoff Document
**Last updated:** March 10, 2026  
**Repo:** https://github.com/fju7/parity-poc  
**Local path:** `/Users/fredugast/Desktop/AI Projects/Parity Medical/parity-poc-repo`  
**Rules:** python3/pip3 only · commit directly to main · Claude Code only on main branch  

---

## SESSION STATUS

| Session | Status | Summary |
|---------|--------|---------|
| A | ✅ Complete | Unified auth architecture |
| B | ✅ Complete | Broker auth migration + website redesign strategy |
| C | ✅ Complete | Provider auth migration |
| D | ✅ Complete | Account pages polish |
| E-Signal | 🔜 Next | Analytical profiles build-out |
| E-Health | Queued | Parity Health MVP — denial appeals |
| F | Queued | Website redesign + investor page |
| G | Queued | Go live |

---

## INFRASTRUCTURE

- **Frontend:** React/Vite → Vercel (auto-deploys main)
- **Backend:** FastAPI Python 3.11 → Render at `parity-poc-api.onrender.com`
- **Database:** Supabase (paid plan)
- **Payments:** Stripe (test mode — going live requires key swap in Render)
- **Email:** Resend (`noreply@civicscale.ai`)
- **Auth:** Unified OTP system (8-digit codes) — see Session A below

---

## WHAT WAS BUILT — SESSION A ✅
**Unified Auth Architecture**  
Commit: `61a4bb5` on main

**New tables (migration `001_unified_auth.sql` — ALREADY RUN):**
- `companies` — core organizational unit (employer/broker/provider)
- `company_users` — people belonging to companies, with roles (admin/member/viewer)
- `sessions` — UUID token-based auth, 30-day expiry
- `company_invitations` — admin-controlled invite flow with 7-day token expiry

**Backend:**
- `backend/routers/auth.py` — full unified auth module
  - `POST /api/auth/send-otp`
  - `POST /api/auth/verify-otp` — returns token + user + company, or `needs_company: true`
  - `GET /api/auth/me` — validates Bearer token
  - `POST /api/auth/logout`
  - `POST /api/auth/company` — creates company + admin user + auto-creates session
  - `POST /api/auth/invite` — admin invites team member
  - `POST /api/auth/accept-invite` — accepts invitation via token
  - `GET/PATCH /api/auth/company` — get/update company details
  - `GET /api/auth/users` — list company members
  - `PATCH/DELETE /api/auth/users/{id}` — admin manages team
  - `get_current_user(authorization, sb)` — shared helper, import in any router

**Frontend:**
- `frontend/src/context/AuthContext.jsx` — React context, `useAuth()` hook
  - Stores `cs_session_token` in localStorage
  - Provides: `token, user, company, login, logout, isAdmin, isMember, isAuthenticated, refetch`
- `frontend/src/components/AuthGate.jsx` — wraps protected pages, inline OTP login
- `frontend/src/components/EmployerSignupPage.jsx` — `/billing/employer/signup`
- `frontend/src/components/EmployerDashboard.jsx` — `/billing/employer/dashboard`
- `frontend/src/components/EmployerAccountPage.jsx` — `/billing/employer/account`
- `frontend/src/components/AcceptInvitePage.jsx` — `/accept-invite?token=`

---

## WHAT WAS BUILT — SESSION B ✅
**Broker Auth Migration + Website Redesign Strategy**

- Migrated broker auth from email-only localStorage to unified `sessions` + `companies` tables
- Broker firms are now `companies` with `type = 'broker'`
- Multi-broker firm support (shared book of business)
- Broker-controlled employer invitation flow ("Invite Client" button)
- Broker commission tracking (20% for 12 months on employer referrals, starting first paid month)
- Website redesign strategy session (see Strategic Context section below)

---

## WHAT WAS BUILT — SESSION C ✅
**Provider Auth Migration**

**Backend (4 files modified):**
- `provider_shared.py` — Replaced `_get_authenticated_user` with unified auth via `get_current_user()`, added `_AuthUser` wrapper for `.id`/`.email` backward compat, updated `_verify_admin` to use role-based check
- `provider_audit.py` — Removed `await` from auth call, added 4 new API endpoints (`/my-profile`, `/save-profile`, `/my-analyses`, `/analysis/{id}`) to replace direct Supabase queries from frontend
- `provider_appeals.py` — Removed `await` from 4 auth calls
- `provider_subscription.py` — Removed `await` from 4 auth calls

**Frontend (5 files modified):**
- `ProviderApp.jsx` — Full migration from Supabase auth to `useAuth()`/`AuthGate`, removed login views
- `AuditAccount.jsx` — Full rewrite: replaced Supabase OTP flow with `AuthGate` wrapper + `useAuth()` hook
- `ProviderAuditAdmin.jsx` — Replaced `session` prop with `useAuth()` hook
- `ProviderAuditReport.jsx` — Replaced `supabase.auth.getSession()` with `useAuth()` token
- `AuditStandalone.jsx` — Removed `session={null}` prop from `ProviderAuditPage`

**Routes:** `/provider/*` protected by AuthGate in ProviderApp · `/audit/account` protected by AuthGate in AuditAccount · `/audit` remains public (free audit form)

---

## WHAT WAS BUILT — SESSION D ✅
**Account Pages Polish**

**Backend (1 file modified):**
- `auth.py` — Added `POST /api/auth/deletion-request` endpoint. Requires admin role + company name confirmation. Records request in `deletion_requests` table, sends confirmation email to user and internal notification to `admin@civicscale.ai`.

**Frontend (2 files modified):**
- `EmployerAccountPage.jsx` — Fixed billing portal URL (`/api/employer/billing-portal`), replaced mailto link with real deletion request modal (type company name to confirm)
- `BrokerAccountPage.jsx` — Wrapped with `AuthGate`, added role change dropdown and remove button for team members, added role selector to invite form, added data deletion request modal

**Migration:** `028_deletion_requests.sql` — run in Supabase ✅ · Render redeployed ✅

---

## PENDING WORK — SESSION E-SIGNAL (QUEUED)
**Analytical Profiles Build-out**

Read `CLAUDE.md` first. Then read the full handoff document before writing any code.

**Context:** Parity Signal already has a multi-dimensional claim scoring system — each claim is scored across 6 dimensions (`source_quality`, `data_support`, `reproducibility`, `consensus`, `recency`, `rigor`) with weights stored in `signal_claim_composites.weights_used`. The `signal_analytical_profiles` table already exists in the schema (migration `005_signal_tables.sql`) but is empty and not wired into the scoring pipeline.

**What to build:**

1. **Seed analytical profiles** — populate `signal_analytical_profiles` with at least 3 named profiles, each with a different `weights JSONB` configuration and a plain-English `trade_off_summary`. Suggested profiles:
   - `Regulatory` — heavily weights `source_quality` and `consensus` (FDA/CMS sources dominate)
   - `Clinical` — heavily weights `reproducibility` and `rigor` (peer-reviewed trials dominate)
   - `Patient` — heavily weights `recency` and `data_support` (what's known now, practically)

2. **Backend endpoints:**
   - `GET /api/signal/profiles` — returns all profiles
   - `POST /api/signal/score?profile_id=` — re-scores a claim set using the named profile's weights instead of defaults. Returns composite scores AND a `divergence` field showing where this profile's conclusion differs from the default scoring.

3. **Frontend UI** — On the Signal topic/issue page, add a profile selector (dropdown or toggle). When user switches profiles, claim scores and evidence categories update to reflect that profile's weighting. Show a small callout explaining the trade-off in plain English (use `trade_off_summary` from the profile record). **Premium-only feature — gate behind tier check.**

4. **Divergence highlighting** — Claims where different profiles reach different `evidence_category` conclusions (e.g. `moderate` vs `weak`) should be visually flagged. This is the core investor-demo feature — it makes the "we show you how conclusions differ" story tangible.

**Do not touch:** Auth system, employer/broker/provider routers, Stripe logic.

**Commit directly to main. No feature branches.**

---

## PENDING WORK — SESSION E-HEALTH (QUEUED)
**Parity Health Enhancements: CPT Labels + Denial Appeals**

Read `CLAUDE.md` first. Then read the full handoff document before writing any code.

**Context:** Parity Health is substantially built. The following already exist and should not be touched unless directly relevant to the tasks below:
- `ParityHealthLandingPage.jsx` — landing page at `/parity-health`
- `UploadView.jsx` — drag/drop PDF upload, privacy-first design
- `ReportView.jsx` — full bill analysis report with anomaly scoring, coding pattern analysis, what-to-do-next
- `BillHistoryView.jsx` — local bill history with export
- `extractBillData.js` — browser-side PDF extraction
- `localBillStore.js` — local storage for bill history
- `backend/routers/health_analyze.py` — AI extraction endpoints for text and image input (`/api/health/analyze-text`, `/api/health/analyze-image`)
- `ImageUploadView.jsx`, `ItemizedBillRequestView.jsx` — supporting views

**Four things to build, in this order:**

---

### 1. CPT Plain-English Labels in ReportView

**Problem:** The Description column in the line items table shows whatever text was extracted from the PDF — often blank, truncated, or using internal billing shorthand. The employer codebase already has a `cptLabel()` helper that maps CPT codes to plain-English procedure names.

**What to do:**
- Find the `cptLabel()` helper in the employer codebase — likely in `frontend/src/lib/` or `frontend/src/utils/`. Verify the exact file path before doing anything.
- Import it into `ReportView.jsx`
- In the `LineItemRow` component, use `cptLabel(item.code)` as a fallback when `item.description` is blank or very short (under 5 characters). Display format: show the plain-English label, with the original extracted description beneath it in smaller gray text if both exist.
- If the code is a REVENUE code (`item.codeType === "REVENUE"`), do not apply cptLabel — revenue codes have a different lookup. Leave those as-is.

---

### 2. Denial/EOB Analysis Flow

**Problem:** There is no path for a user who received an insurance denial. Denial appeals is a distinct high-value use case — different document type, different analytical questions, different output.

**Frontend — new upload entry point:**
- Add a second option to the existing `UploadView.jsx` — below the current drop zone, add a clearly separated section: "Received a denial? Analyze it here →" as a button/link navigating to `/parity-health/denial`
- Create `DenialUploadView.jsx` at `/parity-health/denial` — same visual style as `UploadView.jsx` but with empathetic copy ("Insurance denied your claim. Let's find out why — and what you can do about it."). Accept PDF upload or text paste. No image upload needed for MVP.

**Backend — new endpoint in `health_analyze.py`:**
- Add `POST /api/health/analyze-denial`
- Accepts `{ text: string }` — extracted text from a denial letter or EOB
- Sends to Claude with this system prompt:
```
You are a medical insurance denial analyst. Analyze this insurance denial letter or Explanation of Benefits (EOB) and extract the following as JSON only, no other text:
{
  "denial_reason_code": "the specific reason code if present (e.g. CO-97, PR-96)",
  "denial_reason_plain": "plain English explanation of why the claim was denied",
  "denial_type": "clinical (medical necessity) | administrative (paperwork/auth) | coverage (not covered) | other",
  "specific_criterion": "the exact criterion, policy, or rule the carrier cited to deny",
  "weakness": "any apparent weakness in the denial reasoning — e.g. if the criterion cited is vague, inconsistently applied, or contradicted by the clinical record. Return null if the denial appears straightforward.",
  "supporting_documentation": ["list of specific documents or evidence that would strengthen an appeal"],
  "appeal_deadline_hint": "any appeal deadline mentioned, or null",
  "confidence": "high if denial reason is clearly stated, medium if partially clear, low if ambiguous"
}
```
- Returns structured JSON matching the above shape

**Frontend — denial result view:**
- Create `DenialReportView.jsx` — displays the structured analysis in plain English
- Sections:
  - **Why it was denied** — `denial_reason_plain` in large readable text, denial type badge (Clinical / Administrative / Coverage)
  - **What they cited** — `specific_criterion` with a brief explanation of what that means
  - **Weakness in their reasoning** — only show if `weakness` is not null. Highlight this clearly — it is the most valuable section.
  - **What to include in your appeal** — `supporting_documentation` as a printable checklist
  - **Appeal deadline** — if present, show prominently in amber
- Below the analysis: "Generate an Appeal Letter" button → calls the appeal letter endpoint (item 3)
- Same "Download Report" / print functionality as `ReportView.jsx`

---

### 3. Appeal Letter Generator

**Backend — new endpoint in `health_analyze.py`:**
- Add `POST /api/health/generate-appeal`
- Accepts the full denial analysis JSON from step 2 plus optional `{ patient_name: string, provider_name: string, claim_number: string }`
- Sends to Claude with this system prompt:
```
You are a medical billing advocate writing a formal insurance appeal letter on behalf of a patient. Using the denial analysis provided, write a professional, assertive appeal letter that:
- Opens with the specific claim/denial reference
- States clearly that the patient is appealing the denial
- Directly addresses the specific criterion the carrier cited
- If a weakness was identified in the denial reasoning, leads with that as the primary argument
- Lists the supporting documentation the patient will provide
- Closes with a clear request for reconsideration and a deadline expectation
- Uses professional but plain language — not legal jargon
- Is formatted as a real letter (date, addresses, subject line, body, closing)
Return only the letter text, no explanation or commentary.
```
- Returns `{ letter_text: string }`

**Frontend:**
- Add a letter display section to `DenialReportView.jsx` — shown after user clicks "Generate Appeal Letter"
- Show the letter in a clean readable format with "Copy to Clipboard" and "Download as PDF" buttons (use browser print to PDF, same pattern as existing report download)
- Add small editable fields above the letter: Patient Name, Provider Name, Claim Number — passed to backend and inserted into letter

---

### 4. Subdomain Routing — `health.civicscale.ai`

- Add a Vercel routing rule so `health.civicscale.ai` serves the React app with `/parity-health` as the root path
- Verify the Vercel config file path before editing — do not assume the filename
- Existing `/parity-health` routes continue to work unchanged — subdomain is additive

---

**After Claude Code completes, Fred needs to:**
1. Test CPT label display on a real bill upload — verify labels appear correctly and revenue codes are unaffected
2. Test the denial upload flow with a pasted denial letter — verify analysis JSON returns correctly
3. Test the appeal letter generator — verify the letter is coherent and references the specific denial
4. Verify `health.civicscale.ai` resolves correctly in Vercel

**Do not touch:** Signal, broker, employer, or provider routers. Auth system untouched — all Parity Health features remain anonymous for this session.

**Commit directly to main. No feature branches.**

---

## PENDING WORK — SESSION F (QUEUED)
**Website Redesign + Investor Page**

To be designed in Claude.ai first, then handed off to Claude Code.

**What to build:**
- Updated `civicscale.ai` homepage — mission statement, employer/broker two-path routing, Signal footer attribution, investor nav link
- `investors.civicscale.ai` subdomain — full platform story page, public-facing, single long-scroll
- `health.civicscale.ai` entry point (if not built in E-Health)
- Consistent CTA language and design conventions across all products

**Design conventions to apply everywhere:**

| Element | Standard |
|---------|----------|
| Primary CTA | "Start Free Trial" (employer) / "Get Started Free" (broker) |
| Trust line | "No credit card required for first 30 days · Cancel anytime" |
| Secondary CTA | Always "See a Demo" |
| Value prop format | 3 outcome bullets, not feature bullets |
| Tone | Direct, data-confident — never salesy |

**Subdomain architecture:**
```
civicscale.ai              → Main site: Employer + Broker + mission
provider.civicscale.ai     → Standalone Provider entry point
health.civicscale.ai       → Parity Health consumer app
investors.civicscale.ai    → Investor-facing narrative site
```

**Note:** Do not begin Session F until E-Signal and E-Health are complete. The investor copy depends on analytical profiles being real and Parity Health being a working product, not a landing page.

---

## PENDING WORK — SESSION G (QUEUED)
**Go Live**

- Swap Stripe test keys for live keys across all three products (env var swap in Render only)
- Verify all webhooks fire correctly in live mode
- Smoke test all checkout flows
- Half-session — mostly env var swaps and verification

---

## BROKER PORTAL — FULLY BUILT & DEPLOYED

### Features complete:
- OTP auth (8-digit codes) — migrated to unified auth (Session B)
- Book of Business dashboard with three tabs: Book of Business / Renewals / Prospects
- Renewal Timeline Tracker (≤90d amber / 91-180d blue / 180d+ muted)
- Renewal Prep Report at `/broker/renewal-prep/:companySlug`
- Prospect Benchmarking Tool
- CAA Claims Data Guide at `/broker/caa-guide` with dynamic letter generator
- Email notifications (welcome, renewal reminders, shared report viewed)
- Broker account page at `/broker/account`
- Level 2 Insights in broker dashboard and renewal prep report
- Multi-broker firm support (shared book of business)
- Broker-controlled employer invitation flow

### Broker freemium tier:
- Starter: free, up to 10 clients
- Pro: $99/mo, unlimited clients
- `broker_accounts.plan` field: `starter` | `pro` | `pro_cancelling`
- Stripe price: `STRIPE_PRICE_BROKER_PRO` (already in Render)

---

## PARITY EMPLOYER — PRODUCT FEATURES

### Fully built:
- `/billing/employer` — product landing page
- `/billing/employer/benchmark` — free benchmark tool (no auth required)
- `/billing/employer/claims-check` — claims upload + Level 1 + Level 2 analysis
- `/billing/employer/scorecard` — plan grading
- `/billing/employer/rbp-calculator` — RBP savings calculator
- `/billing/employer/contract-parse` — contract parser
- `/billing/employer/demo` — demo page
- `/employer/shared-report/:shareToken` — broker-shared report
- 30-day free trial ($99/mo after, introductory price locked 24 months)
- Read-only access preserved after cancellation

### Employer pricing:
- Single plan: 30-day free trial (card required upfront) → $99/mo
- Stripe price: `STRIPE_PRICE_EMPLOYER_PRO` (in Render)

### Level 2 Claims Analytics:
- Provider price variation (anonymized)
- Site of care opportunities (hospital vs non-hospital)
- Network leakage detection
- Carrier effective rate vs Medicare multiples
- CPT descriptions via `cptLabel()` helper
- Requires 835 EDI format (CSV uploads get Level 1 only)

### Sample 835 file:
`backend/data/sample/Midwest_Manufacturing_Dec2024.835`
- 1083 claims, 2166 NM1 segments, provider data included

---

## PARITY PROVIDER — STATUS

Full product exists, now on unified auth (Session C):
- `ProviderAuditPage.jsx` — audit submission
- `ProviderAuditReport.jsx` — report display
- `ProviderAuditAdmin.jsx` — admin view
- `ProviderDemoPage.jsx` — demo
- `AuditAccount.jsx` — account page
- All routes protected by AuthGate
- No real users exist

---

## PARITY SIGNAL — STATUS

Evidence intelligence platform. Multi-dimensional claim scoring across 6 dimensions. Analytical profiles table exists but not yet wired in (Session E-Signal).

**What's built and operational:**
- Multi-dimensional scoring: `source_quality`, `data_support`, `reproducibility`, `consensus`, `recency`, `rigor`
- Composite scores stored with `weights_used JSONB` — the weighting used to reach each conclusion is recorded
- `signal_consensus` table tracks `arguments_for` and `arguments_against` for debated claims
- Q&A endpoint — premium users can ask questions about topics, answered by Claude with scored evidence context
- Live metrics endpoint — claims scored, topics tracked, sources monitored, updates this month
- Subscription tiers: free / standard / premium
- Topic requests (premium feature)
- Evidence update notifications

**What's built but not yet wired in (Session E-Signal):**
- `signal_analytical_profiles` table — named profiles with different weightings showing how different conclusions arise. Marked "Phase 1 — create table now for readiness." Table exists, not populated.

---

## UNIFIED AUTH — DESIGN DECISIONS

| Decision | Choice |
|----------|--------|
| Session tokens | UUID stored in `sessions` table, 30-day expiry |
| Company membership | Admin-only invites — no auto domain matching |
| Broker firms | Same companies/company_users model as employers |
| Employer invitations from broker | Broker-controlled "Invite Client" button |
| Company types | employer / broker / provider |
| localStorage key | `cs_session_token` (single key across all products) |
| API auth header | `Authorization: Bearer {token}` |
| Role model | admin / member / viewer |

---

## ENVIRONMENT VARIABLES (Render — current)

```
ANTHROPIC_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET (used by signal_stripe.py)
STRIPE_EMPLOYER_WEBHOOK_SECRET (employer/broker webhook)
STRIPE_PRICE_BROKER_PRO
STRIPE_PRICE_EMPLOYER_PRO
RESEND_API_KEY
CRON_SECRET = notify-deliver-2026
```

**Obsolete (remove after confirming no references):**
```
STRIPE_PRICE_EMPLOYER_STARTER
STRIPE_PRICE_EMPLOYER_GROWTH
STRIPE_PRICE_EMPLOYER_SCALE
```

---

## STRIPE WEBHOOKS (registered)

1. Provider webhook: `https://parity-poc-api.onrender.com/api/provider/subscription/webhook`
2. Signal webhook: `https://parity-poc-api.onrender.com/api/signal/stripe/webhooks`
3. Employer/Broker webhook: `https://parity-poc-api.onrender.com/api/employer/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`
   - Secret: `STRIPE_EMPLOYER_WEBHOOK_SECRET`

---

## ROUTES (complete list)

```
/                                    → CivicScaleHomepage
/parity-health                       → ParityHealthLandingPage (to be replaced in E-Health)
/accept-invite                       → AcceptInvitePage

/billing/employer                    → EmployerProductPage
/billing/employer/signup             → EmployerSignupPage
/billing/employer/dashboard          → EmployerDashboard (auth protected)
/billing/employer/account            → EmployerAccountPage (auth protected)
/billing/employer/benchmark          → EmployerBenchmark
/billing/employer/claims-check       → EmployerClaimsCheck
/billing/employer/scorecard          → EmployerScorecard
/billing/employer/subscribe          → EmployerSubscribe (redirects to dashboard)
/billing/employer/rbp-calculator     → EmployerRBPCalculator
/billing/employer/contract-parse     → EmployerContractParser
/billing/employer/demo               → EmployerDemoPage

/billing/provider                    → ProviderProductPage
/billing/provider/demo               → ProviderDemoPage
/provider/*                          → ProviderApp (unified auth — Session C complete)
/audit                               → AuditStandalone (public)
/audit/account                       → AuditAccount (auth protected)

/employer/shared-report/:shareToken  → EmployerSharedReport

/broker                              → BrokerLandingPage
/broker/signup                       → BrokerSignupPage
/broker/login                        → BrokerLoginPage
/broker/dashboard                    → BrokerDashboard
/broker/account                      → BrokerAccountPage
/broker/caa-guide                    → CAABrokerGuide
/broker/renewal-prep/:companySlug    → RenewalPrepReport
```

---

## MIGRATIONS (run status)

| File | Status |
|------|--------|
| `001_unified_auth.sql` | ✅ Run |
| `002_employer_trial.sql` | ✅ Run |
| `028_deletion_requests.sql` | ✅ Run |
| `005_signal_tables.sql` | ✅ Run |
| `006_signal_public_read.sql` | ✅ Run |
| `007_signal_topic_requests.sql` | ✅ Run |

---

## STRATEGIC CONTEXT

### Brand architecture
```
civicscale.ai              → Main site: Employer + Broker + mission
provider.civicscale.ai     → Standalone Provider entry point (separate nav/hero)
health.civicscale.ai       → Parity Health consumer app
investors.civicscale.ai    → Investor-facing narrative site
```

### Product audience map
| Product | Who buys | Their goal | Their adversary |
|---------|----------|------------|-----------------|
| Parity Employer | HR/benefits directors | Reduce cost, benchmark, understand carrier data | Their carrier |
| Parity Provider | Practice managers, billing directors, CFOs | Get paid correctly, fight denials | Their payers/carriers |
| Parity Health | Individual consumers | Understand bills, appeal denials | Their insurer + provider |
| Parity Signal | Enterprise, researchers, policy orgs | Systemic intelligence | Opacity itself |

### The platform thesis (for investor conversations)
CivicScale is not a healthcare company. It is an information asymmetry engine deployed in healthcare first because the conditions there are uniquely favorable: a public reference price exists (Medicare), data is available due to price transparency regulations, the problem is visceral, and regulatory tailwinds (CAA, No Surprises Act) are forcing data into the open.

The real thesis: **any market where a discoverable truth exists but powerful intermediaries profit from hiding it is a Parity Signal market.**

What makes Parity Signal genuinely differentiated: it doesn't just find the gap between what things cost and what institutions claim they cost. It scores claims across multiple dimensions with recorded weights, tracks divergent arguments on contested claims, and is architected to support named analytical profiles that make competing conclusions legible — showing not just what is true but how different weightings of the same evidence produce different conclusions, and what it would take to change a decision.

### Go-to-market
- **Primary channel:** Independent benefits brokers (beachhead)
- **Broker value prop:** "Your clients' carriers have a data team. Now you do too."
- **Employer value prop:** Transparent benchmarking, not black-box consultant
- **Pricing:** Broker free (10 clients) / Pro $99/mo · Employer 30-day trial / $99/mo intro locked 24 months
- **Broker commission:** 20% recurring for 12 months on employer referrals, starts at first paid month
- **Data commitment:** "We will never contact your clients directly"
- **Key differentiator:** Independent data (not carrier-sourced), procedure-level Medicare benchmarking

### CTA conventions (to apply consistently across all products)
| Element | Standard |
|---------|----------|
| Primary CTA | "Start Free Trial" (employer) / "Get Started Free" (broker) |
| Trust line | "No credit card required for first 30 days · Cancel anytime" |
| Secondary CTA | Always "See a Demo" |
| Value prop format | 3 outcome bullets, not feature bullets |
| Tone | Direct, data-confident — never salesy |

---

## TECH STACK

- Python3 / pip3 (never python/pip)
- FastAPI backend on Render
- React/Vite frontend on Vercel
- Supabase PostgreSQL
- Stripe (test mode — Session G swaps to live)
- Resend email
- Anthropic Claude API (`claude-sonnet-4-6`) for AI features
- No feature branches — commit directly to main
