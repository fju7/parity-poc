import { useState } from "react";
import { Link } from "react-router-dom";

const STEP_LABELS = [
  "Industry Benchmark",
  "Claims Analysis",
  "Pharmacy Analysis",
  "Action Plan",
];

export default function EmployerDemoPage() {
  const [step, setStep] = useState(0);

  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "'Inter', -apple-system, sans-serif" }}>
      {/* Header */}
      <header style={{ background: "#1e3a5f", padding: "14px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Link to="/" style={{ color: "#fff", fontSize: 18, fontWeight: 700, textDecoration: "none", letterSpacing: "-0.01em" }}>
          CivicScale
        </Link>
        <a
          href="https://employer.civicscale.ai/signup"
          style={{ background: "#0d9488", color: "#fff", padding: "8px 20px", borderRadius: 8, fontWeight: 600, fontSize: 14, textDecoration: "none" }}
        >
          Sign Up Free &rarr;
        </a>
      </header>

      {/* Progress bar */}
      <div style={{ background: "#e2e8f0", height: 4 }}>
        <div style={{ height: 4, background: "#0d9488", transition: "width 0.4s ease", width: `${((step + 1) / 4) * 100}%` }} />
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: 32, padding: "12px 24px", background: "#fff", borderBottom: "1px solid #e2e8f0" }}>
        {STEP_LABELS.map((label, i) => (
          <button
            key={i}
            onClick={() => setStep(i)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: "4px 0",
              fontSize: 13,
              fontWeight: step === i ? 600 : 400,
              color: step === i ? "#0d9488" : i < step ? "#475569" : "#94a3b8",
              borderBottom: step === i ? "2px solid #0d9488" : "2px solid transparent",
            }}
          >
            {i + 1}. {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px" }}>
        <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 24px", textAlign: "right" }}>Step {step + 1} of 4</p>

        {step === 0 && <StepBenchmark onNext={() => setStep(1)} />}
        {step === 1 && <StepClaims onNext={() => setStep(2)} onBack={() => setStep(0)} />}
        {step === 2 && <StepPharmacy onNext={() => setStep(3)} onBack={() => setStep(1)} />}
        {step === 3 && <StepActionPlan onBack={() => setStep(2)} />}
      </div>
    </div>
  );
}

/* ─── Shared styles ─────────────────────────────────────────────────────────── */

const card = {
  background: "#fff",
  borderRadius: 12,
  border: "1px solid #e2e8f0",
  padding: 32,
};

const heading = {
  fontSize: 24,
  fontWeight: 700,
  color: "#1e3a5f",
  margin: "0 0 6px",
};

const subtitle = {
  fontSize: 15,
  color: "#64748b",
  margin: "0 0 24px",
  lineHeight: 1.6,
};

const btnNext = {
  background: "#0d9488",
  color: "#fff",
  border: "none",
  padding: "12px 28px",
  borderRadius: 8,
  fontWeight: 600,
  fontSize: 15,
  cursor: "pointer",
};

const btnBack = {
  background: "none",
  color: "#64748b",
  border: "1px solid #e2e8f0",
  padding: "12px 28px",
  borderRadius: 8,
  fontWeight: 500,
  fontSize: 15,
  cursor: "pointer",
};

const navRow = {
  display: "flex",
  justifyContent: "space-between",
  marginTop: 32,
};

/* ─── Step 1: Industry Benchmark ────────────────────────────────────────────── */

const BENCHMARK_METRICS = [
  { label: "Your PEPM", value: "$485", benchmark: "$412", benchmarkLabel: "Industry Average", gap: "+17.7%", gapNote: "above average" },
  { label: "Your Pharmacy PEPM", value: "$89", benchmark: "$71", benchmarkLabel: "Industry Average", gap: "+25.4%", gapNote: "above average" },
];

function StepBenchmark({ onNext }) {
  return (
    <div style={card}>
      <h2 style={heading}>See How Your Plan Compares</h2>
      <p style={subtitle}>Benchmark comparison for a mid-size manufacturing company — 500 employees, Ohio.</p>

      {/* Metric cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
        {BENCHMARK_METRICS.map((m) => (
          <div key={m.label} style={{ background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0", padding: 20 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5, margin: "0 0 8px" }}>{m.label}</p>
            <p style={{ fontSize: 32, fontWeight: 700, color: "#1e3a5f", margin: "0 0 12px" }}>{m.value}</p>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 13, color: "#64748b" }}>{m.benchmarkLabel}: <strong>{m.benchmark}</strong></span>
              <span style={{
                fontSize: 13,
                fontWeight: 600,
                color: "#dc2626",
                background: "#fef2f2",
                padding: "3px 10px",
                borderRadius: 20,
              }}>
                {m.gap} {m.gapNote}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Overall Score */}
      <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10, padding: 20, display: "flex", alignItems: "center", gap: 20, marginBottom: 24 }}>
        <div style={{
          width: 56,
          height: 56,
          borderRadius: "50%",
          background: "#f59e0b",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 22,
          fontWeight: 800,
          color: "#fff",
          flexShrink: 0,
        }}>
          C+
        </div>
        <div>
          <p style={{ fontSize: 16, fontWeight: 600, color: "#92400e", margin: "0 0 4px" }}>Overall Score: C+</p>
          <p style={{ fontSize: 14, color: "#92400e", margin: 0 }}>Room for improvement — your plan is paying significantly above industry benchmarks in multiple categories.</p>
        </div>
      </div>

      {/* Disclaimer */}
      <p style={{ fontSize: 13, color: "#94a3b8", fontStyle: "italic", margin: "0 0 0" }}>
        Sample data shown. Your actual results will vary based on your claims upload.
      </p>

      <div style={{ ...navRow, justifyContent: "flex-end" }}>
        <button style={btnNext} onClick={onNext}>Next &rarr;</button>
      </div>
    </div>
  );
}

/* ─── Step 2: Claims Analysis ───────────────────────────────────────────────── */

const FLAGGED_CLAIMS = [
  { cpt: "99214", desc: "Office Visit", billed: "$285", medicare: "$148", variance: "+92%", flag: "HIGH" },
  { cpt: "27447", desc: "Knee Replacement", billed: "$42,500", medicare: "$8,912", variance: "+376%", flag: "CRITICAL" },
  { cpt: "93000", desc: "EKG", billed: "$185", medicare: "$19", variance: "+874%", flag: "CRITICAL" },
  { cpt: "80053", desc: "Metabolic Panel", billed: "$245", medicare: "$14", variance: "+1,650%", flag: "CRITICAL" },
  { cpt: "71046", desc: "Chest X-Ray", billed: "$380", medicare: "$42", variance: "+805%", flag: "CRITICAL" },
];

function flagColor(flag) {
  return flag === "CRITICAL"
    ? { bg: "#fef2f2", text: "#dc2626" }
    : { bg: "#fffbeb", text: "#d97706" };
}

function StepClaims({ onNext, onBack }) {
  return (
    <div style={card}>
      <h2 style={heading}>Flagged Billing Anomalies in Your Claims</h2>
      <p style={subtitle}>These CPT codes show the widest gap between what was billed and what Medicare would reimburse.</p>

      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
              {["CPT", "Description", "Billed", "Medicare Rate", "Variance", "Flag"].map((h) => (
                <th key={h} style={{ textAlign: "left", padding: "10px 12px", fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: 0.5 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FLAGGED_CLAIMS.map((c) => {
              const fc = flagColor(c.flag);
              return (
                <tr key={c.cpt} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "12px 12px", fontWeight: 600, color: "#1e3a5f" }}>{c.cpt}</td>
                  <td style={{ padding: "12px 12px", color: "#475569" }}>{c.desc}</td>
                  <td style={{ padding: "12px 12px", color: "#1e3a5f", fontWeight: 500 }}>{c.billed}</td>
                  <td style={{ padding: "12px 12px", color: "#64748b" }}>{c.medicare}</td>
                  <td style={{ padding: "12px 12px", fontWeight: 600, color: "#dc2626" }}>{c.variance}</td>
                  <td style={{ padding: "12px 12px" }}>
                    <span style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: fc.text,
                      background: fc.bg,
                      padding: "3px 10px",
                      borderRadius: 20,
                      textTransform: "uppercase",
                      letterSpacing: 0.5,
                    }}>
                      {c.flag}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary bar */}
      <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 10, padding: "16px 20px", marginTop: 24, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <span style={{ fontSize: 14, color: "#0f766e", fontWeight: 500 }}>5 of 847 claims flagged</span>
        <span style={{ fontSize: 16, fontWeight: 700, color: "#0d9488" }}>Estimated recoverable: $127,400 annually</span>
      </div>

      <div style={navRow}>
        <button style={btnBack} onClick={onBack}>&larr; Back</button>
        <button style={btnNext} onClick={onNext}>Next &rarr;</button>
      </div>
    </div>
  );
}

/* ─── Step 3: Pharmacy NADAC Analysis ───────────────────────────────────────── */

const PHARMACY_DRUGS = [
  { name: "Metformin 1000mg", yourCost: "$48.50", nadac: "$4.20", markup: "1,055%" },
  { name: "Lisinopril 10mg", yourCost: "$32.00", nadac: "$2.80", markup: "1,043%" },
  { name: "Atorvastatin 40mg", yourCost: "$156.00", nadac: "$8.90", markup: "1,652%" },
  { name: "Omeprazole 20mg", yourCost: "$89.00", nadac: "$5.40", markup: "1,548%" },
];

function StepPharmacy({ onNext, onBack }) {
  return (
    <div style={card}>
      <h2 style={heading}>Your Pharmacy Costs vs. Acquisition Price</h2>
      <p style={subtitle}>Comparing what your plan pays for common generics against the National Average Drug Acquisition Cost (NADAC).</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
        {PHARMACY_DRUGS.map((d) => (
          <div key={d.name} style={{ background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0", padding: 20 }}>
            <p style={{ fontSize: 14, fontWeight: 600, color: "#1e3a5f", margin: "0 0 12px" }}>{d.name}</p>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <div>
                <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 2px", textTransform: "uppercase", letterSpacing: 0.5 }}>Your Cost</p>
                <p style={{ fontSize: 22, fontWeight: 700, color: "#1e3a5f", margin: 0 }}>{d.yourCost}</p>
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 2px", textTransform: "uppercase", letterSpacing: 0.5 }}>NADAC</p>
                <p style={{ fontSize: 22, fontWeight: 700, color: "#0d9488", margin: 0 }}>{d.nadac}</p>
              </div>
            </div>
            <div style={{ background: "#fef2f2", borderRadius: 6, padding: "6px 12px", textAlign: "center" }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: "#dc2626" }}>{d.markup} markup</span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary bar */}
      <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 10, padding: "16px 20px", display: "flex", justifyContent: "center", alignItems: "center" }}>
        <span style={{ fontSize: 16, fontWeight: 700, color: "#0d9488" }}>Estimated pharmacy savings opportunity: $43,200 annually</span>
      </div>

      <div style={navRow}>
        <button style={btnBack} onClick={onBack}>&larr; Back</button>
        <button style={btnNext} onClick={onNext}>Next &rarr;</button>
      </div>
    </div>
  );
}

/* ─── Step 4: Action Plan ───────────────────────────────────────────────────── */

const ACTION_ITEMS = [
  {
    number: 1,
    title: "Ask your broker",
    text: "What is our actual paid-to-billed ratio for the top 20 CPT codes, and how does it compare to Medicare benchmarks?",
  },
  {
    number: 2,
    title: "Request from your TPA",
    text: "A line-item claims report showing all claims over $10,000 with the corresponding contracted rates.",
  },
  {
    number: 3,
    title: "Demand transparency",
    text: "Under the CAA, you have the right to your full claims data. Request a machine-readable file of all 2024 claims.",
  },
];

function StepActionPlan({ onBack }) {
  return (
    <div style={card}>
      <h2 style={heading}>Your 3-Step Action Plan</h2>
      <p style={subtitle}>Start holding your health plan accountable — these three questions will change the conversation with your broker and TPA.</p>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 32 }}>
        {ACTION_ITEMS.map((item) => (
          <div key={item.number} style={{ background: "#f0fdfa", border: "1px solid #ccfbf1", borderRadius: 12, padding: 24, display: "flex", gap: 20, alignItems: "flex-start" }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              background: "#0d9488",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 18,
              fontWeight: 700,
              color: "#fff",
              flexShrink: 0,
            }}>
              {item.number}
            </div>
            <div>
              <p style={{ fontSize: 15, fontWeight: 700, color: "#0f766e", margin: "0 0 6px" }}>{item.title}</p>
              <p style={{ fontSize: 15, color: "#1e3a5f", margin: 0, lineHeight: 1.6 }}>{item.text}</p>
            </div>
          </div>
        ))}
      </div>

      {/* CTA section */}
      <div style={{
        background: "linear-gradient(135deg, #1e3a5f 0%, #0f766e 100%)",
        borderRadius: 12,
        padding: 32,
        textAlign: "center",
        marginBottom: 8,
      }}>
        <p style={{ fontSize: 20, fontWeight: 700, color: "#fff", margin: "0 0 8px" }}>Ready to see your real data?</p>
        <p style={{ fontSize: 15, color: "#cbd5e1", margin: "0 0 24px" }}>Start your free 30-day trial.</p>
        <a
          href="https://employer.civicscale.ai/signup"
          style={{
            display: "inline-block",
            background: "#0d9488",
            color: "#fff",
            padding: "14px 36px",
            borderRadius: 8,
            fontWeight: 700,
            fontSize: 16,
            textDecoration: "none",
          }}
        >
          Upload Your Claims Data &rarr;
        </a>
      </div>

      <div style={{ ...navRow, justifyContent: "flex-start" }}>
        <button style={btnBack} onClick={onBack}>&larr; Back</button>
      </div>
    </div>
  );
}
