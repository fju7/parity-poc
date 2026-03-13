import { Link } from "react-router-dom";

export default function ParityHealthLandingPage() {
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
          <a
            href="https://civicscale.ai"
            style={{ color: "inherit", textDecoration: "none" }}
          >
            CivicScale
          </a>
          <a
            href="https://health.civicscale.ai/health/login"
            style={{
              color: "#14b8a6",
              textDecoration: "none",
              border: "1px solid #14b8a6",
              borderRadius: "6px",
              padding: "6px 16px",
            }}
          >
            Sign In
          </a>
          <a
            href="https://health.civicscale.ai/health/signup"
            style={{
              color: "#0a1628",
              textDecoration: "none",
              background: "#14b8a6",
              borderRadius: "6px",
              padding: "6px 16px",
              fontWeight: 600,
            }}
          >
            Start Free Trial
          </a>
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
            background: "rgba(20,184,166,0.12)",
            borderRadius: "8px",
            padding: "8px 14px",
            marginBottom: "24px",
          }}
        >
          <span
            style={{ fontSize: "13px", fontWeight: "600", color: "#14b8a6" }}
          >
            PARITY HEALTH
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
          Your medical bill explained.
          <br />
          <span style={{ color: "#14b8a6" }}>In plain English.</span>
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
          Parity Health analyzes medical bills and Explanations of Benefits
          against Medicare rates and typical commercial benchmarks. Upload yours
          and we'll show you what every line means — and flag anything worth a
          closer look.
        </p>
        <div
          style={{
            display: "flex",
            gap: "16px",
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          <a
            href="https://health.civicscale.ai/health/signup"
            style={{
              display: "inline-block",
              background: "#14b8a6",
              color: "#0a1628",
              padding: "12px 28px",
              borderRadius: "8px",
              fontWeight: "600",
              fontSize: "15px",
              textDecoration: "none",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#0d9488")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#14b8a6")}
          >
            Start Free Trial &rarr;
          </a>
          <a
            href="#how-it-works"
            style={{
              display: "inline-block",
              border: "1px solid rgba(20,184,166,0.4)",
              color: "#14b8a6",
              padding: "12px 28px",
              borderRadius: "8px",
              fontWeight: "600",
              fontSize: "15px",
              textDecoration: "none",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#14b8a6";
              e.currentTarget.style.background = "rgba(20,184,166,0.08)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(20,184,166,0.4)";
              e.currentTarget.style.background = "transparent";
            }}
          >
            See How It Works
          </a>
        </div>
        <p
          style={{
            fontSize: "13px",
            color: "#64748b",
            marginTop: "16px",
          }}
        >
          30-day free trial &mdash; $9.95/month or $29/year. Cancel anytime.
        </p>
      </section>

      {/* How It Works */}
      <section
        id="how-it-works"
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
                  background: "rgba(20,184,166,0.15)",
                  color: "#14b8a6",
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

      {/* What We Look For */}
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
          What We Look For
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "24px",
          }}
        >
          {LOOK_FOR_CARDS.map((c) => (
            <div
              key={c.title}
              style={{
                background: "rgba(255,255,255,0.02)",
                border: "1px solid rgba(20,184,166,0.18)",
                borderRadius: "14px",
                padding: "28px",
              }}
            >
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "10px",
                  background: "rgba(20,184,166,0.12)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "16px",
                  color: "#14b8a6",
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

      {/* Who Uses Parity Health */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "72px",
          maxWidth: "780px",
          margin: "0 auto",
        }}
      >
        <div
          style={{
            background: "rgba(20,184,166,0.04)",
            border: "1px solid rgba(20,184,166,0.12)",
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
            Who Uses Parity Health
          </h2>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
            }}
          >
            Anyone navigating an unexpected medical bill or an Explanation of
            Benefits they don't fully understand. Parity Health is used by
            patients trying to make sense of hospital charges, patient advocates
            helping others dispute bills, and employers who want to understand
            what their employees experience on the receiving end of the claims
            their plan is paying.
          </p>
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
          Medical bills are among the most complex documents most people will
          ever receive.
        </h2>
        <p
          style={{
            fontSize: "15px",
            color: "#94a3b8",
            marginBottom: "28px",
            lineHeight: "1.7",
          }}
        >
          30-day free trial. $9.95/month or $29/year. Cancel anytime.
        </p>
        <a
          href="https://health.civicscale.ai/health/signup"
          style={{
            display: "inline-block",
            background: "#14b8a6",
            color: "#0a1628",
            padding: "12px 32px",
            borderRadius: "8px",
            fontWeight: "600",
            fontSize: "15px",
            textDecoration: "none",
            transition: "background 0.2s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#0d9488")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#14b8a6")}
        >
          Start Free Trial &rarr;
        </a>
      </section>

      {/* Employer link */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "40px",
          maxWidth: "600px",
          margin: "0 auto",
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: "14px", color: "#64748b" }}>
          Managing employee benefits?{" "}
          <a href="https://employer.civicscale.ai" style={{ color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>
            Learn about Parity Employer &rarr;
          </a>
        </p>
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
          to="/"
          style={{
            color: "#64748b",
            textDecoration: "none",
            marginRight: "24px",
          }}
        >
          &larr; Home
        </Link>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}

const STEPS = [
  {
    title: "Upload your document",
    text: "PDF, photo, or paste the text. Hospital bills, doctor bills, Explanations of Benefits. Any format works.",
  },
  {
    title: "We compare every line",
    text: "Each procedure code is checked against Medicare rates and typical commercial benchmarks for your region.",
  },
  {
    title: "You get a plain-English report",
    text: "Every charge explained. Anything above benchmark flagged. Your options laid out clearly.",
  },
];

const LOOK_FOR_CARDS = [
  {
    icon: "\u2261",
    title: "Duplicate billing",
    text: "The same service billed more than once under different codes.",
  },
  {
    icon: "\u2191",
    title: "Upcoding",
    text: "A routine visit billed as a more complex and expensive service.",
  },
  {
    icon: "\u2702",
    title: "Unbundling",
    text: "Procedures split into separate components to inflate the total charge.",
  },
  {
    icon: "$",
    title: "Above-benchmark pricing",
    text: "Amounts significantly higher than Medicare or typical commercial rates for your area.",
  },
];
