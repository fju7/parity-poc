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
          AI-powered contract benchmarking and denial intelligence for physician
          practices that want to negotiate from evidence, not intuition.
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

      {/* Why AI — "Your billing team is fighting denials blind" */}
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
          <h2
            style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: "24px",
              fontWeight: "400",
              color: "#f1f5f9",
              marginBottom: "20px",
            }}
          >
            Your billing team is fighting denials blind
          </h2>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            The average physician practice has a denial rate between 5-10%. Each
            denied claim costs $25-35 to rework and takes 14+ days to resolve.
            Most practices send generic appeal letters — "we believe this was
            incorrectly denied" — and win about 30% of the time.
          </p>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            The problem isn't effort. It's information asymmetry. The payer used
            a specific algorithm or rule to deny your claim — a bundling edit, a
            medical necessity algorithm, a frequency limit. But they don't tell
            you which rule, and your billing team doesn't have time to research
            it for every denial.
          </p>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#cbd5e1" }}>
            AI changes this equation. Parity Provider reads your ERA data,
            classifies each denial by its root cause, identifies patterns across
            hundreds of denials, and — using our Analytical Paths methodology —
            maps the specific analytical choices the payer made. Then it
            generates a targeted appeal that challenges that specific logic,
            citing the relevant CMS guidelines, specialty society criteria, and
            coding rules. A generic appeal succeeds ~30% of the time. A targeted
            appeal that addresses the actual denial logic succeeds ~60-65% of
            the time.
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

      {/* Analytical Paths — The Core Innovation */}
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
            Analytical Paths — The Core Innovation
          </h3>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            Every denial is a conclusion. Behind that conclusion is a chain of
            analytical choices the payer made:
          </p>
          <div
            style={{
              background: "rgba(59,130,246,0.06)",
              borderRadius: "10px",
              padding: "20px 24px",
              marginBottom: "16px",
            }}
          >
            {[
              "Which bundling rules to apply",
              "How to interpret modifier usage",
              "What constitutes medical necessity for a given procedure",
              "How strictly to enforce frequency limits",
              "Whether to apply the most restrictive or most generous interpretation",
            ].map((item) => (
              <p
                key={item}
                style={{
                  fontSize: "14px",
                  lineHeight: "1.8",
                  color: "#cbd5e1",
                  paddingLeft: "16px",
                  position: "relative",
                }}
              >
                <span
                  style={{
                    position: "absolute",
                    left: 0,
                    color: "#60a5fa",
                  }}
                >
                  &rsaquo;
                </span>
                {item}
              </p>
            ))}
          </div>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            These choices are invisible to you. You see "claim denied" — you
            don't see which analytical path led to that denial.
          </p>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#cbd5e1",
              marginBottom: "24px",
            }}
          >
            Analytical Paths is our methodology for making those invisible
            choices visible. For each denial, we identify the specific rule
            applied, the interpretation used, and the alternative
            interpretations that support your claim. Then we build an appeal
            that doesn't just say "we disagree" — it says "you applied Rule X
            with Interpretation Y, but CMS Guideline Z supports Interpretation
            W, and here's why."
          </p>

          {/* Standard vs Analytical Paths comparison */}
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
                  marginBottom: "4px",
                }}
              >
                Standard Appeal
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: "#94a3b8",
                  marginBottom: "8px",
                }}
              >
                ~30% success rate
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
                  marginBottom: "4px",
                }}
              >
                Analytical Paths Appeal
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: "#94a3b8",
                  marginBottom: "8px",
                }}
              >
                ~60-65% success rate
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
                documented clinical circumstances meet CMS exception criteria
                under NCCI Policy Manual Chapter 1, Section G."
              </p>
            </div>
          </div>

          <p
            style={{
              fontSize: "14px",
              lineHeight: "1.7",
              color: "#64748b",
              marginTop: "16px",
              fontStyle: "italic",
            }}
          >
            This is the same methodology that powers Parity Signal's evidence
            scoring and Parity Health's bill analysis. One engine, multiple
            applications — all focused on making analytical choices transparent.
          </p>
        </div>
      </section>

      {/* How We're Different — 3 comparison cards */}
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
          How We're Different
        </h2>
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

      {/* What You Need to Get Started */}
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
            What You Need to Get Started
          </h2>
          <p
            style={{
              fontSize: "15px",
              fontWeight: "600",
              color: "#cbd5e1",
              marginBottom: "8px",
            }}
          >
            For contract benchmarking:
          </p>
          <ul
            style={{
              fontSize: "15px",
              lineHeight: "2",
              color: "#94a3b8",
              paddingLeft: "20px",
              marginBottom: "20px",
            }}
          >
            <li>
              Your payer fee schedules (the contracted rates for your top CPT
              codes)
            </li>
            <li>
              If you don't have a fee schedule document, your recent remittance
              data works — we can extract effective rates from payment history
            </li>
          </ul>
          <p
            style={{
              fontSize: "15px",
              fontWeight: "600",
              color: "#cbd5e1",
              marginBottom: "8px",
            }}
          >
            For denial intelligence:
          </p>
          <ul
            style={{
              fontSize: "15px",
              lineHeight: "2",
              color: "#94a3b8",
              paddingLeft: "20px",
              marginBottom: "20px",
            }}
          >
            <li>
              ERA/835 remittance files from your practice management system
              (most systems can export these)
            </li>
            <li>
              Or a denial report with: CPT code, denial reason code
              (CARC/RARC), payer, date, and billed amount
            </li>
            <li>CSV or Excel exports also accepted</li>
          </ul>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#cbd5e1" }}>
            Your data is processed securely and never shared outside your
            practice.
          </p>
        </div>
      </section>

      {/* How It Builds Over Time */}
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
          How It Builds Over Time
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "28px",
          }}
        >
          {TIMELINE.map((t, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "50%",
                  background: t.bgColor,
                  color: t.fgColor,
                  fontWeight: "700",
                  fontSize: "14px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                }}
              >
                {t.badge}
              </div>
              <h3
                style={{
                  fontSize: "16px",
                  fontWeight: "600",
                  color: "#f1f5f9",
                  marginBottom: "8px",
                }}
              >
                {t.title}
              </h3>
              <p
                style={{
                  fontSize: "14px",
                  lineHeight: "1.7",
                  color: "#94a3b8",
                }}
              >
                {t.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Roadmap Transparency */}
      <section
        className="cs-home-section"
        style={{
          paddingBottom: "72px",
          maxWidth: "780px",
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
          Where We Are
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {ROADMAP.map((r, i) => (
            <div
              key={i}
              style={{
                background: "rgba(255,255,255,0.02)",
                border: `1px solid ${r.borderColor}`,
                borderRadius: "14px",
                padding: "24px 28px",
                display: "flex",
                gap: "16px",
                alignItems: "flex-start",
              }}
            >
              <span style={{ fontSize: "20px", flexShrink: 0, marginTop: "2px" }}>
                {r.icon}
              </span>
              <div>
                <h3
                  style={{
                    fontSize: "15px",
                    fontWeight: "600",
                    color: r.labelColor,
                    marginBottom: "8px",
                  }}
                >
                  {r.label}
                </h3>
                <p
                  style={{
                    fontSize: "14px",
                    lineHeight: "1.7",
                    color: "#94a3b8",
                  }}
                >
                  {r.text}
                </p>
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

const DIFF_CARDS = [
  {
    title: "vs. Your Billing Company",
    text: "Your billing team processes denials reactively \u2014 one at a time, using template letters. They don\u2019t have the bandwidth to research each denial\u2019s root cause or track patterns across payers. Parity Provider analyzes all your denials at once, identifies systematic patterns, and generates appeals that address the actual reason \u2014 not just the outcome.",
  },
  {
    title: "vs. Revenue Cycle Management Software",
    text: "RCM platforms track denials and help you manage the workflow. But they don\u2019t analyze why denials happen or generate targeted appeals. They tell you \u2018you had 47 denials from UHC this quarter.\u2019 We tell you \u2018UHC denied 12 echocardiograms using a frequency limit that doesn\u2019t account for documented clinical changes \u2014 here are 12 targeted appeals with supporting guidelines.\u2019",
  },
  {
    title: "vs. Denial Management Services",
    text: "Outsourced denial management services charge 15-25% of recovered revenue. They use standard appeal processes that don\u2019t scale. Parity Provider gives your own team the intelligence to fight denials effectively \u2014 and you keep 100% of what you recover.",
  },
];

const TIMELINE = [
  {
    badge: "M1",
    title: "Month 1: Pattern Detection",
    text: "Upload your denial data and see immediate insights \u2014 denial rates by payer, most-denied CPT codes, most common denial reasons. AI generates initial appeals using general coding guidelines and payer-specific rules.",
    bgColor: "rgba(59,130,246,0.15)",
    fgColor: "#60a5fa",
  },
  {
    badge: "M2",
    title: "Month 2\u20133: Targeted Intelligence",
    text: "As the system processes more of your denials, patterns sharpen. Analytical Paths identifies the specific logic behind recurring denial types. Appeals become increasingly targeted \u2014 citing exact policy manual sections, pointing to specific guideline criteria your claims meet.",
    bgColor: "rgba(34,197,94,0.15)",
    fgColor: "#4ade80",
  },
  {
    badge: "M4",
    title: "Month 4+: Predictive & Proactive",
    text: "With enough history, the system begins predicting which claims are likely to be denied before submission and recommending documentation or coding adjustments. Contract negotiation briefs are generated automatically before renewal periods.",
    bgColor: "rgba(168,85,247,0.15)",
    fgColor: "#c084fc",
  },
];

const ROADMAP = [
  {
    icon: "\u2705",
    label: "Available now",
    text: "Fee schedule benchmarking against Medicare rates for every CPT code, geographic adjustment, payer-by-payer rate comparison, revenue gap calculation.",
    borderColor: "rgba(34,197,94,0.25)",
    labelColor: "#4ade80",
  },
  {
    icon: "\u2705",
    label: "Available now",
    text: "Denial pattern analysis \u2014 classification by reason code, payer, and procedure category, with frequency and dollar-impact tracking.",
    borderColor: "rgba(34,197,94,0.25)",
    labelColor: "#4ade80",
  },
  {
    icon: "\uD83D\uDD04",
    label: "Coming soon",
    text: "AI-generated targeted denial appeals using Analytical Paths methodology, with CMS guideline citations and specialty-specific supporting evidence.",
    borderColor: "rgba(59,130,246,0.25)",
    labelColor: "#60a5fa",
  },
  {
    icon: "\uD83D\uDD04",
    label: "Coming soon",
    text: "Community-reported contract rate benchmarks (aggregated from Parity Provider users \u2014 anonymized, minimum thresholds for display).",
    borderColor: "rgba(59,130,246,0.25)",
    labelColor: "#60a5fa",
  },
  {
    icon: "\uD83D\uDD2E",
    label: "On our roadmap",
    text: "Pre-submission denial risk scoring, automated ERA ingestion from clearinghouses, contract negotiation brief generator, payer performance scorecards.",
    borderColor: "rgba(148,163,184,0.2)",
    labelColor: "#94a3b8",
  },
];
