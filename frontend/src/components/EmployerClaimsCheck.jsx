import { useState, useCallback, useEffect } from "react";
import { Link } from "react-router-dom";
import { cptLabel } from "../lib/cptLabel";
import { useAuth } from "../context/AuthContext";
import BrokerConnectCard from "./BrokerConnectCard";

import { API_BASE } from "../lib/apiBase";

function SignalContextCard({ cpt }) {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);

  function load() {
    if (loaded) { setOpen(!open); return; }
    fetch(`${API_BASE}/api/signal/evidence-for-code?cpt_code=${encodeURIComponent(cpt)}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d && d.coverage !== "none") setData(d); setLoaded(true); setOpen(true); })
      .catch(() => { setLoaded(true); });
  }

  if (loaded && !data) return null;

  const CONSENSUS_BADGE = {
    strong_consensus: { bg: "#ecfdf5", color: "#059669", label: "Consensus" },
    active_debate: { bg: "#fff7ed", color: "#d97706", label: "Debated" },
    genuine_uncertainty: { bg: "#f1f5f9", color: "#64748b", label: "Uncertain" },
    manufactured_controversy: { bg: "#fef2f2", color: "#dc2626", label: "Controversy" },
  };

  return (
    <div style={{ marginTop: 6 }}>
      <button onClick={load} style={{ background: "none", border: "none", fontSize: 11, color: "#6366f1", cursor: "pointer", padding: 0, textDecoration: "underline" }}>
        {open ? "Hide" : "View"} clinical evidence
      </button>
      {open && data && (
        <div style={{ marginTop: 8, background: "#eef2ff", border: "1px solid #c7d2fe", borderRadius: 10, padding: 14, fontSize: 12 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, cursor: "pointer" }} onClick={() => setOpen(false)}>
            <strong style={{ color: "#1e293b" }}>{data.topic_title}</strong>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontWeight: 700, color: data.score >= 3.5 ? "#059669" : data.score >= 2.5 ? "#d97706" : "#64748b" }}>
                {data.score}/5.0
              </span>
              <span style={{ color: "#94a3b8", fontSize: 14, lineHeight: 1 }} title="Collapse">&times;</span>
            </div>
          </div>
          {data.key_claims?.slice(0, 3).map((c, i) => (
            <div key={i} style={{ marginBottom: 6, paddingLeft: 10, borderLeft: "2px solid #a5b4fc" }}>
              <span style={{ color: "#475569" }}>{c.claim_text}</span>
              {c.consensus_type && CONSENSUS_BADGE[c.consensus_type] && (
                <span style={{ marginLeft: 6, fontSize: 10, fontWeight: 600, padding: "1px 6px", borderRadius: 8, background: CONSENSUS_BADGE[c.consensus_type].bg, color: CONSENSUS_BADGE[c.consensus_type].color }}>
                  {CONSENSUS_BADGE[c.consensus_type].label}
                </span>
              )}
            </div>
          ))}
          <a href={`https://signal.civicscale.ai/${data.topic_slug}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: "#0d7377", marginTop: 4, display: "inline-block" }}>
            View full evidence dashboard →
          </a>
        </div>
      )}
    </div>
  );
}

function SignalActionPlanCards({ lineItems }) {
  const [cards, setCards] = useState([]);

  useEffect(() => {
    if (!lineItems) return;
    const flagged = lineItems.filter(l => l.flag).slice(0, 5);
    const seen = new Set();
    const unique = flagged.filter(l => { if (seen.has(l.cpt_code)) return false; seen.add(l.cpt_code); return true; });

    async function fetchAll() {
      const results = [];
      for (const l of unique) {
        try {
          const res = await fetch(`${API_BASE}/api/signal/evidence-for-code?cpt_code=${encodeURIComponent(l.cpt_code)}`);
          if (res.ok) {
            const d = await res.json();
            if (d.coverage !== "none" && d.score >= 3.5) {
              results.push({ cpt: l.cpt_code, ...d });
            }
          }
        } catch { /* non-fatal */ }
      }
      setCards(results);
    }
    fetchAll();
  }, [lineItems]);

  if (cards.length === 0) return null;

  return (
    <div style={{ marginBottom: 12 }}>
      {cards.map((c, i) => (
        <div key={i} style={{ display: "flex", gap: 14, alignItems: "flex-start", background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.2)", borderRadius: 10, padding: "16px 20px", marginBottom: 10 }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#6366f1", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, flexShrink: 0 }}>⚡</div>
          <div>
            <p style={{ margin: 0, fontSize: 14, color: "#e2e8f0", lineHeight: 1.6 }}>
              <strong>Clinical appropriateness question:</strong> Ask your plan administrator whether CPT {c.cpt} was denied on clinical grounds.
              Signal Intelligence rates the supporting evidence at <strong>{c.score}/5.0</strong>.
            </p>
            <a href={`https://signal.civicscale.ai/${c.topic_slug}`} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: "#818cf8", marginTop: 4, display: "inline-block" }}>
              View {c.topic_title} evidence →
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function EmployerClaimsCheck() {
  const { isAuthenticated, user } = useAuth();
  const [file, setFile] = useState(null);
  const [zipCode, setZipCode] = useState("");
  const [email, setEmail] = useState(() => sessionStorage.getItem("cs_anon_email") || "");
  const [wantsCopy, setWantsCopy] = useState(false);
  const anonEmailKnown = !isAuthenticated && !!sessionStorage.getItem("cs_anon_email");
  const showEmailField = !isAuthenticated && !anonEmailKnown;
  const [dragOver, setDragOver] = useState(false);
  const [fileError, setFileError] = useState("");
  const [view, setView] = useState("upload"); // upload, processing, results, error, column_mapping
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Column mapping recovery state
  const [mappingColumns, setMappingColumns] = useState([]);
  const [mappingSampleRows, setMappingSampleRows] = useState([]);
  const [mappingValues, setMappingValues] = useState({ cpt_code: "", paid_amount: "", billed_amount: "", provider_name: "", service_date: "" });
  const [caaOpen, setCaaOpen] = useState(false);
  const [tpaOpen, setTpaOpen] = useState(false);
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
    if (f && isValidFile(f)) { setFile(f); setFileError(""); }
    else if (f) { setFileError("Unsupported file format. Please upload a CSV, Excel (.xlsx), 835 EDI, or ZIP file."); }
  }, []);

  const handleFileInput = useCallback((e) => {
    const f = e.target.files[0];
    if (f && isValidFile(f)) { setFile(f); setFileError(""); }
    else if (f) { setFileError("Unsupported file format. Please upload a CSV, Excel (.xlsx), 835 EDI, or ZIP file."); }
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
      const resolvedEmail = isAuthenticated ? (user?.email || null) : (email || sessionStorage.getItem("cs_anon_email") || null);
      if (resolvedEmail) formData.append("email", resolvedEmail);
      if (email && !isAuthenticated) sessionStorage.setItem("cs_anon_email", email);

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
        if (res.status === 422) {
          const detail = body.detail || {};
          if (detail.columns) {
            setMappingColumns(detail.columns);
            setMappingSampleRows(detail.sample_rows || []);
            setMappingValues({ cpt_code: "", paid_amount: "", billed_amount: "", provider_name: "", service_date: "" });
            setView("column_mapping");
            return;
          }
        }
        throw new Error(body.detail?.error || body.detail || `API error: ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      if (data.session_id) {
        localStorage.setItem("employer_claims_session_id", data.session_id);
        localStorage.setItem("employer_claims_zip_code", zipCode);
      }
      setView("results");
    } catch (err) {
      clearInterval(progressInterval);
      setError(err.message);
      setView("error");
    }
  };

  const handleMappingSubmit = async () => {
    if (!mappingValues.cpt_code || !mappingValues.paid_amount) return;

    const mapping = { cpt_code: mappingValues.cpt_code, paid_amount: mappingValues.paid_amount };
    if (mappingValues.billed_amount && mappingValues.billed_amount !== "-- skip this field --") mapping.billed_amount = mappingValues.billed_amount;
    if (mappingValues.provider_name && mappingValues.provider_name !== "-- skip this field --") mapping.provider_name = mappingValues.provider_name;
    if (mappingValues.service_date && mappingValues.service_date !== "-- skip this field --") mapping.service_date = mappingValues.service_date;

    setView("processing");
    setProgress(10);
    const progressInterval = setInterval(() => setProgress(p => Math.min(p + 8, 85)), 600);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("zip_code", zipCode);
      formData.append("column_mapping", JSON.stringify(mapping));
      const resolvedEmail = isAuthenticated ? (user?.email || null) : (email || sessionStorage.getItem("cs_anon_email") || null);
      if (resolvedEmail) formData.append("email", resolvedEmail);

      const res = await fetch(`${API_BASE}/api/employer/claims-check`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail?.error || body.detail || `API error: ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      if (data.session_id) {
        localStorage.setItem("employer_claims_session_id", data.session_id);
        localStorage.setItem("employer_claims_zip_code", zipCode);
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
          <Link to="/dashboard" style={{ color: "#60a5fa", textDecoration: "none" }}>Parity Employer</Link>
        </nav>
      </header>

      <div className="cs-home-section" style={{ maxWidth: "800px", margin: "0 auto", paddingTop: "60px", paddingBottom: "80px" }}>

        {/* Tab toggle — Medical / Pharmacy */}
        <div style={{ display: "flex", gap: "4px", background: "rgba(255,255,255,0.04)", borderRadius: "10px", padding: "4px", marginBottom: "28px", maxWidth: "320px", margin: "0 auto 28px" }}>
          <div style={{ flex: 1, textAlign: "center", padding: "10px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: "600", color: "#f1f5f9", background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.3)" }}>
            Medical Claims
          </div>
          <Link to="/pharmacy" style={{ flex: 1, textAlign: "center", padding: "10px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: "600", color: "#94a3b8", textDecoration: "none", background: "transparent" }}>
            Pharmacy Claims
          </Link>
        </div>

        {/* Upload View */}
        {view === "upload" && (
          <>
            <div style={{ textAlign: "center", marginBottom: "36px" }}>
              <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>CLAIMS CHECK</span>
              </div>
              <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 36px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
                Find where your plan costs may exceed benchmarks
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
                  <p style={{ margin: "0 0 14px", fontSize: "13px", color: "#94a3b8" }}>
                    If you're self-insured, your TPA should be able to provide 835 transaction files directly &mdash; ask your administrator for claims data in 835 EDI format.
                  </p>

                  {/* Letter generator form */}
                  <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", padding: "16px", marginBottom: "14px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                      <div>
                        <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "500" }}>Your Company Name *</label>
                        <input value={caaForm.companyName} onChange={e => caaU("companyName", e.target.value)} placeholder="Acme Corp" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "500" }}>Group/Policy Number *</label>
                        <input value={caaForm.policyNumber} onChange={e => caaU("policyNumber", e.target.value)} placeholder="GRP-12345" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginBottom: "10px" }}>
                      <div>
                        <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "500" }}>Carrier *</label>
                        <select value={caaForm.carrier} onChange={e => caaU("carrier", e.target.value)} style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }}>
                          {caaCarrierOptions.map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                        {caaForm.carrier === "Other" && (
                          <input value={caaForm.carrierOther} onChange={e => caaU("carrierOther", e.target.value)} placeholder="Carrier name" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box", marginTop: "6px" }} />
                        )}
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "500" }}>Plan Year *</label>
                        <select value={caaForm.planYear} onChange={e => caaU("planYear", e.target.value)} style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }}>
                          <option value="2024">2024</option>
                          <option value="2025">2025</option>
                          <option value="2026">2026</option>
                        </select>
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px" }}>
                      <div>
                        <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "500" }}>Contact Name</label>
                        <input value={caaForm.contactName} onChange={e => caaU("contactName", e.target.value)} placeholder="Your name" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "500" }}>Contact Email</label>
                        <input value={caaForm.contactEmail} onChange={e => caaU("contactEmail", e.target.value)} placeholder="you@company.com" style={{ width: "100%", padding: "7px 10px", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.03)", color: "#e2e8f0", boxSizing: "border-box" }} />
                      </div>
                      <div>
                        <label style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "500" }}>Phone (optional)</label>
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

            {/* TPA format guide collapsible */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.12)", borderRadius: "12px", marginBottom: "20px", overflow: "hidden" }}>
              <button
                onClick={() => setTpaOpen(!tpaOpen)}
                style={{ width: "100%", background: "none", border: "none", padding: "16px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", color: "#94a3b8" }}
              >
                <span style={{ fontSize: "14px", fontWeight: "600", color: "#cbd5e1" }}>What format does my TPA export?</span>
                <span style={{ fontSize: "18px", transform: tpaOpen ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }}>{"\u25BE"}</span>
              </button>
              {tpaOpen && (
                <div style={{ padding: "0 20px 20px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                  {[
                    { name: "HealthSmart", text: "Export \u2192 Claims Detail Report \u2192 CSV. Columns: 'Procedure Code', 'Amount Paid', 'Amount Billed'" },
                    { name: "Meritain Health", text: "Reports \u2192 Claims \u2192 Download Claims Data \u2192 Excel. Look for 'Proc Cd', 'Net Paid Amt'" },
                    { name: "Trustmark", text: "Employer Portal \u2192 Reports \u2192 Claims Extract. Column names vary \u2014 use our column mapper above." },
                    { name: "Cigna (self-insured/ASO)", text: "myCigna Employer \u2192 Reports \u2192 Medical Claims \u2192 CSV. Columns: 'Procedure', 'Plan Paid Amount'" },
                    { name: "Aetna (ASO)", text: "Navigator \u2192 Reports \u2192 Claims Detail. Look for 'Procedure Code', 'Paid Amount'" },
                    { name: "BCBS (self-insured)", text: "Varies by Blue plan \u2014 look for 835 EDI export option in your TPA portal, which gives the most accurate results." },
                  ].map(tpa => (
                    <div key={tpa.name} style={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px", padding: "12px" }}>
                      <p style={{ margin: "0 0 4px", fontSize: "13px", fontWeight: "600", color: "#0d9488" }}>{tpa.name}</p>
                      <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", lineHeight: "1.5" }}>{tpa.text}</p>
                    </div>
                  ))}
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
                    <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>{(file.size / 1024).toFixed(0)} KB &middot; Click to change</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: "28px", marginBottom: "8px" }}>&#8593;</div>
                    <div style={{ fontSize: "16px", fontWeight: "500", color: "#cbd5e1" }}>Drop your claims file here</div>
                    <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>Supports CSV, Excel, 835 EDI, and ZIP files &middot; Max 10MB</div>
                  </>
                )}
              </div>

              {fileError && (
                <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: 8, padding: "10px 14px", marginTop: 8 }}>
                  <p style={{ margin: 0, fontSize: 13, color: "#fca5a5" }}>{fileError}</p>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: showEmailField ? "1fr 1fr" : "1fr", gap: "16px" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Provider ZIP code</span>
                  <input type="text" maxLength={5} pattern="[0-9]{5}" placeholder="e.g. 33701" value={zipCode} onChange={(e) => setZipCode(e.target.value)} style={inputStyle} />
                </label>
                {showEmailField && (
                  <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <span style={{ fontSize: "14px", fontWeight: "500", color: "#cbd5e1" }}>Email (optional)</span>
                    <input type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
                  </label>
                )}
              </div>

              <button type="submit" disabled={!file || !zipCode || zipCode.length < 5} style={{ ...btnPrimary, opacity: file && zipCode.length >= 5 ? 1 : 0.5, cursor: file && zipCode.length >= 5 ? "pointer" : "not-allowed" }}>
                Analyze Claims
              </button>
            </form>

            <div style={{ marginTop: "24px", fontSize: "12px", color: "#94a3b8", textAlign: "center", lineHeight: "1.6" }}>
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
            <p style={{ fontSize: "14px", color: "#94a3b8" }}>
              {progress < 30 ? "Reading file and detecting columns..." :
               progress < 60 ? "Mapping CPT codes to Medicare benchmarks..." :
               progress < 85 ? "Flagging anomalies and computing variances..." :
               "Finalizing results..."}
            </p>
          </div>
        )}

        {/* Column Mapping Recovery View */}
        {view === "column_mapping" && (
          <div>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "26px", fontWeight: "400", color: "#f1f5f9", marginBottom: "8px" }}>Help us read your file</h2>
            <p style={{ fontSize: "14px", color: "#94a3b8", marginBottom: "16px", lineHeight: "1.6" }}>
              We couldn't automatically identify your columns. Match each field below to the correct column from your file.
            </p>
            <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)", borderRadius: "10px", padding: "12px 16px", marginBottom: "20px" }}>
              <p style={{ margin: 0, fontSize: "13px", color: "#fbbf24", lineHeight: "1.6" }}>
                This is common with TPA exports. Once you map the columns, your analysis will run normally.
              </p>
            </div>

            {/* Sample data preview */}
            {mappingSampleRows.length > 0 && (
              <div style={{ marginBottom: "20px" }}>
                <p style={{ fontSize: "12px", color: "#64748b", marginBottom: "8px" }}>Your file's columns — first {mappingSampleRows.length} rows shown</p>
                <div style={{ overflowX: "auto", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "8px" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                    <thead>
                      <tr>
                        {mappingColumns.map(col => (
                          <th key={col} style={{ padding: "8px 10px", textAlign: "left", color: "#94a3b8", fontWeight: "600", borderBottom: "1px solid rgba(255,255,255,0.08)", whiteSpace: "nowrap" }}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {mappingSampleRows.map((row, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? "rgba(255,255,255,0.01)" : "transparent" }}>
                          {mappingColumns.map(col => (
                            <td key={col} style={{ padding: "6px 10px", color: "#cbd5e1", borderBottom: "1px solid rgba(255,255,255,0.04)", whiteSpace: "nowrap" }}>{row[col] || ""}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Mapping form */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "20px" }}>
              {[
                { key: "cpt_code", label: "CPT / Procedure Code column *", required: true },
                { key: "paid_amount", label: "Amount Paid / Paid Amount column *", required: true },
                { key: "billed_amount", label: "Billed / Charged Amount column (optional)", required: false },
                { key: "provider_name", label: "Provider / Vendor Name column (optional)", required: false },
                { key: "service_date", label: "Date of Service column (optional)", required: false },
              ].map(field => (
                <div key={field.key}>
                  <label style={{ fontSize: "13px", color: "#cbd5e1", fontWeight: "500", marginBottom: "4px", display: "block" }}>{field.label}</label>
                  <select
                    value={mappingValues[field.key]}
                    onChange={e => setMappingValues({ ...mappingValues, [field.key]: e.target.value })}
                    style={{ ...selectStyle, width: "100%" }}
                  >
                    {field.required
                      ? <option value="">— select a column —</option>
                      : <option value="-- skip this field --">— skip this field —</option>
                    }
                    {mappingColumns.map(col => <option key={col} value={col}>{col}</option>)}
                  </select>
                </div>
              ))}
            </div>

            <div style={{ display: "flex", gap: "12px" }}>
              <button
                onClick={handleMappingSubmit}
                disabled={!mappingValues.cpt_code || !mappingValues.paid_amount}
                style={{ ...btnPrimary, opacity: (!mappingValues.cpt_code || !mappingValues.paid_amount) ? 0.5 : 1, width: "auto", flex: 1 }}
              >
                Run Analysis &rarr;
              </button>
              <button onClick={() => setView("upload")} style={{ background: "none", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", padding: "14px 24px", color: "#94a3b8", fontSize: "15px", cursor: "pointer" }}>
                Start Over
              </button>
            </div>
          </div>
        )}

        {/* Error View */}
        {view === "error" && error === "free_tier_limit" && (
          <div style={{ textAlign: "center", paddingTop: "60px" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>&#128274;</div>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "26px", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px" }}>
              Free trial ended
            </h2>
            <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "480px", margin: "0 auto 24px" }}>
              Your 30-day free trial has ended. Subscribe to continue using claims analysis, RBP calculator, contract parser, and trend monitoring.
            </p>
            <div style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: "14px", padding: "24px", maxWidth: "400px", margin: "0 auto 24px" }}>
              <div style={{ fontSize: "13px", color: "#10b981", fontWeight: "600", marginBottom: "8px" }}>PLANS START AT</div>
              <div style={{ fontSize: "36px", fontWeight: "700", color: "#f1f5f9" }}>$99<span style={{ fontSize: "16px", fontWeight: "400", color: "#94a3b8" }}>/mo</span></div>
              <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>30-day free trial · Savings guarantee</div>
            </div>
            <Link to="/subscribe" style={{ ...btnPrimary, display: "inline-block", textDecoration: "none", width: "auto", padding: "14px 36px", background: "#10b981" }}>
              View Plans & Subscribe
            </Link>
            <div style={{ marginTop: "16px" }}>
              <button onClick={() => setView("upload")} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: "14px", cursor: "pointer" }}>
                &larr; Back
              </button>
            </div>
          </div>
        )}
        {view === "error" && error !== "free_tier_limit" && (
          <div style={{ textAlign: "center", paddingTop: "80px" }}>
            <div style={{ fontSize: "40px", marginBottom: "16px" }}>!</div>
            <h2 style={{ fontSize: "22px", fontWeight: "600", color: "#f1f5f9", marginBottom: "12px" }}>Analysis failed</h2>
            <p style={{ fontSize: "14px", color: "#fca5a5", marginBottom: "12px" }}>{error}</p>
            <p style={{ fontSize: "12px", color: "#64748b", marginBottom: "24px" }}>If this continues, contact us at admin@civicscale.ai</p>
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
              <p style={{ fontSize: "14px", color: "#94a3b8" }}>
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

            {/* Rate year note */}
            {result.rate_year_note && (
              <div style={{ background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: "10px", padding: "12px 16px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "14px" }}>&#x1f4c5;</span>
                <span style={{ fontSize: "13px", color: "#93c5fd" }}>{result.rate_year_note}</span>
              </div>
            )}

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
                <div style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "6px" }}>ESTIMATED ANNUAL EXCESS SPEND</div>
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
                  to={`/subscribe`}
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
                  <strong>Free trial:</strong> Unlimited analysis for 30 days. Subscribe for ongoing access + RBP calculator + trend monitoring.
                </div>
                <Link to="/subscribe" style={{ color: "#fbbf24", fontSize: "13px", fontWeight: "600", textDecoration: "none", whiteSpace: "nowrap" }}>
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

            {/* Action Plan */}
            {result.action_plan && result.action_plan.length > 0 && (
              <div style={{ marginBottom: "24px" }}>
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
                <SignalActionPlanCards lineItems={result.line_items} />
                <button onClick={() => window.print()} style={{ background: "none", border: "1px solid rgba(255,255,255,0.15)", borderRadius: "8px", padding: "6px 14px", fontSize: "13px", color: "#94a3b8", cursor: "pointer" }}>
                  Print Action Plan
                </button>
              </div>
            )}

            {/* Print stylesheet */}
            <style>{`@media print {
              header, nav, .tab-toggle, button, a.back-link { display: none !important; }
              body, html { background: white !important; }
              * {
                color: #1e293b !important;
                background-color: white !important;
                border-color: #d1d5db !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
              }
              h1, h2, h3, strong, b { color: #0f172a !important; }
              th { background-color: #f1f5f9 !important; color: #334155 !important; }
              td { border-bottom: 1px solid #e5e7eb !important; }
              span[style*="color: #10b981"], span[style*="color: #059669"],
              span[style*="color: #0d9488"], span[style*="color: #0d7377"] {
                color: #047857 !important;
              }
              span[style*="color: #ef4444"], span[style*="color: #f87171"] {
                color: #dc2626 !important;
              }
              span[style*="color: #f59e0b"], span[style*="color: #d97706"] {
                color: #b45309 !important;
              }
              div[style*="border-radius"] {
                border: 1px solid #d1d5db !important;
              }
            }`}</style>

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
                            <SignalContextCard cpt={l.cpt_code} />
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Level 2 Analysis */}
            {result.level2 && result.level2.has_level2 && (
              <>
                <div style={{ textAlign: "center", marginBottom: "16px", marginTop: "8px" }}>
                  <h3 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "22px", fontWeight: "400", color: "#f1f5f9", marginBottom: "6px" }}>
                    Level 2 Analysis
                  </h3>
                  <p style={{ fontSize: "12px", color: "#94a3b8" }}>Available because your file included 835 EDI provider data</p>
                </div>

                {/* Card 1 — Provider Price Variation */}
                <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "18px" }}>&#127973;</span> Provider Price Variation
                  </h3>
                  {result.level2.provider_variation.flagged_cpts.length > 0 ? (
                    <>
                      <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "12px" }}>Significant price variation exists for the same procedures across providers</p>
                      {result.level2.provider_variation.flagged_cpts.slice(0, 3).map((v, i) => (
                        <div key={i} style={{ padding: "10px 0", borderBottom: i < 2 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
                          <div style={{ fontSize: "13px", color: "#e2e8f0" }}>
                            <strong>{cptLabel(v.cpt_code)}</strong> &mdash; Lowest-cost provider <span style={{ color: "#22c55e" }}>${v.low_provider.avg_paid.toLocaleString()}</span> vs Highest-cost provider <span style={{ color: "#f59e0b" }}>${v.high_provider.avg_paid.toLocaleString()}</span> &middot; <span style={{ color: "#ef4444" }}>{v.variation_ratio}x variation</span>
                          </div>
                        </div>
                      ))}
                      <div style={{ marginTop: "12px", fontSize: "13px", color: "#10b981", fontWeight: "500" }}>
                        Estimated cost reduction opportunity: up to ${result.level2.provider_variation.total_variation_opportunity.toLocaleString()} if members select lower-cost providers
                      </div>
                    </>
                  ) : (
                    <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>Consistent pricing across providers &mdash; no significant variation detected</p>
                  )}
                </div>

                {/* Card 2 — Site of Care */}
                <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "18px" }}>&#128205;</span> Site of Care Opportunities
                  </h3>
                  {result.level2.site_of_care.has_hospital_outpatient && result.level2.site_of_care.flagged_cpts.length > 0 ? (
                    <>
                      <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "12px" }}>Some procedures are performed in hospital settings where costs are substantially higher for the same service</p>
                      {result.level2.site_of_care.flagged_cpts.slice(0, 3).map((s, i) => (
                        <div key={i} style={{ padding: "10px 0", borderBottom: i < 2 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
                          <div style={{ fontSize: "13px", color: "#e2e8f0" }}>
                            <strong>{cptLabel(s.cpt_code)}</strong> &mdash; Hospital <span style={{ color: "#f59e0b" }}>${s.hospital_avg.toLocaleString()}</span> vs Non-hospital <span style={{ color: "#22c55e" }}>${s.non_hospital_avg.toLocaleString()}</span> &middot; {s.hospital_claims} hospital claim{s.hospital_claims !== 1 ? "s" : ""}
                          </div>
                        </div>
                      ))}
                      <div style={{ marginTop: "12px", fontSize: "13px", color: "#10b981", fontWeight: "500" }}>
                        Estimated opportunity: up to ${result.level2.site_of_care.total_site_opportunity.toLocaleString()} if members choose lower-cost care settings
                      </div>
                    </>
                  ) : (
                    <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>No hospital outpatient site-of-care issues detected</p>
                  )}
                </div>

                {/* Card 3 — Network Analysis */}
                <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "18px" }}>&#128279;</span> Network Coverage
                  </h3>
                  <div style={{ marginBottom: "12px" }}>
                    {result.level2.network_leakage.flag === "LOW" && (
                      <p style={{ fontSize: "13px", color: "#22c55e", margin: 0, fontWeight: "500" }}>Network utilization looks healthy &mdash; less than 5% of spend is out-of-network</p>
                    )}
                    {result.level2.network_leakage.flag === "MODERATE" && (
                      <p style={{ fontSize: "13px", color: "#f59e0b", margin: 0, fontWeight: "500" }}>{result.level2.network_leakage.out_of_network_pct}% of spend (${result.level2.network_leakage.out_of_network_paid.toLocaleString()}) appears out-of-network &mdash; review network adequacy</p>
                    )}
                    {result.level2.network_leakage.flag === "HIGH" && (
                      <p style={{ fontSize: "13px", color: "#ef4444", margin: 0, fontWeight: "500" }}>{result.level2.network_leakage.out_of_network_pct}% of spend (${result.level2.network_leakage.out_of_network_paid.toLocaleString()}) is out-of-network &mdash; significant network leakage detected</p>
                    )}
                  </div>
                  <div>
                    {result.level2.denial_rate.flag === "NORMAL" && (
                      <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>Claim denial rate is within normal range ({result.level2.denial_rate.rate_pct}%)</p>
                    )}
                    {result.level2.denial_rate.flag === "ELEVATED" && (
                      <p style={{ fontSize: "13px", color: "#f59e0b", margin: 0 }}>Elevated denial rate ({result.level2.denial_rate.rate_pct}%) &mdash; may indicate network or authorization issues</p>
                    )}
                  </div>
                </div>

                {/* Card 4 — Carrier Rate Summary */}
                <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "24px", marginBottom: "32px" }}>
                  <h3 style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "18px" }}>&#128202;</span> Your Carrier's Effective Rates
                  </h3>
                  {result.level2.carrier_rates.top_cpts.length > 0 ? (
                    <>
                      <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "12px" }}>Based on your claims data, here's what your carrier is actually paying for high-volume procedures:</p>
                      <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", fontSize: "13px", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.08)" }}>
                              <th style={thStyle}>CPT</th>
                              <th style={thStyle}>Claims</th>
                              <th style={thStyle}>Avg Allowed</th>
                              <th style={thStyle}>Medicare</th>
                              <th style={thStyle}>Multiple</th>
                            </tr>
                          </thead>
                          <tbody>
                            {result.level2.carrier_rates.top_cpts.slice(0, 10).map((r, i) => (
                              <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                                <td style={tdStyle}>{cptLabel(r.cpt_code)}</td>
                                <td style={tdStyle}>{r.claim_count}</td>
                                <td style={tdStyle}>${r.avg_allowed.toLocaleString()}</td>
                                <td style={tdStyle}>${r.medicare_rate.toLocaleString()}</td>
                                <td style={{ ...tdStyle, color: r.multiple > 2 ? "#ef4444" : r.multiple > 1.5 ? "#f59e0b" : "#e2e8f0", fontWeight: "600" }}>{r.multiple}x</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div style={{ marginTop: "12px", fontSize: "13px", color: "#60a5fa", fontWeight: "500" }}>
                        Average across top procedures: {result.level2.carrier_rates.avg_multiple_vs_medicare}x Medicare
                      </div>
                    </>
                  ) : (
                    <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>Insufficient claims volume for carrier rate analysis</p>
                  )}
                </div>

                {/* Help Your Employees CTA */}
                <div style={{ background: "rgba(13,148,136,0.08)", border: "1px solid rgba(13,148,136,0.25)", borderRadius: "14px", padding: "28px", marginBottom: "32px" }}>
                  <h3 style={{ fontSize: "17px", fontWeight: "600", color: "#f1f5f9", marginBottom: "10px" }}>
                    Help Your Employees Make Informed Choices
                  </h3>
                  <p style={{ fontSize: "14px", color: "#94a3b8", lineHeight: "1.7", marginBottom: "16px" }}>
                    Employer-level analysis shows where the opportunities are &mdash; but cost reduction happens when individual employees choose lower-cost providers and care settings before elective procedures. Parity Health gives your employees the same benchmarking tools at the individual claim level: they can look up fair prices for procedures in their area, compare providers, and understand their bills.
                  </p>
                  <a href="https://health.civicscale.ai" target="_blank" rel="noopener noreferrer" style={{ display: "inline-block", background: "#0d9488", color: "#fff", padding: "10px 22px", borderRadius: "8px", fontWeight: "600", fontSize: "14px", textDecoration: "none" }}>
                    Learn About Parity Health &rarr;
                  </a>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "12px", marginBottom: 0 }}>
                    Employees who shop on price before elective care reduce plan costs over time &mdash; which directly affects your renewal rates.
                  </p>
                </div>
              </>
            )}

            {/* Level 2 unavailable notice */}
            {result.level2 && !result.level2.has_level2 && (
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "14px", padding: "24px", marginBottom: "32px", textAlign: "center" }}>
                <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0, lineHeight: "1.7" }}>
                  Level 2 analysis (provider variation, site of care, carrier rates) requires 835 EDI format with provider data. CSV uploads support Level 1 Medicare benchmarking only.
                </p>
              </div>
            )}

            {/* Email copy checkbox */}
            {(isAuthenticated || sessionStorage.getItem("cs_anon_email")) && (
              <label style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer", marginBottom: "8px" }}>
                <input type="checkbox" checked={wantsCopy} onChange={(e) => setWantsCopy(e.target.checked)} style={{ accentColor: "#3b82f6", width: "16px", height: "16px" }} />
                <span style={{ fontSize: "14px", color: "#94a3b8" }}>Email me a copy of this report</span>
              </label>
            )}

            {/* Broker Connect */}
            {result.summary.total_excess_2x > 0 && (
              <div style={{ marginBottom: "20px" }}>
                <BrokerConnectCard
                  benchmarkData={{
                    email: isAuthenticated ? user?.email : (sessionStorage.getItem("cs_anon_email") || ""),
                    excess_amount: result.summary.total_excess_2x,
                  }}
                  source="claims"
                />
              </div>
            )}

            {/* CTAs */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <Link to="/rbp-calculator" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
                Calculate RBP Savings &rarr;
              </Link>
              <Link to="/scorecard" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none", background: "#1e3a5f" }}>
                Grade Your Plan Design &rarr;
              </Link>
              <Link to="/subscribe" style={{ textAlign: "center", color: "#60a5fa", fontSize: "14px", textDecoration: "none" }}>
                {result.pricing_tier ? `Subscribe — ${result.pricing_tier_label} from $${result.pricing_tier_price}/mo` : "Get ongoing monitoring"} &rarr;
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
    <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "10px", padding: "16px", textAlign: "center" }}>
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

const thStyle = { textAlign: "left", padding: "8px 12px", color: "#94a3b8", fontWeight: "500" };
const tdStyle = { padding: "8px 12px", color: "#e2e8f0" };
