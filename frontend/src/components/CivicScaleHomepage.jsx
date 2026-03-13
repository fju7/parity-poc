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
          <div className="cs-bar cs-bar-teal cs-bar-short" style={{ opacity: 0.7 }} />
          <div className="cs-bar cs-bar-short" style={{ background: "rgba(255,255,255,0.4)" }} />
          <div className="cs-bar cs-bar-teal cs-bar-tall" style={{ opacity: 0.7 }} />
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


export default function CivicScaleHomepage() {
  const [hoveredProduct, setHoveredProduct] = useState(null);

  return (
    <div className="cs-home-root">
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* ── Section 1: Navigation ── */}
      <header className="cs-home-header">
        <Link to="/" className="cs-home-logo-link">
          <div className="cs-home-logo-mark">C</div>
          <span className="cs-home-wordmark">CivicScale</span>
        </Link>
        <nav className="cs-home-nav">
          <a href="https://employer.civicscale.ai" className="cs-home-nav-link">Employer</a>
          <a href="https://broker.civicscale.ai" className="cs-home-nav-link">Broker</a>
          <a href="https://provider.civicscale.ai" className="cs-home-nav-link">Provider</a>
          <a href="https://health.civicscale.ai" className="cs-home-nav-link">Health</a>
          <a href="https://signal.civicscale.ai" className="cs-home-nav-link">Signal</a>
          <Link to="/investors" className="cs-home-nav-link cs-home-nav-investors">Investors</Link>
        </nav>
        <div className="cs-home-nav-actions" />
        <button className="cs-home-mobile-toggle" onClick={() => {
          document.querySelector('.cs-home-nav').classList.toggle('cs-home-nav--open');
        }} aria-label="Toggle navigation">
          <span /><span /><span />
        </button>
      </header>

      {/* ── Section 2: Hero ── */}
      <section className="cs-home-hero">
        <div className="cs-home-hero-glow" />
        <div className="cs-home-hero-glow-2" />
        <div className="cs-home-hero-content">
          <div className="cs-home-hero-eyebrow">
            <span className="cs-home-hero-eyebrow-dot" />
            Independent Healthcare Intelligence
          </div>
          <h1 className="cs-home-hero-h1">
            Healthcare costs more than it should.<br />
            <span className="cs-home-hero-accent">Now you can see exactly where.</span>
          </h1>
          <p className="cs-home-hero-sub">
            CivicScale gives employers, brokers, providers, and patients clear,
            independent data on what healthcare actually costs — so every
            stakeholder can make informed decisions, backed by evidence instead
            of carrier narratives.
          </p>
        </div>
      </section>

      {/* ── Section 3: The Problem ── */}
      <section className="cs-home-section cs-home-problem-section">
        <div className="cs-home-section-inner cs-home-problem-inner">
          <div className="cs-home-section-label">The Problem</div>
          <h2 className="cs-home-section-title">
            One claim. Four perspectives. Zero shared visibility.
          </h2>
          <p className="cs-home-section-sub" style={{ maxWidth: 720, margin: "0 auto 48px" }}>
            A single healthcare claim touches a patient, a physician, an employer,
            and a broker — each seeing a different piece of the same transaction,
            none of them with the full picture. The carrier sees everything.
          </p>
          <div className="cs-home-problem-grid">
            {PROBLEM_ITEMS.map((item) => (
              <div key={item.role} className="cs-home-problem-card">
                <div className="cs-home-problem-icon">{item.icon}</div>
                <h3 className="cs-home-problem-role">{item.role}</h3>
                <p className="cs-home-problem-desc">{item.desc}</p>
              </div>
            ))}
          </div>
          <p className="cs-home-problem-kicker">
            CivicScale sits at all four points — independent data, no carrier
            relationships, no conflicts of interest.
          </p>
        </div>
      </section>

      {/* ── Section 4: Product Cards ── */}
      <section className="cs-home-section cs-home-products-section">
        <div className="cs-home-section-inner">
          <div className="cs-home-section-label">Products</div>
          <h2 className="cs-home-section-title">Four products. One analytical engine.</h2>
          <p className="cs-home-section-sub" style={{ maxWidth: 680, margin: "0 auto 56px" }}>
            Each product serves a different stakeholder in the healthcare system.
            All are powered by the same benchmark and scoring infrastructure.
          </p>
          <div className="cs-home-product-cards">
            {PRODUCT_CARDS.map((card) => {
              const isExternal = card.to.startsWith("http");
              const Wrapper = isExternal ? "a" : Link;
              const linkProps = isExternal
                ? { href: card.to, target: "_blank", rel: "noopener noreferrer" }
                : { to: card.to };
              return (
              <Wrapper
                key={card.key}
                {...linkProps}
                className={`cs-home-product-card cs-home-product-card--${card.key}`}
                onMouseEnter={() => setHoveredProduct(card.key)}
                onMouseLeave={() => setHoveredProduct(null)}
                style={{
                  borderColor: hoveredProduct === card.key ? card.hoverBorder : undefined,
                }}
              >
                <div className="cs-home-product-accent" style={{ background: card.accentGrad }} />
                <div className="cs-home-product-badge" style={{ background: card.badgeBg, color: card.accent }}>
                  {card.label}
                </div>
                <h3 className="cs-home-product-heading">{card.heading}</h3>
                <p className="cs-home-product-body">{card.body}</p>
                <ul className="cs-home-product-bullets">
                  {card.bullets.map((b, i) => (
                    <li key={i}><span className="cs-home-bullet-check" style={{ color: card.accent }}>&#10003;</span> {b}</li>
                  ))}
                </ul>
                <div className="cs-home-product-footer">
                  <span className="cs-home-product-cta" style={{ color: card.accent }}>
                    {card.cta} <span>&rarr;</span>
                  </span>
                  {card.badge && (
                    <span className="cs-home-product-tier">{card.badge}</span>
                  )}
                </div>
              </Wrapper>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Section 5: The Parity Engine ── */}
      <section className="cs-home-section cs-home-engine-section">
        <div className="cs-home-section-inner">
          <div className="cs-home-section-label" style={{ color: "var(--cs-teal-light)" }}>Powered By</div>
          <h2 className="cs-home-section-title" style={{ color: "#f1f5f9" }}>
            The Parity Engine
          </h2>
          <p className="cs-home-section-sub" style={{ color: "rgba(255,255,255,0.6)", maxWidth: 740, margin: "0 auto 48px" }}>
            One domain-agnostic architecture that ingests publicly available
            benchmark data, normalizes it across geographies and time, applies
            anomaly scoring, and generates plain-language explanations. The same
            logic that compares a medical bill to a Medicare fee schedule also
            scores a health claim against the clinical evidence base.
          </p>
          <div className="cs-home-engine-capabilities">
            {ENGINE_CAPABILITIES.map((cap) => (
              <div key={cap.name} className="cs-home-engine-cap">
                <div className="cs-home-engine-cap-icon">{cap.icon}</div>
                <div>
                  <h4 className="cs-home-engine-cap-name">{cap.name}</h4>
                  <p className="cs-home-engine-cap-desc">{cap.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 6: Analytical Paths (investor-weight) ── */}
      <section className="cs-home-section cs-home-paths-section">
        <div className="cs-home-section-inner">
          <div className="cs-home-section-label">Core Technology</div>
          <h2 className="cs-home-section-title">
            Analytical Paths: See Why Sources Disagree
          </h2>
          <p className="cs-home-section-sub" style={{ maxWidth: 740, margin: "0 auto 40px" }}>
            Most disagreements aren't about the facts — they're about which facts
            to emphasize. Sources make invisible analytical choices about what to
            weight and what to ignore. The Parity Engine makes those choices visible.
          </p>
          <div className="cs-home-paths-demo">
            <div className="cs-home-paths-demo-header">
              <h4>Same Claim, Different Conclusions</h4>
              <p>Each profile weights the same six evidence dimensions differently — producing different composite scores from identical data.</p>
            </div>
            <div className="cs-home-paths-profiles">
              {ANALYTICAL_PROFILES.map((profile) => (
                <div key={profile.name} className="cs-home-paths-profile">
                  <div className="cs-home-paths-profile-name">{profile.name}</div>
                  <div className="cs-home-paths-profile-emphasis">{profile.emphasis}</div>
                  <div className="cs-home-paths-profile-maps">{profile.mapsTo}</div>
                </div>
              ))}
            </div>
          </div>
          <p className="cs-home-paths-kicker">
            This isn't prompt engineering. It's persistent scoring infrastructure —
            per-dimension scores, configurable weights, named analytical profiles —
            that makes competing conclusions legible.
          </p>
        </div>
      </section>

      {/* ── Section 7: Why Not Just Ask an AI? (investor-weight) ── */}
      <section className="cs-home-section cs-home-whyai-section">
        <div className="cs-home-section-inner">
          <div className="cs-home-section-label" style={{ color: "var(--cs-teal-light)" }}>
            Why This Requires AI — And Why Ours Is Different
          </div>
          <h2 className="cs-home-section-title" style={{ color: "#f1f5f9" }}>
            AI that shows its work
          </h2>
          <p className="cs-home-section-sub" style={{ color: "rgba(255,255,255,0.6)", maxWidth: 720, margin: "0 auto 56px" }}>
            Most AI tools give you an answer. We show you how the answer was
            built — which evidence was weighted, what assumptions were made,
            and where reasonable people disagree. That's the difference between
            an AI that thinks for you and one that helps you think.
          </p>
          <div className="cs-home-whyai-grid">
            {WHYAI_CARDS.map((card) => (
              <div key={card.title} className="cs-home-whyai-card">
                <div className="cs-home-whyai-icon">{card.icon}</div>
                <h3 className="cs-home-whyai-title">{card.title}</h3>
                <p className="cs-home-whyai-desc">{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 8: Where We're Going ── */}
      <section className="cs-home-section cs-home-vision-section">
        <div className="cs-home-section-inner cs-home-vision-inner">
          <div className="cs-home-section-label">Vision</div>
          <h2 className="cs-home-section-title">Where We're Going</h2>
          <p className="cs-home-vision-text">
            Healthcare is where we start — because a public reference price
            exists (Medicare), data is available due to price transparency
            regulations, the problem is visceral, and regulatory tailwinds
            (CAA, No Surprises Act) are forcing data into the open.
          </p>
          <p className="cs-home-vision-text">
            But the real thesis is broader: <strong>any market where a discoverable
            truth exists but powerful intermediaries profit from hiding it</strong> is
            a Parity Engine market. Insurance premiums. Property tax assessments.
            Policy claims in public debate.
          </p>
          <p className="cs-home-vision-kicker">
            Information asymmetry is the problem. Transparency infrastructure is the solution.
          </p>
        </div>
      </section>

      {/* ── Section 9: Final CTA ── */}
      <section className="cs-home-section cs-home-cta-section">
        <div className="cs-home-section-inner cs-home-cta-inner">
          <h2 className="cs-home-cta-title">Ready to see what your healthcare actually costs?</h2>
          <div className="cs-home-cta-paths">
            <a href="https://employer.civicscale.ai/signup" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm an employer</div>
              <div className="cs-home-cta-path-action">Start Free Trial &rarr;</div>
              <div className="cs-home-cta-path-note">30-day free trial, cancel anytime</div>
            </a>
            <a href="https://broker.civicscale.ai/signup" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm a broker</div>
              <div className="cs-home-cta-path-action">Start Free Trial &rarr;</div>
              <div className="cs-home-cta-path-note">30-day free trial, cancel anytime</div>
            </a>
            <a href="https://provider.civicscale.ai" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm a provider</div>
              <div className="cs-home-cta-path-action">Start Free Trial &rarr;</div>
              <div className="cs-home-cta-path-note">30-day free trial, cancel anytime</div>
            </a>
            <a href="https://health.civicscale.ai" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm a patient</div>
              <div className="cs-home-cta-path-action">Understand My Bill &rarr;</div>
              <div className="cs-home-cta-path-note">$9.95/month or $29/year, 30-day free trial</div>
            </a>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="cs-home-footer">
        <div className="cs-home-footer-inner">
          <div className="cs-home-footer-brand">
            <Link to="/" className="cs-home-footer-logo">
              <LogoIcon footer />
              <span className="cs-home-footer-wordmark">CivicScale</span>
            </Link>
            <p className="cs-home-footer-tagline">
              Independent healthcare intelligence, powered by the Parity Engine.
            </p>
          </div>
          <div className="cs-home-footer-links-group">
            <div className="cs-home-footer-col">
              <h5>Products</h5>
              <a href="https://employer.civicscale.ai">Parity Employer</a>
              <a href="https://broker.civicscale.ai">Broker Portal</a>
              <a href="https://provider.civicscale.ai">Parity Provider</a>
              <a href="https://health.civicscale.ai">Parity Health</a>
              <a href="https://signal.civicscale.ai">Parity Signal</a>
            </div>
            <div className="cs-home-footer-col">
              <h5>Company</h5>
              <Link to="/investors">Investors</Link>
              <Link to="/terms">Terms</Link>
              <Link to="/privacy">Privacy</Link>
            </div>
            <div className="cs-home-footer-col">
              <h5>Get Started</h5>
              <a href="https://employer.civicscale.ai/signup">Employer Trial</a>
              <a href="https://broker.civicscale.ai/signup">Broker Signup</a>
              <a href="https://employer.civicscale.ai/demo">See a Demo</a>
            </div>
          </div>
        </div>
        <div className="cs-home-footer-bottom">
          <span>&copy; CivicScale 2026. All rights reserved.</span>
          <span className="cs-home-footer-signal">
            Analytical intelligence powered by <a href="https://signal.civicscale.ai" style={{ color: "inherit" }}>Parity Signal</a>
          </span>
        </div>
      </footer>
    </div>
  );
}

/* ── Data ── */

const PROBLEM_ITEMS = [
  {
    icon: "\u{1F464}",
    role: "The Patient",
    desc: "Gets a bill they may not fully understand. Can't tell if they were overcharged or if a denial was justified.",
  },
  {
    icon: "\u{1FA7A}",
    role: "The Physician",
    desc: "Receives a payment that may not match their contracted rate. Denial patterns are invisible without analytics.",
  },
  {
    icon: "\u{1F3E2}",
    role: "The Employer",
    desc: "Pays a price that may be well above what comparable plans pay for the same procedure. No independent benchmark exists.",
  },
  {
    icon: "\u{1F4BC}",
    role: "The Broker",
    desc: "Advises on plan design with limited visibility into claims data. Carrier reports don't show what they don't want seen.",
  },
];

const PRODUCT_CARDS = [
  {
    key: "employer",
    label: "PARITY EMPLOYER",
    accent: "#3b82f6",
    accentGrad: "linear-gradient(90deg, #3b82f6, #60a5fa)",
    badgeBg: "rgba(59,130,246,0.12)",
    hoverBorder: "rgba(59,130,246,0.4)",
    heading: "See exactly where your health plan overpays",
    body: "Benchmark your plan against comparable employers. Analyze claims data to surface excess spend. Build leverage for your next renewal.",
    bullets: [
      "Industry-specific benchmarking (9 MEPS sectors)",
      "Claims analytics with provider-level detail",
      "Pharmacy benefit benchmarking with NADAC data",
    ],
    cta: "Start Free Trial",
    badge: "30-day free trial, cancel anytime",
    to: "https://employer.civicscale.ai",
  },
  {
    key: "broker",
    label: "BROKER PORTAL",
    accent: "#f59e0b",
    accentGrad: "linear-gradient(90deg, #f59e0b, #fbbf24)",
    badgeBg: "rgba(245,158,11,0.12)",
    hoverBorder: "rgba(245,158,11,0.4)",
    heading: "Better data for your book of business",
    body: "Run benchmarks for your clients, share interactive reports, and manage renewals with independent analytics your carriers can't provide.",
    bullets: [
      "Benchmark any client in minutes",
      "Shareable reports with client branding",
      "Renewal pipeline with 90-day alerts",
    ],
    cta: "Start Free Trial",
    badge: "30-day free trial, cancel anytime",
    to: "https://broker.civicscale.ai",
  },
  {
    key: "provider",
    label: "PARITY PROVIDER",
    accent: "#8b5cf6",
    accentGrad: "linear-gradient(90deg, #8b5cf6, #a78bfa)",
    badgeBg: "rgba(139,92,246,0.12)",
    hoverBorder: "rgba(139,92,246,0.4)",
    heading: "Find out what your payers actually owe you",
    body: "Upload remittance data and get a contract integrity audit. Surface underpayments, denial patterns, and billing discrepancies.",
    bullets: [
      "835 EDI parsing and contract comparison",
      "Denial pattern analysis with appeal letters",
      "Billing performance scorecard",
    ],
    cta: "Start Free Trial",
    badge: "30-day free trial, cancel anytime",
    to: "https://provider.civicscale.ai",
  },
  {
    key: "health",
    label: "PARITY HEALTH",
    accent: "#14b8a6",
    accentGrad: "linear-gradient(90deg, #0d9488, #14b8a6)",
    badgeBg: "rgba(20,184,166,0.12)",
    hoverBorder: "rgba(20,184,166,0.4)",
    heading: "Understand your medical bill in plain English",
    body: "Upload a bill or EOB and see what was charged, what your plan covered, and what your options are — including denial appeals.",
    bullets: [
      "Instant bill translation to plain language",
      "Medicare benchmark comparison",
      "AI-powered denial appeal letter generator",
    ],
    cta: "Understand My Bill",
    badge: "$9.95/month or $29/year, 30-day free trial",
    to: "https://health.civicscale.ai",
  },
];

const ENGINE_CAPABILITIES = [
  {
    icon: "\u{1F4CA}",
    name: "Benchmark Normalization",
    desc: "Ingests Medicare fee schedules, MEPS-IC data, state cost indices, and NADAC drug pricing into a unified reference layer.",
  },
  {
    icon: "\u{1F50D}",
    name: "Anomaly Scoring",
    desc: "Compares every claim, line item, and payment against normalized benchmarks to flag outliers and quantify excess spend.",
  },
  {
    icon: "\u{1F500}",
    name: "Analytical Paths",
    desc: "Shows why different analytical frameworks reach different conclusions from the same evidence — by making weight choices visible.",
  },
  {
    icon: "\u{2696}\u{FE0F}",
    name: "Evidence Scoring",
    desc: "Scores claims across six transparent dimensions: source quality, data support, reproducibility, consensus, recency, and rigor.",
  },
  {
    icon: "\u{1F310}",
    name: "Consensus Mapping",
    desc: "Maps where credible sources agree, disagree, or remain uncertain — with recorded arguments on each side.",
  },
  {
    icon: "\u{1F4DD}",
    name: "Plain-Language Output",
    desc: "Translates complex analytical results into clear, actionable language that requires no medical or policy background.",
  },
];

const ANALYTICAL_PROFILES = [
  { name: "Balanced", emphasis: "Equal weight across all dimensions", mapsTo: "Default analysis" },
  { name: "Regulatory", emphasis: "Source quality 40%, Consensus 30%", mapsTo: "How regulators see it" },
  { name: "Clinical", emphasis: "Rigor 35%, Reproducibility 30%", mapsTo: "How researchers see it" },
  { name: "Patient", emphasis: "Data support 35%, Recency 30%", mapsTo: "What matters to patients" },
];

const WHYAI_CARDS = [
  {
    icon: "\u26A1",
    title: "Scale that humans can't match",
    desc: "A single medical bill can reference hundreds of procedure codes across dozens of fee schedules. A single drug safety topic spans thousands of clinical trial data points. AI processes this volume in minutes — a human analyst would need weeks.",
  },
  {
    icon: "\u{1F50D}",
    title: "Transparent methodology, not a black box",
    desc: "Every score has a visible rationale. Every dimension is individually viewable. Every weight is disclosed. Analytical Paths shows you exactly why different sources reach different conclusions — by revealing which analytical choices each one made.",
  },
  {
    icon: "\u{1F3D7}\u{FE0F}",
    title: "Infrastructure, not a chat window",
    desc: "ChatGPT gives you a different answer every time you ask. CivicScale builds persistent, structured intelligence — scored claims tracked over time, updated when new evidence emerges. Ask the same question next month and see what changed, why, and what triggered the shift.",
  },
];
