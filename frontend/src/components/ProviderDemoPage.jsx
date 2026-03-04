import { useState } from "react";
import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// Sample data — Lakeside Internal Medicine & Cardiology
// ---------------------------------------------------------------------------

const PRACTICE = {
  name: "Lakeside Internal Medicine & Cardiology",
  physicians: 6,
  physDesc: "4 internists, 2 cardiologists",
  annualRevenue: 4200000,
  revenueGap: 150000,
  denialRate: 11.2,
  denialBenchmark: "5\u201310%",
  deniedRevenue: 89000,
  totalRecovery: 239000,
};

const PAYERS = [
  {
    name: "Blue Cross Blue Shield",
    short: "BCBS",
    status: "good",
    statusLabel: "Strong",
    avgVsMedicare: 7,
    denialRate: 6.4,
    denials: 10,
    revenueGap: 0,
    denialPatterns: [
      { reason: "Timely filing (>90 days)", count: 4, reasonCode: "CO-29" },
      { reason: "Coordination of benefits", count: 3, reasonCode: "CO-22" },
      { reason: "Various other", count: 3, reasonCode: "Various" },
    ],
  },
  {
    name: "Aetna",
    short: "Aetna",
    status: "critical",
    statusLabel: "Underpaying",
    avgVsMedicare: -9,
    denialRate: 9.1,
    denials: 16,
    revenueGap: 127000,
    denialPatterns: [
      { reason: "Bundling \u2014 99214 + 93000 denied as inclusive", count: 7, reasonCode: "CO-97" },
      { reason: "Pre-authorization not obtained (cardiac imaging)", count: 5, reasonCode: "CO-197" },
      { reason: "Various other", count: 4, reasonCode: "Various" },
    ],
  },
  {
    name: "UnitedHealthcare",
    short: "UHC",
    status: "warning",
    statusLabel: "High Denials",
    avgVsMedicare: 1,
    denialRate: 14.3,
    denials: 34,
    revenueGap: 23000,
    denialPatterns: [
      { reason: "Medical necessity not established \u2014 CPT 93306 (echo)", count: 12, reasonCode: "CO-50" },
      { reason: "Modifier 25 rejected on same-day E&M + procedure", count: 8, reasonCode: "CO-4" },
      { reason: "Duplicate claim (actually separate dates of service)", count: 6, reasonCode: "CO-18" },
      { reason: "Various other", count: 8, reasonCode: "Various" },
    ],
  },
];

const FEE_SCHEDULE = [
  { cpt: "99214", desc: "Office visit, est. patient, moderate", medicare: 128, bcbs: 142, aetna: 118, uhc: 135 },
  { cpt: "99213", desc: "Office visit, est. patient, low", medicare: 98, bcbs: 104, aetna: 89, uhc: 96 },
  { cpt: "93000", desc: "ECG, 12-lead", medicare: 18, bcbs: 22, aetna: 15, uhc: 19 },
  { cpt: "93306", desc: "Echocardiogram, complete", medicare: 185, bcbs: 198, aetna: 165, uhc: 190 },
  { cpt: "99215", desc: "Office visit, est. patient, high", medicare: 172, bcbs: 180, aetna: 155, uhc: 168 },
  { cpt: "99203", desc: "Office visit, new patient, low", medicare: 112, bcbs: 124, aetna: 98, uhc: 115 },
  { cpt: "93000", desc: "ECG interpretation only", medicare: 12, bcbs: 14, aetna: 10, uhc: 13 },
  { cpt: "93350", desc: "Stress echocardiogram", medicare: 145, bcbs: 162, aetna: 128, uhc: 148 },
  { cpt: "71046", desc: "Chest X-ray, 2 views", medicare: 28, bcbs: 32, aetna: 24, uhc: 29 },
  { cpt: "36415", desc: "Venipuncture", medicare: 3, bcbs: 4, aetna: 3, uhc: 3 },
  { cpt: "80053", desc: "Comprehensive metabolic panel", medicare: 11, bcbs: 14, aetna: 10, uhc: 12 },
  { cpt: "85025", desc: "CBC with differential", medicare: 8, bcbs: 10, aetna: 7, uhc: 9 },
  { cpt: "99395", desc: "Preventive visit, 18-39", medicare: 145, bcbs: 158, aetna: 130, uhc: 148 },
  { cpt: "99396", desc: "Preventive visit, 40-64", medicare: 155, bcbs: 170, aetna: 140, uhc: 160 },
  { cpt: "93000", desc: "ECG, complete", medicare: 30, bcbs: 36, aetna: 25, uhc: 32 },
];

// Revenue gap detail for Aetna
const AETNA_GAP_DETAIL = [
  { cpt: "99214", desc: "Office visit, est. moderate", volume: 420, yourRate: 118, medicare: 128, gap: 4200 },
  { cpt: "99213", desc: "Office visit, est. low", volume: 310, yourRate: 89, medicare: 98, gap: 2790 },
  { cpt: "99215", desc: "Office visit, est. high", volume: 85, yourRate: 155, medicare: 172, gap: 1445 },
  { cpt: "93306", desc: "Echo, complete", volume: 60, yourRate: 165, medicare: 185, gap: 1200 },
  { cpt: "99203", desc: "Office visit, new low", volume: 95, yourRate: 98, medicare: 112, gap: 1330 },
];

const RECOVERY_MONTHS = [
  { month: "Oct 2025", denied: 32, appealed: 18, won: 5, recovered: 4200 },
  { month: "Nov 2025", denied: 28, appealed: 22, won: 11, recovered: 12800 },
  { month: "Dec 2025", denied: 25, appealed: 24, won: 15, recovered: 17400 },
];

const SAMPLE_APPEAL = {
  claimNumber: "UHC-2025-8847291",
  patientDOB: "03/15/1958",
  dateOfService: "09/12/2025",
  cpt: "93306",
  billedAmount: 190,
  denialReason: "CO-50: Medical necessity not established. The requested service does not meet the plan's medical necessity criteria based on the submitted documentation.",
  analyticalPaths: [
    {
      choice: "UHC applied a frequency limit of 1 echocardiogram per 90 days",
      finding: "The prior echocardiogram was performed on 06/08/2025 \u2014 96 days prior to this service. The frequency limit was technically met.",
    },
    {
      choice: "Override for clinical change was not recognized",
      finding: "The patient's medical record documents new onset dyspnea on exertion and a 15-point decrease in ejection fraction noted on physical exam, constituting a significant change in clinical status.",
    },
    {
      choice: "Documentation of clinical change was present but not in the expected structured data field",
      finding: "The clinical change was documented in the progress note narrative but was not captured in the structured reason-for-study field on the order. UHC's automated review system processes only structured fields.",
    },
  ],
  appealLetter: `RE: Appeal of Denied Claim UHC-2025-8847291
CPT 93306 — Complete Echocardiogram
Date of Service: September 12, 2025
Patient DOB: 03/15/1958
Billed Amount: $190.00

Dear UnitedHealthcare Claims Review Department,

I am writing to appeal the denial of the above-referenced claim under reason code CO-50 (Medical necessity not established).

DENIAL ANALYSIS

This denial was based on UHC's frequency limitation policy, which restricts echocardiograms to one per 90-day period absent documented clinical change. However, this denial should be overturned for the following reasons:

1. FREQUENCY LIMIT WAS MET: The prior echocardiogram was performed on June 8, 2025 — 96 days before the September 12 study. The 90-day frequency limit was satisfied.

2. CLINICAL CHANGE WAS DOCUMENTED: The patient presented with new onset dyspnea on exertion beginning approximately 3 weeks prior to the study. Physical examination revealed a new S3 gallop and bilateral lower extremity edema. These findings represent a significant change in clinical status warranting repeat echocardiographic evaluation.

3. APPROPRIATE USE CRITERIA SUPPORT: Per the ACC/AHA 2024 Appropriate Use Criteria for Echocardiography, repeat echocardiography is rated as "Appropriate" (Score 7-9) when there is "a change in clinical status or cardiac examination suggesting a change in cardiac structure or function" (Indication #14).

The documentation supporting this clinical change was present in the visit progress note dated September 12, 2025. We have attached the relevant progress note and prior echocardiogram report for your review.

We respectfully request that this claim be reprocessed and paid at the contracted rate of $190.00.

Sincerely,
[Physician Name], MD
Lakeside Internal Medicine & Cardiology
NPI: [Practice NPI]`,
  successRate: "This appeal addresses the actual analytical logic behind the denial, not just the outcome. Generic appeals succeed ~30% of the time. Targeted appeals succeed ~65% of the time.",
};

// ---------------------------------------------------------------------------
// Screens
// ---------------------------------------------------------------------------

const TABS = [
  "Practice Overview",
  "Contract Benchmarking",
  "Denial Intelligence",
  "Sample Appeal",
  "Revenue Recovery",
];

export default function ProviderDemoPage() {
  const [tab, setTab] = useState(0);
  const [selectedPayer, setSelectedPayer] = useState(1); // default Aetna
  const [selectedDenialPayer, setSelectedDenialPayer] = useState(2); // default UHC
  const [expandedPath, setExpandedPath] = useState(null);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a1628",
        color: "#e2e8f0",
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap"
        rel="stylesheet"
      />

      {/* Demo banner */}
      <div
        style={{
          background: "rgba(59,130,246,0.15)",
          borderBottom: "1px solid rgba(59,130,246,0.25)",
          padding: "10px 20px",
          textAlign: "center",
          fontSize: "13px",
          color: "#93c5fd",
        }}
      >
        You're viewing a demo with sample data from a fictional practice.{" "}
        <Link
          to="/billing/provider"
          style={{ color: "#60a5fa", fontWeight: "600", textDecoration: "none" }}
        >
          Learn more &rarr;
        </Link>
        {" "}&middot;{" "}
        <Link
          to="/employer/login"
          style={{ color: "#60a5fa", fontWeight: "600", textDecoration: "none" }}
        >
          Sign up for access &rarr;
        </Link>
      </div>

      {/* Header */}
      <header
        style={{
          padding: "16px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Link
            to="/"
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #0d9488, #14b8a6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "16px",
              fontWeight: "700",
              color: "#0a1628",
              textDecoration: "none",
            }}
          >
            C
          </Link>
          <span style={{ fontWeight: "600", fontSize: "16px" }}>Parity Provider</span>
          <span
            style={{
              background: "rgba(59,130,246,0.15)",
              color: "#60a5fa",
              fontSize: "11px",
              fontWeight: "600",
              padding: "3px 8px",
              borderRadius: "4px",
              textTransform: "uppercase",
            }}
          >
            Demo
          </span>
        </div>
        <div style={{ fontSize: "13px", color: "#64748b" }}>
          {PRACTICE.name} &middot; {PRACTICE.physDesc}
        </div>
      </header>

      {/* Tab navigation */}
      <nav
        style={{
          display: "flex",
          gap: "0",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          padding: "0 24px",
          overflowX: "auto",
        }}
      >
        {TABS.map((t, i) => (
          <button
            key={t}
            onClick={() => setTab(i)}
            style={{
              padding: "14px 18px",
              fontSize: "13px",
              fontWeight: tab === i ? "600" : "400",
              color: tab === i ? "#60a5fa" : "#64748b",
              borderBottom: tab === i ? "2px solid #3b82f6" : "2px solid transparent",
              background: "none",
              border: "none",
              cursor: "pointer",
              whiteSpace: "nowrap",
              transition: "color 0.2s",
              fontFamily: "inherit",
            }}
          >
            {t}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ padding: "32px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        {tab === 0 && <PracticeOverview onDrillPayer={(i) => { setSelectedPayer(i); setTab(1); }} />}
        {tab === 1 && (
          <ContractBenchmarking
            payerIndex={selectedPayer}
            onSelectPayer={setSelectedPayer}
          />
        )}
        {tab === 2 && (
          <DenialIntelligence
            payerIndex={selectedDenialPayer}
            onSelectPayer={setSelectedDenialPayer}
            onViewAppeal={() => setTab(3)}
          />
        )}
        {tab === 3 && (
          <SampleAppeal
            expandedPath={expandedPath}
            onTogglePath={(i) => setExpandedPath(expandedPath === i ? null : i)}
          />
        )}
        {tab === 4 && <RevenueRecovery />}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 1: Practice Overview
// ---------------------------------------------------------------------------

function PracticeOverview({ onDrillPayer }) {
  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "28px" }}>Practice Overview</h2>

      {/* Top stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <StatCard label="Annual Revenue" value={fmt(PRACTICE.annualRevenue)} />
        <StatCard label="Revenue Gap" value={fmt(PRACTICE.revenueGap)} sub="Contract shortfalls" accent />
        <StatCard
          label="Denial Rate"
          value={`${PRACTICE.denialRate}%`}
          sub={`Benchmark: ${PRACTICE.denialBenchmark}`}
          accent
        />
        <StatCard label="Denied Revenue" value={fmt(PRACTICE.deniedRevenue)} sub="At risk" />
        <StatCard
          label="Total Recovery"
          value={fmt(PRACTICE.totalRecovery)}
          sub="Opportunity"
          accent
        />
      </div>

      {/* Payer performance cards */}
      <h3 style={{ ...h3Style, marginBottom: "16px" }}>Payer Performance</h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "16px",
        }}
      >
        {PAYERS.map((p, i) => (
          <div
            key={p.name}
            style={{
              ...cardStyle,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onClick={() => onDrillPayer(i)}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(59,130,246,0.3)";
              e.currentTarget.style.background = "rgba(59,130,246,0.04)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)";
              e.currentTarget.style.background = "rgba(255,255,255,0.02)";
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "12px",
              }}
            >
              <span style={{ fontSize: "16px", fontWeight: "600", color: "#e2e8f0" }}>
                {p.name}
              </span>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: "600",
                  padding: "3px 10px",
                  borderRadius: "10px",
                  background: statusBg(p.status),
                  color: statusColor(p.status),
                }}
              >
                {p.statusLabel}
              </span>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "12px",
                fontSize: "13px",
              }}
            >
              <div>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "2px" }}>
                  Rates vs Medicare
                </div>
                <div
                  style={{
                    fontWeight: "600",
                    color: p.avgVsMedicare > 0 ? "#4ade80" : "#f87171",
                  }}
                >
                  {p.avgVsMedicare > 0 ? "+" : ""}{p.avgVsMedicare}% avg
                </div>
              </div>
              <div>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "2px" }}>
                  Denial Rate
                </div>
                <div
                  style={{
                    fontWeight: "600",
                    color: p.denialRate > 10 ? "#f87171" : p.denialRate > 7 ? "#fbbf24" : "#4ade80",
                  }}
                >
                  {p.denialRate}%
                </div>
              </div>
              <div>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "2px" }}>
                  Revenue Gap
                </div>
                <div style={{ fontWeight: "600", color: p.revenueGap > 0 ? "#f87171" : "#4ade80" }}>
                  {p.revenueGap > 0 ? fmt(p.revenueGap) : "\u2014"}
                </div>
              </div>
              <div>
                <div style={{ color: "#64748b", fontSize: "11px", marginBottom: "2px" }}>
                  Denials
                </div>
                <div style={{ fontWeight: "600" }}>
                  {p.denials}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 2: Contract Benchmarking
// ---------------------------------------------------------------------------

function ContractBenchmarking({ payerIndex, onSelectPayer }) {
  const payer = PAYERS[payerIndex];

  return (
    <div>
      {/* Payer selector */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "28px" }}>
        {PAYERS.map((p, i) => (
          <button
            key={p.name}
            onClick={() => onSelectPayer(i)}
            style={{
              padding: "6px 14px",
              fontSize: "12px",
              fontWeight: i === payerIndex ? "600" : "400",
              background: i === payerIndex ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.04)",
              color: i === payerIndex ? "#60a5fa" : "#94a3b8",
              border: `1px solid ${i === payerIndex ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.08)"}`,
              borderRadius: "6px",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            {p.short}
          </button>
        ))}
      </div>

      <h2 style={{ ...h2Style, marginBottom: "8px" }}>
        {payer.name} Contract Rates
      </h2>
      <p style={{ fontSize: "14px", color: "#64748b", marginBottom: "28px" }}>
        CPT-by-CPT comparison against Medicare and other payers.
      </p>

      {/* Rate comparison table */}
      <div style={cardStyle}>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>CPT</th>
                <th style={thStyle}>Description</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Medicare</th>
                <th style={{ ...thStyle, textAlign: "right" }}>BCBS</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Aetna</th>
                <th style={{ ...thStyle, textAlign: "right" }}>UHC</th>
              </tr>
            </thead>
            <tbody>
              {FEE_SCHEDULE.slice(0, 8).map((row, idx) => (
                <tr key={idx}>
                  <td style={{ ...tdStyle, fontFamily: "monospace", color: "#60a5fa" }}>{row.cpt}</td>
                  <td style={tdStyle}>{row.desc}</td>
                  <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>${row.medicare}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>
                    <RateCell rate={row.bcbs} benchmark={row.medicare} />
                  </td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>
                    <RateCell rate={row.aetna} benchmark={row.medicare} />
                  </td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>
                    <RateCell rate={row.uhc} benchmark={row.medicare} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Revenue gap detail — only for Aetna */}
      {payerIndex === 1 && (
        <div style={{ marginTop: "28px" }}>
          <div
            style={{
              ...cardStyle,
              background: "rgba(239,68,68,0.04)",
              borderColor: "rgba(239,68,68,0.15)",
            }}
          >
            <h3 style={h3Style}>Revenue Gap: Aetna \u2014 ${(127000).toLocaleString()}</h3>
            <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>
              Aetna pays 8\u201311% below Medicare across E&M codes. Top 5 codes driving the gap:
            </p>
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>CPT</th>
                    <th style={thStyle}>Description</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Volume</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Your Rate</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Medicare</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Annual Gap</th>
                  </tr>
                </thead>
                <tbody>
                  {AETNA_GAP_DETAIL.map((row) => (
                    <tr key={row.cpt}>
                      <td style={{ ...tdStyle, fontFamily: "monospace", color: "#60a5fa" }}>{row.cpt}</td>
                      <td style={tdStyle}>{row.desc}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>{row.volume}</td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#f87171" }}>${row.yourRate}</td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>${row.medicare}</td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#f87171", fontWeight: "600" }}>
                        ${row.gap.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Negotiation brief */}
          <div
            style={{
              ...cardStyle,
              marginTop: "16px",
              background: "rgba(59,130,246,0.04)",
              borderColor: "rgba(59,130,246,0.15)",
            }}
          >
            <h4 style={{ fontSize: "14px", fontWeight: "600", color: "#60a5fa", marginBottom: "8px" }}>
              Negotiation Brief Preview
            </h4>
            <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.7" }}>
              Your Aetna contract rates for E&M codes are systematically 8\u201311% below the
              2026 Medicare Fee Schedule. CPT 99214 alone accounts for $42K of the $127K
              annual gap across 420 encounters. A rate adjustment to Medicare parity on
              your top 5 E&M codes would recover $127K annually with no change in volume
              or practice patterns.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function RateCell({ rate, benchmark }) {
  const pct = Math.round(((rate - benchmark) / benchmark) * 100);
  const color = pct > 0 ? "#4ade80" : pct < -5 ? "#f87171" : "#fbbf24";
  return (
    <span>
      ${rate}{" "}
      <span style={{ fontSize: "11px", color }}>
        ({pct > 0 ? "+" : ""}{pct}%)
      </span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Screen 3: Denial Intelligence
// ---------------------------------------------------------------------------

function DenialIntelligence({ payerIndex, onSelectPayer, onViewAppeal }) {
  const payer = PAYERS[payerIndex];

  return (
    <div>
      {/* Payer selector */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "28px" }}>
        {PAYERS.map((p, i) => (
          <button
            key={p.name}
            onClick={() => onSelectPayer(i)}
            style={{
              padding: "6px 14px",
              fontSize: "12px",
              fontWeight: i === payerIndex ? "600" : "400",
              background: i === payerIndex ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.04)",
              color: i === payerIndex ? "#60a5fa" : "#94a3b8",
              border: `1px solid ${i === payerIndex ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.08)"}`,
              borderRadius: "6px",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            {p.short}
          </button>
        ))}
      </div>

      <h2 style={{ ...h2Style, marginBottom: "8px" }}>
        Denial Patterns: {payer.name}
      </h2>
      <div style={{ display: "flex", gap: "24px", fontSize: "13px", color: "#64748b", marginBottom: "28px", flexWrap: "wrap" }}>
        <span>Denial Rate: <strong style={{ color: payer.denialRate > 10 ? "#f87171" : "#fbbf24" }}>{payer.denialRate}%</strong></span>
        <span>Total Denials: <strong style={{ color: "#e2e8f0" }}>{payer.denials}</strong></span>
        <span>Benchmark: <strong style={{ color: "#4ade80" }}>5\u201310%</strong></span>
      </div>

      {/* Denial patterns */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Denial Breakdown</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {payer.denialPatterns.map((d, i) => {
            const pct = Math.round((d.count / payer.denials) * 100);
            return (
              <div key={i}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontSize: "13px" }}>
                  <span style={{ color: "#e2e8f0" }}>{d.reason}</span>
                  <span style={{ color: "#94a3b8" }}>
                    {d.count} ({pct}%)
                  </span>
                </div>
                <div
                  style={{
                    height: "8px",
                    background: "rgba(255,255,255,0.04)",
                    borderRadius: "4px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${pct}%`,
                      background: pct > 30 ? "rgba(239,68,68,0.6)" : "rgba(251,191,36,0.6)",
                      borderRadius: "4px",
                    }}
                  />
                </div>
                <div style={{ fontSize: "11px", color: "#475569", marginTop: "2px" }}>
                  Reason code: {d.reasonCode}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Root cause analysis — show for UHC echocardiogram denials */}
      {payerIndex === 2 && (
        <div style={{ marginTop: "24px" }}>
          <div
            style={{
              ...cardStyle,
              background: "rgba(239,68,68,0.04)",
              borderColor: "rgba(239,68,68,0.15)",
            }}
          >
            <h3 style={{ ...h3Style, color: "#f87171" }}>Root Cause Analysis: Echo Denials (CPT 93306)</h3>
            <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.7", marginBottom: "20px" }}>
              12 denials, same reason code (CO-50), same CPT code, spanning 6 months. UHC is
              applying a medical necessity algorithm that requires a documented change in
              clinical status within 90 days of the prior echocardiogram.{" "}
              <strong style={{ color: "#fbbf24" }}>
                9 of 12 denied claims had a documented change
              </strong>{" "}
              — the denial appears to be systematic, not case-by-case.
            </p>

            {/* Analytical Paths */}
            <h4 style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa", marginBottom: "12px" }}>
              Analytical Paths Breakdown
            </h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "20px" }}>
              {SAMPLE_APPEAL.analyticalPaths.map((ap, i) => (
                <div
                  key={i}
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "8px",
                    padding: "14px 16px",
                  }}
                >
                  <div style={{ fontSize: "11px", fontWeight: "600", color: "#60a5fa", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
                    Choice {i + 1}
                  </div>
                  <div style={{ fontSize: "13px", color: "#e2e8f0", marginBottom: "6px" }}>
                    {ap.choice}
                  </div>
                  <div style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.6" }}>
                    {ap.finding}
                  </div>
                </div>
              ))}
            </div>

            <div
              style={{
                background: "rgba(34,197,94,0.06)",
                border: "1px solid rgba(34,197,94,0.2)",
                borderRadius: "8px",
                padding: "14px 16px",
              }}
            >
              <div style={{ fontSize: "11px", fontWeight: "600", color: "#4ade80", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
                Suggested Appeal Strategy
              </div>
              <p style={{ fontSize: "13px", color: "#cbd5e1", lineHeight: "1.6" }}>
                Challenge the frequency limit application by citing the documented clinical
                changes. Reference ACC/AHA Appropriate Use Criteria for repeat
                echocardiography. Target all 9 claims with documented changes for batch appeal.
              </p>
            </div>

            <button
              onClick={onViewAppeal}
              style={{
                marginTop: "16px",
                padding: "10px 24px",
                fontSize: "13px",
                fontWeight: "600",
                background: "#3b82f6",
                color: "#fff",
                border: "none",
                borderRadius: "8px",
                cursor: "pointer",
                fontFamily: "inherit",
                transition: "background 0.2s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#2563eb")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "#3b82f6")}
            >
              View Sample Appeal Letter &rarr;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 4: Sample Denial Appeal
// ---------------------------------------------------------------------------

function SampleAppeal({ expandedPath, onTogglePath }) {
  const a = SAMPLE_APPEAL;

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "28px" }}>Sample Denial Appeal</h2>

      {/* Claim details */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "16px",
          marginBottom: "28px",
        }}
      >
        <StatCard label="Claim Number" value={a.claimNumber} small />
        <StatCard label="CPT Code" value={a.cpt} small />
        <StatCard label="Date of Service" value={a.dateOfService} small />
        <StatCard label="Billed Amount" value={`$${a.billedAmount}`} small />
      </div>

      {/* Denial reason */}
      <div
        style={{
          ...cardStyle,
          background: "rgba(239,68,68,0.04)",
          borderColor: "rgba(239,68,68,0.15)",
          marginBottom: "24px",
        }}
      >
        <div style={{ fontSize: "11px", fontWeight: "600", color: "#f87171", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" }}>
          Denial Reason
        </div>
        <p style={{ fontSize: "14px", color: "#e2e8f0", lineHeight: "1.6" }}>
          {a.denialReason}
        </p>
      </div>

      {/* Analytical Paths */}
      <div style={{ ...cardStyle, marginBottom: "24px" }}>
        <h3 style={{ ...h3Style, color: "#60a5fa" }}>Analytical Paths Analysis</h3>
        <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px", lineHeight: "1.6" }}>
          Each "choice" represents a specific analytical decision the payer made when processing this claim.
          The appeal challenges each decision with documented evidence.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {a.analyticalPaths.map((ap, i) => (
            <div
              key={i}
              style={{
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: "8px",
                overflow: "hidden",
              }}
            >
              <div
                onClick={() => onTogglePath(i)}
                style={{
                  padding: "14px 16px",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  cursor: "pointer",
                  background: expandedPath === i ? "rgba(59,130,246,0.06)" : "rgba(255,255,255,0.02)",
                }}
              >
                <div>
                  <span style={{ fontSize: "11px", fontWeight: "600", color: "#60a5fa", marginRight: "8px" }}>
                    CHOICE {i + 1}
                  </span>
                  <span style={{ fontSize: "13px", color: "#e2e8f0" }}>{ap.choice}</span>
                </div>
                <span style={{ color: "#64748b", fontSize: "18px" }}>
                  {expandedPath === i ? "\u2212" : "+"}
                </span>
              </div>
              {expandedPath === i && (
                <div
                  style={{
                    padding: "14px 16px",
                    borderTop: "1px solid rgba(255,255,255,0.06)",
                    background: "rgba(255,255,255,0.01)",
                  }}
                >
                  <div style={{ fontSize: "11px", fontWeight: "600", color: "#4ade80", marginBottom: "6px" }}>
                    FINDING
                  </div>
                  <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.6" }}>
                    {ap.finding}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Appeal letter */}
      <div style={cardStyle}>
        <h3 style={{ ...h3Style, color: "#4ade80" }}>Generated Appeal Letter</h3>
        <div
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: "8px",
            padding: "24px",
            fontFamily: "'DM Sans', monospace",
            fontSize: "13px",
            lineHeight: "1.8",
            color: "#cbd5e1",
            whiteSpace: "pre-wrap",
          }}
        >
          {a.appealLetter}
        </div>
        <div
          style={{
            marginTop: "16px",
            background: "rgba(59,130,246,0.06)",
            border: "1px solid rgba(59,130,246,0.15)",
            borderRadius: "8px",
            padding: "14px 16px",
          }}
        >
          <p style={{ fontSize: "13px", color: "#93c5fd", lineHeight: "1.6" }}>
            {a.successRate}
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 5: Revenue Recovery
// ---------------------------------------------------------------------------

function RevenueRecovery() {
  const totalRecovered = RECOVERY_MONTHS.reduce((s, m) => s + m.recovered, 0);
  const totalAppealed = RECOVERY_MONTHS.reduce((s, m) => s + m.appealed, 0);
  const totalWon = RECOVERY_MONTHS.reduce((s, m) => s + m.won, 0);
  const overturnRate = Math.round((totalWon / totalAppealed) * 100);

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "28px" }}>Revenue Recovery Tracker</h2>

      {/* Summary stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <StatCard label="Total Recovered" value={fmt(totalRecovered)} accent />
        <StatCard label="Appeals Sent" value={String(totalAppealed)} />
        <StatCard label="Appeals Won" value={String(totalWon)} />
        <StatCard label="Overturn Rate" value={`${overturnRate}%`} accent />
      </div>

      {/* Monthly chart */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Monthly Recovery (3-month pilot)</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Month</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Denials</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Appeals Sent</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Appeals Won</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Overturn Rate</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Recovered</th>
              </tr>
            </thead>
            <tbody>
              {RECOVERY_MONTHS.map((m) => {
                const rate = m.appealed > 0 ? Math.round((m.won / m.appealed) * 100) : 0;
                return (
                  <tr key={m.month}>
                    <td style={tdStyle}>{m.month}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{m.denied}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{m.appealed}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#4ade80" }}>{m.won}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: rate > 50 ? "#4ade80" : "#fbbf24" }}>
                      {rate}%
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600", color: "#4ade80" }}>
                      {fmt(m.recovered)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Visual bars */}
        <div style={{ marginTop: "24px" }}>
          {RECOVERY_MONTHS.map((m) => {
            const maxDenied = Math.max(...RECOVERY_MONTHS.map((x) => x.denied));
            return (
              <div key={m.month} style={{ marginBottom: "12px" }}>
                <div style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "4px" }}>{m.month}</div>
                <div style={{ display: "flex", gap: "4px", height: "14px" }}>
                  <div
                    style={{
                      width: `${(m.denied / maxDenied) * 100}%`,
                      background: "rgba(239,68,68,0.4)",
                      borderRadius: "3px",
                    }}
                    title={`${m.denied} denials`}
                  />
                  <div
                    style={{
                      width: `${(m.appealed / maxDenied) * 100}%`,
                      background: "rgba(59,130,246,0.5)",
                      borderRadius: "3px",
                    }}
                    title={`${m.appealed} appealed`}
                  />
                  <div
                    style={{
                      width: `${(m.won / maxDenied) * 100}%`,
                      background: "rgba(34,197,94,0.6)",
                      borderRadius: "3px",
                    }}
                    title={`${m.won} won`}
                  />
                </div>
              </div>
            );
          })}
          <div style={{ display: "flex", gap: "16px", fontSize: "11px", color: "#64748b", marginTop: "8px" }}>
            <span><span style={{ display: "inline-block", width: "10px", height: "10px", background: "rgba(239,68,68,0.5)", borderRadius: "2px", marginRight: "4px" }} />Denials</span>
            <span><span style={{ display: "inline-block", width: "10px", height: "10px", background: "rgba(59,130,246,0.5)", borderRadius: "2px", marginRight: "4px" }} />Appealed</span>
            <span><span style={{ display: "inline-block", width: "10px", height: "10px", background: "rgba(34,197,94,0.6)", borderRadius: "2px", marginRight: "4px" }} />Won</span>
          </div>
        </div>
      </div>

      {/* Improvement callout */}
      <div
        style={{
          marginTop: "24px",
          background: "rgba(34,197,94,0.06)",
          border: "1px solid rgba(34,197,94,0.2)",
          borderRadius: "12px",
          padding: "24px",
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: "15px", color: "#cbd5e1", lineHeight: "1.7" }}>
          Since implementing targeted appeals: denial overturn rate improved from{" "}
          <strong style={{ color: "#fbbf24" }}>28%</strong> to{" "}
          <strong style={{ color: "#4ade80" }}>62%</strong>, recovering{" "}
          <strong style={{ color: "#4ade80" }}>{fmt(totalRecovered)}</strong>{" "}
          in previously lost revenue over 3 months.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

function StatCard({ label, value, accent, sub, small }) {
  return (
    <div
      style={{
        background: accent ? "rgba(59,130,246,0.08)" : "rgba(255,255,255,0.03)",
        border: `1px solid ${accent ? "rgba(59,130,246,0.25)" : "rgba(255,255,255,0.06)"}`,
        borderRadius: "12px",
        padding: small ? "14px" : "20px",
      }}
    >
      <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
        {label}
      </div>
      <div style={{ fontSize: small ? "15px" : "22px", fontWeight: "700", color: accent ? "#60a5fa" : "#f1f5f9", wordBreak: "break-all" }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>{sub}</div>}
    </div>
  );
}

function statusBg(s) {
  if (s === "good") return "rgba(34,197,94,0.15)";
  if (s === "warning") return "rgba(251,191,36,0.15)";
  return "rgba(239,68,68,0.15)";
}

function statusColor(s) {
  if (s === "good") return "#4ade80";
  if (s === "warning") return "#fbbf24";
  return "#f87171";
}

function fmt(n) {
  if (typeof n === "string") return n;
  if (n >= 1000000) return "$" + (n / 1000000).toFixed(1) + "M";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
}

const h2Style = {
  fontFamily: "'DM Serif Display', serif",
  fontSize: "24px",
  fontWeight: "400",
  color: "#f1f5f9",
};

const h3Style = {
  fontSize: "15px",
  fontWeight: "600",
  color: "#e2e8f0",
  marginBottom: "16px",
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
  textAlign: "left",
  padding: "8px 12px 8px 0",
  fontSize: "11px",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  borderBottom: "1px solid rgba(255,255,255,0.06)",
};

const tdStyle = {
  padding: "10px 12px 10px 0",
  color: "#e2e8f0",
  borderBottom: "1px solid rgba(255,255,255,0.04)",
};
