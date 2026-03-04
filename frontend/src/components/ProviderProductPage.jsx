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
          Know what your contracts
          <br />
          <span style={{ color: "#60a5fa" }}>are really paying you.</span>
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
          Parity Provider compares your payer contract rates against Medicare
          benchmarks and regional averages — and builds evidence-based denial
          appeals when claims are rejected.
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
            to="/billing/provider/demo"
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
            Most physician practices sign payer contracts and never benchmark
            them. You know what Medicare pays for CPT 99214, but do you know
            how your Blue Cross rate compares? Your Aetna rate? What about the
            rates your competitor down the street negotiated?
          </p>
          <p
            style={{
              fontSize: "16px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "20px",
            }}
          >
            When claims are denied, your billing team sends a standard appeal
            letter. But denials aren't random — they follow patterns driven by
            specific analytical choices the payer made about coding, bundling,
            or medical necessity. A generic appeal doesn't address the actual
            reason.
          </p>
          <p style={{ fontSize: "16px", lineHeight: "1.8", color: "#cbd5e1" }}>
            Parity Provider gives you two things: contract intelligence that
            shows where you're leaving money on the table, and denial
            intelligence that builds targeted appeals challenging the specific
            logic behind each denial.
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

      {/* Analytical Paths Highlight */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "72px",
          maxWidth: "800px",
          margin: "0 auto",
        }}
      >
        <div
          style={{
            background: "rgba(59,130,246,0.06)",
            border: "1px solid rgba(59,130,246,0.15)",
            borderRadius: "16px",
            padding: "36px",
          }}
        >
          <h3
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: "22px",
              fontWeight: "400",
              color: "#f1f5f9",
              marginBottom: "16px",
            }}
          >
            Powered by Analytical Paths
          </h3>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "24px",
            }}
          >
            Most denial appeals fail because they argue the wrong point. Parity
            Provider uses Analytical Paths — our methodology for revealing the
            invisible choices behind a decision — to identify exactly why a
            claim was denied and build an appeal that challenges that specific
            logic.
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
            }}
          >
            <div
              style={{
                background: "rgba(239,68,68,0.08)",
                border: "1px solid rgba(239,68,68,0.2)",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <div
                style={{
                  fontSize: "11px",
                  fontWeight: "600",
                  color: "#f87171",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  marginBottom: "8px",
                }}
              >
                Standard Appeal
              </div>
              <p
                style={{
                  fontSize: "14px",
                  lineHeight: "1.6",
                  color: "#94a3b8",
                  fontStyle: "italic",
                }}
              >
                "We believe this claim was incorrectly denied."
              </p>
            </div>
            <div
              style={{
                background: "rgba(34,197,94,0.08)",
                border: "1px solid rgba(34,197,94,0.2)",
                borderRadius: "10px",
                padding: "20px",
              }}
            >
              <div
                style={{
                  fontSize: "11px",
                  fontWeight: "600",
                  color: "#4ade80",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  marginBottom: "8px",
                }}
              >
                Analytical Paths Appeal
              </div>
              <p
                style={{
                  fontSize: "14px",
                  lineHeight: "1.6",
                  color: "#cbd5e1",
                  fontStyle: "italic",
                }}
              >
                "This denial applied CPT bundling rule 59.4, which assumes
                services were part of a single procedure. However, the
                documented clinical circumstances — separate anatomical sites,
                distinct diagnoses — meet CMS exception criteria under NCCI
                Policy Manual Chapter 1, Section G."
              </p>
            </div>
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
          Explore a sample practice dashboard with contract benchmarks, denial
          pattern analysis, and AI-generated appeal letters.
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
    icon: "\u2637",
    title: "Contract Rate Benchmarking",
    text: "Upload your fee schedules and see how every CPT code compares to Medicare, regional commercial averages, and specialty-specific benchmarks. Identify the codes where you're underpaid and quantify the revenue gap.",
  },
  {
    icon: "\u2691",
    title: "Denial Intelligence & Appeals",
    text: "Analyze your denial patterns by payer, reason code, and procedure. Our AI identifies the specific analytical choices behind each denial and generates targeted appeal language that challenges that specific logic.",
  },
  {
    icon: "\u2197",
    title: "Revenue Gap Analysis",
    text: "See the total dollar impact of contract shortfalls and denial patterns. Prioritize which payer negotiations and appeal efforts will recover the most revenue. Track your progress over time.",
  },
];

const STEPS = [
  {
    title: "Connect your data",
    text: "Upload your fee schedules, remittance data (ERA/835), and denial reports. We accept standard formats from all major practice management systems.",
  },
  {
    title: "We analyze every rate and denial",
    text: "Each contracted rate is benchmarked. Each denial is classified by root cause and mapped to the payer's analytical logic. Patterns emerge that aren't visible in standard reports.",
  },
  {
    title: "Act on insights",
    text: "Use contract benchmarks in your next payer negotiation. Deploy targeted denial appeals that address the actual reason for rejection. Track revenue recovery over time.",
  },
];
