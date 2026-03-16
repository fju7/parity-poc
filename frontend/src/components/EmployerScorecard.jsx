import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import BrokerConnectCard from "./BrokerConnectCard";

import { API_BASE } from "../lib/apiBase";
const gradeColor = (g) => {
  if (g === "A") return "#22c55e";
  if (g === "B+" || g === "B") return "#60a5fa";
  if (g === "C+" || g === "C") return "#f59e0b";
  return "#ef4444";
};

const scoreIcon = (s) => {
  if (s >= 75) return { icon: "\u2713", color: "#22c55e", label: "Pass" };
  if (s >= 50) return { icon: "\u25CB", color: "#f59e0b", label: "Partial" };
  return { icon: "\u2717", color: "#ef4444", label: "Fail" };
};

export default function EmployerScorecard() {
  const { isAuthenticated, user } = useAuth();
  const [file, setFile] = useState(null);
  const [email, setEmail] = useState(() => sessionStorage.getItem("cs_anon_email") || "");
  const [wantsCopy, setWantsCopy] = useState(false);
  const anonEmailKnown = !isAuthenticated && !!sessionStorage.getItem("cs_anon_email");
  const showEmailField = !isAuthenticated && !anonEmailKnown;
  const [planName, setPlanName] = useState("");
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
    if (f) setFile(f);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setView("processing");
    setProgress(10);
    setError(null);

    const progressInterval = setInterval(() => {
      setProgress((p) => Math.min(p + 5, 80));
    }, 800);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const resolvedEmail = isAuthenticated ? (user?.email || null) : (email || sessionStorage.getItem("cs_anon_email") || null);
      if (resolvedEmail) formData.append("email", resolvedEmail);
      if (email && !isAuthenticated) sessionStorage.setItem("cs_anon_email", email);
      if (planName) formData.append("plan_name", planName);

      const res = await fetch(`${API_BASE}/api/employer/scorecard`, {
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

      {/* Header */}
      <header className="cs-home-header">
        <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", fontWeight: "700", color: "#0a1628" }}>C</div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>CivicScale</span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/dashboard" style={{ color: "#60a5fa", textDecoration: "none" }}>Parity Employer</Link>
        </nav>
      </header>

      <div className="cs-home-section" style={{ maxWidth: "640px", margin: "0 auto", paddingTop: "60px", paddingBottom: "80px" }}>

        {/* Upload View */}
        {view === "upload" && (
          <>
            <div style={{ textAlign: "center", marginBottom: "36px" }}>
              <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>PLAN SCORECARD</span>
              </div>
              <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
                Grade your health plan
              </h1>
              <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "480px", margin: "0 auto" }}>
                Upload your Summary of Benefits and Coverage (SBC) PDF. Our AI reads every detail and scores your plan against best-practice benchmarks.
              </p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Drop zone */}
              <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => document.getElementById("sbc-file-input").click()}
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
                <input id="sbc-file-input" type="file" accept=".pdf" onChange={handleFileInput} style={{ display: "none" }} />
                {file ? (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#10003;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#22c55e" }}>{file.name}</div>
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>{(file.size / 1024).toFixed(0)} KB &middot; Click to change</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#8593;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#cbd5e1" }}>Drop your SBC PDF here</div>
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px" }}>PDF format &middot; Max 10MB</div>
                  </>
                )}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: showEmailField ? "1fr 1fr" : "1fr", gap: "16px" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Plan name (optional)</span>
                  <input type="text" placeholder="e.g. Blue Cross PPO" value={planName} onChange={(e) => setPlanName(e.target.value)} style={inputStyle} />
                </label>
                {showEmailField && (
                  <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Email (optional)</span>
                    <input type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
                  </label>
                )}
              </div>

              <button type="submit" disabled={!file} style={{ ...btnPrimary, opacity: file ? 1 : 0.5, cursor: file ? "pointer" : "not-allowed" }}>
                Grade My Plan
              </button>
            </form>

            <div style={{ marginTop: "24px", fontSize: "12px", color: "#475569", textAlign: "center", lineHeight: "1.6" }}>
              Your SBC is processed by AI and not stored after analysis. We extract plan design features only — no member data.
            </div>
          </>
        )}

        {/* Processing View */}
        {view === "processing" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "24px", fontWeight: "400", color: "#f1f5f9", marginBottom: "24px" }}>
              Reading your SBC...
            </h2>
            <div style={{ maxWidth: "400px", margin: "0 auto 16px", background: "rgba(255,255,255,0.06)", borderRadius: "8px", overflow: "hidden", height: "8px" }}>
              <div style={{ height: "100%", width: `${progress}%`, background: "linear-gradient(90deg, #3b82f6, #60a5fa)", borderRadius: "8px", transition: "width 0.5s ease" }} />
            </div>
            <p style={{ fontSize: "14px", color: "#64748b" }}>
              {progress < 30 ? "Extracting plan details from PDF..." :
               progress < 60 ? "Scoring deductibles, copays, and coverage..." :
               progress < 85 ? "Generating grade and savings estimate..." :
               "Finalizing scorecard..."}
            </p>
          </div>
        )}

        {/* Error View */}
        {view === "error" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>!</div>
            <h2 style={{ fontSize: "22px", fontWeight: "600", color: "#f1f5f9", marginBottom: "12px" }}>Could not grade this plan</h2>
            <p style={{ fontSize: "14px", color: "#fca5a5", marginBottom: "24px" }}>{error}</p>
            <button onClick={() => setView("upload")} style={btnPrimary}>Try Again</button>
          </div>
        )}

        {/* Results View */}
        {view === "results" && result && (
          <>
            <div style={{ textAlign: "center", marginBottom: "28px" }}>
              <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "28px", fontWeight: "400", color: "#f1f5f9", marginBottom: "8px" }}>
                Plan Scorecard
              </h2>
              <p style={{ fontSize: "14px", color: "#64748b" }}>{result.plan_name} &middot; {result.network_type}</p>
            </div>

            {/* Grade */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "16px", padding: "36px", textAlign: "center", marginBottom: "20px" }}>
              <div style={{ fontSize: "72px", fontWeight: "700", color: gradeColor(result.grade), lineHeight: "1" }}>
                {result.grade}
              </div>
              <div style={{ fontSize: "14px", color: "#94a3b8", marginTop: "8px" }}>
                Overall Score: {result.score}/100
              </div>
              {result.interpretation && (
                <p style={{ fontSize: "14px", color: "#94a3b8", marginTop: "16px", lineHeight: "1.7", maxWidth: "480px", margin: "16px auto 0", textAlign: "left" }}>
                  {result.interpretation.context}
                </p>
              )}
            </div>

            {/* Action recommendation */}
            {result.interpretation && (
              <div style={{ borderLeft: "3px solid #0d9488", paddingLeft: "16px", marginBottom: "20px" }}>
                <p style={{ fontSize: "14px", color: "#cbd5e1", lineHeight: "1.6", margin: 0 }}>
                  {result.interpretation.action}
                </p>
              </div>
            )}

            {/* Action Plan */}
            {result.action_plan && result.action_plan.length > 0 && (
              <div style={{ marginBottom: "20px" }}>
                <h3 style={{ fontSize: "16px", fontWeight: "600", color: "#f1f5f9", marginBottom: "4px" }}>Your 3-Step Action Plan</h3>
                <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "16px" }}>Specific questions to bring to your next broker or carrier meeting.</p>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "12px" }}>
                  {result.action_plan.map((step, i) => (
                    <div key={i} style={{ display: "flex", gap: "14px", alignItems: "flex-start", background: "rgba(13,148,136,0.08)", border: "1px solid rgba(13,148,136,0.2)", borderRadius: "10px", padding: "16px 20px" }}>
                      <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#0d9488", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "13px", fontWeight: "700", flexShrink: 0 }}>{i + 1}</div>
                      <p style={{ margin: 0, fontSize: "14px", color: "#e2e8f0", lineHeight: "1.6" }}>{step}</p>
                    </div>
                  ))}
                </div>
                <button onClick={() => window.print()} style={{ background: "none", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", padding: "6px 14px", fontSize: "13px", color: "#94a3b8", cursor: "pointer" }}>
                  Print Action Plan
                </button>
              </div>
            )}

            {/* Print stylesheet */}
            <style>{`@media print {
              header, nav, .tab-toggle, button:not(.print-keep), a.back-link { display: none !important; }
              body { background: white !important; color: #1e293b !important; }
              .results-card { background: white !important; border: 1px solid #e2e8f0 !important; }
            }`}</style>

            {/* Savings Estimate */}
            {result.savings_estimate_per_ee > 0 && (
              <div style={{ background: "rgba(59,130,246,0.04)", border: "1px solid rgba(59,130,246,0.12)", borderRadius: "12px", padding: "20px", textAlign: "center", marginBottom: "24px" }}>
                <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "6px" }}>ESTIMATED SAVINGS POTENTIAL</div>
                <div style={{ fontSize: "28px", fontWeight: "700", color: "#60a5fa" }}>
                  ${result.savings_estimate_per_ee.toLocaleString()}/yr per employee
                </div>
                <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                  Based on plan design opportunities identified &mdash; these are negotiable at renewal
                </div>
              </div>
            )}

            {/* Scored Criteria */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "32px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>Scoring Breakdown</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {(result.scored_criteria || []).map((c) => {
                  const si = scoreIcon(c.score);
                  return (
                    <div key={c.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 12px", borderRadius: "8px", background: "rgba(255,255,255,0.02)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span style={{ color: si.color, fontWeight: "700", fontSize: "14px", width: "18px" }}>{si.icon}</span>
                        <span style={{ fontSize: "14px", color: "#e2e8f0" }}>{c.label}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span style={{ fontSize: "12px", color: "#64748b" }}>wt: {c.weight}%</span>
                        <span style={{ fontSize: "14px", fontWeight: "600", color: si.color, minWidth: "36px", textAlign: "right" }}>{Math.round(c.score)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Email copy checkbox */}
            {(isAuthenticated || sessionStorage.getItem("cs_anon_email")) && (
              <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", marginBottom: "8px" }}>
                <input type="checkbox" checked={wantsCopy} onChange={(e) => setWantsCopy(e.target.checked)} style={{ accentColor: "#3b82f6", width: "16px", height: "16px" }} />
                <span style={{ fontSize: "14px", color: "#94a3b8" }}>Email me a copy of this report</span>
              </label>
            )}

            {/* Broker Connect */}
            <div style={{ marginBottom: "20px" }}>
              <BrokerConnectCard
                benchmarkData={{
                  email: isAuthenticated ? user?.email : (sessionStorage.getItem("cs_anon_email") || ""),
                }}
                source="scorecard"
              />
            </div>

            {/* CTAs */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Link to="/subscribe" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
                Get Ongoing Plan Monitoring &rarr;
              </Link>
              <Link to="/dashboard" style={{ textAlign: "center", color: "#64748b", fontSize: "14px", textDecoration: "none" }}>
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
