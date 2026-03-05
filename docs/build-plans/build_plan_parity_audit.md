# Parity Audit — Complete Build Plan
**Product:** Free 30-day proof-of-value billing audit for physician practices
**Route:** civicscale.ai/provider/audit
**Status:** Not yet built
**Last updated:** March 5, 2026
**Estimated effort:** 10-13 days Claude Code + legal + outreach

---

## Concept

Practice provides one month of 835 remittance files + payer fee schedules → CivicScale runs full analysis → delivers branded PDF audit report within 5-7 business days → if findings are significant, conversion conversation about ongoing monitoring subscription ($300/month).

Zero cost. Zero commitment. Zero integration with their EHR or PM system. The 835 files and fee schedules are all we need.

---

## Prerequisites (Non-Code — Do First)

### P1: BAA Template — BLOCKER
- Template drafted (civicscale_baa_template.docx)
- **Must be reviewed by a healthcare attorney before first use**
- Budget: $500-1,500 for attorney review
- Timeline: 1-2 weeks
- No practice will send real 835 data without a signed BAA

### P2: Sample 835 File
- Ask Joe (or first pilot practice) for a de-identified sample 835 from their clearinghouse
- Test the existing parser against it BEFORE committing to an audit timeline
- If parser fails, fix it before building the rest of the audit infrastructure

### P3: Sample Fee Schedule
- Ask the same practice: "Do you know if your payer contracts are percentage-of-Medicare or custom fee schedules?"
- Get a sample fee schedule in whatever format they have (PDF, Excel, screenshot — anything)
- This determines which ingestion method to prioritize

---

## Build Sequence — 7 Claude Code Instructions

### Instruction 1: Multi-File 835 Upload (Day 1)

> "Update the Provider 835 upload to accept: (1) single .835 or .edi files, (2) multiple files selected at once via file picker, (3) .zip files containing multiple 835s — auto-extract and parse each file individually. Add clear instructions on the upload page explaining where to find 835 files:
> 
> - **From your clearinghouse:** Log into Availity, Office Ally, Change Healthcare, or your clearinghouse portal. Look for 'ERA Downloads' or '835 Downloads.' Download files for the month you want audited.
> - **From your PM system:** Some systems (Athena, Kareo, eClinicalWorks) can export raw 835 files. Check your reports or billing section.
> - **From your billing company:** If you outsource billing, ask your billing company to export the raw 835 remittance files for the month you want audited.
> 
> Include a 'Need help finding your files?' expandable section with these instructions. Show upload progress for each file with success/error status per file."

**Verify:** Upload a single .835 file, upload 3 files at once, upload a .zip containing 2 .835 files. All parse correctly.

---

### Instruction 2: Multi-Input Fee Schedule Ingestion (Days 2-3)

> "Build a multi-input fee schedule ingestion system for Parity Provider, similar to how Parity Health accepts bills via PDF, paste, and photo. Create these input methods:
> 
> **Method 1: Excel/CSV upload (exists — keep as-is)**
> Template with columns: CPT Code, Contracted Rate, Payer Name. Add a 'Download Template' button.
> 
> **Method 2: PDF contract extraction (new)**
> Practice uploads their payer contract PDF. Claude vision scans the document, identifies pages containing fee schedule tables, and extracts CPT code → rate pairs. Show extracted rates on a confirmation screen for the practice to review and correct.
> Endpoint: `POST /api/provider/extract-fee-schedule-pdf`
> 
> **Method 3: Percentage-of-Medicare (new — very common)**
> Many contracts say '115% of Medicare PFS' rather than listing individual rates. Add an input option: 'My contract pays a percentage of Medicare.' Practice enters: Payer name, percentage (e.g., 115%), and effective date. System calculates contracted rates by multiplying our existing 841K CMS PFS rates by that percentage. No extraction needed.
> 
> **Method 4: Paste from portal or email (new)**
> Practice copies fee schedule text from their payer portal or email. Claude extracts CPT → rate pairs from unstructured text.
> Endpoint: `POST /api/provider/extract-fee-schedule-text`
> 
> **Method 5: Photo/screenshot (new)**
> Practice photographs a printed fee schedule or screenshots their PM system's rate screen. Claude vision extracts rates.
> Endpoint: `POST /api/provider/extract-fee-schedule-image`
> 
> **All methods converge on the same confirmation screen** showing: Payer name, effective date, and editable table of CPT Code | Contracted Rate. User can edit, add rows, or delete rows before saving.
> 
> Add help text: 'Where to find your fee schedules' with instructions for each scenario."

**Verify:** Upload an Excel template, enter a percentage-of-Medicare, paste some text with rates, upload a screenshot. All produce the same confirmation screen with extracted rates.

---

### Instruction 3: Multi-Payer Batch Processing (Days 4-5)

> "Update the Provider analysis flow to handle multiple payers in one audit. The practice will upload fee schedules for 2-3 payers (each via any input method) and multiple 835 files (one or more per payer). The system should:
> 
> (a) Let the user add multiple payers, uploading a fee schedule for each one.
> (b) Let the user upload multiple 835 files. Auto-detect which payer each 835 belongs to by reading the N1*PR (payer name) segment from the 835 header. If auto-detection fails, let user assign manually.
> (c) Run the contract integrity analysis on each 835 against its matched fee schedule.
> (d) Run denial intelligence on each 835.
> (e) Store all results under a single audit ID so they can be consolidated into one report.
> 
> Create a Supabase table `provider_audits`:
> - id (UUID, primary key)
> - practice_name (TEXT)
> - practice_specialty (TEXT)
> - num_providers (INTEGER)
> - billing_company (TEXT, nullable)
> - contact_email (TEXT)
> - payer_list (JSONB — array of {payer_name, fee_schedule_method, fee_schedule_data})
> - analysis_ids (JSONB — array of provider_analyses IDs)
> - status (TEXT — submitted, processing, review, delivered)
> - admin_notes (TEXT, nullable)
> - created_at (TIMESTAMPTZ)
> - delivered_at (TIMESTAMPTZ, nullable)
> - follow_up_sent (BOOLEAN, default false)
> 
> Enable RLS: service_role full access, authenticated users can read own audits by contact_email or user_id.
> 
> Cross-payer summary: After all analyses complete, generate a consolidated view: 'Aetna underpaid $4,200 this month across 12 line items. UHC underpaid $1,800 across 6 line items. BCBS was within contract on all lines.'"

**Verify:** Create an audit with 2 payers, upload fee schedules for each, upload 835s for each, run analysis, confirm results are grouped by payer under one audit ID.

---

### Instruction 4: Audit Report PDF Generation (Days 6-8)

> "Create a branded PDF audit report for Parity Provider. New endpoint: `POST /api/provider/audit-report` that takes an audit_id and generates a professional PDF.
> 
> **Report sections:**
> 
> 1. **Cover page** — CivicScale Parity Audit header, practice name, date range analyzed, report date. Brand colors: teal #0D9488, navy #1E293B.
> 
> 2. **Executive summary** — AI-generated 3-4 sentences using Claude: total underpayments found across all payers, top denial pattern identified, estimated annualized revenue gap, and one-sentence recommendation.
> 
> 3. **Contract integrity findings** — Table sorted by dollar impact: CPT Code | Description | Expected Rate | Paid Amount | Difference | Payer | Date of Service. Group by payer with subtotals. Highlight any line where difference exceeds 10% of expected rate.
> 
> 4. **Denial pattern analysis** — Top 5 denial codes by frequency and dollar value. For each: denial code, count, total dollars, AI plain-language explanation of what the code means and recommended action (resubmit, appeal, write off).
> 
> 5. **Revenue gap estimate** — Monthly underpayment total × 12 = annualized projection. Break down by payer. Show both 'identified underpayments' (specific line items) and 'estimated additional recovery from denial appeals' (based on appeal success rates by denial type).
> 
> 6. **Billing contractor assessment** (if determinable from 835 data) — Clean claim rate estimate, denial follow-up patterns, resubmission timeliness.
> 
> 7. **Recommended actions** — AI-generated prioritized list: which underpayments to appeal first (highest dollar, most clear-cut), which denial patterns to address with the payer, which contract terms to review at next renegotiation.
> 
> 8. **Methodology** — One paragraph: 'CivicScale analyzed [N] remittance transactions across [N] payers for the period [dates]. Each payment line was compared against contracted rates provided by the practice. Denial codes were classified and scored for appeal worthiness. Revenue gaps were estimated by annualizing one month of findings. This analysis is informational and does not constitute legal or financial advice.'
> 
> 9. **Next steps** — Brief paragraph: 'This report represents one month of data. Systematic underpayment and denial patterns often vary month to month. CivicScale offers ongoing monitoring that automatically scans every remittance against your contracted rates and alerts you when new underpayments or denial patterns are detected. Contact fred@civicscale.ai to discuss.'
> 
> Use weasyprint or reportlab for PDF generation. Store generated PDF in Supabase storage or filesystem with a download URL. Also create a frontend component `ProviderAuditReport.jsx` that renders the report in-browser with a 'Download PDF' button."

**Verify:** Generate a report from a completed multi-payer audit. Confirm all 9 sections render correctly in PDF. Download and confirm formatting.

---

### Instruction 5: Audit Landing Page and Onboarding Wizard (Days 9-11)

> "Create a dedicated audit landing page and step-by-step onboarding flow at `/provider/audit`.
> 
> **Landing page:**
> Headline: 'Parity Audit: Find out what your payers owe you.'
> Subheadline: 'Free. No commitment. No integration required.'
> Value proposition section:
> - We check every payment line against your contracted rates
> - We identify denial patterns costing you money
> - We estimate your annualized revenue gap
> - Delivered within 5-7 business days
> 'Start Your Free Audit →' button.
> 
> **Onboarding wizard (5 steps):**
> 
> **Step 1 — Practice Profile**
> Fields: Practice name, specialty (dropdown), number of providers, billing company name (optional — 'Leave blank if you handle billing in-house'), contact email, contact phone (optional).
> 
> **Step 2 — Add Payers**
> 'Add a payer' button. For each payer:
> - Payer name (dropdown with common payers: Aetna, BCBS, Cigna, Humana, UHC, Medicare, Medicaid, Other with text input)
> - Fee schedule input method selector: Excel upload | Percentage of Medicare | Paste text | Upload PDF | Upload screenshot
> - Fee schedule input based on selected method
> - Confirmation screen showing extracted rates
> - 'Add another payer' button (up to 5 payers)
> 
> **Step 3 — Upload 835 Files**
> Drag and drop area accepting multiple .835, .edi, or .zip files.
> After upload, show list of files with auto-detected payer for each (from N1*PR segment).
> Let user correct payer assignment if auto-detection is wrong.
> Show: '[filename] — detected payer: Aetna ✓' or '[filename] — payer not detected [Select payer ▾]'
> 
> **Step 4 — Review and Submit**
> Summary: practice name, specialty, number of providers.
> Payers: list with number of rate entries per payer.
> 835 files: list with payer assignment for each.
> Consent checkbox: 'I authorize CivicScale to analyze this data under the terms of our Business Associate Agreement. I consent to anonymized, de-identified data being used for benchmark improvement.' (default checked)
> 'Submit Audit' button.
> 
> **Step 5 — Confirmation**
> 'Your Parity Audit has been submitted.'
> 'Audit ID: [id]'
> 'You will receive your report at [email] within 5-7 business days.'
> 'Questions? Contact fred@civicscale.ai'
> 
> On submission, send confirmation email via Resend to the practice contact email AND to fred@civicscale.ai with full audit details (practice name, specialty, payers, number of files, audit ID)."

**Verify:** Walk through the entire wizard with test data. Confirm all 5 steps work, confirmation email arrives at both addresses.

---

### Instruction 6: Admin Audit Dashboard (Day 12)

> "Add a Provider Audit admin view at `/provider/admin/audits`, protected by ADMIN_USER_ID (same pattern as Signal admin dashboard — check Bearer token or ?secret= query parameter).
> 
> **Dashboard shows:**
> - Table of all audits: Practice Name | Specialty | Payers | # Files | Status | Submitted | Actions
> - Filter tabs: All | Submitted | Processing | Review | Delivered
> - Click on audit row to expand details
> 
> **Actions per audit:**
> - 'Run Analysis' button — triggers the batch analysis for all payer/835 combinations in this audit. Shows progress. Updates status to 'processing' then 'review' when complete.
> - 'View Results' — shows the analysis results in-browser (same as current Provider dashboard but consolidated across payers)
> - 'Generate Report' — creates the audit PDF. Shows preview.
> - 'Add Review Notes' — text area for Fred to add notes before delivery (e.g., 'Verified CO-45 findings against fee schedule. Claim 3 may be a legitimate carve-out — flagged in recommended actions.')
> - 'Deliver Report' — updates status to 'delivered', sends delivery email to practice with report link/PDF, records delivered_at timestamp.
> - 'Send Follow-up' — manually triggers the follow-up email (or auto-triggers 3 days after delivery)
> 
> This gives Fred a manual review step before every delivery. No audit report goes to a practice without Fred reviewing it first."

**Verify:** Submit a test audit via the wizard, open admin dashboard, run analysis, generate report, add notes, deliver. Confirm delivery email arrives.

---

### Instruction 7: Email Templates (Day 13)

> "Set up three email templates via Resend for the Provider audit flow:
> 
> **Email 1: Submission Confirmation**
> Sent immediately when audit is submitted.
> To: practice contact email
> From: notifications@civicscale.ai
> Subject: 'Your Parity Audit has been submitted — [Practice Name]'
> Body: 'Thank you for submitting your billing data for analysis. Your Parity Audit Report will be delivered to this email address within 5-7 business days. Audit ID: [id]. Date range: [dates from 835 files]. Payers analyzed: [payer list]. If you have questions, reply to this email or contact fred@civicscale.ai.'
> 
> **Email 2: Report Delivery**
> Sent when Fred clicks 'Deliver Report' in admin dashboard.
> To: practice contact email
> From: notifications@civicscale.ai
> Subject: 'Your Parity Audit Report is ready — [Practice Name]'
> Body: 'Your Parity Audit Report is ready. [View Report Online →] [Download PDF →]. Key finding: [executive summary first sentence from the report]. We analyzed [N] transactions across [N] payers and identified [total underpayment amount] in potential recoverable revenue. [If Fred added review notes, include a Notes from our review section]. Want to discuss the findings? Reply to this email or schedule a call at fred@civicscale.ai.'
> 
> **Email 3: Follow-up (3 days after delivery)**
> Sent automatically via cron endpoint, or manually by Fred from admin dashboard.
> To: practice contact email
> From: notifications@civicscale.ai
> Subject: 'Following up on your Parity Audit — [Practice Name]'
> Body: 'We delivered your Parity Audit Report [3 days ago]. We identified [dollar amount] in potential annual recoverable revenue across [N] payers. Have you had a chance to review the findings? If you would like to discuss: which underpayments to appeal first, how to address the denial patterns we identified, or what ongoing monitoring would look like for your practice — reply to this email or contact fred@civicscale.ai. Ongoing monitoring scans every remittance automatically and alerts you when new underpayments or denial patterns emerge. It costs $300/month and typically pays for itself within the first month.'
> 
> Also send admin notification to fred@civicscale.ai on audit submission (with details) and follow-up sent (for tracking)."

**Verify:** Trigger all three emails for a test audit. Confirm content, formatting, and links work.

---

## Implementation Order Summary

| Phase | Instructions | Days | What it enables |
|---|---|---|---|
| **Data ingestion** | 1 (835 upload) + 2 (fee schedules) + 3 (batch processing) | 5 days | Practice can submit data and get results |
| **Report & delivery** | 4 (PDF report) + 7 (emails) | 3-4 days | Professional deliverable with email notifications |
| **Onboarding & admin** | 5 (wizard) + 6 (admin dashboard) | 3-4 days | Complete self-service flow with admin review |

Build in this order. After Phase 1 (data ingestion), you can run a manual audit — upload files yourself, run analysis, manually write up findings. This lets you test with a practice while the report and onboarding are still being built.

---

## Manual First Audit (Before Full Infrastructure)

Before the onboarding flow is built, you can test the core engine:

1. Sign BAA with pilot practice
2. Receive 835 files and fee schedule data via email
3. Upload 835s through the existing Provider upload
4. Enter fee schedule via whichever method they provide
5. Run analysis
6. Review results manually
7. Write up findings in a document (branded PDF not built yet)
8. Deliver via email
9. Use feedback to refine before building the automated flow

This validates the engine before investing in the full infrastructure.

---

## Non-Code Tasks

| Task | Owner | Status | Blocks |
|---|---|---|---|
| BAA attorney review | Fred + attorney | Template ready, needs review | First audit |
| Get sample 835 from practice | Fred (ask Joe) | Not started | Parser testing |
| Test parser against real 835 | Claude Code | Waiting on sample | Audit accuracy |
| Get sample fee schedule | Fred (ask Joe) | Not started | Fee schedule testing |
| Set up Google Workspace (fred@civicscale.ai) | Fred | Not started | Professional delivery emails |
| Manual review of first 3-5 reports | Fred | Future | Every delivery until billing SME hired |
| Send response to Joe | Fred | Draft ready | Relationship + pilot ask |
| Hire Head of Clinical Accuracy | Fred | Future | Expert report review |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| BAA delays | Medium | BLOCKER | Start immediately, use template |
| 835 parser fails on real data | Medium | HIGH | Get sample early, fix incrementally |
| Fee schedule extraction inaccurate | Medium | MEDIUM | Confirmation screen lets user correct |
| AI flags legitimate adjustments as underpayments | High (first few) | HIGH | Manual review, document edge cases |
| Practice doesn't have clean fee schedules | High | MEDIUM | Percentage-of-Medicare method covers many cases |
| Practice takes weeks to provide data | High | LOW | Set expectations, walk them through it |
| Findings are trivial ($500 or less) | Medium | MEDIUM | Reframe as validation of clean operations |

---

## Conversion Path

If audit finds $10,000+ annualized recoverable revenue → subscription conversation is easy:
- Ongoing monitoring: $300/month ($3,600/year)
- ROI: if $10K found in one month, $3,600/year monitoring is 3x+ return
- Features: automatic monthly 835 scan, underpayment alerts, denial trend tracking, quarterly AI narrative

---

## Data Value to CivicScale

Every audit generates:
- Real 835 data that tests and improves the parser
- Contracted rate data from real practices (feeds benchmark observations with consent)
- Denial pattern data across real payers and specialties
- Validation evidence for sales narrative: "$X found across Y practices"
- Expert review corrections that improve AI accuracy

The first 5 audits are worth more in data and validation than any subscription revenue.
