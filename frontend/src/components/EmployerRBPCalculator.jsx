import { useState, useEffect } from "react";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const MULTIPLIER_LABELS = {
  1.2: "Aggressive — maximum savings, may face provider pushback",
  1.25: "Aggressive — strong savings, some provider friction",
  1.3: "Moderate-aggressive — solid savings with manageable friction",
  1.35: "Moderate — good balance of savings and provider acceptance",
  1.4: "Conservative — most RBP programs start here",
  1.45: "Conservative — slightly above typical starting point",
  1.5: "Moderate — broad provider acceptance",
  1.55: "Moderate — comfortable for most providers",
  1.6: "Moderate — reduces provider friction",
  1.65: "Liberal-moderate — easy provider acceptance",
  1.7: "Liberal — minimal network disruption",
  1.75: "Liberal — very broad acceptance",
  1.8: "Liberal — nearly universal acceptance",
  1.85: "Very liberal — almost no disruption",
  1.9: "Very liberal — minimal savings impact",
  1.95: "Very liberal — marginal savings",
  2.0: "Liberal — minimal network disruption, still meaningful savings",
};

function getMultiplierLabel(val) {
  return MULTIPLIER_LABELS[val] || (val <= 1.4 ? "Conservative range" : val <= 1.6 ? "Moderate range" : "Liberal range");
}

function fmt$(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function savingsColor(pct) {
  if (pct >= 20) return "#22c55e";
  if (pct >= 10) return "#f59e0b";
  return "#64748b";
}

export default function EmployerRBPCalculator() {
  const [sessionId, setSessionId] = useState("");
  const [multiplier, setMultiplier] = useState(1.4);
  const [zipCode, setZipCode] = useState("");
  const [view, setView] = useState("input"); // input, processing, results, error
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("employer_claims_session_id");
    if (stored) setSessionId(stored);
    const storedZip = localStorage.getItem("employer_claims_zip_code");
    if (storedZip) setZipCode(storedZip);
  }, []);

  const handleCalculate = async () => {
    if (!sessionId) return;
    setView("processing");
    setProgress(10);
    setError(null);

    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 6, 85));
    }, 600);

    try {
      const body = {
        claims_session_id: sessionId,
        medicare_multiplier: multiplier,
      };
      if (zipCode) body.zip_code = zipCode;

      const res = await fetch(`${API_BASE}/api/employer/rbp-calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        if (res.status === 402) {
          setError("subscription_required");
          setView("error");
          return;
        }
        throw new Error(data.detail || `API error: ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      setView("results");
    } catch (err) {
      clearInterval(progressInterval);
      setError(err.message);
      setView("error");
    }
  };

  const handleDownloadPdf = async () => {
    if (!result) return;
    setPdfLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/employer/rbp-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "parity_rbp_analysis.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("[RBP PDF] download failed:", err);
    } finally {
      setPdfLoading(false);
    }
  };

  const multiplierPct = Math.round(multiplier * 100);

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* Header */}
      <header className="cs-home-header">
        <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", fontWeight: "700", color: "#0a1628" }}>C</div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>CivicScale</span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/billing/employer" style={{ color: "#60a5fa", textDecoration: "none" }}>Parity Employer</Link>
        </nav>
      </header>

      <div className="cs-home-section" style={{ maxWidth: "880px", margin: "0 auto", paddingTop: "60px", paddingBottom: "80px" }}>

        {/* Input View */}
        {view === "input" && (
          <>
            <div style={{ textAlign: "center", marginBottom: "36px" }}>
              <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>RBP CALCULATOR</span>
              </div>
              <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
                Reference-Based Pricing Savings
              </h1>
              <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "560px", margin: "0 auto" }}>
                See what your plan would have paid under reference-based pricing — capping reimbursement at a fixed percentage of Medicare rates.
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
              {/* Session ID */}
              <div>
                <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Claims Session ID</span>
                  <input
                    type="text"
                    value={sessionId}
                    onChange={(e) => setSessionId(e.target.value)}
                    placeholder="Auto-populated from your last claims check"
                    style={inputStyle}
                  />
                </label>
                {!sessionId && (
                  <p style={{ fontSize: "12px", color: "#f59e0b", marginTop: "6px" }}>
                    No recent claims session found. <Link to="/billing/employer/claims-check" style={{ color: "#60a5fa" }}>Run a claims check first</Link>.
                  </p>
                )}
              </div>

              {/* Multiplier slider */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Medicare Multiplier</span>
                  <span style={{ fontSize: "24px", fontWeight: "700", color: "#60a5fa" }}>{multiplierPct}%</span>
                </div>
                <input
                  type="range"
                  min="1.2"
                  max="2.0"
                  step="0.05"
                  value={multiplier}
                  onChange={(e) => setMultiplier(parseFloat(e.target.value))}
                  style={{ width: "100%", accentColor: "#3b82f6" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#475569", marginTop: "4px" }}>
                  <span>120%</span>
                  <span>200%</span>
                </div>
                <div style={{ marginTop: "8px", fontSize: "13px", color: "#94a3b8", fontStyle: "italic" }}>
                  {getMultiplierLabel(multiplier)}
                </div>
                <div style={{ marginTop: "16px", fontSize: "15px", fontWeight: "500", color: "#cbd5e1", textAlign: "center" }}>
                  Calculate what you would have paid at {multiplierPct}% of Medicare
                </div>
              </div>

              {/* Optional ZIP override */}
              <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>ZIP code (optional override)</span>
                <input
                  type="text"
                  maxLength={5}
                  pattern="[0-9]{5}"
                  placeholder="Uses ZIP from claims session if blank"
                  value={zipCode}
                  onChange={(e) => setZipCode(e.target.value)}
                  style={inputStyle}
                />
              </label>

              <button
                onClick={handleCalculate}
                disabled={!sessionId}
                style={{ ...btnPrimary, opacity: sessionId ? 1 : 0.5, cursor: sessionId ? "pointer" : "not-allowed" }}
              >
                Calculate RBP Savings
              </button>
            </div>
          </>
        )}

        {/* Processing View */}
        {view === "processing" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "24px", fontWeight: "400", color: "#f1f5f9", marginBottom: "24px" }}>
              Calculating RBP savings...
            </h2>
            <div style={{ maxWidth: "400px", margin: "0 auto 16px", background: "rgba(255,255,255,0.06)", borderRadius: "8px", overflow: "hidden", height: "8px" }}>
              <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg, #3b82f6, #60a5fa)", borderRadius: "8px", transition: "width 0.5s ease" }} />
            </div>
            <p style={{ fontSize: "14px", color: "#64748b" }}>
              {progress < 30 ? "Loading claims data..." :
               progress < 60 ? "Computing RBP rates for each procedure..." :
               progress < 85 ? "Aggregating savings by category..." :
               "Generating analysis..."}
            </p>
          </div>
        )}

        {/* Error View — Subscription gate */}
        {view === "error" && error === "subscription_required" && (
          <div style={{ textAlign: "center", paddingTop: "60px" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>&#128274;</div>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "26px", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px" }}>
              Subscription Required
            </h2>
            <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "480px", margin: "0 auto 24px" }}>
              The RBP calculator is available with an active Parity Employer subscription. Subscribe to unlock RBP analysis, unlimited claims checks, contract parsing, and trend monitoring.
            </p>
            <div style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: "14px", padding: "24px", maxWidth: "400px", margin: "0 auto 24px" }}>
              <div style={{ fontSize: "13px", color: "#10b981", fontWeight: "600", marginBottom: "8px" }}>PLANS START AT</div>
              <div style={{ fontSize: "36px", fontWeight: "700", color: "#f1f5f9" }}>$149<span style={{ fontSize: "16px", fontWeight: "400", color: "#94a3b8" }}>/mo</span></div>
              <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>3x savings guarantee</div>
            </div>
            <Link to="/billing/employer/subscribe" style={{ ...btnPrimary, display: "inline-block", textDecoration: "none", width: "auto", padding: "14px 36px", background: "#10b981" }}>
              View Plans & Subscribe
            </Link>
            <div style={{ marginTop: "16px" }}>
              <button onClick={() => setView("input")} style={{ background: "none", border: "none", color: "#64748b", fontSize: "14px", cursor: "pointer" }}>
                &larr; Back
              </button>
            </div>
          </div>
        )}

        {/* Error View — General */}
        {view === "error" && error !== "subscription_required" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>!</div>
            <h2 style={{ fontSize: "22px", fontWeight: "600", color: "#f1f5f9", marginBottom: "12px" }}>Calculation failed</h2>
            <p style={{ fontSize: "14px", color: "#fca5a5", marginBottom: "24px" }}>{error}</p>
            <button onClick={() => setView("input")} style={btnPrimary}>Try Again</button>
          </div>
        )}

        {/* Results View */}
        {view === "results" && result && (
          <>
            {/* Section 1: Savings Summary */}
            <div style={{
              background: "linear-gradient(135deg, rgba(34,197,94,0.08), rgba(59,130,246,0.06))",
              border: "1px solid rgba(34,197,94,0.25)",
              borderRadius: "16px",
              padding: "32px",
              textAlign: "center",
              marginBottom: "28px",
            }}>
              <div style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "6px", fontWeight: "600", letterSpacing: "0.05em" }}>
                POTENTIAL ANNUAL SAVINGS
              </div>
              <div style={{ fontSize: "48px", fontWeight: "700", color: "#22c55e", lineHeight: "1.1" }}>
                {fmt$(result.total_potential_savings * 12)}
              </div>
              <div style={{ fontSize: "14px", color: "#94a3b8", marginTop: "8px" }}>
                at {multiplierPct}% of Medicare vs. your actual paid amounts
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "24px", maxWidth: "400px", margin: "24px auto 0" }}>
                <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: "10px", padding: "16px" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>Actual Paid</div>
                  <div style={{ fontSize: "22px", fontWeight: "700", color: "#f1f5f9" }}>{fmt$(result.total_actual_paid)}</div>
                </div>
                <div style={{ background: "rgba(255,255,255,0.04)", borderRadius: "10px", padding: "16px" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>RBP Equivalent</div>
                  <div style={{ fontSize: "22px", fontWeight: "700", color: "#60a5fa" }}>{fmt$(result.total_rbp_equivalent)}</div>
                </div>
              </div>

              <div style={{ marginTop: "16px" }}>
                <span style={{
                  display: "inline-block", background: "rgba(34,197,94,0.15)", color: "#22c55e",
                  padding: "6px 14px", borderRadius: "20px", fontSize: "15px", fontWeight: "700",
                }}>
                  {result.savings_pct_overall}% savings
                </span>
              </div>
            </div>

            {/* Eligibility Assessment */}
            {result.eligibility && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>RBP Viability for Your Company</h3>
                {(() => {
                  const v = result.eligibility.verdict;
                  const bg = v === "strong_fit" ? "rgba(34,197,94,0.1)" : v === "possible_fit" ? "rgba(59,130,246,0.1)" : v === "borderline" ? "rgba(245,158,11,0.1)" : "rgba(239,68,68,0.1)";
                  const border = v === "strong_fit" ? "rgba(34,197,94,0.3)" : v === "possible_fit" ? "rgba(59,130,246,0.3)" : v === "borderline" ? "rgba(245,158,11,0.3)" : "rgba(239,68,68,0.3)";
                  const color = v === "strong_fit" ? "#22c55e" : v === "possible_fit" ? "#60a5fa" : v === "borderline" ? "#f59e0b" : "#ef4444";
                  return (
                    <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: "10px", padding: "16px", marginBottom: "16px" }}>
                      <div style={{ fontSize: "16px", fontWeight: "600", color }}>{result.eligibility.verdict_text}</div>
                    </div>
                  );
                })()}
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {result.eligibility.criteria.map((c, i) => {
                    const dotColor = c.status === "green" ? "#22c55e" : c.status === "red" ? "#ef4444" : "#f59e0b";
                    return (
                      <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
                        <div style={{ width: "10px", height: "10px", borderRadius: "50%", background: dotColor, marginTop: "5px", flexShrink: 0 }} />
                        <div>
                          <span style={{ fontWeight: "600", color: "#f1f5f9", fontSize: "14px" }}>{c.criterion}: </span>
                          <span style={{ color: "#94a3b8", fontSize: "13px" }}>{c.note}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                {result.eligibility.alternative_levers && result.eligibility.alternative_levers.length > 0 && (
                  <div style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
                    <div style={{ fontSize: "13px", fontWeight: "600", color: "#cbd5e1", marginBottom: "8px" }}>Other savings levers to consider:</div>
                    <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "13px", color: "#94a3b8", lineHeight: "1.8" }}>
                      {result.eligibility.alternative_levers.map((lever, i) => (
                        <li key={i}>{lever}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Section 2: Category Breakdown */}
            {result.categories && result.categories.length > 0 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Savings by Category</h3>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                        <th style={thStyle}>Category</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Actual Paid</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>RBP Equivalent</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Savings</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Savings %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.categories.map((cat, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                          <td style={tdStyle}>{cat.category}</td>
                          <td style={{ ...tdStyle, textAlign: "right" }}>{fmt$(cat.actual_paid)}</td>
                          <td style={{ ...tdStyle, textAlign: "right" }}>{fmt$(cat.rbp_equivalent)}</td>
                          <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600", color: cat.savings > 0 ? "#22c55e" : "#64748b" }}>{fmt$(cat.savings)}</td>
                          <td style={{ ...tdStyle, textAlign: "right" }}>
                            <span style={{ fontWeight: "600", color: savingsColor(cat.savings_pct) }}>
                              {cat.savings_pct}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Section 3: Top 10 Procedures */}
            {result.top_procedures && result.top_procedures.length > 0 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Top 10 Procedures by Savings</h3>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                        <th style={thStyle}>CPT</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Actual Paid</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>RBP Rate</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Savings/Claim</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Claims</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Total Savings</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.top_procedures.map((p, i) => {
                        const savPct = p.actual_paid_avg > 0 ? (p.savings_per_claim / p.actual_paid_avg * 100) : 0;
                        return (
                          <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                            <td style={tdStyle}>{p.cpt_code}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>{fmt$(p.actual_paid_avg)}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>{fmt$(p.rbp_rate)}</td>
                            <td style={{ ...tdStyle, textAlign: "right", fontWeight: "600", color: savingsColor(savPct) }}>{fmt$(p.savings_per_claim)}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>{p.claims_count}</td>
                            <td style={{ ...tdStyle, textAlign: "right", fontWeight: "700", color: "#22c55e" }}>{fmt$(p.total_savings)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Section 4: AI Narrative */}
            {result.rbp_narrative && (
              <div style={{ background: "rgba(255,255,255,0.02)", borderLeft: "4px solid #3b82f6", borderRadius: "8px", padding: "20px", marginBottom: "28px" }}>
                <div style={{ fontSize: "11px", fontWeight: "600", color: "#60a5fa", marginBottom: "10px", letterSpacing: "0.05em" }}>RBP ANALYSIS</div>
                <div style={{ fontSize: "15px", color: "#e2e8f0", fontWeight: "400", lineHeight: "1.6" }}>{result.rbp_narrative}</div>
              </div>
            )}

            {/* Next Steps */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "24px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Next Steps</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                <button
                  onClick={handleDownloadPdf}
                  disabled={pdfLoading}
                  style={{
                    background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.25)",
                    borderRadius: "10px", padding: "20px 16px", cursor: pdfLoading ? "wait" : "pointer",
                    textAlign: "center", color: "#e2e8f0",
                  }}
                >
                  <div style={{ fontSize: "24px", marginBottom: "8px" }}>&#128196;</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#60a5fa", marginBottom: "4px" }}>
                    {pdfLoading ? "Generating..." : "Download One-Page PDF"}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>Share with your broker</div>
                </button>
                <a
                  href="https://www.imagine360.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.25)",
                    borderRadius: "10px", padding: "20px 16px", textDecoration: "none",
                    textAlign: "center", color: "#e2e8f0", display: "block",
                  }}
                >
                  <div style={{ fontSize: "24px", marginBottom: "8px" }}>&#127891;</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#60a5fa", marginBottom: "4px" }}>
                    Imagine360 &rarr;
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>RBP-specialized TPA</div>
                </a>
                <Link
                  to="/billing/employer/demo"
                  style={{
                    background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.25)",
                    borderRadius: "10px", padding: "20px 16px", textDecoration: "none",
                    textAlign: "center", color: "#e2e8f0", display: "block",
                  }}
                >
                  <div style={{ fontSize: "24px", marginBottom: "8px" }}>&#128200;</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#60a5fa", marginBottom: "4px" }}>
                    Back to Full Analysis &rarr;
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>See other savings levers</div>
                </Link>
              </div>
            </div>

            {/* Recalculate */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <button onClick={() => setView("input")} style={btnPrimary}>
                Recalculate with Different Multiplier
              </button>
              <Link to="/billing/employer" style={{ textAlign: "center", color: "#64748b", fontSize: "14px", textDecoration: "none" }}>
                &larr; Back to Parity Employer
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const inputStyle = {
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: "8px",
  padding: "12px 14px",
  fontSize: "15px",
  color: "#f1f5f9",
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const btnPrimary = {
  display: "block",
  width: "100%",
  background: "#3b82f6",
  color: "#fff",
  border: "none",
  borderRadius: "8px",
  padding: "14px 28px",
  fontWeight: "600",
  fontSize: "15px",
  cursor: "pointer",
  textAlign: "center",
  textDecoration: "none",
};

const thStyle = { textAlign: "left", padding: "8px 12px", color: "#64748b", fontWeight: "500" };
const tdStyle = { padding: "8px 12px", color: "#e2e8f0" };
