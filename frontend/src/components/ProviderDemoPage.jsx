import { useState } from "react";
import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// Sample data — Lakeside Internal Medicine (fictional)
// ---------------------------------------------------------------------------

const PRACTICE = {
  name: "Lakeside Internal Medicine",
  location: "Tampa, FL",
  providers: 3,
  specialty: "Internal Medicine",
};

// Tab 1: Audit Report data (1 month)
const AUDIT_PAYERS = [
  {
    name: "Blue Cross Blue Shield",
    short: "BCBS",
    cleanClaimRate: 89,
    denialRate: 11,
    totalBilled: 28400,
    totalPaid: 24870,
    totalContracted: 25157,
    underpayments: [
      { cpt: "99214", desc: "Office visit, est. moderate", billed: 285, paid: 122, contracted: 142, variance: -20, flag: "Underpaid" },
      { cpt: "99215", desc: "Office visit, est. high", billed: 380, paid: 161, contracted: 178, variance: -17, flag: "Underpaid" },
      { cpt: "93000", desc: "ECG, 12-lead", billed: 95, paid: 18, contracted: 22, variance: -4, flag: "Underpaid" },
    ],
    underpaymentTotal: 287,
    denials: [],
    denialTotal: 0,
  },
  {
    name: "Aetna",
    short: "Aetna",
    cleanClaimRate: 75,
    denialRate: 25,
    totalBilled: 18200,
    totalPaid: 12380,
    totalContracted: 12850,
    underpayments: [
      { cpt: "99213", desc: "Office visit, est. low", billed: 185, paid: 82, contracted: 89, variance: -7, flag: "Underpaid" },
    ],
    underpaymentTotal: 44,
    denials: [
      { cpt: "99213", desc: "Office visit, est. low", billed: 185, reasonCode: "CO-16", reason: "Claim lacks information needed for adjudication", amount: 185, appealScore: 8 },
      { cpt: "99214", desc: "Office visit, est. moderate", billed: 285, reasonCode: "CO-16", reason: "Claim lacks information needed for adjudication", amount: 285, appealScore: 7 },
    ],
    denialTotal: 470,
  },
  {
    name: "UnitedHealthcare",
    short: "UHC",
    cleanClaimRate: 96,
    denialRate: 4,
    totalBilled: 22600,
    totalPaid: 19850,
    totalContracted: 19850,
    underpayments: [],
    underpaymentTotal: 0,
    denials: [
      { cpt: "99214", desc: "Office visit, est. moderate", billed: 285, reasonCode: "OA-18", reason: "Exact duplicate claim", amount: 285, appealScore: 9 },
    ],
    denialTotal: 285,
  },
];

const AUDIT_SUMMARY = {
  totalBilled: 69200,
  totalPaid: 57100,
  totalContracted: 57857,
  totalUnderpayment: 331,
  totalDenied: 755,
  monthlyGap: 1086,
  annualizedGap: 13032,
  execSummary: "Lakeside Internal Medicine shows a monthly revenue gap of $1,086 across three payers. BCBS has three active underpayments totaling $287/month, primarily on office visits where payments are consistently below contracted rates. Aetna's CO-16 denials ($470) suggest a documentation submission issue that should be addressable. UHC's OA-18 denial ($285) appears to be a corrected resubmission flagged as duplicate — a straightforward appeal. Annualized, this practice is leaving approximately $13,032 on the table.",
  recommendedActions: [
    "Appeal the two Aetna CO-16 denials immediately — these are documentation-based and have a high overturn rate when supporting records are attached.",
    "Appeal the UHC OA-18 denial with proof this was a corrected claim, not a duplicate submission. Include the original claim number and correction reason.",
    "Contact BCBS about the systematic underpayment on 99214, 99215, and 93000 — request a rate review referencing your contract terms.",
    "Implement a pre-submission checklist for Aetna claims to ensure all required documentation fields are populated before submission.",
  ],
};

// Tab 2: Month-over-month trend data (3 months)
const TREND_MONTHS = ["January 2026", "February 2026", "March 2026"];

const TREND_DATA = {
  aetna99214: {
    label: "Aetna 99214 Underpayment",
    values: [13, 18, 22],
    direction: "worsening",
    color: "#EF4444",
  },
  bcbsDenialRate: {
    label: "BCBS Denial Rate",
    values: [11, 8, 6],
    unit: "%",
    direction: "improving",
    color: "#22C55E",
  },
  uhcCO197: {
    label: "UHC CO-197 Denials (new pattern)",
    values: [0, 0, 3],
    direction: "new",
    color: "#F59E0B",
  },
  monthlyGap: {
    label: "Total Monthly Revenue Gap",
    values: [1086, 1240, 1415],
    direction: "worsening",
    color: "#EF4444",
  },
};

const TREND_NARRATIVE = `Over the past three months, Lakeside Internal Medicine's revenue gap is trending upward — from $1,086 in January to $1,415 in March (+30%).

Key changes:
- Aetna's underpayment on 99214 has increased from $13 to $22 per claim. With ~35 claims/month, this adds ~$315/month in lost revenue vs. January. This suggests a systematic issue, possibly a fee schedule update that wasn't applied to your contract.
- BCBS denial rate improved from 11% to 6%, likely due to the documentation checklist implemented after the audit. This is saving approximately $180/month in denied claims.
- A new pattern emerged in March: UHC denied 3 claims with CO-197 (precertification not obtained). This was not present in prior months and should be investigated immediately before it becomes systemic.

Recommended action: Contact your Aetna representative about the 99214 rate discrepancy. This single issue represents ~$3,780/year in underpayments at current volume.`;

// Tab 3: Appeal letters
const APPEAL_LETTERS = [
  {
    payer: "Aetna",
    cpt: "99213",
    reasonCode: "CO-16",
    amount: 185,
    dos: "02/14/2026",
    claimId: "AET-2026-441872",
    letter: `RE: Appeal of Denied Claim AET-2026-441872
CPT 99213 — Office Visit, Established Patient, Low Complexity
Date of Service: February 14, 2026
Patient DOB: 07/22/1965
Billed Amount: $185.00

Dear Aetna Claims Review Department,

I am writing to appeal the denial of the above-referenced claim under reason code CO-16 (Claim/service lacks information needed for adjudication).

APPEAL BASIS

This denial indicates that required documentation was not received with the original claim submission. We have confirmed that all required documentation was present in our practice management system at the time of service. The issue appears to be a transmission error during electronic claim submission.

SUPPORTING DOCUMENTATION ENCLOSED

1. Complete progress note for the February 14, 2026 encounter, documenting:
   - Chief complaint and history of present illness
   - Review of systems (2 systems reviewed)
   - Physical examination findings
   - Medical decision-making of low complexity
   - Assessment and plan

2. Signed physician attestation confirming the services were rendered as billed

3. Electronic claim submission confirmation showing original transmission date

Per CMS Guidelines (MLN Matters SE0726), claims denied for missing information should be reconsidered when the information was available at the time of service and is subsequently provided. The enclosed documentation satisfies all requirements for CPT 99213.

We respectfully request that this claim be reprocessed and paid at the contracted rate.

Sincerely,
[Physician Name], MD
Lakeside Internal Medicine
NPI: [Practice NPI]`,
  },
  {
    payer: "UHC",
    cpt: "99214",
    reasonCode: "OA-18",
    amount: 285,
    dos: "02/21/2026",
    claimId: "UHC-2026-559103",
    letter: `RE: Appeal of Denied Claim UHC-2026-559103
CPT 99214 — Office Visit, Established Patient, Moderate Complexity
Date of Service: February 21, 2026
Patient DOB: 11/03/1971
Billed Amount: $285.00

Dear UnitedHealthcare Claims Review Department,

I am writing to appeal the denial of the above-referenced claim under reason code OA-18 (Exact duplicate claim/service).

APPEAL BASIS

This claim is NOT a duplicate. It is a corrected resubmission of claim UHC-2026-502847 (original date of submission: February 25, 2026). The original claim contained an incorrect modifier and was resubmitted with the correction on March 3, 2026 using frequency type code "7" (replacement claim) as required by UHC's corrected claim policy.

EVIDENCE OF CORRECTION

1. Original claim UHC-2026-502847 — submitted 02/25/2026 (included for reference)
2. Corrected claim UHC-2026-559103 — submitted 03/03/2026 with frequency type "7"
3. The only change between claims is the removal of an incorrect modifier 25 that was applied in error

Per UHC's Provider Administrative Guide, Section 8.4: "Corrected claims submitted with frequency type code 7 should be processed as replacements, not flagged as duplicates."

The corrected claim should be adjudicated on its own merits and paid at the contracted rate of $285.00.

Sincerely,
[Physician Name], MD
Lakeside Internal Medicine
NPI: [Practice NPI]`,
  },
  {
    payer: "Aetna",
    cpt: "99214",
    reasonCode: "CO-16",
    amount: 285,
    dos: "02/07/2026",
    claimId: "AET-2026-438291",
    letter: `RE: Appeal of Denied Claim AET-2026-438291
CPT 99214 — Office Visit, Established Patient, Moderate Complexity
Date of Service: February 7, 2026
Patient DOB: 03/15/1958
Billed Amount: $285.00

Dear Aetna Claims Review Department,

I am writing to appeal the denial of the above-referenced claim under reason code CO-16 (Claim/service lacks information needed for adjudication).

APPEAL BASIS

The denial states that information needed for adjudication was not included. Upon review, all required elements for a CPT 99214 encounter were documented in the medical record:

1. History: Detailed HPI with 4+ elements, pertinent ROS (3 systems), pertinent PFSH
2. Examination: Detailed multi-system examination (8 organ systems)
3. Medical Decision Making: Moderate complexity — multiple diagnoses, prescription drug management, moderate data review

DOCUMENTATION ENCLOSED

- Complete progress note for 02/07/2026 encounter
- Problem list and medication list current as of date of service
- Prior authorization reference (if applicable)

This encounter meets all documentation requirements for CPT 99214 per the 2021 E&M Guidelines. We respectfully request reprocessing and payment at the contracted rate.

Sincerely,
[Physician Name], MD
Lakeside Internal Medicine
NPI: [Practice NPI]`,
  },
];

// Tab 4: Payer Intelligence (coming soon mockup)
const BENCHMARK_DATA = [
  { cpt: "99213", desc: "Office visit, est. low", yourRate: 89, marketMedian: 102, percentile: 28 },
  { cpt: "99214", desc: "Office visit, est. moderate", yourRate: 118, marketMedian: 138, percentile: 22 },
  { cpt: "99215", desc: "Office visit, est. high", yourRate: 155, marketMedian: 178, percentile: 25 },
  { cpt: "99203", desc: "Office visit, new low", yourRate: 98, marketMedian: 118, percentile: 30 },
  { cpt: "99204", desc: "Office visit, new moderate", yourRate: 165, marketMedian: 192, percentile: 27 },
];

const CODING_DIST = [
  { code: "99213", yours: 65, peers: 48 },
  { code: "99214", yours: 25, peers: 35 },
  { code: "99215", yours: 5, peers: 10 },
  { code: "99211/12", yours: 5, peers: 7 },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TABS = [
  { key: "start", label: "Getting Started" },
  { key: "audit", label: "Your Audit Report" },
  { key: "trends", label: "Month-Over-Month Trends" },
  { key: "appeals", label: "Appeal Letters" },
  { key: "intel", label: "Payer Intelligence" },
];

export default function ProviderDemoPage() {
  const [activeTab, setActiveTab] = useState("start");
  const [expandedAppeal, setExpandedAppeal] = useState(null);

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap"
        rel="stylesheet"
      />

      {/* Demo banner */}
      <div style={{
        background: "rgba(59,130,246,0.15)",
        borderBottom: "1px solid rgba(59,130,246,0.25)",
        padding: "10px 20px",
        textAlign: "center",
        fontSize: "13px",
        color: "#93c5fd",
      }}>
        You're viewing a demo with sample data from {PRACTICE.name} (fictional).{" "}
        <Link to="/audit" style={{ color: "#60a5fa", fontWeight: "600", textDecoration: "none" }}>
          Start Your Free Audit &rarr;
        </Link>
      </div>

      {/* Header */}
      <header style={{
        padding: "16px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        flexWrap: "wrap",
        gap: "8px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Link to="/" style={{
            width: "32px", height: "32px", borderRadius: "8px",
            background: "linear-gradient(135deg, #0d9488, #14b8a6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px", fontWeight: "700", color: "#0a1628", textDecoration: "none",
          }}>C</Link>
          <span style={{ fontWeight: "600", fontSize: "16px" }}>Parity Provider</span>
          <span style={{
            background: "rgba(59,130,246,0.15)", color: "#60a5fa",
            fontSize: "11px", fontWeight: "600", padding: "3px 8px",
            borderRadius: "4px", textTransform: "uppercase",
          }}>Demo</span>
        </div>
        <div style={{ fontSize: "13px", color: "#64748b" }}>
          {PRACTICE.name} &middot; {PRACTICE.location} &middot; {PRACTICE.providers} providers
        </div>
      </header>

      {/* Tab navigation */}
      <nav style={{
        display: "flex", gap: "0",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "0 24px", overflowX: "auto",
      }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            style={{
              padding: "14px 18px", fontSize: "13px",
              fontWeight: activeTab === t.key ? "600" : "400",
              color: activeTab === t.key ? "#60a5fa" : "#64748b",
              borderBottom: activeTab === t.key ? "2px solid #3b82f6" : "2px solid transparent",
              background: "none", border: "none", cursor: "pointer",
              whiteSpace: "nowrap", fontFamily: "inherit",
            }}
          >{t.label}</button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ padding: "32px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        {activeTab === "start" && <GettingStartedTab onNavigate={setActiveTab} />}
        {activeTab === "audit" && <AuditReport />}
        {activeTab === "trends" && <TrendsTab />}
        {activeTab === "appeals" && (
          <AppealsTab expanded={expandedAppeal} onToggle={(i) => setExpandedAppeal(expandedAppeal === i ? null : i)} />
        )}
        {activeTab === "intel" && <IntelTab />}
      </main>

      {/* Bottom CTA */}
      <div style={{
        maxWidth: "1100px", margin: "0 auto", padding: "0 24px 48px",
        textAlign: "center",
      }}>
        <div style={{
          background: "rgba(59,130,246,0.06)",
          border: "1px solid rgba(59,130,246,0.15)",
          borderRadius: "12px",
          padding: "28px",
        }}>
          <p style={{ fontSize: "15px", color: "#94a3b8", margin: "0 0 16px" }}>
            This is what Parity Provider finds. Start with a free audit using your own data — no cost, no commitment.
          </p>
          <Link to="/audit" style={{
            display: "inline-block", background: "#3b82f6", color: "#fff",
            padding: "12px 28px", borderRadius: "8px", fontWeight: "600",
            fontSize: "15px", textDecoration: "none",
          }}>
            Start Your Free Audit &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 0: Getting Started
// ---------------------------------------------------------------------------

const FEE_METHODS = [
  { id: "excel", label: "Upload Excel file" },
  { id: "pdf", label: "Upload PDF contract" },
  { id: "paste", label: "Paste or type rates" },
  { id: "photo", label: "Upload photo of contract page" },
  { id: "medicare", label: "% of Medicare" },
];

const SAMPLE_FILES = [
  "Aetna_ERA_Jan2026.835",
  "BCBS_ERA_Jan2026.edi",
  "UHC_Remit_Jan.835",
];

const mockInput = {
  background: "#fff",
  border: "1px solid #CBD5E1",
  borderRadius: "6px",
  padding: "8px 12px",
  fontSize: "13px",
  color: "#1E293B",
  width: "100%",
  boxSizing: "border-box",
  cursor: "default",
};

function GettingStartedTab({ onNavigate }) {
  return (
    <div>
      <div style={{ textAlign: "center", marginBottom: "36px" }}>
        <h2 style={{ ...h2Style, marginBottom: "10px" }}>
          Two steps. Five minutes. No data entry.
        </h2>
        <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "560px", margin: "0 auto" }}>
          That's all it takes to find out if your payers are paying what they owe you.
        </p>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
        gap: "24px",
        marginBottom: "40px",
      }}>
        {/* Step 1 */}
        <div style={stepCardOuter}>
          <div style={stepLabel}>Step 1 — 30 seconds</div>
          <h3 style={stepTitle}>Tell us your payers</h3>

          {/* Payer dropdown */}
          <div style={{ marginBottom: "16px" }}>
            <div style={fieldLabel}>Payer</div>
            <div style={{ ...mockInput, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>Aetna</span>
              <span style={{ color: "#94a3b8", fontSize: "11px" }}>{"\u25BC"}</span>
            </div>
          </div>

          {/* Fee schedule methods */}
          <div style={{ marginBottom: "16px" }}>
            <div style={fieldLabel}>How would you like to provide your fee schedule?</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {FEE_METHODS.map((m) => {
                const selected = m.id === "medicare";
                return (
                  <div
                    key={m.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      padding: "10px 14px",
                      borderRadius: "8px",
                      border: selected ? "2px solid #0D9488" : "1px solid #E2E8F0",
                      background: selected ? "rgba(13,148,136,0.04)" : "#fff",
                      cursor: "default",
                      position: "relative",
                    }}
                  >
                    <div style={{
                      width: "16px", height: "16px", borderRadius: "50%",
                      border: selected ? "5px solid #0D9488" : "2px solid #CBD5E1",
                      boxSizing: "border-box", flexShrink: 0,
                    }} />
                    <span style={{ fontSize: "13px", color: "#1E293B", fontWeight: selected ? "600" : "400" }}>
                      {m.label}
                    </span>
                    {selected && (
                      <span style={{
                        marginLeft: "auto",
                        fontSize: "10px", fontWeight: "700", textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        background: "#0D9488", color: "#fff",
                        padding: "3px 8px", borderRadius: "4px",
                      }}>Easiest</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* % of Medicare inputs */}
          <div style={{
            background: "#F0FDFA", border: "1px solid #99F6E4",
            borderRadius: "10px", padding: "16px", marginBottom: "16px",
          }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
              <div>
                <div style={fieldLabel}>Percentage of Medicare</div>
                <div style={{ ...mockInput, background: "#fff" }}>120%</div>
              </div>
              <div>
                <div style={fieldLabel}>Practice ZIP Code</div>
                <div style={{ ...mockInput, background: "#fff" }}>33611</div>
              </div>
            </div>
            <div style={{
              display: "flex", alignItems: "flex-start", gap: "8px",
              background: "#fff", borderRadius: "8px", padding: "12px",
              border: "1px solid #99F6E4",
            }}>
              <span style={{ color: "#0D9488", fontSize: "16px", lineHeight: "1", flexShrink: 0 }}>{"\u2713"}</span>
              <span style={{ fontSize: "12px", color: "#1E293B", lineHeight: "1.5" }}>
                <strong>7,718 CPT codes</strong> generated instantly from 2026 CMS Medicare Fee Schedule, adjusted for Tampa, FL locality
              </span>
            </div>
          </div>

          <p style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.6", margin: 0 }}>
            Most contracts are structured as a percentage of Medicare. If yours is, you don't need to upload anything — just enter the percentage and your ZIP code. We do the rest.
          </p>
        </div>

        {/* Step 2 */}
        <div style={stepCardOuter}>
          <div style={stepLabel}>Step 2 — 60 seconds</div>
          <h3 style={stepTitle}>Upload your 835 files</h3>

          {/* Drop zone */}
          <div style={{
            border: "2px dashed #CBD5E1",
            borderRadius: "10px",
            padding: "28px 20px",
            textAlign: "center",
            marginBottom: "16px",
            background: "#F8FAFC",
          }}>
            <div style={{ fontSize: "28px", marginBottom: "8px", color: "#94a3b8" }}>{"\u2B06"}</div>
            <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "4px" }}>
              Drag & drop your remittance files here
            </div>
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>
              3 files selected
            </div>
          </div>

          {/* File chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "12px" }}>
            {SAMPLE_FILES.map((f) => (
              <div key={f} style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "#EFF6FF", border: "1px solid #BFDBFE",
                borderRadius: "6px", padding: "6px 12px", fontSize: "12px", color: "#1E40AF",
              }}>
                <span style={{ fontSize: "14px" }}>{"\uD83D\uDCC4"}</span>
                {f}
              </div>
            ))}
          </div>

          <p style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "16px" }}>
            Accepted formats: .835, .edi, .txt, or .zip containing multiple files
          </p>

          <p style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.6", marginBottom: "20px" }}>
            Your clearinghouse (Availity, Office Ally, Change Healthcare) sends these to you monthly. Download them from your clearinghouse portal and upload here — or just forward the email to us.
          </p>

          {/* Progress indicator */}
          <div style={{
            background: "#F8FAFC", borderRadius: "8px", padding: "14px",
            border: "1px solid #E2E8F0", marginBottom: "12px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "12px", color: "#64748b" }}>Processing...</span>
              <span style={{ fontSize: "12px", color: "#3B82F6", fontWeight: "600" }}>100%</span>
            </div>
            <div style={{ height: "4px", borderRadius: "2px", background: "#E2E8F0" }}>
              <div style={{ height: "4px", borderRadius: "2px", background: "#3B82F6", width: "100%" }} />
            </div>
            <div style={{ fontSize: "11px", color: "#64748b", marginTop: "6px" }}>
              247 payment lines identified across 3 payers
            </div>
          </div>

          {/* Success state */}
          <div style={{
            display: "flex", alignItems: "center", gap: "8px",
            background: "#F0FDF4", border: "1px solid #BBF7D0",
            borderRadius: "8px", padding: "12px 14px",
          }}>
            <span style={{ color: "#10B981", fontSize: "18px", flexShrink: 0 }}>{"\u2713"}</span>
            <span style={{ fontSize: "13px", color: "#166534", fontWeight: "600" }}>
              Analysis complete — your report is ready
            </span>
          </div>
        </div>
      </div>

      {/* Transition / CTA */}
      <div style={{ textAlign: "center", marginBottom: "8px" }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: "10px",
          fontSize: "22px", color: "#3B82F6", marginBottom: "20px",
        }}>
          <span>{"\u2501\u2501"}</span>
          <span>{"\u25B6"}</span>
          <span>{"\u2501\u2501"}</span>
        </div>
        <p style={{
          fontSize: "15px", color: "#94a3b8", lineHeight: "1.8",
          maxWidth: "640px", margin: "0 auto 24px",
        }}>
          That's it. From here, our AI analyzes every payment line against your contracted rates,
          interprets every denial code in plain English, and delivers a complete report.
          Here's what {PRACTICE.name}'s report looked like:
        </p>
        <button
          onClick={() => onNavigate("audit")}
          style={{
            display: "inline-block",
            background: "#3b82f6", color: "#fff",
            padding: "12px 28px", borderRadius: "8px",
            fontWeight: "600", fontSize: "15px",
            border: "none", cursor: "pointer",
            fontFamily: "inherit",
            transition: "background 0.2s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#2563eb")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#3b82f6")}
        >
          See the Audit Report &rarr;
        </button>
      </div>
    </div>
  );
}

const stepCardOuter = {
  background: "#fff",
  borderRadius: "14px",
  padding: "28px",
  boxShadow: "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04)",
};

const stepLabel = {
  fontSize: "11px",
  fontWeight: "600",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "#0D9488",
  marginBottom: "6px",
};

const stepTitle = {
  fontSize: "18px",
  fontWeight: "600",
  color: "#1E293B",
  marginBottom: "20px",
};

const fieldLabel = {
  fontSize: "11px",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  marginBottom: "6px",
};

// ---------------------------------------------------------------------------
// Tab 1: Audit Report
// ---------------------------------------------------------------------------

function AuditReport() {
  return (
    <div>
      <h2 style={h2Style}>Audit Report — {PRACTICE.name}</h2>
      <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "28px" }}>
        Period: February 2026 &middot; 3 payers analyzed &middot; Report generated March 1, 2026
      </p>

      {/* Summary stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        <StatCard label="Total Billed" value={fmt(AUDIT_SUMMARY.totalBilled)} />
        <StatCard label="Total Paid" value={fmt(AUDIT_SUMMARY.totalPaid)} />
        <StatCard label="Underpayments" value={fmt(AUDIT_SUMMARY.totalUnderpayment)} accent="#EF4444" />
        <StatCard label="Denied Revenue" value={fmt(AUDIT_SUMMARY.totalDenied)} accent="#F59E0B" />
        <StatCard label="Monthly Gap" value={fmt(AUDIT_SUMMARY.monthlyGap)} accent="#EF4444" />
        <StatCard label="Annualized Gap" value={fmt(AUDIT_SUMMARY.annualizedGap)} accent="#EF4444" />
      </div>

      {/* Executive Summary */}
      <div style={{ ...cardStyle, marginBottom: "28px" }}>
        <h3 style={h3Style}>AI Executive Summary</h3>
        <p style={{ fontSize: "14px", lineHeight: "1.8", color: "#94a3b8" }}>
          {AUDIT_SUMMARY.execSummary}
        </p>
      </div>

      {/* Recommended Actions */}
      <div style={{ ...cardStyle, marginBottom: "32px" }}>
        <h3 style={h3Style}>Recommended Actions</h3>
        <ol style={{ margin: 0, paddingLeft: "20px", fontSize: "14px", lineHeight: "2", color: "#94a3b8" }}>
          {AUDIT_SUMMARY.recommendedActions.map((a, i) => <li key={i}>{a}</li>)}
        </ol>
      </div>

      {/* Per-payer breakdown */}
      {AUDIT_PAYERS.map((p) => (
        <div key={p.short} style={{ ...cardStyle, marginBottom: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
            <h3 style={{ ...h3Style, margin: 0 }}>{p.name}</h3>
            <div style={{ display: "flex", gap: "16px", fontSize: "13px" }}>
              <span style={{ color: "#94a3b8" }}>Clean claim rate: <strong style={{ color: p.cleanClaimRate >= 90 ? "#22C55E" : p.cleanClaimRate >= 80 ? "#F59E0B" : "#EF4444" }}>{p.cleanClaimRate}%</strong></span>
              <span style={{ color: "#94a3b8" }}>Denial rate: <strong style={{ color: p.denialRate <= 5 ? "#22C55E" : p.denialRate <= 15 ? "#F59E0B" : "#EF4444" }}>{p.denialRate}%</strong></span>
            </div>
          </div>

          {p.underpayments.length > 0 && (
            <>
              <div style={{ fontSize: "12px", fontWeight: "600", color: "#EF4444", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>
                Underpayments ({fmt(p.underpaymentTotal)})
              </div>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    {["CPT", "Description", "Billed", "Paid", "Contracted", "Variance", "Flag"].map(h => (
                      <th key={h} style={thStyle}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {p.underpayments.map((u, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={tdStyle}>{u.cpt}</td>
                      <td style={{ ...tdStyle, color: "#94a3b8" }}>{u.desc}</td>
                      <td style={tdStyleR}>{fmt(u.billed)}</td>
                      <td style={tdStyleR}>{fmt(u.paid)}</td>
                      <td style={tdStyleR}>{fmt(u.contracted)}</td>
                      <td style={{ ...tdStyleR, color: "#EF4444" }}>{fmt(u.variance)}</td>
                      <td style={{ ...tdStyle, color: "#EF4444", fontWeight: "600", fontSize: "11px" }}>{u.flag}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {p.denials.length > 0 && (
            <>
              <div style={{ fontSize: "12px", fontWeight: "600", color: "#F59E0B", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px", marginTop: p.underpayments.length > 0 ? "20px" : 0 }}>
                Denials ({fmt(p.denialTotal)})
              </div>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    {["CPT", "Description", "Billed", "Reason Code", "Reason", "Appeal Score"].map(h => (
                      <th key={h} style={thStyle}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {p.denials.map((d, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={tdStyle}>{d.cpt}</td>
                      <td style={{ ...tdStyle, color: "#94a3b8" }}>{d.desc}</td>
                      <td style={tdStyleR}>{fmt(d.billed)}</td>
                      <td style={{ ...tdStyle, color: "#F59E0B", fontWeight: "600" }}>{d.reasonCode}</td>
                      <td style={{ ...tdStyle, color: "#94a3b8", fontSize: "12px" }}>{d.reason}</td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: "10px", fontSize: "11px", fontWeight: "600",
                          background: d.appealScore >= 8 ? "rgba(34,197,94,0.15)" : "rgba(59,130,246,0.15)",
                          color: d.appealScore >= 8 ? "#22C55E" : "#60a5fa",
                        }}>{d.appealScore}/10</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {p.underpayments.length === 0 && p.denials.length === 0 && (
            <p style={{ fontSize: "13px", color: "#64748b" }}>No underpayments or notable denials this period.</p>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: Month-Over-Month Trends
// ---------------------------------------------------------------------------

function TrendsTab() {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "8px" }}>
        <h2 style={{ ...h2Style, margin: 0 }}>Month-Over-Month Trends</h2>
        <span style={liveBadge}>LIVE — Available now with monitoring subscription</span>
      </div>

      {/* Trend cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        {Object.values(TREND_DATA).map((t) => (
          <div key={t.label} style={cardStyle}>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#94a3b8", marginBottom: "8px" }}>{t.label}</div>
            <div style={{ display: "flex", gap: "12px", alignItems: "flex-end", marginBottom: "8px" }}>
              {t.values.map((v, i) => (
                <div key={i} style={{ flex: 1, textAlign: "center" }}>
                  <div style={{ fontSize: "20px", fontWeight: "700", color: i === t.values.length - 1 ? t.color : "#94a3b8" }}>
                    {t.unit === "%" ? `${v}%` : v === 0 ? "—" : `$${v}`}
                  </div>
                  <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px" }}>{TREND_MONTHS[i].split(" ")[0].slice(0, 3)}</div>
                </div>
              ))}
            </div>
            <div style={{
              fontSize: "11px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.06em",
              color: t.direction === "improving" ? "#22C55E" : t.direction === "new" ? "#F59E0B" : "#EF4444",
            }}>
              {t.direction === "improving" ? "\u2193 Improving" : t.direction === "new" ? "\u26A0 New Pattern" : "\u2191 Worsening"}
            </div>
          </div>
        ))}
      </div>

      {/* Revenue gap chart (simplified bar representation) */}
      <div style={{ ...cardStyle, marginBottom: "28px" }}>
        <h3 style={h3Style}>Revenue Gap Trend</h3>
        <div style={{ display: "flex", gap: "16px", alignItems: "flex-end", height: "140px", padding: "20px 0" }}>
          {TREND_DATA.monthlyGap.values.map((v, i) => {
            const maxVal = Math.max(...TREND_DATA.monthlyGap.values);
            const height = (v / maxVal) * 100;
            return (
              <div key={i} style={{ flex: 1, textAlign: "center" }}>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#EF4444", marginBottom: "6px" }}>{fmt(v)}</div>
                <div style={{
                  height: `${height}px`, background: "rgba(239,68,68,0.3)",
                  border: "1px solid rgba(239,68,68,0.5)", borderRadius: "4px 4px 0 0",
                }} />
                <div style={{ fontSize: "12px", color: "#64748b", marginTop: "6px" }}>{TREND_MONTHS[i]}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* AI Trend Narrative */}
      <div style={cardStyle}>
        <h3 style={h3Style}>AI Trend Analysis</h3>
        {TREND_NARRATIVE.split("\n\n").map((p, i) => (
          <p key={i} style={{ fontSize: "14px", lineHeight: "1.8", color: "#94a3b8", marginBottom: "12px", whiteSpace: "pre-line" }}>
            {p}
          </p>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: Appeal Letters
// ---------------------------------------------------------------------------

function AppealsTab({ expanded, onToggle }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "8px" }}>
        <h2 style={{ ...h2Style, margin: 0 }}>Appeal Letters</h2>
        <span style={liveBadge}>LIVE — Available now</span>
      </div>

      <p style={{ fontSize: "14px", color: "#94a3b8", marginBottom: "24px", lineHeight: "1.7" }}>
        Each denial from your audit has a draft appeal letter ready to review, edit, and send.
        Letters cite specific CMS guidelines and your contract terms.
      </p>

      {APPEAL_LETTERS.map((a, i) => (
        <div key={i} style={{ ...cardStyle, marginBottom: "16px" }}>
          {/* Summary row */}
          <div
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", flexWrap: "wrap", gap: "8px" }}
            onClick={() => onToggle(i)}
          >
            <div>
              <span style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0" }}>
                {a.payer} — {a.reasonCode} on CPT {a.cpt}
              </span>
              <span style={{ fontSize: "13px", color: "#64748b", marginLeft: "12px" }}>
                {fmt(a.amount)} &middot; DOS {a.dos}
              </span>
            </div>
            <button
              style={{
                padding: "6px 16px", borderRadius: "6px", fontSize: "12px", fontWeight: "600",
                border: "1px solid #3b82f6", background: expanded === i ? "#3b82f6" : "transparent",
                color: expanded === i ? "#fff" : "#60a5fa", cursor: "pointer", fontFamily: "inherit",
              }}
            >
              {expanded === i ? "Hide Letter" : "View Appeal Letter"}
            </button>
          </div>

          {/* Expanded letter */}
          {expanded === i && (
            <div style={{
              marginTop: "16px", padding: "20px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "8px",
            }}>
              <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "12px" }}>
                Claim ID: {a.claimId}
              </div>
              <pre style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: "13px",
                lineHeight: "1.8",
                color: "#cbd5e1",
                whiteSpace: "pre-wrap",
                margin: 0,
              }}>
                {a.letter}
              </pre>
              <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
                <button style={{
                  padding: "8px 20px", borderRadius: "6px", fontSize: "13px", fontWeight: "600",
                  background: "#3b82f6", color: "#fff", border: "none", cursor: "pointer", fontFamily: "inherit",
                }}>
                  Copy to Clipboard
                </button>
                <button style={{
                  padding: "8px 20px", borderRadius: "6px", fontSize: "13px", fontWeight: "600",
                  background: "transparent", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.3)",
                  cursor: "pointer", fontFamily: "inherit",
                }}>
                  Download PDF
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 4: Payer Intelligence (Coming Soon)
// ---------------------------------------------------------------------------

function IntelTab() {
  return (
    <div style={{ position: "relative" }}>
      {/* Coming soon overlay */}
      <div style={{
        position: "absolute", inset: 0, zIndex: 10,
        background: "rgba(10,22,40,0.7)",
        display: "flex", alignItems: "center", justifyContent: "center",
        borderRadius: "12px",
      }}>
        <div style={{ textAlign: "center", padding: "40px" }}>
          <div style={{ fontSize: "32px", marginBottom: "16px" }}>{"\uD83D\uDD2E"}</div>
          <h3 style={{ fontSize: "20px", fontWeight: "600", color: "#f1f5f9", marginBottom: "8px" }}>Coming Soon</h3>
          <p style={{ fontSize: "14px", color: "#94a3b8", maxWidth: "400px", lineHeight: "1.7" }}>
            Payer intelligence and benchmark comparisons become available as more practices join.
            Early adopters get priority access.
          </p>
          <Link to="/audit" style={{
            display: "inline-block", marginTop: "20px",
            background: "#3b82f6", color: "#fff", padding: "10px 24px",
            borderRadius: "8px", fontWeight: "600", fontSize: "14px", textDecoration: "none",
          }}>
            Start Your Free Audit &rarr;
          </Link>
        </div>
      </div>

      {/* Mockup content (visible but blurred behind overlay) */}
      <div style={{ filter: "blur(2px)", pointerEvents: "none" }}>
        <h2 style={h2Style}>Payer Intelligence — Aetna</h2>
        <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "28px" }}>
          Your Aetna rates vs. Internal Medicine practices in Tampa metro
        </p>

        {/* Rate comparison table */}
        <div style={{ ...cardStyle, marginBottom: "28px" }}>
          <h3 style={h3Style}>Contract Rate Benchmarks</h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                {["CPT", "Description", "Your Rate", "Market Median", "Percentile"].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {BENCHMARK_DATA.map((r) => (
                <tr key={r.cpt} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={tdStyle}>{r.cpt}</td>
                  <td style={{ ...tdStyle, color: "#94a3b8" }}>{r.desc}</td>
                  <td style={tdStyleR}>{fmt(r.yourRate)}</td>
                  <td style={tdStyleR}>{fmt(r.marketMedian)}</td>
                  <td style={{ ...tdStyle, textAlign: "center" }}>
                    <span style={{
                      display: "inline-block", padding: "2px 8px", borderRadius: "10px",
                      fontSize: "11px", fontWeight: "600",
                      background: "rgba(239,68,68,0.15)", color: "#EF4444",
                    }}>{r.percentile}th</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8", marginTop: "16px" }}>
            Your Aetna rates are below the 35th percentile across your top codes. At your next
            contract renewal, this data supports requesting a 10-15% rate increase.
          </p>
        </div>

        {/* Coding distribution */}
        <div style={cardStyle}>
          <h3 style={h3Style}>E&M Coding Distribution vs. Specialty Peers</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "16px", marginBottom: "16px" }}>
            {CODING_DIST.map((c) => (
              <div key={c.code} style={{ textAlign: "center" }}>
                <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "8px" }}>{c.code}</div>
                <div style={{ display: "flex", gap: "4px", justifyContent: "center", alignItems: "flex-end", height: "60px" }}>
                  <div style={{
                    width: "24px", height: `${c.yours * 0.8}px`,
                    background: "rgba(59,130,246,0.4)", borderRadius: "3px 3px 0 0",
                  }} />
                  <div style={{
                    width: "24px", height: `${c.peers * 0.8}px`,
                    background: "rgba(148,163,184,0.3)", borderRadius: "3px 3px 0 0",
                  }} />
                </div>
                <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginTop: "4px", fontSize: "11px" }}>
                  <span style={{ color: "#60a5fa" }}>{c.yours}%</span>
                  <span style={{ color: "#64748b" }}>{c.peers}%</span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: "16px", fontSize: "11px", justifyContent: "center" }}>
            <span><span style={{ display: "inline-block", width: "10px", height: "10px", borderRadius: "2px", background: "rgba(59,130,246,0.4)", marginRight: "4px", verticalAlign: "middle" }} />Your practice</span>
            <span><span style={{ display: "inline-block", width: "10px", height: "10px", borderRadius: "2px", background: "rgba(148,163,184,0.3)", marginRight: "4px", verticalAlign: "middle" }} />Specialty peers</span>
          </div>
          <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8", marginTop: "16px" }}>
            Your practice bills 99213 at 65% vs. a peer average of 48%, and 99214 at only 25% vs. 35%.
            This suggests potential undercoding — a coding optimization review could shift 10-15% of your
            99213 visits to 99214, increasing revenue by an estimated $8,000-12,000 annually.
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared styles and helpers
// ---------------------------------------------------------------------------

const h2Style = {
  fontFamily: "'DM Serif Display', serif",
  fontSize: "24px",
  fontWeight: "400",
  color: "#f1f5f9",
  marginBottom: "16px",
};

const h3Style = {
  fontSize: "15px",
  fontWeight: "600",
  color: "#e2e8f0",
  marginBottom: "12px",
};

const cardStyle = {
  background: "rgba(255,255,255,0.02)",
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "12px",
  padding: "24px",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "13px",
};

const thStyle = {
  padding: "8px 10px",
  textAlign: "left",
  fontSize: "11px",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
};

const tdStyle = {
  padding: "8px 10px",
  color: "#e2e8f0",
};

const tdStyleR = {
  ...tdStyle,
  textAlign: "right",
};

const liveBadge = {
  display: "inline-block",
  fontSize: "11px",
  fontWeight: "600",
  padding: "4px 10px",
  borderRadius: "6px",
  background: "rgba(34,197,94,0.12)",
  color: "#22C55E",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

function fmt(n) {
  if (n == null) return "—";
  if (n < 0) return `-$${Math.abs(n).toLocaleString()}`;
  return `$${n.toLocaleString()}`;
}

function StatCard({ label, value, sub, accent }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>{label}</div>
      <div style={{ fontSize: "22px", fontWeight: "700", color: accent || "#e2e8f0" }}>{value}</div>
      {sub && <div style={{ fontSize: "11px", color: "#475569", marginTop: "2px" }}>{sub}</div>}
    </div>
  );
}
