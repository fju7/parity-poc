import { useState, useCallback } from "react";
import { Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TEAL = "#0D9488";
const NAVY = "#1E293B";
const SLATE = "#64748B";

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

const PAYER_OPTIONS = [
  "Aetna",
  "BCBS",
  "Cigna",
  "Humana",
  "UnitedHealthcare",
  "Medicare",
  "Medicaid",
  "Other",
];

const FEE_METHODS = [
  { key: "excel", title: "Excel/CSV Upload", desc: "Upload a spreadsheet with CPT codes and rates" },
  { key: "pdf", title: "PDF Contract", desc: "AI extracts rates from your payer contract PDF" },
  { key: "medicare-pct", title: "% of Medicare", desc: "Enter payer's percentage of Medicare PFS rates" },
  { key: "paste", title: "Paste Text", desc: "Copy and paste rate table from email or portal" },
  { key: "photo", title: "Photo/Screenshot", desc: "Upload an image of your fee schedule" },
];

const btnPrimary = {
  padding: "12px 28px", borderRadius: 8, border: "none",
  background: TEAL, color: "#fff", fontSize: 15, fontWeight: 600,
  cursor: "pointer",
};

const btnOutline = {
  padding: "12px 28px", borderRadius: 8,
  border: `1px solid ${NAVY}`, background: "none",
  color: NAVY, fontSize: 15, fontWeight: 600, cursor: "pointer",
};

const inputStyle = {
  width: "100%", padding: "10px 14px", borderRadius: 8,
  border: "1px solid #CBD5E1", fontSize: 14, color: NAVY,
  boxSizing: "border-box",
};

const labelStyle = {
  display: "block", fontSize: 13, fontWeight: 600,
  color: NAVY, marginBottom: 6,
};

// ---------------------------------------------------------------------------
// Mini components (self-contained — no dependency on ProviderApp internals)
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <div style={{
      width: 40, height: 40, border: "3px solid #E2E8F0",
      borderTopColor: TEAL, borderRadius: "50%",
      margin: "0 auto", animation: "spin 0.8s linear infinite",
    }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function DropZone({ accept, onChange, children, multiple = false }) {
  const [dragging, setDragging] = useState(false);

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setDragging(true); }}
      onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setDragging(false); }}
      onDrop={(e) => {
        e.preventDefault(); e.stopPropagation(); setDragging(false);
        const dropped = e.dataTransfer?.files;
        if (dropped?.length) onChange({ target: { files: multiple ? dropped : [dropped[0]] } });
      }}
      style={{
        border: dragging ? `2px solid ${TEAL}` : "2px dashed #CBD5E1",
        borderRadius: 10, padding: 32, textAlign: "center",
        background: dragging ? "#F0FDFA" : "#F8FAFC",
        transition: "border-color 0.15s, background 0.15s",
      }}
    >
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke={TEAL} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="17 8 12 3 7 8"/>
        <line x1="12" y1="3" x2="12" y2="15"/>
      </svg>
      <p style={{ color: SLATE, fontSize: 14, marginTop: 12, marginBottom: 12 }}>{children}</p>
      <label style={{
        display: "inline-block", padding: "8px 20px", borderRadius: 8,
        background: NAVY, color: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer",
      }}>
        {multiple ? "Choose Files" : "Choose File"}
        <input type="file" accept={accept} multiple={multiple} onChange={onChange} style={{ display: "none" }} />
      </label>
    </div>
  );
}

function StepIndicator({ current, total }) {
  return (
    <div style={{ display: "flex", gap: 6, justifyContent: "center", marginBottom: 32 }}>
      {Array.from({ length: total }, (_, i) => (
        <div key={i} style={{
          width: i === current ? 32 : 12, height: 6, borderRadius: 3,
          background: i <= current ? TEAL : "#CBD5E1",
          transition: "all 0.2s",
        }} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ProviderAuditPage({ session, profile }) {
  const [started, setStarted] = useState(false);
  const [step, setStep] = useState(0);

  // Step 1: Practice profile
  const [practiceData, setPracticeData] = useState({
    practice_name: profile?.practice_name || "",
    specialty: profile?.specialty || "",
    num_providers: 1,
    billing_company: "",
    contact_email: session?.user?.email || "",
    contact_phone: "",
  });

  // Step 2: Payers
  const [payers, setPayers] = useState([]); // [{payer_name, method, rates[], codeCount}]
  const [editingPayer, setEditingPayer] = useState(null); // {payer_name, method, ...}
  const [feeMethod, setFeeMethod] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [extractedRates, setExtractedRates] = useState(null);
  const [payerError, setPayerError] = useState("");

  // Step 3: 835 files
  const [remittanceResults, setRemittanceResults] = useState([]);
  const [uploading835, setUploading835] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [filePayerMap, setFilePayerMap] = useState({});

  // Step 4/5: Submit
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [auditId, setAuditId] = useState(null);
  const [submitError, setSubmitError] = useState("");

  // --------------- Step 2 handlers ---------------

  function startAddPayer() {
    setEditingPayer({ payer_name: "" });
    setFeeMethod(null);
    setExtractedRates(null);
    setPayerError("");
  }

  async function handleFeeScheduleExtract(method, data) {
    setExtracting(true);
    setPayerError("");

    try {
      let result;

      if (method === "excel" || method === "pdf" || method === "photo") {
        const endpoint =
          method === "excel" ? "extract-fee-schedule-pdf" :
          method === "pdf" ? "extract-fee-schedule-pdf" :
          "extract-fee-schedule-image";

        // For excel, we'll parse locally via the same approach
        // Actually, excel files are handled differently — read with xlsx
        if (method === "excel") {
          const file = data;
          const XLSX = (await import("xlsx")).default;
          const buf = await file.arrayBuffer();
          const wb = XLSX.read(buf, { type: "array" });
          const ws = wb.Sheets[wb.SheetNames[0]];
          const json = XLSX.utils.sheet_to_json(ws, { header: 1 });

          // Simple parse: look for CPT codes and rates
          const rates = [];
          for (const row of json) {
            if (!row || row.length < 2) continue;
            const cpt = String(row[0] || "").trim();
            if (/^\d{5}$/.test(cpt)) {
              const rate = parseFloat(row[row.length - 1]) || parseFloat(row[1]) || 0;
              if (rate > 0) {
                rates.push({ cpt, rate, description: String(row[1] || "") });
              }
            }
          }
          result = { rates, payer_name: editingPayer.payer_name };
        } else {
          const formData = new FormData();
          formData.append("file", data);
          const res = await fetch(`${API_BASE}/api/provider/${endpoint}`, { method: "POST", body: formData });
          if (!res.ok) throw new Error("Extraction failed");
          result = await res.json();
        }
      } else if (method === "paste") {
        const res = await fetch(`${API_BASE}/api/provider/extract-fee-schedule-text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: data }),
        });
        if (!res.ok) throw new Error("Extraction failed");
        result = await res.json();
      } else if (method === "medicare-pct") {
        const { percentage, zipCode } = data;
        const res = await fetch(`${API_BASE}/api/provider/calculate-medicare-percentage`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            payer_name: editingPayer.payer_name,
            percentage,
            zip_code: zipCode,
          }),
        });
        if (!res.ok) throw new Error("Calculation failed");
        result = await res.json();
      }

      if (result?.rates?.length > 0) {
        setExtractedRates(result.rates);
      } else {
        setPayerError("No rates found. Please try a different method or file.");
      }
    } catch (err) {
      console.error("Fee schedule extraction error:", err);
      setPayerError(err.message || "Failed to extract rates. Please try again.");
    } finally {
      setExtracting(false);
    }
  }

  function confirmPayer() {
    if (!editingPayer?.payer_name) return;
    const ratesMap = {};
    (extractedRates || []).forEach(r => { ratesMap[r.cpt] = r.rate; });

    setPayers(prev => [
      ...prev,
      {
        payer_name: editingPayer.payer_name,
        method: feeMethod,
        rates: ratesMap,
        codeCount: Object.keys(ratesMap).length,
      },
    ]);
    setEditingPayer(null);
    setFeeMethod(null);
    setExtractedRates(null);
  }

  function removePayer(idx) {
    setPayers(prev => prev.filter((_, i) => i !== idx));
  }

  // --------------- Step 3 handlers ---------------

  const handle835Upload = useCallback(async (e) => {
    const fileList = e.target.files;
    if (!fileList?.length) return;
    setUploading835(true);
    setUploadError("");

    try {
      const formData = new FormData();
      for (let i = 0; i < fileList.length; i++) {
        formData.append("files", fileList[i]);
      }

      const res = await fetch(`${API_BASE}/api/provider/parse-835-batch`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Failed to parse 835 files");
      const data = await res.json();
      setRemittanceResults(data.results || []);

      // Auto-assign payers based on detected payer name
      const newMap = {};
      for (const r of (data.results || [])) {
        if (r.payer_name) {
          // Try to match to saved payer
          const match = payers.find(
            p => p.payer_name.toLowerCase() === r.payer_name.toLowerCase()
          );
          if (match) {
            newMap[r.filename] = match.payer_name;
          }
        }
      }
      setFilePayerMap(prev => ({ ...prev, ...newMap }));

      if (data.errors?.length) {
        setUploadError(`${data.errors.length} file(s) failed to parse`);
      }
    } catch (err) {
      console.error("835 upload error:", err);
      setUploadError(err.message || "Upload failed");
    } finally {
      setUploading835(false);
    }
  }, [payers]);

  // --------------- Step 4: Submit ---------------

  async function handleSubmit() {
    if (!consent) {
      setSubmitError("Please accept the consent agreement.");
      return;
    }
    setSubmitting(true);
    setSubmitError("");

    try {
      const payload = {
        practice_name: practiceData.practice_name,
        specialty: practiceData.specialty,
        num_providers: practiceData.num_providers,
        billing_company: practiceData.billing_company,
        contact_email: practiceData.contact_email,
        contact_phone: practiceData.contact_phone,
        payer_list: payers.map(p => ({
          payer_name: p.payer_name,
          fee_schedule_method: p.method,
          code_count: p.codeCount,
          fee_schedule_data: p.rates, // {cpt: rate} — persist for admin analysis
        })),
        remittance_data: remittanceResults.map(r => ({
          filename: r.filename || "",
          payer_name: filePayerMap[r.filename] || r.payer_name || "",
          claims: (r.claims || []).map(c => ({
            claim_id: c.claim_id || "",
            lines: (c.line_items || c.lines || []).map(l => ({
              cpt_code: l.cpt_code || l.procedure_code || "",
              billed_amount: l.billed_amount || l.charge_amount || 0,
              paid_amount: l.paid_amount || 0,
              units: l.units || 1,
              adjustments: l.adjustments || l.adjustment_codes || "",
            })),
          })),
        })),
        consent: true,
        user_id: session?.user?.id || null,
      };

      const res = await fetch(`${API_BASE}/api/provider/submit-audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Submission failed");
      }

      const data = await res.json();
      setAuditId(data.audit_id);
      setSubmitted(true);
      setStep(4); // confirmation
    } catch (err) {
      console.error("Submit error:", err);
      setSubmitError(err.message || "Failed to submit audit");
    } finally {
      setSubmitting(false);
    }
  }

  // --------------- Validation ---------------

  function canProceed(s) {
    if (s === 0) return practiceData.practice_name.trim() && practiceData.contact_email.includes("@");
    if (s === 1) return payers.length > 0;
    if (s === 2) return true; // 835 optional
    if (s === 3) return consent;
    return true;
  }

  // ================================
  // LANDING PAGE (before wizard)
  // ================================
  if (!started) {
    return (
      <div style={{ fontFamily: "'DM Sans', Arial, sans-serif", color: NAVY }}>
        {/* Hero */}
        <div style={{
          background: `linear-gradient(135deg, ${NAVY} 0%, #0F172A 100%)`,
          padding: "80px 24px", textAlign: "center", color: "#fff",
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#5EEAD4", letterSpacing: 2, textTransform: "uppercase", marginBottom: 16 }}>
            Parity Audit
          </div>
          <h1 style={{ fontSize: 40, fontWeight: 700, margin: "0 0 16px", lineHeight: 1.2 }}>
            Find out what your payers owe you.
          </h1>
          <p style={{ fontSize: 18, color: "#94A3B8", maxWidth: 600, margin: "0 auto 32px" }}>
            Free. No commitment. No integration required.
          </p>
          <button
            onClick={() => setStarted(true)}
            style={{
              ...btnPrimary, fontSize: 18, padding: "16px 40px",
              background: TEAL, boxShadow: "0 4px 14px rgba(13,148,136,0.4)",
            }}
          >
            Start Your Free Audit &rarr;
          </button>
        </div>

        {/* Value props */}
        <div style={{ maxWidth: 960, margin: "0 auto", padding: "64px 24px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 32 }}>
            {[
              {
                icon: "\u2713",
                title: "Check Payments",
                desc: "Compare every payment against your contracted rates to identify underpayments.",
              },
              {
                icon: "\u2717",
                title: "Identify Denials",
                desc: "AI-powered denial analysis with appeal worthiness scoring and letter templates.",
              },
              {
                icon: "$",
                title: "Estimate Revenue Gap",
                desc: "See exactly how much money is on the table — by payer, by CPT code.",
              },
              {
                icon: "\u23F1",
                title: "Instant Results",
                desc: "Submit your data today. Receive a comprehensive audit report within a week.",
              },
            ].map((vp, i) => (
              <div key={i} style={{ textAlign: "center", padding: "24px 16px" }}>
                <div style={{
                  width: 56, height: 56, borderRadius: "50%",
                  background: "#F0FDFA", color: TEAL,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 24, fontWeight: 700, margin: "0 auto 16px",
                  border: `2px solid ${TEAL}`,
                }}>
                  {vp.icon}
                </div>
                <h3 style={{ fontSize: 17, fontWeight: 600, margin: "0 0 8px" }}>{vp.title}</h3>
                <p style={{ fontSize: 14, color: SLATE, lineHeight: 1.6, margin: 0 }}>{vp.desc}</p>
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center", marginTop: 48 }}>
            <button onClick={() => setStarted(true)} style={btnPrimary}>
              Start Your Free Audit &rarr;
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={{
          textAlign: "center", padding: "24px", borderTop: "1px solid #E2E8F0",
          fontSize: 12, color: SLATE,
        }}>
          Parity Audit by CivicScale. Benchmark comparisons use publicly available CMS Medicare data. Not legal advice. &copy; CivicScale 2026.
        </div>
      </div>
    );
  }

  // ================================
  // WIZARD
  // ================================
  return (
    <div style={{
      fontFamily: "'DM Sans', Arial, sans-serif", color: NAVY,
      maxWidth: 720, margin: "0 auto", padding: "40px 24px",
    }}>
      <div style={{ textAlign: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: TEAL, letterSpacing: 1, textTransform: "uppercase" }}>
          Parity Audit
        </span>
      </div>

      <StepIndicator current={step} total={5} />

      {/* ========== STEP 1: Practice Profile ========== */}
      {step === 0 && (
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: NAVY, margin: "0 0 8px" }}>
            Practice Profile
          </h2>
          <p style={{ fontSize: 14, color: SLATE, marginBottom: 24 }}>
            Tell us about your practice so we can tailor the audit.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label style={labelStyle}>Practice Name *</label>
              <input
                value={practiceData.practice_name}
                onChange={e => setPracticeData(d => ({ ...d, practice_name: e.target.value }))}
                style={inputStyle}
                placeholder="e.g., Sunshine Medical Group"
              />
            </div>

            <div>
              <label style={labelStyle}>Specialty</label>
              <select
                value={practiceData.specialty}
                onChange={e => setPracticeData(d => ({ ...d, specialty: e.target.value }))}
                style={inputStyle}
              >
                <option value="">Select specialty...</option>
                {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div>
                <label style={labelStyle}>Number of Providers</label>
                <input
                  type="number" min="1" max="100"
                  value={practiceData.num_providers}
                  onChange={e => setPracticeData(d => ({ ...d, num_providers: parseInt(e.target.value) || 1 }))}
                  style={inputStyle}
                />
              </div>
              <div>
                <label style={labelStyle}>Billing Company (optional)</label>
                <input
                  value={practiceData.billing_company}
                  onChange={e => setPracticeData(d => ({ ...d, billing_company: e.target.value }))}
                  style={inputStyle}
                  placeholder="e.g., ABC Billing"
                />
              </div>
            </div>

            <div>
              <label style={labelStyle}>Contact Email *</label>
              <input
                type="email"
                value={practiceData.contact_email}
                onChange={e => setPracticeData(d => ({ ...d, contact_email: e.target.value }))}
                style={inputStyle}
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label style={labelStyle}>Contact Phone (optional)</label>
              <input
                type="tel"
                value={practiceData.contact_phone}
                onChange={e => setPracticeData(d => ({ ...d, contact_phone: e.target.value }))}
                style={inputStyle}
                placeholder="(555) 123-4567"
              />
            </div>
          </div>
        </div>
      )}

      {/* ========== STEP 2: Add Payers ========== */}
      {step === 1 && (
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: NAVY, margin: "0 0 8px" }}>
            Payer Fee Schedules
          </h2>
          <p style={{ fontSize: 14, color: SLATE, marginBottom: 24 }}>
            Add each payer and their contracted rates. We support 5 ways to enter fee schedules.
          </p>

          {/* Saved payers */}
          {payers.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              {payers.map((p, i) => (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "12px 16px", borderRadius: 8, marginBottom: 8,
                  background: "#F0FDFA", border: `1px solid ${TEAL}`,
                }}>
                  <span style={{ fontSize: 14 }}>
                    <strong>{p.payer_name}</strong> — {p.codeCount} CPT codes ({p.method})
                  </span>
                  <button onClick={() => removePayer(i)} style={{
                    background: "none", border: "none", cursor: "pointer",
                    fontSize: 18, color: SLATE, padding: "0 4px",
                  }}>&times;</button>
                </div>
              ))}
            </div>
          )}

          {/* Adding a payer */}
          {editingPayer ? (
            <div style={{ border: "1px solid #CBD5E1", borderRadius: 12, padding: 24, background: "#fff" }}>
              {!feeMethod ? (
                <>
                  <div style={{ marginBottom: 20 }}>
                    <label style={labelStyle}>Payer Name *</label>
                    <select
                      value={editingPayer.payer_name}
                      onChange={e => setEditingPayer(p => ({ ...p, payer_name: e.target.value }))}
                      style={inputStyle}
                    >
                      <option value="">Select payer...</option>
                      {PAYER_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                    {editingPayer.payer_name === "Other" && (
                      <input
                        value={editingPayer.custom_name || ""}
                        onChange={e => setEditingPayer(p => ({ ...p, payer_name: e.target.value }))}
                        style={{ ...inputStyle, marginTop: 8 }}
                        placeholder="Enter payer name"
                      />
                    )}
                  </div>

                  {editingPayer.payer_name && (
                    <>
                      <label style={labelStyle}>Fee Schedule Method</label>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                        {FEE_METHODS.map(m => (
                          <button
                            key={m.key}
                            onClick={() => setFeeMethod(m.key)}
                            style={{
                              display: "flex", alignItems: "center", padding: "12px 16px",
                              border: "1px solid #CBD5E1", borderRadius: 8,
                              background: "#fff", cursor: "pointer", textAlign: "left",
                              transition: "border-color 0.15s",
                            }}
                            onMouseEnter={e => e.currentTarget.style.borderColor = TEAL}
                            onMouseLeave={e => e.currentTarget.style.borderColor = "#CBD5E1"}
                          >
                            <div>
                              <div style={{ fontWeight: 600, color: NAVY, fontSize: 14 }}>{m.title}</div>
                              <div style={{ fontSize: 12, color: SLATE, marginTop: 2 }}>{m.desc}</div>
                            </div>
                          </button>
                        ))}
                      </div>
                    </>
                  )}

                  <div style={{ marginTop: 16 }}>
                    <button onClick={() => setEditingPayer(null)} style={{ ...btnOutline, fontSize: 13, padding: "8px 16px" }}>
                      Cancel
                    </button>
                  </div>
                </>
              ) : extracting ? (
                <div style={{ textAlign: "center", padding: 32 }}>
                  <Spinner />
                  <p style={{ color: NAVY, fontWeight: 600, marginTop: 16, fontSize: 15 }}>
                    Extracting rates for {editingPayer.payer_name}...
                  </p>
                </div>
              ) : extractedRates ? (
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: NAVY, margin: "0 0 12px" }}>
                    {editingPayer.payer_name} — {extractedRates.length} CPT codes found
                  </h3>
                  <div style={{ overflowX: "auto", maxHeight: 300, marginBottom: 16 }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                      <thead>
                        <tr>
                          <th style={{ padding: "8px 12px", textAlign: "left", background: NAVY, color: "#fff", fontSize: 12, position: "sticky", top: 0 }}>CPT</th>
                          <th style={{ padding: "8px 12px", textAlign: "right", background: NAVY, color: "#fff", fontSize: 12, position: "sticky", top: 0 }}>Rate</th>
                          <th style={{ padding: "8px 12px", textAlign: "left", background: NAVY, color: "#fff", fontSize: 12, position: "sticky", top: 0 }}>Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        {extractedRates.slice(0, 20).map((r, i) => (
                          <tr key={i} style={{ background: i % 2 === 0 ? "#fff" : "#F8FAFC" }}>
                            <td style={{ padding: "6px 12px", borderBottom: "1px solid #E2E8F0" }}>{r.cpt}</td>
                            <td style={{ padding: "6px 12px", borderBottom: "1px solid #E2E8F0", textAlign: "right" }}>${(r.rate || 0).toFixed(2)}</td>
                            <td style={{ padding: "6px 12px", borderBottom: "1px solid #E2E8F0", color: SLATE }}>{r.description || ""}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {extractedRates.length > 20 && (
                      <p style={{ fontSize: 12, color: SLATE, marginTop: 4 }}>
                        Showing 20 of {extractedRates.length} codes
                      </p>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 12 }}>
                    <button onClick={confirmPayer} style={btnPrimary}>Confirm &amp; Save Payer</button>
                    <button onClick={() => { setExtractedRates(null); setFeeMethod(null); }} style={btnOutline}>Try Different Method</button>
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
                    <button onClick={() => setFeeMethod(null)} style={{ ...btnOutline, padding: "6px 14px", fontSize: 13 }}>&larr; Back</button>
                    <span style={{ fontWeight: 600, color: NAVY, fontSize: 15 }}>
                      {editingPayer.payer_name} — {FEE_METHODS.find(m => m.key === feeMethod)?.title}
                    </span>
                  </div>

                  {payerError && (
                    <div style={{ padding: 12, borderRadius: 8, background: "#FEF2F2", border: "1px solid #FECACA", marginBottom: 16, fontSize: 14, color: "#DC2626" }}>
                      {payerError}
                    </div>
                  )}

                  <FeeMethodInput
                    method={feeMethod}
                    zipCode={profile?.zip_code || ""}
                    onExtract={(data) => handleFeeScheduleExtract(feeMethod, data)}
                  />
                </div>
              )}
            </div>
          ) : payers.length < 5 ? (
            <button onClick={startAddPayer} style={{ ...btnOutline, width: "100%" }}>
              + Add a Payer
            </button>
          ) : (
            <p style={{ fontSize: 13, color: SLATE, textAlign: "center" }}>Maximum 5 payers reached</p>
          )}
        </div>
      )}

      {/* ========== STEP 3: Upload 835 Files ========== */}
      {step === 2 && (
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: NAVY, margin: "0 0 8px" }}>
            Upload 835 Remittance Files
          </h2>
          <p style={{ fontSize: 14, color: SLATE, marginBottom: 24 }}>
            Upload your 835 Electronic Remittance Advice files. You can upload multiple files or a zip archive.
          </p>

          {uploading835 ? (
            <div style={{ textAlign: "center", padding: 32 }}>
              <Spinner />
              <p style={{ color: NAVY, fontWeight: 600, marginTop: 16, fontSize: 15 }}>Parsing remittance files...</p>
            </div>
          ) : (
            <DropZone accept=".txt,.835,.edi,.zip,text/plain,application/zip" onChange={handle835Upload} multiple>
              Drag 835 files here, or click to browse. Accepts .835, .edi, .txt, and .zip files.
            </DropZone>
          )}

          {uploadError && (
            <div style={{ padding: 12, borderRadius: 8, background: "#FEF2F2", border: "1px solid #FECACA", marginTop: 16, fontSize: 14, color: "#DC2626" }}>
              {uploadError}
            </div>
          )}

          {/* Parsed results */}
          {remittanceResults.length > 0 && (
            <div style={{ marginTop: 24 }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: NAVY, marginBottom: 12 }}>
                {remittanceResults.length} file{remittanceResults.length !== 1 ? "s" : ""} parsed
              </h3>
              {remittanceResults.map((r, i) => (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "12px 16px", borderRadius: 8, marginBottom: 8,
                  border: "1px solid #CBD5E1", background: "#fff",
                }}>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 500 }}>{r.filename || `File ${i + 1}`}</div>
                    <div style={{ fontSize: 12, color: SLATE }}>
                      {r.claims?.length || 0} claims &middot; {r.payer_name || "Unknown payer"}
                    </div>
                  </div>
                  <select
                    value={filePayerMap[r.filename] || ""}
                    onChange={e => setFilePayerMap(prev => ({ ...prev, [r.filename]: e.target.value }))}
                    style={{ ...inputStyle, width: 180 }}
                  >
                    <option value="">Assign payer...</option>
                    {payers.map((p, pi) => (
                      <option key={pi} value={p.payer_name}>{p.payer_name}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          )}

          <p style={{ fontSize: 13, color: SLATE, marginTop: 16, fontStyle: "italic" }}>
            Don&rsquo;t have 835 files yet? You can skip this step and submit your fee schedules for a contract-only audit.
          </p>
        </div>
      )}

      {/* ========== STEP 4: Review & Submit ========== */}
      {step === 3 && (
        <div>
          <h2 style={{ fontSize: 22, fontWeight: 700, color: NAVY, margin: "0 0 8px" }}>
            Review &amp; Submit
          </h2>
          <p style={{ fontSize: 14, color: SLATE, marginBottom: 24 }}>
            Please review your audit details before submitting.
          </p>

          {/* Summary */}
          <div style={{ border: "1px solid #CBD5E1", borderRadius: 12, padding: 24, marginBottom: 24, background: "#fff" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontSize: 14 }}>
              <div>
                <span style={{ color: SLATE }}>Practice:</span>{" "}
                <strong>{practiceData.practice_name}</strong>
              </div>
              <div>
                <span style={{ color: SLATE }}>Specialty:</span>{" "}
                <strong>{practiceData.specialty || "Not specified"}</strong>
              </div>
              <div>
                <span style={{ color: SLATE }}>Providers:</span>{" "}
                <strong>{practiceData.num_providers}</strong>
              </div>
              <div>
                <span style={{ color: SLATE }}>Billing Co:</span>{" "}
                <strong>{practiceData.billing_company || "Not specified"}</strong>
              </div>
              <div>
                <span style={{ color: SLATE }}>Email:</span>{" "}
                <strong>{practiceData.contact_email}</strong>
              </div>
              {practiceData.contact_phone && (
                <div>
                  <span style={{ color: SLATE }}>Phone:</span>{" "}
                  <strong>{practiceData.contact_phone}</strong>
                </div>
              )}
            </div>

            <div style={{ borderTop: "1px solid #E2E8F0", marginTop: 16, paddingTop: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 8 }}>
                Payers ({payers.length})
              </div>
              {payers.map((p, i) => (
                <div key={i} style={{ fontSize: 14, color: NAVY, marginBottom: 4 }}>
                  {p.payer_name} — {p.codeCount} CPT codes
                </div>
              ))}
            </div>

            {remittanceResults.length > 0 && (
              <div style={{ borderTop: "1px solid #E2E8F0", marginTop: 16, paddingTop: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 8 }}>
                  Remittance Files ({remittanceResults.length})
                </div>
                {remittanceResults.map((r, i) => (
                  <div key={i} style={{ fontSize: 14, color: NAVY, marginBottom: 4 }}>
                    {r.filename} — {r.claims?.length || 0} claims
                    {filePayerMap[r.filename] ? ` (${filePayerMap[r.filename]})` : ""}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Consent */}
          <div style={{
            border: "1px solid #CBD5E1", borderRadius: 12, padding: 24,
            marginBottom: 24, background: "#F8FAFC",
          }}>
            <label style={{ display: "flex", gap: 12, cursor: "pointer", alignItems: "flex-start" }}>
              <input
                type="checkbox"
                checked={consent}
                onChange={e => setConsent(e.target.checked)}
                style={{ marginTop: 3, width: 18, height: 18, accentColor: TEAL }}
              />
              <span style={{ fontSize: 13, color: NAVY, lineHeight: 1.6 }}>
                I authorize CivicScale to analyze the submitted data for the purpose of generating a payer
                contract audit report. I understand that submitted data will be processed securely and
                used only for this audit. No protected health information (PHI) is collected or stored.
                This analysis is not legal or financial advice. I have the authority to submit this data
                on behalf of the practice named above.
              </span>
            </label>
          </div>

          {submitError && (
            <div style={{ padding: 12, borderRadius: 8, background: "#FEF2F2", border: "1px solid #FECACA", marginBottom: 16, fontSize: 14, color: "#DC2626" }}>
              {submitError}
            </div>
          )}
        </div>
      )}

      {/* ========== STEP 5: Confirmation ========== */}
      {step === 4 && (
        <div style={{ textAlign: "center", padding: "32px 0" }}>
          <div style={{
            width: 72, height: 72, borderRadius: "50%",
            background: "#F0FDFA", color: TEAL,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 36, margin: "0 auto 24px", border: `3px solid ${TEAL}`,
          }}>
            &#10003;
          </div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: NAVY, margin: "0 0 12px" }}>
            Audit Submitted
          </h2>
          <p style={{ fontSize: 16, color: SLATE, maxWidth: 500, margin: "0 auto 24px" }}>
            Your Parity Audit for <strong>{practiceData.practice_name}</strong> has been submitted.
            A confirmation has been sent to <strong>{practiceData.contact_email}</strong>.
          </p>

          <div style={{
            background: "#F0FDFA", border: `1px solid ${TEAL}`, borderRadius: 12,
            padding: 24, maxWidth: 400, margin: "0 auto 32px", textAlign: "left",
          }}>
            {auditId && auditId !== "pending" && (
              <div style={{ marginBottom: 12 }}>
                <span style={{ fontSize: 12, color: SLATE }}>Audit ID</span>
                <div style={{ fontSize: 14, fontWeight: 600, color: NAVY, fontFamily: "monospace" }}>
                  {auditId}
                </div>
              </div>
            )}
            <div>
              <span style={{ fontSize: 12, color: SLATE }}>Expected Delivery</span>
              <div style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>Instantly</div>
            </div>
          </div>

          <div style={{ fontSize: 14, color: SLATE, lineHeight: 1.6, maxWidth: 500, margin: "0 auto" }}>
            <p><strong>What happens next:</strong></p>
            <ul style={{ textAlign: "left", paddingLeft: 20 }}>
              <li>Your audit results are generated automatically</li>
              <li>We run a full contract integrity analysis across all payers</li>
              <li>You receive your complete Parity Audit report via email</li>
            </ul>
          </div>

          <div style={{ marginTop: 24 }}>
            <Link
              to="/audit/account"
              style={{ color: "#0D9488", fontSize: 15, fontWeight: 600, textDecoration: "none" }}
            >
              View your audit status &rarr;
            </Link>
          </div>
        </div>
      )}

      {/* Navigation buttons */}
      {step < 4 && (
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          marginTop: 32, paddingTop: 24, borderTop: "1px solid #E2E8F0",
        }}>
          <button
            onClick={() => step === 0 ? setStarted(false) : setStep(s => s - 1)}
            style={{ ...btnOutline, fontSize: 14, padding: "10px 20px" }}
          >
            {step === 0 ? "\u2190 Back" : "\u2190 Previous"}
          </button>

          {step < 3 ? (
            <button
              onClick={() => setStep(s => s + 1)}
              disabled={!canProceed(step)}
              style={{
                ...btnPrimary, fontSize: 14, padding: "10px 24px",
                opacity: canProceed(step) ? 1 : 0.5,
                cursor: canProceed(step) ? "pointer" : "not-allowed",
              }}
            >
              Next &rarr;
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!consent || submitting}
              style={{
                ...btnPrimary, fontSize: 15, padding: "12px 32px",
                opacity: consent && !submitting ? 1 : 0.5,
                cursor: consent && !submitting ? "pointer" : "not-allowed",
              }}
            >
              {submitting ? "Submitting..." : "Submit Audit"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}


// ---------------------------------------------------------------------------
// Fee method input sub-component
// ---------------------------------------------------------------------------

function FeeMethodInput({ method, zipCode, onExtract }) {
  const [text, setText] = useState("");
  const [pct, setPct] = useState("");
  const [zip, setZip] = useState(zipCode || "");

  if (method === "excel") {
    return (
      <DropZone accept=".xlsx,.xls,.csv" onChange={e => e.target.files?.[0] && onExtract(e.target.files[0])}>
        Upload your fee schedule spreadsheet (.xlsx, .csv)
      </DropZone>
    );
  }

  if (method === "pdf") {
    return (
      <DropZone accept=".pdf,application/pdf" onChange={e => e.target.files?.[0] && onExtract(e.target.files[0])}>
        Upload your payer contract PDF
      </DropZone>
    );
  }

  if (method === "photo") {
    return (
      <DropZone accept="image/*" onChange={e => e.target.files?.[0] && onExtract(e.target.files[0])}>
        Upload a photo or screenshot of your fee schedule
      </DropZone>
    );
  }

  if (method === "paste") {
    return (
      <div>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste your fee schedule text here (CPT codes and rates)..."
          style={{
            ...inputStyle, minHeight: 160, resize: "vertical",
            fontFamily: "monospace", fontSize: 13,
          }}
        />
        <button
          onClick={() => text.trim() && onExtract(text)}
          disabled={!text.trim()}
          style={{
            ...btnPrimary, marginTop: 12, fontSize: 14, padding: "10px 24px",
            opacity: text.trim() ? 1 : 0.5,
          }}
        >
          Extract Rates
        </button>
      </div>
    );
  }

  if (method === "medicare-pct") {
    return (
      <div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
          <div>
            <label style={labelStyle}>Percentage of Medicare</label>
            <input
              type="number" min="50" max="300" step="1"
              value={pct}
              onChange={e => setPct(e.target.value)}
              style={inputStyle}
              placeholder="e.g., 115"
            />
          </div>
          <div>
            <label style={labelStyle}>Practice ZIP Code</label>
            <input
              value={zip}
              onChange={e => setZip(e.target.value)}
              style={inputStyle}
              placeholder="e.g., 33701"
              maxLength={5}
            />
          </div>
        </div>
        <button
          onClick={() => pct && zip.length === 5 && onExtract({ percentage: parseFloat(pct), zipCode: zip })}
          disabled={!pct || zip.length !== 5}
          style={{
            ...btnPrimary, fontSize: 14, padding: "10px 24px",
            opacity: pct && zip.length === 5 ? 1 : 0.5,
          }}
        >
          Calculate Rates
        </button>
      </div>
    );
  }

  return null;
}
