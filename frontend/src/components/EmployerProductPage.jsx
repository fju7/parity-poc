import { Link } from "react-router-dom";

export default function EmployerProductPage() {
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
          <span
            style={{
              fontSize: "18px",
              fontWeight: "600",
              letterSpacing: "-0.02em",
            }}
          >
            CivicScale
          </span>
        </Link>
        <nav className="cs-home-nav">
          <Link
            to="/billing"
            style={{ color: "#60a5fa", textDecoration: "none" }}
          >
            Billing Products
          </Link>
          <Link
            to="/signal"
            style={{ color: "inherit", textDecoration: "none" }}
          >
            Parity Signal
          </Link>
          <Link
            to="/investors"
            style={{ color: "inherit", textDecoration: "none" }}
          >
            About
          </Link>
          <Link
            to="/employer/login"
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
          <span
            style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}
          >
            PARITY EMPLOYER
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
          See what your health plan
          <br />
          <span style={{ color: "#60a5fa" }}>is really costing you.</span>
        </h1>
        <p
          style={{
            fontSize: "17px",
            lineHeight: "1.7",
            color: "#94a3b8",
            maxWidth: "640px",
            margin: "0 auto 32px",
          }}
        >
          Parity Employer benchmarks your self-insured claims against regional
          and national data to surface hidden cost drivers, overpriced
          providers, and savings opportunities.
        </p>
        <div
          style={{
            display: "flex",
            gap: "16px",
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          <Link
            to="/billing/employer/demo"
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
            Try the Demo
          </Link>
          <Link
            to="/employer/login"
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
            Sign In
          </Link>
        </div>
      </section>

      {/* Problem Statement */}
      <section
        className="cs-home-section"
        style={{
          paddingTop: "0",
          paddingBottom: "64px",
          maxWidth: "780px",
          margin: "0 auto",
        }}
      >
        <div
          style={{
            background: "rgba(59,130,246,0.04)",
            border: "1px solid rgba(59,130,246,0.12)",
            borderRadius: "16px",
            padding: "36px",
          }}
        >
          <p
            style={{
              fontSize: "16px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "20px",
            }}
          >
            Self-insured employers spend $15,000+ per employee annually on
            healthcare — but most can't tell you whether those costs are fair.
            Your TPA sends you reports, but without independent benchmarks,
            you're trusting the same system that generates the bills to tell
            you if the bills are reasonable.
          </p>
          <p style={{ fontSize: "16px", lineHeight: "1.8", color: "#cbd5e1" }}>
            Parity Employer changes that. We compare your claims against
            Medicare fee schedules, regional commercial rates, and national
            averages — procedure by procedure, provider by provider — so you
            can see exactly where your plan is overpaying.
          </p>
        </div>
      </section>

      {/* What You Get — 3 cards */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "72px",
          maxWidth: "960px",
          margin: "0 auto",
        }}
      >
        <h2
          style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: "28px",
            fontWeight: "400",
            color: "#f1f5f9",
            textAlign: "center",
            marginBottom: "40px",
          }}
        >
          What You Get
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "24px",
          }}
        >
          {CARDS.map((c) => (
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
                  fontSize: "17px",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  marginBottom: "10px",
                }}
              >
                {c.title}
              </h3>
              <p
                style={{
                  fontSize: "14px",
                  lineHeight: "1.7",
                  color: "#94a3b8",
                }}
              >
                {c.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works — 3 steps */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "72px",
          maxWidth: "900px",
          margin: "0 auto",
        }}
      >
        <h2
          style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: "28px",
            fontWeight: "400",
            color: "#f1f5f9",
            textAlign: "center",
            marginBottom: "40px",
          }}
        >
          How It Works
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "28px",
          }}
        >
          {STEPS.map((s, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "50%",
                  background: "rgba(59,130,246,0.15)",
                  color: "#60a5fa",
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
                  fontSize: "16px",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  marginBottom: "8px",
                }}
              >
                {s.title}
              </h3>
              <p
                style={{
                  fontSize: "14px",
                  lineHeight: "1.7",
                  color: "#94a3b8",
                }}
              >
                {s.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats strip */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "72px",
          maxWidth: "900px",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        <div
          style={{
            background: "rgba(59,130,246,0.06)",
            border: "1px solid rgba(59,130,246,0.15)",
            borderRadius: "16px",
            padding: "32px",
            display: "flex",
            justifyContent: "center",
            gap: "48px",
            flexWrap: "wrap",
          }}
        >
          {STATS.map((s) => (
            <div key={s.label}>
              <div
                style={{
                  fontSize: "24px",
                  fontWeight: "600",
                  color: "#60a5fa",
                }}
              >
                {s.value}
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: "#64748b",
                  marginTop: "4px",
                  maxWidth: "180px",
                }}
              >
                {s.label}
              </div>
            </div>
          ))}
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
          See the demo in action
        </h2>
        <p
          style={{
            fontSize: "15px",
            color: "#94a3b8",
            marginBottom: "28px",
            lineHeight: "1.7",
          }}
        >
          Explore a sample employer dashboard pre-loaded with realistic claims
          data, benchmark comparisons, and savings opportunities.
        </p>
        <Link
          to="/billing/employer/demo"
          style={{
            display: "inline-block",
            background: "#3b82f6",
            color: "#fff",
            padding: "12px 32px",
            borderRadius: "8px",
            fontWeight: "600",
            fontSize: "15px",
            textDecoration: "none",
            transition: "background 0.2s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#2563eb")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#3b82f6")}
        >
          Try the Demo &rarr;
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
          style={{
            color: "#64748b",
            textDecoration: "none",
            marginRight: "24px",
          }}
        >
          &larr; All Billing Products
        </Link>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}

const CARDS = [
  {
    icon: "\u2261",
    title: "Cost Benchmarking by Category",
    text: "See how your spending in orthopedics, cardiology, imaging, and 20+ other categories compares to regional benchmarks. Instantly identify which categories are driving above-market costs.",
  },
  {
    icon: "\u2316",
    title: "Provider-Level Analysis",
    text: "Drill into individual providers to see who charges above market rates. Identify high-cost outliers and quantify the savings from steering to fairly-priced alternatives.",
  },
  {
    icon: "\u2193",
    title: "Actionable Savings Report",
    text: "Get a prioritized list of savings opportunities ranked by dollar impact. Each recommendation includes the data behind it \u2014 not just 'you're overpaying' but exactly how much, on which procedures, at which providers.",
  },
];

const STEPS = [
  {
    title: "Upload your claims data",
    text: "Export your claims file from your TPA or benefits administrator. We accept standard EDI 837/835 formats, CSV exports, or Excel files.",
  },
  {
    title: "We benchmark every line",
    text: "Each claim is compared against Medicare fee schedules adjusted for your geography, regional commercial rates, and national averages. We flag anomalies and quantify variances.",
  },
  {
    title: "Review your insights",
    text: "Your dashboard shows cost variances by category, provider, and procedure \u2014 with specific dollar amounts and percentage differences. Export reports for your broker or benefits committee.",
  },
];

const STATS = [
  { value: "$300B+", label: "Estimated annual billing errors across the U.S. healthcare system" },
  { value: "12\u201318%", label: "Average overpayment on specialist procedures by self-insured employers" },
  { value: "Parity Engine", label: "Same benchmark infrastructure behind Parity Signal and Parity Health" },
];
