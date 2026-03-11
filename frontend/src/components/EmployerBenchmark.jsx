import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const INDUSTRIES = [
  "Agriculture / Forestry / Fishing",
  "Construction",
  "Finance / Real Estate / Insurance",
  "Manufacturing",
  "Other Services",
  "Professional Services",
  "Retail Trade",
  "Transportation / Utilities",
  "Wholesale Trade",
];

const COMPANY_SIZES = [
  { value: "10-49", label: "10\u201349 employees" },
  { value: "50-199", label: "50\u2013199 employees" },
  { value: "200-999", label: "200\u2013999 employees" },
  { value: "1000+", label: "1,000+ employees" },
];

const STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
  "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
  "VA","WA","WV","WI","WY","DC",
];

function ordinalSuffix(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

export default function EmployerBenchmark() {
  const [industry, setIndustry] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [state, setState] = useState("");
  const [pepm, setPepm] = useState("");
  const [email, setEmail] = useState(() => sessionStorage.getItem("cs_anon_email") || "");
  const [view, setView] = useState("form"); // form, email, results, loading
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [methodOpen, setMethodOpen] = useState(false);
  const [wantsCopy, setWantsCopy] = useState(false);
  const { isAuthenticated, user } = useAuth();

  const formValid = industry && companySize && state && pepm && parseFloat(pepm) > 0;

  const resolvedEmail = isAuthenticated ? (user?.email || null) : (email || sessionStorage.getItem("cs_anon_email") || null);

  const handleSubmitForm = (e) => {
    e.preventDefault();
    if (!formValid) return;
    // Signed-in or email already known → skip email step
    if (isAuthenticated || sessionStorage.getItem("cs_anon_email")) {
      runBenchmark();
    } else {
      setView("email");
    }
  };

  const handleSubmitEmail = async (e) => {
    e.preventDefault();
    if (email) sessionStorage.setItem("cs_anon_email", email);
    runBenchmark();
  };

  const runBenchmark = async () => {
    setView("loading");
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/employer/benchmark`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry,
          company_size: companySize,
          state,
          pepm_input: parseFloat(pepm),
          email: resolvedEmail,
        }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResult(data);
      setWantsCopy(!!resolvedEmail);
      setView("results");
    } catch (err) {
      setError(err.message);
      setView("form");
    }
  };

  const pctColor = (pct) => {
    if (pct <= 40) return "#22c55e";
    if (pct <= 60) return "#60a5fa";
    if (pct <= 75) return "#f59e0b";
    return "#ef4444";
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

      <div className="cs-home-section" style={{ maxWidth: "640px", margin: "0 auto", paddingTop: "60px", paddingBottom: "80px" }}>
        {/* Form View */}
        {view === "form" && (
          <>
            <div style={{ textAlign: "center", marginBottom: "40px" }}>
              <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>FREE BENCHMARK</span>
              </div>
              <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
                How does your health plan stack up?
              </h1>
              <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7" }}>
                Enter your plan costs and see how you compare to employers in your industry, size, and state.
              </p>
            </div>

            {error && (
              <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "10px", padding: "12px 16px", marginBottom: "20px", fontSize: "14px", color: "#fca5a5" }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmitForm} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Industry</span>
                <select value={industry} onChange={(e) => setIndustry(e.target.value)} style={selectStyle}>
                  <option value="">Select industry...</option>
                  {INDUSTRIES.map((i) => <option key={i} value={i}>{i}</option>)}
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Company Size</span>
                <select value={companySize} onChange={(e) => setCompanySize(e.target.value)} style={selectStyle}>
                  <option value="">Select size...</option>
                  {COMPANY_SIZES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>State</span>
                <select value={state} onChange={(e) => setState(e.target.value)} style={selectStyle}>
                  <option value="">Select state...</option>
                  {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </label>

              <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Current employer PEPM cost ($)</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 558"
                  value={pepm}
                  onChange={(e) => setPepm(e.target.value)}
                  style={inputStyle}
                />
                <span style={{ fontSize: "12px", color: "#64748b" }}>Per Employee Per Month — your employer-paid share of single-coverage premiums</span>
              </label>

              <button type="submit" disabled={!formValid} style={{ ...btnPrimary, opacity: formValid ? 1 : 0.5, cursor: formValid ? "pointer" : "not-allowed" }}>
                Get My Benchmark
              </button>
            </form>
          </>
        )}

        {/* Email Capture */}
        {view === "email" && (
          <>
            <div style={{ textAlign: "center", marginBottom: "32px" }}>
              <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "28px", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px" }}>
                Almost there
              </h2>
              <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7" }}>
                Enter your email to receive your benchmark results. We'll also save them so you can revisit anytime.
              </p>
            </div>
            <form onSubmit={handleSubmitEmail} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <input
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={inputStyle}
              />
              <button type="submit" style={btnPrimary}>Show My Results</button>
              <button type="button" onClick={() => { setEmail(""); handleSubmitEmail({ preventDefault: () => {} }); }} style={{ background: "none", border: "none", color: "#64748b", fontSize: "13px", cursor: "pointer" }}>
                Skip — show results without saving
              </button>
            </form>
          </>
        )}

        {/* Loading */}
        {view === "loading" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <div style={{ width: "40px", height: "40px", border: "3px solid rgba(59,130,246,0.2)", borderTop: "3px solid #3b82f6", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto 20px" }} />
            <p style={{ fontSize: "16px", color: "#94a3b8" }}>Calculating your benchmark...</p>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
        )}

        {/* Results */}
        {view === "results" && result && (
          <>
            <div style={{ textAlign: "center", marginBottom: "32px" }}>
              <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "28px", fontWeight: "400", color: "#f1f5f9", marginBottom: "8px" }}>
                Your Benchmark Results
              </h2>
              <p style={{ fontSize: "14px", color: "#64748b" }}>
                {result.input.industry} &middot; {result.input.company_size} employees &middot; {result.input.state}
              </p>
            </div>

            {/* Percentile */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "16px", padding: "32px", textAlign: "center", marginBottom: "20px" }}>
              <div style={{ fontSize: "13px", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>Your Percentile</div>
              <div style={{ fontSize: "56px", fontWeight: "700", color: pctColor(result.result.percentile), lineHeight: "1" }}>
                {Math.round(result.result.percentile)}
                <span style={{ fontSize: "24px", fontWeight: "400", verticalAlign: "super" }}>{ordinalSuffix(Math.round(result.result.percentile))}</span>
              </div>
              <p style={{ fontSize: "14px", color: "#94a3b8", marginTop: "12px", lineHeight: "1.6", maxWidth: "400px", margin: "12px auto 0" }}>
                {result.result.interpretation}
              </p>
            </div>

            {/* Dollar Gap */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "20px" }}>
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "12px", padding: "20px" }}>
                <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "6px" }}>Your PEPM</div>
                <div style={{ fontSize: "24px", fontWeight: "600", color: "#f1f5f9" }}>${result.input.pepm_input.toLocaleString()}</div>
              </div>
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "12px", padding: "20px" }}>
                <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "6px" }}>Adjusted Median</div>
                <div style={{ fontSize: "24px", fontWeight: "600", color: "#60a5fa" }}>${result.benchmarks.adjusted_median_pepm.toLocaleString()}</div>
              </div>
            </div>

            {/* Annual Gap */}
            <div style={{ background: result.result.dollar_gap_annual > 0 ? "rgba(239,68,68,0.06)" : "rgba(34,197,94,0.06)", border: `1px solid ${result.result.dollar_gap_annual > 0 ? "rgba(239,68,68,0.2)" : "rgba(34,197,94,0.2)"}`, borderRadius: "12px", padding: "20px", textAlign: "center", marginBottom: "20px" }}>
              <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "6px" }}>Annual Gap per Employee</div>
              <div style={{ fontSize: "28px", fontWeight: "700", color: result.result.dollar_gap_annual > 0 ? "#ef4444" : "#22c55e" }}>
                {result.result.dollar_gap_annual > 0 ? "+" : ""}${Math.abs(result.result.dollar_gap_annual).toLocaleString()}
              </div>
              <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                {result.result.dollar_gap_annual > 0 ? "above" : "below"} the adjusted median for your segment
              </div>
            </div>

            {/* Distribution */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "12px", padding: "20px", marginBottom: "32px" }}>
              <div style={{ fontSize: "13px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px" }}>PEPM Distribution</div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#64748b", marginBottom: "8px" }}>
                <span>P10: ${result.distribution.p10}</span>
                <span>P25: ${result.distribution.p25}</span>
                <span>P50: ${result.distribution.p50}</span>
                <span>P75: ${result.distribution.p75}</span>
                <span>P90: ${result.distribution.p90}</span>
              </div>
              <div style={{ height: "8px", background: "rgba(255,255,255,0.06)", borderRadius: "4px", position: "relative" }}>
                <div style={{ position: "absolute", left: `${Math.min(result.result.percentile, 98)}%`, top: "-4px", width: "16px", height: "16px", borderRadius: "50%", background: pctColor(result.result.percentile), transform: "translateX(-50%)" }} />
              </div>
            </div>

            {/* Contextual Framing — shown when above 50th percentile */}
            {result.result.percentile > 50 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: "12px", padding: "24px", marginBottom: "20px" }}>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#f59e0b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "12px" }}>What This Means</div>
                <p style={{ fontSize: "14px", color: "#cbd5e1", lineHeight: "1.7", margin: "0 0 16px" }}>
                  Being above the median doesn't mean your plan is poorly managed — it means there may be opportunities
                  to negotiate better rates at your next renewal. Many employers in this range find savings by adjusting
                  network contracts, plan design, or pharmacy benefits.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {result.result.percentile > 65 && (
                    <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                      <span style={{ color: "#f59e0b", fontSize: "14px", flexShrink: 0 }}>&#9679;</span>
                      <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", lineHeight: "1.6" }}>
                        <strong style={{ color: "#cbd5e1" }}>Orthopedics &amp; specialist costs</strong> — Employers above the 65th percentile often see outsized spending on musculoskeletal procedures and specialist visits. Site-of-care steering and centers of excellence programs can reduce these costs by 15–30%.
                      </p>
                    </div>
                  )}
                  {result.result.percentile > 55 && (
                    <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                      <span style={{ color: "#f59e0b", fontSize: "14px", flexShrink: 0 }}>&#9679;</span>
                      <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", lineHeight: "1.6" }}>
                        <strong style={{ color: "#cbd5e1" }}>Imaging &amp; diagnostics</strong> — Advanced imaging (MRI, CT) costs vary 3–10x depending on where employees receive care. Freestanding imaging centers often charge 50–70% less than hospital outpatient departments.
                      </p>
                    </div>
                  )}
                  <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                    <span style={{ color: "#f59e0b", fontSize: "14px", flexShrink: 0 }}>&#9679;</span>
                    <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", lineHeight: "1.6" }}>
                      <strong style={{ color: "#cbd5e1" }}>Pharmacy &amp; specialty drugs</strong> — Pharmacy costs are the fastest-growing component of employer health spend. GLP-1 drugs, biologics, and specialty medications can account for 30–40% of total plan costs.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Methodology */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.12)", borderRadius: "12px", marginBottom: "32px", overflow: "hidden" }}>
              <button
                onClick={() => setMethodOpen(!methodOpen)}
                style={{ width: "100%", background: "none", border: "none", padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", color: "#94a3b8" }}
              >
                <span style={{ fontSize: "13px", fontWeight: "600", letterSpacing: "0.02em" }}>How We Calculate This</span>
                <span style={{ fontSize: "18px", transform: methodOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>{"\u25BE"}</span>
              </button>
              {methodOpen && (
                <div style={{ padding: "0 20px 20px", fontSize: "13px", color: "#94a3b8", lineHeight: "1.7" }}>
                  <div style={{ marginBottom: "16px" }}>
                    <div style={{ fontWeight: "600", color: "#cbd5e1", marginBottom: "6px" }}>Your percentile ranking</div>
                    <p style={{ margin: 0 }}>
                      We compare your per-employee-per-month (PEPM) health cost against {result.benchmarks?.sample_note || "thousands of"} employers in your industry and region using data from the Medical Expenditure Panel Survey (MEPS-IC 2024), the KFF Employer Health Benefits Survey (2025), and the Bureau of Labor Statistics. Your percentile shows where you rank — {Math.round(result.result.percentile)}{ordinalSuffix(Math.round(result.result.percentile))} percentile means you spend more than {Math.round(result.result.percentile)}% of similar employers.
                    </p>
                  </div>
                  <div style={{ marginBottom: "16px" }}>
                    <div style={{ fontWeight: "600", color: "#cbd5e1", marginBottom: "6px" }}>Your dollar gap</div>
                    <p style={{ margin: 0 }}>
                      The dollar gap is the difference between your current PEPM cost and the median (50th percentile) for your industry and company size. We multiply this by your employee count to show the annual impact.
                    </p>
                  </div>
                  <div>
                    <div style={{ fontWeight: "600", color: "#cbd5e1", marginBottom: "10px" }}>Data sources</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                      <span style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: "6px", padding: "5px 10px", fontSize: "11px", color: "#60a5fa", whiteSpace: "nowrap" }}>MEPS-IC 2024 · 50 States</span>
                      <span style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: "6px", padding: "5px 10px", fontSize: "11px", color: "#60a5fa", whiteSpace: "nowrap" }}>KFF EHBS 2025 · 1,862 Employers Surveyed</span>
                      <span style={{ background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: "6px", padding: "5px 10px", fontSize: "11px", color: "#60a5fa", whiteSpace: "nowrap" }}>BLS ECEC 2024 · National Compensation Survey</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Email copy checkbox */}
            <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#94a3b8", cursor: "pointer", marginBottom: "8px" }}>
              <input type="checkbox" checked={wantsCopy} onChange={(e) => setWantsCopy(e.target.checked)} style={{ accentColor: "#3b82f6" }} />
              Email me a copy of this report
            </label>

            {/* CTAs */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Link to="/billing/employer/claims-check" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
                Upload Claims for Detailed Analysis &rarr;
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

const selectStyle = {
  ...inputStyle,
  appearance: "auto",
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
