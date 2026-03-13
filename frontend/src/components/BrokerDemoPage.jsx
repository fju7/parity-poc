import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";

// ─── Sample clients (from BrokerLandingPage) ────────────────────────────────
const SAMPLE_CLIENTS = [
  { id: 1, name: "Midwest Manufacturing Co.", employees: 340, state: "IL", carrier: "Cigna", renewal: "Apr 2026", pepm: 612, benchmarkPepm: 485, excessPct: 26, annualExcess: 51816 },
  { id: 2, name: "Prairie Logistics Group", employees: 185, state: "MO", carrier: "BCBS", renewal: "Jun 2026", pepm: 548, benchmarkPepm: 510, excessPct: 7, annualExcess: 8436 },
  { id: 3, name: "Lakeview Financial Partners", employees: 92, state: "WI", carrier: "UnitedHealth", renewal: "Mar 2026", pepm: 735, benchmarkPepm: 520, excessPct: 41, annualExcess: 23736 },
  { id: 4, name: "Summit Construction LLC", employees: 210, state: "IN", carrier: "Aetna", renewal: "Aug 2026", pepm: 580, benchmarkPepm: 495, excessPct: 17, annualExcess: 21420 },
  { id: 5, name: "Heartland Retail Group", employees: 425, state: "OH", carrier: "BCBS", renewal: "Dec 2026", pepm: 498, benchmarkPepm: 470, excessPct: 6, annualExcess: 14280 },
];

const STEP_LABELS = ["Your Book of Business", "The Findings", "Renewal Prep Report", "CAA Data Request Letter"];

export default function BrokerDemoPage() {
  const [step, setStep] = useState(0);

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "'Inter', -apple-system, sans-serif" }}>
      {/* Header */}
      <header style={{ background: "#1B3A5C", padding: "14px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Link to="/" style={{ color: "#fff", fontSize: 18, fontWeight: 700, textDecoration: "none", letterSpacing: "-0.01em" }}>
          CivicScale
        </Link>
        <a href="https://broker.civicscale.ai/signup" style={{ background: "#0D7377", color: "#fff", padding: "8px 20px", borderRadius: 8, fontWeight: 600, fontSize: 14, textDecoration: "none" }}>
          Sign Up Free &rarr;
        </a>
      </header>

      {/* Progress bar */}
      <div style={{ background: "#e2e8f0", height: 4 }}>
        <div style={{ height: 4, background: "#0D7377", transition: "width 0.4s ease", width: `${((step + 1) / 4) * 100}%` }} />
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: 32, padding: "12px 24px", background: "#fff", borderBottom: "1px solid #e2e8f0" }}>
        {STEP_LABELS.map((label, i) => (
          <button
            key={i}
            onClick={() => setStep(i)}
            style={{
              background: "none", border: "none", cursor: "pointer", padding: "4px 0",
              fontSize: 13, fontWeight: step === i ? 600 : 400,
              color: step === i ? "#0D7377" : i < step ? "#475569" : "#94a3b8",
              borderBottom: step === i ? "2px solid #0D7377" : "2px solid transparent",
            }}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px" }}>
        <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 24px", textAlign: "right" }}>Step {step + 1} of 4</p>

        {step === 0 && <StepBook onNext={() => setStep(1)} />}
        {step === 1 && <StepFindings onNext={() => setStep(2)} onBack={() => setStep(0)} />}
        {step === 2 && <StepReport onNext={() => setStep(3)} onBack={() => setStep(1)} />}
        {step === 3 && <StepLetter onBack={() => setStep(2)} />}
      </div>
    </div>
  );
}

// ─── Step 1: Your Book of Business ───────────────────────────────────────────
function StepBook({ onNext }) {
  return (
    <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 32 }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 6px" }}>See your entire book — benchmarked, at a glance</h2>
      <p style={{ fontSize: 15, color: "#64748b", margin: "0 0 24px", lineHeight: 1.6 }}>Every client compared to their peers. Renewal dates tracked. Gaps quantified.</p>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
              {["Company", "Employees", "Carrier", "PEPM vs Benchmark", "Annual Gap", "Renewal"].map(h => (
                <th key={h} style={{ textAlign: "left", padding: "10px 12px", fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SAMPLE_CLIENTS.map(c => {
              const isMidwest = c.id === 1;
              const badgeColor = c.excessPct > 25 ? "#dc2626" : c.excessPct > 10 ? "#f59e0b" : "#22c55e";
              const badgeBg = c.excessPct > 25 ? "#fef2f2" : c.excessPct > 10 ? "#fffbeb" : "#f0fdf4";
              return (
                <tr key={c.id} style={{ borderBottom: "1px solid #f1f5f9", background: isMidwest ? "#fffbeb" : "transparent", border: isMidwest ? "2px solid #fbbf24" : undefined }}>
                  <td style={{ padding: "12px", fontWeight: 600, color: "#1B3A5C" }}>{c.name}</td>
                  <td style={{ padding: "12px", color: "#475569" }}>{c.employees}</td>
                  <td style={{ padding: "12px", color: "#475569" }}>{c.carrier}</td>
                  <td style={{ padding: "12px" }}>
                    <span style={{ display: "inline-block", padding: "2px 10px", borderRadius: 10, background: badgeBg, color: badgeColor, fontWeight: 600, fontSize: 13 }}>
                      {c.excessPct > 0 ? "+" : ""}{c.excessPct}%
                    </span>
                  </td>
                  <td style={{ padding: "12px", fontWeight: 600, color: "#1B3A5C" }}>${c.annualExcess.toLocaleString()}</td>
                  <td style={{ padding: "12px", color: "#475569" }}>{c.renewal}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: "14px 20px", marginTop: 24 }}>
        <p style={{ margin: 0, fontSize: 14, color: "#92400e", lineHeight: 1.6 }}>
          <strong>Midwest Manufacturing Co.</strong> is 26% above benchmark — <strong>$51,816 in potential excess identified</strong>. Let's look closer.
        </p>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 24 }}>
        <button onClick={onNext} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          See the findings &rarr;
        </button>
      </div>
    </div>
  );
}

// ─── Step 2: The Findings ────────────────────────────────────────────────────
function StepFindings({ onNext, onBack }) {
  const claimsData = [
    { cpt: "99214", procedure: "Office visit, moderate complexity", paid: "$340", medicare: "$187", markup: "1.82\u00D7", flag: "HIGH" },
    { cpt: "93000", procedure: "Electrocardiogram, 12-lead", paid: "$310", medicare: "$148", markup: "2.09\u00D7", flag: "SEVERE" },
    { cpt: "85025", procedure: "Complete blood count, automated", paid: "$42", medicare: "$8", markup: "5.25\u00D7", flag: "SEVERE" },
  ];

  const pharmaData = [
    { drug: "Omeprazole 20mg", paid: "$22.30", nadac: "$3.92", markup: "469%" },
    { drug: "Gabapentin 300mg", paid: "$32.40", nadac: "$8.55", markup: "279%" },
  ];

  return (
    <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 32 }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 6px" }}>What your carrier isn't telling you</h2>
      <p style={{ fontSize: 15, color: "#64748b", margin: "0 0 24px" }}>Midwest Manufacturing Co. &middot; 340 employees &middot; Cigna &middot; Illinois</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 24 }}>
        {/* Claims Findings */}
        <div style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Claims Findings</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #e2e8f0" }}>
                {["CPT", "Procedure", "Paid", "Medicare", "Markup", "Flag"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "6px 8px", fontSize: 11, fontWeight: 600, color: "#64748b" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {claimsData.map(r => (
                <tr key={r.cpt} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "8px", fontWeight: 600, color: "#475569" }}>{r.cpt}</td>
                  <td style={{ padding: "8px", color: "#475569", fontSize: 12 }}>{r.procedure}</td>
                  <td style={{ padding: "8px", color: "#475569" }}>{r.paid}</td>
                  <td style={{ padding: "8px", color: "#475569" }}>{r.medicare}</td>
                  <td style={{ padding: "8px", fontWeight: 600, color: "#1B3A5C" }}>{r.markup}</td>
                  <td style={{ padding: "8px" }}>
                    <span style={{
                      fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6,
                      background: r.flag === "SEVERE" ? "#fef2f2" : "#fffbeb",
                      color: r.flag === "SEVERE" ? "#dc2626" : "#92400e",
                    }}>{r.flag}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ margin: "16px 0 0", fontSize: 14, color: "#1B3A5C", fontWeight: 600 }}>
            Total excess vs. 2&times; Medicare benchmark: <span style={{ color: "#dc2626" }}>$51,816/year</span>
          </p>
        </div>

        {/* Pharmacy Findings */}
        <div style={{ border: "1px solid #e2e8f0", borderRadius: 10, padding: 20 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Pharmacy Findings</h3>
          {pharmaData.map(d => (
            <div key={d.drug} style={{ background: "#f8fafc", borderRadius: 8, padding: "12px 16px", marginBottom: 10 }}>
              <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "#1B3A5C" }}>{d.drug}</p>
              <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 13, color: "#475569" }}>
                <span>Paid: {d.paid}</span>
                <span>NADAC: {d.nadac}</span>
                <span style={{ fontWeight: 600, color: "#dc2626" }}>{d.markup} markup</span>
              </div>
            </div>
          ))}
          <p style={{ margin: "16px 0 0", fontSize: 13, color: "#64748b", lineHeight: 1.6 }}>
            These drug costs are 3–5&times; what the plan should pay. This alone is an easy renewal negotiation point.
          </p>
        </div>
      </div>

      {/* Executive Summary */}
      <div style={{ background: "#1B3A5C", borderRadius: 10, padding: "20px 24px", marginBottom: 24 }}>
        <p style={{ margin: 0, fontSize: 14, color: "#e2e8f0", lineHeight: 1.8, fontStyle: "italic" }}>
          "Midwest Manufacturing's plan is paying Cigna's network rates at 82–525% above Medicare benchmarks on core office procedures. The most actionable finding: CBC lab work (CPT 85025) at 5.25&times; Medicare is a common, high-frequency code — directing employees to any reference lab would recover approximately $8,000–$12,000 annually with no benefit reduction."
        </p>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
        <button onClick={onBack} style={{ background: "#fff", color: "#475569", border: "1px solid #e2e8f0", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          &larr; Back
        </button>
        <button onClick={onNext} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          Generate renewal report &rarr;
        </button>
      </div>
    </div>
  );
}

// ─── Step 3: Renewal Prep Report ─────────────────────────────────────────────
function StepReport({ onNext, onBack }) {
  const [timerDisplay, setTimerDisplay] = useState("3:00:00");
  const timerDone = useRef(false);

  useEffect(() => {
    if (timerDone.current) return;
    timerDone.current = true;
    const totalMs = 2500;
    const startTime = 3 * 60 * 60;
    const endTime = 15;
    const start = Date.now();

    const interval = setInterval(() => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / totalMs, 1);
      // ease-out curve for dramatic countdown
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.max(Math.round(startTime - (startTime - endTime) * eased), endTime);

      const h = Math.floor(current / 3600);
      const m = Math.floor((current % 3600) / 60);
      const s = current % 60;
      setTimerDisplay(`${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`);

      if (progress >= 1) {
        clearInterval(interval);
        setTimerDisplay("0:00:15");
      }
    }, 30);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 32, marginBottom: 24 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 6px" }}>Everything you need for the renewal meeting — in one page</h2>
        <p style={{ fontSize: 15, color: "#64748b", margin: "0 0 24px" }}>Generated in seconds. Branded with your firm. Ready to present.</p>

        {/* Mock report card */}
        <div style={{ border: "1px solid #e2e8f0", borderRadius: 10, overflow: "hidden", boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}>
          <div style={{ background: "#1B3A5C", padding: "14px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ color: "#fff", fontSize: 13, fontWeight: 700, letterSpacing: 1, textTransform: "uppercase" }}>Renewal Prep Report</span>
            <span style={{ color: "#94a3b8", fontSize: 12 }}>Demo Brokerage Partners</span>
          </div>

          <div style={{ padding: 24 }}>
            {/* Client summary */}
            <div style={{ background: "#f8fafc", borderRadius: 8, padding: "12px 16px", marginBottom: 20, display: "flex", flexWrap: "wrap", gap: "4px 20px", fontSize: 13, color: "#475569" }}>
              <span><strong>Midwest Manufacturing</strong></span>
              <span>340 EEs</span>
              <span>IL</span>
              <span>Cigna</span>
              <span>Renewing April 2026</span>
            </div>

            {/* Benchmark */}
            <div style={{ marginBottom: 20 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#64748b", margin: "0 0 6px", textTransform: "uppercase", letterSpacing: 0.5 }}>Benchmark</p>
              <p style={{ margin: 0, fontSize: 14, color: "#1B3A5C", lineHeight: 1.7 }}>
                74th percentile (above median) &middot; $127/mo excess per employee &middot; <strong style={{ color: "#dc2626" }}>$51,816 annual gap</strong>
              </p>
            </div>

            {/* Key findings */}
            <div style={{ marginBottom: 20 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#64748b", margin: "0 0 6px", textTransform: "uppercase", letterSpacing: 0.5 }}>Key Findings</p>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 14, color: "#475569", lineHeight: 1.8 }}>
                <li>CBC lab costs at 5.25&times; Medicare — highest markup in plan</li>
                <li>Office visit E&M codes 82% above benchmark</li>
                <li>PBM drug spread averaging 3–5&times; NADAC acquisition cost</li>
              </ul>
            </div>

            {/* Talking points */}
            <div style={{ marginBottom: 20 }}>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#64748b", margin: "0 0 6px", textTransform: "uppercase", letterSpacing: 0.5 }}>Renewal Talking Points</p>
              <ol style={{ margin: 0, paddingLeft: 18, fontSize: 14, color: "#475569", lineHeight: 1.8 }}>
                <li>Your CBC lab costs are 5&times; Medicare rates — request a lab carve-out or reference-lab option</li>
                <li>Office visit E&M codes are 82% above Medicare — negotiate a fee schedule cap at 175% Medicare</li>
                <li>Pharmacy rebates: Request itemized rebate pass-through accounting from your PBM</li>
                <li>Under CAA Section 204, you have a legal right to all claims data — we're requesting it this week</li>
              </ol>
            </div>

            <p style={{ margin: 0, fontSize: 11, color: "#94a3b8", borderTop: "1px solid #e2e8f0", paddingTop: 12 }}>
              Analysis based on CMS Medicare Physician Fee Schedule 2026 &middot; NADAC pricing &middot; MEPS-IC industry benchmarks
            </p>
          </div>
        </div>

        {/* Timer animation */}
        <div style={{ textAlign: "center", marginTop: 28 }}>
          <p style={{ fontSize: 15, color: "#1B3A5C", fontWeight: 600, margin: "0 0 8px" }}>This report takes 3 hours to build manually. Parity Broker generates it in 15 seconds.</p>
          <p style={{ fontSize: 36, fontWeight: 700, fontFamily: "'Courier New', monospace", color: "#0D7377", margin: 0 }}>{timerDisplay}</p>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <button onClick={onBack} style={{ background: "#fff", color: "#475569", border: "1px solid #e2e8f0", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          &larr; Back
        </button>
        <button onClick={onNext} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          Generate CAA letter &rarr;
        </button>
      </div>
    </div>
  );
}

// ─── Step 4: CAA Data Request Letter ─────────────────────────────────────────
function StepLetter({ onBack }) {
  const [copied, setCopied] = useState(false);
  const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

  const letterText = `${today}

Via Email and Certified Mail

Cigna Group Benefits
Claims Data Request Department
[Carrier Address]

Re: Request for Claims Data Under the Consolidated Appropriations Act
    Plan Sponsor: Midwest Manufacturing Co.
    Group Policy Number: [Policy Number]
    Employer Size: Approximately 340 employees
    Plan Year: 2025–2026

Dear Claims Data Department,

Pursuant to Section 204 of Division BB of the Consolidated Appropriations Act of 2021 (CAA 2021), codified at 29 U.S.C. \u00A7 1185i, and in fulfillment of the fiduciary obligations established under ERISA \u00A7 404(a)(1), I am writing on behalf of our client, Midwest Manufacturing Co., to formally request the following claims data for the current and prior plan year.

As referenced in DOL guidance from November 2021 and EBSA Field Assistance Bulletin 2021-04, plan fiduciaries have an obligation to obtain and evaluate plan cost information. This request supports that obligation.

1. MEDICAL CLAIMS DATA
   \u2014 Complete 835 Electronic Remittance Advice files for current and prior plan year
   \u2014 Allowed amounts, billed amounts, and paid amounts by CPT/HCPCS code
   \u2014 Provider-level detail including NPI, facility type, and network status

2. PHARMACY CLAIMS DATA
   \u2014 All prescription claims including NDC codes, quantities dispensed, and amounts paid
   \u2014 Ingredient cost, dispensing fees, and any applicable rebate credits applied
   \u2014 Generic/brand classification and therapeutic class

3. PLAN COST SUMMARY
   \u2014 Monthly PEPM cost broken down by medical, pharmacy, and administrative fees
   \u2014 Stop-loss premiums and attachment points
   \u2014 Network access fees and other plan-level charges

Please provide the requested data in electronic format (835 EDI preferred for medical claims, CSV acceptable for pharmacy) within 30 business days, consistent with the carrier's contractual obligations under the service agreement.

As the broker of record for Midwest Manufacturing Co., I am authorized to receive this information on behalf of the plan sponsor. If you have questions regarding this request, please contact me directly at the information below.

Sincerely,
Sarah Thompson
Demo Brokerage Partners
[Email]
[Phone]

cc: Midwest Manufacturing Co., Benefits Director`;

  return (
    <div>
      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 32, marginBottom: 24 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 6px" }}>Your legal right to the data — drafted and ready</h2>
        <p style={{ fontSize: 15, color: "#64748b", margin: "0 0 24px" }}>One click. Attorney-quality language. Specific to this carrier and client.</p>

        {/* Letter display */}
        <div style={{
          background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, padding: "32px 40px",
          fontFamily: "'Georgia', serif", fontSize: 14, lineHeight: 1.8, color: "#1e293b",
          maxHeight: 500, overflowY: "auto", boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
          whiteSpace: "pre-wrap",
        }}>
          {letterText}
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
          <button
            onClick={() => { setCopied(true); try { navigator.clipboard.writeText(letterText); } catch {} setTimeout(() => setCopied(false), 2000); }}
            style={{ padding: "8px 20px", border: "1px solid #e2e8f0", borderRadius: 8, background: "#fff", fontSize: 13, fontWeight: 600, color: "#475569", cursor: "pointer" }}
          >
            {copied ? "Copied!" : "Copy Letter"}
          </button>
          <a href="https://broker.civicscale.ai/signup" style={{ display: "inline-flex", alignItems: "center", padding: "8px 20px", background: "#0D7377", color: "#fff", borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: "none" }}>
            Sign Up to Use This &rarr;
          </a>
        </div>
      </div>

      {/* What you just saw */}
      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 24, marginBottom: 24 }}>
        <p style={{ fontSize: 16, fontWeight: 700, color: "#1B3A5C", margin: "0 0 12px" }}>What you just saw:</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
          {[
            "7 clients benchmarked",
            "Claims analysis: $51,816 excess identified",
            "Renewal prep report generated",
            "CAA letter drafted",
          ].map((item, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ color: "#22c55e", fontWeight: 700 }}>✓</span>
              <span style={{ fontSize: 14, color: "#475569" }}>{item}</span>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 15, fontWeight: 600, color: "#1B3A5C", margin: 0 }}>
          Time in a real workflow: 3+ hours. Time with Parity Broker: about 15 minutes.
        </p>
      </div>

      {/* Final CTA */}
      <div style={{ background: "#0D7377", borderRadius: 12, padding: "40px 32px", textAlign: "center" }}>
        <p style={{ fontSize: 22, fontWeight: 700, color: "#fff", margin: "0 0 20px" }}>
          Ready to run this on your actual book of business?
        </p>
        <a href="https://broker.civicscale.ai/signup" style={{ display: "inline-block", background: "#fff", color: "#0D7377", padding: "14px 36px", borderRadius: 10, fontWeight: 700, fontSize: 16, textDecoration: "none" }}>
          Start Free — No Credit Card Required
        </a>
        <p style={{ fontSize: 13, color: "rgba(255,255,255,0.7)", marginTop: 12 }}>Setup takes 10 minutes. First benchmark is free.</p>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-start", marginTop: 24 }}>
        <button onClick={onBack} style={{ background: "#fff", color: "#475569", border: "1px solid #e2e8f0", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          &larr; Back
        </button>
      </div>
    </div>
  );
}
