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
          Your health plan is costing you
          <br />
          <span style={{ color: "#60a5fa" }}>more than it should.</span>
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
          We can show you exactly how much. AI-powered benchmarking, claims
          analysis, and plan grading that tells you where your self-insured
          plan is overpaying — by category, by provider, by procedure.
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
            to="/billing/employer/benchmark"
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
            Get Your Free Benchmark &rarr;
          </Link>
          <Link
            to="/billing/employer/demo"
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

      {/* Why AI Changes Everything */}
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
            Why this couldn't exist without AI
          </h2>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            Traditional benefits consultants sample 5-10% of your claims and
            compare them against broad averages. That misses the details that
            matter — the specific provider charging 40% above market for knee
            replacements, the hospital outpatient facility fee that's triple what
            a freestanding center charges, the imaging costs that quietly doubled
            year over year.
          </p>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            Parity Employer uses AI to analyze every single claim against
            Medicare fee schedules, regional commercial benchmarks, and — as our
            community database grows — actual reported rates from real plans. Not
            a sample. Every line. The AI reads CPT codes, maps them to procedure
            categories, normalizes for geography, and flags anomalies that a
            human analyst reviewing spreadsheets would never catch.
          </p>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#cbd5e1" }}>
            But unlike a black-box AI that just gives you a number, we show you
            the analytical path: why a cost is flagged, what benchmark it's
            compared against, and what assumptions went into the comparison. You
            see the methodology, not just the conclusion.
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
                  marginBottom: s.link ? "12px" : "0",
                }}
              >
                {s.text}
              </p>
              {s.link && (
                <Link to={s.link} style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa", textDecoration: "none" }}>
                  {s.linkText}
                </Link>
              )}
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
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            Export your claims data from your TPA or benefits administrator.
            Most TPAs can generate a claims extract in CSV or Excel format — ask
            for service dates, CPT/HCPCS codes, billed amounts, allowed
            amounts, paid amounts, provider names, and member ZIP codes.
          </p>
          <p
            style={{
              fontSize: "15px",
              lineHeight: "1.8",
              color: "#94a3b8",
              marginBottom: "16px",
            }}
          >
            We accept:
          </p>
          <ul
            style={{
              fontSize: "15px",
              lineHeight: "2",
              color: "#94a3b8",
              paddingLeft: "20px",
              marginBottom: "16px",
            }}
          >
            <li>CSV or Excel claims exports (most common)</li>
            <li>EDI 837 Professional/Institutional files</li>
            <li>EDI 835 Remittance files</li>
            <li>Custom formats (contact us and we'll build an importer)</li>
          </ul>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#cbd5e1" }}>
            Your data is processed securely and never shared. Individual claims
            are anonymized after analysis — we keep only aggregate benchmarks,
            never identifiable records.
          </p>
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

      {/* Pricing */}
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
          Pricing
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "24px",
          }}
        >
          {PRICING.map((p) => (
            <div
              key={p.name}
              style={{
                background: p.popular ? "rgba(59,130,246,0.06)" : "rgba(255,255,255,0.02)",
                border: `1px solid ${p.popular ? "rgba(59,130,246,0.35)" : "rgba(59,130,246,0.18)"}`,
                borderRadius: "14px",
                padding: "28px",
                position: "relative",
              }}
            >
              {p.popular && (
                <div style={{ position: "absolute", top: "-12px", left: "50%", transform: "translateX(-50%)", background: "#3b82f6", color: "#fff", fontSize: "11px", fontWeight: "700", padding: "4px 14px", borderRadius: "12px" }}>
                  MOST POPULAR
                </div>
              )}
              <div style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa", marginBottom: "8px" }}>{p.name}</div>
              <div style={{ marginBottom: "16px" }}>
                <span style={{ fontSize: "32px", fontWeight: "700", color: "#f1f5f9" }}>{p.price}</span>
                <span style={{ fontSize: "14px", color: "#64748b" }}>/mo</span>
              </div>
              <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8", marginBottom: "20px" }}>{p.text}</p>
              <Link
                to="/billing/employer/subscribe"
                style={{
                  display: "block",
                  textAlign: "center",
                  background: p.popular ? "#3b82f6" : "transparent",
                  color: p.popular ? "#fff" : "#60a5fa",
                  border: p.popular ? "none" : "1px solid rgba(59,130,246,0.4)",
                  borderRadius: "8px",
                  padding: "10px",
                  fontWeight: "600",
                  fontSize: "14px",
                  textDecoration: "none",
                }}
              >
                Get Started
              </Link>
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
          Start with a free benchmark
        </h2>
        <p
          style={{
            fontSize: "15px",
            color: "#94a3b8",
            marginBottom: "28px",
            lineHeight: "1.7",
          }}
        >
          See how your health plan costs compare to employers in your industry
          and state — no signup required.
        </p>
        <Link
          to="/billing/employer/benchmark"
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
          Get Your Free Benchmark &rarr;
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
    text: "Get a prioritized list of savings opportunities ranked by dollar impact. Each recommendation includes the data behind it \u2014 not just \u2018you\u2019re overpaying\u2019 but exactly how much, on which procedures, at which providers.",
  },
];

const DIFF_CARDS = [
  {
    title: "vs. Your Benefits Consultant",
    text: "Consultants review summary-level data and rely on proprietary benchmarks you can\u2019t verify. They bill $50\u2013150K annually for what amounts to a few pivot tables and some industry averages. Parity Employer analyzes every claim, uses transparent benchmarks, and costs a fraction of traditional consulting.",
  },
  {
    title: "vs. TPA Reports",
    text: "Your TPA manages the same claims they\u2019re reporting on \u2014 that\u2019s a structural conflict of interest. Their reports tell you what happened but not whether it was fair. Parity Employer provides independent analysis against external benchmarks, so you\u2019re not relying on the same system that generates the bills to tell you if the bills are reasonable.",
  },
  {
    title: "vs. Other Analytics Platforms",
    text: "Most claims analytics platforms require a 6-month implementation, EDI integration, and a six-figure contract. Parity Employer works with the claims export you already have \u2014 CSV, Excel, or standard EDI formats. Upload your data and get results the same day. No implementation project required.",
  },
];

const STEPS = [
  {
    title: "Benchmark your costs",
    text: "Enter your industry, company size, and current PEPM. Instantly see where you rank against national and regional employer benchmarks.",
    link: "/billing/employer/benchmark",
    linkText: "Try it free \u2192",
  },
  {
    title: "Check your claims",
    text: "Upload your claims file (CSV or Excel) and we\u2019ll compare every line against CMS Medicare rates for your geography. AI auto-detects your column headers.",
    link: "/billing/employer/claims-check",
    linkText: "Upload claims \u2192",
  },
  {
    title: "Get ongoing monitoring",
    text: "Subscribe for continuous analysis, quarterly savings reports, and alerts when new cost anomalies appear in your claims data.",
    link: "/billing/employer/subscribe",
    linkText: "See pricing \u2192",
  },
];

const ROADMAP = [
  {
    icon: "\u2705",
    label: "Available now",
    text: "Medicare fee schedule benchmarking for every CPT code, geographic adjustment, category-level cost analysis, provider-level variance identification.",
    borderColor: "rgba(34,197,94,0.25)",
    labelColor: "#4ade80",
  },
  {
    icon: "\uD83D\uDD04",
    label: "Coming soon",
    text: "Community-reported commercial rate benchmarks (powered by anonymized data from Parity Health users), year-over-year trend analysis, automated savings recommendations with estimated dollar impact.",
    borderColor: "rgba(59,130,246,0.25)",
    labelColor: "#60a5fa",
  },
  {
    icon: "\uD83D\uDD2E",
    label: "On our roadmap",
    text: "Direct TPA integration for automated data refresh, network optimization modeling, pharmacy benefit benchmarking.",
    borderColor: "rgba(148,163,184,0.2)",
    labelColor: "#94a3b8",
  },
];

const PRICING = [
  {
    name: "Small",
    price: "$299",
    text: "Up to 100 employees. Monthly benchmarking, claims analysis, and plan scorecard.",
  },
  {
    name: "Mid-Market",
    price: "$799",
    popular: true,
    text: "100\u20131,000 employees. Unlimited uploads, provider-level analysis, quarterly savings reports.",
  },
  {
    name: "Employer+",
    price: "$1,999",
    text: "1,000+ employees. Dedicated account manager, custom cohorts, EDI integration, API access.",
  },
];

const STATS = [
  { value: "$300B+", label: "Estimated annual billing errors across the U.S. healthcare system" },
  { value: "12\u201318%", label: "Average overpayment on specialist procedures by self-insured employers" },
  { value: "Parity Engine", label: "Same benchmark infrastructure behind Parity Signal and Parity Health" },
];
