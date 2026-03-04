import { Link } from "react-router-dom";

const PRODUCTS = [
  {
    name: "Parity Health",
    subtitle: "Consumer Bill Analysis",
    description:
      "Analyze your medical bill against Medicare benchmarks to see if you're being charged fairly.",
    to: "/parity-health/",
    cta: "Analyze My Bill",
  },
  {
    name: "Parity Employer",
    subtitle: "Self-Insured Employer Analytics",
    description:
      "Benchmark your claims data against regional and national rates to surface hidden cost drivers.",
    to: "/billing/employer",
    cta: "Learn More",
  },
  {
    name: "Parity Provider",
    subtitle: "Practice Contract & Denial Intelligence",
    description:
      "Compare your contract rates against benchmarks and build evidence-based denial appeals.",
    to: "/billing/provider",
    cta: "Learn More",
  },
];

export default function BillingLanding() {
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
          paddingBottom: "48px",
          maxWidth: "800px",
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
            BILLING INTELLIGENCE
          </span>
        </div>
        <h1
          style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: "clamp(32px, 4vw, 48px)",
            lineHeight: "1.15",
            fontWeight: "400",
            color: "#f1f5f9",
            marginBottom: "20px",
            letterSpacing: "-0.02em",
          }}
        >
          Healthcare billing analysis
          <br />
          <span style={{ color: "#60a5fa" }}>powered by the Parity Engine.</span>
        </h1>
        <p
          style={{
            fontSize: "17px",
            lineHeight: "1.7",
            color: "#94a3b8",
            maxWidth: "620px",
            margin: "0 auto",
          }}
        >
          AI-powered benchmark analysis for medical bills, insurance claims, and
          provider contracts. We surface the analytical choices that drive
          billing outcomes — for consumers, employers, and physician practices.
        </p>
      </section>

      {/* Product cards */}
      <section
        className="cs-billing-cards cs-home-section"
        style={{
          paddingTop: "0",
          paddingBottom: "80px",
          maxWidth: "900px",
          margin: "0 auto",
        }}
      >
        {PRODUCTS.map((p) => (
          <Link
            key={p.name}
            to={p.to}
            style={{
              display: "block",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(59,130,246,0.2)",
              borderRadius: "16px",
              padding: "32px",
              textDecoration: "none",
              color: "inherit",
              transition: "all 0.25s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(59,130,246,0.06)";
              e.currentTarget.style.borderColor = "rgba(59,130,246,0.4)";
              e.currentTarget.style.transform = "translateY(-2px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(255,255,255,0.02)";
              e.currentTarget.style.borderColor = "rgba(59,130,246,0.2)";
              e.currentTarget.style.transform = "none";
            }}
          >
            <div
              style={{
                fontSize: "12px",
                fontWeight: "600",
                color: "#60a5fa",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "6px",
              }}
            >
              {p.subtitle}
            </div>
            <h2
              style={{
                fontFamily: "'DM Serif Display', serif",
                fontSize: "24px",
                fontWeight: "400",
                color: "#f1f5f9",
                marginBottom: "10px",
              }}
            >
              {p.name}
            </h2>
            <p
              style={{
                fontSize: "15px",
                lineHeight: "1.7",
                color: "#94a3b8",
                marginBottom: "20px",
              }}
            >
              {p.description}
            </p>
            <span
              style={{ fontSize: "14px", fontWeight: "500", color: "#60a5fa" }}
            >
              {p.cta} &rarr;
            </span>
          </Link>
        ))}
      </section>

      {/* Stats strip */}
      <section
        className="cs-home-section"
        style={{
          paddingTop: "40px",
          paddingBottom: "60px",
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
          {[
            { n: "$300B+", l: "Estimated annual billing errors" },
            { n: "96%", l: "US hospital coverage" },
            { n: "841K+", l: "Procedure rates benchmarked" },
          ].map((s) => (
            <div key={s.l}>
              <div
                style={{ fontSize: "24px", fontWeight: "600", color: "#60a5fa" }}
              >
                {s.n}
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: "#64748b",
                  marginTop: "4px",
                }}
              >
                {s.l}
              </div>
            </div>
          ))}
        </div>
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
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}
