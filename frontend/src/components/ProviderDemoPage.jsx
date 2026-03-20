import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { API_BASE } from "../lib/apiBase";

// ---------------------------------------------------------------------------
// Denial code descriptions (for audit report display)
// ---------------------------------------------------------------------------

const DENIAL_CODE_REASONS = {
  "CO-97": "Procedure/service bundled — payer says it should be included in another service.",
  "CO-4": "Modifier required — payer expected a modifier that was missing or incorrect.",
  "CO-50": "Non-covered service — payer says this service is not covered under the plan.",
  "CO-45": "Contractual obligation — difference between billed and allowed amount.",
  "CO-16": "Missing information — claim lacks data needed for adjudication.",
  "OA-18": "Exact duplicate claim.",
};

// Appeal score heuristic: how likely is this denial to be overturned?
function appealScore(code) {
  const scores = { "CO-97": 7, "CO-4": 8, "CO-50": 5 };
  return scores[code] || 6;
}

// ---------------------------------------------------------------------------
// Static demo content for tabs that don't come from the 835 parse
// (Trends, Appeal Letters, Payer Intelligence)
// These reference Chesapeake Family Medicine and the actual denial codes.
// ---------------------------------------------------------------------------

const APPEAL_LETTERS = [
  {
    payer: "BlueCross Maryland",
    cpt: "99215",
    reasonCode: "CO-97",
    amount: 750,
    dos: "06/15/2024",
    claimId: "CFM240623023",
    letter: `RE: Appeal of Denied Claim CFM240623023
CPT 99215 — Office Visit, Established Patient, High Complexity
Date of Service: June 15, 2024
Billed Amount: $750.00

Dear BlueCross Maryland Claims Review Department,

I am writing to appeal the denial of the above-referenced claim under reason code CO-97 (The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated).

APPEAL BASIS

This denial incorrectly bundles CPT 99215 with a separately identifiable service. The E/M visit on June 15 involved a high-complexity evaluation that was distinct from any procedure performed on the same date. The documentation clearly supports:

1. A separately identifiable chief complaint requiring independent medical decision-making
2. Moderate-to-high complexity MDM with multiple chronic conditions assessed
3. 40+ minutes of total physician time documented

Per CMS NCCI Policy Manual, Chapter 1, Section E: "E/M services on the same date as a procedure are separately reportable when the E/M service is significant and separately identifiable." Modifier 25 was appropriately appended.

SUPPORTING DOCUMENTATION ENCLOSED

1. Complete progress note documenting the distinct E/M service
2. Procedure note (if applicable) showing the separate service
3. Time documentation supporting high complexity

We respectfully request that this claim be reprocessed and paid at the contracted rate.

Sincerely,
[Physician Name], MD
Chesapeake Family Medicine
NPI: [Practice NPI]`,
  },
  {
    payer: "BlueCross Maryland",
    cpt: "99214",
    reasonCode: "CO-4",
    amount: 550,
    dos: "06/18/2024",
    claimId: "CFM240626026",
    letter: `RE: Appeal of Denied Claim CFM240626026
CPT 99214 — Office Visit, Established Patient, Moderate Complexity
Date of Service: June 18, 2024
Billed Amount: $550.00

Dear BlueCross Maryland Claims Review Department,

I am writing to appeal the denial of the above-referenced claim under reason code CO-4 (The procedure code is inconsistent with the modifier used, or a required modifier is missing).

APPEAL BASIS

This denial indicates a modifier issue. Upon review, the original claim submission either omitted a required modifier or used an incorrect one. The service rendered was a legitimate, separately identifiable E/M encounter that warrants payment.

CORRECTIVE ACTION

1. The corrected claim is resubmitted with the appropriate modifier (25 — Significant, Separately Identifiable E/M Service)
2. The encounter note documents a distinct chief complaint, separate from any procedure performed
3. Medical decision-making of moderate complexity is supported by the clinical documentation

Per the AMA CPT Guidelines and CMS Claims Processing Manual (Chapter 12, Section 20.4.2), modifier 25 should be appended when "the physician may need to indicate that on the day a procedure or service was performed, the patient's condition required a significant, separately identifiable E/M service."

DOCUMENTATION ENCLOSED

- Corrected CMS-1500 with appropriate modifier
- Complete progress note for 06/18/2024
- Procedure note demonstrating the separate service

We respectfully request reprocessing and payment at the contracted rate.

Sincerely,
[Physician Name], MD
Chesapeake Family Medicine
NPI: [Practice NPI]`,
  },
  {
    payer: "BlueCross Maryland",
    cpt: "90707",
    reasonCode: "CO-50",
    amount: 180,
    dos: "06/22/2024",
    claimId: "CFM240630030",
    letter: `RE: Appeal of Denied Claim CFM240630030
CPT 90707 — MMR Vaccine (Measles, Mumps, Rubella)
Date of Service: June 22, 2024
Billed Amount: $180.00

Dear BlueCross Maryland Claims Review Department,

I am writing to appeal the denial of the above-referenced claim under reason code CO-50 (These are non-covered services because this is not deemed a "medical necessity" by the payer).

APPEAL BASIS

This denial states that the MMR vaccine is not covered. However, MMR vaccination is a medically necessary preventive service under the following circumstances:

1. The patient's immunization records indicated an incomplete vaccination series
2. The patient is in a high-risk category per CDC/ACIP guidelines
3. Under the ACA, ACIP-recommended vaccines must be covered without cost-sharing for in-network providers (42 USC §300gg-13)

REGULATORY CITATIONS

- Section 2713 of the Public Health Service Act requires coverage of immunizations recommended by ACIP with an "A" or "B" rating
- The ACIP recommends MMR vaccination for adults born after 1957 without evidence of immunity
- Maryland Insurance Code §15-836 requires coverage of immunizations

DOCUMENTATION ENCLOSED

1. Patient immunization history showing need for MMR
2. CDC/ACIP recommendation applicable to this patient
3. Clinical notes documenting medical necessity

We respectfully request that this claim be reprocessed. Denial of an ACIP-recommended vaccine may constitute a violation of federal preventive care coverage mandates.

Sincerely,
[Physician Name], MD
Chesapeake Family Medicine
NPI: [Practice NPI]`,
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TABS = [
  { key: "start", label: "Getting Started" },
  { key: "audit", label: "Your Audit Report" },
  { key: "trends", label: "Month-Over-Month Trends" },
  { key: "appeals", label: "Appeal Letters" },
  { key: "intel", label: "Payer Intelligence" },
];

export default function ProviderDemoPage() {
  const [activeTab, setActiveTab] = useState("start");
  const [expandedAppeal, setExpandedAppeal] = useState(null);
  const [demoData, setDemoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch demo analysis from backend on mount
  useEffect(() => {
    let cancelled = false;
    async function fetchDemo() {
      try {
        const res = await fetch(`${API_BASE}/api/provider/demo-analysis`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setDemoData(data);
          setLoading(false);
        }
      } catch (err) {
        console.error("Failed to load demo analysis:", err);
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    }
    fetchDemo();
    return () => { cancelled = true; };
  }, []);

  // Derive practice info from API data or use defaults during loading
  const practice = demoData?.practice || {
    name: "Chesapeake Family Medicine",
    location: "Baltimore, MD",
    providers: 4,
    payer_name: "BlueCross Maryland",
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap"
        rel="stylesheet"
      />

      {/* Demo banner */}
      <div style={{
        background: "rgba(59,130,246,0.15)",
        borderBottom: "1px solid rgba(59,130,246,0.25)",
        padding: "10px 20px",
        textAlign: "center",
        fontSize: "13px",
        color: "#93c5fd",
      }}>
        You're viewing a demo with sample data from {practice.name} (fictional).{" "}
        <Link to="/audit" style={{ color: "#60a5fa", fontWeight: "600", textDecoration: "none" }}>
          Start Your Free Audit &rarr;
        </Link>
      </div>

      {/* Header */}
      <header style={{
        padding: "16px 24px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        flexWrap: "wrap",
        gap: "8px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Link to="/" style={{
            width: "32px", height: "32px", borderRadius: "8px",
            background: "linear-gradient(135deg, #0d9488, #14b8a6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px", fontWeight: "700", color: "#0a1628", textDecoration: "none",
          }}>C</Link>
          <span style={{ fontWeight: "600", fontSize: "16px" }}>Parity Provider</span>
          <span style={{
            background: "rgba(59,130,246,0.15)", color: "#60a5fa",
            fontSize: "11px", fontWeight: "600", padding: "3px 8px",
            borderRadius: "4px", textTransform: "uppercase",
          }}>Demo</span>
        </div>
        <div style={{ fontSize: "13px", color: "#64748b" }}>
          {practice.name} &middot; {practice.location} &middot; {practice.providers} providers
        </div>
      </header>

      {/* Tab navigation */}
      <nav style={{
        display: "flex", gap: "0",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "0 24px", overflowX: "auto",
      }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            style={{
              padding: "14px 18px", fontSize: "13px",
              fontWeight: activeTab === t.key ? "600" : "400",
              color: activeTab === t.key ? "#60a5fa" : "#64748b",
              borderBottom: activeTab === t.key ? "2px solid #3b82f6" : "2px solid transparent",
              background: "none", border: "none", cursor: "pointer",
              whiteSpace: "nowrap", fontFamily: "inherit",
            }}
          >{t.label}</button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ padding: "32px 24px", maxWidth: "1100px", margin: "0 auto" }}>
        {activeTab === "start" && <GettingStartedTab practice={practice} onNavigate={setActiveTab} />}
        {activeTab === "audit" && (
          loading ? <LoadingState /> :
          error ? <ErrorState message={error} /> :
          <AuditReport data={demoData} practice={practice} />
        )}
        {activeTab === "trends" && <TrendsTab practice={practice} demoData={demoData} />}
        {activeTab === "appeals" && (
          <AppealsTab expanded={expandedAppeal} onToggle={(i) => setExpandedAppeal(expandedAppeal === i ? null : i)} />
        )}
        {activeTab === "intel" && <IntelTab practice={practice} />}
      </main>

      {/* Bottom CTA */}
      {activeTab !== "start" && <div style={{
        maxWidth: "1100px", margin: "0 auto", padding: "0 24px 48px",
        textAlign: "center",
      }}>
        <div style={{
          background: "rgba(59,130,246,0.06)",
          border: "1px solid rgba(59,130,246,0.15)",
          borderRadius: "12px",
          padding: "28px",
        }}>
          <p style={{ fontSize: "15px", color: "#94a3b8", margin: "0 0 16px" }}>
            This is what Parity Provider finds. Start with a free audit using your own data — no cost, no commitment.
          </p>
          <Link to="/audit" style={{
            display: "inline-block", background: "#3b82f6", color: "#fff",
            padding: "12px 28px", borderRadius: "8px", fontWeight: "600",
            fontSize: "15px", textDecoration: "none",
          }}>
            Start Your Free Audit &rarr;
          </Link>
        </div>
      </div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading / Error states
// ---------------------------------------------------------------------------

function LoadingState() {
  return (
    <div style={{ textAlign: "center", padding: "60px 20px" }}>
      <div style={{ fontSize: "16px", color: "#94a3b8", marginBottom: "12px" }}>
        Parsing demo 835 file...
      </div>
      <div style={{ fontSize: "13px", color: "#64748b" }}>
        Analyzing claims against contracted rates
      </div>
    </div>
  );
}

function ErrorState({ message }) {
  return (
    <div style={{ textAlign: "center", padding: "60px 20px" }}>
      <div style={{ fontSize: "16px", color: "#EF4444", marginBottom: "12px" }}>
        Failed to load demo analysis
      </div>
      <div style={{ fontSize: "13px", color: "#64748b" }}>{message}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 0: Getting Started
// ---------------------------------------------------------------------------

const FEE_METHODS = [
  { id: "excel", label: "Upload Excel file" },
  { id: "pdf", label: "Upload PDF contract" },
  { id: "paste", label: "Paste or type rates" },
  { id: "photo", label: "Upload photo of contract page" },
  { id: "medicare", label: "% of Medicare" },
];

const SAMPLE_FILES = [
  "BlueCross_ERA_Jun2024.835",
];

const mockInput = {
  background: "#fff",
  border: "1px solid #CBD5E1",
  borderRadius: "6px",
  padding: "8px 12px",
  fontSize: "13px",
  color: "#1E293B",
  width: "100%",
  boxSizing: "border-box",
  cursor: "default",
};

// Module-level flag persists across unmount/remount so animation only plays once
let gsAnimationPlayed = false;

function GettingStartedTab({ practice, onNavigate }) {
  const timers = useRef([]);

  const [payerVisible, setPayerVisible] = useState(false);
  const [medicareHighlighted, setMedicareHighlighted] = useState(false);
  const [percentText, setPercentText] = useState("");
  const [zipText, setZipText] = useState("");
  const [cptCalloutVisible, setCptCalloutVisible] = useState(false);
  const [visibleChips, setVisibleChips] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [linesVisible, setLinesVisible] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [ctaVisible, setCtaVisible] = useState(false);
  const [buttonPulse, setButtonPulse] = useState(false);

  useEffect(() => {
    if (gsAnimationPlayed) {
      setPayerVisible(true);
      setMedicareHighlighted(true);
      setPercentText("120");
      setZipText("21201");
      setCptCalloutVisible(true);
      setVisibleChips(1);
      setProgressPercent(100);
      setLinesVisible(true);
      setAnalysisComplete(true);
      setCtaVisible(true);
      setButtonPulse(true);
      return;
    }

    gsAnimationPlayed = true;

    const t = (fn, ms) => {
      const id = setTimeout(fn, ms);
      timers.current.push(id);
      return id;
    };

    t(() => setPayerVisible(true), 1000);
    t(() => setMedicareHighlighted(true), 1500);

    const pctChars = "120".split("");
    pctChars.forEach((ch, i) => {
      t(() => setPercentText((prev) => prev + ch), 1800 + i * 167);
    });

    const zipChars = "21201".split("");
    zipChars.forEach((ch, i) => {
      t(() => setZipText((prev) => prev + ch), 2300 + i * 100);
    });

    t(() => setCptCalloutVisible(true), 2800);

    t(() => setVisibleChips(1), 3800);

    const progressStart = 4700;
    const progressDuration = 1500;
    const progressSteps = 30;
    const stepInterval = progressDuration / progressSteps;
    for (let i = 1; i <= progressSteps; i++) {
      const pct = Math.round((i / progressSteps) * 100);
      t(() => setProgressPercent(pct), progressStart + i * stepInterval);
    }

    t(() => setLinesVisible(true), progressStart + progressDuration * 0.5);
    t(() => setAnalysisComplete(true), progressStart + progressDuration);

    t(() => {
      setCtaVisible(true);
      t(() => setButtonPulse(true), 300);
    }, progressStart + progressDuration + 500);

    return () => {
      timers.current.forEach(clearTimeout);
      timers.current = [];
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const progressColor = progressPercent >= 100 ? "#10B981" : "#3B82F6";

  return (
    <div>
      <style>{`
        @keyframes gsTypeCursor {
          0%, 100% { border-right-color: #1E293B; }
          50% { border-right-color: transparent; }
        }
        @keyframes gsChipBounce {
          0% { opacity: 0; transform: translateY(-12px) scale(0.95); }
          60% { opacity: 1; transform: translateY(3px) scale(1.02); }
          80% { transform: translateY(-1px) scale(1); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes gsScaleIn {
          0% { opacity: 0; transform: scale(0.92); }
          100% { opacity: 1; transform: scale(1); }
        }
        @keyframes gsPulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(59,130,246,0.5); }
          50% { box-shadow: 0 0 0 8px rgba(59,130,246,0); }
        }
      `}</style>

      <div style={{ textAlign: "center", marginBottom: "36px" }}>
        <h2 style={{ ...h2Style, marginBottom: "10px" }}>
          Two steps. Five minutes. No data entry.
        </h2>
        <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "560px", margin: "0 auto" }}>
          That's all it takes to find out if your payers are paying what they owe you.
        </p>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
        gap: "24px",
        marginBottom: "40px",
      }}>
        {/* Step 1 */}
        <div style={stepCardOuter}>
          <div style={stepLabel}>Step 1 — 30 seconds</div>
          <h3 style={stepTitle}>Tell us your payer</h3>

          <div style={{ marginBottom: "16px" }}>
            <div style={fieldLabel}>Payer</div>
            <div style={{ ...mockInput, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{
                opacity: payerVisible ? 1 : 0,
                transition: "opacity 0.5s ease",
              }}>BlueCross Maryland</span>
              <span style={{ color: "#94a3b8", fontSize: "11px" }}>{"\u25BC"}</span>
            </div>
          </div>

          <div style={{ marginBottom: "16px" }}>
            <div style={fieldLabel}>How would you like to provide your fee schedule?</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {FEE_METHODS.map((m) => {
                const isMedicare = m.id === "medicare";
                const selected = isMedicare && medicareHighlighted;
                return (
                  <div
                    key={m.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "10px",
                      padding: "10px 14px",
                      borderRadius: "8px",
                      border: selected ? "2px solid #0D9488" : "1px solid #E2E8F0",
                      background: selected ? "rgba(13,148,136,0.04)" : "#fff",
                      cursor: "default",
                      position: "relative",
                      transition: "border 0.3s ease, background 0.3s ease",
                    }}
                  >
                    <div style={{
                      width: "16px", height: "16px", borderRadius: "50%",
                      border: selected ? "5px solid #0D9488" : "2px solid #CBD5E1",
                      boxSizing: "border-box", flexShrink: 0,
                      transition: "border 0.3s ease",
                    }} />
                    <span style={{
                      fontSize: "13px", color: "#1E293B",
                      fontWeight: selected ? "600" : "400",
                      transition: "font-weight 0.3s ease",
                    }}>
                      {m.label}
                    </span>
                    {selected && (
                      <span style={{
                        marginLeft: "auto",
                        fontSize: "10px", fontWeight: "700", textTransform: "uppercase",
                        letterSpacing: "0.04em",
                        background: "#0D9488", color: "#fff",
                        padding: "3px 8px", borderRadius: "4px",
                        animation: "gsScaleIn 0.3s ease forwards",
                      }}>Easiest</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{
            background: "#F0FDFA", border: "1px solid #99F6E4",
            borderRadius: "10px", padding: "16px", marginBottom: "16px",
            opacity: medicareHighlighted ? 1 : 0.4,
            transition: "opacity 0.4s ease",
          }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "14px" }}>
              <div>
                <div style={fieldLabel}>Percentage of Medicare</div>
                <div style={{
                  ...mockInput, background: "#fff",
                  borderRight: percentText.length > 0 && percentText.length < 3 ? "2px solid #1E293B" : undefined,
                  animation: percentText.length > 0 && percentText.length < 3 ? "gsTypeCursor 0.6s step-end infinite" : undefined,
                }}>
                  {percentText ? `${percentText}%` : "\u00A0"}
                </div>
              </div>
              <div>
                <div style={fieldLabel}>Practice ZIP Code</div>
                <div style={{
                  ...mockInput, background: "#fff",
                  borderRight: zipText.length > 0 && zipText.length < 5 ? "2px solid #1E293B" : undefined,
                  animation: zipText.length > 0 && zipText.length < 5 ? "gsTypeCursor 0.6s step-end infinite" : undefined,
                }}>
                  {zipText || "\u00A0"}
                </div>
              </div>
            </div>
            <div style={{
              display: "flex", alignItems: "flex-start", gap: "8px",
              background: "#fff", borderRadius: "8px", padding: "12px",
              border: "1px solid #99F6E4",
              opacity: cptCalloutVisible ? 1 : 0,
              transform: cptCalloutVisible ? "scale(1)" : "scale(0.92)",
              transition: "opacity 0.5s ease, transform 0.5s ease",
            }}>
              <span style={{
                color: "#0D9488", fontSize: "16px", lineHeight: "1", flexShrink: 0,
                opacity: cptCalloutVisible ? 1 : 0,
                transition: "opacity 0.3s ease 0.2s",
              }}>{"\u2713"}</span>
              <span style={{ fontSize: "12px", color: "#1E293B", lineHeight: "1.5" }}>
                <strong>7,718 CPT codes</strong> generated instantly from 2026 CMS Medicare Fee Schedule, adjusted for Baltimore, MD locality
              </span>
            </div>
          </div>

          <p style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.6", margin: 0 }}>
            Most contracts are structured as a percentage of Medicare. If yours is, you don't need to upload anything — just enter the percentage and your ZIP code. We do the rest.
          </p>
        </div>

        {/* Step 2 */}
        <div style={stepCardOuter}>
          <div style={stepLabel}>Step 2 — 60 seconds</div>
          <h3 style={stepTitle}>Upload your 835 file</h3>

          <div style={{
            border: "2px dashed #CBD5E1",
            borderRadius: "10px",
            padding: "28px 20px",
            textAlign: "center",
            marginBottom: "16px",
            background: "#F8FAFC",
          }}>
            <div style={{ fontSize: "28px", marginBottom: "8px", color: "#94a3b8" }}>{"\u2B06"}</div>
            <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "4px" }}>
              Drag & drop your remittance file here
            </div>
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>
              {visibleChips > 0 ? "1 file selected" : "\u00A0"}
            </div>
          </div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "12px", minHeight: "32px" }}>
            {SAMPLE_FILES.map((f, idx) => (
              <div
                key={f}
                style={{
                  display: idx < visibleChips ? "inline-flex" : "none",
                  alignItems: "center", gap: "6px",
                  background: "#EFF6FF", border: "1px solid #BFDBFE",
                  borderRadius: "6px", padding: "6px 12px", fontSize: "12px", color: "#1E40AF",
                  animation: "gsChipBounce 0.4s ease forwards",
                }}
              >
                <span style={{ fontSize: "14px" }}>{"\uD83D\uDCC4"}</span>
                {f}
              </div>
            ))}
          </div>

          <p style={{ fontSize: "11px", color: "#94a3b8", marginBottom: "16px" }}>
            Accepted formats: .835, .edi, .txt, or .zip containing multiple files
          </p>

          <p style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.6", marginBottom: "20px" }}>
            Your clearinghouse (Availity, Office Ally, Change Healthcare) sends these to you monthly.
            Download them from your clearinghouse portal and upload here — or just forward the email to us.
          </p>

          <div style={{
            background: "#F8FAFC", borderRadius: "8px", padding: "14px",
            border: "1px solid #E2E8F0", marginBottom: "12px",
            opacity: visibleChips >= 1 ? 1 : 0.3,
            transition: "opacity 0.4s ease",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
              <span style={{ fontSize: "12px", color: "#64748b" }}>
                {progressPercent > 0 ? "Processing..." : "\u00A0"}
              </span>
              <span style={{ fontSize: "12px", color: progressColor, fontWeight: "600", transition: "color 0.3s" }}>
                {progressPercent > 0 ? `${progressPercent}%` : "\u00A0"}
              </span>
            </div>
            <div style={{ height: "4px", borderRadius: "2px", background: "#E2E8F0" }}>
              <div style={{
                height: "4px", borderRadius: "2px",
                background: progressColor,
                width: `${progressPercent}%`,
                transition: "width 50ms linear, background 0.3s ease",
              }} />
            </div>
            <div style={{
              fontSize: "11px", color: "#64748b", marginTop: "6px",
              opacity: linesVisible ? 1 : 0,
              transition: "opacity 0.4s ease",
            }}>
              30 payment lines identified from BlueCross Maryland
            </div>
          </div>

          <div style={{
            display: "flex", alignItems: "center", gap: "8px",
            background: "#F0FDF4", border: "1px solid #BBF7D0",
            borderRadius: "8px", padding: "12px 14px",
            opacity: analysisComplete ? 1 : 0,
            transform: analysisComplete ? "translateY(0)" : "translateY(6px)",
            transition: "opacity 0.4s ease, transform 0.4s ease",
          }}>
            <span style={{ color: "#10B981", fontSize: "18px", flexShrink: 0 }}>{"\u2713"}</span>
            <span style={{ fontSize: "13px", color: "#166534", fontWeight: "600" }}>
              Analysis complete — your report is ready
            </span>
          </div>
        </div>
      </div>

      {/* Transition CTA */}
      <div style={{
        textAlign: "center", marginBottom: "8px",
        opacity: ctaVisible ? 1 : 0,
        transform: ctaVisible ? "translateY(0)" : "translateY(12px)",
        transition: "opacity 0.5s ease, transform 0.5s ease",
      }}>
        <div style={{
          display: "inline-flex", alignItems: "center", gap: "10px",
          fontSize: "22px", color: "#3B82F6", marginBottom: "20px",
        }}>
          <span>{"\u2501\u2501"}</span>
          <span>{"\u25B6"}</span>
          <span>{"\u2501\u2501"}</span>
        </div>
        <p style={{
          fontSize: "15px", color: "#94a3b8", lineHeight: "1.8",
          maxWidth: "640px", margin: "0 auto 24px",
        }}>
          That's it. From here, our AI analyzes every payment line against your contracted rates,
          interprets every denial code in plain English, and delivers a complete report.
          Here's what {practice.name}'s report looked like:
        </p>
        <button
          onClick={() => onNavigate("audit")}
          style={{
            display: "inline-block",
            background: "#3b82f6", color: "#fff",
            padding: "12px 28px", borderRadius: "8px",
            fontWeight: "600", fontSize: "15px",
            border: "none", cursor: "pointer",
            fontFamily: "inherit",
            transition: "background 0.2s",
            animation: buttonPulse ? "gsPulse 2s ease-in-out infinite" : "none",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#2563eb")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#3b82f6")}
        >
          See the Audit Report &rarr;
        </button>
      </div>
    </div>
  );
}

const stepCardOuter = {
  background: "#fff",
  borderRadius: "14px",
  padding: "28px",
  boxShadow: "0 1px 3px rgba(0,0,0,0.08), 0 4px 12px rgba(0,0,0,0.04)",
};

const stepLabel = {
  fontSize: "11px",
  fontWeight: "600",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "#0D9488",
  marginBottom: "6px",
};

const stepTitle = {
  fontSize: "18px",
  fontWeight: "600",
  color: "#1E293B",
  marginBottom: "20px",
};

const fieldLabel = {
  fontSize: "11px",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  marginBottom: "6px",
};

// ---------------------------------------------------------------------------
// Tab 1: Audit Report (data-driven from backend)
// ---------------------------------------------------------------------------

function AuditReport({ data, practice }) {
  const summary = data?.summary || {};
  const underpayments = data?.underpayments || [];
  const denials = data?.denials || [];

  const paidCount = summary.paid_count || 0;
  const deniedCount = summary.denied_count || 0;
  const totalCount = paidCount + deniedCount;
  const cleanClaimRate = totalCount > 0 ? Math.round((paidCount / totalCount) * 100) : 0;
  const denialRate = totalCount > 0 ? Math.round((deniedCount / totalCount) * 100) : 0;

  // Build executive summary from real numbers
  const denialCodeSummary = Object.entries(summary.denial_code_counts || {})
    .map(([code, count]) => `${code} (${count} ${count === 1 ? "claim" : "claims"})`)
    .join(", ");

  const execSummary = `${practice.name} shows a monthly revenue gap of ${fmt(summary.monthly_gap)} from a single payer (${practice.payer_name}). Of ${totalCount} claims analyzed, ${deniedCount} were denied outright totaling ${fmt(summary.total_denied)}, with denial codes ${denialCodeSummary}. Additionally, ${underpayments.length} paid claims show underpayments totaling ${fmt(summary.total_underpayment)} when compared to the contracted rate of ${practice.medicare_pct || 120}% of Medicare. Annualized, this practice is leaving approximately ${fmt(summary.annualized_gap)} on the table from this single payer alone.`;

  const recommendedActions = [
    `Appeal the ${summary.denial_code_counts?.["CO-97"] || 0} CO-97 (bundling) denials immediately — these claims were for separately identifiable services and modifier 25 documentation supports unbundling.`,
    `Appeal the ${summary.denial_code_counts?.["CO-4"] || 0} CO-4 (modifier) denials with corrected claims — resubmit with the appropriate modifier and supporting documentation.`,
    `Appeal the CO-50 denial on CPT 90707 (MMR vaccine) — ACIP-recommended vaccines are federally mandated covered services under ACA Section 2713.`,
    `Review all underpaid claims against your ${practice.medicare_pct || 120}% of Medicare contracted rate and file bulk rate discrepancy requests with ${practice.payer_name}.`,
  ];

  return (
    <div>
      <h2 style={h2Style}>Audit Report — {practice.name}</h2>
      <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "28px" }}>
        Period: June 2024 &middot; {practice.payer_name} &middot; {totalCount} claims analyzed
      </p>

      {/* Summary stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        <StatCard label="Total Billed" value={fmt(summary.total_billed)} />
        <StatCard label="Total Paid" value={fmt(summary.total_paid)} />
        <StatCard label="Underpayments" value={fmt(summary.total_underpayment)} accent="#EF4444" />
        <StatCard label="Denied Revenue" value={fmt(summary.total_denied)} accent="#F59E0B" />
        <StatCard label="Monthly Gap" value={fmt(summary.monthly_gap)} accent="#EF4444" />
        <StatCard label="Annualized Gap" value={fmt(summary.annualized_gap)} accent="#EF4444" />
      </div>

      {/* Executive Summary */}
      <div style={{ ...cardStyle, marginBottom: "28px" }}>
        <h3 style={h3Style}>AI Executive Summary</h3>
        <p style={{ fontSize: "14px", lineHeight: "1.8", color: "#94a3b8" }}>
          {execSummary}
        </p>
      </div>

      {/* Recommended Actions */}
      <div style={{ ...cardStyle, marginBottom: "32px" }}>
        <h3 style={h3Style}>Recommended Actions</h3>
        <ol style={{ margin: 0, paddingLeft: "20px", fontSize: "14px", lineHeight: "2", color: "#94a3b8" }}>
          {recommendedActions.map((a, i) => <li key={i}>{a}</li>)}
        </ol>
      </div>

      {/* Payer breakdown — single payer from the 835 */}
      <div style={{ ...cardStyle, marginBottom: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
          <h3 style={{ ...h3Style, margin: 0 }}>{practice.payer_name}</h3>
          <div style={{ display: "flex", gap: "16px", fontSize: "13px" }}>
            <span style={{ color: "#94a3b8" }}>Clean claim rate: <strong style={{ color: cleanClaimRate >= 90 ? "#22C55E" : cleanClaimRate >= 80 ? "#F59E0B" : "#EF4444" }}>{cleanClaimRate}%</strong></span>
            <span style={{ color: "#94a3b8" }}>Denial rate: <strong style={{ color: denialRate <= 5 ? "#22C55E" : denialRate <= 15 ? "#F59E0B" : "#EF4444" }}>{denialRate}%</strong></span>
          </div>
        </div>

        {underpayments.length > 0 && (
          <>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#EF4444", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>
              Underpayments ({fmt(summary.total_underpayment)})
            </div>
            <table style={tableStyle}>
              <thead>
                <tr>
                  {["CPT", "Description", "Billed", "Paid", "Contracted", "Variance", "Flag"].map(h => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {underpayments.map((u, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={tdStyle}>{u.cpt}</td>
                    <td style={{ ...tdStyle, color: "#94a3b8" }}>{u.desc}</td>
                    <td style={tdStyleR}>{fmt(u.billed)}</td>
                    <td style={tdStyleR}>{fmt(u.paid)}</td>
                    <td style={tdStyleR}>{fmt(u.contracted)}</td>
                    <td style={{ ...tdStyleR, color: "#EF4444" }}>-{fmt(u.variance)}</td>
                    <td style={{ ...tdStyle, color: "#EF4444", fontWeight: "600", fontSize: "11px" }}>{u.flag}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {denials.length > 0 && (
          <>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#F59E0B", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px", marginTop: underpayments.length > 0 ? "20px" : 0 }}>
              Denials ({fmt(summary.total_denied)})
            </div>
            <table style={tableStyle}>
              <thead>
                <tr>
                  {["CPT", "Description", "Billed", "Reason Code", "Reason", "Appeal Score"].map(h => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {denials.map((d, i) => {
                  const score = appealScore(d.reasonCode);
                  return (
                    <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={tdStyle}>{d.cpt}</td>
                      <td style={{ ...tdStyle, color: "#94a3b8" }}>{d.desc}</td>
                      <td style={tdStyleR}>{fmt(d.billed)}</td>
                      <td style={{ ...tdStyle, color: "#F59E0B", fontWeight: "600" }}>{d.reasonCode}</td>
                      <td style={{ ...tdStyle, color: "#94a3b8", fontSize: "12px" }}>{DENIAL_CODE_REASONS[d.reasonCode] || d.reasonCode}</td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: "10px", fontSize: "11px", fontWeight: "600",
                          background: score >= 7 ? "rgba(34,197,94,0.15)" : "rgba(59,130,246,0.15)",
                          color: score >= 7 ? "#22C55E" : "#60a5fa",
                        }}>{score}/10</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: Month-Over-Month Trends
// ---------------------------------------------------------------------------

function TrendsTab({ practice, demoData }) {
  const monthlyGap = demoData?.summary?.monthly_gap || 4855;

  // Illustrative trend: gap growing over 3 months
  const trendMonths = ["April 2024", "May 2024", "June 2024"];
  const gapValues = [
    Math.round(monthlyGap * 0.82),
    Math.round(monthlyGap * 0.91),
    monthlyGap,
  ];

  const trendData = [
    {
      label: `${practice.payer_name || "BlueCross"} CO-97 Denials`,
      values: [1, 2, 3],
      direction: "worsening",
      color: "#EF4444",
    },
    {
      label: "CO-4 Modifier Denials",
      values: [1, 1, 3],
      direction: "worsening",
      color: "#F59E0B",
    },
    {
      label: "Underpayment per Paid Claim",
      values: [8, 9, 11],
      unit: "$",
      direction: "worsening",
      color: "#EF4444",
    },
    {
      label: "Total Monthly Revenue Gap",
      values: gapValues,
      direction: "worsening",
      color: "#EF4444",
    },
  ];

  const trendNarrative = `Over the past three months, ${practice.name}'s revenue gap with ${practice.payer_name || "BlueCross Maryland"} has been trending upward — from ${fmt(gapValues[0])} in April to ${fmt(gapValues[2])} in June (+${Math.round(((gapValues[2] - gapValues[0]) / gapValues[0]) * 100)}%).

Key changes:
- CO-97 (bundling) denials increased from 1 to 3 per month. This suggests a systematic change in the payer's claims processing rules — possibly a new NCCI edit being applied. These denials are highly appealable with proper modifier 25 documentation.
- CO-4 (modifier) denials tripled from 1 to 3 in June. This pattern often indicates a new pre-edit check in the payer's system. A pre-submission modifier review checklist would prevent most of these.
- Underpayment per paid claim increased from $8 to $11, suggesting possible fee schedule changes that haven't been reflected in the contracted rate.

Recommended action: Schedule a joint call with your ${practice.payer_name || "BlueCross Maryland"} provider representative to discuss the bundling edit changes and verify your contracted rates are being applied correctly.`;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "8px" }}>
        <h2 style={{ ...h2Style, margin: 0 }}>Month-Over-Month Trends</h2>
        <span style={liveBadge}>LIVE — Available now with monitoring subscription</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        {trendData.map((t) => (
          <div key={t.label} style={cardStyle}>
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#94a3b8", marginBottom: "8px" }}>{t.label}</div>
            <div style={{ display: "flex", gap: "12px", alignItems: "flex-end", marginBottom: "8px" }}>
              {t.values.map((v, i) => (
                <div key={i} style={{ flex: 1, textAlign: "center" }}>
                  <div style={{ fontSize: "20px", fontWeight: "700", color: i === t.values.length - 1 ? t.color : "#94a3b8" }}>
                    {t.unit === "$" ? `$${v}` : t.unit === "%" ? `${v}%` : v === 0 ? "\u2014" : typeof v === "number" && v > 100 ? fmt(v) : v}
                  </div>
                  <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px" }}>{trendMonths[i].split(" ")[0].slice(0, 3)}</div>
                </div>
              ))}
            </div>
            <div style={{
              fontSize: "11px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.06em",
              color: t.direction === "improving" ? "#22C55E" : t.direction === "new" ? "#F59E0B" : "#EF4444",
            }}>
              {t.direction === "improving" ? "\u2193 Improving" : t.direction === "new" ? "\u26A0 New Pattern" : "\u2191 Worsening"}
            </div>
          </div>
        ))}
      </div>

      <div style={{ ...cardStyle, marginBottom: "28px" }}>
        <h3 style={h3Style}>Revenue Gap Trend</h3>
        <div style={{ display: "flex", gap: "16px", alignItems: "flex-end", height: "140px", padding: "20px 0" }}>
          {gapValues.map((v, i) => {
            const maxVal = Math.max(...gapValues);
            const height = (v / maxVal) * 100;
            return (
              <div key={i} style={{ flex: 1, textAlign: "center" }}>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#EF4444", marginBottom: "6px" }}>{fmt(v)}</div>
                <div style={{
                  height: `${height}px`, background: "rgba(239,68,68,0.3)",
                  border: "1px solid rgba(239,68,68,0.5)", borderRadius: "4px 4px 0 0",
                }} />
                <div style={{ fontSize: "12px", color: "#64748b", marginTop: "6px" }}>{trendMonths[i]}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div style={cardStyle}>
        <h3 style={h3Style}>AI Trend Analysis</h3>
        {trendNarrative.split("\n\n").map((p, i) => (
          <p key={i} style={{ fontSize: "14px", lineHeight: "1.8", color: "#94a3b8", marginBottom: "12px", whiteSpace: "pre-line" }}>
            {p}
          </p>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: Appeal Letters
// ---------------------------------------------------------------------------

function AppealsTab({ expanded, onToggle }) {
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px", flexWrap: "wrap", gap: "8px" }}>
        <h2 style={{ ...h2Style, margin: 0 }}>Appeal Letters</h2>
        <span style={liveBadge}>LIVE — Available now</span>
      </div>

      <p style={{ fontSize: "14px", color: "#94a3b8", marginBottom: "24px", lineHeight: "1.7" }}>
        Each denial from your audit has a draft appeal letter ready to review, edit, and send.
        Letters cite specific CMS guidelines and your contract terms.
      </p>

      {APPEAL_LETTERS.map((a, i) => (
        <div key={i} style={{ ...cardStyle, marginBottom: "16px" }}>
          <div
            style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer", flexWrap: "wrap", gap: "8px" }}
            onClick={() => onToggle(i)}
          >
            <div>
              <span style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0" }}>
                {a.payer} — {a.reasonCode} on CPT {a.cpt}
              </span>
              <span style={{ fontSize: "13px", color: "#64748b", marginLeft: "12px" }}>
                {fmt(a.amount)} &middot; DOS {a.dos}
              </span>
            </div>
            <button
              style={{
                padding: "6px 16px", borderRadius: "6px", fontSize: "12px", fontWeight: "600",
                border: "1px solid #3b82f6", background: expanded === i ? "#3b82f6" : "transparent",
                color: expanded === i ? "#fff" : "#60a5fa", cursor: "pointer", fontFamily: "inherit",
              }}
            >
              {expanded === i ? "Hide Letter" : "View Appeal Letter"}
            </button>
          </div>

          {expanded === i && (
            <div style={{
              marginTop: "16px", padding: "20px",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "8px",
            }}>
              <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "12px" }}>
                Claim ID: {a.claimId}
              </div>
              <pre style={{
                fontFamily: "'DM Sans', sans-serif",
                fontSize: "13px",
                lineHeight: "1.8",
                color: "#cbd5e1",
                whiteSpace: "pre-wrap",
                margin: 0,
              }}>
                {a.letter}
              </pre>
              <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
                <button style={{
                  padding: "8px 20px", borderRadius: "6px", fontSize: "13px", fontWeight: "600",
                  background: "#3b82f6", color: "#fff", border: "none", cursor: "pointer", fontFamily: "inherit",
                }}>
                  Copy to Clipboard
                </button>
                <button style={{
                  padding: "8px 20px", borderRadius: "6px", fontSize: "13px", fontWeight: "600",
                  background: "transparent", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.3)",
                  cursor: "pointer", fontFamily: "inherit",
                }}>
                  Download PDF
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 4: Payer Intelligence (Coming Soon)
// ---------------------------------------------------------------------------

function IntelTab({ practice }) {
  const benchmarkData = [
    { cpt: "99213", desc: "Office visit, est. low", yourRate: 105, marketMedian: 122, percentile: 28 },
    { cpt: "99214", desc: "Office visit, est. moderate", yourRate: 149, marketMedian: 168, percentile: 25 },
    { cpt: "99215", desc: "Office visit, est. high", yourRate: 210, marketMedian: 238, percentile: 22 },
    { cpt: "99396", desc: "Preventive visit, 40-64", yourRate: 178, marketMedian: 195, percentile: 32 },
    { cpt: "93000", desc: "ECG, 12-lead", yourRate: 33, marketMedian: 42, percentile: 20 },
  ];

  const codingDist = [
    { code: "99213", yours: 60, peers: 45 },
    { code: "99214", yours: 20, peers: 35 },
    { code: "99215", yours: 10, peers: 12 },
    { code: "99211/12", yours: 10, peers: 8 },
  ];

  return (
    <div style={{ position: "relative" }}>
      <div style={{
        position: "absolute", inset: 0, zIndex: 10,
        background: "rgba(10,22,40,0.7)",
        display: "flex", alignItems: "center", justifyContent: "center",
        borderRadius: "12px",
      }}>
        <div style={{ textAlign: "center", padding: "40px" }}>
          <div style={{ fontSize: "32px", marginBottom: "16px" }}>{"\uD83D\uDD2E"}</div>
          <h3 style={{ fontSize: "20px", fontWeight: "600", color: "#f1f5f9", marginBottom: "8px" }}>Coming Soon</h3>
          <p style={{ fontSize: "14px", color: "#94a3b8", maxWidth: "400px", lineHeight: "1.7" }}>
            Payer intelligence and benchmark comparisons become available as more practices join.
            Early adopters get priority access.
          </p>
          <Link to="/audit" style={{
            display: "inline-block", marginTop: "20px",
            background: "#3b82f6", color: "#fff", padding: "10px 24px",
            borderRadius: "8px", fontWeight: "600", fontSize: "14px", textDecoration: "none",
          }}>
            Start Your Free Audit &rarr;
          </Link>
        </div>
      </div>

      <div style={{ filter: "blur(2px)", pointerEvents: "none" }}>
        <h2 style={h2Style}>Payer Intelligence — {practice.payer_name || "BlueCross Maryland"}</h2>
        <p style={{ fontSize: "13px", color: "#64748b", marginBottom: "28px" }}>
          Your {practice.payer_name || "BlueCross"} rates vs. Family Medicine practices in {practice.location || "Baltimore metro"}
        </p>

        <div style={{ ...cardStyle, marginBottom: "28px" }}>
          <h3 style={h3Style}>Contract Rate Benchmarks</h3>
          <table style={tableStyle}>
            <thead>
              <tr>
                {["CPT", "Description", "Your Rate", "Market Median", "Percentile"].map(h => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmarkData.map((r) => (
                <tr key={r.cpt} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                  <td style={tdStyle}>{r.cpt}</td>
                  <td style={{ ...tdStyle, color: "#94a3b8" }}>{r.desc}</td>
                  <td style={tdStyleR}>{fmt(r.yourRate)}</td>
                  <td style={tdStyleR}>{fmt(r.marketMedian)}</td>
                  <td style={{ ...tdStyle, textAlign: "center" }}>
                    <span style={{
                      display: "inline-block", padding: "2px 8px", borderRadius: "10px",
                      fontSize: "11px", fontWeight: "600",
                      background: "rgba(239,68,68,0.15)", color: "#EF4444",
                    }}>{r.percentile}th</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8", marginTop: "16px" }}>
            Your {practice.payer_name || "BlueCross"} rates are below the 35th percentile across your top codes. At your next
            contract renewal, this data supports requesting a 10-15% rate increase.
          </p>
        </div>

        <div style={cardStyle}>
          <h3 style={h3Style}>E&M Coding Distribution vs. Specialty Peers</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: "16px", marginBottom: "16px" }}>
            {codingDist.map((c) => (
              <div key={c.code} style={{ textAlign: "center" }}>
                <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "8px" }}>{c.code}</div>
                <div style={{ display: "flex", gap: "4px", justifyContent: "center", alignItems: "flex-end", height: "60px" }}>
                  <div style={{
                    width: "24px", height: `${c.yours * 0.8}px`,
                    background: "rgba(59,130,246,0.4)", borderRadius: "3px 3px 0 0",
                  }} />
                  <div style={{
                    width: "24px", height: `${c.peers * 0.8}px`,
                    background: "rgba(148,163,184,0.3)", borderRadius: "3px 3px 0 0",
                  }} />
                </div>
                <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginTop: "4px", fontSize: "11px" }}>
                  <span style={{ color: "#60a5fa" }}>{c.yours}%</span>
                  <span style={{ color: "#64748b" }}>{c.peers}%</span>
                </div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: "16px", fontSize: "11px", justifyContent: "center" }}>
            <span><span style={{ display: "inline-block", width: "10px", height: "10px", borderRadius: "2px", background: "rgba(59,130,246,0.4)", marginRight: "4px", verticalAlign: "middle" }} />Your practice</span>
            <span><span style={{ display: "inline-block", width: "10px", height: "10px", borderRadius: "2px", background: "rgba(148,163,184,0.3)", marginRight: "4px", verticalAlign: "middle" }} />Specialty peers</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared styles and helpers
// ---------------------------------------------------------------------------

const h2Style = {
  fontFamily: "'DM Serif Display', serif",
  fontSize: "24px",
  fontWeight: "400",
  color: "#f1f5f9",
  marginBottom: "16px",
};

const h3Style = {
  fontSize: "15px",
  fontWeight: "600",
  color: "#e2e8f0",
  marginBottom: "12px",
};

const cardStyle = {
  background: "rgba(255,255,255,0.02)",
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "12px",
  padding: "24px",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "13px",
};

const thStyle = {
  padding: "8px 10px",
  textAlign: "left",
  fontSize: "11px",
  fontWeight: "600",
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
};

const tdStyle = {
  padding: "8px 10px",
  color: "#e2e8f0",
};

const tdStyleR = {
  padding: "8px 10px",
  color: "#e2e8f0",
  textAlign: "right",
};

const liveBadge = {
  display: "inline-block",
  fontSize: "11px",
  fontWeight: "600",
  padding: "4px 10px",
  borderRadius: "6px",
  background: "rgba(34,197,94,0.12)",
  color: "#22C55E",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};

function fmt(n) {
  if (n == null) return "\u2014";
  if (typeof n !== "number") return "\u2014";
  if (n < 0) return `-$${Math.abs(n).toLocaleString()}`;
  return `$${n.toLocaleString()}`;
}

function StatCard({ label, value, sub, accent }) {
  return (
    <div style={cardStyle}>
      <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>{label}</div>
      <div style={{ fontSize: "22px", fontWeight: "700", color: accent || "#e2e8f0" }}>{value}</div>
      {sub && <div style={{ fontSize: "11px", color: "#475569", marginTop: "2px" }}>{sub}</div>}
    </div>
  );
}
