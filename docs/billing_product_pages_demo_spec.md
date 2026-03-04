# Parity Employer & Parity Provider — Product Pages + Sample Data Demos

## Overview

Each billing product needs two things: a public-facing product page that explains the value proposition (no login required), and an interactive demo pre-loaded with realistic sample data that lets visitors experience the actual dashboard.

---

## PARITY EMPLOYER

### Product Page — Route: `/billing/employer`

**Hero Section:**
- Headline: "See what your health plan is really costing you."
- Subhead: "Parity Employer benchmarks your self-insured claims against regional and national data to surface hidden cost drivers, overpriced providers, and savings opportunities."
- CTA: "Try the Demo" (loads sample data) and "Sign In" (existing login)

**Problem Statement Section:**
- "Self-insured employers spend $15,000+ per employee annually on healthcare — but most can't tell you whether those costs are fair. Your TPA sends you reports, but without independent benchmarks, you're trusting the same system that generates the bills to tell you if the bills are reasonable."
- "Parity Employer changes that. We compare your claims against Medicare fee schedules, regional commercial rates, and national averages — procedure by procedure, provider by provider — so you can see exactly where your plan is overpaying."

**What You Get Section (3 cards):**

Card 1: "Cost Benchmarking by Category"
- "See how your spending in orthopedics, cardiology, imaging, and 20+ other categories compares to regional benchmarks. Instantly identify which categories are driving above-market costs."

Card 2: "Provider-Level Analysis"  
- "Drill into individual providers to see who charges above market rates. Identify high-cost outliers and quantify the savings from steering to fairly-priced alternatives."

Card 3: "Actionable Savings Report"
- "Get a prioritized list of savings opportunities ranked by dollar impact. Each recommendation includes the data behind it — not just 'you're overpaying' but exactly how much, on which procedures, at which providers."

**How It Works Section (3 steps):**
1. "Upload your claims data" — "Export your claims file from your TPA or benefits administrator. We accept standard EDI 837/835 formats, CSV exports, or Excel files."
2. "We benchmark every line" — "Each claim is compared against Medicare fee schedules (adjusted for your geography), regional commercial rates, and national averages. We flag anomalies and quantify variances."
3. "Review your insights" — "Your dashboard shows cost variances by category, provider, and procedure — with specific dollar amounts and percentage differences. Export reports for your broker or benefits committee."

**Social Proof / Scale Section:**
- "$300B+ in estimated annual billing errors across the U.S. healthcare system"
- "The average self-insured employer overpays by 12-18% on specialist procedures"
- "Powered by the Parity Engine — the same benchmark infrastructure behind Parity Signal and Parity Health"

---

### Sample Data Demo — Route: `/billing/employer/demo`

**Sample Company Profile:**
- Company: "Midwest Manufacturing Co." (fictional)
- 500 covered lives (employees + dependents)
- Self-insured with Cigna TPA
- Plan year: 2025
- Total annual claims: ~$7.5M

**Sample Claims Dataset (pre-loaded, ~200 line items across categories):**

Category breakdown with benchmark variances:
- **Orthopedics**: $1.2M spent, 38% above regional benchmark (highest variance)
  - Key driver: Dr. James Orthton at Lakeview Ortho charges $4,200 for CPT 27447 (knee replacement) vs. $3,050 Medicare rate
  - 3 providers, 45 claims
- **Cardiology**: $890K spent, 12% above benchmark
  - Mostly in-line except imaging (cardiac MRI at $2,100 vs $1,400 benchmark)
  - 4 providers, 62 claims
- **Primary Care**: $1.8M spent, 5% below benchmark (good)
  - Well-managed, competitive rates
  - 12 providers, 340 claims
- **Imaging/Radiology**: $650K spent, 28% above benchmark
  - Hospital outpatient imaging driving cost vs. freestanding centers
  - MRI at hospital: $1,800 avg vs. $650 at freestanding
- **Emergency**: $420K spent, 22% above benchmark
  - Driven by 3 high-cost ER visits at out-of-network facilities
- **Lab/Pathology**: $380K spent, 8% above benchmark
  - Minor variances, a few specialty lab markups
- **Behavioral Health**: $310K spent, 2% below benchmark (good)
- **Pharmacy (Medical Benefit)**: $830K spent, 15% above benchmark
  - Infusion drugs at hospital outpatient vs. home infusion

**Demo Dashboard Screens:**

Screen 1: **Executive Summary**
- Total spend: $7.5M
- Benchmark spend: $6.1M  
- Potential savings: $1.4M (18.7%)
- Bar chart showing each category with actual vs. benchmark spend
- "Top 3 Savings Opportunities" cards with dollar amounts

Screen 2: **Category Deep Dive** (click into Orthopedics)
- Procedure-level breakdown: knee replacements, hip replacements, arthroscopy, spine
- Each procedure shows: your average cost, regional benchmark, Medicare rate, variance %
- Provider comparison table within category

Screen 3: **Provider Analysis** (click into specific provider)
- Provider profile: name, specialty, address, network status
- All claims from this provider with CPT codes, billed amounts, benchmark comparison
- "This provider charges 38% above the regional average for orthopedic procedures. Redirecting 50% of volume to benchmark-priced alternatives could save $180K annually."

Screen 4: **Savings Report**
- Ranked list of opportunities:
  1. "Switch orthopedic volume from Lakeview Ortho to Midwest Ortho Associates" — $180K
  2. "Move outpatient imaging to freestanding centers" — $95K  
  3. "Negotiate cardiac imaging rates with Heartland Cardiology" — $45K
  4. "Establish center of excellence for knee/hip replacement" — $120K
- Total identified savings: $440K (top 4 opportunities)
- Each item is expandable with supporting data

**Demo Banner:**
- Persistent banner at top: "You're viewing a demo with sample data. [Upload your own data →] [Sign up for access →]"

---

## PARITY PROVIDER

### Product Page — Route: `/billing/provider`

**Hero Section:**
- Headline: "Know what your contracts are really paying you."
- Subhead: "Parity Provider compares your payer contract rates against Medicare benchmarks and regional averages — and builds evidence-based denial appeals when claims are rejected."
- CTA: "Try the Demo" (loads sample data) and "Sign In" (existing login)

**Problem Statement Section:**
- "Most physician practices sign payer contracts and never benchmark them. You know what Medicare pays for CPT 99214, but do you know how your Blue Cross rate compares? Your Aetna rate? What about the rates your competitor down the street negotiated?"
- "When claims are denied, your billing team sends a standard appeal letter. But denials aren't random — they follow patterns driven by specific analytical choices the payer made about coding, bundling, or medical necessity. A generic appeal doesn't address the actual reason."
- "Parity Provider gives you two things: contract intelligence that shows where you're leaving money on the table, and denial intelligence that builds targeted appeals challenging the specific logic behind each denial."

**What You Get Section (3 cards):**

Card 1: "Contract Rate Benchmarking"
- "Upload your fee schedules and see how every CPT code compares to Medicare, regional commercial averages, and specialty-specific benchmarks. Identify the codes where you're underpaid and quantify the revenue gap."

Card 2: "Denial Intelligence & Appeals"
- "Analyze your denial patterns by payer, reason code, and procedure. Our AI identifies the specific analytical choices behind each denial — was it a bundling rule? A medical necessity algorithm? A modifier issue? — and generates targeted appeal language that challenges that specific logic."

Card 3: "Revenue Gap Analysis"
- "See the total dollar impact of contract shortfalls and denial patterns. Prioritize which payer negotiations and appeal efforts will recover the most revenue. Track your progress over time."

**How It Works Section (3 steps):**
1. "Connect your data" — "Upload your fee schedules, remittance data (ERA/835), and denial reports. We accept standard formats from all major practice management systems."
2. "We analyze every rate and denial" — "Each contracted rate is benchmarked. Each denial is classified by root cause and mapped to the payer's analytical logic. Patterns emerge that aren't visible in standard reports."
3. "Act on insights" — "Use contract benchmarks in your next payer negotiation. Deploy targeted denial appeals that address the actual reason for rejection. Track revenue recovery over time."

**Analytical Paths Highlight Section:**
- "Most denial appeals fail because they argue the wrong point. Parity Provider uses Analytical Paths — our proprietary methodology for revealing the invisible choices behind a decision — to identify exactly why a claim was denied and build an appeal that challenges that specific logic."
- Example callout: "A standard appeal says: 'We believe this claim was incorrectly denied.' An Analytical Paths appeal says: 'This denial applied CPT bundling rule 59.4, which assumes services were part of a single procedure. However, the documented clinical circumstances — separate anatomical sites, distinct diagnoses — meet CMS exception criteria under NCCI Policy Manual Chapter 1, Section G.'"

---

### Sample Data Demo — Route: `/billing/provider/demo`

**Sample Practice Profile:**
- Practice: "Lakeside Internal Medicine & Cardiology" (fictional)
- 6 physicians (4 internists, 2 cardiologists)
- 3 payer contracts: Blue Cross Blue Shield, Aetna, UnitedHealthcare
- Annual revenue: ~$4.2M
- Denial rate: 11.2% (industry average ~5-10%)

**Sample Fee Schedule Data (pre-loaded):**

Payer rate comparisons for top 20 CPT codes:

| CPT | Description | Medicare | BCBS | Aetna | UHC | Best Rate | Worst Rate |
|-----|-------------|----------|------|-------|-----|-----------|------------|
| 99214 | Office visit, est. patient, moderate | $128 | $142 (+11%) | $118 (-8%) | $135 (+5%) | BCBS | Aetna |
| 99213 | Office visit, est. patient, low | $98 | $104 (+6%) | $89 (-9%) | $96 (-2%) | BCBS | Aetna |
| 93000 | ECG, 12-lead | $18 | $22 (+22%) | $15 (-17%) | $19 (+6%) | BCBS | Aetna |
| 93306 | Echo, complete | $185 | $198 (+7%) | $165 (-11%) | $190 (+3%) | BCBS | Aetna |
| 99215 | Office visit, est. patient, high | $172 | $180 (+5%) | $155 (-10%) | $168 (-2%) | BCBS | Aetna |

**Key Findings in Demo:**
- Aetna contract is systematically 8-11% below Medicare across E&M codes — $127K annual revenue gap
- BCBS is the strongest contract (+7% avg above Medicare)
- UHC is near Medicare rates but has the highest denial rate (14.3%)
- Total identified revenue gap from contract shortfalls: $127K (Aetna) + $23K (UHC) = $150K

**Sample Denial Data (pre-loaded, ~60 denials):**

Denial patterns by payer:
- **UnitedHealthcare** (14.3% denial rate, 34 denials):
  - 12 denials: "Medical necessity not established" on CPT 93306 (echocardiogram)
  - 8 denials: Modifier 25 rejected on same-day E&M + procedure
  - 6 denials: "Duplicate claim" (actually separate dates of service)
  - 8 denials: Various other
- **Aetna** (9.1% denial rate, 16 denials):
  - 7 denials: Bundling — 99214 + 93000 denied as inclusive
  - 5 denials: Pre-authorization not obtained (cardiac imaging)
  - 4 denials: Various other
- **BCBS** (6.4% denial rate, 10 denials):
  - 4 denials: Timely filing (>90 days)
  - 3 denials: Coordination of benefits
  - 3 denials: Various other

**Demo Dashboard Screens:**

Screen 1: **Practice Overview**
- Annual revenue: $4.2M
- Revenue gap (contract shortfalls): $150K
- Denial rate: 11.2% (benchmark: 5-10%)
- Denied revenue at risk: $89K
- Total recovery opportunity: $239K
- Payer performance cards: BCBS (green — strong), UHC (amber — high denials), Aetna (red — underpaying)

Screen 2: **Contract Benchmarking** (click into Aetna)
- CPT-by-CPT comparison: your rate vs. Medicare vs. regional average
- Highlight codes where Aetna pays below Medicare
- Revenue gap by code: 99214 accounts for $42K of the $127K gap
- "Negotiation brief" preview: top 5 codes to prioritize in next contract negotiation with supporting benchmark data

Screen 3: **Denial Intelligence** (click into UHC echocardiogram denials)
- Pattern view: 12 denials, same reason code, same CPT, span 6 months
- Root cause analysis: "UHC is applying a medical necessity algorithm that requires a documented change in clinical status within 90 days of the prior echocardiogram. 9 of 12 denied claims had a documented change — the denial appears to be systematic, not case-by-case."
- Analytical Paths breakdown:
  - Choice 1: "UHC applied frequency limit (1 echo per 90 days)"
  - Choice 2: "Override for clinical change was not recognized"
  - Choice 3: "Documentation of clinical change was present but not in the expected field"
- Suggested appeal strategy: "Challenge the frequency limit application by citing the documented clinical changes. Reference ACC/AHA Appropriate Use Criteria for repeat echocardiography."

Screen 4: **Sample Denial Appeal** (generated for one specific claim)
- Full appeal letter with:
  - Claim details (patient DOB, dates, CPT, billed amount)
  - Denial reason quoted from the ERA
  - Analytical Paths analysis: "This denial was based on [specific rule]. However, [specific evidence contradicting the rule]."
  - Supporting references: CMS guidelines, ACC/AHA criteria, NCCI Policy Manual
  - Request for reconsideration with specific dollar amount
- "This appeal addresses the actual analytical logic behind the denial, not just the outcome. Generic appeals succeed ~30% of the time. Targeted appeals succeed ~65% of the time."

Screen 5: **Revenue Recovery Tracker** (over time)
- Monthly chart showing: denials submitted → appeals sent → appeals won → dollars recovered
- Sample data shows 3 months of tracking with improving recovery rate
- "Since implementing targeted appeals: denial overturn rate improved from 28% to 62%, recovering $34K in previously lost revenue"

**Demo Banner:**
- Persistent banner at top: "You're viewing a demo with sample data from a fictional practice. [Upload your own data →] [Sign up for access →]"

---

## Shared Design Notes

**Visual Consistency:**
- Use the blue accent (#3b82f6 / #60a5fa) for all billing product pages — matches the homepage billing section
- Dark theme consistent with rest of site
- DM Sans + DM Serif Display fonts
- Cards, stats, and layout patterns should feel like siblings of the Signal dashboard

**Demo Data Storage:**
- All sample data should be hardcoded JSON files in the frontend — no database queries needed for demo mode
- Demo mode is detected by route (`/billing/employer/demo` and `/billing/provider/demo`)
- Same dashboard components render real or demo data — just a different data source

**Mobile Responsive:**
- Product pages: single column on mobile, stacked sections
- Demo dashboards: tables become scrollable horizontally on mobile, cards stack vertically

**Navigation:**
- From billing landing page (`/billing`): each product card links to its product page
- From product page: "Try the Demo" → demo dashboard, "Sign In" → existing auth flow
- Demo dashboard has persistent banner linking to sign-up
- Back navigation: product page → billing landing page → homepage

---

## Implementation Priority

1. **Product pages** for both Employer and Provider (content + layout, no data)
2. **Employer demo dashboard** with sample data (most straightforward — benchmarking is the core feature)
3. **Provider demo dashboard** with sample data (more complex — includes denial intelligence and appeal generation)
4. **Connect demo CTAs** to sign-up/auth flow

## Estimated Build Effort

- Product pages: ~2 hours each (mostly content, standard layout)
- Employer demo: ~4 hours (dashboard components + sample data)
- Provider demo: ~6 hours (dashboard + denial analysis + sample appeal generation)
- Total: ~14 hours of Claude Code time
