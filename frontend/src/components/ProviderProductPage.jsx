import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";



// ─── Component ───────────────────────────────────────────────────────────────
export default function ProviderProductPage() {
  const { isAuthenticated, company } = useAuth();

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
              <a href="https://provider.civicscale.ai/provider/login" style={{ color: "#94a3b8", textDecoration: "none", fontWeight: 500 }}>Sign In</a>
              <a href="https://provider.civicscale.ai/provider/signup" style={{ background: "#3b82f6", color: "#fff", textDecoration: "none", borderRadius: 6, padding: "8px 20px", fontWeight: 500, fontSize: 14 }}>
                Start Free Trial
              </a>
            </>
          )}
        </nav>
      </header>

      {/* ── Section 1: Hero ── */}
      <section style={{ paddingTop: 120, paddingBottom: 56, maxWidth: 820, margin: "0 auto", textAlign: "center", padding: "120px 24px 56px" }}>
        <div style={{ display: "inline-block", background: "rgba(13,148,136,0.12)", borderRadius: 8, padding: "8px 14px", marginBottom: 24 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#0d9488" }}>PARITY PROVIDER</span>
        </div>
        <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(30px, 4vw, 46px)", lineHeight: 1.15, fontWeight: 400, color: "#f1f5f9", marginBottom: 12, letterSpacing: "-0.02em" }}>
          See the money your payers owe you.<br />
          <span style={{ color: "#0d9488" }}>In 5 minutes.</span>
        </h1>
        <p style={{ fontSize: 17, lineHeight: 1.7, color: "#94a3b8", maxWidth: 700, margin: "0 auto 32px" }}>
          Upload your 835 remittance file and Parity Provider automatically identifies underpayments, denial patterns, and coding gaps &mdash; with specific dollar amounts and a PDF you can act on today.
        </p>

        {/* Proof points */}
        <div style={{ display: "flex", gap: 32, justifyContent: "center", flexWrap: "wrap", marginBottom: 32 }}>
          <div style={{ textAlign: "center", maxWidth: 200 }}>
            <div style={{ width: 40, height: 40, borderRadius: "50%", background: "rgba(13,148,136,0.15)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 8px" }}>
              <span style={{ fontSize: 18, color: "#0d9488" }}>$</span>
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9" }}>11%</div>
            <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.4 }}>Average commercial payer denial rate (CAQH Index 2024)</div>
          </div>
          <div style={{ textAlign: "center", maxWidth: 200 }}>
            <div style={{ width: 40, height: 40, borderRadius: "50%", background: "rgba(13,148,136,0.15)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 8px" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0d9488" strokeWidth="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9" }}>$42K</div>
            <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.4 }}>Median annual underpayment found per 3-provider practice</div>
            <div style={{ fontSize: 10, color: "#64748b", marginTop: 2, fontStyle: "italic" }}>(internal estimate from sample remittance data)</div>
          </div>
          <div style={{ textAlign: "center", maxWidth: 200 }}>
            <div style={{ width: 40, height: 40, borderRadius: "50%", background: "rgba(13,148,136,0.15)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 8px" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0d9488" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9" }}>5 min</div>
            <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.4 }}>From 835 upload to full revenue gap report</div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/provider/signup" style={{ display: "inline-block", background: "#0d9488", color: "#fff", padding: "14px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            Start Free Trial &mdash; Upload Your 835
          </Link>
          <Link to="/provider/demo" style={{ display: "inline-block", border: "1px solid rgba(13,148,136,0.4)", color: "#0d9488", padding: "14px 28px", borderRadius: 8, fontWeight: 600, fontSize: 15, textDecoration: "none" }}>
            See a Live Demo &rarr;
          </Link>
        </div>
        <p style={{ fontSize: 13, color: "#64748b", marginTop: 16 }}>30-day free trial, cancel anytime</p>
      </section>

      {/* ── Section 1b: How It Works ── */}
      <section style={{ padding: "0 24px 72px", maxWidth: 820, margin: "0 auto" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", textAlign: "center", marginBottom: 32 }}>
          From file to findings in 3 steps
        </h2>
        <div style={{ display: "flex", gap: 24, justifyContent: "center", flexWrap: "wrap" }}>
          {[
            { num: "1", title: "Upload your 835", desc: "Drag and drop your Electronic Remittance Advice file. We accept single files, batches, and ZIP archives." },
            { num: "2", title: "Add your contract rates", desc: "Enter rates as % of Medicare, upload your fee schedule PDF, or paste from your payer portal — we extract the numbers automatically." },
            { num: "3", title: "Review your report", desc: "See underpayments flagged by claim, denial rates vs. industry benchmarks, coding gaps by specialty, and a one-page PDF to share with your physician." },
          ].map((step) => (
            <div key={step.num} style={{ flex: "1 1 220px", maxWidth: 260, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "24px 20px" }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#0d9488", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 15, marginBottom: 12 }}>{step.num}</div>
              <div style={{ fontSize: 15, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>{step.title}</div>
              <div style={{ fontSize: 13, lineHeight: 1.6, color: "#94a3b8" }}>{step.desc}</div>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 11, color: "#64748b", textAlign: "center", marginTop: 24, fontStyle: "italic", maxWidth: 700, margin: "24px auto 0" }}>
          Benchmark comparisons use publicly available CMS Medicare Physician Fee Schedule data and published CAQH/Change Healthcare industry reports. No PHI is stored — analysis is performed in-memory on your uploaded files.
        </p>
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

      {/* ── Section 3: What You Get ── */}
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
            30-day free trial, cancel anytime
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
