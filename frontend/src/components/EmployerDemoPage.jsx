import { useState } from "react";
import { Link } from "react-router-dom";

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
];

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

const TABS = [
  { key: "start", label: "Getting Started" },
  { key: "benchmark", label: "Benefits Benchmark" },
  { key: "claims", label: "Claims Spot Check" },
  { key: "scorecard", label: "Plan Design Scorecard" },
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
        {activeTab === "monitoring" && <MonitoringTab />}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 1: Getting Started
// ---------------------------------------------------------------------------

function GettingStartedTab({ onNavigate }) {
  const navButtons = [
    { key: "benchmark", label: "Benefits Benchmark", desc: "See how your PEPM compares to industry medians" },
    { key: "claims", label: "Claims Spot Check", desc: "Review flagged procedures with excessive markups" },
    { key: "scorecard", label: "Plan Design Scorecard", desc: "Grade your plan design against 10 best-practice criteria" },
    { key: "monitoring", label: "Monitoring Dashboard", desc: "Preview ongoing monitoring and renewal prep tools" },
  ];

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "8px" }}>
        {COMPANY.name} &mdash; Interactive Demo
      </h2>
      <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", marginBottom: "32px" }}>
        Explore how Parity Employer found {fmt(COMPANY.potentialSavings)} in potential savings
        for a {COMPANY.lives}-person manufacturing company.
      </p>

      {/* Company snapshot */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Company Snapshot</h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: "20px",
          }}
        >
          {[
            { label: "Employees", value: COMPANY.lives.toLocaleString() },
            { label: "Industry", value: COMPANY.industry },
            { label: "State", value: COMPANY.state },
            { label: "Network", value: `${COMPANY.tpa} ${COMPANY.planType}` },
            { label: "Plan Year", value: COMPANY.planYear },
            { label: "Total Health Spend", value: fmt(COMPANY.totalSpend) },
          ].map((item) => (
            <div key={item.label}>
              <div style={fieldLabel}>{item.label}</div>
              <div style={{ fontSize: "16px", fontWeight: "600", color: "#f1f5f9" }}>
                {item.value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation buttons */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginTop: "28px",
        }}
      >
        {navButtons.map((btn) => (
          <button
            key={btn.key}
            onClick={() => onNavigate(btn.key)}
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "12px",
              padding: "20px",
              textAlign: "left",
              cursor: "pointer",
              fontFamily: "inherit",
              transition: "border-color 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "rgba(59,130,246,0.4)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)")}
          >
            <div style={{ fontSize: "14px", fontWeight: "600", color: "#60a5fa", marginBottom: "6px" }}>
              {btn.label} &rarr;
            </div>
            <div style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.5" }}>
              {btn.desc}
            </div>
          </button>
        ))}
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
// Tab 5: Monitoring Dashboard (Coming Soon)
// ---------------------------------------------------------------------------

function MonitoringTab() {
  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "8px" }}>What Ongoing Monitoring Delivers</h2>
      <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", marginBottom: "32px" }}>
        Parity Employer subscribers receive monthly intelligence reports that keep your
        benefits spend under control year-round.
      </p>

      {/* Feature cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "36px",
        }}
      >
        {MONITORING_FEATURES.map((feat, i) => (
          <div key={feat.title} style={cardStyle}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background: "rgba(59,130,246,0.15)",
                color: "#60a5fa",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: "700",
                marginBottom: "14px",
              }}
            >
              {i + 1}
            </div>
            <h4
              style={{
                fontSize: "15px",
                fontWeight: "600",
                color: "#e2e8f0",
                marginBottom: "8px",
              }}
            >
              {feat.title}
            </h4>
            <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.6" }}>
              {feat.description}
            </p>
          </div>
        ))}
      </div>

      {/* Pricing CTA */}
      <div
        style={{
          background: "rgba(59,130,246,0.06)",
          border: "1px solid rgba(59,130,246,0.2)",
          borderRadius: "12px",
          padding: "28px",
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: "14px", color: "#94a3b8", marginBottom: "8px" }}>
          {COMPANY.name} qualifies for the <strong style={{ color: "#e2e8f0" }}>Mid-Market tier</strong> &mdash; 101&ndash;500 employees
        </p>
        <div style={{ fontSize: "32px", fontWeight: "700", color: "#f1f5f9", marginBottom: "16px" }}>
          $799<span style={{ fontSize: "16px", fontWeight: "400", color: "#64748b" }}>/month</span>
        </div>
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
          Start Monitoring Subscription &rarr;
        </Link>
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
