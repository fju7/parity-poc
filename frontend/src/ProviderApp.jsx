import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import * as XLSX from "xlsx";
import { supabase } from "./lib/supabase.js";
import { LogoIcon } from "./components/CivicScaleHomepage.jsx";
import "./components/CivicScaleHomepage.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const SPECIALTIES = [
  "Internal Medicine",
  "Family Medicine",
  "Cardiology",
  "Orthopedics",
  "Dermatology",
  "Radiology",
  "Pathology/Lab",
  "Other",
];

export default function ProviderApp() {
  // "landing" | "sent" | "onboarding" | "dashboard"
  const [view, setView] = useState(null);
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [authError, setAuthError] = useState("");
  const [activeTab, setActiveTab] = useState("contract");

  // Onboarding form state
  const [formData, setFormData] = useState({
    practice_name: "",
    specialty: "",
    npi: "",
    zip_code: "",
  });
  const [formError, setFormError] = useState("");
  const [formSaving, setFormSaving] = useState(false);

  // ── Contract Integrity state ──
  const [contractStep, setContractStep] = useState("upload-rates");
  const [contractError, setContractError] = useState("");
  const [parsedRates, setParsedRates] = useState(null); // { payers, rows }
  const [savingRates, setSavingRates] = useState(false);
  const [savedContractRates, setSavedContractRates] = useState({}); // {cpt: rate}
  const [savedPayerName, setSavedPayerName] = useState("");
  const [parsedRemittance, setParsedRemittance] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [sortField, setSortField] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  // Auth bootstrap
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      if (s) {
        setSession(s);
        loadProfile(s.user.id);
      } else {
        setView("landing");
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      if (s) {
        setSession(s);
        loadProfile(s.user.id);
      } else {
        setSession(null);
        setProfile(null);
        setView("landing");
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  async function loadProfile(userId) {
    const { data, error } = await supabase
      .from("provider_profiles")
      .select("*")
      .eq("user_id", userId)
      .maybeSingle();

    if (error) {
      console.error("[ProviderApp] Error loading profile:", error);
      setView("onboarding");
      return;
    }

    if (data) {
      setProfile(data);
      setView("dashboard");
    } else {
      setView("onboarding");
    }
  }

  // Magic link send
  const handleSendLink = useCallback(async (e) => {
    e.preventDefault();
    setSending(true);
    setAuthError("");

    const origin = window.location.hostname === "localhost"
      ? window.location.origin
      : "https://civicscale.ai";

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: origin + "/provider" },
    });

    setSending(false);
    if (error) {
      setAuthError(error.message);
    } else {
      setView("sent");
    }
  }, [email]);

  // Onboarding submit
  const handleOnboardingSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!formData.practice_name.trim()) {
      setFormError("Practice name is required.");
      return;
    }
    setFormSaving(true);
    setFormError("");

    const { data, error } = await supabase
      .from("provider_profiles")
      .insert({
        user_id: session.user.id,
        practice_name: formData.practice_name.trim(),
        specialty: formData.specialty || null,
        npi: formData.npi.trim() || null,
        zip_code: formData.zip_code.trim() || null,
      })
      .select()
      .single();

    setFormSaving(false);
    if (error) {
      setFormError(error.message);
    } else {
      setProfile(data);
      setView("dashboard");
    }
  }, [session, formData]);

  // Sign out
  const handleSignOut = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setProfile(null);
    setView("landing");
  }, []);

  // ── Contract Integrity handlers ──

  function resetContract() {
    setContractStep("upload-rates");
    setContractError("");
    setParsedRates(null);
    setSavedContractRates({});
    setSavedPayerName("");
    setParsedRemittance(null);
    setAnalysisResult(null);
    setSortField(null);
    setSortDir("asc");
  }

  async function handleDownloadTemplate() {
    try {
      const resp = await fetch(`${API_BASE}/api/provider/contract-template`);
      if (!resp.ok) throw new Error("Failed to download template");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "contract_rates_template.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setContractError("Could not download template. Is the backend running?");
    }
  }

  function handleRatesFileUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setContractError("");

    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const wb = XLSX.read(evt.target.result, { type: "array" });
        // Find "Contract Rates" sheet or use first sheet
        const sheetName = wb.SheetNames.find(n => n.toLowerCase().includes("contract")) || wb.SheetNames[0];
        const ws = wb.Sheets[sheetName];
        const data = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" });

        if (data.length < 5) {
          setContractError("Template appears empty. Please fill in CPT codes and rates starting at row 5.");
          return;
        }

        // Row 4 (index 3) = payer headers starting at column D (index 3)
        const headerRow = data[3] || [];
        const payers = [];
        for (let i = 3; i < headerRow.length; i++) {
          const name = String(headerRow[i] || "").trim();
          if (name) payers.push({ index: i, name });
        }

        if (payers.length === 0) {
          setContractError("No payer names found in row 4 (columns D onward). Check the template format.");
          return;
        }

        // Rows 5+ (index 4+): Col A = CPT, Col B = description, Cols D+ = rates
        const rows = [];
        for (let r = 4; r < data.length; r++) {
          const row = data[r];
          const cpt = String(row[0] || "").trim();
          if (!cpt) continue;
          const desc = String(row[1] || "").trim();
          const rates = {};
          for (const p of payers) {
            const val = parseFloat(row[p.index]);
            if (!isNaN(val) && val > 0) rates[p.name] = val;
          }
          if (Object.keys(rates).length > 0) {
            rows.push({ cpt, description: desc, rates });
          }
        }

        if (rows.length === 0) {
          setContractError("No valid CPT codes with rates found. Check that rates are in columns D onward.");
          return;
        }

        setParsedRates({ payers: payers.map(p => p.name), rows });
        setContractStep("preview-rates");
      } catch (err) {
        setContractError("Could not parse Excel file: " + err.message);
      }
    };
    reader.readAsArrayBuffer(file);
  }

  async function handleSaveRates() {
    if (!parsedRates || !session) return;
    setSavingRates(true);
    setContractError("");

    // Save for each payer
    const firstPayer = parsedRates.payers[0];
    const ratesPayload = parsedRates.rows.map(r => ({
      cpt: r.cpt,
      description: r.description,
      rates: r.rates,
    }));

    try {
      const resp = await fetch(`${API_BASE}/api/provider/save-rates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: session.user.id,
          payer_name: firstPayer,
          rates: ratesPayload,
        }),
      });
      if (!resp.ok) throw new Error("Failed to save rates");

      // Build flat rate lookup for first payer (used in analysis)
      const flatRates = {};
      for (const row of parsedRates.rows) {
        if (row.rates[firstPayer]) {
          flatRates[row.cpt] = row.rates[firstPayer];
        }
      }
      setSavedContractRates(flatRates);
      setSavedPayerName(firstPayer);
      setContractStep("upload-835");
    } catch (err) {
      setContractError("Failed to save contract rates: " + err.message);
    } finally {
      setSavingRates(false);
    }
  }

  async function handle835Upload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setContractError("");
    setContractStep("parsing-835");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch(`${API_BASE}/api/provider/parse-835`, {
        method: "POST",
        body: formData,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to parse 835 file");
      }
      const data = await resp.json();
      setParsedRemittance(data);
      setContractStep("preview-835");
    } catch (err) {
      setContractError(err.message);
      setContractStep("upload-835");
    }
  }

  async function handleRunAnalysis() {
    if (!parsedRemittance || !session) return;
    setContractStep("analyzing");
    setContractError("");

    const remittanceLines = parsedRemittance.line_items.map(item => ({
      cpt_code: item.cpt_code,
      code_type: item.code_type || "CPT",
      billed_amount: item.billed_amount || 0,
      paid_amount: item.paid_amount || 0,
      units: item.units || 1,
      adjustments: (item.adjustments || []).map(a => a.code || "").join(", "),
      claim_id: item.claim_id || "",
    }));

    try {
      const resp = await fetch(`${API_BASE}/api/provider/analyze-contract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: session.user.id,
          payer_name: savedPayerName || parsedRemittance.payer_name || "",
          zip_code: profile?.zip_code || "",
          contract_rates: savedContractRates,
          remittance_lines: remittanceLines,
        }),
      });
      if (!resp.ok) throw new Error("Analysis failed");
      const data = await resp.json();
      setAnalysisResult(data);
      setContractStep("report");
    } catch (err) {
      setContractError("Analysis failed: " + err.message);
      setContractStep("preview-835");
    }
  }

  function handleSort(field) {
    if (sortField === field) {
      setSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  }

  function getSortedLines() {
    if (!analysisResult?.line_items) return [];
    const lines = [...analysisResult.line_items];
    if (!sortField) return lines;

    const flagOrder = { UNDERPAID: 0, DENIED: 1, OVERPAID: 2, NO_CONTRACT: 3, CORRECT: 4 };
    lines.sort((a, b) => {
      let va, vb;
      if (sortField === "flag") {
        va = flagOrder[a.flag] ?? 5;
        vb = flagOrder[b.flag] ?? 5;
      } else {
        va = a[sortField] ?? 0;
        vb = b[sortField] ?? 0;
      }
      if (va < vb) return sortDir === "asc" ? -1 : 1;
      if (va > vb) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return lines;
  }

  // ── Shared nav ──
  const nav = (
    <nav className="cs-nav">
      <Link className="cs-nav-logo" to="/">
        <LogoIcon />
        <span className="cs-nav-wordmark">CivicScale</span>
      </Link>
      <div className="cs-nav-links">
        <Link to="/provider">For Providers</Link>
      </div>
    </nav>
  );

  // Don't render until auth check completes
  if (view === null) {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p style={{ color: "var(--cs-slate)" }}>Loading...</p>
        </div>
      </div>
    );
  }

  // ── LANDING VIEW ──
  if (view === "landing" || view === "sent") {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 420, padding: "0 16px" }}>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
                Parity Provider
              </h1>
              <p style={{ color: "var(--cs-slate)", marginTop: 8, fontSize: 15 }}>
                Audit your payer contracts. Find what they owe you.
              </p>
            </div>

            {view === "sent" ? (
              <div style={{
                padding: 24, borderRadius: 12, border: "1px solid var(--cs-teal)",
                background: "var(--cs-teal-pale)", textAlign: "center"
              }}>
                <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginBottom: 4 }}>
                  Check your email
                </p>
                <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
                  We sent a login link to <strong>{email}</strong>. Click it to sign in.
                </p>
                <button
                  onClick={() => setView("landing")}
                  style={{
                    marginTop: 16, background: "none", border: "none",
                    color: "var(--cs-teal)", cursor: "pointer", fontSize: 14,
                    textDecoration: "underline",
                  }}
                >
                  Use a different email
                </button>
              </div>
            ) : (
              <form onSubmit={handleSendLink}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{
                    display: "block", fontSize: 14, fontWeight: 500,
                    color: "var(--cs-navy)", marginBottom: 6,
                  }}>
                    Email address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="doctor@yourpractice.com"
                    style={{
                      width: "100%", padding: "10px 12px", borderRadius: 8,
                      border: "1px solid var(--cs-border)", fontSize: 15,
                      outline: "none", boxSizing: "border-box",
                    }}
                  />
                </div>

                {authError && (
                  <div style={{
                    padding: 12, borderRadius: 8, background: "#fef2f2",
                    border: "1px solid #fecaca", marginBottom: 16,
                  }}>
                    <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{authError}</p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={sending}
                  className="cs-btn-primary"
                  style={{
                    width: "100%", justifyContent: "center",
                    opacity: sending ? 0.6 : 1,
                  }}
                >
                  {sending ? "Sending..." : "Send Login Link"}
                </button>

                <p style={{ textAlign: "center", fontSize: 13, color: "var(--cs-slate)", marginTop: 16 }}>
                  We'll send you a secure login link — no password needed.
                </p>
              </form>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── ONBOARDING VIEW ──
  if (view === "onboarding") {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 460, padding: "0 16px" }}>
            <div style={{ textAlign: "center", marginBottom: 32 }}>
              <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
                Set up your practice
              </h1>
              <p style={{ color: "var(--cs-slate)", marginTop: 8, fontSize: 14 }}>
                Tell us about your practice so we can tailor the analysis.
              </p>
            </div>

            <form onSubmit={handleOnboardingSubmit}>
              {/* Practice Name */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Practice name *</label>
                <input
                  type="text"
                  required
                  value={formData.practice_name}
                  onChange={(e) => setFormData(d => ({ ...d, practice_name: e.target.value }))}
                  placeholder="e.g. Sunshine Internal Medicine"
                  style={inputStyle}
                />
              </div>

              {/* Specialty */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Specialty</label>
                <select
                  value={formData.specialty}
                  onChange={(e) => setFormData(d => ({ ...d, specialty: e.target.value }))}
                  style={{ ...inputStyle, appearance: "auto" }}
                >
                  <option value="">Select a specialty</option>
                  {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {/* NPI */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>NPI number</label>
                <input
                  type="text"
                  value={formData.npi}
                  onChange={(e) => setFormData(d => ({ ...d, npi: e.target.value }))}
                  placeholder="Optional — 10-digit NPI"
                  maxLength={10}
                  style={inputStyle}
                />
              </div>

              {/* ZIP Code */}
              <div style={{ marginBottom: 24 }}>
                <label style={labelStyle}>Practice ZIP code</label>
                <input
                  type="text"
                  value={formData.zip_code}
                  onChange={(e) => setFormData(d => ({ ...d, zip_code: e.target.value }))}
                  placeholder="e.g. 33701"
                  maxLength={5}
                  style={inputStyle}
                />
              </div>

              {formError && (
                <div style={{
                  padding: 12, borderRadius: 8, background: "#fef2f2",
                  border: "1px solid #fecaca", marginBottom: 16,
                }}>
                  <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{formError}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={formSaving}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: formSaving ? 0.6 : 1,
                }}
              >
                {formSaving ? "Saving..." : "Continue to Dashboard"}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // ── DASHBOARD VIEW ──
  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
      {/* Dashboard nav with practice info */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--cs-navy)" }}>
              {profile?.practice_name}
            </div>
            {profile?.specialty && (
              <span style={{
                fontSize: 11, fontWeight: 500, color: "var(--cs-teal)",
                background: "var(--cs-teal-pale)", padding: "2px 8px",
                borderRadius: 4, display: "inline-block", marginTop: 2,
              }}>
                {profile.specialty}
              </span>
            )}
          </div>
          <button
            onClick={handleSignOut}
            style={{
              background: "none", border: "1px solid var(--cs-border)",
              borderRadius: 8, padding: "6px 14px", fontSize: 13,
              color: "var(--cs-slate)", cursor: "pointer",
            }}
          >
            Sign out
          </button>
        </div>
      </nav>

      <div style={{ paddingTop: 88, maxWidth: 960, margin: "0 auto", padding: "88px 24px 60px" }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
            Parity Provider
          </h1>
          <p style={{ color: "var(--cs-slate)", marginTop: 4, fontSize: 14 }}>
            Contract integrity and coding intelligence for your practice.
          </p>
        </div>

        {/* Tab buttons */}
        <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
          <button
            onClick={() => setActiveTab("contract")}
            style={{
              padding: "10px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600,
              cursor: "pointer", border: "1px solid",
              ...(activeTab === "contract"
                ? { background: "var(--cs-navy)", color: "#fff", borderColor: "var(--cs-navy)" }
                : { background: "#fff", color: "var(--cs-slate)", borderColor: "var(--cs-border)" }
              ),
            }}
          >
            Contract Integrity
          </button>
          <button
            onClick={() => setActiveTab("coding")}
            style={{
              padding: "10px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600,
              cursor: "pointer", border: "1px solid",
              ...(activeTab === "coding"
                ? { background: "var(--cs-navy)", color: "#fff", borderColor: "var(--cs-navy)" }
                : { background: "#fff", color: "var(--cs-slate)", borderColor: "var(--cs-border)" }
              ),
            }}
          >
            Coding Analysis
          </button>
        </div>

        {/* Tab content */}
        {activeTab === "contract" ? (
          <ContractIntegrityTab
            step={contractStep}
            error={contractError}
            parsedRates={parsedRates}
            savingRates={savingRates}
            parsedRemittance={parsedRemittance}
            analysisResult={analysisResult}
            sortField={sortField}
            sortDir={sortDir}
            onDownloadTemplate={handleDownloadTemplate}
            onRatesFileUpload={handleRatesFileUpload}
            onSaveRates={handleSaveRates}
            on835Upload={handle835Upload}
            onRunAnalysis={handleRunAnalysis}
            onSort={handleSort}
            getSortedLines={getSortedLines}
            onReset={resetContract}
          />
        ) : (
          <div style={{
            border: "1px solid var(--cs-border)", borderRadius: 12,
            padding: 40, textAlign: "center", background: "var(--cs-mist)",
          }}>
            <div style={{ marginBottom: 16 }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--cs-teal)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
              Coding Pattern Analysis
            </h3>
            <p style={{ color: "var(--cs-slate)", fontSize: 14, maxWidth: 480, margin: "0 auto 20px" }}>
              We'll analyze your coding patterns across claims to identify undercoding opportunities and compliance risks.
            </p>
            <div style={{
              display: "inline-block", padding: "6px 14px", borderRadius: 6,
              background: "var(--cs-teal-pale)", color: "var(--cs-teal)",
              fontSize: 13, fontWeight: 500,
            }}>
              Coming in next step
            </div>
          </div>
        )}
      </div>

      {/* Print styles */}
      <style>{`
        @media print {
          .cs-nav, button, .no-print { display: none !important; }
          body { font-size: 11px; color: #000; }
          div[style] { max-width: 100% !important; padding: 0 !important; }
        }
      `}</style>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Contract Integrity Tab Component
// ═══════════════════════════════════════════════════════════════════

function ContractIntegrityTab({
  step, error, parsedRates, savingRates, parsedRemittance, analysisResult,
  sortField, sortDir,
  onDownloadTemplate, onRatesFileUpload, onSaveRates, on835Upload,
  onRunAnalysis, onSort, getSortedLines, onReset,
}) {
  // ── Step: upload-rates ──
  if (step === "upload-rates") {
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 32, background: "#fff" }}>
        <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
          Step 1: Upload Your Contract Rates
        </h3>
        <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 24 }}>
          Download our template, fill in your contracted rates for each payer, then upload the completed file.
        </p>

        <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
          <button onClick={onDownloadTemplate} style={btnOutline}>
            <DownloadIcon /> Download Template
          </button>
        </div>

        <div style={{
          border: "2px dashed var(--cs-border)", borderRadius: 10,
          padding: 32, textAlign: "center", background: "var(--cs-mist)",
        }}>
          <UploadIcon />
          <p style={{ color: "var(--cs-slate)", fontSize: 14, marginTop: 12, marginBottom: 12 }}>
            Upload your completed contract rates spreadsheet (.xlsx)
          </p>
          <label style={{
            display: "inline-block", padding: "8px 20px", borderRadius: 8,
            background: "var(--cs-navy)", color: "#fff", fontSize: 14, fontWeight: 600,
            cursor: "pointer",
          }}>
            Choose File
            <input type="file" accept=".xlsx,.xls" onChange={onRatesFileUpload} style={{ display: "none" }} />
          </label>
        </div>

        {error && <ErrorBanner message={error} />}

        <div style={{ marginTop: 20, padding: 16, borderRadius: 8, background: "var(--cs-mist)", fontSize: 13, color: "var(--cs-slate)" }}>
          <strong style={{ color: "var(--cs-navy)" }}>Template format:</strong> Row 4 contains payer names (columns D onward).
          Rows 5+ contain CPT codes (column A), descriptions (column B), and contracted rates under each payer column.
        </div>
      </div>
    );
  }

  // ── Step: preview-rates ──
  if (step === "preview-rates") {
    const { payers, rows } = parsedRates || { payers: [], rows: [] };
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 32, background: "#fff" }}>
        <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
          Step 1: Review Contract Rates
        </h3>

        <div style={{
          padding: 12, borderRadius: 8, background: "var(--cs-teal-pale)",
          border: "1px solid var(--cs-teal)", marginBottom: 20, fontSize: 14,
        }}>
          Found <strong>{rows.length}</strong> CPT codes across <strong>{payers.length}</strong> payer{payers.length !== 1 ? "s" : ""}: {payers.join(", ")}
        </div>

        <div style={{ overflowX: "auto", marginBottom: 20 }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>CPT</th>
                <th style={thStyle}>Description</th>
                {payers.map(p => <th key={p} style={{ ...thStyle, textAlign: "right" }}>{p}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 20).map((row, i) => (
                <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                  <td style={tdStyle}><code>{row.cpt}</code></td>
                  <td style={{ ...tdStyle, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{row.description}</td>
                  {payers.map(p => (
                    <td key={p} style={{ ...tdStyle, textAlign: "right" }}>
                      {row.rates[p] ? `$${row.rates[p].toFixed(2)}` : <span style={{ color: "#ccc" }}>—</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length > 20 && (
            <p style={{ fontSize: 13, color: "var(--cs-slate)", marginTop: 8 }}>
              Showing 20 of {rows.length} rows
            </p>
          )}
        </div>

        {error && <ErrorBanner message={error} />}

        <div style={{ display: "flex", gap: 12 }}>
          <button onClick={onSaveRates} disabled={savingRates} style={{ ...btnPrimary, opacity: savingRates ? 0.6 : 1 }}>
            {savingRates ? "Saving..." : "Save Contract Rates"}
          </button>
          <button onClick={onReset} style={btnOutline}>Start Over</button>
        </div>
      </div>
    );
  }

  // ── Step: upload-835 ──
  if (step === "upload-835") {
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 32, background: "#fff" }}>
        <StepIndicator current={2} />
        <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
          Step 2: Upload 835 Remittance File
        </h3>
        <p style={{ color: "var(--cs-slate)", fontSize: 14, marginBottom: 24 }}>
          Upload an Electronic Remittance Advice (ERA/835) file from your clearinghouse or payer portal.
        </p>

        <div style={{
          border: "2px dashed var(--cs-border)", borderRadius: 10,
          padding: 32, textAlign: "center", background: "var(--cs-mist)",
        }}>
          <UploadIcon />
          <p style={{ color: "var(--cs-slate)", fontSize: 14, marginTop: 12, marginBottom: 12 }}>
            Accepted formats: .835, .txt, .edi
          </p>
          <label style={{
            display: "inline-block", padding: "8px 20px", borderRadius: 8,
            background: "var(--cs-navy)", color: "#fff", fontSize: 14, fontWeight: 600,
            cursor: "pointer",
          }}>
            Choose File
            <input type="file" accept=".835,.txt,.edi" onChange={on835Upload} style={{ display: "none" }} />
          </label>
        </div>

        {error && <ErrorBanner message={error} />}

        <div style={{ marginTop: 20, padding: 16, borderRadius: 8, background: "var(--cs-mist)", fontSize: 13, color: "var(--cs-slate)" }}>
          <strong style={{ color: "var(--cs-navy)" }}>Where to find 835 files:</strong> Your clearinghouse (e.g., Availity, Trizetto, Office Ally)
          typically provides ERA/835 files for download. Check your payer portal under "Remittance" or "Payment" sections.
        </div>

        <div style={{ marginTop: 16 }}>
          <button onClick={onReset} style={btnOutline}>Start Over</button>
        </div>
      </div>
    );
  }

  // ── Step: parsing-835 ──
  if (step === "parsing-835") {
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 48, textAlign: "center", background: "#fff" }}>
        <Spinner />
        <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 16, fontSize: 16 }}>
          Parsing remittance file...
        </p>
        <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
          Reading claims and payment data from the 835 file.
        </p>
      </div>
    );
  }

  // ── Step: preview-835 ──
  if (step === "preview-835" && parsedRemittance) {
    const items = parsedRemittance.line_items || [];
    const preview = items.slice(0, 10);
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 32, background: "#fff" }}>
        <StepIndicator current={2} />
        <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
          Step 2: Remittance Preview
        </h3>

        <div style={{
          padding: 12, borderRadius: 8, background: "var(--cs-teal-pale)",
          border: "1px solid var(--cs-teal)", marginBottom: 20, fontSize: 14,
        }}>
          Found <strong>{parsedRemittance.claim_count}</strong> claims,{" "}
          <strong>{items.length}</strong> line items,{" "}
          <strong>${(parsedRemittance.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong> total paid
          {parsedRemittance.payer_name && <> — from <strong>{parsedRemittance.payer_name}</strong></>}
          {parsedRemittance.production_date && <> ({parsedRemittance.production_date})</>}
        </div>

        <div style={{ overflowX: "auto", marginBottom: 20 }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>CPT</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Billed</th>
                <th style={{ ...thStyle, textAlign: "center" }}>Units</th>
                <th style={{ ...thStyle, textAlign: "right" }}>Paid</th>
                <th style={thStyle}>Adj Codes</th>
              </tr>
            </thead>
            <tbody>
              {preview.map((item, i) => (
                <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                  <td style={tdStyle}><code>{item.cpt_code}</code></td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>${(item.billed_amount || 0).toFixed(2)}</td>
                  <td style={{ ...tdStyle, textAlign: "center" }}>{item.units || 1}</td>
                  <td style={{ ...tdStyle, textAlign: "right" }}>${(item.paid_amount || 0).toFixed(2)}</td>
                  <td style={{ ...tdStyle, fontSize: 12, color: "var(--cs-slate)" }}>
                    {(item.adjustments || []).map(a => a.code).filter(Boolean).join(", ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {items.length > 10 && (
            <p style={{ fontSize: 13, color: "var(--cs-slate)", marginTop: 8 }}>
              Showing 10 of {items.length} line items
            </p>
          )}
        </div>

        {error && <ErrorBanner message={error} />}

        <div style={{ display: "flex", gap: 12 }}>
          <button onClick={onRunAnalysis} style={btnPrimary}>
            Looks Right — Run Analysis
          </button>
          <button onClick={onReset} style={btnOutline}>Start Over</button>
        </div>
      </div>
    );
  }

  // ── Step: analyzing ──
  if (step === "analyzing") {
    return (
      <div style={{ border: "1px solid var(--cs-border)", borderRadius: 12, padding: 48, textAlign: "center", background: "#fff" }}>
        <Spinner />
        <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginTop: 16, fontSize: 16 }}>
          Comparing remittance against your contracted rates...
        </p>
        <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
          Checking each line item for underpayments, denials, and rate discrepancies.
        </p>
      </div>
    );
  }

  // ── Step: report ──
  if (step === "report" && analysisResult) {
    const s = analysisResult.summary || {};
    const sortedLines = getSortedLines();
    const adherenceColor = s.adherence_rate >= 97 ? "#059669" : s.adherence_rate >= 90 ? "#d97706" : "#dc2626";

    return (
      <div>
        {/* Summary Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 24 }}>
          <SummaryCard label="Total Contracted" value={`$${(s.total_contracted || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
          <SummaryCard label="Total Paid" value={`$${(s.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} />
          <SummaryCard label="Underpayment" value={`$${(s.total_underpayment || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`} color={s.total_underpayment > 0 ? "#dc2626" : undefined} />
          <SummaryCard label="Adherence Rate" value={`${s.adherence_rate || 0}%`} color={adherenceColor} />
        </div>

        {/* Underpayment callout */}
        {s.total_underpayment > 0 && (
          <div style={{
            background: "var(--cs-navy)", borderRadius: 12, padding: 24,
            marginBottom: 24, color: "#fff",
          }}>
            <div style={{ fontSize: 14, opacity: 0.8, marginBottom: 4 }}>Total Potential Underpayment</div>
            <div style={{ fontSize: 32, fontWeight: 700 }}>
              ${s.total_underpayment.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: 13, marginTop: 8, opacity: 0.7 }}>
              {s.underpaid_count} underpaid line{s.underpaid_count !== 1 ? "s" : ""} + {s.denied_count} denied
              {" "}out of {s.line_count} total
            </div>
          </div>
        )}

        {/* Flag breakdown */}
        <div style={{
          display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap",
        }}>
          <FlagBadge label="Correct" count={s.correct_count} color="#059669" bg="#ecfdf5" />
          <FlagBadge label="Underpaid" count={s.underpaid_count} color="#dc2626" bg="#fef2f2" />
          <FlagBadge label="Denied" count={s.denied_count} color="#d97706" bg="#fffbeb" />
          <FlagBadge label="Overpaid" count={s.overpaid_count} color="#2563eb" bg="#eff6ff" />
          <FlagBadge label="No Contract" count={s.no_contract_count} color="#6b7280" bg="#f3f4f6" />
        </div>

        {/* Top Underpaid Codes */}
        {analysisResult.top_underpaid?.length > 0 && (
          <div style={{ marginBottom: 24 }}>
            <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
              Top Underpaid Codes
            </h4>
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>CPT Code</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Total Underpayment</th>
                  </tr>
                </thead>
                <tbody>
                  {analysisResult.top_underpaid.map((item, i) => (
                    <tr key={i} style={i % 2 === 0 ? {} : { background: "var(--cs-mist)" }}>
                      <td style={tdStyle}><code>{item.cpt_code}</code></td>
                      <td style={{ ...tdStyle, textAlign: "right", color: "#dc2626", fontWeight: 600 }}>
                        ${item.total_underpayment.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Full Line Items */}
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ fontSize: 15, fontWeight: 600, color: "var(--cs-navy)", marginBottom: 12 }}>
            All Line Items ({sortedLines.length})
          </h4>
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <SortTh field="cpt_code" label="CPT" current={sortField} dir={sortDir} onSort={onSort} />
                  <SortTh field="billed_amount" label="Billed" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="paid_amount" label="Paid" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="expected_payment" label="Expected" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="variance" label="Variance" current={sortField} dir={sortDir} onSort={onSort} align="right" />
                  <SortTh field="flag" label="Flag" current={sortField} dir={sortDir} onSort={onSort} />
                  <th style={{ ...thStyle, textAlign: "right" }}>Medicare</th>
                </tr>
              </thead>
              <tbody>
                {sortedLines.map((item, i) => {
                  const rowBg = flagRowColor(item.flag, i);
                  return (
                    <tr key={i} style={{ background: rowBg }}>
                      <td style={tdStyle}><code>{item.cpt_code}</code></td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.billed_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>${(item.paid_amount || 0).toFixed(2)}</td>
                      <td style={{ ...tdStyle, textAlign: "right" }}>
                        {item.expected_payment != null ? `$${item.expected_payment.toFixed(2)}` : "—"}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontWeight: 600, color: varianceColor(item.variance) }}>
                        {item.variance != null ? `${item.variance >= 0 ? "+" : ""}$${item.variance.toFixed(2)}` : "—"}
                      </td>
                      <td style={tdStyle}>
                        <FlagPill flag={item.flag} />
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontSize: 12, color: "var(--cs-slate)" }}>
                        {item.medicare_rate ? `$${item.medicare_rate.toFixed(2)}` : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Disclaimer */}
        <div style={{
          padding: 16, borderRadius: 8, background: "var(--cs-mist)",
          fontSize: 12, color: "var(--cs-slate)", marginBottom: 24,
          lineHeight: 1.6,
        }}>
          <strong>Disclaimer:</strong> This analysis compares payer remittance data against your self-reported contracted rates
          and publicly available CMS Medicare benchmarks. It is not legal or financial advice. Verify all findings with your
          payer contracts and consult a billing specialist before taking action.
        </div>

        {/* Action buttons */}
        <div className="no-print" style={{ display: "flex", gap: 12 }}>
          <button onClick={() => window.print()} style={btnPrimary}>
            Download Report
          </button>
          <button onClick={onReset} style={btnOutline}>
            Start Over
          </button>
        </div>
      </div>
    );
  }

  // Fallback
  return null;
}


// ═══════════════════════════════════════════════════════════════════
// Small reusable components
// ═══════════════════════════════════════════════════════════════════

function StepIndicator({ current }) {
  const steps = ["Contract Rates", "Remittance", "Analysis"];
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
      {steps.map((label, i) => {
        const num = i + 1;
        const active = num <= current;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{
              width: 24, height: 24, borderRadius: "50%", fontSize: 12, fontWeight: 700,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: active ? "var(--cs-navy)" : "var(--cs-border)",
              color: active ? "#fff" : "var(--cs-slate)",
            }}>
              {num}
            </div>
            <span style={{ fontSize: 13, color: active ? "var(--cs-navy)" : "var(--cs-slate)", fontWeight: active ? 600 : 400 }}>
              {label}
            </span>
            {i < steps.length - 1 && <div style={{ width: 20, height: 1, background: "var(--cs-border)" }} />}
          </div>
        );
      })}
    </div>
  );
}

function SummaryCard({ label, value, color }) {
  return (
    <div style={{
      border: "1px solid var(--cs-border)", borderRadius: 10,
      padding: 20, background: "#fff",
    }}>
      <div style={{ fontSize: 13, color: "var(--cs-slate)", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || "var(--cs-navy)" }}>{value}</div>
    </div>
  );
}

function FlagBadge({ label, count, color, bg }) {
  return (
    <div style={{
      padding: "6px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600,
      background: bg, color, display: "inline-flex", gap: 6, alignItems: "center",
    }}>
      <span>{count}</span>
      <span style={{ fontWeight: 400 }}>{label}</span>
    </div>
  );
}

function FlagPill({ flag }) {
  const colors = {
    UNDERPAID: { bg: "#fef2f2", color: "#dc2626" },
    DENIED: { bg: "#fffbeb", color: "#d97706" },
    CORRECT: { bg: "#ecfdf5", color: "#059669" },
    OVERPAID: { bg: "#eff6ff", color: "#2563eb" },
    NO_CONTRACT: { bg: "#f3f4f6", color: "#6b7280" },
  };
  const c = colors[flag] || colors.NO_CONTRACT;
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
      background: c.bg, color: c.color,
    }}>
      {flag}
    </span>
  );
}

function SortTh({ field, label, current, dir, onSort, align = "left" }) {
  const active = current === field;
  return (
    <th
      onClick={() => onSort(field)}
      style={{
        ...thStyle,
        textAlign: align,
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      {label} {active ? (dir === "asc" ? "\u25B2" : "\u25BC") : ""}
    </th>
  );
}

function ErrorBanner({ message }) {
  return (
    <div style={{
      padding: 12, borderRadius: 8, background: "#fef2f2",
      border: "1px solid #fecaca", marginTop: 16,
    }}>
      <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{message}</p>
    </div>
  );
}

function Spinner() {
  return (
    <div style={{
      width: 40, height: 40, border: "3px solid var(--cs-border)",
      borderTopColor: "var(--cs-teal)", borderRadius: "50%",
      margin: "0 auto", animation: "spin 0.8s linear infinite",
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--cs-teal)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6, verticalAlign: "middle" }}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" y1="15" x2="12" y2="3"/>
    </svg>
  );
}


// ═══════════════════════════════════════════════════════════════════
// Style helpers
// ═══════════════════════════════════════════════════════════════════

function flagRowColor(flag, index) {
  const even = index % 2 === 0;
  switch (flag) {
    case "UNDERPAID": return even ? "#fef2f2" : "#fee2e2";
    case "DENIED": return even ? "#fffbeb" : "#fef3c7";
    case "CORRECT": return even ? "#ecfdf5" : "#d1fae5";
    case "OVERPAID": return even ? "#eff6ff" : "#dbeafe";
    case "NO_CONTRACT": return even ? "#f9fafb" : "#f3f4f6";
    default: return even ? "#fff" : "var(--cs-mist)";
  }
}

function varianceColor(v) {
  if (v == null) return "var(--cs-slate)";
  if (v < -0.5) return "#dc2626";
  if (v > 0.5) return "#2563eb";
  return "#059669";
}

const tableStyle = {
  width: "100%", borderCollapse: "collapse", fontSize: 13,
};

const thStyle = {
  padding: "8px 10px", textAlign: "left", fontSize: 12, fontWeight: 600,
  color: "var(--cs-slate)", borderBottom: "2px solid var(--cs-border)",
  whiteSpace: "nowrap",
};

const tdStyle = {
  padding: "7px 10px", borderBottom: "1px solid var(--cs-border)",
};

const btnPrimary = {
  padding: "10px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600,
  cursor: "pointer", border: "none",
  background: "var(--cs-navy)", color: "#fff",
};

const btnOutline = {
  padding: "10px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600,
  cursor: "pointer", border: "1px solid var(--cs-border)",
  background: "#fff", color: "var(--cs-slate)",
};

// ── Shared styles ──
const labelStyle = {
  display: "block", fontSize: 14, fontWeight: 500,
  color: "var(--cs-navy)", marginBottom: 6,
};

const inputStyle = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1px solid var(--cs-border)", fontSize: 15,
  outline: "none", boxSizing: "border-box",
};
