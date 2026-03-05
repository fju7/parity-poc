import { useState } from "react";
import { Link } from "react-router-dom";
import "./CivicScaleHomepage.css";

export function LogoIcon({ footer }) {
  if (footer) {
    return (
      <div className="cs-nav-logo-icon">
        <div className="cs-bar-col">
          <div className="cs-bar cs-bar-tall" style={{ background: "rgba(255,255,255,0.4)" }} />
          <div className="cs-bar cs-bar-mid" style={{ background: "var(--cs-teal-light)", opacity: 0.7 }} />
          <div className="cs-bar cs-bar-short" style={{ background: "rgba(255,255,255,0.4)" }} />
        </div>
        <div className="cs-bar-col">
          <div className="cs-bar cs-bar-short" style={{ background: "var(--cs-teal-light)", opacity: 0.7 }} />
          <div className="cs-bar cs-bar-mid" style={{ background: "rgba(255,255,255,0.4)" }} />
          <div className="cs-bar cs-bar-tall" style={{ background: "var(--cs-teal-light)", opacity: 0.7 }} />
        </div>
      </div>
    );
  }

  return (
    <div className="cs-nav-logo-icon">
      <div className="cs-bar-col">
        <div className="cs-bar cs-bar-navy cs-bar-tall" />
        <div className="cs-bar cs-bar-teal cs-bar-mid" />
        <div className="cs-bar cs-bar-navy cs-bar-short" />
      </div>
      <div className="cs-bar-col">
        <div className="cs-bar cs-bar-teal cs-bar-short" />
        <div className="cs-bar cs-bar-navy cs-bar-mid" />
        <div className="cs-bar cs-bar-teal cs-bar-tall" />
      </div>
    </div>
  );
}

const SIGN_IN_PRODUCTS = [
  { name: "Parity Health", path: "/parity-health/login", desc: "Medical bill analysis" },
  { name: "Parity Provider", path: "/provider/login", desc: "Provider benchmarks" },
  { name: "Parity Signal", path: "/signal/login", desc: "Evidence intelligence" },
  { name: "Parity Employer", path: "/employer/login", desc: "Employer claims" },
];

function SignInDropdown() {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen(!open)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        style={{
          color: "#14b8a6", background: "transparent", cursor: "pointer",
          border: "1px solid #14b8a6", borderRadius: "6px",
          padding: "6px 16px", fontFamily: "inherit", fontSize: "inherit",
          fontWeight: "inherit",
        }}
      >
        Sign In
      </button>
      {open && (
        <div style={{
          position: "absolute", right: 0, top: "calc(100% + 8px)",
          background: "#111827", border: "1px solid #1e293b",
          borderRadius: "10px", padding: "6px", minWidth: "220px",
          boxShadow: "0 8px 24px rgba(0,0,0,0.4)", zIndex: 100,
        }}>
          {SIGN_IN_PRODUCTS.map((p) => (
            <Link
              key={p.path}
              to={p.path}
              style={{
                display: "block", padding: "10px 12px", borderRadius: "6px",
                textDecoration: "none", color: "#e2e8f0", transition: "background 0.15s",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "#1e293b")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <div style={{ fontSize: "13px", fontWeight: 600 }}>{p.name}</div>
              <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>{p.desc}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CivicScaleHomepage() {
  const [hoveredProduct, setHoveredProduct] = useState(null);

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a1628",
      color: "#e2e8f0",
      fontFamily: "'DM Sans', sans-serif",
      overflowX: "hidden"
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      <header className="cs-home-header">
        <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{
            width: "32px", height: "32px", borderRadius: "8px",
            background: "linear-gradient(135deg, #0d9488, #14b8a6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "16px", fontWeight: "700", color: "#0a1628"
          }}>C</div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>
            CivicScale
          </span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/audit" style={{ color: "#14b8a6", textDecoration: "none", fontWeight: "600" }}>Free Audit</Link>
          <Link to="/billing" style={{ color: "inherit", textDecoration: "none" }}>Billing Products</Link>
          <Link to="/signal" style={{ color: "inherit", textDecoration: "none" }}>Parity Signal</Link>
          <Link to="/investors" style={{ color: "inherit", textDecoration: "none" }}>About</Link>
          <SignInDropdown />
        </nav>
      </header>

      <section className="cs-home-section" style={{
        paddingTop: "100px", paddingBottom: "80px",
        maxWidth: "1100px",
        margin: "0 auto",
        textAlign: "center",
        position: "relative"
      }}>
        <div style={{
          position: "absolute", top: "0", left: "50%", transform: "translateX(-50%)",
          width: "600px", height: "400px",
          background: "radial-gradient(ellipse, rgba(20,184,166,0.08) 0%, transparent 70%)",
          pointerEvents: "none"
        }} />
        <p style={{
          fontSize: "13px", fontWeight: "500", letterSpacing: "0.12em",
          textTransform: "uppercase", color: "#14b8a6", marginBottom: "24px"
        }}>AI-Powered Benchmark Intelligence</p>
        <h1 style={{
          fontFamily: "'DM Serif Display', serif",
          fontSize: "clamp(36px, 5vw, 62px)",
          lineHeight: "1.1", fontWeight: "400",
          color: "#f1f5f9", marginBottom: "28px",
          letterSpacing: "-0.02em"
        }}>
          The evidence should be clear.<br />
          <span style={{ color: "#14b8a6" }}>The numbers should be right.</span>
        </h1>
        <p style={{
          fontSize: "18px", lineHeight: "1.7", color: "#94a3b8",
          maxWidth: "680px", margin: "0 auto 48px"
        }}>
          CivicScale builds AI tools that surface what's hidden — in medical bills,
          insurance claims, and public evidence. We make invisible analytical choices
          visible so individuals and organizations can make informed decisions.
        </p>
        <div style={{ display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap" }}>
          <Link to="/signal" style={{
            background: "linear-gradient(135deg, #0d9488, #14b8a6)",
            color: "#0a1628", border: "none", borderRadius: "8px",
            padding: "14px 28px", fontSize: "15px", fontWeight: "600",
            cursor: "pointer", fontFamily: "inherit", textDecoration: "none",
            display: "inline-block"
          }}>Explore Parity Signal &rarr;</Link>
          <Link to="/billing" style={{
            background: "linear-gradient(135deg, #2563eb, #3b82f6)",
            color: "#0a1628", border: "none", borderRadius: "8px",
            padding: "14px 28px", fontSize: "15px", fontWeight: "600",
            cursor: "pointer", fontFamily: "inherit", textDecoration: "none",
            display: "inline-block"
          }}>Billing Products &rarr;</Link>
        </div>
      </section>

      <section className="cs-home-section" style={{
        paddingTop: "0", paddingBottom: "80px", maxWidth: "900px",
        margin: "0 auto", textAlign: "center"
      }}>
        <div className="cs-home-quote-box" style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: "16px"
        }}>
          <p style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: "20px", fontStyle: "italic",
            color: "#cbd5e1", lineHeight: "1.7"
          }}>
            Most disagreements aren't about the facts — they're about which facts to
            emphasize. Sources make invisible choices about what to weight and what to
            ignore. The Parity Engine makes those choices visible.
          </p>
        </div>
      </section>

      <div className="cs-home-section" style={{
        display: "flex", alignItems: "center", gap: "20px",
        maxWidth: "1100px", margin: "0 auto", paddingTop: "0", paddingBottom: "48px"
      }}>
        <div style={{ flex: 1, height: "1px", background: "rgba(255,255,255,0.06)" }} />
        <span style={{
          fontSize: "12px", fontWeight: "600", letterSpacing: "0.1em",
          textTransform: "uppercase", color: "#64748b"
        }}>Two Product Lines, One Engine</span>
        <div style={{ flex: 1, height: "1px", background: "rgba(255,255,255,0.06)" }} />
      </div>

      <section className="cs-home-products-grid cs-home-section" style={{
        paddingTop: "0", paddingBottom: "100px", maxWidth: "1100px", margin: "0 auto"
      }}>
        <Link to="/signal" style={{ textDecoration: "none", color: "inherit", display: "flex" }}
          onMouseEnter={() => setHoveredProduct("signal")} onMouseLeave={() => setHoveredProduct(null)}>
          <div style={{
            background: hoveredProduct === "signal" ? "rgba(20,184,166,0.06)" : "rgba(255,255,255,0.02)",
            border: hoveredProduct === "signal" ? "1px solid rgba(20,184,166,0.25)" : "1px solid rgba(255,255,255,0.06)",
            borderRadius: "16px", padding: "40px", transition: "all 0.3s ease",
            cursor: "pointer", display: "flex", flexDirection: "column", width: "100%"
          }}>
            <div style={{ display: "inline-block", background: "rgba(20,184,166,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "20px", alignSelf: "flex-start" }}>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#14b8a6" }}>PARITY SIGNAL</span>
            </div>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "28px", fontWeight: "400", color: "#f1f5f9", marginBottom: "16px" }}>Evidence Intelligence</h2>
            <p style={{ fontSize: "15px", lineHeight: "1.7", color: "#94a3b8", marginBottom: "28px" }}>
              AI-scored evidence analysis for complex public issues. Subscribe to topics that matter to you and get transparent, grounded assessments of what the evidence actually says — from drug safety to public policy.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "28px" }}>
              {["GLP-1 Drugs", "Breast Cancer Therapies", "Social Media & Teen Mental Health"].map(t => (
                <span key={t} style={{ fontSize: "12px", padding: "5px 12px", borderRadius: "20px", background: "rgba(20,184,166,0.1)", color: "#5eead4", border: "1px solid rgba(20,184,166,0.2)" }}>{t}</span>
              ))}
              <span style={{ fontSize: "12px", padding: "5px 12px", borderRadius: "20px", background: "rgba(255,255,255,0.04)", color: "#64748b", fontStyle: "italic" }}>+ more coming</span>
            </div>
            <div style={{ display: "flex", gap: "24px", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "20px" }}>
              {[{ n: "559+", l: "Claims Scored" }, { n: "124", l: "Sources" }, { n: "6", l: "Dimensions" }].map(s => (
                <div key={s.l}>
                  <div style={{ fontSize: "20px", fontWeight: "600", color: "#14b8a6" }}>{s.n}</div>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>{s.l}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: "auto", paddingTop: "24px" }}>
              <span style={{ fontSize: "14px", fontWeight: "500", color: "#14b8a6" }}>Explore Signal &rarr;</span>
            </div>
          </div>
        </Link>

        <Link to="/billing" style={{ textDecoration: "none", color: "inherit", display: "flex" }}
          onMouseEnter={() => setHoveredProduct("billing")} onMouseLeave={() => setHoveredProduct(null)}>
          <div style={{
            background: hoveredProduct === "billing" ? "rgba(59,130,246,0.06)" : "rgba(255,255,255,0.02)",
            border: hoveredProduct === "billing" ? "1px solid rgba(59,130,246,0.25)" : "1px solid rgba(255,255,255,0.06)",
            borderRadius: "16px", padding: "40px", transition: "all 0.3s ease",
            cursor: "pointer", display: "flex", flexDirection: "column", width: "100%"
          }}>
            <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "20px", alignSelf: "flex-start" }}>
              <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>BILLING INTELLIGENCE</span>
            </div>
            <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "28px", fontWeight: "400", color: "#f1f5f9", marginBottom: "16px" }}>Healthcare Billing Analysis</h2>
            <p style={{ fontSize: "15px", lineHeight: "1.7", color: "#94a3b8", marginBottom: "28px" }}>
              AI-powered benchmark analysis for medical bills, insurance claims, and provider contracts. We surface the analytical choices that drive billing outcomes — for consumers, employers, and physician practices.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "28px" }}>
              {[{ name: "Parity Health", desc: "Consumer bill analysis", to: "/parity-health/" }, { name: "Parity Employer", desc: "Self-insured employer analytics", to: "/employer" }, { name: "Parity Provider", desc: "Practice contract & denial intelligence", to: "/provider" }].map(p => (
                <div key={p.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderRadius: "8px", background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.04)" }}>
                  <div>
                    <div style={{ fontSize: "14px", fontWeight: "600", color: "#e2e8f0" }}>{p.name}</div>
                    <div style={{ fontSize: "12px", color: "#64748b", marginTop: "2px" }}>{p.desc}</div>
                  </div>
                  <span style={{ fontSize: "13px", color: "#60a5fa" }}>&rarr;</span>
                </div>
              ))}
            </div>
            <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "20px" }}>
              <div style={{ fontSize: "15px", color: "#94a3b8" }}>
                <span style={{ color: "#60a5fa", fontWeight: "600" }}>$300B+</span> in estimated annual billing errors
              </div>
            </div>
            <div style={{ marginTop: "auto", paddingTop: "24px" }}>
              <span style={{ fontSize: "14px", fontWeight: "500", color: "#60a5fa" }}>View Billing Products &rarr;</span>
            </div>
          </div>
        </Link>
      </section>

      {/* Parity Audit CTA */}
      <section className="cs-home-section" style={{
        paddingTop: "0", paddingBottom: "80px", maxWidth: "1100px", margin: "0 auto"
      }}>
        <Link to="/audit" style={{ textDecoration: "none", color: "inherit", display: "block" }}
          onMouseEnter={() => setHoveredProduct("audit")} onMouseLeave={() => setHoveredProduct(null)}>
          <div style={{
            background: hoveredProduct === "audit"
              ? "linear-gradient(135deg, rgba(20,184,166,0.12), rgba(13,148,136,0.06))"
              : "linear-gradient(135deg, rgba(20,184,166,0.06), rgba(255,255,255,0.02))",
            border: hoveredProduct === "audit"
              ? "1px solid rgba(20,184,166,0.35)"
              : "1px solid rgba(20,184,166,0.15)",
            borderRadius: "16px", padding: "40px 48px",
            transition: "all 0.3s ease", cursor: "pointer",
            display: "flex", alignItems: "center", gap: "48px",
          }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: "inline-block", background: "rgba(20,184,166,0.15)", borderRadius: "8px", padding: "6px 14px", marginBottom: "16px" }}>
                <span style={{ fontSize: "12px", fontWeight: "700", color: "#14b8a6", letterSpacing: "0.08em" }}>FREE FOR PRACTICES</span>
              </div>
              <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "28px", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px" }}>
                Parity Audit
              </h2>
              <p style={{ fontSize: "16px", lineHeight: "1.7", color: "#94a3b8", marginBottom: "20px", maxWidth: "540px" }}>
                Find out what your payers owe you. Upload one month of remittance data and get a detailed contract integrity report within 5-7 business days. No cost. No commitment. No integration required.
              </p>
              <div style={{ display: "flex", gap: "24px", marginBottom: "20px" }}>
                {[
                  { icon: "1", label: "Upload 835 files" },
                  { icon: "2", label: "Add payer contracts" },
                  { icon: "3", label: "Get your report" },
                ].map(s => (
                  <div key={s.icon} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{
                      width: "24px", height: "24px", borderRadius: "50%",
                      background: "rgba(20,184,166,0.15)", display: "flex",
                      alignItems: "center", justifyContent: "center",
                      fontSize: "12px", fontWeight: "700", color: "#14b8a6",
                    }}>{s.icon}</div>
                    <span style={{ fontSize: "13px", color: "#cbd5e1" }}>{s.label}</span>
                  </div>
                ))}
              </div>
              <span style={{ fontSize: "15px", fontWeight: "600", color: "#14b8a6" }}>
                Start Your Free Audit &rarr;
              </span>
            </div>
            <div style={{
              flexShrink: 0, width: "180px", height: "180px", borderRadius: "16px",
              background: "rgba(20,184,166,0.08)", border: "1px solid rgba(20,184,166,0.15)",
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              gap: "8px",
            }}>
              <div style={{ fontSize: "42px", fontWeight: "700", color: "#14b8a6" }}>$0</div>
              <div style={{ fontSize: "13px", color: "#94a3b8", textAlign: "center" }}>No cost to practices</div>
              <div style={{ fontSize: "11px", color: "#64748b" }}>5-7 day delivery</div>
            </div>
          </div>
        </Link>
      </section>

      <section className="cs-home-section" style={{ paddingTop: "80px", paddingBottom: "80px", maxWidth: "1100px", margin: "0 auto", textAlign: "center" }}>
        <p style={{ fontSize: "13px", fontWeight: "500", letterSpacing: "0.12em", textTransform: "uppercase", color: "#64748b", marginBottom: "20px" }}>Powered By</p>
        <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "36px", fontWeight: "400", color: "#f1f5f9", marginBottom: "20px" }}>The Parity Engine</h2>
        <p style={{ fontSize: "16px", lineHeight: "1.7", color: "#94a3b8", maxWidth: "700px", margin: "0 auto 48px" }}>
          One domain-agnostic architecture that ingests publicly available benchmark data, normalizes it across geographies and time, applies anomaly scoring, and generates plain-language explanations. The same logic that compares a medical bill to a Medicare fee schedule also scores a health claim against the clinical evidence base.
        </p>
        <div style={{ display: "flex", justifyContent: "center", gap: "16px", flexWrap: "wrap" }}>
          {["Benchmark Normalization", "Anomaly Scoring", "Analytical Paths", "Evidence Scoring", "Consensus Mapping", "Plain-Language Explanations"].map(c => (
            <span key={c} style={{ fontSize: "13px", padding: "8px 16px", borderRadius: "8px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)", color: "#94a3b8" }}>{c}</span>
          ))}
        </div>
      </section>

      <section className="cs-home-section" style={{ paddingTop: "80px", paddingBottom: "80px", maxWidth: "1100px", margin: "0 auto" }}>
        <div style={{ textAlign: "center", marginBottom: "56px" }}>
          <p style={{ fontSize: "13px", fontWeight: "500", letterSpacing: "0.12em", textTransform: "uppercase", color: "#14b8a6", marginBottom: "20px" }}>Why This Requires AI — And Why Ours Is Different</p>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "36px", fontWeight: "400", color: "#f1f5f9", marginBottom: "20px" }}>AI that shows its work</h2>
          <p style={{ fontSize: "16px", lineHeight: "1.7", color: "#94a3b8", maxWidth: "700px", margin: "0 auto" }}>
            Most AI tools give you an answer. We show you how the answer was built — which evidence was weighted, what assumptions were made, and where reasonable people disagree. That's the difference between an AI that thinks for you and one that helps you think.
          </p>
        </div>
        <div className="cs-home-whyai-grid">
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "12px", padding: "32px" }}>
            <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(20,184,166,0.1)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "20px", fontSize: "20px" }}>&#x26A1;</div>
            <h3 style={{ fontSize: "17px", fontWeight: "600", color: "#f1f5f9", marginBottom: "12px" }}>Scale that humans can't match</h3>
            <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>A single medical bill can reference hundreds of procedure codes across dozens of fee schedules. A single drug safety topic spans thousands of clinical trial data points, FDA filings, and published studies. AI processes this volume in minutes — a human analyst would need weeks.</p>
          </div>
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "12px", padding: "32px" }}>
            <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(20,184,166,0.1)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "20px", fontSize: "20px" }}>&#x1F50D;</div>
            <h3 style={{ fontSize: "17px", fontWeight: "600", color: "#f1f5f9", marginBottom: "12px" }}>Transparent methodology, not a black box</h3>
            <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>Every score has a visible rationale. Every dimension is individually viewable. Every weight is disclosed. Our Analytical Paths technology shows you exactly why different sources reach different conclusions — by revealing which analytical choices each one made. You see the trade-offs and draw your own conclusions.</p>
          </div>
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "12px", padding: "32px" }}>
            <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(20,184,166,0.1)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "20px", fontSize: "20px" }}>&#x1F3D7;&#xFE0F;</div>
            <h3 style={{ fontSize: "17px", fontWeight: "600", color: "#f1f5f9", marginBottom: "12px" }}>Infrastructure, not a chat window</h3>
            <p style={{ fontSize: "14px", lineHeight: "1.7", color: "#94a3b8" }}>ChatGPT gives you a different answer every time you ask. CivicScale builds persistent, structured intelligence — scored claims, tracked over time, updated when new evidence emerges. Ask the same question next month and you'll see what changed, why it changed, and what triggered the shift. That's a living analytical system, not a conversation.</p>
          </div>
        </div>
      </section>

      <section className="cs-home-section" style={{ paddingTop: "60px", paddingBottom: "100px", maxWidth: "900px", margin: "0 auto" }}>
        <div className="cs-home-quote-box" style={{ background: "linear-gradient(135deg, rgba(20,184,166,0.05), rgba(59,130,246,0.05))", border: "1px solid rgba(255,255,255,0.06)", borderRadius: "16px", textAlign: "center" }}>
          <h3 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "24px", fontWeight: "400", color: "#f1f5f9", marginBottom: "16px" }}>Where We're Going</h3>
          <p style={{ fontSize: "15px", lineHeight: "1.8", color: "#94a3b8", maxWidth: "600px", margin: "0 auto" }}>
            Healthcare is where we start. Information asymmetry is where we're going. The same engine that analyzes medical bills and scores drug safety evidence can evaluate property tax assessments, insurance premium fairness, and policy claims across any domain where individuals face decisions they can't independently verify.
          </p>
        </div>
      </section>

      <footer className="cs-home-section" style={{ paddingTop: "40px", paddingBottom: "40px", borderTop: "1px solid rgba(255,255,255,0.06)", textAlign: "center", fontSize: "13px", color: "#475569" }}>
        &copy; CivicScale 2026. All rights reserved.
      </footer>
    </div>
  );
}
