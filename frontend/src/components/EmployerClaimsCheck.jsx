import { useState, useCallback } from "react";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function EmployerClaimsCheck() {
  const [file, setFile] = useState(null);
  const [zipCode, setZipCode] = useState("");
  const [email, setEmail] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [view, setView] = useState("upload"); // upload, processing, results, error
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && isValidFile(f)) setFile(f);
  }, []);

  const handleFileInput = useCallback((e) => {
    const f = e.target.files[0];
    if (f && isValidFile(f)) setFile(f);
  }, []);

  const isValidFile = (f) => {
    const ext = f.name.toLowerCase();
    return ext.endsWith(".csv") || ext.endsWith(".xlsx") || ext.endsWith(".xls");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !zipCode) return;

    setView("processing");
    setProgress(10);
    setError(null);

    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 8, 85));
    }, 600);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("zip_code", zipCode);
      if (email) formData.append("email", email);

      const res = await fetch(`${API_BASE}/api/employer/claims-check`, {
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

  const flagColor = (flag) => {
    if (flag === "SEVERE") return "#ef4444";
    if (flag === "HIGH") return "#f59e0b";
    if (flag === "ELEVATED") return "#60a5fa";
    if (flag === "LOW") return "#22c55e";
    return "#64748b";
  };

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

      <div className="cs-home-section" style={{ maxWidth: "800px", margin: "0 auto", paddingTop: "60px", paddingBottom: "80px" }}>

        {/* Upload View */}
        {view === "upload" && (
          <>
            <div style={{ textAlign: "center", marginBottom: "36px" }}>
              <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>CLAIMS CHECK</span>
              </div>
              <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
                Find what your plan is overpaying
              </h1>
              <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "560px", margin: "0 auto" }}>
                Upload your claims file and we'll compare every line against CMS Medicare benchmarks for your geography.
              </p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => document.getElementById("claims-file-input").click()}
                style={{
                  border: `2px dashed ${dragOver ? "#3b82f6" : file ? "#22c55e" : "rgba(255,255,255,0.15)"}`,
                  borderRadius: "14px",
                  padding: "48px 24px",
                  textAlign: "center",
                  cursor: "pointer",
                  background: dragOver ? "rgba(59,130,246,0.04)" : "rgba(255,255,255,0.01)",
                  transition: "all 0.2s",
                }}
              >
                <input id="claims-file-input" type="file" accept=".csv,.xlsx,.xls" onChange={handleFileInput} style={{ display: "none" }} />
                {file ? (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#10003;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#22c55e" }}>{file.name}</div>
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>{(file.size / 1024).toFixed(0)} KB &middot; Click to change</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#8593;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#cbd5e1" }}>Drop your claims file here</div>
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>CSV or Excel &middot; Max 10MB</div>
                  </>
                )}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Provider ZIP code</span>
                  <input type="text" maxLength={5} pattern="[0-9]{5}" placeholder="e.g. 33701" value={zipCode} onChange={(e) => setZipCode(e.target.value)} style={inputStyle} />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Email (optional)</span>
                  <input type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
                </label>
              </div>

              <button type="submit" disabled={!file || !zipCode || zipCode.length < 5} style={{ ...btnPrimary, opacity: file && zipCode.length >= 5 ? 1 : 0.5, cursor: file && zipCode.length >= 5 ? "pointer" : "not-allowed" }}>
                Analyze Claims
              </button>
            </form>

            <div style={{ marginTop: "24px", fontSize: "12px", color: "#475569", textAlign: "center", lineHeight: "1.6" }}>
              Your data is processed securely. We use AI to auto-detect column headers. No patient-identifiable data is stored.
            </div>
          </>
        )}

        {/* Processing View */}
        {view === "processing" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "24px", fontWeight: "400", color: "#f1f5f9", marginBottom: "24px" }}>
              Analyzing your claims...
            </h2>
            <div style={{ maxWidth: "400px", margin: "0 auto 16px", background: "rgba(255,255,255,0.06)", borderRadius: "8px", overflow: "hidden", height: "8px" }}>
              <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg, #3b82f6, #60a5fa)", borderRadius: "8px", transition: "width 0.5s ease" }} />
            </div>
            <p style={{ fontSize: "14px", color: "#64748b" }}>
              {progress < 30 ? "Reading file and detecting columns..." :
               progress < 60 ? "Mapping CPT codes to Medicare benchmarks..." :
               progress < 85 ? "Flagging anomalies and computing variances..." :
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
                Claims Analysis Complete
              </h2>
              <p style={{ fontSize: "14px", color: "#64748b" }}>{result.total_lines_analyzed} claims analyzed &middot; {file?.name}</p>
            </div>

            {/* Summary Banner */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px", marginBottom: "24px" }}>
              <StatCard label="Total Claims" value={result.summary.total_claims.toLocaleString()} />
              <StatCard label="Total Paid" value={`$${result.summary.total_paid.toLocaleString()}`} />
              <StatCard label="Flagged" value={result.summary.flagged_count.toLocaleString()} color="#f59e0b" />
              <StatCard label="Excess (>2x)" value={`$${result.summary.total_excess_2x.toLocaleString()}`} color="#ef4444" />
            </div>

            {/* Highest excess callout */}
            {result.summary.top_flagged_cpt && (
              <div style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "12px", padding: "20px", marginBottom: "24px" }}>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#fca5a5", marginBottom: "6px" }}>HIGHEST EXCESS PROCEDURE</div>
                <div style={{ fontSize: "22px", fontWeight: "700", color: "#ef4444" }}>
                  CPT {result.summary.top_flagged_cpt} &mdash; ${result.summary.top_flagged_excess.toLocaleString()} excess
                </div>
                <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                  Total paid above 2x Medicare for this procedure across all claims
                </div>
              </div>
            )}

            {/* Annualized estimate */}
            {result.summary.total_excess_2x > 0 && (
              <div style={{ background: "rgba(59,130,246,0.04)", border: "1px solid rgba(59,130,246,0.12)", borderRadius: "12px", padding: "20px", marginBottom: "24px", textAlign: "center" }}>
                <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "6px" }}>ESTIMATED ANNUAL EXCESS SPEND</div>
                <div style={{ fontSize: "32px", fontWeight: "700", color: "#60a5fa" }}>
                  ${(result.summary.total_excess_2x * 12).toLocaleString()}
                </div>
                <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                  Annualized from this claims file &middot; amounts paid above 2x Medicare
                </div>
              </div>
            )}

            {/* Top 10 Flagged Procedures Table */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "32px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Top Flagged Procedures</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                      <th style={thStyle}>CPT</th>
                      <th style={thStyle}>Paid</th>
                      <th style={thStyle}>Medicare</th>
                      <th style={thStyle}>Ratio</th>
                      <th style={thStyle}>Flag</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.line_items || [])
                      .filter((l) => l.flag)
                      .slice(0, 10)
                      .map((l, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                          <td style={tdStyle}>{l.cpt_code}</td>
                          <td style={tdStyle}>${l.paid_amount?.toLocaleString()}</td>
                          <td style={tdStyle}>{l.medicare_rate ? `$${l.medicare_rate.toLocaleString()}` : "—"}</td>
                          <td style={tdStyle}>{l.ratio ? `${l.ratio}x` : "—"}</td>
                          <td style={tdStyle}>
                            <span style={{ color: flagColor(l.flag), fontWeight: "600" }}>{l.flag}</span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* CTAs */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Link to="/billing/employer/scorecard" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
                Grade Your Plan Design &rarr;
              </Link>
              <Link to="/billing/employer/subscribe" style={{ textAlign: "center", color: "#60a5fa", fontSize: "14px", textDecoration: "none" }}>
                Get ongoing monitoring &rarr;
              </Link>
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

function StatCard({ label, value, color = "#f1f5f9" }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "10px", padding: "16px", textAlign: "center" }}>
      <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>{label}</div>
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
  background: "#3b82f6",
  color: "#fff",
  border: "none",
  borderRadius: "8px",
  padding: "14px 28px",
  fontWeight: "600",
  fontSize: "15px",
  cursor: "pointer",
};

const thStyle = { textAlign: "left", padding: "8px 12px", color: "#64748b", fontWeight: "500" };
const tdStyle = { padding: "8px 12px", color: "#e2e8f0" };
