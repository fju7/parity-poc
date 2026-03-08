import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";

// Module-level flag persists across unmount/remount so animation only plays once
let gsAnimationPlayed = false;

// ---------------------------------------------------------------------------
// Sample data — Midwest Manufacturing Co.
// ---------------------------------------------------------------------------

const COMPANY = {
  name: "Midwest Manufacturing Co.",
  lives: 500,
  tpa: "Cigna",
  planType: "PPO",
  planYear: "2025",
  state: "Illinois",
  industry: "Manufacturing",
  totalSpend: 7480000,
  benchmarkSpend: 6100000,
  potentialSavings: 1380000,
  savingsPercent: 18.4,
};

const CATEGORIES = [
  {
    name: "Primary Care",
    spend: 1800000,
    benchmark: 1890000,
    variance: -5,
    providers: 12,
    claims: 340,
    status: "good",
    procedures: [
      { cpt: "99214", desc: "Office visit, est. patient, moderate", avgCost: 148, benchmark: 155, claims: 120 },
      { cpt: "99213", desc: "Office visit, est. patient, low", avgCost: 105, benchmark: 110, claims: 95 },
      { cpt: "99215", desc: "Office visit, est. patient, high", avgCost: 195, benchmark: 205, claims: 45 },
      { cpt: "99395", desc: "Preventive visit, 18-39", avgCost: 210, benchmark: 225, claims: 42 },
      { cpt: "99396", desc: "Preventive visit, 40-64", avgCost: 240, benchmark: 250, claims: 38 },
    ],
    topProviders: [
      { name: "Heartland Family Medicine", claims: 120, avgCost: 142, benchmark: 155, variance: -8 },
      { name: "Prairie Health Group", claims: 95, avgCost: 148, benchmark: 155, variance: -5 },
      { name: "Midwest Primary Partners", claims: 65, avgCost: 158, benchmark: 155, variance: 2 },
    ],
  },
  {
    name: "Orthopedics",
    spend: 1200000,
    benchmark: 870000,
    variance: 38,
    providers: 3,
    claims: 45,
    status: "critical",
    procedures: [
      { cpt: "27447", desc: "Total knee arthroplasty", avgCost: 4200, benchmark: 3050, claims: 8 },
      { cpt: "27130", desc: "Total hip arthroplasty", avgCost: 3800, benchmark: 2900, claims: 5 },
      { cpt: "29881", desc: "Knee arthroscopy w/ meniscectomy", avgCost: 1950, benchmark: 1400, claims: 12 },
      { cpt: "22551", desc: "Anterior cervical discectomy", avgCost: 5100, benchmark: 3800, claims: 4 },
      { cpt: "20610", desc: "Joint injection, major joint", avgCost: 280, benchmark: 195, claims: 16 },
    ],
    topProviders: [
      { name: "Lakeview Orthopedics", claims: 22, avgCost: 3150, benchmark: 2280, variance: 38 },
      { name: "Midwest Ortho Associates", claims: 15, avgCost: 2350, benchmark: 2280, variance: 3 },
      { name: "Dr. James Orthton", claims: 8, avgCost: 4200, benchmark: 3050, variance: 38 },
    ],
  },
  {
    name: "Cardiology",
    spend: 890000,
    benchmark: 795000,
    variance: 12,
    providers: 4,
    claims: 62,
    status: "warning",
    procedures: [
      { cpt: "93306", desc: "Echocardiogram, complete", avgCost: 420, benchmark: 380, claims: 18 },
      { cpt: "93000", desc: "ECG, 12-lead", avgCost: 85, benchmark: 72, claims: 45 },
      { cpt: "75571", desc: "Cardiac CT, calcium scoring", avgCost: 310, benchmark: 245, claims: 12 },
      { cpt: "93350", desc: "Stress echocardiogram", avgCost: 680, benchmark: 520, claims: 8 },
      { cpt: "75574", desc: "Cardiac MRI", avgCost: 2100, benchmark: 1400, claims: 6 },
    ],
    topProviders: [
      { name: "Heartland Cardiology", claims: 28, avgCost: 520, benchmark: 420, variance: 24 },
      { name: "Prairie Heart Institute", claims: 20, avgCost: 380, benchmark: 380, variance: 0 },
      { name: "Midwest Cardiovascular", claims: 14, avgCost: 410, benchmark: 420, variance: -2 },
    ],
  },
  {
    name: "Imaging / Radiology",
    spend: 650000,
    benchmark: 508000,
    variance: 28,
    providers: 6,
    claims: 85,
    status: "critical",
    procedures: [
      { cpt: "70553", desc: "MRI brain w/ & w/o contrast", avgCost: 1800, benchmark: 650, claims: 15 },
      { cpt: "72148", desc: "MRI lumbar spine w/o contrast", avgCost: 1650, benchmark: 580, claims: 18 },
      { cpt: "74177", desc: "CT abdomen/pelvis w/ contrast", avgCost: 950, benchmark: 420, claims: 22 },
      { cpt: "71046", desc: "Chest X-ray, 2 views", avgCost: 180, benchmark: 95, claims: 30 },
    ],
    topProviders: [
      { name: "Regional Hospital Imaging", claims: 35, avgCost: 1420, benchmark: 580, variance: 145 },
      { name: "ClearScan Imaging Center", claims: 30, avgCost: 520, benchmark: 580, variance: -10 },
      { name: "University Radiology", claims: 20, avgCost: 890, benchmark: 580, variance: 53 },
    ],
  },
  {
    name: "Pharmacy (Medical)",
    spend: 830000,
    benchmark: 722000,
    variance: 15,
    providers: 5,
    claims: 48,
    status: "warning",
    procedures: [
      { cpt: "96413", desc: "Chemo IV infusion, first hour", avgCost: 890, benchmark: 680, claims: 12 },
      { cpt: "96365", desc: "IV infusion, therapeutic, first hour", avgCost: 420, benchmark: 340, claims: 18 },
      { cpt: "J1745", desc: "Infliximab injection", avgCost: 4200, benchmark: 3600, claims: 8 },
    ],
    topProviders: [
      { name: "Regional Hospital Infusion", claims: 22, avgCost: 2800, benchmark: 2100, variance: 33 },
      { name: "HomeCare Infusion Services", claims: 16, avgCost: 1950, benchmark: 2100, variance: -7 },
    ],
  },
  {
    name: "Emergency",
    spend: 420000,
    benchmark: 344000,
    variance: 22,
    providers: 8,
    claims: 28,
    status: "warning",
    procedures: [
      { cpt: "99285", desc: "ED visit, high complexity", avgCost: 1850, benchmark: 1350, claims: 8 },
      { cpt: "99284", desc: "ED visit, high urgency", avgCost: 980, benchmark: 780, claims: 12 },
      { cpt: "99283", desc: "ED visit, moderate", avgCost: 580, benchmark: 450, claims: 8 },
    ],
    topProviders: [
      { name: "St. Francis ER (OON)", claims: 3, avgCost: 4200, benchmark: 1350, variance: 211 },
      { name: "Regional Medical ER", claims: 18, avgCost: 920, benchmark: 780, variance: 18 },
    ],
  },
  {
    name: "Lab / Pathology",
    spend: 380000,
    benchmark: 352000,
    variance: 8,
    providers: 4,
    claims: 120,
    status: "ok",
    procedures: [
      { cpt: "80053", desc: "Comprehensive metabolic panel", avgCost: 48, benchmark: 42, claims: 45 },
      { cpt: "85025", desc: "CBC with differential", avgCost: 28, benchmark: 24, claims: 55 },
      { cpt: "81001", desc: "Urinalysis, automated", avgCost: 18, benchmark: 14, claims: 20 },
    ],
    topProviders: [
      { name: "Quest Diagnostics", claims: 65, avgCost: 32, benchmark: 30, variance: 7 },
      { name: "Regional Hospital Lab", claims: 40, avgCost: 52, benchmark: 42, variance: 24 },
    ],
  },
  {
    name: "Behavioral Health",
    spend: 310000,
    benchmark: 316000,
    variance: -2,
    providers: 6,
    claims: 85,
    status: "good",
    procedures: [
      { cpt: "90834", desc: "Psychotherapy, 45 min", avgCost: 125, benchmark: 128, claims: 50 },
      { cpt: "90837", desc: "Psychotherapy, 60 min", avgCost: 165, benchmark: 170, claims: 25 },
      { cpt: "99213", desc: "Psych med management", avgCost: 105, benchmark: 110, claims: 10 },
    ],
    topProviders: [
      { name: "Clarity Behavioral Health", claims: 40, avgCost: 130, benchmark: 128, variance: 2 },
      { name: "Midwest Counseling Group", claims: 30, avgCost: 118, benchmark: 128, variance: -8 },
    ],
  },
];

// ---------------------------------------------------------------------------
// Benchmark data (Tab 2)
// ---------------------------------------------------------------------------

const BENCHMARK = {
  companyPEPM: 1246,
  industryMedianPEPM: 896,
  percentile: 71,
  dollarGapPEPM: 350,
  dollarGapAnnual: 2100000,
  costDrivers: [
    "Specialty prescription drugs (including GLP-1 weight loss medications)",
    "Outpatient orthopedic surgery",
    "Outpatient imaging (MRI, CT scans)",
  ],
  dataSources: [
    "MEPS-IC 2024 \u00b7 50 States",
    "KFF EHBS 2025 \u00b7 1,862 Employers",
    "BLS ECEC 2024",
  ],
};

// ---------------------------------------------------------------------------
// Claims spot check data (Tab 3)
// ---------------------------------------------------------------------------

const FLAGGED_PROCEDURES = [
  { procedure: "Total knee arthroplasty", cpt: "27447", count: 8, avgPaid: 4200, medicareRate: 1520, markup: 2.8 },
  { procedure: "Knee arthroscopy w/ meniscectomy", cpt: "29881", count: 12, avgPaid: 1950, medicareRate: 698, markup: 2.8 },
  { procedure: "MRI knee without contrast", cpt: "73721", count: 14, avgPaid: 1840, medicareRate: 285, markup: 6.5 },
  { procedure: "Total hip arthroplasty", cpt: "27130", count: 5, avgPaid: 3800, medicareRate: 1487, markup: 2.6 },
  { procedure: "Echocardiogram, complete", cpt: "93306", count: 18, avgPaid: 420, medicareRate: 187, markup: 2.2 },
  { procedure: "Cardiac CT, calcium scoring", cpt: "75571", count: 12, avgPaid: 310, medicareRate: 98, markup: 3.2 },
  { procedure: "Anterior cervical discectomy", cpt: "22551", count: 4, avgPaid: 5100, medicareRate: 1843, markup: 2.8 },
  { procedure: "Stress echocardiogram", cpt: "93350", count: 8, avgPaid: 680, medicareRate: 245, markup: 2.8 },
  { procedure: "Cardiac MRI", cpt: "75574", count: 6, avgPaid: 2100, medicareRate: 612, markup: 3.4 },
  { procedure: "Joint injection, major joint", cpt: "20610", count: 16, avgPaid: 280, medicareRate: 68, markup: 4.1 },
];

const CLAIMS_SUMMARY = {
  totalClaims: 847,
  totalPaid: 623000,
  totalExcess: 218400,
  annualizedExcess: 2620800,
};

// ---------------------------------------------------------------------------
// Scorecard data (Tab 4)
// ---------------------------------------------------------------------------

const SCORECARD = {
  grade: "C+",
  score: 6.0,
  maxScore: 10,
  passCount: 6,
  criteria: [
    { num: 1, criterion: "Deductible level", result: "pass", note: "Single deductible $1,200 \u2014 below $1,500 benchmark" },
    { num: 2, criterion: "Out-of-pocket max", result: "partial", note: "Single OOP $5,500 \u2014 above $4,000 best-practice target" },
    { num: 3, criterion: "Preventive care", result: "pass", note: "Covered at $0 cost-share" },
    { num: 4, criterion: "Telehealth", result: "pass", note: "Covered, $0 copay through Cigna MDLive" },
    { num: 5, criterion: "Mental health parity", result: "pass", note: "Mental health covered same as medical" },
    { num: 6, criterion: "Network type", result: "fail", note: "Standard PPO \u2014 no reference-based pricing or narrow network" },
    { num: 7, criterion: "Pharmacy carve-out", result: "fail", note: "No separate pharmacy benefit \u2014 Rx bundled with medical" },
    { num: 8, criterion: "ER cost sharing", result: "partial", note: "ER copay $150 \u2014 at threshold, not above it" },
    { num: 9, criterion: "Specialist cost sharing", result: "pass", note: "Specialist copay $50" },
    { num: 10, criterion: "HSA eligibility", result: "fail", note: "PPO plan \u2014 not HSA-eligible" },
  ],
  savingsLow: 62500,
  savingsHigh: 82500,
  savingsPerEmpLow: 125,
  savingsPerEmpHigh: 165,
};

// ---------------------------------------------------------------------------
// Monitoring features (Tab 5)
// ---------------------------------------------------------------------------

const MONITORING_FEATURES = [
  {
    title: "Monthly Spend Drift Report",
    description: "We re-run your claims against the Medicare benchmark every month and flag any new outliers or worsening markup ratios before they compound.",
  },
  {
    title: "New Outlier Alerts",
    description: "When a new high-markup procedure appears in your claims data, you\u2019re notified within 30 days \u2014 not at annual renewal.",
  },
  {
    title: "Renewal Negotiation Prep",
    description: "30 days before your renewal date, we deliver a benchmark comparison report you can take directly to your broker to negotiate from a position of data.",
  },
  {
    title: "Annual Plan Design Re-Score",
    description: "Your plan design is re-scored every year against updated benchmarks. You\u2019ll see exactly which criteria improved and which new gaps emerged.",
  },
  {
    title: "RBP Savings Tracking",
    description: "We re-run your RBP savings estimate monthly as new claims come in \u2014 so you can see whether your savings opportunity is growing or shrinking before renewal.",
  },
  {
    title: "Contract Competitiveness Alerts",
    description: "When your carrier contract comes up for renewal, we re-parse your fee schedule and flag any rates that have drifted further above Medicare benchmarks since your last analysis.",
  },
];

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

const TABS = [
  { key: "start", label: "Getting Started" },
  { key: "benchmark", label: "Benefits Benchmark" },
  { key: "claims", label: "Claims Spot Check" },
  { key: "scorecard", label: "Plan Design Scorecard" },
  { key: "rbp", label: "RBP Calculator" },
  { key: "contract", label: "Contract Parser" },
  { key: "monitoring", label: "Monitoring Dashboard" },
];

export default function EmployerDemoPage() {
  const [activeTab, setActiveTab] = useState("start");

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
        You're viewing a demo with sample data.{" "}
        <Link
          to="/billing/employer"
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
          <span style={{ fontWeight: "600", fontSize: "16px" }}>
            Parity Employer
          </span>
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
          {COMPANY.name} &middot; {COMPANY.lives} covered lives &middot; {COMPANY.tpa} {COMPANY.planType}
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
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            style={{
              padding: "14px 18px",
              fontSize: "13px",
              fontWeight: activeTab === t.key ? "600" : "400",
              color: activeTab === t.key ? "#60a5fa" : "#64748b",
              borderBottom: activeTab === t.key ? "2px solid #3b82f6" : "2px solid transparent",
              background: "none",
              border: "none",
              cursor: "pointer",
              whiteSpace: "nowrap",
              fontFamily: "inherit",
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Tab content */}
      <main style={{ padding: "32px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        {activeTab === "start" && <GettingStartedTab onNavigate={setActiveTab} />}
        {activeTab === "benchmark" && <BenchmarkTab />}
        {activeTab === "claims" && <ClaimsSpotCheckTab />}
        {activeTab === "scorecard" && <ScorecardTab />}
        {activeTab === "rbp" && <RBPCalculatorTab />}
        {activeTab === "contract" && <ContractParserTab />}
        {activeTab === "monitoring" && <MonitoringTab />}

        {/* Bottom CTA — all tabs except Getting Started */}
        {activeTab !== "start" && (
          <div style={{
            background: "rgba(59,130,246,0.06)",
            border: "1px solid rgba(59,130,246,0.2)",
            borderRadius: "12px",
            padding: "28px",
            textAlign: "center",
            marginTop: "36px",
          }}>
            <p style={{ fontSize: "14px", color: "#94a3b8", marginBottom: "8px", lineHeight: "1.7" }}>
              This demo uses sample data for {COMPANY.name}. Start your free benchmark with your own numbers &mdash; no credit card required.
            </p>
            <p style={{ fontSize: "13px", color: "#10b981", marginBottom: "16px" }}>
              Plans from $149/mo &middot; 3x savings guarantee
            </p>
            <Link
              to="/billing/employer/benchmark"
              style={{
                display: "inline-block",
                background: "#3b82f6",
                color: "#fff",
                padding: "12px 28px",
                borderRadius: "8px",
                fontWeight: "600",
                fontSize: "14px",
                textDecoration: "none",
              }}
            >
              Start Free Benchmark &rarr;
            </Link>
            <div style={{ marginTop: "12px" }}>
              <Link
                to="/broker/login"
                style={{ fontSize: "13px", color: "#64748b", textDecoration: "none" }}
              >
                View broker portal &rarr;
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 1: Getting Started
// ---------------------------------------------------------------------------

function GettingStartedTab({ onNavigate }) {
  const timers = useRef([]);

  // Animation state
  const [field1Visible, setField1Visible] = useState(false);
  const [field2Visible, setField2Visible] = useState(false);
  const [field3Visible, setField3Visible] = useState(false);
  const [field4Visible, setField4Visible] = useState(false);
  const [pepmText, setPepmText] = useState("");
  const [fileChip1, setFileChip1] = useState(false);
  const [fileChip2, setFileChip2] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  const [analysisLabel, setAnalysisLabel] = useState(false);
  const [pdfChipVisible, setPdfChipVisible] = useState(false);
  const [ctaVisible, setCtaVisible] = useState(false);
  const [buttonPulse, setButtonPulse] = useState(false);

  useEffect(() => {
    if (gsAnimationPlayed) {
      setField1Visible(true);
      setField2Visible(true);
      setField3Visible(true);
      setField4Visible(true);
      setPepmText("$1,246");
      setFileChip1(true);
      setFileChip2(true);
      setProgressPercent(100);
      setAnalysisLabel(true);
      setPdfChipVisible(true);
      setCtaVisible(true);
      setButtonPulse(true);
      return;
    }

    gsAnimationPlayed = true;

    const t = (fn, ms) => {
      const id = setTimeout(fn, ms);
      timers.current.push(id);
      return id;
    };

    // Step 1 — form fields scale in
    t(() => setField1Visible(true), 400);
    t(() => setField2Visible(true), 900);
    t(() => setField3Visible(true), 1400);
    t(() => setField4Visible(true), 1900);

    // PEPM typewriter
    const pepmChars = "$1,246".split("");
    pepmChars.forEach((ch, i) => {
      t(() => setPepmText((prev) => prev + ch), 2200 + i * 120);
    });

    // Step 2 — file chips
    t(() => setFileChip1(true), 3800);
    t(() => setFileChip2(true), 4200);

    // Progress bar 0→100% from t=4600 to t=6600
    const progressStart = 4600;
    const progressDuration = 2000;
    const progressSteps = 30;
    const stepInterval = progressDuration / progressSteps;
    for (let i = 1; i <= progressSteps; i++) {
      const pct = Math.round((i / progressSteps) * 100);
      t(() => setProgressPercent(pct), progressStart + i * stepInterval);
    }
    t(() => setAnalysisLabel(true), progressStart + progressDuration * 0.5);

    // Step 3 — PDF chip
    t(() => setPdfChipVisible(true), 7200);

    // CTA
    t(() => {
      setCtaVisible(true);
      t(() => setButtonPulse(true), 300);
    }, 8200);

    return () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const progressColor = progressPercent >= 100 ? "#10B981" : "#3B82F6";

  return (
    <div>
      {/* Inject keyframes */}
      <style>{`
        @keyframes gsTypeCursor {
          0%, 100% { border-right-color: #1E293B; }
          50% { border-right-color: transparent; }
        }
        @keyframes gsChipBounce {
          0% { opacity: 0; transform: translateY(-12px) scale(0.95); }
          60% { opacity: 1; transform: translateY(3px) scale(1.02); }
          80% { transform: translateY(-1px) scale(1); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes gsScaleIn {
          0% { opacity: 0; transform: scale(0.92); }
          100% { opacity: 1; transform: scale(1); }
        }
        @keyframes gsPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0.5); }
          50% { box-shadow: 0 0 0 8px rgba(59,130,246,0); }
        }
      `}</style>

      <div style={{ textAlign: "center", marginBottom: "36px" }}>
        <h2 style={{ ...h2Style, marginBottom: "10px" }}>
          Three steps. Under five minutes. No consultants.
        </h2>
        <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "640px", margin: "0 auto", fontStyle: "italic" }}>
          This demo shows how Parity Employer analyzed Midwest Manufacturing&apos;s health spend
          using 841,000 public Medicare procedure rates &mdash; the same data your carriers use,
          but rarely share. Start with a free benchmark, upload one month of claims, and get a
          complete action plan including an RBP savings estimate and broker-ready PDF. No carrier
          relationships. No commissions. Just the numbers.
        </p>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
        gap: "24px",
        marginBottom: "40px",
      }}>
        {/* Step 1 — Benefits Benchmark */}
        <div style={stepCardOuter}>
          <div style={stepLabel}>Step 1 &mdash; 60 seconds</div>
          <h3 style={stepTitle}>Enter your plan details</h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "16px" }}>
            {/* Field 1: Industry */}
            <div style={{
              animation: field1Visible ? "gsScaleIn 0.4s ease forwards" : "none",
              opacity: field1Visible ? 1 : 0,
            }}>
              <div style={gsFieldLabel}>Industry</div>
              <div style={gsMockInput}>
                <span>Manufacturing</span>
                <span style={{ color: "#94a3b8", fontSize: "11px" }}>{"\u25BC"}</span>
              </div>
            </div>

            {/* Field 2: Company size */}
            <div style={{
              animation: field2Visible ? "gsScaleIn 0.4s ease forwards" : "none",
              opacity: field2Visible ? 1 : 0,
            }}>
              <div style={gsFieldLabel}>Company Size</div>
              <div style={gsMockInput}>
                <span>101&ndash;500 employees</span>
                <span style={{ color: "#94a3b8", fontSize: "11px" }}>{"\u25BC"}</span>
              </div>
            </div>

            {/* Field 3: State */}
            <div style={{
              animation: field3Visible ? "gsScaleIn 0.4s ease forwards" : "none",
              opacity: field3Visible ? 1 : 0,
            }}>
              <div style={gsFieldLabel}>State</div>
              <div style={gsMockInput}>
                <span>Illinois</span>
                <span style={{ color: "#94a3b8", fontSize: "11px" }}>{"\u25BC"}</span>
              </div>
            </div>

            {/* Field 4: PEPM with typewriter */}
            <div style={{
              animation: field4Visible ? "gsScaleIn 0.4s ease forwards" : "none",
              opacity: field4Visible ? 1 : 0,
            }}>
              <div style={gsFieldLabel}>Current PEPM Cost</div>
              <div style={{
                ...gsMockInput,
                borderRight: pepmText.length > 0 && pepmText.length < 6 ? "2px solid #1E293B" : undefined,
                animation: pepmText.length > 0 && pepmText.length < 6 ? "gsTypeCursor 0.6s step-end infinite" : undefined,
              }}>
                {pepmText || "\u00A0"}
              </div>
            </div>
          </div>

          <p style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.6", margin: 0 }}>
            No files needed. We compare your costs against 841,000 Medicare procedure rates
            and peer employer benchmarks from KFF, MEPS-IC, and BLS.
          </p>
        </div>

        {/* Step 2 — Claims Spot Check */}
        <div style={stepCardOuter}>
          <div style={stepLabel}>Step 2 &mdash; 2 minutes</div>
          <h3 style={stepTitle}>Upload one month of claims</h3>

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
              Drag &amp; drop your claims file here
            </div>
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>
              {fileChip1 ? "1 file selected" : "\u00A0"}
            </div>
          </div>

          {/* File chips */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px", minHeight: "32px" }}>
            {fileChip1 && (
              <div style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "#EFF6FF", border: "1px solid #BFDBFE",
                borderRadius: "6px", padding: "6px 12px", fontSize: "12px", color: "#1E40AF",
                animation: "gsChipBounce 0.4s ease forwards",
              }}>
                <span style={{ fontSize: "14px" }}>{"\uD83D\uDCC4"}</span>
                Cigna_Claims_Dec2024.835
              </div>
            )}
            {fileChip1 && (
              <div style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "#FFFBEB", border: "1px solid #FDE68A",
                borderRadius: "6px", padding: "6px 12px", fontSize: "12px", color: "#92400E",
                animation: "gsChipBounce 0.4s ease forwards",
              }}>
                <span style={{ fontSize: "14px" }}>{"\uD83D\uDCC4"}</span>
                Cigna_Claims_Dec2024.xlsx <span style={{ color: "#B45309", fontStyle: "italic" }}>(CSV also accepted)</span>
              </div>
            )}
            {fileChip2 && (
              <div style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "#F0FDF4", border: "1px solid #BBF7D0",
                borderRadius: "6px", padding: "6px 12px", fontSize: "12px", color: "#166534",
                animation: "gsChipBounce 0.4s ease forwards",
              }}>
                <span style={{ fontSize: "14px" }}>{"\u2713"}</span>
                500 employees &middot; 847 claims
              </div>
            )}
          </div>

          {/* Progress bar */}
          <div style={{
            background: "#F8FAFC", borderRadius: "8px", padding: "14px",
            border: "1px solid #E2E8F0", marginBottom: "16px",
            opacity: fileChip2 ? 1 : 0.3,
            transition: "opacity 0.4s ease",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "12px", color: "#64748b" }}>
                {progressPercent > 0 ? "Analyzing against Medicare rates..." : "\u00A0"}
              </span>
              <span style={{ fontSize: "12px", color: progressColor, fontWeight: "600", transition: "color 0.3s" }}>
                {progressPercent > 0 ? `${progressPercent}%` : "\u00A0"}
              </span>
            </div>
            <div style={{ height: "4px", borderRadius: "2px", background: "#E2E8F0" }}>
              <div style={{
                height: "4px", borderRadius: "2px",
                background: progressColor,
                width: `${progressPercent}%`,
                transition: "width 50ms linear, background 0.3s ease",
              }} />
            </div>
            <div style={{
              fontSize: "11px", color: "#64748b", marginTop: "6px",
              opacity: analysisLabel ? 1 : 0,
              transition: "opacity 0.4s ease",
            }}>
              847 claims matched across 10 procedure categories
            </div>
          </div>

          <p style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.6", margin: 0 }}>
            Accepts 835 EDI remittance files, CSV, Excel, or ZIP archives. Our AI maps
            your columns automatically &mdash; no manual field matching required.
          </p>
        </div>

        {/* Step 3 — Plan Design Scorecard */}
        <div style={stepCardOuter}>
          <div style={stepLabel}>Step 3 &mdash; 1 minute</div>
          <h3 style={stepTitle}>Upload your Summary of Benefits</h3>

          {/* Drop zone */}
          <div style={{
            border: "2px dashed #CBD5E1",
            borderRadius: "10px",
            padding: "28px 20px",
            textAlign: "center",
            marginBottom: "16px",
            background: "#F8FAFC",
          }}>
            <div style={{ fontSize: "28px", marginBottom: "8px", color: "#94a3b8" }}>{"\uD83D\uDCC4"}</div>
            <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "4px" }}>
              Drag &amp; drop your SBC document here
            </div>
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>
              {pdfChipVisible ? "1 file selected" : "\u00A0"}
            </div>
          </div>

          {/* PDF chip */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "16px", minHeight: "32px" }}>
            {pdfChipVisible && (
              <div style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "#EFF6FF", border: "1px solid #BFDBFE",
                borderRadius: "6px", padding: "6px 12px", fontSize: "12px", color: "#1E40AF",
                animation: "gsChipBounce 0.4s ease forwards",
              }}>
                <span style={{ fontSize: "14px" }}>{"\uD83D\uDCC4"}</span>
                Cigna_SBC_2025.pdf
              </div>
            )}
            {pdfChipVisible && (
              <div style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "#F0FDF4", border: "1px solid #BBF7D0",
                borderRadius: "6px", padding: "6px 12px", fontSize: "12px", color: "#166534",
                animation: "gsChipBounce 0.4s ease forwards",
              }}>
                <span style={{ fontSize: "14px" }}>{"\u2713"}</span>
                Summary of Benefits and Coverage &middot; 4 pages
              </div>
            )}
          </div>

          <p style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.6", margin: 0 }}>
            Your SBC is the standardized 2&ndash;4 page document your carrier is required by
            law to provide. Request it from your broker or download it from your carrier portal.
          </p>
        </div>
      </div>

      {/* CTA — fades in after all steps */}
      <div style={{
        textAlign: "center", marginBottom: "8px",
        opacity: ctaVisible ? 1 : 0,
        transform: ctaVisible ? "translateY(0)" : "translateY(12px)",
        transition: "opacity 0.5s ease, transform 0.5s ease",
      }}>
        <p style={{
          fontSize: "15px", color: "#94a3b8", lineHeight: "1.8",
          maxWidth: "640px", margin: "0 auto 24px",
        }}>
          Three steps. Under five minutes. See exactly where your health spend is going.
        </p>
        <button
          onClick={() => onNavigate("benchmark")}
          style={{
            display: "inline-block",
            background: "#3b82f6", color: "#fff",
            padding: "12px 28px", borderRadius: "8px",
            fontWeight: "600", fontSize: "15px",
            border: "none", cursor: "pointer",
            fontFamily: "inherit",
            transition: "background 0.2s",
            animation: buttonPulse ? "gsPulse 2s ease-in-out infinite" : "none",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#2563eb")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#3b82f6")}
        >
          See {COMPANY.name}&apos;s Full Analysis &rarr;
        </button>
        <div style={{ marginTop: "12px" }}>
          <Link
            to="/billing/employer/benchmark"
            style={{ fontSize: "13px", color: "#64748b", textDecoration: "none" }}
          >
            This demo uses sample data. Start your free benchmark with your own numbers &rarr;
          </Link>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: Benefits Benchmark
// ---------------------------------------------------------------------------

function BenchmarkTab() {
  const pct = BENCHMARK.percentile;
  const barColor = pct > 75 ? "#ef4444" : pct > 50 ? "#f59e0b" : "#22c55e";

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "28px" }}>Benefits Benchmark</h2>

      {/* PEPM comparison */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <StatCard label="Your PEPM" value={fmt(BENCHMARK.companyPEPM)} sub="per employee per month" />
        <StatCard
          label={`Industry Median (${COMPANY.industry}, ${COMPANY.state})`}
          value={fmt(BENCHMARK.industryMedianPEPM)}
          sub="per employee per month"
        />
        <StatCard label="Gap" value={`+${fmt(BENCHMARK.dollarGapPEPM)}`} sub="per employee per month" accent />
      </div>

      {/* Percentile gauge */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Industry Percentile</h3>
        <div style={{ marginBottom: "12px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "12px",
              color: "#64748b",
              marginBottom: "6px",
            }}
          >
            <span>{ordinal(0)}</span>
            <span>{ordinal(25)}</span>
            <span>{ordinal(50)} (median)</span>
            <span>{ordinal(75)}</span>
            <span>{ordinal(100)}</span>
          </div>
          <div
            style={{
              position: "relative",
              height: "28px",
              borderRadius: "14px",
              overflow: "hidden",
            }}
          >
            {/* Background gradient */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: "linear-gradient(to right, #22c55e 0%, #22c55e 50%, #f59e0b 50%, #f59e0b 75%, #ef4444 75%, #ef4444 100%)",
                opacity: 0.15,
                borderRadius: "14px",
              }}
            />
            {/* Fill bar */}
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                height: "100%",
                width: `${pct}%`,
                background: barColor,
                opacity: 0.35,
                borderRadius: "14px 0 0 14px",
                transition: "width 0.6s ease-out",
              }}
            />
            {/* Marker */}
            <div
              style={{
                position: "absolute",
                top: "2px",
                left: `${pct}%`,
                transform: "translateX(-50%)",
                width: "24px",
                height: "24px",
                borderRadius: "50%",
                background: barColor,
                border: "3px solid #0a1628",
                boxShadow: `0 0 8px ${barColor}60`,
              }}
            />
          </div>
          <div style={{ textAlign: "center", marginTop: "10px" }}>
            <span
              style={{
                fontSize: "28px",
                fontWeight: "700",
                color: barColor,
              }}
            >
              {ordinal(pct)}
            </span>
            <span style={{ fontSize: "14px", color: "#94a3b8", marginLeft: "8px" }}>
              percentile &mdash; above median, in the warning zone
            </span>
          </div>
        </div>
      </div>

      {/* Dollar gap callout */}
      <div
        style={{
          marginTop: "24px",
          background: "rgba(245,158,11,0.08)",
          border: "1px solid rgba(245,158,11,0.25)",
          borderRadius: "12px",
          padding: "24px",
        }}
      >
        <div style={{ fontSize: "14px", fontWeight: "600", color: "#fbbf24", marginBottom: "6px" }}>
          Dollar Gap
        </div>
        <p style={{ fontSize: "15px", lineHeight: "1.7", color: "#e2e8f0" }}>
          {fmt(BENCHMARK.dollarGapPEPM)}/employee/month above median &mdash;{" "}
          <strong style={{ color: "#fbbf24" }}>{fmt(BENCHMARK.dollarGapAnnual)}/year</strong>{" "}
          above the {COMPANY.industry} benchmark for a {COMPANY.lives}-person company.
        </p>
      </div>

      {/* Top 3 cost drivers */}
      <div style={{ ...cardStyle, marginTop: "24px" }}>
        <h3 style={h3Style}>Top 3 Cost Drivers for {COMPANY.industry}</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {BENCHMARK.costDrivers.map((driver, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "12px",
              }}
            >
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background: "rgba(59,130,246,0.15)",
                  color: "#60a5fa",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "13px",
                  fontWeight: "700",
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <div style={{ fontSize: "14px", color: "#e2e8f0", lineHeight: "1.6", paddingTop: "3px" }}>
                {driver}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data source badges */}
      <div
        style={{
          display: "flex",
          gap: "10px",
          flexWrap: "wrap",
          marginTop: "24px",
        }}
      >
        {BENCHMARK.dataSources.map((src) => (
          <span
            key={src}
            style={{
              fontSize: "11px",
              fontWeight: "500",
              color: "#64748b",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "6px",
              padding: "5px 10px",
            }}
          >
            {src}
          </span>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: Claims Spot Check
// ---------------------------------------------------------------------------

function ClaimsSpotCheckTab() {
  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "12px" }}>Claims Spot Check</h2>

      {/* Summary banner */}
      <div
        style={{
          background: "rgba(59,130,246,0.06)",
          border: "1px solid rgba(59,130,246,0.2)",
          borderRadius: "12px",
          padding: "20px 24px",
          marginBottom: "28px",
        }}
      >
        <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#e2e8f0", margin: 0 }}>
          We analyzed <strong>{CLAIMS_SUMMARY.totalClaims.toLocaleString()} claims</strong> totaling{" "}
          <strong>{fmt(CLAIMS_SUMMARY.totalPaid)}</strong> paid. We found{" "}
          <strong style={{ color: "#f59e0b" }}>{fmt(CLAIMS_SUMMARY.totalExcess)}</strong> in
          potentially excess payments vs. a 2x Medicare benchmark.
        </p>
      </div>

      {/* Flagged procedures table */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Top 10 Flagged Procedures</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Procedure</th>
                <th style={thStyle}>CPT Code</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Times Billed</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Avg Paid</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Medicare Rate</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Markup</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Total Excess</th>
              </tr>
            </thead>
            <tbody>
              {FLAGGED_PROCEDURES.map((p) => {
                const excess = Math.round((p.avgPaid - p.medicareRate * 2) * p.count);
                const rowBg =
                  p.markup > 5
                    ? "rgba(239,68,68,0.08)"
                    : p.markup >= 3
                    ? "rgba(245,158,11,0.06)"
                    : "transparent";
                const markupColor =
                  p.markup > 5
                    ? "#f87171"
                    : p.markup >= 3
                    ? "#fbbf24"
                    : "#e2e8f0";
                return (
                  <tr key={p.cpt} style={{ background: rowBg }}>
                    <td style={tdStyle}>{p.procedure}</td>
                    <td style={{ ...tdStyle, fontFamily: "monospace", color: "#60a5fa" }}>{p.cpt}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{p.count}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(p.avgPaid)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>{fmt(p.medicareRate)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600", color: markupColor }}>
                      {p.markup}x
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600" }}>
                      {excess > 0 ? fmt(excess) : "\u2014"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Callout card — highest excess */}
      <div
        style={{
          marginTop: "24px",
          background: "rgba(239,68,68,0.06)",
          border: "1px solid rgba(239,68,68,0.2)",
          borderRadius: "12px",
          padding: "24px",
        }}
      >
        <div style={{ fontSize: "14px", fontWeight: "600", color: "#f87171", marginBottom: "6px" }}>
          Highest Excess Item
        </div>
        <p style={{ fontSize: "15px", lineHeight: "1.7", color: "#e2e8f0", margin: 0 }}>
          You paid <strong style={{ color: "#f87171" }}>6.5x Medicare</strong> for MRI Knee (CPT 73721)
          across 14 claims &mdash;{" "}
          <strong style={{ color: "#f87171" }}>$21,770 in excess</strong> vs. a 2x Medicare benchmark.
        </p>
      </div>

      {/* Annualized total */}
      <div
        style={{
          marginTop: "24px",
          background: "rgba(245,158,11,0.08)",
          border: "1px solid rgba(245,158,11,0.25)",
          borderRadius: "12px",
          padding: "24px",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: "12px",
            fontWeight: "600",
            color: "#fbbf24",
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            marginBottom: "6px",
          }}
        >
          Annualized Excess Estimate
        </div>
        <div style={{ fontSize: "32px", fontWeight: "700", color: "#fbbf24" }}>
          {fmt(CLAIMS_SUMMARY.annualizedExcess)}/year
        </div>
        <p style={{ fontSize: "13px", color: "#94a3b8", marginTop: "6px" }}>
          If this pattern holds over 12 months
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 4: Plan Design Scorecard
// ---------------------------------------------------------------------------

function ScorecardTab() {
  const resultIcon = (r) => {
    if (r === "pass") return { icon: "\u2713", color: "#22c55e", bg: "rgba(34,197,94,0.1)" };
    if (r === "partial") return { icon: "\u26A0", color: "#f59e0b", bg: "rgba(245,158,11,0.1)" };
    return { icon: "\u2717", color: "#ef4444", bg: "rgba(239,68,68,0.1)" };
  };

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "28px" }}>Plan Design Scorecard</h2>

      {/* Grade display */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "24px",
          marginBottom: "32px",
          flexWrap: "wrap",
        }}
      >
        <div
          style={{
            width: "100px",
            height: "100px",
            borderRadius: "50%",
            background: "rgba(245,158,11,0.1)",
            border: "3px solid #f59e0b",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <span style={{ fontSize: "36px", fontWeight: "700", color: "#fbbf24" }}>
            {SCORECARD.grade}
          </span>
        </div>
        <div>
          <div style={{ fontSize: "22px", fontWeight: "600", color: "#f1f5f9" }}>
            {SCORECARD.score} / {SCORECARD.maxScore}
          </div>
          <div style={{ fontSize: "14px", color: "#94a3b8", marginTop: "4px" }}>
            {SCORECARD.passCount} of {SCORECARD.maxScore} best-practice criteria met
          </div>
        </div>
      </div>

      {/* Criteria checklist */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Criteria Checklist</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={{ ...thStyle, width: "40px" }}>#</th>
                <th style={thStyle}>Criterion</th>
                <th style={{ ...thStyle, textAlign: "center", width: "80px" }}>Result</th>
                <th style={thStyle}>Note</th>
              </tr>
            </thead>
            <tbody>
              {SCORECARD.criteria.map((c) => {
                const ri = resultIcon(c.result);
                return (
                  <tr key={c.num}>
                    <td style={{ ...tdStyle, color: "#64748b", fontWeight: "500" }}>{c.num}</td>
                    <td style={{ ...tdStyle, fontWeight: "500" }}>{c.criterion}</td>
                    <td style={{ ...tdStyle, textAlign: "center" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          width: "28px",
                          height: "28px",
                          borderRadius: "50%",
                          background: ri.bg,
                          color: ri.color,
                          fontSize: "14px",
                          fontWeight: "700",
                        }}
                      >
                        {ri.icon}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, fontSize: "12px", color: "#94a3b8" }}>{c.note}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Savings estimate */}
      <div
        style={{
          marginTop: "24px",
          background: "rgba(34,197,94,0.06)",
          border: "1px solid rgba(34,197,94,0.2)",
          borderRadius: "12px",
          padding: "24px",
        }}
      >
        <div style={{ fontSize: "14px", fontWeight: "600", color: "#4ade80", marginBottom: "6px" }}>
          Savings Estimate
        </div>
        <p style={{ fontSize: "15px", lineHeight: "1.7", color: "#e2e8f0", margin: 0 }}>
          Fixing your top 3 gaps (network, pharmacy carve-out, HSA migration) could save an estimated{" "}
          <strong style={{ color: "#4ade80" }}>
            ${SCORECARD.savingsPerEmpLow}&ndash;${SCORECARD.savingsPerEmpHigh} per employee per year
          </strong>{" "}
          &mdash; {fmt(SCORECARD.savingsLow)}&ndash;{fmt(SCORECARD.savingsHigh)} annually for
          your {COMPANY.lives}-person company.
        </p>
      </div>

      {/* CTA */}
      <div style={{ marginTop: "28px", textAlign: "center" }}>
        <Link
          to="/billing/employer/subscribe"
          style={{
            display: "inline-block",
            background: "#3b82f6",
            color: "#fff",
            padding: "12px 28px",
            borderRadius: "8px",
            fontWeight: "600",
            fontSize: "14px",
            textDecoration: "none",
          }}
        >
          Start monitoring &rarr; Subscribe
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 5: RBP Calculator
// ---------------------------------------------------------------------------

function RBPCalculatorTab() {
  const rbpCategories = [
    { name: "Orthopedics", actual: 1200000, rbp: 720000, savings: 480000, pct: 40 },
    { name: "Radiology", actual: 640000, rbp: 310000, savings: 330000, pct: 52 },
    { name: "Cardiology", actual: 890000, rbp: 620000, savings: 270000, pct: 30 },
    { name: "Surgery", actual: 1450000, rbp: 1160000, savings: 290000, pct: 20 },
    { name: "E&M / Primary Care", actual: 1800000, rbp: 1710000, savings: 90000, pct: 5 },
  ];

  const pctColor = (pct) => pct > 25 ? "#22c55e" : pct >= 10 ? "#f59e0b" : "#64748b";

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "6px" }}>
        Reference-Based Pricing Analysis &mdash; {COMPANY.name}
      </h2>
      <p style={{ fontSize: "14px", color: "#64748b", marginBottom: "28px" }}>
        At 140% of Medicare &middot; Based on December 2024 claims
      </p>

      {/* Eligibility panel */}
      <div style={{
        ...cardStyle,
        marginBottom: "24px",
        borderLeft: "4px solid #f59e0b",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
          <span style={{
            display: "inline-block", padding: "4px 12px", borderRadius: "16px",
            fontSize: "12px", fontWeight: "700", background: "rgba(245,158,11,0.15)",
            color: "#fbbf24",
          }}>
            Possible Fit
          </span>
          <span style={{ fontSize: "13px", color: "#94a3b8" }}>RBP Eligibility Assessment</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
            <span style={{ fontSize: "16px", flexShrink: 0 }}>{"\uD83D\uDFE1"}</span>
            <div>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#e2e8f0" }}>Company size: </span>
              <span style={{ fontSize: "13px", color: "#94a3b8" }}>500 employees &mdash; viable, administrative burden is manageable at this size</span>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
            <span style={{ fontSize: "16px", flexShrink: 0 }}>{"\uD83D\uDFE1"}</span>
            <div>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#e2e8f0" }}>Plan funding: </span>
              <span style={{ fontSize: "13px", color: "#94a3b8" }}>Cigna PPO &mdash; fully insured. Moving to self-insurance is a prerequisite for RBP. Most 500-person employers qualify.</span>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
            <span style={{ fontSize: "16px", flexShrink: 0 }}>{"\uD83D\uDFE2"}</span>
            <div>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#e2e8f0" }}>Geographic concentration: </span>
              <span style={{ fontSize: "13px", color: "#94a3b8" }}>Illinois &mdash; geographically concentrated workforce simplifies RBP vendor relationships with local hospitals</span>
            </div>
          </div>
        </div>
      </div>

      {/* Savings summary callout */}
      <div style={{
        background: "rgba(34,197,94,0.06)",
        border: "1px solid rgba(34,197,94,0.2)",
        borderRadius: "12px",
        padding: "28px",
        marginBottom: "24px",
      }}>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "20px", marginBottom: "16px",
        }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
              Actual Annual Spend
            </div>
            <div style={{ fontSize: "24px", fontWeight: "700", color: "#f1f5f9" }}>$7,480,000</div>
          </div>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
              RBP Equivalent at 140% Medicare
            </div>
            <div style={{ fontSize: "24px", fontWeight: "700", color: "#f1f5f9" }}>$5,240,000</div>
          </div>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
              Potential Annual Savings
            </div>
            <div style={{ fontSize: "24px", fontWeight: "700", color: "#4ade80" }}>
              $2,240,000 <span style={{ fontSize: "14px", fontWeight: "500" }}>(30%)</span>
            </div>
          </div>
        </div>
        <p style={{ fontSize: "12px", color: "#64748b", margin: 0, fontStyle: "italic" }}>
          Estimated. Actual savings depend on plan design, employee behavior, and vendor implementation.
        </p>
      </div>

      {/* Category breakdown table */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Category Breakdown</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Category</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Actual Paid</th>
                <th style={{ ...thStyle, textAlign: "right" }}>RBP Equivalent</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Savings</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Savings %</th>
              </tr>
            </thead>
            <tbody>
              {rbpCategories.map((c) => (
                <tr key={c.name}>
                  <td style={{ ...tdStyle, fontWeight: "500" }}>{c.name}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(c.actual)}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(c.rbp)}</td>
                  <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600", color: "#4ade80" }}>{fmt(c.savings)}</td>
                  <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600", color: pctColor(c.pct) }}>{c.pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI narrative */}
      <div style={{
        ...cardStyle,
        marginTop: "24px",
        borderLeft: "4px solid #3b82f6",
      }}>
        <div style={{
          fontSize: "11px", fontWeight: "600", color: "#60a5fa",
          textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "10px",
        }}>
          RBP Analysis
        </div>
        <p style={{ fontSize: "14px", lineHeight: "1.8", color: "#94a3b8", margin: 0 }}>
          Midwest Manufacturing&apos;s highest RBP savings opportunity is in Radiology, where imaging
          procedures average 52% above a 140% Medicare benchmark &mdash; driven primarily by MRI and CT
          scans billed at hospital outpatient rates. Orthopedics follows at 40% excess, concentrated in
          two surgical providers. Primary care is already close to benchmark and would see minimal savings
          under RBP. The estimated $2.24M annual savings assumes full implementation &mdash; a conservative
          first-year target accounting for transition friction would be $1.1M&ndash;$1.5M.
        </p>
      </div>

      {/* Next steps */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
        gap: "16px", marginTop: "24px",
      }}>
        <div style={{
          ...cardStyle,
          opacity: 0.5,
          textAlign: "center",
          padding: "20px",
        }}>
          <div style={{ fontSize: "24px", marginBottom: "8px" }}>{"\uD83D\uDCC4"}</div>
          <div style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0", marginBottom: "4px" }}>
            Download broker summary PDF
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", fontStyle: "italic" }}>
            Available in full product
          </div>
        </div>
        <a
          href="https://www.imagine360.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            ...cardStyle,
            textAlign: "center",
            padding: "20px",
            textDecoration: "none",
            cursor: "pointer",
          }}
        >
          <div style={{ fontSize: "24px", marginBottom: "8px" }}>{"\uD83D\uDD17"}</div>
          <div style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0", marginBottom: "4px" }}>
            Talk to an RBP specialist &mdash; Imagine360 &rarr;
          </div>
          <div style={{ fontSize: "11px", color: "#64748b" }}>
            External partner link
          </div>
        </a>
        <Link
          to="/billing/employer/demo"
          style={{
            ...cardStyle,
            textAlign: "center",
            padding: "20px",
            textDecoration: "none",
          }}
        >
          <div style={{ fontSize: "24px", marginBottom: "8px" }}>{"\u2190"}</div>
          <div style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0", marginBottom: "4px" }}>
            Back to full analysis &rarr;
          </div>
          <div style={{ fontSize: "11px", color: "#64748b" }}>
            Return to demo overview
          </div>
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 6: Contract Parser
// ---------------------------------------------------------------------------

function ContractParserTab() {
  const contractRates = [
    { procedure: "MRI knee without contrast", cpt: "73721", contracted: 1240, medicare: 285, variance: 335 },
    { procedure: "Cardiac MRI", cpt: "75574", contracted: 1890, medicare: 612, variance: 209 },
    { procedure: "Cardiac CT, calcium scoring", cpt: "75571", contracted: 285, medicare: 98, variance: 191 },
    { procedure: "Total knee arthroplasty", cpt: "27447", contracted: 4200, medicare: 1520, variance: 176 },
    { procedure: "Anterior cervical discectomy", cpt: "22551", contracted: 4800, medicare: 1843, variance: 160 },
    { procedure: "Total hip arthroplasty", cpt: "27130", contracted: 3600, medicare: 1487, variance: 142 },
    { procedure: "Stress echocardiogram", cpt: "93350", contracted: 580, medicare: 245, variance: 137 },
    { procedure: "Echocardiogram, complete", cpt: "93306", contracted: 390, medicare: 187, variance: 109 },
    { procedure: "Office visit, est. moderate", cpt: "99214", contracted: 165, medicare: 138, variance: 20 },
    { procedure: "Preventive visit, 40-64", cpt: "99396", contracted: 265, medicare: 250, variance: 6 },
  ];

  const varianceColor = (v) => v > 100 ? "#f87171" : v >= 20 ? "#fbbf24" : "#22c55e";

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "6px" }}>
        Carrier Contract Analysis &mdash; {COMPANY.name}
      </h2>
      <p style={{ fontSize: "14px", color: "#64748b", marginBottom: "28px" }}>
        Cigna PPO Fee Schedule &middot; Effective January 1, 2025 &middot; Parsed January 3, 2025
      </p>

      {/* Contract summary card */}
      <div style={{
        ...cardStyle,
        marginBottom: "24px",
      }}>
        <h3 style={h3Style}>Contract Summary</h3>
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "16px",
        }}>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
              Carrier
            </div>
            <div style={{ fontSize: "16px", fontWeight: "600", color: "#f1f5f9" }}>Cigna</div>
          </div>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
              Effective Date
            </div>
            <div style={{ fontSize: "16px", fontWeight: "600", color: "#f1f5f9" }}>January 1, 2025</div>
          </div>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
              Rate Basis
            </div>
            <div style={{ fontSize: "16px", fontWeight: "600", color: "#f1f5f9" }}>Fixed fee schedule</div>
          </div>
          <div>
            <div style={{ fontSize: "11px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "4px" }}>
              Total Procedures Parsed
            </div>
            <div style={{ fontSize: "16px", fontWeight: "600", color: "#f1f5f9" }}>847</div>
          </div>
        </div>
      </div>

      {/* Rate comparison table */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Rate Comparison &mdash; Top 10 by Variance</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Procedure</th>
                <th style={thStyle}>CPT</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Contracted Rate</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Medicare Rate</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Variance</th>
              </tr>
            </thead>
            <tbody>
              {contractRates.map((r) => (
                <tr key={r.cpt} style={{
                  background: r.variance > 100 ? "rgba(239,68,68,0.06)" : "transparent",
                }}>
                  <td style={tdStyle}>{r.procedure}</td>
                  <td style={{ ...tdStyle, fontFamily: "monospace", color: "#60a5fa" }}>{r.cpt}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(r.contracted)}</td>
                  <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>{fmt(r.medicare)}</td>
                  <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600", color: varianceColor(r.variance) }}>
                    +{r.variance}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI narrative */}
      <div style={{
        ...cardStyle,
        marginTop: "24px",
        borderLeft: "4px solid #3b82f6",
      }}>
        <div style={{
          fontSize: "11px", fontWeight: "600", color: "#60a5fa",
          textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "10px",
        }}>
          Contract Analysis
        </div>
        <p style={{ fontSize: "14px", lineHeight: "1.8", color: "#94a3b8", margin: 0 }}>
          Midwest Manufacturing&apos;s Cigna fee schedule shows contracted rates that are 2&ndash;4x Medicare
          for imaging and orthopedic procedures &mdash; the same categories driving your highest claims spend.
          This is not unusual for a standard PPO contract, but it confirms that your excess claims spend is a
          network pricing issue, not a utilization issue. Primary care contracted rates are competitive and close
          to Medicare. The highest leverage point for renegotiation is imaging: MRI rates at 335% of Medicare are
          well above what reference-based pricing or a direct imaging center contract could deliver.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 7: Monitoring Dashboard (Coming Soon)
// ---------------------------------------------------------------------------

function MonitoringTab() {
  const alerts = [
    {
      color: "#ef4444",
      label: "New Outlier Detected",
      body: "CT scans at Midwest Radiology averaged 4.8x Medicare in December (3 claims, $1,840 paid vs. $383 Medicare rate). This provider was at 2.9x in November. Recommend reviewing whether plan network terms allow steering or referral guidance.",
    },
    {
      color: "#f59e0b",
      label: "Spend Drift \u2014 Orthopedics",
      body: "Orthopedic spend increased 6.2% vs. November. Lakeview Orthopedics added 4 new claims at an average markup of 38% above benchmark. Cumulative 3-month trend is upward. Renewal is 47 days out \u2014 this data is included in your renewal prep report.",
    },
    {
      color: "#22c55e",
      label: "Cardiology Holding Steady",
      body: "Cardiology spend was flat vs. November. Prairie Heart Institute continues to perform at benchmark. No action needed.",
    },
  ];

  const renewalBullets = [
    "Orthopedic spend is 38% above industry benchmark \u2014 flagged with 12 months of claims evidence",
    "MRI and CT imaging: consistent 4\u20136x Medicare markups across 26 claims this year",
    "Plan design gap: no pharmacy carve-out costs an estimated $40\u201380 PEPM vs. best-in-class",
  ];

  const comparisonRows = [
    { dimension: "Review frequency", broker: "Annual renewal", parity: "Monthly" },
    { dimension: "Benchmark source", broker: "Carrier \u201cmarket rates\u201d", parity: "841,000 Medicare procedure rates \u2014 public and verifiable" },
    { dimension: "Conflicts of interest", broker: "Paid by carriers", parity: "No carrier relationships, no commissions" },
    { dimension: "Cost", broker: "$150K\u2013$300K/year (mid-market)", parity: "From $149/month" },
  ];

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: "28px" }}>
        <span
          style={{
            display: "inline-block",
            fontSize: "11px",
            fontWeight: "600",
            padding: "4px 10px",
            borderRadius: "6px",
            background: "rgba(59,130,246,0.15)",
            color: "#60a5fa",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            marginBottom: "12px",
          }}
        >
          Subscriber Report
        </span>
        <h2 style={{ ...h2Style, marginBottom: "6px" }}>
          Month 1 Monitoring Report &mdash; {COMPANY.name}
        </h2>
        <p style={{ fontSize: "14px", color: "#64748b" }}>
          December 2024 &middot; Generated January 3, 2025
        </p>
      </div>

      {/* Alert cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "36px" }}>
        {alerts.map((a) => (
          <div
            key={a.label}
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderLeft: `4px solid ${a.color}`,
              borderRadius: "12px",
              padding: "20px 24px",
            }}
          >
            <div style={{ fontSize: "14px", fontWeight: "600", color: a.color, marginBottom: "8px" }}>
              {a.label}
            </div>
            <p style={{ fontSize: "13px", lineHeight: "1.7", color: "#94a3b8", margin: 0 }}>
              {a.body}
            </p>
          </div>
        ))}
      </div>

      {/* Renewal prep */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Renewal Prep Report &mdash; Ready Now</h3>
        <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "16px" }}>
          Your renewal is January 20, 2025. Your broker meeting is in 3 weeks.
        </p>
        <ul style={{ margin: 0, paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "10px" }}>
          {renewalBullets.map((b, i) => (
            <li key={i} style={{ fontSize: "13px", lineHeight: "1.6", color: "#e2e8f0" }}>
              {b}
            </li>
          ))}
        </ul>
        <p style={{ fontSize: "12px", fontStyle: "italic", color: "#64748b", marginTop: "16px", marginBottom: 0 }}>
          This report is designed to be shared directly with your broker.
        </p>
      </div>

      {/* Comparison table */}
      <div style={{ ...cardStyle, marginTop: "24px" }}>
        <h3 style={h3Style}>What makes this different</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>&nbsp;</th>
                <th style={thStyle}>Your Broker</th>
                <th style={thStyle}>Parity Employer</th>
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((r) => (
                <tr key={r.dimension}>
                  <td style={{ ...tdStyle, fontWeight: "500", color: "#94a3b8", whiteSpace: "nowrap" }}>
                    {r.dimension}
                  </td>
                  <td style={{ ...tdStyle, color: "#64748b" }}>{r.broker}</td>
                  <td style={{ ...tdStyle, color: "#e2e8f0" }}>{r.parity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Feature preview cards */}
      <div style={{ marginTop: "36px" }}>
        <h3 style={{ ...h3Style, marginBottom: "20px" }}>What subscribers get</h3>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "16px",
        }}>
          {MONITORING_FEATURES.map((f) => (
            <div
              key={f.title}
              style={{
                ...cardStyle,
                padding: "20px",
              }}
            >
              <div style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0", marginBottom: "8px" }}>
                {f.title}
              </div>
              <p style={{ fontSize: "13px", lineHeight: "1.6", color: "#94a3b8", margin: 0 }}>
                {f.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared components & helpers
// ---------------------------------------------------------------------------

function StatCard({ label, value, accent, sub }) {
  return (
    <div
      style={{
        background: accent ? "rgba(59,130,246,0.08)" : "rgba(255,255,255,0.03)",
        border: `1px solid ${accent ? "rgba(59,130,246,0.25)" : "rgba(255,255,255,0.06)"}`,
        borderRadius: "12px",
        padding: "20px",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          fontWeight: "600",
          color: "#64748b",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          marginBottom: "6px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "24px",
          fontWeight: "700",
          color: accent ? "#60a5fa" : "#f1f5f9",
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function ordinal(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function fmt(n) {
  if (n >= 1000000) {
    return "$" + (n / 1000000).toFixed(1) + "M";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
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

const fieldLabel = {
  fontSize: "11px",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  marginBottom: "6px",
};

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

const gsFieldLabel = {
  fontSize: "11px",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  marginBottom: "4px",
};

const gsMockInput = {
  background: "#fff",
  border: "1px solid #CBD5E1",
  borderRadius: "6px",
  padding: "8px 12px",
  fontSize: "13px",
  color: "#1E293B",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
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
