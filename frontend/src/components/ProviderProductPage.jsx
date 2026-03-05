import { Link } from "react-router-dom";

export default function ProviderProductPage() {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a1628",
        color: "#e2e8f0",
        fontFamily: "'DM Sans', sans-serif",
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap"
        rel="stylesheet"
      />

      {/* Header */}
      <header className="cs-home-header">
        <Link
          to="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            textDecoration: "none",
            color: "inherit",
          }}
        >
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #0d9488, #14b8a6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "16px",
              fontWeight: "700",
              color: "#0a1628",
            }}
          >
            C
          </div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>
            CivicScale
          </span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/billing" style={{ color: "#60a5fa", textDecoration: "none" }}>
            Billing Products
          </Link>
          <Link to="/signal" style={{ color: "inherit", textDecoration: "none" }}>
            Parity Signal
          </Link>
          <Link to="/investors" style={{ color: "inherit", textDecoration: "none" }}>
            About
          </Link>
          <Link
            to="/audit/account"
            style={{
              color: "#60a5fa",
              textDecoration: "none",
              border: "1px solid #60a5fa",
              borderRadius: "6px",
              padding: "6px 16px",
            }}
          >
            Sign In
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section
        className="cs-home-section"
        style={{
          paddingTop: "80px",
          paddingBottom: "56px",
          maxWidth: "820px",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        <div
          style={{
            display: "inline-block",
            background: "rgba(59,130,246,0.12)",
            borderRadius: "8px",
            padding: "8px 14px",
            marginBottom: "24px",
          }}
        >
          <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>
            PARITY PROVIDER
          </span>
        </div>
        <h1
          style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: "clamp(30px, 4vw, 46px)",
            lineHeight: "1.15",
            fontWeight: "400",
            color: "#f1f5f9",
            marginBottom: "20px",
            letterSpacing: "-0.02em",
          }}
        >
          Know what your payers owe you.
          <br />
          <span style={{ color: "#60a5fa" }}>Every month.</span>
        </h1>
        <p
          style={{
            fontSize: "17px",
            lineHeight: "1.7",
            color: "#94a3b8",
            maxWidth: "660px",
            margin: "0 auto 32px",
          }}
        >
          Start with a free audit. See what you're missing. Then let us watch
          your revenue so you don't have to.
        </p>
        <div style={{ display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link
            to="/audit"
            style={{
              display: "inline-block",
              background: "#3b82f6",
              color: "#fff",
              padding: "12px 28px",
              borderRadius: "8px",
              fontWeight: "600",
              fontSize: "15px",
              textDecoration: "none",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#2563eb")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#3b82f6")}
          >
            Start Your Free Audit &rarr;
          </Link>
          <Link
            to="/billing/provider/demo"
            style={{
              display: "inline-block",
              border: "1px solid rgba(59,130,246,0.4)",
              color: "#60a5fa",
              padding: "12px 28px",
              borderRadius: "8px",
              fontWeight: "600",
              fontSize: "15px",
              textDecoration: "none",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#60a5fa";
              e.currentTarget.style.background = "rgba(59,130,246,0.08)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(59,130,246,0.4)";
              e.currentTarget.style.background = "transparent";
            }}
          >
            See the Demo &rarr;
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section
        className="cs-home-section"
        style={{ paddingBottom: "72px", maxWidth: "960px", margin: "0 auto" }}
      >
        <h2 style={h2Center}>How It Works</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "24px",
          }}
        >
          {STEPS.map((s, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "50%",
                  background: s.bg,
                  color: s.fg,
                  fontWeight: "700",
                  fontSize: "18px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                }}
              >
                {i + 1}
              </div>
              <h3
                style={{
                  fontSize: "17px",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  marginBottom: "8px",
                }}
              >
                {s.title}
              </h3>
              {s.price && (
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: "600",
                    color: s.fg,
                    marginBottom: "10px",
                  }}
                >
                  {s.price}
                </div>
              )}
              <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>
                {s.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* What We Find */}
      <section
        className="cs-home-section"
        style={{ paddingBottom: "72px", maxWidth: "960px", margin: "0 auto" }}
      >
        <h2 style={h2Center}>What We Find</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "24px",
          }}
        >
          {FIND_CARDS.map((c) => (
            <div
              key={c.title}
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(59,130,246,0.18)",
                borderRadius: "14px",
                padding: "28px",
              }}
            >
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "10px",
                  background: "rgba(59,130,246,0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "16px",
                  color: "#60a5fa",
                  fontSize: "18px",
                }}
              >
                {c.icon}
              </div>
              <h3
                style={{
                  fontSize: "16px",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  marginBottom: "10px",
                }}
              >
                {c.title}
              </h3>
              <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>
                {c.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Month-Over-Month Intelligence */}
      <section
        className="cs-home-section"
        style={{ paddingBottom: "72px", maxWidth: "780px", margin: "0 auto" }}
      >
        <div
          style={{
            background: "rgba(59,130,246,0.04)",
            border: "1px solid rgba(59,130,246,0.12)",
            borderRadius: "16px",
            padding: "36px",
          }}
        >
          <h2
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: "24px",
              fontWeight: "400",
              color: "#f1f5f9",
              marginBottom: "20px",
            }}
          >
            Why monitoring changes everything
          </h2>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#94a3b8", marginBottom: "16px" }}>
            The audit shows one month. The subscription shows what's changing.
          </p>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#94a3b8", marginBottom: "16px" }}>
            Is Aetna's underpayment on 99214 getting worse? Did BCBS introduce a new
            denial pattern this quarter? Is your overall revenue gap growing or shrinking?
          </p>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#cbd5e1" }}>
            These patterns only appear over time — and they're where the real money is.
            A single underpayment on a high-volume code can cost you thousands per year.
            A new denial pattern caught early can be appealed before it becomes systemic.
            Monthly monitoring turns reactive billing into proactive revenue management.
          </p>
        </div>
      </section>

      {/* Why This Is Different */}
      <section
        className="cs-home-section"
        style={{ paddingBottom: "72px", maxWidth: "960px", margin: "0 auto" }}
      >
        <h2 style={h2Center}>Why This Is Different</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "24px",
          }}
        >
          {DIFF_CARDS.map((c) => (
            <div
              key={c.title}
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(59,130,246,0.18)",
                borderRadius: "14px",
                padding: "28px",
              }}
            >
              <h3
                style={{
                  fontSize: "15px",
                  fontWeight: "600",
                  color: "#60a5fa",
                  marginBottom: "12px",
                }}
              >
                {c.title}
              </h3>
              <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>
                {c.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Early Adopter */}
      <section
        className="cs-home-section"
        style={{ paddingBottom: "72px", maxWidth: "780px", margin: "0 auto" }}
      >
        <div
          style={{
            background: "rgba(34,197,94,0.06)",
            border: "1px solid rgba(34,197,94,0.2)",
            borderRadius: "16px",
            padding: "36px",
            textAlign: "center",
          }}
        >
          <h2
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: "24px",
              fontWeight: "400",
              color: "#f1f5f9",
              marginBottom: "16px",
            }}
          >
            We're onboarding our first practices now
          </h2>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#94a3b8", marginBottom: "24px" }}>
            Early adopters get: free audit (always), discounted monitoring rate for the first year,
            direct access to our team, and priority access to benchmark intelligence features as they launch.
          </p>
          <div style={{ display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap" }}>
            <Link
              to="/audit"
              style={{
                display: "inline-block",
                background: "#3b82f6",
                color: "#fff",
                padding: "12px 28px",
                borderRadius: "8px",
                fontWeight: "600",
                fontSize: "15px",
                textDecoration: "none",
              }}
            >
              Start Your Free Audit &rarr;
            </Link>
            <a
              href="mailto:fred@civicscale.ai"
              style={{
                display: "inline-block",
                border: "1px solid rgba(59,130,246,0.4)",
                color: "#60a5fa",
                padding: "12px 28px",
                borderRadius: "8px",
                fontWeight: "600",
                fontSize: "15px",
                textDecoration: "none",
              }}
            >
              Contact fred@civicscale.ai
            </a>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section
        className="cs-home-section"
        style={{ paddingBottom: "72px", maxWidth: "780px", margin: "0 auto" }}
      >
        <h2 style={h2Center}>Pricing</h2>
        <p
          style={{
            textAlign: "center",
            fontSize: "15px",
            color: "#94a3b8",
            marginBottom: "32px",
            marginTop: "-24px",
          }}
        >
          Start with the audit. Upgrade if we find something worth watching.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
          {/* Free Audit */}
          <div
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(59,130,246,0.18)",
              borderRadius: "14px",
              padding: "32px",
            }}
          >
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#4ade80", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>
              Free
            </div>
            <h3 style={{ fontSize: "22px", fontWeight: "600", color: "#f1f5f9", marginBottom: "4px" }}>
              The Audit
            </h3>
            <div style={{ fontSize: "28px", fontWeight: "700", color: "#f1f5f9", marginBottom: "20px" }}>
              $0
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "14px", color: "#94a3b8", lineHeight: "2.2" }}>
              {[
                "One month of remittance analysis",
                "All payers analyzed",
                "Contract underpayment report",
                "Denial pattern analysis",
                "AI executive summary",
                "Revenue gap estimate",
                "Appeal letter drafts",
                "Delivered within 5-7 days",
              ].map((f) => (
                <li key={f}>
                  <span style={{ color: "#4ade80", marginRight: "8px" }}>{"\u2713"}</span>
                  {f}
                </li>
              ))}
            </ul>
            <Link
              to="/audit"
              style={{
                display: "block",
                textAlign: "center",
                marginTop: "24px",
                padding: "12px 0",
                background: "#3b82f6",
                color: "#fff",
                borderRadius: "8px",
                fontWeight: "600",
                fontSize: "14px",
                textDecoration: "none",
              }}
            >
              Start Your Free Audit
            </Link>
          </div>

          {/* Monthly Monitoring */}
          <div
            style={{
              background: "rgba(59,130,246,0.06)",
              border: "1px solid rgba(59,130,246,0.3)",
              borderRadius: "14px",
              padding: "32px",
              position: "relative",
            }}
          >
            <div style={{ fontSize: "12px", fontWeight: "600", color: "#60a5fa", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "8px" }}>
              Subscription
            </div>
            <h3 style={{ fontSize: "22px", fontWeight: "600", color: "#f1f5f9", marginBottom: "4px" }}>
              Monthly Monitoring
            </h3>
            <div style={{ fontSize: "28px", fontWeight: "700", color: "#f1f5f9", marginBottom: "4px" }}>
              $300<span style={{ fontSize: "16px", fontWeight: "400", color: "#94a3b8" }}>/month</span>
            </div>
            <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "20px" }}>
              or $3,000/year (2 months free)
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, fontSize: "14px", color: "#94a3b8", lineHeight: "2.2" }}>
              {[
                "Everything in the audit, every month",
                "Month-over-month trend analysis",
                "Worsening underpayment alerts",
                "New denial pattern detection",
                "Revenue gap tracking over time",
                "Updated appeal letters monthly",
                "Email summary each month",
                "Priority support",
              ].map((f) => (
                <li key={f}>
                  <span style={{ color: "#60a5fa", marginRight: "8px" }}>{"\u2713"}</span>
                  {f}
                </li>
              ))}
            </ul>
            <Link
              to="/audit"
              style={{
                display: "block",
                textAlign: "center",
                marginTop: "24px",
                padding: "12px 0",
                border: "1px solid #3b82f6",
                color: "#60a5fa",
                borderRadius: "8px",
                fontWeight: "600",
                fontSize: "14px",
                textDecoration: "none",
              }}
            >
              Start with the Free Audit
            </Link>
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "80px",
          maxWidth: "600px",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        <h2
          style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: "26px",
            fontWeight: "400",
            color: "#f1f5f9",
            marginBottom: "16px",
          }}
        >
          See what you're missing
        </h2>
        <p style={{ fontSize: "15px", color: "#94a3b8", marginBottom: "28px", lineHeight: "1.7" }}>
          Explore a sample audit report, month-over-month trends, and AI-generated appeal letters
          — all built from realistic practice data.
        </p>
        <Link
          to="/billing/provider/demo"
          style={{
            display: "inline-block",
            background: "#3b82f6",
            color: "#fff",
            padding: "12px 32px",
            borderRadius: "8px",
            fontWeight: "600",
            fontSize: "15px",
            textDecoration: "none",
          }}
        >
          See the Demo &rarr;
        </Link>
      </section>

      {/* Footer */}
      <footer
        className="cs-home-section"
        style={{
          paddingTop: "40px",
          paddingBottom: "40px",
          borderTop: "1px solid rgba(255,255,255,0.06)",
          textAlign: "center",
          fontSize: "13px",
          color: "#475569",
        }}
      >
        <Link
          to="/billing"
          style={{ color: "#64748b", textDecoration: "none", marginRight: "24px" }}
        >
          &larr; All Billing Products
        </Link>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}

const h2Center = {
  fontFamily: "'DM Serif Display', serif",
  fontSize: "28px",
  fontWeight: "400",
  color: "#f1f5f9",
  textAlign: "center",
  marginBottom: "40px",
};

const STEPS = [
  {
    title: "The Audit",
    price: "Free",
    text: "Send us one month of remittance files and your payer fee schedules. Within 5\u20137 days, we deliver a detailed report showing every underpayment, denial pattern, and revenue gap. No cost. No commitment.",
    bg: "rgba(34,197,94,0.15)",
    fg: "#4ade80",
  },
  {
    title: "Monthly Monitoring",
    price: "$300/month",
    text: "Like your findings? Keep going. Your fee schedules are already loaded. Each month, send us your 835 files and we analyze everything automatically. You get an email with what changed, what\u2019s new, and what to do about it.",
    bg: "rgba(59,130,246,0.15)",
    fg: "#60a5fa",
  },
  {
    title: "Continuous Intelligence",
    price: "Coming Soon",
    text: "Over time, we show you how your payer rates compare to peers in your specialty and market. Coding optimization recommendations. Contract negotiation data. The intelligence gets smarter as more practices join.",
    bg: "rgba(168,85,247,0.15)",
    fg: "#c084fc",
  },
];

const FIND_CARDS = [
  {
    icon: "\u2637",
    title: "Contract Underpayments",
    text: "Every payment line compared against your contracted rates. When the payer pays less than they agreed to, we flag it with the exact dollar amount.",
  },
  {
    icon: "\u2691",
    title: "Denial Patterns",
    text: "AI interprets every denial code in plain English, identifies patterns across months and payers, and scores each denial for appeal worthiness.",
  },
  {
    icon: "\u2197",
    title: "Revenue Gaps",
    text: "Monthly and annualized estimates of recoverable revenue \u2014 broken down by payer, by denial type, and by priority.",
  },
  {
    icon: "\u2709",
    title: "Appeal Letters",
    text: "One-click appeal drafts citing specific CMS guidelines and your contract terms. Review, edit, and send \u2014 cutting hours from your denial workflow.",
  },
];

const DIFF_CARDS = [
  {
    title: "vs. Your Billing Company",
    text: "Your billing company processes claims. We audit the results. We check whether the payer actually paid what they contracted \u2014 something most billing companies don\u2019t do systematically.",
  },
  {
    title: "vs. Enterprise RCM Software",
    text: "Tools like MD Clarity and PMMC cost $50K+ annually and require deep IT integration. We work with the 835 files you already receive. No integration. No IT project. Works the same whether you\u2019re on Epic, Athena, or paper.",
  },
  {
    title: "vs. Doing Nothing",
    text: "Industry data shows practices lose 3\u20134% of net revenue to underpayments and unworked denials. For a practice billing $400K, that\u2019s $12,000\u201316,000 per year \u2014 and it compounds because payers that underpay without consequence keep underpaying.",
  },
];
