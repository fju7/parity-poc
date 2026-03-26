import { useState } from "react";
import { Link } from "react-router-dom";

// Synthetic demo data
const PRACTICES = [
  { name: "Sunrise Family Medicine", billed: 234500, denialRate: 14.2, lines: 1842, payer: "BCBS FL" },
  { name: "Coastal Cardiology", billed: 312700, denialRate: 22.4, lines: 2106, payer: "United" },
  { name: "Tampa Bay Orthopedics", billed: 178300, denialRate: 16.8, lines: 1204, payer: "Aetna" },
  { name: "Gulf Coast Pediatrics", billed: 121740, denialRate: 12.1, lines: 986, payer: "BCBS FL" },
];

const PAYERS = [
  { name: "Blue Cross Blue Shield of Florida", adherence: 76, practices: 4, status: "review" },
  { name: "Aetna Better Health", adherence: 91, practices: 3, status: "good" },
  { name: "United Healthcare", adherence: 68, practices: 4, status: "watch" },
  { name: "Cigna", adherence: 88, practices: 2, status: "good" },
  { name: "Humana", adherence: 82, practices: 3, status: "review" },
  { name: "Ambetter", adherence: 73, practices: 2, status: "watch" },
  { name: "Molina Healthcare", adherence: 94, practices: 1, status: "good" },
];

const PATTERNS = [
  { payer: "United Healthcare", code: "CO-45", desc: "Charges exceed fee arrangement", practices: 4, denied: 12450, claims: 38 },
  { payer: "United Healthcare", code: "CO-97", desc: "Not paid separately", practices: 3, denied: 8200, claims: 24 },
  { payer: "BCBS FL", code: "CO-4", desc: "Procedure inconsistent with modifier", practices: 4, denied: 6800, claims: 19 },
  { payer: "Ambetter", code: "CO-16", desc: "Lacks info for adjudication", practices: 2, denied: 4350, claims: 12 },
];

const UHC_DETAIL = {
  summary: [
    { label: "Total Billed", value: "$78,400" },
    { label: "Total Paid", value: "$52,200" },
    { label: "Denied", value: "142 lines" },
    { label: "Denial Rate", value: "32%", color: "#fca5a5" },
  ],
  codes: [
    { code: "CO-45", desc: "Charges exceed fee arrangement", count: 38, amount: "$12,450" },
    { code: "CO-97", desc: "Not paid separately", count: 24, amount: "$8,200" },
    { code: "CO-4", desc: "Procedure inconsistent with modifier", count: 18, amount: "$5,100" },
  ],
  practices: [
    { name: "Sunrise Family Medicine", denied: "$4,200", lines: 32 },
    { name: "Coastal Cardiology", denied: "$8,900", lines: 56 },
    { name: "Tampa Bay Orthopedics", denied: "$3,100", lines: 28 },
    { name: "Gulf Coast Pediatrics", denied: "$2,250", lines: 26 },
  ],
};

const STEPS = [
  { id: 0, label: "Portfolio Overview" },
  { id: 1, label: "Payer Benchmarking" },
  { id: 2, label: "Pattern Detection" },
  { id: 3, label: "Branded Reports" },
];

export default function BillingDemoPage() {
  const [step, setStep] = useState(0);
  const [uhcExpanded, setUhcExpanded] = useState(false);
  const [escalated, setEscalated] = useState(false);

  const totalBilled = PRACTICES.reduce((s, p) => s + p.billed, 0);
  const overallDenial = 18.3;

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* Header */}
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: 64, display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.92)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: 12, textDecoration: "none", color: "inherit" }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
            <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" }}>CivicScale</span>
          </a>
          <span style={{ color: "#475569" }}>|</span>
          <span style={{ color: "#60a5fa", fontWeight: 600, fontSize: 14 }}>Parity Billing</span>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: "rgba(59,130,246,0.15)", color: "#60a5fa", fontWeight: 600 }}>DEMO</span>
        </div>
        <a href="https://billing.civicscale.ai" style={{ background: "#3b82f6", color: "#fff", textDecoration: "none", borderRadius: 6, padding: "8px 20px", fontWeight: 500, fontSize: 14 }}>
          Start Free
        </a>
      </header>

      {/* Step tabs */}
      <nav style={{ paddingTop: 64, borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "center", gap: 0 }}>
        {STEPS.map(s => (
          <button key={s.id} onClick={() => setStep(s.id)} style={{
            padding: "14px 24px", fontSize: 14, fontWeight: step === s.id ? 600 : 400,
            color: step === s.id ? "#f1f5f9" : "#64748b",
            background: "none", border: "none", cursor: "pointer",
            borderBottom: step === s.id ? "2px solid #3b82f6" : "2px solid transparent",
          }}>
            <span style={{ fontSize: 12, color: "#60a5fa", marginRight: 6 }}>{s.id + 1}</span>
            {s.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ padding: "32px 40px", maxWidth: 1100, margin: "0 auto" }}>

        {/* Step 1: Portfolio Overview */}
        {step === 0 && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Portfolio Dashboard</h2>
            <Callout
              seeing="Your entire managed portfolio in one view. Total billed, overall denial rate, and per-practice breakdown — data that no individual practice can see on their own."
              matters="When Coastal Cardiology's denial rate (22.4%) is nearly double Gulf Coast Pediatrics' (12.1%), that's a conversation you need to have — and data you need to have it with."
            />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
              {[
                { label: "Total Billed", value: `$${totalBilled.toLocaleString()}` },
                { label: "Overall Denial Rate", value: `${overallDenial}%`, color: "#fca5a5" },
                { label: "Active Practices", value: "4" },
                { label: "Payers Tracked", value: "7" },
              ].map(k => (
                <div key={k.label} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: 24 }}>
                  <div style={{ fontSize: 12, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>{k.label}</div>
                  <div style={{ fontSize: 24, fontWeight: 600, color: k.color || "#f1f5f9" }}>{k.value}</div>
                </div>
              ))}
            </div>
            <Table headers={["Practice", "Total Billed", "Denial Rate", "Lines", "Top Payer"]}
              rows={PRACTICES.map(p => [
                p.name,
                `$${p.billed.toLocaleString()}`,
                <span style={{ color: p.denialRate > 15 ? "#fca5a5" : "#5eead4" }}>{p.denialRate}%</span>,
                p.lines.toLocaleString(),
                p.payer,
              ])} />
            <NextStep onClick={() => setStep(1)} label="See Payer Benchmarking" />
          </div>
        )}

        {/* Step 2: Payer Benchmarking */}
        {step === 1 && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Payer Benchmarking</h2>
            <Callout
              seeing="Every payer ranked by adherence rate across all your practices. United Healthcare at 68% adherence is flagged as a Watch — its rate has dropped more than 10 points compared to the prior 90-day period."
              matters="A single practice might dismiss a denial pattern as a coding error. When you see United Healthcare's adherence dropping across all four of your practices simultaneously, that's a systematic payer policy change — and grounds for a coordinated escalation."
            />
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead><tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  {["Payer", "Adherence Rate", "Practices", "Status"].map(h => (
                    <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase" }}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {PAYERS.map(p => (
                    <tr key={p.name} onClick={() => p.name === "United Healthcare" && setUhcExpanded(!uhcExpanded)}
                      style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: p.name === "United Healthcare" ? "pointer" : "default",
                        background: uhcExpanded && p.name === "United Healthcare" ? "rgba(59,130,246,0.05)" : p.status === "watch" ? "rgba(245,158,11,0.03)" : "transparent" }}>
                      <td style={{ padding: "12px 16px", fontSize: 14, color: "#e2e8f0" }}>
                        {p.name}
                        {p.status === "watch" && <span style={{ display: "inline-block", marginLeft: 8, padding: "1px 6px", borderRadius: 4, background: "rgba(245,158,11,0.15)", color: "#fbbf24", fontSize: 10, fontWeight: 600 }}>DECLINING</span>}
                      </td>
                      <td style={{ padding: "12px 16px", fontSize: 14, fontWeight: 600, color: p.adherence < 75 ? "#fca5a5" : p.adherence < 90 ? "#fbbf24" : "#5eead4" }}>{p.adherence}%</td>
                      <td style={{ padding: "12px 16px", fontSize: 14, color: "#94a3b8" }}>{p.practices}</td>
                      <td style={{ padding: "12px 16px" }}>
                        <StatusBadge status={p.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {uhcExpanded && (
              <div style={{ background: "rgba(59,130,246,0.03)", border: "1px solid rgba(59,130,246,0.1)", borderRadius: 12, padding: 20, marginTop: 12 }}>
                <h3 style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" }}>United Healthcare — Detail</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
                  {UHC_DETAIL.summary.map(s => (
                    <div key={s.label}>
                      <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase" }}>{s.label}</div>
                      <div style={{ fontSize: 16, fontWeight: 600, color: s.color || "#f1f5f9" }}>{s.value}</div>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 6, textTransform: "uppercase" }}>Top Denial Codes</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                  {UHC_DETAIL.codes.map(c => (
                    <div key={c.code} style={{ padding: "4px 10px", borderRadius: 6, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)", fontSize: 12 }}>
                      <span style={{ fontFamily: "monospace", color: "#fca5a5", fontWeight: 600 }}>{c.code}</span>
                      <span style={{ color: "#94a3b8", marginLeft: 6 }}>{c.desc}</span>
                      <span style={{ color: "#64748b", marginLeft: 6 }}>({c.count}x, {c.amount})</span>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 6, textTransform: "uppercase" }}>Per-Practice Breakdown</div>
                {UHC_DETAIL.practices.map(p => (
                  <div key={p.name} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13, color: "#cbd5e1", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                    <span>{p.name}</span>
                    <span style={{ color: "#94a3b8" }}>{p.denied} denied / {p.lines} lines</span>
                  </div>
                ))}
              </div>
            )}
            <NextStep onClick={() => setStep(2)} label="See Pattern Detection" />
          </div>
        )}

        {/* Step 3: Pattern Detection */}
        {step === 2 && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Cross-Practice Pattern Detection</h2>
            <Callout
              seeing={`Denial patterns that appear across 2 or more practices automatically surfaced. United Healthcare's CO-45 denials are affecting all 4 practices — $12,450 in denied claims from a single payer behavior.`}
              matters="Instead of 4 separate appeals from 4 separate practices, you create one escalation with a shared evidence package. One conversation with United Healthcare's provider relations team, backed by cross-practice data they can't dismiss."
            />
            <Table headers={["Payer", "Code", "Description", "Practices", "Total Denied", "Action"]}
              rows={PATTERNS.map(p => [
                p.payer,
                <span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600, padding: "2px 6px", borderRadius: 4, background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}>{p.code}</span>,
                <span style={{ fontSize: 12, color: "#94a3b8" }}>{p.desc}</span>,
                <span style={{ padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: "rgba(59,130,246,0.15)", color: "#60a5fa" }}>{p.practices}</span>,
                <span style={{ color: "#fca5a5" }}>${p.denied.toLocaleString()}</span>,
                p.code === "CO-45" ? (
                  escalated ? <span style={{ color: "#5eead4", fontSize: 12 }}>Created</span> :
                  <button onClick={() => setEscalated(true)} style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer" }}>Escalate</button>
                ) : <span style={{ fontSize: 12, color: "#64748b" }}>Escalate</span>,
              ])} />
            {escalated && (
              <div style={{ marginTop: 16, background: "rgba(13,148,136,0.05)", border: "1px solid rgba(13,148,136,0.2)", borderRadius: 12, padding: 20 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#5eead4", marginBottom: 8 }}>ESCALATION CREATED</div>
                <p style={{ fontSize: 14, color: "#cbd5e1", lineHeight: 1.7, margin: 0 }}>
                  United Healthcare has systematically denied claims with code CO-45 (Charges exceed fee arrangement)
                  across 4 practices managed by your company, totaling $12,450 in denied claims.
                  This pattern suggests a systematic payer-side policy rather than individual coding errors.
                </p>
              </div>
            )}
            <NextStep onClick={() => setStep(3)} label="See Branded Reports" />
          </div>
        )}

        {/* Step 4: Branded Reports */}
        {step === 3 && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>White-Label Client Reports</h2>
            <Callout
              seeing="A white-label PDF report generated for Sunrise Family Medicine — your company name, your logo, their data."
              matters="Every billing company tells clients they're maximizing collections. You can show them proof. A monthly branded report demonstrating what you recovered on their behalf is a client retention tool that most of your competitors can't offer."
            />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
              {/* Mock PDF cover */}
              <div style={{ background: "#fff", borderRadius: 12, padding: 40, color: "#1e293b", boxShadow: "0 8px 32px rgba(0,0,0,0.3)" }}>
                <div style={{ textAlign: "center", marginBottom: 24 }}>
                  <div style={{ width: 48, height: 48, borderRadius: 8, background: "linear-gradient(135deg, #3b82f6, #60a5fa)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 700, color: "#fff", marginBottom: 12 }}>A</div>
                  <h3 style={{ fontSize: 20, fontWeight: 700, color: "#1e293b", margin: "0 0 4px" }}>Acme Revenue Cycle</h3>
                  <p style={{ fontSize: 12, color: "#64748b", margin: 0 }}>Prepared by Acme Revenue Cycle Management</p>
                </div>
                <hr style={{ border: "none", borderTop: "2px solid #3b82f6", margin: "16px 0" }} />
                <p style={{ fontSize: 14, color: "#475569", margin: "0 0 4px" }}>Report for: <strong>Sunrise Family Medicine</strong></p>
                <p style={{ fontSize: 14, color: "#475569", margin: "0 0 4px" }}>Denial Summary Report</p>
                <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 4px" }}>Period: Last 90 Days (Jan 1 – Mar 31, 2026)</p>
                <p style={{ fontSize: 12, color: "#94a3b8", margin: 0 }}>Generated: March 26, 2026</p>
                <div style={{ marginTop: 32, fontSize: 10, color: "#94a3b8", fontStyle: "italic", textAlign: "center" }}>
                  Confidential — for practice use only
                </div>
              </div>
              {/* Description */}
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
                <h3 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", marginBottom: 16 }}>Your brand. Their data. One click.</h3>
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {[
                    "Your company name and logo on every page",
                    "Denial summary, payer performance, and recovery data",
                    "Practice-specific — each client sees only their data",
                    "PDF download or send via the Practice Portal",
                    "Custom header and footer text",
                  ].map(t => (
                    <li key={t} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 10, fontSize: 14, color: "#94a3b8" }}>
                      <span style={{ color: "#5eead4", fontWeight: 600, flexShrink: 0 }}>&#10003;</span>
                      {t}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Final CTA */}
            <div style={{ textAlign: "center", marginTop: 48, padding: "32px 24px", background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: 16 }}>
              <h3 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 24, fontWeight: 400, color: "#f1f5f9", marginBottom: 12 }}>
                Ready to see this for your portfolio?
              </h3>
              <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 20 }}>First practice free. No credit card required.</p>
              <a href="https://billing.civicscale.ai" style={{ display: "inline-block", background: "linear-gradient(135deg, #3b82f6, #60a5fa)", color: "#fff", textDecoration: "none", borderRadius: 8, padding: "14px 32px", fontWeight: 600, fontSize: 16 }}>
                Sign Up to Use This
              </a>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Helper components
function Table({ headers, rows }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, overflow: "hidden" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          {headers.map(h => <th key={h} style={{ padding: "12px 16px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>)}
        </tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
              {row.map((cell, j) => <td key={j} style={{ padding: "12px 16px", fontSize: 14, color: "#e2e8f0" }}>{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    good: { bg: "rgba(13,148,136,0.15)", color: "#5eead4", label: "Good" },
    review: { bg: "rgba(148,163,184,0.15)", color: "#94a3b8", label: "Review" },
    watch: { bg: "rgba(245,158,11,0.15)", color: "#fbbf24", label: "Watch" },
  };
  const s = map[status] || map.review;
  return <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: s.bg, color: s.color }}>{s.label}</span>;
}

function Callout({ seeing, matters }) {
  return (
    <div style={{
      borderLeft: "3px solid #0D9488", background: "rgba(13, 148, 136, 0.08)",
      borderRadius: 6, padding: 16, marginBottom: 24,
    }}>
      <p style={{ fontSize: 14, color: "#e2e8f0", margin: "0 0 8px", lineHeight: 1.6 }}>
        <strong style={{ color: "#5eead4" }}>What you're seeing:</strong> {seeing}
      </p>
      <p style={{ fontSize: 13, color: "#94a3b8", margin: 0, lineHeight: 1.6, fontStyle: "italic" }}>
        <strong style={{ color: "#5eead4", fontStyle: "normal" }}>Why it matters:</strong> {matters}
      </p>
    </div>
  );
}

function NextStep({ onClick, label }) {
  return (
    <div style={{ textAlign: "center", marginTop: 32 }}>
      <button onClick={onClick} style={{
        padding: "10px 24px", borderRadius: 8, border: "none", cursor: "pointer",
        background: "linear-gradient(135deg, #3b82f6, #60a5fa)", color: "#fff",
        fontWeight: 600, fontSize: 14,
      }}>
        {label} &rarr;
      </button>
    </div>
  );
}
