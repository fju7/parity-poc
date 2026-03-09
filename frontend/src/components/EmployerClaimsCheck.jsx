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
  const [caaOpen, setCaaOpen] = useState(false);
  const [caaForm, setCaaForm] = useState({
    companyName: "", policyNumber: "", carrier: "UnitedHealthcare", carrierOther: "",
    planYear: "2025", contactName: "", contactEmail: "", contactPhone: "",
  });
  const [caaCopied, setCaaCopied] = useState(false);

  const caaU = (field, val) => setCaaForm({ ...caaForm, [field]: val });
  const caaCarrierOptions = ["UnitedHealthcare", "Cigna", "Aetna / CVS Health", "Anthem / Elevance Health", "BCBS", "Other"];
  const caaIsComplete = caaForm.companyName.trim() && caaForm.policyNumber.trim() && caaForm.carrier && caaForm.planYear;

  const buildCaaLetter = () => {
    const f = caaForm;
    const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
    return `${today}\n\n${f.carrier}${f.carrier === "Other" && f.carrierOther ? ` (${f.carrierOther})` : ""} \u2014 Employer Services / Client Relations\n\nRE: CAA Section 201 Claims Data Request\nPlan Sponsor: ${f.companyName}\nGroup/Policy Number: ${f.policyNumber}\nPlan Year: ${f.planYear}\n\nTo Whom It May Concern:\n\nI am the plan sponsor / authorized representative for the above-referenced employer health plan and am formally requesting machine-readable claims data pursuant to Section 201 of the Consolidated Appropriations Act of 2021 and its implementing regulations.\n\nRequested format: 835 EDI transaction files or equivalent HIPAA-compliant machine-readable format\nScope: All medical and pharmacy claims for plan year ${f.planYear}\n\nPlease confirm receipt of this request and provide an expected delivery timeline. Federal regulations require a response within 30 days.\n\nIf there are any questions or additional authorization requirements, please contact me directly.\n\nSincerely,\n\n${f.contactName}${f.contactEmail ? "\n" + f.contactEmail : ""}${f.contactPhone ? "\n" + f.contactPhone : ""}`;
  };

  const copyCaaLetter = () => {
    navigator.clipboard.writeText(buildCaaLetter()).then(() => {
      setCaaCopied(true);
      setTimeout(() => setCaaCopied(false), 2000);
    });
  };

  const downloadCaaLetter = () => {
    const safeName = caaForm.companyName.replace(/[^a-zA-Z0-9]/g, "-").replace(/-+/g, "-");
    const blob = new Blob([buildCaaLetter()], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `CAA-Request-${safeName}-${caaForm.planYear}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
    return ext.endsWith(".csv") || ext.endsWith(".xlsx") || ext.endsWith(".xls") || ext.endsWith(".835") || ext.endsWith(".edi") || ext.endsWith(".zip");
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
        if (res.status === 402) {
          setError("free_tier_limit");
          setView("error");
          return;
        }
        throw new Error(body.detail || `API error: ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      if (data.session_id) {
        localStorage.setItem("employer_claims_session_id", data.session_id);
        localStorage.setItem("employer_claims_zip_code", zipCode);
      }
      if (data.pricing_tier) {
        localStorage.setItem("employer_pricing_tier", data.pricing_tier);
        localStorage.setItem("employer_annualized_excess", String(data.annualized_excess || 0));
      }
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

            {/* CAA collapsible section */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.12)", borderRadius: "12px", marginBottom: "20px", overflow: "hidden" }}>
              <button
                onClick={() => setCaaOpen(!caaOpen)}
                style={{ width: "100%", background: "none", border: "none", padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", color: "#94a3b8" }}
              >
                <span style={{ fontSize: "14px", fontWeight: "600", color: "#cbd5e1" }}>Don't have claims data yet?</span>
                <span style={{ fontSize: "18px", transform: caaOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>{"\u25BE"}</span>
              </button>
              {caaOpen && (
                <div style={{ padding: "0 20px 20px", fontSize: "14px", color: "#94a3b8", lineHeight: "1.8" }}>
                  <p style={{ margin: "0 0 14px" }}>
                    If your company is fully insured (your carrier pays claims directly), you may not have received claims data automatically &mdash; but you have a legal right to it.
                  </p>
                  <p style={{ margin: "0 0 14px" }}>
                    The Consolidated Appropriations Act of 2021 requires your carrier to provide machine-readable claims data upon request. Fill in the form below to generate a request letter you can send directly.
                  </p>
                  <p style={{ margin: "0 0 14px", fontSize: "13px", color: "#64748b" }}>
                    If you're self-insured, your TPA should be able to provide 835 transaction files directly &mdash; ask your administrator for claims data in 835 EDI format.
                  </p>

                  {/* Letter generator form */}
                  <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", padding: "16px", marginBottom: "14px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                      <div>
                        <label style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Your Company Name *</label>
                        <input value={caaForm.companyName} onChange={e => caaU("companyName", e.target.value)} placeholder="Acme Corp" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Group/Policy Number *</label>
                        <input value={caaForm.policyNumber} onChange={e => caaU("policyNumber", e.target.value)} placeholder="GRP-12345" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                      <div>
                        <label style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Carrier *</label>
                        <select value={caaForm.carrier} onChange={e => caaU("carrier", e.target.value)} style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }}>
                          {caaCarrierOptions.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                        {caaForm.carrier === "Other" && (
                          <input value={caaForm.carrierOther} onChange={e => caaU("carrierOther", e.target.value)} placeholder="Carrier name" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box", marginTop: "6px" }} />
                        )}
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Plan Year *</label>
                        <select value={caaForm.planYear} onChange={e => caaU("planYear", e.target.value)} style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }}>
                          <option value="2024">2024</option>
                          <option value="2025">2025</option>
                          <option value="2026">2026</option>
                        </select>
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
                      <div>
                        <label style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Contact Name</label>
                        <input value={caaForm.contactName} onChange={e => caaU("contactName", e.target.value)} placeholder="Your name" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Contact Email</label>
                        <input value={caaForm.contactEmail} onChange={e => caaU("contactEmail", e.target.value)} placeholder="you@company.com" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#64748b", fontWeight: "500" }}>Phone (optional)</label>
                        <input value={caaForm.contactPhone} onChange={e => caaU("contactPhone", e.target.value)} placeholder="(555) 123-4567" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                    </div>
                  </div>

                  {caaIsComplete && (
                    <>
                      <div style={{ background: "#fff", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "8px", padding: "20px 24px", marginBottom: "12px" }}>
                        <pre style={{ margin: 0, fontSize: "12px", color: "#334155", lineHeight: "1.8", whiteSpace: "pre-wrap", wordWrap: "break-word", fontFamily: "Georgia, 'Times New Roman', serif" }}>
                          {buildCaaLetter()}
                        </pre>
                      </div>
                      <div style={{ display: "flex", gap: "10px", marginBottom: "14px" }}>
                        <button onClick={copyCaaLetter} style={{ background: caaCopied ? "#10b981" : "#3b82f6", color: "#fff", border: "none", borderRadius: "6px", padding: "8px 16px", fontSize: "13px", fontWeight: "600", cursor: "pointer" }}>
                          {caaCopied ? "Copied \u2713" : "Copy Letter"}
                        </button>
                        <button onClick={downloadCaaLetter} style={{ background: "rgba(255,255,255,0.06)", color: "#e2e8f0", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", padding: "8px 16px", fontSize: "13px", fontWeight: "600", cursor: "pointer" }}>
                          Download as .txt
                        </button>
                      </div>
                    </>
                  )}

                  <Link to="/broker/caa-guide" style={{ color: "#60a5fa", fontSize: "13px", textDecoration: "none", fontWeight: "500" }}>
                    Broker guide: How to request claims data from major carriers &rarr;
                  </Link>
                </div>
              )}
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
                <input id="claims-file-input" type="file" accept=".csv,.xlsx,.xls,.835,.edi,.zip" onChange={handleFileInput} style={{ display: "none" }} />
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
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>Supports CSV, Excel, 835 EDI, and ZIP files &middot; Max 10MB</div>
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
        {view === "error" && error === "free_tier_limit" && (
          <div style={{ textAlign: "center", paddingTop: "60px" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>&#128274;</div>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "26px", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px" }}>
              Free claims check used
            </h2>
            <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "480px", margin: "0 auto 24px" }}>
              Your free quarterly claims analysis has been used. Subscribe to unlock unlimited claims checks, RBP calculator, contract parser, and trend monitoring.
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
              <button onClick={() => setView("upload")} style={{ background: "none", border: "none", color: "#64748b", fontSize: "14px", cursor: "pointer" }}>
                &larr; Back
              </button>
            </div>
          </div>
        )}
        {view === "error" && error !== "free_tier_limit" && (
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
              <p style={{ fontSize: "14px", color: "#64748b" }}>
                {result.total_lines_analyzed} claims analyzed &middot; {file?.name}
                {result.source_format?.startsWith("835") && (
                  <span style={{ display: "inline-block", marginLeft: "8px", background: "rgba(59,130,246,0.15)", color: "#60a5fa", fontSize: "11px", fontWeight: "600", padding: "2px 8px", borderRadius: "4px" }}>
                    Parsed from 835 EDI
                  </span>
                )}
              </p>
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

            {/* Pricing Tier Recommendation */}
            {result.pricing_tier && (
              <div style={{
                background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.25)",
                borderRadius: "14px", padding: "24px", marginBottom: "24px",
                display: "flex", alignItems: "center", justifyContent: "space-between",
                flexWrap: "wrap", gap: "16px",
              }}>
                <div>
                  <div style={{ fontSize: "11px", fontWeight: "600", color: "#10b981", letterSpacing: "0.05em", marginBottom: "6px" }}>RECOMMENDED PLAN</div>
                  <div style={{ fontSize: "22px", fontWeight: "700", color: "#f1f5f9", marginBottom: "4px" }}>
                    {result.pricing_tier_label} &mdash; ${result.pricing_tier_price}/mo
                  </div>
                  <div style={{ fontSize: "13px", color: "#94a3b8" }}>
                    Based on ${Math.round(result.annualized_excess).toLocaleString()} annual excess identified.
                    Your subscription pays for itself {Math.round(result.annualized_excess / (result.pricing_tier_price * 12))}x over.
                  </div>
                </div>
                <Link
                  to={`/billing/employer/subscribe`}
                  style={{
                    background: "#10b981", color: "#fff", padding: "12px 24px",
                    borderRadius: "8px", fontWeight: "600", fontSize: "14px",
                    textDecoration: "none", whiteSpace: "nowrap",
                  }}
                >
                  Subscribe &rarr;
                </Link>
              </div>
            )}

            {/* Free tier banner */}
            {!result.pricing_tier && (
              <div style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: "12px", padding: "16px 20px", marginBottom: "24px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
                <div style={{ fontSize: "13px", color: "#fbbf24" }}>
                  <strong>Free tier:</strong> 1 claims check per quarter. Subscribe for unlimited analysis + RBP calculator + trend monitoring.
                </div>
                <Link to="/billing/employer/subscribe" style={{ color: "#fbbf24", fontSize: "13px", fontWeight: "600", textDecoration: "none", whiteSpace: "nowrap" }}>
                  View plans &rarr;
                </Link>
              </div>
            )}

            {/* AI Narrative Summary */}
            {result.narrative && (
              <div style={{ background: "rgba(255,255,255,0.02)", borderLeft: "4px solid #3b82f6", borderRadius: "8px", padding: "20px", marginBottom: "24px" }}>
                <div style={{ fontSize: "11px", fontWeight: "600", color: "#60a5fa", marginBottom: "10px", letterSpacing: "0.05em" }}>AI SUMMARY</div>
                <div style={{ fontSize: "15px", color: "#e2e8f0", fontWeight: "400", lineHeight: "1.6" }}>{result.narrative}</div>
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
              <Link to="/billing/employer/rbp-calculator" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
                Calculate RBP Savings &rarr;
              </Link>
              <Link to="/billing/employer/scorecard" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none", background: "#1e3a5f" }}>
                Grade Your Plan Design &rarr;
              </Link>
              <Link to="/billing/employer/subscribe" style={{ textAlign: "center", color: "#60a5fa", fontSize: "14px", textDecoration: "none" }}>
                {result.pricing_tier ? `Subscribe — ${result.pricing_tier_label} from $${result.pricing_tier_price}/mo` : "Get ongoing monitoring"} &rarr;
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
