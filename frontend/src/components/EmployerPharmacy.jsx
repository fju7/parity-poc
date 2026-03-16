import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

import { API_BASE } from "../lib/apiBase";
export default function EmployerPharmacy() {
  const { isAuthenticated, user } = useAuth();
  const [file, setFile] = useState(null);
  const [email, setEmail] = useState(() => sessionStorage.getItem("cs_anon_email") || "");
  const [wantsCopy, setWantsCopy] = useState(false);
  const anonEmailKnown = !isAuthenticated && !!sessionStorage.getItem("cs_anon_email");
  const showEmailField = !isAuthenticated && !anonEmailKnown;
  const [dragOver, setDragOver] = useState(false);
  const [view, setView] = useState("upload");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }, []);

  const handleFileInput = useCallback((e) => {
    const f = e.target.files[0];
    if (f) setFile(f);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setView("processing");
    setProgress(10);
    setError(null);

    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 8, 85));
    }, 600);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const resolvedEmail = isAuthenticated ? (user?.email || null) : (email || sessionStorage.getItem("cs_anon_email") || null);
      if (resolvedEmail) formData.append("email", resolvedEmail);
      if (email && !isAuthenticated) sessionStorage.setItem("cs_anon_email", email);

      const res = await fetch(`${API_BASE}/api/employer/pharmacy/analyze`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `API error: ${res.status}`);
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

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      <header className="cs-home-header">
        <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", fontWeight: "700", color: "#0a1628" }}>C</div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>CivicScale</span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/dashboard" style={{ color: "#60a5fa", textDecoration: "none" }}>Parity Employer</Link>
        </nav>
      </header>

      <div className="cs-home-section" style={{ maxWidth: "800px", margin: "0 auto", paddingTop: "60px", paddingBottom: "80px" }}>

        {/* Tab toggle */}
        <div style={{ display: "flex", gap: "4px", background: "rgba(255,255,255,0.04)", borderRadius: "10px", padding: "4px", marginBottom: "28px", maxWidth: "320px", margin: "0 auto 28px" }}>
          <Link to="/claims-check" style={{ flex: 1, textAlign: "center", padding: "10px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: "600", color: "#94a3b8", textDecoration: "none", background: "transparent" }}>
            Medical Claims
          </Link>
          <div style={{ flex: 1, textAlign: "center", padding: "10px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: "600", color: "#f1f5f9", background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.3)" }}>
            Pharmacy Claims
          </div>
        </div>

        {/* Upload View */}
        {view === "upload" && (
          <>
            <div style={{ textAlign: "center", marginBottom: "36px" }}>
              <div style={{ display: "inline-block", background: "rgba(16,185,129,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "#10b981" }}>PHARMACY ANALYSIS</span>
              </div>
              <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
                Benchmark your pharmacy spend against NADAC
              </h1>
              <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "560px", margin: "0 auto" }}>
                Upload your pharmacy claims file and we'll compare drug costs against National Average Drug Acquisition Cost (NADAC) benchmarks.
              </p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => document.getElementById("pharmacy-file-input").click()}
                style={{
                  border: `2px dashed ${dragOver ? "#10b981" : file ? "#22c55e" : "rgba(255,255,255,0.15)"}`,
                  borderRadius: "14px",
                  padding: "48px 24px",
                  textAlign: "center",
                  cursor: "pointer",
                  background: dragOver ? "rgba(16,185,129,0.04)" : "rgba(255,255,255,0.01)",
                  transition: "all 0.2s",
                }}
              >
                <input id="pharmacy-file-input" type="file" accept=".csv,.xlsx,.xls,.835,.edi,.pdf,.txt" onChange={handleFileInput} style={{ display: "none" }} />
                {file ? (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#10003;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#22c55e" }}>{file.name}</div>
                    <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>{(file.size / 1024).toFixed(0)} KB &middot; Click to change</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#128138;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#cbd5e1" }}>Drop your pharmacy claims file here</div>
                    <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>CSV, Excel, 835 EDI, PDF, or PBM exports &middot; Max 10MB</div>
                  </>
                )}
              </div>

              {showEmailField && (
                <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Email (optional)</span>
                  <input type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
                </label>
              )}

              <button type="submit" disabled={!file} style={{ ...btnPrimary, background: "#10b981", opacity: file ? 1 : 0.5, cursor: file ? "pointer" : "not-allowed" }}>
                Analyze Pharmacy Claims
              </button>
            </form>

            <div style={{ marginTop: "24px", fontSize: "12px", color: "#94a3b8", textAlign: "center", lineHeight: "1.6" }}>
              Your data is processed securely. No patient-identifiable data is stored. Drug costs are benchmarked against NADAC public pricing data.
            </div>
          </>
        )}

        {/* Processing View */}
        {view === "processing" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "24px", fontWeight: "400", color: "#f1f5f9", marginBottom: "24px" }}>
              Analyzing pharmacy claims...
            </h2>
            <div style={{ maxWidth: "400px", margin: "0 auto 16px", background: "rgba(255,255,255,0.06)", borderRadius: "8px", overflow: "hidden", height: "8px" }}>
              <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg, #10b981, #34d399)", borderRadius: "8px", transition: "width 0.5s ease" }} />
            </div>
            <p style={{ fontSize: "14px", color: "#94a3b8" }}>
              {progress < 30 ? "Reading file and extracting drug claims..." :
               progress < 60 ? "Looking up NADAC benchmark pricing..." :
               progress < 85 ? "Calculating spreads and generic opportunities..." :
               "Finalizing results..."}
            </p>
          </div>
        )}

        {/* Error View */}
        {view === "error" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>!</div>
            <h2 style={{ fontSize: "22px", fontWeight: "600", color: "#f1f5f9", marginBottom: "12px" }}>Analysis failed</h2>
            <p style={{ fontSize: "14px", color: "#fca5a5", marginBottom: "24px" }}>{error}</p>
            <button onClick={() => setView("upload")} style={btnPrimary}>Try Again</button>
          </div>
        )}

        {/* Results View */}
        {view === "results" && result && (
          <>
            <div style={{ textAlign: "center", marginBottom: "28px" }}>
              <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "28px", fontWeight: "400", color: "#f1f5f9", marginBottom: "8px" }}>
                Pharmacy Analysis Complete
              </h2>
              <p style={{ fontSize: "14px", color: "#94a3b8" }}>
                {result.summary.total_claims} claims analyzed &middot; {file?.name}
              </p>
            </div>

            {/* Summary Stats */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px", marginBottom: "24px" }}>
              <StatCard label="Total Billed" value={`$${result.summary.total_billed.toLocaleString()}`} />
              <StatCard label="Plan Paid" value={`$${result.summary.total_plan_paid.toLocaleString()}`} />
              <StatCard label="Generic Rate" value={`${result.summary.generic_rate}%`} color={result.summary.generic_rate >= 80 ? "#22c55e" : "#f59e0b"} />
              <StatCard label="Specialty Spend" value={`${result.summary.specialty_spend_pct}%`} color={result.summary.specialty_spend_pct <= 20 ? "#22c55e" : "#ef4444"} />
            </div>

            {/* Top Drugs by Cost */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(16,185,129,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "16px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Top Drugs by Cost</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                      <th style={thStyle}>Drug</th>
                      <th style={thStyle}>Type</th>
                      <th style={thStyle}>Plan Paid</th>
                      <th style={thStyle}>Benchmark</th>
                      <th style={thStyle}>Spread</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.top_drugs || []).map((d, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                        <td style={tdStyle}>
                          <div>{d.drug_name}</div>
                          {d.generic_name && d.generic_name !== d.drug_name && (
                            <div style={{ fontSize: "11px", color: "#94a3b8" }}>{d.generic_name}</div>
                          )}
                        </td>
                        <td style={tdStyle}>
                          <span style={{
                            display: "inline-block",
                            padding: "2px 8px",
                            borderRadius: "4px",
                            fontSize: "11px",
                            fontWeight: "600",
                            background: d.brand_or_generic === "generic" ? "rgba(34,197,94,0.15)" :
                                       d.brand_or_generic === "brand" ? "rgba(245,158,11,0.15)" : "rgba(255,255,255,0.06)",
                            color: d.brand_or_generic === "generic" ? "#22c55e" :
                                  d.brand_or_generic === "brand" ? "#f59e0b" : "#94a3b8",
                          }}>
                            {d.brand_or_generic === "generic" ? "Generic" : d.brand_or_generic === "brand" ? "Brand" : "Unknown"}
                          </span>
                          {d.is_specialty && (
                            <span style={{ display: "inline-block", marginLeft: "4px", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: "600", background: "rgba(168,85,247,0.15)", color: "#a855f7" }}>
                              Specialty
                            </span>
                          )}
                        </td>
                        <td style={tdStyle}>${d.plan_paid?.toLocaleString()}</td>
                        <td style={tdStyle}>
                          {d.benchmark_cost != null ? (
                            <div>
                              <div>${d.benchmark_cost.toLocaleString()}</div>
                              <div style={{ fontSize: "10px", color: "#94a3b8", marginTop: "2px" }}>{d.benchmark_source || "NADAC"}</div>
                            </div>
                          ) : d.benchmark_note === "pbm_pricing" ? (
                            <span style={{ color: "#f59e0b", fontSize: "12px" }} title="Brand and specialty drugs are priced through commercial channels. NADAC covers generic retail drugs; Medicare ASP covers physician-administered biologics. Ask your PBM for acquisition cost data on these drugs.">PBM pricing *</span>
                          ) : <span style={{ color: "#94a3b8" }}>No benchmark</span>}
                        </td>
                        <td style={tdStyle}>
                          {d.spread != null ? (
                            <span style={{ color: d.spread_flagged ? "#ef4444" : d.spread > 0 ? "#f59e0b" : "#22c55e", fontWeight: "600" }}>
                              {d.spread >= 0 ? "+" : ""}${d.spread.toLocaleString()}
                            </span>
                          ) : <span style={{ color: "#94a3b8" }}>&mdash;</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {(result.top_drugs || []).some(d => d.benchmark_note === "pbm_pricing") && (
                <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "10px", lineHeight: "1.5" }}>
                  * Brand and specialty drugs are priced through commercial channels. NADAC covers generic retail drugs; Medicare ASP covers physician-administered biologics. Ask your PBM for acquisition cost data on these drugs.
                </div>
              )}
            </div>

            {/* Generic Opportunity */}
            {result.generic_opportunity && result.generic_opportunity.length > 0 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(245,158,11,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "16px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "6px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "18px" }}>&#128138;</span> Generic Substitution Opportunities
                </h3>
                <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>
                  These brand drugs may have generic equivalents available at lower cost
                </p>
                {result.generic_opportunity.slice(0, 5).map((g, i) => (
                  <div key={i} style={{ padding: "10px 0", borderBottom: i < Math.min(result.generic_opportunity.length, 5) - 1 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontSize: "14px", fontWeight: "500", color: "#e2e8f0" }}>{g.drug_name}</div>
                        <div style={{ fontSize: "12px", color: "#94a3b8" }}>Generic: {g.generic_name} &middot; {g.claim_count} claim{g.claim_count !== 1 ? "s" : ""}</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "14px", fontWeight: "600", color: "#22c55e" }}>~${g.estimated_generic_savings.toLocaleString()} savings</div>
                        <div style={{ fontSize: "11px", color: "#94a3b8" }}>Current plan paid: ${g.total_plan_paid.toLocaleString()}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Specialty Drug Spend */}
            {result.specialty_drugs && result.specialty_drugs.length > 0 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(168,85,247,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "16px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "6px", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "18px" }}>&#9878;</span> Specialty Drug Spend
                </h3>
                <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>
                  Specialty drugs account for {result.summary.specialty_spend_pct}% of total pharmacy spend
                </p>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                        <th style={thStyle}>Drug</th>
                        <th style={thStyle}>Class</th>
                        <th style={thStyle}>Plan Paid</th>
                        <th style={thStyle}>% of Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.specialty_drugs.slice(0, 10).map((s, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                          <td style={tdStyle}>
                            <div>{s.drug_name}</div>
                            {s.generic_name && <div style={{ fontSize: "11px", color: "#94a3b8" }}>{s.generic_name}</div>}
                          </td>
                          <td style={{ ...tdStyle, fontSize: "12px", color: "#94a3b8" }}>{s.therapeutic_class || "—"}</td>
                          <td style={tdStyle}>${s.plan_paid.toLocaleString()}</td>
                          <td style={{ ...tdStyle, fontWeight: "600", color: s.pct_of_total > 10 ? "#ef4444" : "#f59e0b" }}>{s.pct_of_total}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* PBM Spread Placeholder */}
            {result.pbm_spread_estimate == null ? (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.12)", borderRadius: "14px", padding: "24px", marginBottom: "16px", textAlign: "center" }}>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#94a3b8", marginBottom: "6px" }}>PBM SPREAD ANALYSIS</div>
                <div style={{ fontSize: "16px", fontWeight: "500", color: "#94a3b8", marginBottom: "8px" }}>Coming Soon</div>
                <p style={{ fontSize: "12px", color: "#94a3b8", margin: 0 }}>
                  PBM spread analysis compares what your PBM charges the plan vs. what they pay pharmacies. Load NADAC reference data to enable this analysis.
                </p>
              </div>
            ) : (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "16px", textAlign: "center" }}>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa", marginBottom: "6px" }}>ESTIMATED PBM SPREAD</div>
                <div style={{ fontSize: "32px", fontWeight: "700", color: result.pbm_spread_estimate > 0 ? "#ef4444" : "#22c55e" }}>
                  ${Math.abs(result.pbm_spread_estimate).toLocaleString()}
                </div>
                <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px", margin: "4px 0 0" }}>
                  {result.pbm_spread_estimate > 0
                    ? "Your plan paid this much more than NADAC across benchmarked claims"
                    : "Your plan costs are below NADAC on average"}
                </p>
              </div>
            )}

            {/* What This Means */}
            <div style={{ background: "rgba(255,255,255,0.02)", borderLeft: "4px solid #10b981", borderRadius: "8px", padding: "20px", marginBottom: "24px" }}>
              <div style={{ fontSize: "11px", fontWeight: "600", color: "#10b981", marginBottom: "10px", letterSpacing: "0.05em" }}>WHAT THIS MEANS</div>
              <div style={{ fontSize: "14px", color: "#e2e8f0", lineHeight: "1.7" }}>
                {result.benchmarks.generic_rate_status === "good" ? (
                  <p style={{ margin: "0 0 8px" }}>Your generic dispensing rate of {result.benchmarks.generic_rate}% meets or exceeds the industry benchmark of {result.benchmarks.generic_benchmark}%. This suggests good formulary management.</p>
                ) : (
                  <p style={{ margin: "0 0 8px" }}>Your generic dispensing rate of {result.benchmarks.generic_rate}% is below the industry benchmark of {result.benchmarks.generic_benchmark}%. Increasing generic utilization could reduce pharmacy costs significantly.</p>
                )}
                {result.benchmarks.specialty_status === "good" ? (
                  <p style={{ margin: 0 }}>Specialty drug spending at {result.benchmarks.specialty_spend_pct}% of total pharmacy cost is within the expected range ({result.benchmarks.specialty_benchmark_low}&ndash;{result.benchmarks.specialty_benchmark_high}%).</p>
                ) : (
                  <p style={{ margin: 0 }}>Specialty drug spending at {result.benchmarks.specialty_spend_pct}% of total pharmacy cost exceeds the typical range of {result.benchmarks.specialty_benchmark_low}&ndash;{result.benchmarks.specialty_benchmark_high}%. Consider specialty pharmacy management programs or biosimilar alternatives.</p>
                )}
              </div>
            </div>

            {/* Email copy checkbox */}
            {(isAuthenticated || sessionStorage.getItem("cs_anon_email")) && (
              <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", marginBottom: "8px" }}>
                <input type="checkbox" checked={wantsCopy} onChange={(e) => setWantsCopy(e.target.checked)} style={{ accentColor: "#10b981", width: "16px", height: "16px" }} />
                <span style={{ fontSize: "14px", color: "#94a3b8" }}>Email me a copy of this report</span>
              </label>
            )}

            {/* CTAs */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Link to="/claims-check" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
                Analyze Medical Claims &rarr;
              </Link>
              <Link to="/subscribe" style={{ textAlign: "center", color: "#60a5fa", fontSize: "14px", textDecoration: "none" }}>
                Get ongoing monitoring &rarr;
              </Link>
              <Link to="/dashboard" style={{ textAlign: "center", color: "#94a3b8", fontSize: "14px", textDecoration: "none" }}>
                &larr; Back to Parity Employer
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color = "#f1f5f9" }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(16,185,129,0.18)", borderRadius: "10px", padding: "16px", textAlign: "center" }}>
      <div style={{ fontSize: "12px", color: "#94a3b8", marginBottom: "4px" }}>{label}</div>
      <div style={{ fontSize: "20px", fontWeight: "600", color }}>{value}</div>
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
  background: "#10b981",
  color: "#fff",
  border: "none",
  borderRadius: "8px",
  padding: "14px 28px",
  fontWeight: "600",
  fontSize: "15px",
  cursor: "pointer",
};

const thStyle = { textAlign: "left", padding: "8px 12px", color: "#94a3b8", fontWeight: "500" };
const tdStyle = { padding: "8px 12px", color: "#e2e8f0" };
