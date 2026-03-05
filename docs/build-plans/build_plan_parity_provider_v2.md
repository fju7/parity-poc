# Parity Provider — Updated Build Plan (v2)
**Product:** Ongoing practice revenue intelligence, powered by the Parity Audit as entry point
**Routes:** civicscale.ai/audit (entry), civicscale.ai/provider (ongoing)
**Status:** Audit complete and tested. Conversion flow and ongoing intelligence features not yet built.
**Last updated:** March 5, 2026
**Supersedes:** build_plan_parity_provider.md (original)

---

## Product Narrative

The Parity Audit is not a separate product — it's Month 1 of Parity Provider. The practice doesn't "convert" from one thing to another. They get a free audit, see the findings, and the natural next step is: "keep watching this for me."

**Audit (free):** "Is your payer paying what they owe you?" One month, one report, concrete findings.

**Monitoring subscription ($300/month):** "Are they still paying correctly, and what's changing?" Monthly analysis against the same fee schedules already loaded, with trend tracking and alerts.

**Full Intelligence (future, $500/month):** "How do you compare to peers, and where should you focus?" Coding optimization, benchmark comparisons, payer negotiation intelligence. Requires scale.

---

## What's Already Built

| Capability | Status |
|---|---|
| 835 remittance file parsing | ✅ Built |
| Multi-input fee schedule ingestion (5 methods) | ✅ Built |
| Multi-payer batch analysis | ✅ Built |
| Contract integrity analysis (paid vs contracted) | ✅ Built |
| AI Denial Intelligence (pattern detection, plain language) | ✅ Built |
| AI Revenue Gap Estimator | ✅ Built |
| AI Contractor Performance Scorecard | ✅ Built |
| Appeal letter drafting | ✅ Built |
| Branded 9-section PDF audit report | ✅ Built |
| Audit onboarding wizard (5 steps) | ✅ Built |
| Audit admin dashboard | ✅ Built |
| Public report viewer (signed token URL) | ✅ Built |
| Audit account page (user's audit history) | ✅ Built |
| Submission, delivery, follow-up emails | ✅ Built |
| Provider demo (Lakeside Internal Medicine) | ✅ Built |
| Provider product page | ✅ Built |

---

## What Needs to Be Built — 4 Instructions

### Instruction 1: Audit-to-Subscription Conversion Flow

**The problem:** When a practice likes their audit results and wants ongoing monitoring, there's no way to carry the audit data forward into a subscription. They'd have to re-upload everything.

**The solution:** One-click conversion that creates a Provider subscription pre-populated with all audit data.

> "Build an audit-to-subscription conversion flow for Parity Provider. When a practice has a completed audit and wants ongoing monitoring, all their data should carry forward seamlessly.
>
> **Backend:**
>
> Create a new Supabase table `provider_subscriptions`:
> - id (UUID, primary key)
> - practice_name (TEXT)
> - practice_specialty (TEXT)
> - num_providers (INTEGER)
> - billing_company (TEXT, nullable)
> - contact_email (TEXT)
> - user_id (UUID, nullable — linked to Supabase auth if they create an account)
> - payer_data (JSONB — array of {payer_name, fee_schedule_method, fee_schedule_data})
> - source_audit_id (UUID, nullable — references provider_audits.id if converted from audit)
> - stripe_customer_id (TEXT, nullable)
> - stripe_subscription_id (TEXT, nullable)
> - status (TEXT — active, canceled, past_due)
> - monthly_analyses (JSONB — array of {month, analysis_ids, report_token, delivered_at})
> - created_at (TIMESTAMPTZ)
> - canceled_at (TIMESTAMPTZ, nullable)
>
> Enable RLS: service_role full access, authenticated users can read own subscription by user_id or contact_email.
>
> New endpoint: `POST /api/provider/subscription/convert-audit`
> - Input: audit_id, optional stripe payment info
> - Copies payer_data (including all fee schedule data) from provider_audits into provider_subscriptions
> - Copies the audit's analysis results as the first entry in monthly_analyses (labeled as the audit month)
> - Copies remittance_data from the audit
> - Sets status to 'active'
> - Returns subscription_id
>
> New endpoint: `POST /api/provider/subscription/add-month`
> - Input: subscription_id, 835 files (multipart upload)
> - Parses 835 files, matches to payers (using existing payer_data fee schedules)
> - Runs contract integrity + denial intelligence analysis
> - Appends results to monthly_analyses array
> - Returns analysis summary
>
> **Admin dashboard addition:**
> - On delivered audits, add a 'Convert to Subscription' button
> - Clicking it creates the provider_subscription record, copies all data, and sends an email to the practice: "Your Parity monitoring is now active. Your audit findings are your baseline. When your next month's remittance files are ready, upload them at [link] or send them to fred@civicscale.ai."
> - Show active subscriptions on the admin dashboard alongside audits (new tab: 'Subscriptions')
>
> **Frontend:**
> - In the audit account page (/audit/account), for delivered audits, show a 'Start Monthly Monitoring' CTA: 'Your audit found $X in recoverable revenue. Keep watching your payer payments for $300/month.' Clicking leads to a simple checkout (Stripe, same pattern as Signal).
> - After subscription is active, the audit account page transforms into a subscription dashboard showing: practice name, subscription status, months analyzed, and an 'Upload New Month' button.
>
> **Stripe:**
> - Create a Provider monitoring product in Stripe: $300/month
> - Use the same Stripe checkout/portal pattern as Signal subscriptions
>
> Print the migration SQL so I can run it in Supabase."

**Verify:** Complete an audit, convert it to subscription from admin dashboard, confirm all data carries over, confirm Stripe checkout works, confirm practice sees their subscription dashboard.

---

### Instruction 2: Inbound Email 835 Ingestion

**The problem:** Logging into a portal to upload 835 files monthly is friction that causes churn. Practices already receive 835 files via email from clearinghouses. They should be able to forward them directly.

**The solution:** An inbound email address that receives 835 files and automatically processes them.

> "Set up inbound email 835 ingestion for Provider subscriptions. The practice should be able to forward their 835 files to an email address and have them automatically processed.
>
> **Approach:** Use Resend's inbound email feature (or Mailgun/Postmark if Resend doesn't support inbound). Set up an inbound email address: 835@civicscale.ai (or upload@civicscale.ai).
>
> **Processing logic:**
> 1. Receive email with attachment(s)
> 2. Identify the practice by matching the sender's email address against provider_subscriptions.contact_email
> 3. If no match found, try matching against provider_audits.contact_email (they may have an audit but not a subscription yet — store the files and notify admin)
> 4. If match found and subscription is active:
>    - Extract all .835, .edi, or .txt attachments
>    - Parse each file using the existing 835 parser
>    - Match parsed claims to the practice's payers using existing fee schedules in payer_data
>    - Run contract integrity analysis and denial intelligence
>    - Append results to the subscription's monthly_analyses
>    - Send confirmation email to the practice: 'We received and analyzed your February remittance files. 4 underpayments found. [View Report]'
>    - Send notification to fred@civicscale.ai: 'New month processed for [practice]. [View in admin]'
> 5. If match found but subscription is not active, send email to admin and reply to practice: 'We received your files. Your monitoring subscription is not currently active. [Reactivate] or contact fred@civicscale.ai.'
> 6. If no match found at all, forward the email to fred@civicscale.ai for manual handling.
>
> **Error handling:**
> - If no attachments found, reply: 'We didn't find any 835 files attached. Please forward the email from your clearinghouse that contains the .835 or .edi attachment.'
> - If parsing fails, notify admin with the error and reply to practice: 'We had trouble processing one of your files. Our team will look into it and follow up.'
>
> **Frontend:**
> - On the subscription dashboard, show the inbound email address prominently: 'Send your 835 files to: 835@civicscale.ai — we'll process them automatically and email you the results.'
> - In the audit delivery email and conversion email, include: 'Each month, just forward your 835 files from your clearinghouse to 835@civicscale.ai. We'll handle the rest.'
>
> Check whether Resend supports inbound email. If not, recommend an alternative that works with our existing infrastructure (Render backend, Python/FastAPI). The inbound webhook should hit a new endpoint: `POST /api/provider/inbound-835`"

**Verify:** Send an email with the sample 835 file as an attachment to the inbound address. Confirm it's parsed, matched to a test subscription, analyzed, and the practice receives a confirmation email with findings.

---

### Instruction 3: Month-Over-Month Trend Comparison

**The problem:** A single month's findings are useful but don't show patterns. The subscription's core value over the audit is showing what's changing over time.

**The solution:** Compare each month's results to the previous month and flag changes.

> "Add month-over-month trend analysis to Provider subscriptions. When a new month of 835 data is analyzed, compare results to previous months and highlight what changed.
>
> **Backend:**
>
> New endpoint: `GET /api/provider/subscription/{id}/trends`
> - Returns per-payer, per-CPT trends across all months in monthly_analyses
> - Structure: { payer_name, cpt_code, months: [{month, paid_amount, expected_amount, variance, denial_count}] }
>
> **Trend detection logic** (runs after each new month's analysis):
> 1. **New underpayments:** CPT codes that were paid correctly last month but are underpaid this month. Flag as: 'NEW: Aetna began underpaying 99214 in February — paid $148 vs contracted $162.'
> 2. **Worsening underpayments:** Same CPT codes underpaid in consecutive months but by increasing amounts. Flag as: 'WORSENING: Aetna 99214 underpayment grew from $13 in January to $22 in February.'
> 3. **Resolved underpayments:** CPT codes that were underpaid last month but are now paid correctly. Flag as: 'RESOLVED: Aetna 99214 now paying at contracted rate.'
> 4. **New denial patterns:** Denial codes appearing this month that didn't appear last month. Flag as: 'NEW PATTERN: CO-16 denials from BCBS appeared for the first time in February (3 claims, $540).'
> 5. **Denial rate changes:** Payer-level denial rate increasing or decreasing month over month. Flag as: 'Aetna denial rate increased from 8% to 14% this month.'
> 6. **Revenue gap trajectory:** Running total of identified underpayments and projected annual gap, updated monthly.
>
> **AI narrative generation:**
> After computing trends, call Claude to generate a plain-English trend summary: 'February analysis for Lakeside Internal Medicine: Compared to January, Aetna's underpayment pattern on 99214 has worsened ($13 → $22 per claim). Two new CO-16 denials appeared from BCBS that weren't present last month — this may indicate a documentation requirement change. Overall revenue gap is trending upward: $1,847/month in January to $2,340/month in February. Annualized gap: $28,080. Priority action: appeal the 4 Aetna 99214 underpayments from February ($88 total) and investigate the new BCBS CO-16 pattern.'
>
> **Frontend:**
> Add a 'Trends' tab to the subscription dashboard showing:
> - Timeline chart: monthly revenue gap by payer (recharts line chart)
> - Trend alerts: list of new, worsening, and resolved items with color coding (red for new/worsening, green for resolved)
> - AI trend narrative at the top
> - Per-payer breakdown expandable sections
>
> **In the monthly report PDF:**
> Add a new section (Section 3, after Executive Summary): 'Changes Since Last Month' — listing all trend flags with the AI narrative. This replaces the static contract integrity table as the lead finding for months 2+. Month 1 (the audit) has no trends yet, so it shows the standard audit report format."

**Verify:** Upload 835 data for two consecutive months for a test subscription. Confirm trend detection fires correctly, AI narrative generates, and the trends tab shows the timeline and alerts.

---

### Instruction 4: One-Click Appeal Drafting from Findings

**The problem:** The appeal letter generator exists but isn't connected to specific findings from the audit or monthly reports. When a practice sees a denial worth appealing, they should be able to generate the appeal letter with one click.

**The solution:** Wire the existing appeal generator to each denial finding in the report.

> "Connect the existing appeal letter generator to specific denial findings in audit reports and monthly reports.
>
> **Backend:**
>
> Update the existing appeal letter generation endpoint (or create `POST /api/provider/generate-appeal`) to accept:
> - claim_id (from the 835 data)
> - denial_code (e.g., CO-16, OA-18)
> - cpt_code
> - billed_amount
> - payer_name
> - date_of_service
> - practice_name
> - practice_address (from subscription or audit data)
> - provider_name and NPI (from 835 NM1 segments)
> - patient_name (from 835 NM1*QC segment — first name, last name only)
>
> The endpoint should:
> 1. Look up the specific CMS guidelines relevant to the denial code and CPT code
> 2. Generate a formal appeal letter using Claude with this prompt approach:
>    - Letter addressed to the payer's appeals department
>    - Reference: claim ID, patient name, date of service, CPT code
>    - State the denial reason and why it should be overturned
>    - Cite specific CMS guidelines, NCCI rules, or payer contract terms as applicable
>    - Request reprocessing and payment at the contracted rate
>    - Professional, firm tone — not adversarial
> 3. Return the letter as both HTML (for preview) and PDF (for download/print)
>
> **Frontend — in ProviderAuditReport.jsx and subscription report views:**
> - Next to each denied claim in the Denial Pattern Analysis section, add a 'Draft Appeal' button
> - Clicking it calls the generate-appeal endpoint with that claim's details
> - Shows the generated letter in a modal with 'Edit,' 'Copy,' 'Download PDF,' and 'Print' buttons
> - The practice can edit the letter text before downloading or printing
>
> **Frontend — in subscription dashboard Trends view:**
> - Next to each denial trend alert, add 'Draft Appeals for All [N] Denials' button
> - Generates appeal letters for all denials in that pattern (batch generation)
> - Shows them in a list view where the practice can review, edit, and download each one
>
> **Track appeal outcomes (simple, for now):**
> After generating an appeal, create a record in a new Supabase table `provider_appeals`:
> - id (UUID)
> - subscription_id or audit_id (UUID)
> - claim_id (TEXT)
> - payer_name (TEXT)
> - denial_code (TEXT)
> - cpt_code (TEXT)
> - amount (DECIMAL)
> - appeal_generated_at (TIMESTAMPTZ)
> - status (TEXT — drafted, sent, won, lost, pending — default 'drafted')
> - outcome_amount (DECIMAL, nullable)
> - notes (TEXT, nullable)
>
> In the subscription dashboard, add an 'Appeals' tab showing all generated appeals with their status. The practice (or admin) can update status as appeals are resolved. This tracking data becomes valuable over time — appeal success rates by denial code and payer.
>
> Print the migration SQL for both provider_subscriptions and provider_appeals so I can run them together in Supabase."

**Verify:** View a completed audit report, click 'Draft Appeal' on a denied claim, confirm the letter generates with correct claim details and CMS references, download the PDF, and confirm the appeal is tracked in the appeals table.

---

## Implementation Sequence

| Phase | Instruction | Days | What it enables |
|---|---|---|---|
| **Conversion** | 1 (Audit → Subscription) | 3-4 days | Practice converts from audit to paid monitoring |
| **Ingestion** | 2 (Inbound email 835) | 2-3 days | Practice forwards files instead of logging in |
| **Intelligence** | 3 (Trend comparison) | 2-3 days | Subscription delivers more value than audit |
| **Action** | 4 (Appeal drafting from findings) | 2 days | Findings lead directly to revenue recovery |

**Total: ~10-12 days Claude Code work**

Build in this order. Instruction 1 is the critical path — without it, there's no conversion mechanism from audit to subscription. Instructions 2-4 can be built in parallel or sequentially after that.

---

## Manual Operations (Before Automation)

Until there are enough practices to justify full automation:

- **835 collection:** Fred follows up with practices monthly via email to request files. The inbound email address (Instruction 2) handles processing once received.
- **Report delivery:** Admin dashboard triggers analysis and generates reports. Fred reviews before delivery.
- **Appeal tracking:** Fred updates appeal statuses based on practice feedback. Outcomes data builds over time.
- **Conversion:** Fred clicks 'Convert to Subscription' in admin dashboard after practice agrees.

This manual-first approach validates the workflow before investing in full automation.

---

## Pricing

| Tier | Price | What they get |
|---|---|---|
| Parity Audit | Free | One-time report, one month of data, concrete findings |
| Monthly Monitoring | $300/month or $3,000/year | Monthly analysis, trend tracking, denial alerts, appeal drafting |
| Full Intelligence (future) | $500/month | Everything above + coding optimization, benchmark comparisons, payer negotiation intelligence |

The $300/month pays for itself if it catches one $30+ underpayment per month. Industry data shows 3-4% revenue leakage — a practice billing $400K annually is losing $12,000-16,000.

---

## Success Metrics

After 5+ active subscriptions, measure:
- Monthly underpayments found per practice (dollar amount)
- Monthly denials identified with appeal recommendations
- Appeal success rate by denial code and payer
- Subscription retention (month-over-month)
- Time from 835 receipt to report delivery
- Practice engagement (do they read the reports? draft appeals?)
- Revenue recovered as a multiple of subscription cost (target: 3x+)

---

## What Comes Later (Requires Scale)

These features depend on having 20+ active practices generating monthly data:

- **Coding pattern analysis:** Compare practice's E&M distribution to specialty peers. Identify undercoding.
- **Payer benchmark comparisons:** "Your Aetna rate for 99214 is 28th percentile for your specialty in your metro."
- **Negotiation intelligence:** Data-backed rate comparison for contract renewal conversations.
- **Credentialing gap detection:** Identify billing anomalies suggesting credentialing issues.
- **Pre-submission claim scrubbing:** Predict denial risk before claims are submitted.
- **Clearinghouse API integration:** Auto-pull 835s monthly without practice involvement.
- **Automated monthly email reports:** Scheduled analysis and delivery without admin trigger.
