import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// ─── Sample Book of Business data ────────────────────────────────────────────
const SAMPLE_CLIENTS = [
  { id: 1, name: "Midwest Manufacturing Co.", employees: 340, state: "IL", industry: "Manufacturing", carrier: "Cigna", planYear: "2025–2026", renewalDate: "2026-04-15", benchmarkStatus: "Analyzed", lastAnalysis: "Mar 5, 2026", pepm: 612, benchmarkPepm: 485, excessPct: 26, annualExcess: 51816, topClaims: [
    { cpt: "99214", desc: "Office visit, moderate complexity", billed: 340, medicare: 187, pctAbove: 82, provider: "Prairie Health Group" },
    { cpt: "93000", desc: "Electrocardiogram, 12-lead", billed: 310, medicare: 148, pctAbove: 109, provider: "Midwest Cardiology Associates" },
    { cpt: "85025", desc: "Complete blood count, automated", billed: 42, medicare: 8, pctAbove: 425, provider: "Quest Diagnostics" },
  ], topDrugs: [
    { drug: "Omeprazole 20mg", ndc: "62175-0118-37", paid: 22.30, nadac: 3.92, spreadPct: 469 },
    { drug: "Gabapentin 300mg", ndc: "27241-0050-03", paid: 32.40, nadac: 8.55, spreadPct: 279 },
  ]},
  { id: 2, name: "Prairie Logistics Group", employees: 185, state: "MO", industry: "Transportation / Utilities", carrier: "BCBS", planYear: "2025–2026", renewalDate: "2026-06-15", benchmarkStatus: "Analyzed", lastAnalysis: "Feb 28, 2026", pepm: 548, benchmarkPepm: 510, excessPct: 7, annualExcess: 8436, topClaims: [
    { cpt: "99213", desc: "Office visit, low complexity", billed: 165, medicare: 92, pctAbove: 79, provider: "Heartland Family Medicine" },
  ], topDrugs: [
    { drug: "Atorvastatin 40mg", ndc: "00378-3952-77", paid: 12.40, nadac: 3.18, spreadPct: 290 },
  ]},
  { id: 3, name: "Lakeview Financial Partners", employees: 92, state: "WI", industry: "Finance / Real Estate / Insurance", carrier: "UnitedHealth", planYear: "2025–2026", renewalDate: "2026-03-28", benchmarkStatus: "Analyzed", lastAnalysis: "Mar 8, 2026", pepm: 735, benchmarkPepm: 520, excessPct: 41, annualExcess: 23736, topClaims: [
    { cpt: "99214", desc: "Office visit, moderate complexity", billed: 380, medicare: 187, pctAbove: 103, provider: "Lakeview Medical Center" },
    { cpt: "71046", desc: "Chest X-ray, 2 views", billed: 340, medicare: 58, pctAbove: 486, provider: "Regional Imaging Center" },
  ], topDrugs: [
    { drug: "Amlodipine 5mg", ndc: "00093-3171-56", paid: 9.80, nadac: 2.15, spreadPct: 356 },
  ]},
  { id: 4, name: "Summit Construction LLC", employees: 210, state: "IN", industry: "Construction", carrier: "Aetna", planYear: "2025–2026", renewalDate: "2026-08-01", benchmarkStatus: "Pending", lastAnalysis: "—", pepm: 580, benchmarkPepm: 495, excessPct: 17, annualExcess: 21420, topClaims: [], topDrugs: [] },
  { id: 5, name: "Heartland Retail Group", employees: 425, state: "OH", industry: "Retail Trade", carrier: "BCBS", planYear: "2025–2026", renewalDate: "2026-12-01", benchmarkStatus: "Analyzed", lastAnalysis: "Mar 1, 2026", pepm: 498, benchmarkPepm: 470, excessPct: 6, annualExcess: 14280, topClaims: [
    { cpt: "99213", desc: "Office visit, low complexity", billed: 155, medicare: 92, pctAbove: 68, provider: "Midwest Primary Partners" },
  ], topDrugs: [] },
  { id: 6, name: "Great Plains Ag Supply", employees: 78, state: "KS", industry: "Agriculture / Forestry / Fishing", carrier: "Cigna", planYear: "2025–2026", renewalDate: "2026-04-01", benchmarkStatus: "Not started", lastAnalysis: "—", pepm: 695, benchmarkPepm: 475, excessPct: 46, annualExcess: 20592, topClaims: [], topDrugs: [] },
  { id: 7, name: "Riverdale Engineering", employees: 150, state: "MI", industry: "Professional Services", carrier: "Aetna", planYear: "2025–2026", renewalDate: "2026-09-15", benchmarkStatus: "Analyzed", lastAnalysis: "Feb 15, 2026", pepm: 558, benchmarkPepm: 512, excessPct: 9, annualExcess: 8280, topClaims: [
    { cpt: "99214", desc: "Office visit, moderate complexity", billed: 260, medicare: 187, pctAbove: 39, provider: "Great Lakes Medical" },
  ], topDrugs: [
    { drug: "Lisinopril 10mg", ndc: "00378-0831-01", paid: 8.50, nadac: 2.45, spreadPct: 247 },
  ]},
];

// ─── Prospect benchmark data (hardcoded for demo) ───────────────────────────
const PROSPECT_BENCHMARKS = {
  "Manufacturing": { variancePct: 28, pharmacySpreadPct: 22, medianPepm: 485 },
  "Construction": { variancePct: 24, pharmacySpreadPct: 18, medianPepm: 495 },
  "Finance / Real Estate / Insurance": { variancePct: 32, pharmacySpreadPct: 25, medianPepm: 520 },
  "Professional Services": { variancePct: 26, pharmacySpreadPct: 20, medianPepm: 512 },
  "Retail Trade": { variancePct: 22, pharmacySpreadPct: 17, medianPepm: 470 },
  "Transportation / Utilities": { variancePct: 25, pharmacySpreadPct: 19, medianPepm: 510 },
  "Agriculture / Forestry / Fishing": { variancePct: 30, pharmacySpreadPct: 23, medianPepm: 475 },
  "Wholesale Trade": { variancePct: 27, pharmacySpreadPct: 21, medianPepm: 490 },
  "Other Services": { variancePct: 29, pharmacySpreadPct: 22, medianPepm: 505 },
};

const INDUSTRIES = Object.keys(PROSPECT_BENCHMARKS);
const US_STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
  "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
  "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
];

// ─── CAA Letter Generator ────────────────────────────────────────────────────
function generateCAALetter(client) {
  const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  return `${today}

Via Email and Certified Mail

${client.carrier} Group Benefits
Claims Data Request Department
[Carrier Address]

Re: Request for Claims Data Under the Consolidated Appropriations Act
    Plan Sponsor: ${client.name}
    Group Policy Number: [Policy Number]
    Employer Size: ${client.employees} employees
    Plan Year: ${client.planYear}

Dear Claims Data Department,

Pursuant to Section 204 of Division BB of the Consolidated Appropriations Act of 2021 (CAA), and on behalf of our client ${client.name}, we are requesting the following claims data for the current and prior plan year:

1. MEDICAL CLAIMS DATA
   — Complete 835 Electronic Remittance Advice files for all processed claims
   — Allowed amounts, billed amounts, and paid amounts by CPT/HCPCS code
   — Provider-level detail including NPI, facility type, and network status
   — Geographic locality codes for all claims

2. PHARMACY CLAIMS DATA
   — All prescription claims including NDC codes, quantities dispensed, and amounts paid
   — Ingredient cost, dispensing fees, and any applicable rebate credits
   — Generic/brand classification and therapeutic class

3. PLAN COST SUMMARY
   — Monthly PEPM cost broken down by medical, pharmacy, and administrative fees
   — Stop-loss premiums and any pooling charges
   — Network access fees and other plan-level charges

This request is made pursuant to the fiduciary obligations established under ERISA §404(a)(1) and the transparency requirements of CAA §204. As the broker of record for ${client.name}, we are authorized to receive this information on behalf of the plan sponsor.

Please provide the requested data in electronic format (835 EDI preferred for medical claims, CSV acceptable for pharmacy) within 30 business days as required by applicable regulations.

If you have questions regarding this request, please contact me directly at the information below.

Sincerely,
[Broker Name]
[Firm Name]
[Email]
[Phone]

cc: ${client.name}, Benefits Director`;
}

// ─── Renewal urgency helper ──────────────────────────────────────────────────
function renewalUrgency(dateStr) {
  const days = Math.ceil((new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24));
  if (days < 0) return { color: "#94a3b8", label: "Past", days };
  if (days <= 30) return { color: "#ef4444", label: `${days}d`, days };
  if (days <= 90) return { color: "#f59e0b", label: `${days}d`, days };
  return { color: "#4ade80", label: `${days}d`, days };
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function BrokerLandingPage() {
  const [demoTab, setDemoTab] = useState("book");
  const [selectedClient, setSelectedClient] = useState(null);
  const [showCAALetter, setShowCAALetter] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [showConversion, setShowConversion] = useState(false);
  const { isAuthenticated, company } = useAuth();

  // Prospect form state
  const [prospectIndustry, setProspectIndustry] = useState("Manufacturing");
  const [prospectState, setProspectState] = useState("IL");
  const [prospectEmployees, setProspectEmployees] = useState("200");
  const [prospectResult, setProspectResult] = useState(null);

  const trackInteraction = useCallback(() => {
    if (!hasInteracted) {
      setHasInteracted(true);
      setTimeout(() => setShowConversion(true), 2000);
    }
  }, [hasInteracted]);

  const handleTabSwitch = useCallback((tab) => {
    setDemoTab(tab);
    if (tab !== "detail") {
      setSelectedClient(null);
      setShowCAALetter(false);
    }
    trackInteraction();
  }, [trackInteraction]);

  const handleClientClick = useCallback((client) => {
    setSelectedClient(client);
    setShowCAALetter(false);
    setDemoTab("detail");
    trackInteraction();
  }, [trackInteraction]);

  const handleProspectBenchmark = useCallback(() => {
    const bench = PROSPECT_BENCHMARKS[prospectIndustry] || PROSPECT_BENCHMARKS["Manufacturing"];
    const empCount = parseInt(prospectEmployees) || 200;
    const estExcess = Math.round(bench.medianPepm * (bench.variancePct / 100) * empCount * 12);
    setProspectResult({
      variancePct: bench.variancePct,
      pharmacySpreadPct: bench.pharmacySpreadPct,
      medianPepm: bench.medianPepm,
      estimatedAnnualExcess: estExcess,
      empCount,
    });
    trackInteraction();
  }, [prospectIndustry, prospectState, prospectEmployees, trackInteraction]);

  const renewalsIn90 = SAMPLE_CLIENTS.filter((c) => {
    const days = Math.ceil((new Date(c.renewalDate) - new Date()) / (1000 * 60 * 60 * 24));
    return days > 0 && days <= 90;
  }).length;
  const analysesComplete = SAMPLE_CLIENTS.filter((c) => c.benchmarkStatus === "Analyzed").length;

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* ── Header — matches EmployerProductPage ── */}
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.92)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" }}>CivicScale</span>
        </a>
        <nav style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 14 }}>
          {isAuthenticated && company?.type === "broker" ? (
            <>
              <Link to="/broker/dashboard" style={{ color: "#94a3b8", textDecoration: "none" }}>Dashboard</Link>
              <Link to="/broker/account" style={{ color: "#94a3b8", textDecoration: "none" }}>Account</Link>
            </>
          ) : (
            <>
              <Link to="/broker/login" style={{ color: "#94a3b8", textDecoration: "none", fontWeight: 500 }}>Sign In</Link>
              <Link to="/broker/signup" style={{ background: "#14b8a6", color: "#0a1628", textDecoration: "none", borderRadius: 6, padding: "8px 20px", fontWeight: 500, fontSize: 14 }}>
                Start Free Trial
              </Link>
            </>
          )}
        </nav>
      </header>

      {/* ── SECTION 1: Hero ── */}
      <section style={{ paddingTop: 120, paddingBottom: 56, maxWidth: 820, margin: "0 auto", textAlign: "center", padding: "120px 24px 56px" }}>
        <div style={{ display: "inline-block", background: "rgba(20,184,166,0.12)", borderRadius: 8, padding: "8px 14px", marginBottom: 24 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#14b8a6" }}>PARITY BROKER</span>
        </div>
        <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(30px, 4vw, 46px)", lineHeight: 1.15, fontWeight: 400, color: "#f1f5f9", marginBottom: 8, letterSpacing: "-0.02em" }}>
          For the first time, you can walk into every renewal with an independent benchmark for every client.
        </h1>
        <p style={{ fontSize: 22, fontWeight: 500, color: "#14b8a6", marginBottom: 20 }}>
          That changes what's possible.
        </p>
        <p style={{ fontSize: 17, lineHeight: 1.7, color: "#94a3b8", maxWidth: 680, margin: "0 auto 32px" }}>
          Parity Broker benchmarks every client's plan against Medicare rates and NADAC drug costs, generates CAA-compliant data request letters automatically, and tracks your entire book of business in one dashboard. Walk into every renewal meeting with findings your clients have never seen.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <a href="#demo" style={{ display: "inline-block", background: "#14b8a6", color: "#0a1628", padding: "12px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            See Your Dashboard &darr;
          </a>
          <a href="#demo" onClick={() => setTimeout(() => setDemoTab("prospect"), 100)} style={{ display: "inline-block", border: "1px solid rgba(20,184,166,0.4)", color: "#14b8a6", padding: "12px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            Benchmark a Prospect Free &rarr;
          </a>
        </div>
        <p style={{ fontSize: 13, color: "#64748b", marginTop: 16 }}>30-day free trial, cancel anytime</p>
        <Link to="/demo" style={{ display: "inline-block", marginTop: 8, color: "rgba(255,255,255,0.7)", fontSize: 14, textDecoration: "underline" }}>
          See a live demo first &rarr;
        </Link>
      </section>

      {/* ── SECTION 2: The Renewal Problem ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 780, margin: "0 auto" }}>
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(20,184,166,0.15)", borderRadius: 16, padding: "36px 40px" }}>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 24, fontWeight: 400, color: "#f1f5f9", marginBottom: 20 }}>
            What renewal season looks like now
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, fontSize: 15, lineHeight: 1.75, color: "#94a3b8" }}>
            <p style={{ margin: 0 }}>
              Every year, carriers bring renewal numbers to the table. Those numbers reflect the carrier's analysis of the plan data — claims experience, utilization patterns, cost trends. The analysis is real. Until now, it was usually the only analysis in the room.
            </p>
            <p style={{ margin: 0 }}>
              Most of the time, it is. The employer doesn't have an independent benchmark. The broker doesn't have time to build one for every client before renewal season hits. The carrier's numbers become the conversation.
            </p>
            <p style={{ margin: 0, color: "#cbd5e1" }}>
              Parity Broker changes that. For every client in your book, you have an independent benchmark — claims compared to Medicare rates, pharmacy spend compared to NADAC acquisition costs, renewal history tracked over time. You walk in with your own analysis. The conversation changes.
            </p>
            <p style={{ margin: 0, fontWeight: 500, color: "#14b8a6" }}>
              And when a client asks "why are our costs this high" — you have a specific answer, not a general one.
            </p>
          </div>
        </div>
      </section>

      {/* ── SECTION 3: Embedded Demo ── */}
      <section id="demo" style={{ padding: "0 24px 80px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", color: "#14b8a6", marginBottom: 12 }}>Interactive Demo</div>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 32, fontWeight: 400, color: "#f1f5f9", marginBottom: 12 }}>
            Your book of business — with data behind every client
          </h2>
          <p style={{ fontSize: 15, color: "#94a3b8", maxWidth: 600, margin: "0 auto" }}>
            This is sample data. Add your own clients during your free trial.
          </p>
        </div>

        {/* Demo container */}
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(20,184,166,0.2)", borderRadius: 16, overflow: "hidden" }}>

          {/* Tab bar */}
          <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            {[
              { key: "book", label: "Book of Business" },
              { key: "prospect", label: "Prospect Benchmark" },
              { key: "detail", label: selectedClient ? selectedClient.name : "Client Detail" },
            ].map((tab) => (
              <button key={tab.key} onClick={() => handleTabSwitch(tab.key)} style={{
                flex: 1, padding: "14px 0", background: demoTab === tab.key ? "rgba(20,184,166,0.08)" : "transparent",
                border: "none", borderBottom: demoTab === tab.key ? "2px solid #14b8a6" : "2px solid transparent",
                color: demoTab === tab.key ? "#14b8a6" : "#64748b", fontSize: 14, fontWeight: 600, cursor: "pointer",
                fontFamily: "'DM Sans', sans-serif", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              }}>{tab.label}{tab.key === "detail" && !selectedClient ? " (click a row)" : ""}</button>
            ))}
          </div>

          {/* ── TAB 1: Book of Business ── */}
          {demoTab === "book" && (
            <div>
              {/* Summary bar */}
              <div style={{ display: "flex", gap: 0, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {[
                  { value: SAMPLE_CLIENTS.length, label: "Clients", color: "#f1f5f9" },
                  { value: renewalsIn90, label: "Renewals in next 90 days", color: "#f59e0b" },
                  { value: analysesComplete, label: "Analyses complete", color: "#14b8a6" },
                ].map((s, i) => (
                  <div key={i} style={{ flex: 1, padding: "16px 20px", borderRight: i < 2 ? "1px solid rgba(255,255,255,0.06)" : "none" }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Table header */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 90px 100px 120px 100px", padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 11, fontWeight: 600, color: "#64748b", letterSpacing: 0.5, textTransform: "uppercase" }}>
                <span>Client</span>
                <span>Employees</span>
                <span>Plan Year</span>
                <span>Renewal Date</span>
                <span>Benchmark Status</span>
                <span>Last Analysis</span>
              </div>

              {/* Rows */}
              {SAMPLE_CLIENTS.map((client) => {
                const urg = renewalUrgency(client.renewalDate);
                return (
                  <div
                    key={client.id}
                    onClick={() => handleClientClick(client)}
                    style={{
                      display: "grid", gridTemplateColumns: "1fr 80px 90px 100px 120px 100px",
                      padding: "12px 16px", fontSize: 13, cursor: "pointer",
                      background: "transparent",
                      borderBottom: "1px solid rgba(255,255,255,0.03)",
                      borderLeft: urg.days <= 30 && urg.days > 0 ? "3px solid #ef4444" : urg.days <= 90 && urg.days > 0 ? "3px solid #f59e0b" : "3px solid transparent",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255,255,255,0.03)"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <span style={{ color: "#f1f5f9", fontWeight: 500 }}>{client.name}</span>
                    <span style={{ color: "#94a3b8" }}>{client.employees}</span>
                    <span style={{ color: "#94a3b8" }}>{client.planYear}</span>
                    <span>
                      <span style={{ color: urg.color, fontWeight: 600 }}>
                        {new Date(client.renewalDate).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                      </span>
                      <span style={{ color: "#64748b", fontSize: 11, marginLeft: 6 }}>({urg.label})</span>
                    </span>
                    <span>
                      <span style={{
                        display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 500,
                        background: client.benchmarkStatus === "Analyzed" ? "rgba(20,184,166,0.12)" : client.benchmarkStatus === "Pending" ? "rgba(245,158,11,0.12)" : "rgba(148,163,184,0.12)",
                        color: client.benchmarkStatus === "Analyzed" ? "#14b8a6" : client.benchmarkStatus === "Pending" ? "#f59e0b" : "#94a3b8",
                      }}>{client.benchmarkStatus}</span>
                    </span>
                    <span style={{ color: "#94a3b8" }}>{client.lastAnalysis}</span>
                  </div>
                );
              })}

              {/* Footer */}
              <div style={{ padding: "12px 16px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "#64748b" }}>
                  {SAMPLE_CLIENTS.length} clients &middot; Click any row to view client detail
                </span>
                <span style={{ fontSize: 11, color: "#475569" }}>Sample data &middot; Acme Benefits Group</span>
              </div>
            </div>
          )}

          {/* ── TAB 2: Prospect Benchmark ── */}
          {demoTab === "prospect" && (
            <div style={{ padding: 24 }}>
              <div style={{ marginBottom: 24 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", marginBottom: 16 }}>Run a prospect benchmark — no data needed</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 120px", gap: 12, alignItems: "end" }}>
                  <div>
                    <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#64748b", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>Industry</label>
                    <select value={prospectIndustry} onChange={(e) => setProspectIndustry(e.target.value)} style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", fontSize: 13, fontFamily: "'DM Sans', sans-serif" }}>
                      {INDUSTRIES.map((ind) => <option key={ind} value={ind}>{ind}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#64748b", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>State</label>
                    <select value={prospectState} onChange={(e) => setProspectState(e.target.value)} style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", fontSize: 13, fontFamily: "'DM Sans', sans-serif" }}>
                      {US_STATES.map((st) => <option key={st} value={st}>{st}</option>)}
                    </select>
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#64748b", marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>Estimated Employees</label>
                    <input type="number" value={prospectEmployees} onChange={(e) => setProspectEmployees(e.target.value)} style={{ width: "100%", padding: "8px 10px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", fontSize: 13, boxSizing: "border-box", fontFamily: "'DM Sans', sans-serif" }} />
                  </div>
                  <button onClick={handleProspectBenchmark} style={{ padding: "8px 16px", borderRadius: 6, background: "#14b8a6", color: "#0a1628", border: "none", fontWeight: 600, fontSize: 13, cursor: "pointer", fontFamily: "'DM Sans', sans-serif", height: 36 }}>
                    Run Benchmark
                  </button>
                </div>
              </div>

              {prospectResult && (
                <div style={{ background: "rgba(20,184,166,0.06)", border: "1px solid rgba(20,184,166,0.2)", borderRadius: 12, padding: 24, marginBottom: 20 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
                    {[
                      { label: "Avg. benchmark variance", value: `+${prospectResult.variancePct}%`, color: "#f59e0b" },
                      { label: "Typical pharmacy spread", value: `+${prospectResult.pharmacySpreadPct}%`, color: "#ef4444" },
                      { label: "Industry median PEPM", value: `$${prospectResult.medianPepm}`, color: "#14b8a6" },
                      { label: "Est. annual excess", value: `$${prospectResult.estimatedAnnualExcess.toLocaleString()}`, color: "#ef4444" },
                    ].map((m) => (
                      <div key={m.label} style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 28, fontWeight: 700, color: m.color }}>{m.value}</div>
                        <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{m.label}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ borderTop: "1px solid rgba(20,184,166,0.15)", paddingTop: 16 }}>
                    <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8", margin: "0 0 12px" }}>
                      A typical {prospectIndustry.toLowerCase()} employer with {prospectResult.empCount} employees in {prospectState} pays approximately {prospectResult.variancePct}% above Medicare benchmark rates. At industry median PEPM of ${prospectResult.medianPepm}, estimated annual excess spend is <strong style={{ color: "#ef4444" }}>${prospectResult.estimatedAnnualExcess.toLocaleString()}</strong>.
                    </p>
                    <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8", margin: "0 0 16px" }}>
                      Pharmacy claims in this segment typically show {prospectResult.pharmacySpreadPct}% spread above NADAC acquisition costs — a strong indicator of PBM margin that may be recoverable through contract renegotiation or plan design changes.
                    </p>
                    <p style={{ fontSize: 13, color: "#14b8a6", fontWeight: 600, margin: 0 }}>
                      Win the meeting. Walk in with this data before the prospect gives you anything.
                    </p>
                  </div>
                </div>
              )}

              {!prospectResult && (
                <div style={{ textAlign: "center", padding: "40px 0", color: "#64748b", fontSize: 14 }}>
                  Select an industry and state, then click Run Benchmark to see the analysis.
                </div>
              )}
            </div>
          )}

          {/* ── TAB 3: Client Detail ── */}
          {demoTab === "detail" && (
            <div style={{ padding: 24 }}>
              {!selectedClient ? (
                <div style={{ textAlign: "center", padding: "60px 24px" }}>
                  <p style={{ fontSize: 15, color: "#64748b" }}>Click a client row in the Book of Business tab to see their detail view.</p>
                  <button onClick={() => setDemoTab("book")} style={{
                    background: "rgba(20,184,166,0.12)", color: "#14b8a6", border: "1px solid rgba(20,184,166,0.3)",
                    borderRadius: 8, padding: "10px 24px", fontWeight: 600, fontSize: 14, cursor: "pointer", marginTop: 12,
                    fontFamily: "'DM Sans', sans-serif",
                  }}>Go to Book of Business</button>
                </div>
              ) : (
                <>
                  {/* Client header */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
                    <div>
                      <h3 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", margin: "0 0 6px" }}>{selectedClient.name}</h3>
                      <p style={{ fontSize: 14, color: "#94a3b8", margin: 0 }}>
                        {selectedClient.employees} employees &middot; {selectedClient.state} &middot; {selectedClient.industry} &middot; {selectedClient.carrier} &middot; {selectedClient.planYear}
                      </p>
                    </div>
                    <button onClick={() => setDemoTab("book")} style={{ background: "none", border: "1px solid rgba(255,255,255,0.15)", color: "#94a3b8", borderRadius: 6, padding: "6px 16px", fontSize: 12, cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}>
                      &larr; Back to Book
                    </button>
                  </div>

                  {/* Metrics row */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
                    {[
                      { label: "Current PEPM", value: `$${selectedClient.pepm}`, color: "#f1f5f9" },
                      { label: "Benchmark PEPM", value: `$${selectedClient.benchmarkPepm}`, color: "#14b8a6" },
                      { label: "Excess Above Benchmark", value: `+${selectedClient.excessPct}%`, color: selectedClient.excessPct > 20 ? "#ef4444" : "#f59e0b" },
                      { label: "Est. Annual Excess", value: `$${selectedClient.annualExcess.toLocaleString()}`, color: "#ef4444" },
                    ].map((m) => (
                      <div key={m.label} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 16, textAlign: "center" }}>
                        <div style={{ fontSize: 24, fontWeight: 700, color: m.color }}>{m.value}</div>
                        <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>{m.label}</div>
                      </div>
                    ))}
                  </div>

                  {/* Claims Benchmark */}
                  {selectedClient.topClaims.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                      <h4 style={{ fontSize: 14, fontWeight: 600, color: "#14b8a6", marginBottom: 12 }}>Claims Benchmark — Top Flagged</h4>
                      <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, overflow: "hidden" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "70px 1fr 1fr 90px 90px 80px", padding: "8px 12px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>
                          <span>CPT</span><span>Description</span><span>Provider</span><span style={{ textAlign: "right" }}>Billed</span><span style={{ textAlign: "right" }}>Medicare</span><span style={{ textAlign: "right" }}>Above</span>
                        </div>
                        {selectedClient.topClaims.map((claim, i) => (
                          <div key={i} style={{ display: "grid", gridTemplateColumns: "70px 1fr 1fr 90px 90px 80px", padding: "10px 12px", fontSize: 13, borderBottom: "1px solid rgba(255,255,255,0.03)", borderLeft: "3px solid #ef4444" }}>
                            <span style={{ color: "#60a5fa", fontFamily: "monospace", fontSize: 12 }}>{claim.cpt}</span>
                            <span style={{ color: "#cbd5e1" }}>{claim.desc}</span>
                            <span style={{ color: "#94a3b8" }}>{claim.provider}</span>
                            <span style={{ textAlign: "right", color: "#94a3b8" }}>${claim.billed}</span>
                            <span style={{ textAlign: "right", color: "#94a3b8" }}>${claim.medicare}</span>
                            <span style={{ textAlign: "right", color: "#ef4444", fontWeight: 600 }}>+{claim.pctAbove}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Pharmacy Analysis */}
                  {selectedClient.topDrugs.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                      <h4 style={{ fontSize: 14, fontWeight: 600, color: "#14b8a6", marginBottom: 12 }}>Pharmacy Analysis — Flagged Spread</h4>
                      <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, overflow: "hidden" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 140px 90px 90px 80px", padding: "8px 12px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>
                          <span>Drug</span><span>NDC</span><span style={{ textAlign: "right" }}>Plan Cost</span><span style={{ textAlign: "right" }}>NADAC</span><span style={{ textAlign: "right" }}>Spread</span>
                        </div>
                        {selectedClient.topDrugs.map((rx, i) => (
                          <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 140px 90px 90px 80px", padding: "10px 12px", fontSize: 13, borderBottom: "1px solid rgba(255,255,255,0.03)", borderLeft: "3px solid #f59e0b" }}>
                            <span style={{ color: "#cbd5e1" }}>{rx.drug}</span>
                            <span style={{ color: "#64748b", fontFamily: "monospace", fontSize: 11 }}>{rx.ndc}</span>
                            <span style={{ textAlign: "right", color: "#cbd5e1" }}>${rx.paid.toFixed(2)}</span>
                            <span style={{ textAlign: "right", color: "#94a3b8" }}>${rx.nadac.toFixed(2)}</span>
                            <span style={{ textAlign: "right", color: "#f59e0b", fontWeight: 600 }}>+{rx.spreadPct}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedClient.topClaims.length === 0 && selectedClient.topDrugs.length === 0 && (
                    <div style={{ padding: "24px 0", textAlign: "center", color: "#64748b", fontSize: 14, marginBottom: 24 }}>
                      No claims analysis available yet. Upload an 835 file to run the benchmark.
                    </div>
                  )}

                  {/* CAA Letter Generator */}
                  <div style={{ marginBottom: 16 }}>
                    <button
                      onClick={() => setShowCAALetter(!showCAALetter)}
                      style={{
                        background: showCAALetter ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.12)",
                        color: showCAALetter ? "#f87171" : "#60a5fa",
                        border: "1px solid " + (showCAALetter ? "rgba(239,68,68,0.3)" : "rgba(59,130,246,0.3)"),
                        borderRadius: 8, padding: "10px 20px", fontWeight: 600, fontSize: 13, cursor: "pointer",
                        fontFamily: "'DM Sans', sans-serif",
                      }}
                    >
                      {showCAALetter ? "Hide CAA Letter" : "Generate Data Request Letter"}
                    </button>
                  </div>

                  {showCAALetter && (
                    <div style={{ background: "#0f172a", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 10, padding: 20, position: "relative" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: "#60a5fa", letterSpacing: 1, textTransform: "uppercase" }}>CAA Data Request Letter — Draft</div>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            onClick={() => navigator.clipboard?.writeText(generateCAALetter(selectedClient))}
                            style={{ background: "rgba(59,130,246,0.12)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.3)", borderRadius: 6, padding: "4px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}
                          >Copy</button>
                          <button
                            onClick={() => window.print()}
                            style={{ background: "rgba(59,130,246,0.12)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.3)", borderRadius: 6, padding: "4px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}
                          >Print</button>
                        </div>
                      </div>
                      <pre style={{ fontSize: 12, lineHeight: 1.65, color: "#cbd5e1", whiteSpace: "pre-wrap", fontFamily: "'DM Sans', monospace", margin: 0 }}>
                        {generateCAALetter(selectedClient)}
                      </pre>
                      <div style={{ marginTop: 12, fontSize: 11, color: "#64748b", fontStyle: "italic" }}>
                        This letter is auto-generated from client data. Review, customize with your firm details and policy number, then send via email and certified mail.
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </section>

      {/* ── Conversion prompt ── */}
      {showConversion && (
        <div style={{
          position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 90,
          background: "linear-gradient(180deg, transparent, rgba(10,22,40,0.95) 30%)",
          padding: "40px 24px 24px", textAlign: "center",
        }}>
          <div style={{ maxWidth: 640, margin: "0 auto", background: "rgba(20,184,166,0.08)", border: "1px solid rgba(20,184,166,0.25)", borderRadius: 14, padding: "24px 32px", backdropFilter: "blur(12px)" }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>
              Start your free 30-day trial to add your own clients and run real analyses.
            </h3>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", alignItems: "center", flexWrap: "wrap", marginTop: 16 }}>
              <Link to="/broker/signup" style={{ background: "#14b8a6", color: "#0a1628", padding: "10px 24px", borderRadius: 8, fontWeight: 600, fontSize: 14, textDecoration: "none" }}>
                Start Free Trial &rarr;
              </Link>
              <button onClick={() => setShowConversion(false)} style={{ background: "none", border: "1px solid rgba(255,255,255,0.15)", color: "#94a3b8", padding: "10px 20px", borderRadius: 8, fontSize: 13, cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}>
                Dismiss
              </button>
            </div>
            <p style={{ fontSize: 11, color: "#64748b", marginTop: 10 }}>30-day free trial, cancel anytime</p>
          </div>
        </div>
      )}

      {/* ── SECTION 4: What You Get ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 960, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 40 }}>What You Get</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 24 }}>
          {FEATURE_CARDS.map((c) => (
            <div key={c.title} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(20,184,166,0.18)", borderRadius: 14, padding: 28 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(20,184,166,0.12)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16, color: "#14b8a6", fontSize: 18 }}>{c.icon}</div>
              <h3 style={{ fontSize: 17, fontWeight: 600, color: "#f1f5f9", marginBottom: 10 }}>{c.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8" }}>{c.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 5: How It Works ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 900, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 40 }}>How It Works</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 28 }}>
          {STEPS.map((s, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div style={{ width: 44, height: 44, borderRadius: "50%", background: "rgba(20,184,166,0.15)", color: "#14b8a6", fontWeight: 700, fontSize: 18, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>{i + 1}</div>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>{s.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8" }}>{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── SECTION 7: Pricing ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 600, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 12 }}>Simple Pricing</h2>
        <p style={{ fontSize: 14, color: "#94a3b8", textAlign: "center", marginBottom: 40, maxWidth: 520, marginLeft: "auto", marginRight: "auto" }}>
          One plan. Full access. Try free for 30 days.
        </p>
        <div style={{ background: "rgba(20,184,166,0.06)", border: "1px solid rgba(20,184,166,0.35)", borderRadius: 14, padding: 36, textAlign: "center" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#14b8a6", marginBottom: 8 }}>PARITY BROKER</div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 40, fontWeight: 700, color: "#f1f5f9" }}>$99</span>
            <span style={{ fontSize: 14, color: "#64748b" }}>/mo</span>
          </div>
          <div style={{ fontSize: 14, color: "#14b8a6", fontWeight: 600, marginBottom: 20 }}>30-day free trial &mdash; cancel anytime</div>
          <ul style={{ listStyle: "none", padding: 0, margin: "0 auto 24px", display: "flex", flexDirection: "column", gap: 10, maxWidth: 360, textAlign: "left" }}>
            {[
              "Unlimited clients",
              "Unlimited 835 uploads and benchmark analyses",
              "CAA letter generation",
              "Book-of-business dashboard with renewal tracking",
              "Prospect benchmarking tool",
              "Shared benchmark reports with client branding",
              "PDF report export",
            ].map((f) => (
              <li key={f} style={{ fontSize: 14, color: "#94a3b8", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ color: "#14b8a6" }}>&#10003;</span> {f}
              </li>
            ))}
          </ul>
          <Link to="/broker/signup" style={{ display: "inline-block", background: "#14b8a6", color: "#0a1628", borderRadius: 8, padding: "12px 32px", fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            Start Free Trial &rarr;
          </Link>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 16 }}>30-day free trial, cancel anytime</p>
        </div>
        <div style={{ textAlign: "center", marginTop: 20, fontSize: 14, color: "#94a3b8" }}>
          Managing your own employer plan too?{" "}
          <a href="https://employer.civicscale.ai" style={{ color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>Learn about Parity Employer &rarr;</a>
        </div>
      </section>

      {/* ── SECTION 8: Built on Public Data ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 780, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 24, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 32 }}>Built on Public Data</h2>
        <p style={{ fontSize: 14, color: "#64748b", textAlign: "center", marginBottom: 32 }}>Verified against current rates.</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
          {[
            { label: "CMS Physician Fee Schedule", detail: "841,000 rates updated annually, locality-adjusted" },
            { label: "NADAC Drug Acquisition Costs", detail: "Weekly CMS update, direct benchmark comparison" },
            { label: "NCCI Edit Pairs", detail: "2.2 million code pair edits for unbundling detection" },
            { label: "CAA 2021", detail: "Statutory data request language pre-populated in every letter" },
          ].map((d) => (
            <div key={d.label} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#14b8a6", marginBottom: 6 }}>{d.label}</div>
              <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>{d.detail}</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 13, color: "#64748b", textAlign: "center", marginTop: 20 }}>
          Your client data is yours. CivicScale will never contact, market to, or share data about any employer you add to your book of business.
        </p>
      </section>

      {/* ── Bottom CTA ── */}
      <section style={{ padding: "0 24px 80px", maxWidth: 600, margin: "0 auto", textAlign: "center" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 26, fontWeight: 400, color: "#f1f5f9", marginBottom: 16 }}>
          Ready to show up to your next renewal with better data than the carrier?
        </h2>
        <p style={{ fontSize: 15, color: "#94a3b8", marginBottom: 28, lineHeight: 1.7 }}>
          Start your free trial in 60 seconds. Add your first client in another 60.
        </p>
        <Link to="/broker/signup" style={{ display: "inline-block", background: "#14b8a6", color: "#0a1628", padding: "12px 32px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
          Start Free Trial &rarr;
        </Link>
      </section>

      {/* ── Footer ── */}
      <footer style={{ padding: "40px 24px", borderTop: "1px solid rgba(255,255,255,0.06)", textAlign: "center", fontSize: 13, color: "#475569" }}>
        <Link to="/" style={{ color: "#64748b", textDecoration: "none", marginRight: 24 }}>&larr; CivicScale Home</Link>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}

// ─── Static Data ─────────────────────────────────────────────────────────────

const FEATURE_CARDS = [
  {
    icon: "\u{1F4CA}",
    title: "Renewal Benchmarking",
    text: "For every client, an independent benchmark of their claims against Medicare rates and pharmacy spend against NADAC costs. Updated every time you upload a new 835. Walk into every renewal meeting with findings the carrier didn't give you.",
  },
  {
    icon: "\u{1F4C4}",
    title: "CAA Letter Generation",
    text: "Generate Consolidated Appropriations Act data request letters automatically — pre-populated with your client's plan information, carrier details, and the specific statutory language carriers are required to respond to. One click, professional document, ready to send.",
  },
  {
    icon: "\u{1F4CB}",
    title: "Book of Business Dashboard",
    text: "All your clients in one view. Renewal dates, benchmark status, last analysis date, and alert flags for clients whose renewal is approaching without a completed analysis. Never walk into a renewal unprepared because you ran out of time.",
  },
  {
    icon: "\u{1F50D}",
    title: "Prospect Benchmarking",
    text: "Before you walk into a prospect meeting, run a free benchmark showing how a typical plan in their industry and state compares to Medicare rates. Arrive with data before they've given you anything. Win the meeting before it starts.",
  },
];

const STEPS = [
  {
    title: "Add your clients",
    text: "Company name, employee count, plan year, renewal date. Takes 2 minutes per client.",
  },
  {
    title: "Upload and analyze",
    text: "Upload their 835 files when you have them — EDI, CSV, or Excel. Run the benchmark analysis. Review findings before your renewal meeting.",
  },
  {
    title: "Bring the data",
    text: "Generate CAA letters, share benchmark reports with your clients, and refer them to Parity Employer for ongoing monitoring.",
  },
];
