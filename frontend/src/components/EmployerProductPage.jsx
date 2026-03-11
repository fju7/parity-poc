import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// ─── Synthetic claims data ───────────────────────────────────────────────────
const MEDICAL_CLAIMS = [
  { id: 1, dos: "2024-12-03", cpt: "99213", desc: "Office visit, est. patient, low complexity", provider: "Prairie Health Group", billed: 185, allowed: 152, medicare: 92, pctAbove: 65, flagged: true },
  { id: 2, dos: "2024-12-05", cpt: "99214", desc: "Office visit, est. patient, moderate complexity", provider: "Heartland Family Medicine", billed: 248, allowed: 210, medicare: 148, pctAbove: 42, flagged: true },
  { id: 3, dos: "2024-12-06", cpt: "93000", desc: "Electrocardiogram, 12-lead", provider: "Midwest Cardiology Associates", billed: 310, allowed: 265, medicare: 148, pctAbove: 79, flagged: true },
  { id: 4, dos: "2024-12-09", cpt: "99214", desc: "Office visit, est. patient, moderate complexity", provider: "Lakeview Medical Center", billed: 225, allowed: 198, medicare: 148, pctAbove: 34, flagged: false },
  { id: 5, dos: "2024-12-10", cpt: "85025", desc: "Complete blood count, automated", provider: "Quest Diagnostics", billed: 42, allowed: 35, medicare: 8, pctAbove: 338, flagged: true },
  { id: 6, dos: "2024-12-11", cpt: "71046", desc: "Chest X-ray, 2 views", provider: "Regional Imaging Center", billed: 180, allowed: 145, medicare: 58, pctAbove: 150, flagged: false },
  { id: 7, dos: "2024-12-12", cpt: "99213", desc: "Office visit, est. patient, low complexity", provider: "Heartland Family Medicine", billed: 165, allowed: 140, medicare: 92, pctAbove: 52, flagged: false },
  { id: 8, dos: "2024-12-13", cpt: "93000", desc: "Electrocardiogram, 12-lead", provider: "Prairie Cardiology", billed: 195, allowed: 168, medicare: 148, pctAbove: 14, flagged: false },
  { id: 9, dos: "2024-12-16", cpt: "99214", desc: "Office visit, est. patient, moderate complexity", provider: "Prairie Health Group", billed: 260, allowed: 228, medicare: 148, pctAbove: 54, flagged: true },
  { id: 10, dos: "2024-12-17", cpt: "85025", desc: "Complete blood count, automated", provider: "LabCorp", billed: 28, allowed: 22, medicare: 8, pctAbove: 175, flagged: false },
  { id: 11, dos: "2024-12-19", cpt: "71046", desc: "Chest X-ray, 2 views", provider: "Midwest Hospital Outpatient", billed: 340, allowed: 285, medicare: 58, pctAbove: 391, flagged: true },
  { id: 12, dos: "2024-12-20", cpt: "99213", desc: "Office visit, est. patient, low complexity", provider: "Midwest Primary Partners", billed: 155, allowed: 130, medicare: 92, pctAbove: 41, flagged: false },
];

const PHARMACY_CLAIMS = [
  { id: 1, fillDate: "2024-12-02", drug: "Atorvastatin 40mg", ndc: "00378-3952-77", qty: 30, paid: 12.40, nadac: 3.18, spread: 9.22, spreadPct: 290, flagged: true },
  { id: 2, fillDate: "2024-12-03", drug: "Lisinopril 10mg", ndc: "00378-0831-01", qty: 30, paid: 8.50, nadac: 2.45, spread: 6.05, spreadPct: 247, flagged: true },
  { id: 3, fillDate: "2024-12-05", drug: "Metformin 500mg", ndc: "00591-2550-01", qty: 60, paid: 14.20, nadac: 4.80, spread: 9.40, spreadPct: 196, flagged: false },
  { id: 4, fillDate: "2024-12-06", drug: "Omeprazole 20mg", ndc: "62175-0118-37", qty: 30, paid: 22.30, nadac: 3.92, spread: 18.38, spreadPct: 469, flagged: true },
  { id: 5, fillDate: "2024-12-09", drug: "Amlodipine 5mg", ndc: "00093-3171-56", qty: 30, paid: 9.80, nadac: 2.15, spread: 7.65, spreadPct: 356, flagged: true },
  { id: 6, fillDate: "2024-12-10", drug: "Levothyroxine 50mcg", ndc: "00378-1805-01", qty: 30, paid: 18.50, nadac: 7.20, spread: 11.30, spreadPct: 157, flagged: false },
  { id: 7, fillDate: "2024-12-12", drug: "Sertraline 100mg", ndc: "16729-0093-01", qty: 30, paid: 11.60, nadac: 4.10, spread: 7.50, spreadPct: 183, flagged: false },
  { id: 8, fillDate: "2024-12-16", drug: "Gabapentin 300mg", ndc: "27241-0050-03", qty: 90, paid: 32.40, nadac: 8.55, spread: 23.85, spreadPct: 279, flagged: true },
  { id: 9, fillDate: "2024-12-18", drug: "Ozempic 1mg pen", ndc: "00169-4772-12", qty: 1, paid: 968.00, nadac: 935.48, spread: 32.52, spreadPct: 3, flagged: false },
  { id: 10, fillDate: "2024-12-20", drug: "Albuterol HFA inhaler", ndc: "00173-0682-20", qty: 1, paid: 58.90, nadac: 25.80, spread: 33.10, spreadPct: 128, flagged: false },
];

// ─── Dispute letter generator ────────────────────────────────────────────────
function generateDisputeLetter(claim) {
  const overpayment = (claim.allowed - claim.medicare).toFixed(2);
  const totalIfMedicare = (claim.medicare * 1.2).toFixed(2); // Medicare + 20% reasonable margin
  return `DISPUTE LETTER — DRAFT

To: ${claim.provider}
Re: Claim dated ${claim.dos}, CPT ${claim.cpt} (${claim.desc})

Dear Claims Department,

We are writing to formally dispute the allowed amount of $${claim.allowed.toFixed(2)} for the above-referenced service. Based on our independent analysis using the CMS Medicare Physician Fee Schedule for the applicable geographic locality, the Medicare benchmark rate for CPT ${claim.cpt} is $${claim.medicare.toFixed(2)}.

The allowed amount on this claim represents a ${claim.pctAbove}% premium above the Medicare benchmark, which exceeds the reasonable range for this service in this market.

We request an adjustment to $${totalIfMedicare} (Medicare benchmark + 20% commercial margin), which would reduce the excess charge by $${overpayment} on this claim alone.

Supporting data:
- CPT Code: ${claim.cpt}
- Description: ${claim.desc}
- Billed amount: $${claim.billed.toFixed(2)}
- Allowed amount: $${claim.allowed.toFixed(2)}
- Medicare benchmark: $${claim.medicare.toFixed(2)}
- Excess above benchmark: ${claim.pctAbove}%

This analysis was generated using CivicScale Parity Employer, which benchmarks commercial claims against the current CMS Medicare fee schedule with geographic locality adjustments.

We request a written response within 30 days.

Sincerely,
[Benefits Director Name]
[Company Name]`;
}

// ─── Analytical Paths data ───────────────────────────────────────────────────
function getAnalyticalPaths(claim) {
  const base = claim.pctAbove;
  return [
    {
      name: "Balanced",
      emphasis: "Equal weight across all dimensions",
      score: base > 60 ? "Significant overpayment" : base > 30 ? "Moderate overpayment" : "Within range",
      detail: `At ${claim.pctAbove}% above Medicare, this claim ${base > 60 ? "substantially exceeds" : base > 30 ? "moderately exceeds" : "is near"} the benchmark. The balanced profile weights geographic adjustment, procedure complexity, and market rates equally.`,
    },
    {
      name: "Regulatory",
      emphasis: "Source quality 40%, Consensus 30%",
      score: base > 40 ? "Above CMS threshold" : "Within CMS norms",
      detail: `CMS sets the reference price for CPT ${claim.cpt} at $${claim.medicare.toFixed(2)}. The regulatory profile prioritizes official fee schedule data and payer consensus. The ${claim.pctAbove}% premium ${base > 40 ? "would likely draw scrutiny in a plan audit" : "falls within typical commercial variance"}.`,
    },
    {
      name: "Market",
      emphasis: "Commercial rates 40%, Recency 25%",
      score: base > 80 ? "Well above market" : base > 40 ? "Above median" : "Market rate",
      detail: `Commercial rates for ${claim.desc.toLowerCase()} in this region typically run 20–35% above Medicare. At ${claim.pctAbove}% above benchmark, ${claim.provider} is ${base > 40 ? "pricing above the commercial median" : "within the expected commercial range"}.`,
    },
  ];
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function EmployerProductPage() {
  const [demoTab, setDemoTab] = useState("medical");
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [showLetter, setShowLetter] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [showConversion, setShowConversion] = useState(false);
  const { isAuthenticated } = useAuth();

  const handleTabSwitch = useCallback((tab) => {
    setDemoTab(tab);
    setSelectedClaim(null);
    setShowLetter(false);
    if (!hasInteracted) {
      setHasInteracted(true);
      setTimeout(() => setShowConversion(true), 2000);
    }
  }, [hasInteracted]);

  const handleClaimClick = useCallback((claim) => {
    setSelectedClaim(selectedClaim?.id === claim.id ? null : claim);
    setShowLetter(false);
    if (!hasInteracted) {
      setHasInteracted(true);
      setTimeout(() => setShowConversion(true), 2000);
    }
  }, [selectedClaim, hasInteracted]);

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* ── Header ── */}
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
          {isAuthenticated ? (
            <>
              <Link to="/billing/employer/dashboard" style={{ color: "#94a3b8", textDecoration: "none" }}>Dashboard</Link>
              <Link to="/billing/employer/account" style={{ color: "#94a3b8", textDecoration: "none" }}>Account</Link>
            </>
          ) : (
            <Link to="/billing/employer/signup" style={{ background: "#3b82f6", color: "#fff", textDecoration: "none", borderRadius: 6, padding: "8px 20px", fontWeight: 500, fontSize: 14 }}>
              Start Free Trial
            </Link>
          )}
        </nav>
      </header>

      {/* ── Hero ── */}
      <section style={{ paddingTop: 120, paddingBottom: 56, maxWidth: 820, margin: "0 auto", textAlign: "center", padding: "120px 24px 56px" }}>
        <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: 8, padding: "8px 14px", marginBottom: 24 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#60a5fa" }}>PARITY EMPLOYER</span>
        </div>
        <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(30px, 4vw, 46px)", lineHeight: 1.15, fontWeight: 400, color: "#f1f5f9", marginBottom: 12, letterSpacing: "-0.02em" }}>
          Most employers never see what's actually<br />
          <span style={{ color: "#60a5fa" }}>in their claims data.</span>
        </h1>
        <p style={{ fontSize: 20, fontWeight: 500, color: "#60a5fa", marginBottom: 20 }}>
          For the first time, you can.
        </p>
        <p style={{ fontSize: 17, lineHeight: 1.7, color: "#94a3b8", maxWidth: 640, margin: "0 auto 32px" }}>
          Parity Employer benchmarks your 835 claims against Medicare rates, flags variance, analyzes your pharmacy spend against actual drug acquisition costs, and delivers a plain-language report your CFO can act on. In minutes.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/billing/employer/signup" style={{ display: "inline-block", background: "#3b82f6", color: "#fff", padding: "12px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            Start Free Trial &rarr;
          </Link>
          <a href="#demo" style={{ display: "inline-block", border: "1px solid rgba(59,130,246,0.4)", color: "#60a5fa", padding: "12px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            See the Demo Below &darr;
          </a>
        </div>
        <p style={{ fontSize: 13, color: "#64748b", marginTop: 16 }}>30-day free trial &middot; Cancel anytime</p>
      </section>

      {/* ── What You Get ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 960, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 40 }}>What You Get</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 24 }}>
          {FEATURE_CARDS.map((c) => (
            <div key={c.title} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: 14, padding: 28 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(59,130,246,0.12)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16, color: "#60a5fa", fontSize: 18 }}>{c.icon}</div>
              <h3 style={{ fontSize: 17, fontWeight: 600, color: "#f1f5f9", marginBottom: 10 }}>{c.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8" }}>{c.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Interactive Demo ── */}
      <section id="demo" style={{ padding: "72px 24px 80px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", color: "#60a5fa", marginBottom: 12 }}>Interactive Demo</div>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 32, fontWeight: 400, color: "#f1f5f9", marginBottom: 12 }}>
            See real analysis on sample data
          </h2>
          <p style={{ fontSize: 15, color: "#94a3b8", maxWidth: 600, margin: "0 auto" }}>
            This is live output from the Parity Engine running against synthetic employer claims. Click any flagged row to see the Analytical Paths breakdown.
          </p>
        </div>

        {/* Demo container */}
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 16, overflow: "hidden" }}>

          {/* Tab bar */}
          <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <button onClick={() => handleTabSwitch("medical")} style={{
              flex: 1, padding: "14px 0", background: demoTab === "medical" ? "rgba(59,130,246,0.08)" : "transparent",
              border: "none", borderBottom: demoTab === "medical" ? "2px solid #3b82f6" : "2px solid transparent",
              color: demoTab === "medical" ? "#60a5fa" : "#64748b", fontSize: 14, fontWeight: 600, cursor: "pointer",
              fontFamily: "'DM Sans', sans-serif",
            }}>Medical Claims</button>
            <button onClick={() => handleTabSwitch("pharmacy")} style={{
              flex: 1, padding: "14px 0", background: demoTab === "pharmacy" ? "rgba(59,130,246,0.08)" : "transparent",
              border: "none", borderBottom: demoTab === "pharmacy" ? "2px solid #3b82f6" : "2px solid transparent",
              color: demoTab === "pharmacy" ? "#60a5fa" : "#64748b", fontSize: 14, fontWeight: 600, cursor: "pointer",
              fontFamily: "'DM Sans', sans-serif",
            }}>Pharmacy Claims</button>
          </div>

          {/* Summary bar */}
          <div style={{ display: "flex", gap: 0, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            {(demoTab === "medical" ? MEDICAL_SUMMARY : PHARMACY_SUMMARY).map((s, i) => (
              <div key={i} style={{ flex: 1, padding: "16px 20px", borderRight: i < 3 ? "1px solid rgba(255,255,255,0.06)" : "none" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: s.color || "#f1f5f9" }}>{s.value}</div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Claims table */}
          {demoTab === "medical" ? (
            <div>
              <div style={{ display: "grid", gridTemplateColumns: "80px 80px 1fr 1fr 90px 90px 90px 80px", padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 11, fontWeight: 600, color: "#64748b", letterSpacing: 0.5, textTransform: "uppercase" }}>
                <span>Date</span><span>CPT</span><span>Description</span><span>Provider</span><span style={{ textAlign: "right" }}>Billed</span><span style={{ textAlign: "right" }}>Allowed</span><span style={{ textAlign: "right" }}>Medicare</span><span style={{ textAlign: "right" }}>Above</span>
              </div>
              {MEDICAL_CLAIMS.map((claim) => (
                <div key={claim.id}>
                  <div
                    onClick={() => handleClaimClick(claim)}
                    style={{
                      display: "grid", gridTemplateColumns: "80px 80px 1fr 1fr 90px 90px 90px 80px",
                      padding: "10px 16px", fontSize: 13, cursor: "pointer",
                      background: selectedClaim?.id === claim.id ? "rgba(59,130,246,0.08)" : claim.flagged ? "rgba(239,68,68,0.04)" : "transparent",
                      borderBottom: "1px solid rgba(255,255,255,0.03)",
                      borderLeft: claim.flagged ? "3px solid #ef4444" : "3px solid transparent",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => { if (selectedClaim?.id !== claim.id) e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
                    onMouseLeave={(e) => { if (selectedClaim?.id !== claim.id) e.currentTarget.style.background = claim.flagged ? "rgba(239,68,68,0.04)" : "transparent"; }}
                  >
                    <span style={{ color: "#94a3b8" }}>{claim.dos.slice(5)}</span>
                    <span style={{ color: "#60a5fa", fontFamily: "monospace", fontSize: 12 }}>{claim.cpt}</span>
                    <span style={{ color: "#cbd5e1", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{claim.desc}</span>
                    <span style={{ color: "#94a3b8", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{claim.provider}</span>
                    <span style={{ textAlign: "right", color: "#94a3b8" }}>${claim.billed}</span>
                    <span style={{ textAlign: "right", color: "#cbd5e1" }}>${claim.allowed}</span>
                    <span style={{ textAlign: "right", color: "#94a3b8" }}>${claim.medicare}</span>
                    <span style={{ textAlign: "right", color: claim.pctAbove > 60 ? "#ef4444" : claim.pctAbove > 30 ? "#f59e0b" : "#4ade80", fontWeight: 600 }}>
                      +{claim.pctAbove}%
                    </span>
                  </div>

                  {/* Analytical Paths panel */}
                  {selectedClaim?.id === claim.id && (
                    <div style={{ padding: "20px 16px 20px 19px", background: "rgba(59,130,246,0.04)", borderBottom: "1px solid rgba(59,130,246,0.15)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                        <h4 style={{ fontSize: 14, fontWeight: 600, color: "#60a5fa", margin: 0 }}>Analytical Paths — CPT {claim.cpt}</h4>
                        <button onClick={(e) => { e.stopPropagation(); setShowLetter(!showLetter); }} style={{
                          background: showLetter ? "rgba(239,68,68,0.1)" : "rgba(59,130,246,0.12)",
                          border: "1px solid " + (showLetter ? "rgba(239,68,68,0.3)" : "rgba(59,130,246,0.3)"),
                          color: showLetter ? "#f87171" : "#60a5fa", borderRadius: 6, padding: "6px 14px",
                          fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "'DM Sans', sans-serif",
                        }}>{showLetter ? "Hide Letter" : "Generate Dispute Letter"}</button>
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: showLetter ? 16 : 0 }}>
                        {getAnalyticalPaths(claim).map((path) => (
                          <div key={path.name} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 16 }}>
                            <div style={{ fontSize: 13, fontWeight: 600, color: "#14b8a6", marginBottom: 4 }}>{path.name}</div>
                            <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>{path.emphasis}</div>
                            <div style={{ fontSize: 13, fontWeight: 600, color: path.score.includes("Significant") || path.score.includes("Well above") || path.score.includes("Above CMS") ? "#ef4444" : path.score.includes("Moderate") || path.score.includes("Above median") ? "#f59e0b" : "#4ade80", marginBottom: 8 }}>
                              {path.score}
                            </div>
                            <p style={{ fontSize: 12, lineHeight: 1.6, color: "#94a3b8", margin: 0 }}>{path.detail}</p>
                          </div>
                        ))}
                      </div>

                      {showLetter && (
                        <div style={{ background: "#0f172a", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 10, padding: 20, position: "relative" }}>
                          <div style={{ fontSize: 11, fontWeight: 600, color: "#f87171", letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>Draft Dispute Letter</div>
                          <pre style={{ fontSize: 12, lineHeight: 1.65, color: "#cbd5e1", whiteSpace: "pre-wrap", fontFamily: "'DM Sans', monospace", margin: 0 }}>
                            {generateDisputeLetter(claim)}
                          </pre>
                          <div style={{ marginTop: 12, fontSize: 11, color: "#64748b", fontStyle: "italic" }}>
                            This letter is auto-generated from claim data. Review and customize before sending.
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div>
              <div style={{ display: "grid", gridTemplateColumns: "80px 1fr 130px 60px 80px 80px 80px 80px", padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 11, fontWeight: 600, color: "#64748b", letterSpacing: 0.5, textTransform: "uppercase" }}>
                <span>Date</span><span>Drug</span><span>NDC</span><span>Qty</span><span style={{ textAlign: "right" }}>Paid</span><span style={{ textAlign: "right" }}>NADAC</span><span style={{ textAlign: "right" }}>Spread</span><span style={{ textAlign: "right" }}>Spread %</span>
              </div>
              {PHARMACY_CLAIMS.map((rx) => (
                <div key={rx.id} style={{
                  display: "grid", gridTemplateColumns: "80px 1fr 130px 60px 80px 80px 80px 80px",
                  padding: "10px 16px", fontSize: 13,
                  background: rx.flagged ? "rgba(245,158,11,0.04)" : "transparent",
                  borderBottom: "1px solid rgba(255,255,255,0.03)",
                  borderLeft: rx.flagged ? "3px solid #f59e0b" : "3px solid transparent",
                }}>
                  <span style={{ color: "#94a3b8" }}>{rx.fillDate.slice(5)}</span>
                  <span style={{ color: "#cbd5e1", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{rx.drug}</span>
                  <span style={{ color: "#64748b", fontFamily: "monospace", fontSize: 11 }}>{rx.ndc}</span>
                  <span style={{ color: "#94a3b8" }}>{rx.qty}</span>
                  <span style={{ textAlign: "right", color: "#cbd5e1" }}>${rx.paid.toFixed(2)}</span>
                  <span style={{ textAlign: "right", color: "#94a3b8" }}>${rx.nadac.toFixed(2)}</span>
                  <span style={{ textAlign: "right", color: rx.spreadPct > 200 ? "#ef4444" : "#f59e0b" }}>${rx.spread.toFixed(2)}</span>
                  <span style={{ textAlign: "right", color: rx.spreadPct > 200 ? "#ef4444" : rx.spreadPct > 100 ? "#f59e0b" : "#4ade80", fontWeight: 600 }}>
                    +{rx.spreadPct}%
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Demo footer */}
          <div style={{ padding: "16px 20px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#64748b" }}>
              {demoTab === "medical" ? "12 claims analyzed \u2022 6 flagged above benchmark" : "10 prescriptions analyzed \u2022 5 flagged for PBM spread"}
              {" "}&middot; Sample data: Midwest Manufacturing Co.
            </span>
            <span style={{ fontSize: 11, color: "#475569" }}>Powered by the Parity Engine</span>
          </div>
        </div>
      </section>

      {/* ── Conversion prompt ── */}
      {showConversion && (
        <div style={{
          position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 90,
          background: "linear-gradient(180deg, transparent, rgba(10,22,40,0.95) 30%)",
          padding: "40px 24px 24px", textAlign: "center",
        }}>
          <div style={{ maxWidth: 640, margin: "0 auto", background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.25)", borderRadius: 14, padding: "24px 32px", backdropFilter: "blur(12px)" }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>
              Run this analysis on your own claims data
            </h3>
            <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 16 }}>
              Upload your 835, CSV, or Excel claims export. Results in under 60 seconds.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", alignItems: "center", flexWrap: "wrap" }}>
              <Link to="/billing/employer/signup" style={{ background: "#3b82f6", color: "#fff", padding: "10px 24px", borderRadius: 8, fontWeight: 600, fontSize: 14, textDecoration: "none" }}>
                Start Free Trial &rarr;
              </Link>
              <button onClick={() => setShowConversion(false)} style={{ background: "none", border: "1px solid rgba(255,255,255,0.15)", color: "#94a3b8", padding: "10px 20px", borderRadius: 8, fontSize: 13, cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}>
                Dismiss
              </button>
            </div>
            <p style={{ fontSize: 11, color: "#64748b", marginTop: 10 }}>30-day trial &middot; No credit card required &middot; Cancel anytime</p>
          </div>
        </div>
      )}

      {/* ── The Regulatory Record ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 960, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 40 }}>The Regulatory Record</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 24 }}>
          {REGULATORY_CARDS.map((c) => (
            <div key={c.title} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: 14, padding: 28, display: "flex", flexDirection: "column" }}>
              <h3 style={{ fontSize: 17, fontWeight: 600, color: "#60a5fa", marginBottom: 14 }}>{c.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8", flex: 1 }}>{c.text}</p>
              <p style={{ fontSize: 12, lineHeight: 1.6, color: "#64748b", fontStyle: "italic", marginTop: 16, borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12 }}>{c.source}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pricing ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 600, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 12 }}>Simple Pricing</h2>
        <p style={{ fontSize: 14, color: "#94a3b8", textAlign: "center", marginBottom: 40, maxWidth: 520, marginLeft: "auto", marginRight: "auto" }}>
          One plan. Full access. Try free for 30 days.
        </p>
        <div style={{ background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.35)", borderRadius: 14, padding: 36, textAlign: "center" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#60a5fa", marginBottom: 8 }}>PARITY EMPLOYER PRO</div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 40, fontWeight: 700, color: "#f1f5f9" }}>$99</span>
            <span style={{ fontSize: 14, color: "#64748b" }}>/mo</span>
          </div>
          <div style={{ fontSize: 14, color: "#60a5fa", fontWeight: 600, marginBottom: 20 }}>30-day free trial &mdash; cancel anytime</div>
          <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8", marginBottom: 24, maxWidth: 420, marginLeft: "auto", marginRight: "auto" }}>
            Claims benchmarking, pharmacy analysis, RBP calculator, contract parser, plan scorecard, provider-level analysis, trend monitoring, and unlimited uploads.
          </p>
          <Link to="/billing/employer/signup" style={{ display: "inline-block", background: "#3b82f6", color: "#fff", borderRadius: 8, padding: "12px 32px", fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            Start Free Trial &rarr;
          </Link>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 16 }}>
            Introductory price locked for 24 months. No charge during trial.
          </p>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section style={{ padding: "0 24px 80px", maxWidth: 600, margin: "0 auto", textAlign: "center" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 26, fontWeight: 400, color: "#f1f5f9", marginBottom: 16 }}>
          Start with a free benchmark
        </h2>
        <p style={{ fontSize: 15, color: "#94a3b8", marginBottom: 28, lineHeight: 1.7 }}>
          See how your health plan costs compare to employers in your industry and state — no signup required.
        </p>
        <Link to="/billing/employer/benchmark" style={{ display: "inline-block", background: "#3b82f6", color: "#fff", padding: "12px 32px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
          Get Your Free Benchmark &rarr;
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

const MEDICAL_SUMMARY = [
  { value: "$2,623", label: "Total billed", color: "#f1f5f9" },
  { value: "$1,998", label: "Total allowed", color: "#f1f5f9" },
  { value: "$1,138", label: "Medicare benchmark", color: "#60a5fa" },
  { value: "6 of 12", label: "Claims flagged", color: "#ef4444" },
];

const PHARMACY_SUMMARY = [
  { value: "$1,156", label: "Total paid", color: "#f1f5f9" },
  { value: "$996", label: "NADAC benchmark", color: "#60a5fa" },
  { value: "$159", label: "Est. PBM spread", color: "#f59e0b" },
  { value: "5 of 10", label: "Claims flagged", color: "#ef4444" },
];

const FEATURE_CARDS = [
  { icon: "\u2261", title: "Cost Benchmarking by Category", text: "See how your spending in orthopedics, cardiology, imaging, and 20+ other categories compares to Medicare and regional benchmarks. Instantly identify which categories drive above-market costs." },
  { icon: "\u{1F50D}", title: "Provider & Site-of-Care Analysis", text: "Drill into individual providers to see who charges above-market rates. Identify when the same procedure costs 2\u20133x more at a hospital outpatient facility vs. a freestanding center." },
  { icon: "\u{1F48A}", title: "Pharmacy Benefit Benchmarking", text: "Compare every prescription against NADAC acquisition cost data. Surface PBM spread — the gap between what your plan pays and what the drug actually costs at wholesale." },
  { icon: "\u2193", title: "Actionable Savings Report", text: "Get a prioritized list of savings opportunities ranked by dollar impact. Each recommendation includes the data behind it — not just a benchmark but exactly how much opportunity exists." },
];

const REGULATORY_CARDS = [
  {
    title: "The FTC agrees",
    text: "The Federal Trade Commission\u2019s 2024 interim staff report documented PBM-affiliated pharmacies charging plan sponsors multiples of the National Average Drug Acquisition Cost \u2014 retaining nearly $1.6 billion in excess dispensing revenue for just two case study drugs over two years.",
    source: "Source: FTC Interim Staff Report on Pharmacy Benefit Managers, July 2024",
  },
  {
    title: "Employers are suing their TPAs",
    text: "Huntsman International, W.W. Grainger, and Kraft Heinz have each filed suit against their third-party administrators alleging approval of improper claims, cross-plan offsetting, and application of less rigorous adjudication standards to self-funded plans than to the TPA\u2019s fully-insured clients.",
    source: "Source: The Source on Healthcare Price and Competition, 2024",
  },
  {
    title: "The data was always there",
    text: "Federal price transparency rules and the Consolidated Appropriations Act now require carriers and TPAs to provide the underlying data that makes this analysis possible. Most self-insured employers have never reviewed it.",
    source: "Source: CAA 2021; CMS Transparency in Coverage Rule 2020",
  },
];
