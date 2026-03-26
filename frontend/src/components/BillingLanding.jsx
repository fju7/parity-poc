import { Link } from "react-router-dom";

const PAIN_POINTS = [
  {
    title: "You're managing practices one at a time.",
    body: "The same CO-4 denial appearing across 12 of your practices is invisible until you see the portfolio. We surface it automatically.",
  },
  {
    title: "Your clients renew based on results they can see.",
    body: "If you can't show a practice what you recovered last quarter, you're competing on price. Branded monthly reports change that conversation.",
  },
  {
    title: "Payer contracts change quietly.",
    body: "A rate reduction buried in a contract amendment costs a practice thousands before anyone notices. Multiply that across your portfolio.",
  },
];

const CAPABILITIES = [
  {
    icon: "📊",
    title: "Portfolio Denial Dashboard",
    body: "Aggregate denial rates, payer adherence, and top denial codes across all managed practices in a single view. Filter by specialty, practice, or date range.",
  },
  {
    icon: "🔍",
    title: "Cross-Practice Payer Benchmarking",
    body: "Identify when a payer is systematically denying a specific code across multiple practices. One coordinated escalation instead of 20 separate appeals.",
  },
  {
    icon: "📄",
    title: "White-Label Client Reports",
    body: "Branded PDF reports with your company name and logo. Send every practice a monthly summary of what you recovered on their behalf.",
  },
  {
    icon: "🔐",
    title: "Practice Client Portal",
    body: "Give each practice read-only access to their own data. Most billing companies can't offer this. You can.",
  },
];

const TIERS = [
  { name: "Free", price: "$0", period: "", practices: "First practice, full features", highlight: false },
  { name: "Starter", price: "$299", period: "/mo", practices: "Up to 10 practices", highlight: true },
  { name: "Growth", price: "$699", period: "/mo", practices: "Up to 30 practices", highlight: false },
  { name: "Enterprise", price: "Custom", period: "", practices: "Unlimited", highlight: false },
];

export default function BillingLanding() {
  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* Header */}
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: 64, display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.92)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: 12, textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" }}>CivicScale</span>
        </a>
        <nav style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 14 }}>
          <a href="https://billing.civicscale.ai/login" style={{ color: "#94a3b8", textDecoration: "none", fontWeight: 500 }}>Sign In</a>
          <a href="https://billing.civicscale.ai" style={{ background: "#3b82f6", color: "#fff", textDecoration: "none", borderRadius: 6, padding: "8px 20px", fontWeight: 500, fontSize: 14 }}>
            Start Free
          </a>
        </nav>
      </header>

      {/* Hero */}
      <section style={{ paddingTop: 120, paddingBottom: 56, maxWidth: 820, margin: "0 auto", textAlign: "center", padding: "120px 24px 56px" }}>
        <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: 8, padding: "8px 14px", marginBottom: 24 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#60a5fa" }}>PARITY BILLING</span>
        </div>
        <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(28px, 4vw, 44px)", lineHeight: 1.15, fontWeight: 400, color: "#f1f5f9", marginBottom: 16, letterSpacing: "-0.02em" }}>
          Your clients think you're<br />catching everything.{" "}
          <span style={{ color: "#60a5fa" }}>Are you?</span>
        </h1>
        <p style={{ fontSize: 17, lineHeight: 1.7, color: "#94a3b8", maxWidth: 700, margin: "0 auto 32px" }}>
          Parity Billing gives revenue cycle management companies the portfolio intelligence
          to find systematic payer underpayment that no individual practice can see &mdash;
          and prove their value to every client they manage.
        </p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/billing/demo" style={{ background: "linear-gradient(135deg, #3b82f6, #60a5fa)", color: "#fff", textDecoration: "none", borderRadius: 8, padding: "12px 28px", fontWeight: 600, fontSize: 15 }}>
            See a Demo
          </Link>
          <a href="https://billing.civicscale.ai" style={{ border: "1px solid rgba(255,255,255,0.15)", color: "#e2e8f0", textDecoration: "none", borderRadius: 8, padding: "12px 28px", fontWeight: 500, fontSize: 15 }}>
            Start Free
          </a>
        </div>
      </section>

      {/* Pain Points */}
      <section style={{ padding: "64px 24px", maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#60a5fa", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>THE PROBLEM</div>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(24px, 3vw, 36px)", fontWeight: 400, color: "#f1f5f9", letterSpacing: "-0.02em" }}>
            The portfolio view no one else has
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
          {PAIN_POINTS.map(p => (
            <div key={p.title} style={{
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 12, padding: 28,
            }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", marginBottom: 12, marginTop: 0 }}>{p.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8", margin: 0 }}>{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section style={{ padding: "64px 24px", maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#60a5fa", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>WHAT YOU GET</div>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(24px, 3vw, 36px)", fontWeight: 400, color: "#f1f5f9", letterSpacing: "-0.02em" }}>
            Four capabilities that change how you compete
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
          {CAPABILITIES.map(c => (
            <div key={c.title} style={{
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(59,130,246,0.15)",
              borderRadius: 12, padding: 28, transition: "border-color 0.2s, transform 0.2s",
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "rgba(59,130,246,0.35)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(59,130,246,0.15)"; e.currentTarget.style.transform = "none"; }}
            >
              <div style={{ fontSize: 28, marginBottom: 12 }}>{c.icon}</div>
              <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", marginBottom: 8, marginTop: 0 }}>{c.title}</h3>
              <p style={{ fontSize: 14, lineHeight: 1.7, color: "#94a3b8", margin: 0 }}>{c.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Signal callout */}
      <section style={{ padding: "48px 24px", maxWidth: 800, margin: "0 auto" }}>
        <div style={{
          background: "rgba(13,148,136,0.06)", border: "1px solid rgba(13,148,136,0.2)",
          borderRadius: 16, padding: "32px 36px", textAlign: "center",
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#0d9488", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>POWERED BY PARITY SIGNAL</div>
          <p style={{ fontSize: 15, lineHeight: 1.7, color: "#94a3b8", margin: 0 }}>
            Every denial pattern identified in your portfolio feeds the CivicScale intelligence network,
            benchmarking your payers against national patterns across thousands of practices.
          </p>
        </div>
      </section>

      {/* Pricing */}
      <section style={{ padding: "64px 24px 48px", maxWidth: 900, margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "#60a5fa", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>PRICING</div>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(24px, 3vw, 36px)", fontWeight: 400, color: "#f1f5f9", letterSpacing: "-0.02em" }}>
            Simple, practice-count pricing
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {TIERS.map(t => (
            <div key={t.name} style={{
              background: t.highlight ? "rgba(59,130,246,0.08)" : "rgba(255,255,255,0.03)",
              border: `1px solid ${t.highlight ? "rgba(59,130,246,0.3)" : "rgba(255,255,255,0.06)"}`,
              borderRadius: 12, padding: "28px 20px", textAlign: "center",
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: t.highlight ? "#60a5fa" : "#94a3b8", textTransform: "uppercase", marginBottom: 8 }}>{t.name}</div>
              <div style={{ fontSize: 32, fontWeight: 700, color: "#f1f5f9", marginBottom: 4 }}>
                {t.price}<span style={{ fontSize: 14, fontWeight: 400, color: "#64748b" }}>{t.period}</span>
              </div>
              <div style={{ fontSize: 13, color: "#94a3b8" }}>{t.practices}</div>
            </div>
          ))}
        </div>
        <p style={{ textAlign: "center", fontSize: 13, color: "#64748b", marginTop: 16 }}>
          First practice always free. No credit card required to start.
        </p>
      </section>

      {/* Final CTA */}
      <section style={{ padding: "48px 24px 80px", maxWidth: 600, margin: "0 auto", textAlign: "center" }}>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: 28, fontWeight: 400, color: "#f1f5f9", marginBottom: 24, letterSpacing: "-0.02em" }}>
          Ready to see the full picture?
        </h2>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/billing/demo" style={{ background: "linear-gradient(135deg, #3b82f6, #60a5fa)", color: "#fff", textDecoration: "none", borderRadius: 8, padding: "12px 28px", fontWeight: 600, fontSize: 15 }}>
            See How It Works
          </Link>
          <a href="https://billing.civicscale.ai" style={{ border: "1px solid rgba(255,255,255,0.15)", color: "#e2e8f0", textDecoration: "none", borderRadius: 8, padding: "12px 28px", fontWeight: 500, fontSize: 15 }}>
            Start With Your First Practice Free
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ padding: "32px 24px", borderTop: "1px solid rgba(255,255,255,0.06)", textAlign: "center", fontSize: 13, color: "#475569" }}>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}
