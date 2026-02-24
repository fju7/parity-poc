# Parity Health — Bill Analysis Tool
## POC Build (Phase 0)

### Brand Architecture

- **CivicScale** — parent infrastructure company (civicscale.ai). Builds the benchmark intelligence platform.
- **Parity** — the benchmark intelligence engine that powers all verticals.
- **Parity Health** — the healthcare product (first vertical). This codebase.
- Future verticals: **Parity Property**, **Parity Insurance**, **Parity Finance**.

In the UI the product is always referred to as "Parity Health". The header shows "Parity Health" with a smaller "by CivicScale" subtitle. The footer references CivicScale benchmark infrastructure.

### What This Project Is

Parity Health is a browser-based medical bill analysis tool that compares itemized hospital bills against CMS Medicare benchmark rates and flags potentially anomalous line items. It is the Phase 0 proof of concept for a larger financial advocacy platform.

**The single most important architectural constraint:** The patient's PDF document must never be uploaded to any server. All document processing happens in the browser (client-side). Only CPT codes and a zip code are ever sent to the backend API. This is a non-negotiable privacy-by-architecture design.

---

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| PDF Parsing | PDF.js (Mozilla, browser-side) |
| Backend API | Python 3.11 + FastAPI |
| Data Processing | Python + Pandas |
| Rate Database | CMS Medicare PFS + OPPS (CSV flat files at POC stage) |
| Frontend Hosting | Vercel |
| Backend Hosting | Render.com |
| Version Control | GitHub |

---

### Directory Structure

```
parity-poc/
├── CLAUDE.md                  ← this file
├── README.md
├── frontend/                  ← React app (Vite)
│   ├── src/
│   │   ├── modules/
│   │   │   ├── extractBillData.js     ← PDF extraction (Task 3)
│   │   │   └── scoreAnomalies.js      ← Anomaly scoring (Task 5)
│   │   ├── components/                ← React UI components (Task 6)
│   │   ├── App.jsx                    ← Main app with 3-screen state
│   │   └── main.jsx
│   ├── public/
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── backend/                   ← FastAPI Python API
│   ├── main.py                        ← FastAPI app entry point
│   ├── routers/
│   │   └── benchmark.py               ← /api/benchmark endpoint (Task 4)
│   ├── data/
│   │   ├── pfs_rates.csv              ← Processed CMS PFS output (Task 2)
│   │   ├── opps_rates.csv             ← Processed CMS OPPS output (Task 2)
│   │   └── zip_locality.csv           ← ZIP to CMS locality crosswalk (Task 2)
│   ├── scripts/
│   │   ├── process_pfs.py             ← CMS PFS processor (Task 2)
│   │   └── process_opps.py            ← CMS OPPS processor (Task 2)
│   ├── requirements.txt
│   └── .env.example
└── data/
    ├── cms-pfs/               ← Raw CMS PFS downloads (not committed to git)
    │   ├── cy2026-carrier-files-nonqp-updated-12-29-2025.zip  ← PRIMARY: pre-calc rates
    │   ├── ZIP5_APR2026.xlsx  ← ZIP-to-locality crosswalk, Q2 2026
    │   └── RVU26A.zip         ← BACKUP: raw RVUs + GPCI file inside
    ├── cms-opps/              ← Raw CMS OPPS downloads (not committed to git)
    └── test-bills/            ← Real test bills (NEVER committed to git)
```

---

### Critical Rules (Never Violate These)

1. **No PHI to server.** The `/api/benchmark` endpoint accepts only: `zipCode` (string), `lineItems` array of `{code, codeType, billedAmount}`. No names, dates of birth, diagnosis codes, insurance IDs, or provider addresses. Ever.

2. **No test bills in git.** The `data/test-bills/` directory must be in `.gitignore`. Real medical bills must never be committed to version control.

3. **Raw CMS files not committed.** The `data/cms-pfs/` and `data/cms-opps/` directories contain large CMS downloads that must also be in `.gitignore`. Only the processed output CSVs go in `backend/data/`.

4. **Brand colors.** The UI must use: primary navy `#1B3A5C`, accent teal `#0D7377`, clean white backgrounds, Arial font family. This is investor-demo quality, not a prototype.

5. **Tailwind only.** Do not write custom CSS. Use Tailwind utility classes throughout.

---

### The Eight Build Tasks (Work Through These in Order)

#### TASK 1 — Project Setup (~1 hour)
Initialize the Vite React frontend and FastAPI backend. Set up GitHub. Deploy empty shells to Vercel and Render to confirm the deployment pipeline before writing any real code.

**Done when:** `http://localhost:5173` shows a React page. `http://localhost:8000` returns `{"status": "ok"}` from FastAPI.

---

#### TASK 2 — CMS Data Processor (~3 hours)
Write `backend/scripts/process_pfs.py` and `backend/scripts/process_opps.py`. These scripts read raw CMS downloads from `data/cms-pfs/` and `data/cms-opps/` and produce clean lookup CSVs in `backend/data/`.

**Source files (already downloaded, saved in `data/cms-pfs/`):**

- `cy2026-carrier-files-nonqp-updated-12-29-2025.zip` — **(PRIMARY SOURCE — use this)** The pre-calculated 2026 Physician Fee Schedule amounts for all CPT codes in all carrier/localities. Downloaded from CMS Carrier Specific Files page. 11MB. These are final dollar amounts with GPCI math already applied — no calculation needed. Contains both nonfacility and facility amounts. Updated 12/29/2025.
  - Download URL: `https://www.cms.gov/files/zip/cy2026-carrier-files-nonqp-updated-12-29-2025.zip`

- `ZIP5_APR2026.xlsx` — the ZIP-to-locality crosswalk file (42,957 rows, Q2 2026). Columns: `STATE`, `ZIP CODE`, `CARRIER`, `LOCALITY`, `RURAL IND`, `LAB CB LOCALITY`, `RURAL IND2`, `PLUS 4 FLAG`, `PART B DRUG INDICATOR`, `YEAR/QTR`. The key columns for lookup are `ZIP CODE`, `CARRIER`, and `LOCALITY`.

- `RVU26A.zip` — **(BACKUP/REFERENCE ONLY)** The raw RVU file with relative value units. The ZIP contains two files: the RVU data file (use the `-nonQP` variant) and a separate GPCI file with geographic adjustment factors. Only needed if the Carrier Files approach fails. If used, apply formula: `[(Work RVU × Work GPCI) + (Nonfacility PE RVU × PE GPCI) + (MP RVU × MP GPCI)] × $33.4009`

**Output files to produce in `backend/data/`:**

`pfs_rates.csv` columns: `cpt_code, carrier, locality_code, nonfacility_amount, facility_amount` — produced by processing the Carrier Files ZIP
`opps_rates.csv` columns: `apc_code, payment_rate, description`
`zip_locality.csv` columns: `zip_code, carrier, locality_code, state` — produced by processing `ZIP5_APR2026.xlsx`

**ZIP-to-locality lookup logic:** Given a provider's 5-digit zip code, look it up in `zip_locality.csv` to get the `carrier` and `locality_code`. Then look up `(carrier, locality_code)` in `pfs_rates.csv` to get the benchmark rate. Use `nonfacility_amount` for physician office visits; use `facility_amount` for hospital-billed services.

**Done when:** CPT code `99213` in `pfs_rates.csv` shows the expected rate for at least two different locality codes, verified against CMS published tables.

---

#### TASK 3 — PDF Extraction Module (~3 hours)
Write `frontend/src/modules/extractBillData.js`. This module uses PDF.js to parse a PDF File object entirely in the browser and returns a structured object. No server call at this step.

**Return shape:**
```javascript
{
  provider: { name: string, zip: string, npi: string|null },
  serviceDate: string,
  lineItems: [
    { code: string, codeType: "CPT"|"REVENUE"|"UNKNOWN", description: string, billedAmount: number }
  ]
}
```

CPT code pattern: 5-digit numeric (`\b\d{5}\b`), typically following keywords like "CPT", "Procedure", or a service description.
Revenue code pattern: 4-digit numeric (`\b\d{4}\b`) on facility bills.
Dollar amounts: match `$X,XXX.XX` and similar currency patterns.

**Done when:** `extractBillData(file)` called on a real medical bill returns at least one correctly identified CPT code and a matching dollar amount.

---

#### TASK 4 — Benchmark API (~3 hours)
Write `backend/routers/benchmark.py`. A single POST endpoint at `/api/benchmark`.

**Request body:**
```json
{
  "zipCode": "33701",
  "lineItems": [
    { "code": "99213", "codeType": "CPT", "billedAmount": 250.00 }
  ]
}
```

**Response:**
```json
{
  "lineItems": [
    {
      "code": "99213",
      "codeType": "CPT",
      "billedAmount": 250.00,
      "benchmarkRate": 78.05,
      "benchmarkSource": "CMS_PFS_2026",
      "localityCode": "01"
    }
  ]
}
```

- Items not found in either rate file: return `benchmarkRate: null, benchmarkSource: "NOT_FOUND"`. Not an error.
- Load CSVs into Pandas DataFrames on app startup (not per-request).
- Add CORS middleware: allow `http://localhost:5173` and the Vercel production domain.
- Target response time: under 500ms for 50 line items.

**Done when:** `curl -X POST http://localhost:8000/api/benchmark` with CPT 99213 and zip 33701 returns the correct geographically adjusted Medicare rate.

---

#### TASK 5 — Anomaly Scoring Engine (~2 hours)
Write `frontend/src/modules/scoreAnomalies.js`. Takes line items from extraction + benchmark rates from API and computes anomaly scores.

**Anomaly score** = `billedAmount / benchmarkRate`. Score of 1.0 = matches benchmark. Score of 2.5 = billed at 2.5× benchmark.

**Flag a line item if any of:**
- Anomaly score > 2.0 (configurable, default 2.0)
- Same CPT code appears more than once on same service date (duplicate billing)
- A group of CPT codes matches a known CMS bundled code set and appears as separate charges (unbundling)

**Return:** enriched line items with `anomalyScore`, `flagged` (boolean), `flagReason` (string), `estimatedDiscrepancy` (billedAmount - benchmarkRate). Plus summary: `{ totalBilled, totalBenchmark, totalPotentialDiscrepancy, flaggedItemCount }`.

**Done when:** Test with 3 synthetic items — one at 1.5× (not flagged), one at 3.0× (flagged), one duplicate CPT (flagged) — produces correct flags and correct summary totals.

---

#### TASK 6 — User Interface (~4 hours)
Build the complete React UI in `frontend/src/`. Three views managed by React `useState` (no router needed):

**Upload View:**
- Parity Health logo (text wordmark, navy, bold, large)
- Drag-and-drop zone (large, teal border, accepts PDF)
- Three-point privacy explanation: "Your document never leaves your device", "Only procedure codes are analyzed in the cloud", "No names, dates, or diagnoses are ever transmitted"
- Disclaimer: "Parity Health provides benchmark comparisons only. This is not legal advice. Consult a billing specialist or attorney before taking action."

**Processing View:**
- Animated progress indicator (Tailwind animate-pulse or similar)
- Sequential status messages: "Reading your document...", "Looking up benchmark rates...", "Analyzing charges..."

**Report View:**
- Bill summary header: provider name, service date, total billed, total benchmark, total discrepancy
- Anomaly meter: visual bar showing ratio of flagged to total charges
- Line items table: all items, flagged ones highlighted in amber/red, with columns: Code, Description, Billed, Benchmark, Anomaly Score, Flag Reason
- Expandable detail panel per flagged item showing benchmark source citation
- Total potential discrepancy callout box (prominent, navy background, white text)
- Next steps section: "Contact the billing department" (with guidance text) + "Connect with a billing specialist" (placeholder button, teal)

Colors: primary `#1B3A5C`, accent `#0D7377`, flags `#F59E0B` (amber) or `#EF4444` (red) for scores >3×. Font: Arial throughout.

**Done when:** The UI renders all three views correctly with mock data. Looks professional enough to show an investor without apology.

---

#### TASK 7 — Integration (~2 hours)
Wire Tasks 3, 4, 5, and 6 together in `App.jsx`.

**Flow:** File drop → `extractBillData(file)` → POST to `/api/benchmark` → `scoreAnomalies(lineItems, benchmarkResponse)` → update state → render Report view.

**Error states to handle:**
- Empty extraction (no CPT codes found): show message "This appears to be a summary bill. Please upload an itemized bill showing individual procedure codes."
- API timeout (>10s): retry once, then show "Rate lookup is temporarily unavailable. Please try again in a moment."
- All-null benchmarks: show partial report with note "X of Y procedure codes could not be benchmarked against current CMS data."

**Done when:** Dropping a real medical bill produces a complete report with line items, anomaly scores, and a discrepancy estimate.

---

#### TASK 8 — Demo Polish and Deployment (~3 hours)
Final investor-demo finishing work:

1. **Sample bill mode:** Add a "Try a Sample Bill" button on the Upload view. It loads a pre-built JavaScript object (no PDF needed) representing a fictional but realistic hospital bill with 8 line items, 3 of which are flagged. This is the primary investor demo path.

2. **Report download:** Add "Download Report" button on Report view. Use browser `window.print()` with a print-specific CSS class that renders a clean, single-column report with: Parity Health logo, date, disclaimer, all line items, flagged items highlighted, benchmark source citations. Add a `@media print` CSS block.

3. **Footer:** Add to every view: "Parity Health is powered by CivicScale benchmark infrastructure. Benchmark comparisons use publicly available CMS Medicare data. Not legal advice. © CivicScale 2026."

4. **Production deployment:** Deploy frontend to Vercel, backend to Render. Update CORS in `backend/main.py` with the production Vercel URL. Confirm end-to-end works on production URLs.

**Done when:** The sample bill loads instantly and shows a professional report. The Download Report button produces a clean printable PDF. The app is live on Vercel and accessible by URL.

---

### Development Commands

```bash
# Frontend
cd frontend
npm install
npm run dev          # starts on http://localhost:5173

# Backend
cd backend
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn main:app --reload  # starts on http://localhost:8000

# Data processing (run from backend/ after activating venv)
# Uses cy2026-carrier-files-nonqp + ZIP5_APR2026.xlsx as primary sources
python scripts/process_pfs.py      # reads Carrier Files ZIP + ZIP5_APR2026.xlsx
python scripts/process_opps.py     # reads OPPS Addendum B
```

---

### Validation Gate (Phase 0 Complete When)

- Detection rate ≥ 80% on known test bills (true positive rate)
- False positive rate < 15%
- Full end-to-end flow works on real medical bills
- Sample bill demo runs cleanly for investor presentation
- App deployed and accessible by URL

---

### What Comes Next (Phase 1 — Not In Scope Here)

- Turquoise Health Clear Rates API integration (replaces CMS-only benchmarks)
- User accounts and bill history
- Employer claims feed integration
- Attorney referral network integration

Do not build Phase 1 features during this sprint. If an architectural decision would require significant rework to add these features later, flag it and ask before proceeding.
