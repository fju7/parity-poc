import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// ─── Sample contract compliance data ────────────────────────────────────────
const COMPLIANCE_ROWS = [
  { id: 1, dos: "2024-12-02", cpt: "99213", desc: "Office visit, est. patient, low", payer: "Aetna", contracted: 142, paid: 142, variance: 0, status: "correct" },
  { id: 2, dos: "2024-12-03", cpt: "99214", desc: "Office visit, est. patient, moderate", payer: "BCBS Illinois", contracted: 198, paid: 198, variance: 0, status: "correct" },
  { id: 3, dos: "2024-12-05", cpt: "99214", desc: "Office visit, est. patient, moderate", payer: "Aetna", contracted: 162, paid: 148, variance: -14, status: "underpaid" },
  { id: 4, dos: "2024-12-06", cpt: "93000", desc: "Electrocardiogram, 12-lead", payer: "Cigna", contracted: 58, paid: 58, variance: 0, status: "correct" },
  { id: 5, dos: "2024-12-09", cpt: "99215", desc: "Office visit, est. patient, high", payer: "UnitedHealth", contracted: 248, paid: 218, variance: -30, status: "underpaid" },
  { id: 6, dos: "2024-12-10", cpt: "36415", desc: "Venipuncture, routine", payer: "Aetna", contracted: 12, paid: 12, variance: 0, status: "correct" },
  { id: 7, dos: "2024-12-11", cpt: "85025", desc: "Complete blood count, automated", payer: "BCBS Illinois", contracted: 18, paid: 14, variance: -4, status: "minor" },
  { id: 8, dos: "2024-12-13", cpt: "99213", desc: "Office visit, est. patient, low", payer: "Cigna", contracted: 138, paid: 138, variance: 0, status: "correct" },
  { id: 9, dos: "2024-12-16", cpt: "99214", desc: "Office visit, est. patient, moderate", payer: "UnitedHealth", contracted: 178, paid: 152, variance: -26, status: "underpaid" },
  { id: 10, dos: "2024-12-18", cpt: "93000", desc: "Electrocardiogram, 12-lead", payer: "Aetna", contracted: 55, paid: 55, variance: 0, status: "correct" },
];

// ─── Sample denial data ─────────────────────────────────────────────────────
const DENIAL_ROWS = [
  { id: 1, dos: "2024-12-04", cpt: "99213", payer: "Aetna", code: "CO-16", reason: "Missing required field", plainReason: "Administrative error — a required claim field was not populated. High appeal success rate when documentation is complete.", appealScore: 5, recoverable: 142 },
  { id: 2, dos: "2024-12-07", cpt: "99214", payer: "BCBS Illinois", code: "CO-197", reason: "Prior authorization required", plainReason: "Payer required prior authorization for this service. Reviewable if authorization was obtained before date of service.", appealScore: 3, recoverable: 198 },
  { id: 3, dos: "2024-12-08", cpt: "93000", payer: "Cigna", code: "CO-4", reason: "Incorrect modifier", plainReason: "The modifier submitted does not match expected coding. Modifier documentation in the medical record supports appeal.", appealScore: 4, recoverable: 58 },
  { id: 4, dos: "2024-12-12", cpt: "99215", payer: "UnitedHealth", code: "CO-50", reason: "Non-covered service", plainReason: "Payer considers this service non-covered under the patient's plan. Appeal may succeed if medical necessity is documented.", appealScore: 2, recoverable: 248 },
  { id: 5, dos: "2024-12-15", cpt: "99214", payer: "Aetna", code: "CO-16", reason: "Missing required field", plainReason: "Repeat CO-16 from same payer — suggests systemic issue with claim submission. Administrative correction likely to resolve.", appealScore: 5, recoverable: 162 },
  { id: 6, dos: "2024-12-17", cpt: "36415", payer: "BCBS Illinois", code: "PR-96", reason: "Patient responsibility — not covered", plainReason: "Service applied to patient responsibility. Review EOB to confirm correct benefit assignment.", appealScore: 1, recoverable: 12 },
  { id: 7, dos: "2024-12-19", cpt: "99213", payer: "Cigna", code: "CO-4", reason: "Incorrect modifier", plainReason: "Second modifier-related denial from Cigna this month. Pattern suggests payer-side adjudication change — contact provider relations.", appealScore: 4, recoverable: 138 },
];

// ─── Appeal letter generator ────────────────────────────────────────────────
function generateAppealLetter(denial) {
  const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const deadlineDate = new Date(Date.now() + 30 * 86400000).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

  const cmsRef = {
    "CO-16": "CMS IOM 100-04, Chapter 1, Section 80.3.2 — Claims Processing Guidelines: Administrative errors in claim submission do not constitute a valid basis for denial when the underlying service was medically necessary and properly rendered.",
    "CO-197": "42 CFR \u00a7 422.568(b) — Prior authorization requirements must be applied consistently. When authorization was obtained prior to the date of service, retroactive denial on prior-auth grounds is not supported.",
    "CO-4": "CMS NCCI Policy Manual, Chapter 1, Section G — Modifier usage must be evaluated in context of the complete medical record. Incorrect modifier denials require review of operative notes and supporting documentation.",
    "CO-50": "42 CFR \u00a7 410.32 — Medical necessity determinations must be based on individual clinical circumstances. Blanket non-coverage determinations are subject to appeal when clinical documentation supports the service.",
    "PR-96": "ERISA \u00a7 503 — Benefit determination must be consistent with plan documents. Patient responsibility assignments require verification against the specific plan benefit structure.",
  }[denial.code] || "CMS Claims Processing Guidelines — Standard appeal procedures apply.";

  return `RIVERSIDE FAMILY MEDICINE
1200 River Road, Suite 200
Springfield, IL 62701
NPI: 1234567890
Tax ID: 36-1234567

${today}

${denial.payer}
Claims Appeals Department
P.O. Box 14079
Lexington, KY 40512

RE: Appeal of Denied Claim
Patient: [Redacted for demo]
Date of Service: ${denial.dos}
CPT Code: ${denial.cpt}
Claim Number: RFM-2024-${String(denial.id).padStart(4, "0")}
Denial Code: ${denial.code} — ${denial.reason}

Dear Claims Review Committee,

We are writing to formally appeal the denial of the above-referenced claim. After careful review of the denial reason code ${denial.code} ("${denial.reason}"), we believe this denial was issued in error and request immediate reconsideration.

DENIAL ANALYSIS
The denial code ${denial.code} indicates: ${denial.plainReason}

REGULATORY BASIS FOR APPEAL
${cmsRef}

CLINICAL DOCUMENTATION SUMMARY
The patient presented on ${denial.dos} for ${denial.cpt === "99213" || denial.cpt === "99214" || denial.cpt === "99215" ? "an established patient office visit" : denial.cpt === "93000" ? "a 12-lead electrocardiogram" : denial.cpt === "36415" ? "routine venipuncture" : "the documented service"}. The medical record includes: chief complaint, history of present illness, review of systems, physical examination findings, and medical decision-making documentation consistent with CPT ${denial.cpt} coding requirements.

${denial.code === "CO-16" ? "All required fields are present in the attached corrected claim form. The original submission error has been identified and corrected." : ""}${denial.code === "CO-197" ? "Prior authorization reference number [AUTH-XXXX] was obtained on [date prior to DOS] and remains on file. We have attached a copy of the authorization confirmation." : ""}${denial.code === "CO-4" ? "The modifier applied is consistent with the documentation in the medical record. We have attached the relevant operative/procedure notes for your review." : ""}${denial.code === "CO-50" ? "The service was medically necessary based on the patient's clinical presentation. Supporting clinical documentation is attached demonstrating medical necessity criteria are met." : ""}${denial.code === "PR-96" ? "We request verification of the patient's benefit structure as our records indicate this service should be a covered benefit under the patient's plan." : ""}

REQUEST
We respectfully request that ${denial.payer} reconsider this denial and process payment of $${denial.recoverable.toFixed(2)} for CPT ${denial.cpt} rendered on ${denial.dos}. Please provide a written response within 30 calendar days per applicable regulatory requirements.

Sincerely,

Dr. Sarah Chen, MD
Riverside Family Medicine
Phone: (217) 555-0142
Fax: (217) 555-0143`;
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function ProviderProductPage() {
  const [demoTab, setDemoTab] = useState("compliance");
  const [selectedDenial, setSelectedDenial] = useState(null);
  const [showAppealLetter, setShowAppealLetter] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [showConversion, setShowConversion] = useState(false);
  const [selectedCompliance, setSelectedCompliance] = useState(null);
  const { isAuthenticated, company } = useAuth();

  const triggerInteraction = useCallback(() => {
    if (!hasInteracted) {
      setHasInteracted(true);
      setTimeout(() => setShowConversion(true), 2000);
    }
  }, [hasInteracted]);

  const handleTabSwitch = useCallback((tab) => {
    setDemoTab(tab);
    setSelectedDenial(null);
    setShowAppealLetter(false);
    setSelectedCompliance(null);
    triggerInteraction();
  }, [triggerInteraction]);

  const handleDenialClick = useCallback((denial) => {
    setSelectedDenial(selectedDenial?.id === denial.id ? null : denial);
    setShowAppealLetter(false);
    triggerInteraction();
  }, [selectedDenial, triggerInteraction]);

  const handleComplianceClick = useCallback((row) => {
    setSelectedCompliance(selectedCompliance?.id === row.id ? null : row);
    triggerInteraction();
  }, [selectedCompliance, triggerInteraction]);

  // Summary calculations
  const totalPayments = COMPLIANCE_ROWS.length;
  const underpayments = COMPLIANCE_ROWS.filter(r => r.variance < 0).length;
  const totalVariance = COMPLIANCE_ROWS.reduce((s, r) => s + Math.abs(Math.min(r.variance, 0)), 0);
  const totalDenials = DENIAL_ROWS.length;
  const appealWorthy = DENIAL_ROWS.filter(r => r.appealScore >= 4).length;
  const totalRecoverable = DENIAL_ROWS.filter(r => r.appealScore >= 3).reduce((s, r) => s + r.recoverable, 0);

  const starColor = (score) => score >= 4 ? "#22c55e" : score >= 3 ? "#f59e0b" : "#64748b";

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* ── Header — matches EmployerProductPage ── */}
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.92)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" }}>CivicScale</span>
        </a>
        <nav style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 14 }}>
          {isAuthenticated && company?.type === "provider" ? (
            <>
              <Link to="/provider/dashboard" style={{ color: "#94a3b8", textDecoration: "none" }}>Dashboard</Link>
            </>
          ) : (
            <>
              <Link to="/provider/login" style={{ color: "#94a3b8", textDecoration: "none", fontWeight: 500 }}>Sign In</Link>
              <Link to="/provider/signup" style={{ background: "#3b82f6", color: "#fff", textDecoration: "none", borderRadius: 6, padding: "8px 20px", fontWeight: 500, fontSize: 14 }}>
                Start Free Trial
              </Link>
            </>
          )}
        </nav>
      </header>

      {/* ── Section 1: Hero ── */}
      <section style={{ paddingTop: 120, paddingBottom: 56, maxWidth: 820, margin: "0 auto", textAlign: "center", padding: "120px 24px 56px" }}>
        <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: 8, padding: "8px 14px", marginBottom: 24 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#60a5fa" }}>PARITY PROVIDER</span>
        </div>
        <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(30px, 4vw, 46px)", lineHeight: 1.15, fontWeight: 400, color: "#f1f5f9", marginBottom: 12, letterSpacing: "-0.02em" }}>
          Your payers agreed to a contract.<br />
          <span style={{ color: "#60a5fa" }}>Most practices never verify they're honoring it.</span>
        </h1>
        <p style={{ fontSize: 20, fontWeight: 500, color: "#60a5fa", marginBottom: 20 }}>
          Now you can &mdash; automatically, every month.
        </p>
        <p style={{ fontSize: 17, lineHeight: 1.7, color: "#94a3b8", maxWidth: 700, margin: "0 auto 32px" }}>
          Parity Provider compares every remittance payment against your contracted rates, identifies denial patterns by payer and reason code, scores each denial for appeal worthiness, and generates AI-drafted appeal letters grounded in specific CMS guidelines and your contract terms. In minutes, not days.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <a href="#demo" style={{ display: "inline-block", background: "#3b82f6", color: "#fff", padding: "12px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            See Your Analysis &darr;
          </a>
          <a href="#demo" style={{ display: "inline-block", border: "1px solid rgba(59,130,246,0.4)", color: "#60a5fa", padding: "12px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            See a Demo &darr;
          </a>
        </div>
        <p style={{ fontSize: 13, color: "#64748b", marginTop: 16 }}>No credit card required &middot; 30-day free trial &middot; Cancel anytime</p>
      </section>

      {/* ── Section 2: The Revenue Leakage Problem ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 780, margin: "0 auto" }}>
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: 16, padding: "36px 40px" }}>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 24, fontWeight: 400, color: "#f1f5f9", marginBottom: 20 }}>
            What your billing system shows you. What it doesn't.
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, fontSize: 15, lineHeight: 1.75, color: "#94a3b8" }}>
            <p style={{ margin: 0 }}>
              Your billing system tracks what was billed and what was paid. It does not tell you whether what was paid matches what was contracted. That comparison &mdash; payment line by payment line, against your actual fee schedule &mdash; requires a separate analytical step that most practices never take.
            </p>
            <p style={{ margin: 0 }}>
              Industry data consistently shows practices lose 3&ndash;4% of net revenue to underpayments and unworked denials. For a practice billing $500,000 annually, that's $15,000&ndash;20,000 per year &mdash; and it compounds, because payers that underpay without consequence tend to continue underpaying.
            </p>
            <p style={{ margin: 0 }}>
              Denials are the other half of the problem. The reason code tells you what happened. It rarely tells you whether the denial is correct, whether it's worth appealing, or what specific documentation would overturn it. Building that analysis manually for every denial is beyond the capacity of most billing teams.
            </p>
            <p style={{ margin: 0, color: "#cbd5e1", fontWeight: 500 }}>
              Parity Provider does both &mdash; systematically, every month, from the 835 files you already receive.
            </p>
          </div>
        </div>
      </section>

      {/* ── Section 3: Embedded Demo ── */}
      <section id="demo" style={{ padding: "72px 24px 80px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase", color: "#60a5fa", marginBottom: 12 }}>Interactive Demo</div>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 32, fontWeight: 400, color: "#f1f5f9", marginBottom: 12 }}>
            See what's in your remittance data &mdash; no upload required
          </h2>
          <p style={{ fontSize: 15, color: "#94a3b8", maxWidth: 640, margin: "0 auto" }}>
            This is sample data from a fictional family medicine practice. Upload your own 835 files during your free trial.
          </p>
        </div>

        {/* Demo container */}
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 16, overflow: "hidden" }}>

          {/* Tab bar */}
          <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            {[
              { key: "compliance", label: "Contract Compliance" },
              { key: "denials", label: "Denial Analysis" },
            ].map((t) => (
              <button key={t.key} onClick={() => handleTabSwitch(t.key)} style={{
                flex: 1, padding: "14px 0", background: demoTab === t.key ? "rgba(59,130,246,0.08)" : "transparent",
                border: "none", borderBottom: demoTab === t.key ? "2px solid #3b82f6" : "2px solid transparent",
                color: demoTab === t.key ? "#60a5fa" : "#64748b", fontSize: 14, fontWeight: 600, cursor: "pointer",
                fontFamily: "'DM Sans', sans-serif",
              }}>{t.label}</button>
            ))}
          </div>

          {/* ─ Compliance Tab ─ */}
          {demoTab === "compliance" && (
            <div>
              {/* Summary bar */}
              <div style={{ display: "flex", gap: 0, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {[
                  { value: totalPayments, label: "Payments analyzed", color: "#f1f5f9" },
                  { value: underpayments, label: "Underpayments identified", color: "#ef4444" },
                  { value: `$${totalVariance}`, label: "Est. variance", color: "#f59e0b" },
                ].map((s, i) => (
                  <div key={i} style={{ flex: 1, padding: "16px 20px", borderRight: i < 2 ? "1px solid rgba(255,255,255,0.06)" : "none" }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Table header */}
              <div style={{ display: "grid", gridTemplateColumns: "80px 70px 1fr 120px 90px 90px 90px 80px", padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 11, fontWeight: 600, color: "#64748b", letterSpacing: 0.5, textTransform: "uppercase" }}>
                <span>Date</span><span>CPT</span><span>Description</span><span>Payer</span>
                <span style={{ textAlign: "right" }}>Contracted</span><span style={{ textAlign: "right" }}>Paid</span>
                <span style={{ textAlign: "right" }}>Variance</span><span style={{ textAlign: "center" }}>Status</span>
              </div>

              {/* Rows */}
              {COMPLIANCE_ROWS.map((row) => (
                <div key={row.id}>
                  <div
                    onClick={() => handleComplianceClick(row)}
                    style={{
                      display: "grid", gridTemplateColumns: "80px 70px 1fr 120px 90px 90px 90px 80px",
                      padding: "10px 16px", fontSize: 13, cursor: "pointer",
                      background: selectedCompliance?.id === row.id ? "rgba(59,130,246,0.08)" : row.status === "underpaid" ? "rgba(239,68,68,0.04)" : "transparent",
                      borderBottom: "1px solid rgba(255,255,255,0.03)",
                      borderLeft: row.status === "underpaid" ? "3px solid #ef4444" : row.status === "minor" ? "3px solid #f59e0b" : "3px solid transparent",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => { if (selectedCompliance?.id !== row.id) e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
                    onMouseLeave={(e) => { if (selectedCompliance?.id !== row.id) e.currentTarget.style.background = row.status === "underpaid" ? "rgba(239,68,68,0.04)" : "transparent"; }}
                  >
                    <span style={{ color: "#94a3b8" }}>{row.dos.slice(5)}</span>
                    <span style={{ color: "#60a5fa", fontFamily: "monospace", fontSize: 12 }}>{row.cpt}</span>
                    <span style={{ color: "#cbd5e1", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{row.desc}</span>
                    <span style={{ color: "#94a3b8" }}>{row.payer}</span>
                    <span style={{ textAlign: "right", color: "#94a3b8" }}>${row.contracted}</span>
                    <span style={{ textAlign: "right", color: "#cbd5e1" }}>${row.paid}</span>
                    <span style={{ textAlign: "right", color: row.variance < 0 ? "#ef4444" : "#4ade80", fontWeight: row.variance !== 0 ? 600 : 400 }}>
                      {row.variance === 0 ? "$0" : `-$${Math.abs(row.variance)}`}
                    </span>
                    <span style={{ textAlign: "center" }}>
                      <span style={{
                        display: "inline-block", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
                        background: row.status === "correct" ? "rgba(34,197,94,0.12)" : row.status === "minor" ? "rgba(245,158,11,0.12)" : "rgba(239,68,68,0.12)",
                        color: row.status === "correct" ? "#4ade80" : row.status === "minor" ? "#fbbf24" : "#f87171",
                      }}>
                        {row.status === "correct" ? "Correct" : row.status === "minor" ? "Minor" : "Underpaid"}
                      </span>
                    </span>
                  </div>

                  {/* Analytical Paths panel */}
                  {selectedCompliance?.id === row.id && row.variance < 0 && (
                    <div style={{ padding: "20px 16px 20px 19px", background: "rgba(59,130,246,0.04)", borderBottom: "1px solid rgba(59,130,246,0.15)" }}>
                      <h4 style={{ fontSize: 14, fontWeight: 600, color: "#60a5fa", margin: "0 0 12px" }}>Analytical Paths &mdash; CPT {row.cpt}, {row.payer}</h4>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12 }}>
                        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 14 }}>
                          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Contracted Rate</div>
                          <div style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9" }}>${row.contracted}</div>
                        </div>
                        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 14 }}>
                          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Paid Amount</div>
                          <div style={{ fontSize: 18, fontWeight: 700, color: "#ef4444" }}>${row.paid}</div>
                        </div>
                        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 14 }}>
                          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Variance</div>
                          <div style={{ fontSize: 18, fontWeight: 700, color: "#f59e0b" }}>-${Math.abs(row.variance)}</div>
                        </div>
                        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 14 }}>
                          <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Recommended Action</div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: "#60a5fa" }}>File contract dispute with {row.payer}</div>
                        </div>
                      </div>
                      <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 12, lineHeight: 1.6, margin: "12px 0 0" }}>
                        Contract reference: Fee Schedule Section {row.cpt.startsWith("99") ? "E&M" : "Diagnostic"}, effective 01/01/2024. {row.payer} is obligated to pay the contracted rate of ${row.contracted} for CPT {row.cpt}. The underpayment of ${Math.abs(row.variance)} should be recoverable through a standard contract dispute.
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ─ Denial Analysis Tab ─ */}
          {demoTab === "denials" && !selectedDenial && (
            <div>
              {/* Summary bar */}
              <div style={{ display: "flex", gap: 0, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                {[
                  { value: totalDenials, label: "Denials analyzed", color: "#f1f5f9" },
                  { value: appealWorthy, label: "Flagged as appeal-worthy", color: "#22c55e" },
                  { value: `$${totalRecoverable.toLocaleString()}`, label: "Est. recoverable", color: "#f59e0b" },
                ].map((s, i) => (
                  <div key={i} style={{ flex: 1, padding: "16px 20px", borderRight: i < 2 ? "1px solid rgba(255,255,255,0.06)" : "none" }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Table header */}
              <div style={{ display: "grid", gridTemplateColumns: "80px 70px 120px 80px 1fr 90px 80px", padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 11, fontWeight: 600, color: "#64748b", letterSpacing: 0.5, textTransform: "uppercase" }}>
                <span>Date</span><span>CPT</span><span>Payer</span><span>Code</span>
                <span>Reason</span><span style={{ textAlign: "center" }}>Appeal Score</span><span style={{ textAlign: "center" }}>Action</span>
              </div>

              {/* Rows */}
              {DENIAL_ROWS.map((denial) => (
                <div
                  key={denial.id}
                  onClick={() => handleDenialClick(denial)}
                  style={{
                    display: "grid", gridTemplateColumns: "80px 70px 120px 80px 1fr 90px 80px",
                    padding: "10px 16px", fontSize: 13, cursor: "pointer",
                    background: denial.appealScore >= 4 ? "rgba(34,197,94,0.04)" : "transparent",
                    borderBottom: "1px solid rgba(255,255,255,0.03)",
                    borderLeft: denial.appealScore >= 4 ? "3px solid #22c55e" : "3px solid transparent",
                    transition: "background 0.15s",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.03)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = denial.appealScore >= 4 ? "rgba(34,197,94,0.04)" : "transparent"; }}
                >
                  <span style={{ color: "#94a3b8" }}>{denial.dos.slice(5)}</span>
                  <span style={{ color: "#60a5fa", fontFamily: "monospace", fontSize: 12 }}>{denial.cpt}</span>
                  <span style={{ color: "#94a3b8" }}>{denial.payer}</span>
                  <span style={{ color: "#cbd5e1", fontFamily: "monospace", fontSize: 12 }}>{denial.code}</span>
                  <span style={{ color: "#cbd5e1", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{denial.plainReason.split(".")[0]}</span>
                  <span style={{ textAlign: "center" }}>
                    {Array.from({ length: 5 }, (_, i) => (
                      <span key={i} style={{ color: i < denial.appealScore ? starColor(denial.appealScore) : "#334155", fontSize: 14 }}>{"\u2605"}</span>
                    ))}
                  </span>
                  <span style={{ textAlign: "center" }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: "#60a5fa" }}>Appeal &rarr;</span>
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* ─ Appeal Letter Generator (Tab 3 — opens on denial click) ─ */}
          {demoTab === "denials" && selectedDenial && (
            <div style={{ padding: "24px" }}>
              {/* Back button */}
              <button onClick={() => { setSelectedDenial(null); setShowAppealLetter(false); }} style={{
                background: "none", border: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", borderRadius: 6,
                padding: "6px 14px", fontSize: 12, cursor: "pointer", fontFamily: "'DM Sans', sans-serif", marginBottom: 20,
              }}>&larr; Back to Denial List</button>

              {/* Denial context */}
              <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 20, marginBottom: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
                  <div>
                    <h3 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", margin: "0 0 8px" }}>
                      {selectedDenial.code} &mdash; {selectedDenial.reason}
                    </h3>
                    <div style={{ display: "flex", gap: 16, fontSize: 13, color: "#94a3b8", flexWrap: "wrap" }}>
                      <span>CPT {selectedDenial.cpt}</span>
                      <span>{selectedDenial.payer}</span>
                      <span>DOS: {selectedDenial.dos}</span>
                      <span>Amount: ${selectedDenial.recoverable}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Appeal Score</div>
                    <div>
                      {Array.from({ length: 5 }, (_, i) => (
                        <span key={i} style={{ color: i < selectedDenial.appealScore ? starColor(selectedDenial.appealScore) : "#334155", fontSize: 20 }}>{"\u2605"}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Interpretation + Strategy */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 16 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#60a5fa", marginBottom: 8 }}>Plain-Language Interpretation</div>
                  <p style={{ fontSize: 13, lineHeight: 1.6, color: "#94a3b8", margin: 0 }}>{selectedDenial.plainReason}</p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, padding: 16 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "#60a5fa", marginBottom: 8 }}>Appeal Strategy</div>
                  <p style={{ fontSize: 13, lineHeight: 1.6, color: "#94a3b8", margin: 0 }}>
                    {selectedDenial.code === "CO-16" && "Submit corrected claim with all required fields populated. Include cover letter referencing CMS IOM 100-04 guidelines. Success rate: ~78%."}
                    {selectedDenial.code === "CO-197" && "Gather prior authorization confirmation and submit with appeal. Reference 42 CFR \u00a7422.568(b) if auth was obtained prior to DOS."}
                    {selectedDenial.code === "CO-4" && "Attach operative/procedure notes demonstrating correct modifier usage. Reference NCCI Policy Manual Chapter 1, Section G."}
                    {selectedDenial.code === "CO-50" && "Document medical necessity with clinical notes. Reference 42 CFR \u00a7410.32 for individual clinical circumstance review."}
                    {selectedDenial.code === "PR-96" && "Verify patient benefit structure against plan documents. Reference ERISA \u00a7503 for benefit determination consistency."}
                  </p>
                </div>
              </div>

              {/* Generate Appeal Letter button */}
              {!showAppealLetter && (
                <button onClick={() => setShowAppealLetter(true)} style={{
                  background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8,
                  padding: "12px 28px", fontSize: 15, fontWeight: 600, cursor: "pointer",
                  fontFamily: "'DM Sans', sans-serif", display: "block", width: "100%",
                }}>
                  Generate Appeal Letter &rarr;
                </button>
              )}

              {/* Appeal letter */}
              {showAppealLetter && (
                <div style={{ background: "#0f172a", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 12, padding: 24, position: "relative" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: "#60a5fa", letterSpacing: 1, textTransform: "uppercase" }}>Generated Appeal Letter</div>
                    <button onClick={() => setShowAppealLetter(false)} style={{
                      background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#f87171",
                      borderRadius: 6, padding: "4px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer",
                      fontFamily: "'DM Sans', sans-serif",
                    }}>Hide Letter</button>
                  </div>
                  <pre style={{ fontSize: 12, lineHeight: 1.65, color: "#cbd5e1", whiteSpace: "pre-wrap", fontFamily: "'DM Sans', monospace", margin: 0 }}>
                    {generateAppealLetter(selectedDenial)}
                  </pre>
                  <div style={{ marginTop: 16, fontSize: 12, color: "#64748b", fontStyle: "italic" }}>
                    This letter is auto-generated from claim data and CMS guidelines. Review and customize before sending.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Demo footer */}
          <div style={{ padding: "16px 20px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "#64748b" }}>
              {demoTab === "compliance"
                ? `${totalPayments} payments analyzed \u2022 ${underpayments} underpayments identified \u2022 $${totalVariance} variance`
                : `${totalDenials} denials analyzed \u2022 ${appealWorthy} appeal-worthy \u2022 $${totalRecoverable.toLocaleString()} recoverable`}
              {" "}&middot; Sample data: Riverside Family Medicine
            </span>
            <span style={{ fontSize: 11, color: "#475569" }}>Powered by the Parity Engine</span>
          </div>
        </div>
      </section>

      {/* ── Conversion prompt ── */}
      {showConversion && (
        <div style={{
          position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 90,
          background: "linear-gradient(180deg, transparent, rgba(10,22,40,0.95) 30%)",
          padding: "40px 24px 24px", textAlign: "center",
        }}>
          <div style={{ maxWidth: 640, margin: "0 auto", background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.25)", borderRadius: 14, padding: "24px 32px", backdropFilter: "blur(12px)" }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>
              Start your free 30-day trial
            </h3>
            <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 16 }}>
              Analyze your actual remittance data and generate real appeal letters.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", alignItems: "center", flexWrap: "wrap" }}>
              <Link to="/provider/signup" style={{ background: "#3b82f6", color: "#fff", padding: "10px 24px", borderRadius: 8, fontWeight: 600, fontSize: 14, textDecoration: "none" }}>
                Start Free Trial &rarr;
              </Link>
              <button onClick={() => setShowConversion(false)} style={{ background: "none", border: "1px solid rgba(255,255,255,0.15)", color: "#94a3b8", padding: "10px 20px", borderRadius: 8, fontSize: 13, cursor: "pointer", fontFamily: "'DM Sans', sans-serif" }}>
                Dismiss
              </button>
            </div>
            <p style={{ fontSize: 11, color: "#64748b", marginTop: 10 }}>No credit card required &middot; 30-day free trial &middot; Cancel anytime</p>
          </div>
        </div>
      )}

      {/* ── Section 4: What You Get ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 960, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 40 }}>What You Get</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 24 }}>
          {FEATURE_CARDS.map((c) => (
            <div key={c.title} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: 14, padding: 28 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(59,130,246,0.12)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16, color: "#60a5fa", fontSize: 18 }}>{c.icon}</div>
              <h3 style={{ fontSize: 17, fontWeight: 600, color: "#f1f5f9", marginBottom: 10 }}>{c.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8" }}>{c.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Section 5: How It Works ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 780, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 40 }}>How It Works</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {HOW_STEPS.map((step, i) => (
            <div key={i} style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
              <div style={{
                width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
                background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.25)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, fontWeight: 700, color: "#60a5fa",
              }}>{i + 1}</div>
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", marginBottom: 6 }}>{step.title}</h3>
                <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8", margin: 0 }}>{step.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Section 6: Pricing ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 600, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 12 }}>Simple Pricing</h2>
        <p style={{ fontSize: 14, color: "#94a3b8", textAlign: "center", marginBottom: 40, maxWidth: 520, marginLeft: "auto", marginRight: "auto" }}>
          One plan. Full access. Try free for 30 days.
        </p>
        <div style={{ background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.35)", borderRadius: 14, padding: 36, textAlign: "center" }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#60a5fa", marginBottom: 8 }}>PARITY PROVIDER</div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 40, fontWeight: 700, color: "#f1f5f9" }}>$99</span>
            <span style={{ fontSize: 14, color: "#64748b" }}>/mo</span>
          </div>
          <div style={{ fontSize: 14, color: "#60a5fa", fontWeight: 600, marginBottom: 24 }}>30-day free trial &mdash; cancel anytime</div>
          <ul style={{ listStyle: "none", padding: 0, margin: "0 auto 24px", fontSize: 14, color: "#94a3b8", lineHeight: 2.2, textAlign: "left", maxWidth: 360 }}>
            {[
              "Unlimited 835 uploads",
              "Full contract compliance analysis",
              "Denial pattern analysis with plain-language interpretation",
              "Appeal letter generation for any denial",
              "Month-over-month trend tracking",
              "PDF report export",
            ].map((f) => (
              <li key={f}><span style={{ color: "#60a5fa", marginRight: 8 }}>{"\u2713"}</span>{f}</li>
            ))}
          </ul>
          <Link to="/provider/signup" style={{ display: "inline-block", background: "#3b82f6", color: "#fff", borderRadius: 8, padding: "12px 32px", fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            Start Free Trial &rarr;
          </Link>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 16 }}>
            No credit card required &middot; 30-day free trial &middot; Cancel anytime
          </p>
        </div>
      </section>

      {/* ── Section 7: Built on Public Data ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 960, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 12 }}>Built on Public Data</h2>
        <p style={{ fontSize: 14, color: "#94a3b8", textAlign: "center", marginBottom: 40 }}>Verified against current rates and guidelines.</p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 20 }}>
          {DATA_SOURCES.map((d) => (
            <div key={d.title} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.15)", borderRadius: 12, padding: 20 }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#60a5fa", marginBottom: 8 }}>{d.title}</h3>
              <p style={{ fontSize: 13, lineHeight: 1.6, color: "#94a3b8", margin: 0 }}>{d.text}</p>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 13, color: "#64748b", textAlign: "center", marginTop: 24 }}>
          No patient data stored beyond the session. Your remittance data is yours.
        </p>
      </section>

      {/* ── Footer ── */}
      <footer style={{ padding: "40px 24px", borderTop: "1px solid rgba(255,255,255,0.06)", textAlign: "center", fontSize: 13, color: "#475569" }}>
        <Link to="/" style={{ color: "#64748b", textDecoration: "none", marginRight: 24 }}>&larr; CivicScale Home</Link>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}

// ─── Static Data ─────────────────────────────────────────────────────────────

const FEATURE_CARDS = [
  { icon: "\u2637", title: "Contract Compliance Audit", text: "Every payment in your 835 compared against your contracted rates by payer, by CPT code, by date of service. Underpayments identified, quantified, and ranked by dollar amount. Monthly so you see whether variance is growing or shrinking." },
  { icon: "\u2691", title: "Denial Pattern Analysis", text: "Every denial code interpreted in plain language. Patterns identified across payers and months \u2014 so a new denial pattern from Aetna that emerged this quarter doesn't get missed in the volume. Each denial scored for appeal worthiness so your team focuses effort where it recovers the most revenue." },
  { icon: "\u2709", title: "AI Appeal Letters", text: "For any denial scored as appeal-worthy, a complete appeal letter drafted automatically \u2014 grounded in the specific CMS guideline relevant to your denial code and the contract terms you uploaded. Review, edit, and send. Hours of drafting time reduced to minutes." },
  { icon: "\u2197", title: "Trend Monitoring", text: "Month-over-month tracking of contract adherence, denial rates, and recoverable revenue by payer. See whether Aetna's underpayment on 99214 is getting worse. See whether your BCBS denial rate improved after you changed your documentation workflow. The patterns only appear over time." },
];

const HOW_STEPS = [
  { title: "Upload your 835 remittance files", text: "EDI format, any payer. Upload your fee schedules if you have them, or we benchmark against Medicare rates." },
  { title: "Review your findings", text: "Underpayments by payer, denial patterns by reason code, appeal-worthy denials ranked by recovery potential." },
  { title: "Act on what you find", text: "Generate appeal letters, track contract adherence trends, share monthly reports with your practice administrator or billing company." },
];

const DATA_SOURCES = [
  { title: "CMS Physician Fee Schedule", text: "841,000 rates updated annually, locality-adjusted." },
  { title: "CMS Denial Reason Codes", text: "Complete CARC/RARC library with plain-language interpretations." },
  { title: "NCCI Edit Pairs", text: "2.2 million code pair edits for coding compliance." },
  { title: "Your Contracted Rates", text: "Upload your fee schedules for contract-specific compliance analysis." },
];
