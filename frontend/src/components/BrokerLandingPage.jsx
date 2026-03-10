import { Link } from "react-router-dom";

export default function BrokerLandingPage() {
  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a1628",
      color: "#e2e8f0",
      fontFamily: "'DM Sans', sans-serif",
    }}>
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap"
        rel="stylesheet"
      />

      {/* Header */}
      <header className="cs-home-header">
        <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{
            width: "32px", height: "32px", borderRadius: "8px",
            background: "linear-gradient(135deg, #0d9488, #14b8a6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px", fontWeight: "700", color: "#0a1628",
          }}>C</div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>CivicScale</span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/billing" style={{ color: "inherit", textDecoration: "none" }}>Billing Products</Link>
          <Link to="/billing/employer" style={{ color: "inherit", textDecoration: "none" }}>Employer</Link>
          <Link to="/broker/login" style={{ color: "#14b8a6", textDecoration: "none", fontWeight: "600" }}>Broker Login</Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="cs-home-section" style={{
        paddingTop: "80px", paddingBottom: "56px",
        maxWidth: "820px", margin: "0 auto", textAlign: "center",
      }}>
        <div style={{
          display: "inline-block", background: "rgba(20,184,166,0.12)",
          borderRadius: "8px", padding: "8px 14px", marginBottom: "24px",
        }}>
          <span style={{ fontSize: "13px", fontWeight: "600", color: "#14b8a6" }}>BROKER PORTAL</span>
        </div>
        <h1 style={{
          fontFamily: "'DM Serif Display', serif",
          fontSize: "clamp(30px, 4vw, 46px)",
          lineHeight: "1.15", fontWeight: "400",
          color: "#f1f5f9", marginBottom: "20px",
          letterSpacing: "-0.02em",
        }}>
          Your clients' carriers have a data team.{" "}
          <span style={{ color: "#14b8a6" }}>Now you do too.</span>
        </h1>
        <p style={{
          fontSize: "17px", lineHeight: "1.7", color: "#94a3b8",
          maxWidth: "640px", margin: "0 auto 32px",
        }}>
          Free to start &mdash; up to 10 clients at no cost. Pro plan at $99/mo unlocks unlimited clients,
          renewal prep reports, and Level 2 claims insights. No carrier relationships, no conflicts of interest.
        </p>
        <div style={{ display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/broker/signup" style={{
            display: "inline-block", background: "#14b8a6", color: "#0a1628",
            padding: "12px 28px", borderRadius: "8px", fontWeight: "600",
            fontSize: "15px", textDecoration: "none", transition: "background 0.2s",
          }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#0d9488")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#14b8a6")}
          >
            Create Free Broker Account &rarr;
          </Link>
          <Link to="/employer/shared-report/a1b2c3d4-e5f6-7890-abcd-ef1234567890?demo=true" style={{
            display: "inline-block", border: "1px solid rgba(20,184,166,0.4)",
            color: "#14b8a6", padding: "12px 28px", borderRadius: "8px",
            fontWeight: "600", fontSize: "15px", textDecoration: "none",
            transition: "all 0.2s",
          }}
            onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#14b8a6"; e.currentTarget.style.background = "rgba(20,184,166,0.08)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(20,184,166,0.4)"; e.currentTarget.style.background = "transparent"; }}
          >
            See a Sample Report &rarr;
          </Link>
        </div>
      </section>

      {/* Value Props — 3 cards */}
      <section className="cs-home-section" style={{
        paddingBottom: "72px", maxWidth: "960px", margin: "0 auto",
      }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "24px",
        }}>
          {VALUE_PROPS.map((c) => (
            <div key={c.title} style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(20,184,166,0.18)",
              borderRadius: "14px", padding: "28px",
            }}>
              <div style={{
                width: "40px", height: "40px", borderRadius: "10px",
                background: "rgba(20,184,166,0.12)", display: "flex",
                alignItems: "center", justifyContent: "center",
                marginBottom: "16px", color: "#14b8a6", fontSize: "18px",
              }}>{c.icon}</div>
              <h3 style={{ fontSize: "17px", fontWeight: "600", color: "#f1f5f9", marginBottom: "10px" }}>
                {c.title}
              </h3>
              <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>
                {c.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* How It Works — 3 steps */}
      <section className="cs-home-section" style={{
        paddingBottom: "72px", maxWidth: "900px", margin: "0 auto",
      }}>
        <h2 style={{
          fontFamily: "'DM Serif Display', serif",
          fontSize: "28px", fontWeight: "400", color: "#f1f5f9",
          textAlign: "center", marginBottom: "40px",
        }}>How It Works</h2>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "28px",
        }}>
          {STEPS.map((s, i) => (
            <div key={i} style={{ textAlign: "center" }}>
              <div style={{
                width: "44px", height: "44px", borderRadius: "50%",
                background: "rgba(20,184,166,0.15)", color: "#14b8a6",
                fontWeight: "700", fontSize: "18px", display: "flex",
                alignItems: "center", justifyContent: "center",
                margin: "0 auto 16px",
              }}>{i + 1}</div>
              <h3 style={{ fontSize: "16px", fontWeight: "600", color: "#f1f5f9", marginBottom: "8px" }}>
                {s.title}
              </h3>
              <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>
                {s.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="cs-home-section" style={{
        paddingBottom: "72px", maxWidth: "780px", margin: "0 auto",
      }}>
        <h2 style={{
          fontFamily: "'DM Serif Display', serif",
          fontSize: "28px", fontWeight: "400", color: "#f1f5f9",
          textAlign: "center", marginBottom: "32px",
        }}>Simple pricing for brokers</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          {/* Starter */}
          <div style={{
            background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: "14px", padding: "28px",
          }}>
            <div style={{ fontSize: "13px", fontWeight: "600", color: "#94a3b8", marginBottom: "8px" }}>STARTER</div>
            <div style={{ fontSize: "32px", fontWeight: "700", color: "#f1f5f9", marginBottom: "16px" }}>Free</div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
              {["Up to 10 clients", "Benchmark tool", "Shared reports", "Prospect benchmarking"].map(f => (
                <li key={f} style={{ fontSize: "14px", color: "#94a3b8", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ color: "#14b8a6" }}>&#10003;</span> {f}
                </li>
              ))}
            </ul>
          </div>
          {/* Pro */}
          <div style={{
            background: "rgba(20,184,166,0.06)", border: "1px solid rgba(20,184,166,0.3)",
            borderRadius: "14px", padding: "28px",
          }}>
            <div style={{ fontSize: "13px", fontWeight: "600", color: "#14b8a6", marginBottom: "8px" }}>PRO</div>
            <div style={{ marginBottom: "16px" }}>
              <span style={{ fontSize: "32px", fontWeight: "700", color: "#f1f5f9" }}>$99</span>
              <span style={{ fontSize: "14px", color: "#64748b" }}>/mo</span>
            </div>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
              {["Unlimited clients", "Everything in Starter", "Renewal prep reports", "Level 2 claims insights", "Bulk onboarding", "Priority support"].map(f => (
                <li key={f} style={{ fontSize: "14px", color: "#94a3b8", display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ color: "#14b8a6" }}>&#10003;</span> {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div style={{
          background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.2)",
          borderRadius: "12px", padding: "16px 24px", marginTop: "20px", textAlign: "center",
        }}>
          <p style={{ fontSize: "14px", color: "#10b981", fontWeight: "600", marginBottom: "4px" }}>Employer Savings Guarantee</p>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0 }}>
            Your clients subscribe separately from $149/mo. If identified savings don't exceed their subscription cost, we refund the difference.
          </p>
        </div>
      </section>

      {/* Data Protection */}
      <section className="cs-home-section" style={{
        paddingBottom: "72px", maxWidth: "780px", margin: "0 auto",
      }}>
        <div style={{
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(20,184,166,0.18)",
          borderRadius: "16px", padding: "36px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "24px" }}>
            <span style={{ fontSize: "28px" }}>&#128737;&#65039;</span>
            <h2 style={{
              fontFamily: "'DM Serif Display', serif",
              fontSize: "24px", fontWeight: "400", color: "#f1f5f9", margin: 0,
            }}>Your client relationships are protected.</h2>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {[
              "We will never directly contact any employer you add to your portal \u2014 not by email, phone, or any other channel.",
              "Your client list is never shared with other brokers, carriers, or third parties.",
              "Your clients only see Parity Employer if you choose to share a report with them.",
            ].map((text, i) => (
              <div key={i} style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <span style={{ color: "#14b8a6", fontSize: "16px", flexShrink: 0, marginTop: "1px" }}>&#10003;</span>
                <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8", margin: 0 }}>{text}</p>
              </div>
            ))}
          </div>
          <p style={{
            fontSize: "16px", fontWeight: "600", color: "#f1f5f9",
            marginTop: "24px", marginBottom: 0, paddingTop: "16px",
            borderTop: "1px solid rgba(20,184,166,0.12)",
          }}>
            You control the relationship. We provide the data.
          </p>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="cs-home-section" style={{
        paddingBottom: "80px", maxWidth: "600px", margin: "0 auto", textAlign: "center",
      }}>
        <h2 style={{
          fontFamily: "'DM Serif Display', serif",
          fontSize: "24px", fontWeight: "400", color: "#f1f5f9",
          marginBottom: "16px", lineHeight: "1.3",
        }}>
          Ready to show up to your next renewal meeting with better data than the carrier?
        </h2>
        <p style={{ fontSize: "15px", color: "#94a3b8", marginBottom: "28px", lineHeight: "1.7" }}>
          Create your free broker account in 60 seconds.
        </p>
        <Link to="/broker/signup" style={{
          display: "inline-block", background: "#14b8a6", color: "#0a1628",
          padding: "12px 32px", borderRadius: "8px", fontWeight: "600",
          fontSize: "15px", textDecoration: "none", transition: "background 0.2s",
        }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "#0d9488")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "#14b8a6")}
        >
          Get Started Free &rarr;
        </Link>
      </section>

      {/* Footer */}
      <footer className="cs-home-section" style={{
        paddingTop: "40px", paddingBottom: "40px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        textAlign: "center", fontSize: "13px", color: "#475569",
      }}>
        <Link to="/" style={{ color: "#64748b", textDecoration: "none", marginRight: "24px" }}>
          &larr; CivicScale Home
        </Link>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}

const VALUE_PROPS = [
  {
    icon: "\u{1F4CA}",
    title: "Benchmark any client in 60 seconds",
    text: "Enter four fields and get an instant percentile ranking against comparable employers in the same industry, state, and size band. Backed by KFF, MEPS-IC, and BLS data.",
  },
  {
    icon: "\u{1F517}",
    title: "Share results before they ask",
    text: "Generate a read-only report link and send it to your client. No login required on their end. Your firm name on every report. You show up to renewal with data they\u2019ve never seen.",
  },
  {
    icon: "\u{1F4CB}",
    title: "See your whole book at a glance",
    text: "Every client benchmarked in one view, ranked by identified excess spend, with renewal dates flagged. Know which clients need attention before they call you.",
  },
];

const STEPS = [
  {
    title: "Add your clients",
    text: "Company name, size, state, carrier, PEPM. 60 seconds per client.",
  },
  {
    title: "We run the analysis",
    text: "Instant benchmark. Claims check available when they upload. Scorecard on plan design.",
  },
  {
    title: "You share the results",
    text: "One link, no login required. Your name on every report.",
  },
];
