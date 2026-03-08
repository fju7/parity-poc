import { useState, useCallback } from "react";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function EmployerContractParser() {
  const [file, setFile] = useState(null);
  const [zipCode, setZipCode] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [view, setView] = useState("upload"); // upload, processing, results, error
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.toLowerCase().endsWith(".pdf")) setFile(f);
  }, []);

  const handleFileInput = useCallback((e) => {
    const f = e.target.files[0];
    if (f && f.name.toLowerCase().endsWith(".pdf")) setFile(f);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !zipCode) return;

    setView("processing");
    setProgress(10);
    setError(null);

    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 5, 85));
    }, 800);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("zip_code", zipCode);

      const res = await fetch(`${API_BASE}/api/employer/contract-parse`, {
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

  const varianceColor = (pct) => {
    if (pct == null) return "#64748b";
    if (pct <= 10) return "#22c55e";
    if (pct <= 30) return "#f59e0b";
    return "#ef4444";
  };

  const rateBasisLabel = (basis) => {
    if (basis === "fee_schedule") return "Fixed fee schedule";
    if (basis === "percent_medicare") return "Percentage of Medicare";
    if (basis === "mixed") return "Mixed (fixed + percentage)";
    return "Unknown";
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
                <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>CONTRACT ANALYSIS</span>
              </div>
              <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
                Are your contracted rates competitive?
              </h1>
              <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "560px", margin: "0 auto" }}>
                Upload your carrier contract or fee schedule PDF. We'll extract your negotiated rates and compare them against CMS Medicare benchmarks.
              </p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => document.getElementById("contract-file-input").click()}
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
                <input id="contract-file-input" type="file" accept=".pdf" onChange={handleFileInput} style={{ display: "none" }} />
                {file ? (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#10003;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#22c55e" }}>{file.name}</div>
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>{(file.size / 1024).toFixed(0)} KB &middot; Click to change</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#8593;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#cbd5e1" }}>Upload your carrier contract or fee schedule PDF</div>
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>PDF only &middot; Max 10MB</div>
                  </>
                )}
              </div>

              <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Provider ZIP code</span>
                <input type="text" maxLength={5} pattern="[0-9]{5}" placeholder="e.g. 33701" value={zipCode} onChange={(e) => setZipCode(e.target.value)} style={inputStyle} />
              </label>

              <button type="submit" disabled={!file || !zipCode || zipCode.length < 5} style={{ ...btnPrimary, opacity: file && zipCode.length >= 5 ? 1 : 0.5, cursor: file && zipCode.length >= 5 ? "pointer" : "not-allowed" }}>
                Analyze Contract
              </button>
            </form>

            <div style={{ marginTop: "24px", fontSize: "12px", color: "#475569", textAlign: "center", lineHeight: "1.6" }}>
              Your contract is processed securely with AI. No patient data is involved. Rate information is not stored.
            </div>
          </>
        )}

        {/* Processing View */}
        {view === "processing" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "24px", fontWeight: "400", color: "#f1f5f9", marginBottom: "24px" }}>
              Analyzing your contract...
            </h2>
            <div style={{ maxWidth: "400px", margin: "0 auto 16px", background: "rgba(255,255,255,0.06)", borderRadius: "8px", overflow: "hidden", height: "8px" }}>
              <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg, #3b82f6, #60a5fa)", borderRadius: "8px", transition: "width 0.5s ease" }} />
            </div>
            <p style={{ fontSize: "14px", color: "#64748b" }}>
              {progress < 25 ? "Reading contract PDF..." :
               progress < 50 ? "Extracting negotiated rates..." :
               progress < 75 ? "Comparing to Medicare benchmarks..." :
               "Finalizing analysis..."}
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
                Contract Analysis Complete
              </h2>
              <p style={{ fontSize: "14px", color: "#64748b" }}>{file?.name}</p>
            </div>

            {/* Section 1: Contract Summary */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "24px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Contract Summary</h3>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "2px" }}>Carrier</div>
                  <div style={{ fontSize: "15px", color: "#f1f5f9", fontWeight: "500" }}>{result.carrier_name || "Not identified"}</div>
                </div>
                <div>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "2px" }}>Effective Date</div>
                  <div style={{ fontSize: "15px", color: "#f1f5f9", fontWeight: "500" }}>{result.contract_effective_date || "Not found"}</div>
                </div>
                <div style={{ gridColumn: "1 / -1" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "2px" }}>Rate Basis</div>
                  <div style={{ fontSize: "15px", color: "#f1f5f9", fontWeight: "500" }}>{rateBasisLabel(result.rate_basis)}</div>
                </div>
              </div>

              {result.rate_basis === "percent_medicare" && result.medicare_percentage && (
                <div style={{ marginTop: "16px", background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: "10px", padding: "20px", textAlign: "center" }}>
                  <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "6px" }}>YOUR CONTRACT PAYS</div>
                  <div style={{ fontSize: "36px", fontWeight: "700", color: "#60a5fa" }}>{result.medicare_percentage}%</div>
                  <div style={{ fontSize: "14px", color: "#94a3b8", marginTop: "4px" }}>of Medicare rates</div>
                </div>
              )}
            </div>

            {/* Section 2: Rate Comparison Table (fixed fee schedule) */}
            {result.line_items && result.line_items.some(i => i.variance_pct != null) && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Rate Comparison</h3>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                        <th style={thStyle}>Procedure</th>
                        <th style={thStyle}>CPT</th>
                        <th style={thStyle}>Your Rate</th>
                        <th style={thStyle}>Medicare</th>
                        <th style={thStyle}>Variance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...result.line_items]
                        .filter(i => i.variance_pct != null)
                        .sort((a, b) => (b.variance_pct || 0) - (a.variance_pct || 0))
                        .map((item, i) => (
                          <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                            <td style={tdStyle}>{item.description || "—"}</td>
                            <td style={tdStyle}>{item.cpt_code}</td>
                            <td style={tdStyle}>${item.negotiated_rate?.toLocaleString()}</td>
                            <td style={tdStyle}>{item.medicare_rate ? `$${item.medicare_rate.toLocaleString()}` : "—"}</td>
                            <td style={tdStyle}>
                              <span style={{ color: varianceColor(item.variance_pct), fontWeight: "600" }}>
                                {item.variance_pct > 0 ? "+" : ""}{item.variance_pct}%
                              </span>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Benchmark comparison for percent-of-Medicare contracts */}
            {result.benchmark_comparison && result.benchmark_comparison.length > 0 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "24px" }}>
                <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>
                  What {result.medicare_percentage}% of Medicare Means
                </h3>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                        <th style={thStyle}>CPT Code</th>
                        <th style={thStyle}>Medicare Rate</th>
                        <th style={thStyle}>Your Contracted Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.benchmark_comparison.map((item, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                          <td style={tdStyle}>{item.cpt_code}</td>
                          <td style={tdStyle}>${item.medicare_rate?.toLocaleString()}</td>
                          <td style={tdStyle}>${item.contracted_rate?.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Section 3: Contract Narrative */}
            {result.contract_narrative && (
              <div style={{ background: "rgba(255,255,255,0.02)", borderLeft: "4px solid #3b82f6", borderRadius: "8px", padding: "20px", marginBottom: "24px" }}>
                <div style={{ fontSize: "11px", fontWeight: "600", color: "#60a5fa", marginBottom: "10px", letterSpacing: "0.05em" }}>CONTRACT ANALYSIS</div>
                <div style={{ fontSize: "15px", color: "#e2e8f0", fontWeight: "400", lineHeight: "1.6" }}>{result.contract_narrative}</div>
              </div>
            )}

            {/* Notes */}
            {result.notes && (
              <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "24px", padding: "0 4px" }}>
                <strong style={{ color: "#94a3b8" }}>Notes:</strong> {result.notes}
              </div>
            )}

            {/* CTAs */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Link to="/billing/employer/claims-check" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
                Analyze Your Claims Data &rarr;
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
