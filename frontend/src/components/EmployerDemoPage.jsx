import { useState } from "react";
import { Link } from "react-router-dom";

// ---------------------------------------------------------------------------
// Sample data — Midwest Manufacturing Co.
// ---------------------------------------------------------------------------

const COMPANY = {
  name: "Midwest Manufacturing Co.",
  lives: 500,
  tpa: "Cigna",
  planYear: "2025",
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

const SAVINGS_OPPORTUNITIES = [
  {
    title: "Switch orthopedic volume from Lakeview Ortho to Midwest Ortho Associates",
    savings: 180000,
    category: "Orthopedics",
    detail: "Lakeview Orthopedics charges 38% above benchmark for joint replacement and arthroscopy. Midwest Ortho Associates is within 3% of benchmark for the same procedures. Redirecting 50% of Lakeview volume to Midwest Ortho would save approximately $180K annually without reducing access.",
  },
  {
    title: "Establish center of excellence for knee/hip replacement",
    savings: 120000,
    category: "Orthopedics",
    detail: "Joint replacements are your highest per-procedure cost driver. A center-of-excellence arrangement with a benchmark-priced facility — requiring prior authorization for out-of-COE procedures — typically reduces total joint costs by 25-35%.",
  },
  {
    title: "Move outpatient imaging to freestanding centers",
    savings: 95000,
    category: "Imaging / Radiology",
    detail: "Hospital outpatient imaging averages $1,420 per study vs. $520 at freestanding imaging centers for identical procedures. Steering MRI and CT to freestanding ClearScan Imaging Center (already in-network) would save $95K with no quality difference.",
  },
  {
    title: "Negotiate cardiac imaging rates with Heartland Cardiology",
    savings: 45000,
    category: "Cardiology",
    detail: "Heartland Cardiology charges 24% above benchmark for echocardiograms and cardiac CT. Their cardiac MRI rate ($2,100) is 50% above the $1,400 benchmark. A targeted rate negotiation for imaging codes could recover $45K.",
  },
];

const TOP_3 = [
  { label: "Redirect orthopedic volume", savings: 180000, category: "Orthopedics" },
  { label: "Move imaging to freestanding", savings: 95000, category: "Imaging" },
  { label: "COE for joint replacements", savings: 120000, category: "Orthopedics" },
];

// ---------------------------------------------------------------------------
// Screens
// ---------------------------------------------------------------------------

const TABS = ["Executive Summary", "Category Deep Dive", "Provider Analysis", "Savings Report"];

export default function EmployerDemoPage() {
  const [tab, setTab] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState(1); // default Orthopedics
  const [selectedProvider, setSelectedProvider] = useState(0);
  const [expandedOpp, setExpandedOpp] = useState(null);

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
          {COMPANY.name} &middot; {COMPANY.lives} covered lives &middot; {COMPANY.tpa} TPA
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
              padding: "14px 20px",
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

      {/* Tab content */}
      <main style={{ padding: "32px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        {tab === 0 && (
          <ExecutiveSummary
            onDrillDown={(catIdx) => {
              setSelectedCategory(catIdx);
              setTab(1);
            }}
          />
        )}
        {tab === 1 && (
          <CategoryDeepDive
            category={CATEGORIES[selectedCategory]}
            categoryIndex={selectedCategory}
            onSelectCategory={setSelectedCategory}
            onDrillProvider={(provIdx) => {
              setSelectedProvider(provIdx);
              setTab(2);
            }}
          />
        )}
        {tab === 2 && (
          <ProviderAnalysis
            category={CATEGORIES[selectedCategory]}
            providerIndex={selectedProvider}
          />
        )}
        {tab === 3 && (
          <SavingsReport
            expandedOpp={expandedOpp}
            onToggleOpp={(i) => setExpandedOpp(expandedOpp === i ? null : i)}
          />
        )}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 1: Executive Summary
// ---------------------------------------------------------------------------

function ExecutiveSummary({ onDrillDown }) {
  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "28px" }}>Executive Summary</h2>

      {/* Top stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "16px",
          marginBottom: "36px",
        }}
      >
        <StatCard label="Total Spend" value={fmt(COMPANY.totalSpend)} />
        <StatCard label="Benchmark Spend" value={fmt(COMPANY.benchmarkSpend)} />
        <StatCard
          label="Potential Savings"
          value={fmt(COMPANY.potentialSavings)}
          accent
          sub={`${COMPANY.savingsPercent}% of total spend`}
        />
      </div>

      {/* Category bar chart */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Spending by Category</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          {CATEGORIES.map((cat, idx) => {
            const maxSpend = Math.max(...CATEGORIES.map((c) => c.spend));
            const spendPct = (cat.spend / maxSpend) * 100;
            const benchPct = (cat.benchmark / maxSpend) * 100;
            return (
              <div
                key={cat.name}
                style={{ cursor: "pointer" }}
                onClick={() => onDrillDown(idx)}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "4px",
                    fontSize: "13px",
                  }}
                >
                  <span style={{ color: "#e2e8f0", fontWeight: "500" }}>
                    {cat.name}
                  </span>
                  <span style={{ color: varianceColor(cat.variance) }}>
                    {cat.variance > 0 ? "+" : ""}
                    {cat.variance}%
                  </span>
                </div>
                <div
                  style={{
                    position: "relative",
                    height: "18px",
                    background: "rgba(255,255,255,0.04)",
                    borderRadius: "4px",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      height: "100%",
                      width: `${benchPct}%`,
                      background: "rgba(59,130,246,0.2)",
                      borderRadius: "4px",
                    }}
                  />
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      left: 0,
                      height: "100%",
                      width: `${spendPct}%`,
                      background: cat.variance > 20
                        ? "rgba(239,68,68,0.5)"
                        : cat.variance > 0
                        ? "rgba(251,191,36,0.5)"
                        : "rgba(34,197,94,0.5)",
                      borderRadius: "4px",
                    }}
                  />
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "11px",
                    color: "#64748b",
                    marginTop: "2px",
                  }}
                >
                  <span>Actual: {fmt(cat.spend)}</span>
                  <span>Benchmark: {fmt(cat.benchmark)}</span>
                </div>
              </div>
            );
          })}
        </div>
        <div
          style={{
            marginTop: "16px",
            display: "flex",
            gap: "20px",
            fontSize: "11px",
            color: "#64748b",
          }}
        >
          <span>
            <span
              style={{
                display: "inline-block",
                width: "10px",
                height: "10px",
                background: "rgba(59,130,246,0.3)",
                borderRadius: "2px",
                marginRight: "4px",
              }}
            />
            Benchmark
          </span>
          <span>
            <span
              style={{
                display: "inline-block",
                width: "10px",
                height: "10px",
                background: "rgba(251,191,36,0.5)",
                borderRadius: "2px",
                marginRight: "4px",
              }}
            />
            Actual
          </span>
        </div>
      </div>

      {/* Top 3 savings cards */}
      <h3 style={{ ...h3Style, marginTop: "32px", marginBottom: "16px" }}>
        Top Savings Opportunities
      </h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "16px",
        }}
      >
        {TOP_3.map((opp) => (
          <div key={opp.label} style={cardStyle}>
            <div
              style={{
                fontSize: "11px",
                fontWeight: "600",
                color: "#60a5fa",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                marginBottom: "6px",
              }}
            >
              {opp.category}
            </div>
            <div
              style={{
                fontSize: "22px",
                fontWeight: "700",
                color: "#4ade80",
                marginBottom: "6px",
              }}
            >
              {fmt(opp.savings)}
            </div>
            <p style={{ fontSize: "13px", color: "#94a3b8", lineHeight: "1.5" }}>
              {opp.label}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 2: Category Deep Dive
// ---------------------------------------------------------------------------

function CategoryDeepDive({ category, categoryIndex, onSelectCategory, onDrillProvider }) {
  return (
    <div>
      {/* Category selector */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          flexWrap: "wrap",
          marginBottom: "28px",
        }}
      >
        {CATEGORIES.map((cat, i) => (
          <button
            key={cat.name}
            onClick={() => onSelectCategory(i)}
            style={{
              padding: "6px 14px",
              fontSize: "12px",
              fontWeight: i === categoryIndex ? "600" : "400",
              background: i === categoryIndex ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.04)",
              color: i === categoryIndex ? "#60a5fa" : "#94a3b8",
              border: `1px solid ${i === categoryIndex ? "rgba(59,130,246,0.4)" : "rgba(255,255,255,0.08)"}`,
              borderRadius: "6px",
              cursor: "pointer",
              fontFamily: "inherit",
              transition: "all 0.15s",
            }}
          >
            {cat.name}
          </button>
        ))}
      </div>

      <h2 style={{ ...h2Style, marginBottom: "8px" }}>{category.name}</h2>
      <div
        style={{
          display: "flex",
          gap: "24px",
          fontSize: "13px",
          color: "#64748b",
          marginBottom: "28px",
          flexWrap: "wrap",
        }}
      >
        <span>Total Spend: <strong style={{ color: "#e2e8f0" }}>{fmt(category.spend)}</strong></span>
        <span>Benchmark: <strong style={{ color: "#e2e8f0" }}>{fmt(category.benchmark)}</strong></span>
        <span>
          Variance:{" "}
          <strong style={{ color: varianceColor(category.variance) }}>
            {category.variance > 0 ? "+" : ""}{category.variance}%
          </strong>
        </span>
        <span>{category.providers} providers &middot; {category.claims} claims</span>
      </div>

      {/* Procedure breakdown */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Procedure-Level Breakdown</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>CPT</th>
                <th style={thStyle}>Description</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Your Avg Cost</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Benchmark</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Variance</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Claims</th>
              </tr>
            </thead>
            <tbody>
              {category.procedures.map((p) => {
                const v = Math.round(((p.avgCost - p.benchmark) / p.benchmark) * 100);
                return (
                  <tr key={p.cpt}>
                    <td style={{ ...tdStyle, fontFamily: "monospace", color: "#60a5fa" }}>{p.cpt}</td>
                    <td style={tdStyle}>{p.desc}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(p.avgCost)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>{fmt(p.benchmark)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: varianceColor(v) }}>
                      {v > 0 ? "+" : ""}{v}%
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>{p.claims}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provider comparison */}
      <div style={{ ...cardStyle, marginTop: "24px" }}>
        <h3 style={h3Style}>Provider Comparison</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Provider</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Claims</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Avg Cost</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Benchmark</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Variance</th>
              </tr>
            </thead>
            <tbody>
              {category.topProviders.map((prov, i) => (
                <tr
                  key={prov.name}
                  style={{ cursor: "pointer" }}
                  onClick={() => onDrillProvider(i)}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(59,130,246,0.06)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <td style={{ ...tdStyle, color: "#60a5fa" }}>{prov.name}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{prov.claims}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(prov.avgCost)}</td>
                  <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>{fmt(prov.benchmark)}</td>
                  <td style={{ ...tdStyle, textAlign: "right", color: varianceColor(prov.variance) }}>
                    {prov.variance > 0 ? "+" : ""}{prov.variance}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 3: Provider Analysis
// ---------------------------------------------------------------------------

function ProviderAnalysis({ category, providerIndex }) {
  const prov = category.topProviders[providerIndex] || category.topProviders[0];
  const annualGap = Math.round((prov.avgCost - prov.benchmark) * prov.claims);
  const redirectSavings = Math.round(annualGap * 0.5);

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "8px" }}>{prov.name}</h2>
      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          fontSize: "13px",
          color: "#64748b",
          marginBottom: "28px",
        }}
      >
        <span>Specialty: <strong style={{ color: "#e2e8f0" }}>{category.name}</strong></span>
        <span>Network: <strong style={{ color: "#4ade80" }}>In-Network</strong></span>
        <span>{prov.claims} claims</span>
      </div>

      {/* Provider stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "16px",
          marginBottom: "28px",
        }}
      >
        <StatCard label="Avg Cost per Claim" value={fmt(prov.avgCost)} />
        <StatCard label="Benchmark Rate" value={fmt(prov.benchmark)} />
        <StatCard
          label="Variance"
          value={`${prov.variance > 0 ? "+" : ""}${prov.variance}%`}
          accent={prov.variance > 15}
        />
        <StatCard
          label="Annual Cost Gap"
          value={fmt(Math.abs(annualGap))}
          accent={annualGap > 0}
        />
      </div>

      {/* Claims table from this provider */}
      <div style={cardStyle}>
        <h3 style={h3Style}>Claims from This Provider</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>CPT</th>
                <th style={thStyle}>Description</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Billed</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Benchmark</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Variance</th>
              </tr>
            </thead>
            <tbody>
              {category.procedures.map((p) => {
                const cost = Math.round(p.avgCost * (1 + (prov.variance - category.variance) * 0.01));
                const v = Math.round(((cost - p.benchmark) / p.benchmark) * 100);
                return (
                  <tr key={p.cpt}>
                    <td style={{ ...tdStyle, fontFamily: "monospace", color: "#60a5fa" }}>{p.cpt}</td>
                    <td style={tdStyle}>{p.desc}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{fmt(cost)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: "#64748b" }}>{fmt(p.benchmark)}</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: varianceColor(v) }}>
                      {v > 0 ? "+" : ""}{v}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Insight callout */}
      {prov.variance > 10 && (
        <div
          style={{
            marginTop: "24px",
            background: "rgba(59,130,246,0.06)",
            border: "1px solid rgba(59,130,246,0.2)",
            borderRadius: "12px",
            padding: "24px",
          }}
        >
          <h4
            style={{
              fontSize: "14px",
              fontWeight: "600",
              color: "#60a5fa",
              marginBottom: "8px",
            }}
          >
            Savings Insight
          </h4>
          <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>
            This provider charges {prov.variance}% above the regional average for{" "}
            {category.name.toLowerCase()} procedures. Redirecting 50% of volume to
            benchmark-priced alternatives could save{" "}
            <strong style={{ color: "#4ade80" }}>
              {fmt(redirectSavings)}
            </strong>{" "}
            annually.
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Screen 4: Savings Report
// ---------------------------------------------------------------------------

function SavingsReport({ expandedOpp, onToggleOpp }) {
  const totalSavings = SAVINGS_OPPORTUNITIES.reduce((s, o) => s + o.savings, 0);

  return (
    <div>
      <h2 style={{ ...h2Style, marginBottom: "8px" }}>Savings Report</h2>
      <p style={{ fontSize: "14px", color: "#64748b", marginBottom: "28px" }}>
        Prioritized opportunities ranked by dollar impact.
      </p>

      {/* Total callout */}
      <div
        style={{
          background: "rgba(34,197,94,0.08)",
          border: "1px solid rgba(34,197,94,0.2)",
          borderRadius: "12px",
          padding: "24px",
          textAlign: "center",
          marginBottom: "32px",
        }}
      >
        <div style={{ fontSize: "12px", color: "#4ade80", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "6px" }}>
          Total Identified Savings (Top {SAVINGS_OPPORTUNITIES.length})
        </div>
        <div style={{ fontSize: "36px", fontWeight: "700", color: "#4ade80" }}>
          {fmt(totalSavings)}
        </div>
      </div>

      {/* Opportunities list */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {SAVINGS_OPPORTUNITIES.map((opp, i) => (
          <div key={i} style={cardStyle}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                cursor: "pointer",
              }}
              onClick={() => onToggleOpp(i)}
            >
              <div>
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: "600",
                    color: "#60a5fa",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    marginBottom: "4px",
                  }}
                >
                  {opp.category}
                </div>
                <div style={{ fontSize: "15px", fontWeight: "500", color: "#e2e8f0" }}>
                  {i + 1}. {opp.title}
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "20px", fontWeight: "700", color: "#4ade80" }}>
                  {fmt(opp.savings)}
                </div>
                <div style={{ fontSize: "11px", color: "#64748b" }}>annual</div>
              </div>
            </div>
            {expandedOpp === i && (
              <div
                style={{
                  marginTop: "16px",
                  paddingTop: "16px",
                  borderTop: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>
                  {opp.detail}
                </p>
              </div>
            )}
          </div>
        ))}
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

function varianceColor(v) {
  if (v > 20) return "#f87171";
  if (v > 0) return "#fbbf24";
  return "#4ade80";
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
