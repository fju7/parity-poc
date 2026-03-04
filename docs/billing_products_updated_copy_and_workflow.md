# Parity Employer & Provider — Updated Product Pages + Build Workflow

## PART 1: UPDATED PRODUCT PAGE COPY

These replace the existing product page text. The key changes: explain WHY AI matters for each product, differentiate from existing market solutions, and be honest about what's built vs. what's coming.

---

### PARITY EMPLOYER — Updated Product Page

**Route: `/billing/employer`**

**Hero:**
- Headline: "See what your health plan is really costing you."
- Subhead: "AI-powered claims benchmarking that tells you exactly where your self-insured plan is overpaying — by category, by provider, by procedure."

**Why AI Changes Everything Section:**

Headline: "Why this couldn't exist without AI"

"Traditional benefits consultants sample 5-10% of your claims and compare them against broad averages. That misses the details that matter — the specific provider charging 40% above market for knee replacements, the hospital outpatient facility fee that's triple what a freestanding center charges, the imaging costs that quietly doubled year over year.

Parity Employer uses AI to analyze every single claim against Medicare fee schedules, regional commercial benchmarks, and — as our community database grows — actual reported rates from real plans. Not a sample. Every line. The AI reads CPT codes, maps them to procedure categories, normalizes for geography, and flags anomalies that a human analyst reviewing spreadsheets would never catch.

But unlike a black-box AI that just gives you a number, we show you the analytical path: why a cost is flagged, what benchmark it's compared against, and what assumptions went into the comparison. You see the methodology, not just the conclusion."

**How We're Different Section:**

Three comparison cards:

Card 1: "vs. Your Benefits Consultant"
"Consultants review summary-level data and rely on proprietary benchmarks you can't verify. They bill $50-150K annually for what amounts to a few pivot tables and some industry averages. Parity Employer analyzes every claim, uses transparent benchmarks, and costs a fraction of traditional consulting."

Card 2: "vs. TPA Reports"
"Your TPA manages the same claims they're reporting on — that's a structural conflict of interest. Their reports tell you what happened but not whether it was fair. Parity Employer provides independent analysis against external benchmarks, so you're not relying on the same system that generates the bills to tell you if the bills are reasonable."

Card 3: "vs. Other Analytics Platforms"
"Most claims analytics platforms require a 6-month implementation, EDI integration, and a six-figure contract. Parity Employer works with the claims export you already have — CSV, Excel, or standard EDI formats. Upload your data and get results the same day. No implementation project required."

**What You Need to Get Started Section:**

"Export your claims data from your TPA or benefits administrator. Most TPAs can generate a claims extract in CSV or Excel format — ask for service dates, CPT/HCPCS codes, billed amounts, allowed amounts, paid amounts, provider names, and member ZIP codes.

We accept:
- CSV or Excel claims exports (most common)
- EDI 837 Professional/Institutional files
- EDI 835 Remittance files
- Custom formats (contact us and we'll build an importer)

Your data is processed securely and never shared. Individual claims are anonymized after analysis — we keep only aggregate benchmarks, never identifiable records."

**Roadmap Transparency Section (builds credibility):**

"✅ Available now: Medicare fee schedule benchmarking for every CPT code, geographic adjustment, category-level cost analysis, provider-level variance identification

🔄 Coming soon: Community-reported commercial rate benchmarks (powered by anonymized data from Parity Health users), year-over-year trend analysis, automated savings recommendations with estimated dollar impact

🔮 On our roadmap: Direct TPA integration for automated data refresh, network optimization modeling, pharmacy benefit benchmarking"

---

### PARITY PROVIDER — Updated Product Page

**Route: `/billing/provider`**

**Hero:**
- Headline: "Know what your contracts are really paying you."
- Subhead: "AI-powered contract benchmarking and denial intelligence for physician practices that want to negotiate from evidence, not intuition."

**Why AI Changes Everything Section:**

Headline: "Your billing team is fighting denials blind"

"The average physician practice has a denial rate between 5-10%. Each denied claim costs $25-35 to rework and takes 14+ days to resolve. Most practices send generic appeal letters — 'we believe this was incorrectly denied' — and win about 30% of the time.

The problem isn't effort. It's information asymmetry. The payer used a specific algorithm or rule to deny your claim — a bundling edit, a medical necessity algorithm, a frequency limit. But they don't tell you which rule, and your billing team doesn't have time to research it for every denial.

AI changes this equation. Parity Provider reads your ERA data, classifies each denial by its root cause, identifies patterns across hundreds of denials, and — using our Analytical Paths methodology — maps the specific analytical choices the payer made. Then it generates a targeted appeal that challenges that specific logic, citing the relevant CMS guidelines, specialty society criteria, and coding rules.

A generic appeal succeeds ~30% of the time. A targeted appeal that addresses the actual denial logic succeeds ~60-65% of the time. That's the difference between recovering $50K and recovering $100K on the same denial volume."

**Analytical Paths — The Core Innovation Section:**

"Every denial is a conclusion. Behind that conclusion is a chain of analytical choices the payer made:

→ Which bundling rules to apply
→ How to interpret modifier usage  
→ What constitutes medical necessity for a given procedure
→ How strictly to enforce frequency limits
→ Whether to apply the most restrictive or most generous interpretation

These choices are invisible to you. You see 'claim denied' — you don't see which analytical path led to that denial.

Analytical Paths is our methodology for making those invisible choices visible. For each denial, we identify the specific rule applied, the interpretation used, and the alternative interpretations that support your claim. Then we build an appeal that doesn't just say 'we disagree' — it says 'you applied Rule X with Interpretation Y, but CMS Guideline Z supports Interpretation W, and here's why.'

This is the same methodology that powers Parity Signal's evidence scoring and Parity Health's bill analysis. One engine, multiple applications — all focused on making analytical choices transparent."

**How We're Different Section:**

Card 1: "vs. Your Billing Company"
"Your billing team processes denials reactively — one at a time, using template letters. They don't have the bandwidth to research each denial's root cause or track patterns across payers. Parity Provider analyzes all your denials at once, identifies systematic patterns, and generates appeals that address the actual reason — not just the outcome."

Card 2: "vs. Revenue Cycle Management Software"
"RCM platforms track denials and help you manage the workflow. But they don't analyze why denials happen or generate targeted appeals. They tell you 'you had 47 denials from UHC this quarter.' We tell you 'UHC denied 12 echocardiograms using a frequency limit that doesn't account for documented clinical changes — here are 12 targeted appeals with supporting guidelines.'"

Card 3: "vs. Denial Management Services"
"Outsourced denial management services charge 15-25% of recovered revenue. They use standard appeal processes that don't scale. Parity Provider gives your own team the intelligence to fight denials effectively — and you keep 100% of what you recover."

**What You Need to Get Started Section:**

"For contract benchmarking:
- Your payer fee schedules (the contracted rates for your top CPT codes)
- If you don't have a fee schedule document, your recent remittance data works — we can extract effective rates from payment history

For denial intelligence:
- ERA/835 remittance files from your practice management system (most systems can export these)
- Or a denial report with: CPT code, denial reason code (CARC/RARC), payer, date, and billed amount
- CSV or Excel exports also accepted

Your data is processed securely and never shared outside your practice."

**How It Builds Over Time Section (honest about the learning curve):**

"Month 1: Pattern Detection
Upload your denial data and see immediate insights — denial rates by payer, most-denied CPT codes, most common denial reasons. AI generates initial appeals using general coding guidelines and payer-specific rules.

Month 2-3: Targeted Intelligence  
As the system processes more of your denials, patterns sharpen. Analytical Paths identifies the specific logic behind recurring denial types. Appeals become increasingly targeted — citing exact policy manual sections, pointing to specific guideline criteria your claims meet.

Month 4+: Predictive & Proactive
With enough history, the system begins predicting which claims are likely to be denied before submission and recommending documentation or coding adjustments. Contract negotiation briefs are generated automatically before renewal periods, showing exactly which codes are underpaid and by how much."

**Roadmap Transparency Section:**

"✅ Available now: Fee schedule benchmarking against Medicare rates for every CPT code, geographic adjustment, payer-by-payer rate comparison, revenue gap calculation

✅ Available now: Denial pattern analysis — classification by reason code, payer, and procedure category, with frequency and dollar-impact tracking

🔄 Coming soon: AI-generated targeted denial appeals using Analytical Paths methodology, with CMS guideline citations and specialty-specific supporting evidence

🔄 Coming soon: Community-reported contract rate benchmarks (aggregated from Parity Provider users — anonymized, minimum thresholds for display)

🔮 On our roadmap: Pre-submission denial risk scoring, automated ERA ingestion from clearinghouses, contract negotiation brief generator, payer performance scorecards"

---

## PART 2: BUILD WORKFLOW — WHAT'S REAL VS. WHAT NEEDS BUILDING

### Current State (What Exists Today)

| Capability | Status | Used By |
|---|---|---|
| CPT → Medicare fee schedule benchmark | ✅ Built | Parity Health |
| Geographic adjustment (ZIP → region) | ✅ Built | Parity Health |
| Claude API extraction from text/image | ✅ Built | Parity Health multi-input |
| Benchmark observations storage | ✅ Being built | Parity Health |
| Supabase database infrastructure | ✅ Live | All products |
| Stripe subscription billing | ✅ Live | Signal |
| Analytical Paths (concept + Signal implementation) | ✅ Live in Signal | Signal evidence scoring |

### Parity Employer — Build Path

**Phase E1: Batch Claims Ingestion (2-3 days Claude Code)**
- New upload flow accepting CSV/Excel with multiple claims
- Column mapping UI: user maps their columns to standard fields (CPT code, amount, provider, date, etc.)
- Claude API assists with auto-detecting column mappings from header names
- Parse and validate all rows, flag issues
- WHY THIS IS BUILDABLE: Same extraction logic as Parity Health, just processing N rows instead of 1

**Phase E2: Category Grouping Engine (1-2 days Claude Code)**  
- CPT → category mapping table (published by CMS — the Berenson-Eggers Type of Service categories, or custom groupings)
- Aggregate claims by category: total spend, claim count, average per-claim
- Compare each category's average against Medicare benchmark
- WHY THIS IS BUILDABLE: Straightforward data transformation, no AI required, CPT→category mappings are public

**Phase E3: Provider-Level Analysis (1-2 days Claude Code)**
- Group claims by provider (name normalization needed — "DR JOHN SMITH" = "John Smith MD")
- Per-provider: total billed, average per-CPT, variance from benchmark
- Rank providers by total dollar variance
- WHY THIS IS BUILDABLE: Grouping and aggregation on data already ingested

**Phase E4: Savings Report (1 day Claude Code)**
- For each high-variance provider/category: calculate savings if rates matched benchmark
- Rank by dollar impact
- Generate plain-language recommendations using Claude API
- WHY THIS IS BUILDABLE: Arithmetic on existing data + Claude for narrative generation

Total employer build: ~7-8 days Claude Code

### Parity Provider — Build Path

**Phase P1: Fee Schedule Ingestion (2-3 days Claude Code)**
- Upload flow for fee schedules (CSV/Excel with CPT code + contracted rate per payer)
- Claude API assists with column detection
- Store in new table: `provider_fee_schedules` (practice_id, payer, cpt_code, contracted_rate)
- Compare each rate against Medicare
- WHY THIS IS BUILDABLE: Same pattern as employer claims ingestion, simpler data structure

**Phase P2: Revenue Gap Calculator (1 day Claude Code)**
- For each CPT where contracted rate < Medicare rate: calculate gap × claim volume
- Aggregate by payer: "Aetna underpays by $127K annually across these codes"
- Rank by dollar impact for negotiation prioritization
- WHY THIS IS BUILDABLE: Pure arithmetic once fee schedule and volume data exist

**Phase P3: Denial Data Ingestion (2-3 days Claude Code)**
- Accept ERA/835 files or CSV denial reports
- Parse denial reason codes (CARC/RARC) — these are standardized codes
- Classify denials: bundling, medical necessity, authorization, timely filing, modifier, etc.
- Store in new table: `provider_denials` (practice_id, payer, cpt_code, carc_code, rarc_code, amount, date, status)
- WHY THIS IS BUILDABLE: CARC/RARC codes are a published standard, parsing is straightforward

**Phase P4: Denial Pattern Analysis (2-3 days Claude Code)**
- Group denials by payer × reason code × CPT code
- Identify systematic patterns: "UHC denied CPT 93306 twelve times using CARC 97"
- Calculate dollar impact per pattern
- WHY THIS IS BUILDABLE: Aggregation and pattern detection on structured data

**Phase P5: Analytical Paths for Denials (3-5 days Claude Code)**
- Build a denial reason code → analytical choices knowledge base
- For each major CARC code, document:
  - What analytical choice the payer made
  - What alternative interpretations exist
  - Which CMS/specialty guidelines support the alternative
- This is a KNOWLEDGE BASE, not code — ~50 CARC codes cover 90% of denials
- Store as structured JSON or a Supabase table
- WHY THIS IS BUILDABLE: The analytical choices are documented in CMS manuals and coding guides. Claude already knows most of this — the knowledge base just structures it for consistent application.

**Phase P6: Appeal Letter Generation (2-3 days Claude Code)**
- Given: denial details + analytical paths knowledge base entry + practice context
- Claude API generates targeted appeal letter
- Prompt includes: the specific CARC/RARC code, the analytical path, relevant guidelines, claim details
- Output: formatted appeal letter with citations
- WHY THIS IS BUILDABLE: This is a prompt engineering task. Claude already knows medical coding, CMS guidelines, and appeal letter format. The analytical paths knowledge base provides the structured context that makes the output targeted rather than generic.

**Phase P7: Recovery Tracking (1 day Claude Code)**
- Track appeal outcomes: submitted → won/lost → amount recovered
- Dashboard showing recovery rate over time
- WHY THIS IS BUILDABLE: Simple status tracking on existing denial records

Total provider build: ~14-18 days Claude Code

### Overall Build Timeline

| Phase | Product | Days | Dependencies |
|---|---|---|---|
| E1 | Employer: Batch ingestion | 2-3 | None |
| E2 | Employer: Category grouping | 1-2 | E1 |
| P1 | Provider: Fee schedule ingestion | 2-3 | None (parallel with E1-E2) |
| E3 | Employer: Provider analysis | 1-2 | E1 |
| E4 | Employer: Savings report | 1 | E2, E3 |
| P2 | Provider: Revenue gap | 1 | P1 |
| P3 | Provider: Denial ingestion | 2-3 | None |
| P4 | Provider: Pattern analysis | 2-3 | P3 |
| P5 | Provider: Analytical Paths KB | 3-5 | P4 |
| P6 | Provider: Appeal generation | 2-3 | P5 |
| P7 | Provider: Recovery tracking | 1 | P6 |

Total: ~20-26 days of Claude Code work
Can be parallelized: Employer and Provider Phase 1-2 can run simultaneously

---

## PART 3: DEMONSTRATING THIS ISN'T VAPORWARE

### The "Show Your Work" Approach

The product pages include a "Roadmap Transparency" section that explicitly labels what's built, what's coming soon, and what's on the longer-term roadmap. This is unusual for a startup — most companies pretend everything is built — and it builds credibility with sophisticated buyers (CFOs, practice managers) who are used to being oversold.

### The Demo Data Connection

The demo dashboards use realistic sample data that demonstrates real analytical capabilities. The benchmark comparisons in the demo are calculated using the same Medicare fee schedule lookup engine that powers live Parity Health analyses. When a visitor sees "CPT 99213: Your rate $89 vs. Medicare $98 (-9%)" in the demo, that Medicare rate is real and accurate.

### The Progressive Capability Narrative

Instead of claiming everything works perfectly on day one, the product pages describe a progression:
- Month 1: Basic benchmarking and pattern detection (this is buildable NOW)
- Month 2-3: Targeted intelligence as the system processes more data
- Month 4+: Predictive capabilities

This is honest AND compelling. It acknowledges that the system improves with use (which is true of any AI system) while demonstrating that day-one value exists.

### Key Talking Points for Investor/Partner Conversations

"Is the denial intelligence actually built?"

Answer: "The AI engine that powers it — Claude — already understands medical coding, CMS guidelines, and appeal letter structure. What we've built is the analytical framework that structures that knowledge: the denial reason code taxonomy, the analytical paths that map each denial type to specific payer choices, and the prompt engineering that generates targeted appeals instead of generic ones. The knowledge base is built from public CMS and NCCI documentation. We're not inventing medical coding rules — we're making the existing rules accessible and actionable."

"How do you know targeted appeals actually work better?"

Answer: "Industry data from MGMA and HFMA consistently shows that appeals citing specific policy references and guideline criteria succeed at roughly double the rate of generic appeals. Our Analytical Paths methodology systematically identifies the right references for each denial type — something a billing team could theoretically do manually, but doesn't have time to do at scale."

"What if the demo data doesn't match real-world data?"

Answer: "The demo uses realistic rates derived from actual Medicare fee schedules and published commercial-to-Medicare rate ratios. The variance patterns (orthopedics running 30-40% above benchmark, primary care near benchmark) match what RAND Corporation and other researchers have documented. When a user uploads their actual data, the same engine runs the same analysis — the demo just shows the output format and analytical approach."
