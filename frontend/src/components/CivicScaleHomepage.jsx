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
          <Link to="/billing" className="cs-home-nav-link">Billing</Link>
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
            Five products. One platform.<br />
            <span className="cs-home-hero-accent">Intelligence that wasn't possible until now.</span>
          </h1>
          <p className="cs-home-hero-sub">
            AI makes it possible for every participant in healthcare — providers,
            billing companies, employers, brokers, and consumers — to see what
            was previously visible only to payers. CivicScale is built on that insight.
          </p>
        </div>
      </section>

      {/* ── Section 3: The Problem ── */}
      <section className="cs-home-section cs-home-problem-section">
        <div className="cs-home-section-inner cs-home-problem-inner">
          <div className="cs-home-section-label">The Problem</div>
          <h2 className="cs-home-section-title">
            One claim. Six perspectives. Now finally connected.
          </h2>
          <p className="cs-home-section-sub" style={{ maxWidth: 720, margin: "0 auto 48px" }}>
            A single healthcare claim touches six different parties — each seeing
            a different piece of the same transaction. AI makes it possible, for
            the first time, to give every party the intelligence they need.
          </p>
          <div className="cs-home-problem-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
            {PROBLEM_ITEMS.map((item) => (
              <div key={item.role} className="cs-home-problem-card" style={item.isCarrier ? {
                borderColor: "rgba(245,158,11,0.25)",
                background: "rgba(245,158,11,0.04)",
              } : undefined}>
                <div className="cs-home-problem-icon">{item.icon}</div>
                <h3 className="cs-home-problem-role">{item.role}</h3>
                <p className="cs-home-problem-desc">{item.desc}</p>
                {item.isCarrier && (
                  <p style={{ fontSize: 10, color: "#f59e0b", marginTop: 8, marginBottom: 0, fontStyle: "italic" }}>
                    The information advantage CivicScale addresses
                  </p>
                )}
              </div>
            ))}
          </div>
          <p className="cs-home-problem-kicker">
            CivicScale sits at all six points — independent data, no carrier
            relationships, no conflicts of interest. The intelligence that carriers
            have always had, now available to everyone else.
          </p>
        </div>
      </section>

      {/* ── Section 4: Product Cards ── */}
      <section className="cs-home-section cs-home-products-section">
        <div className="cs-home-section-inner">
          <div className="cs-home-section-label">Products</div>
          <h2 className="cs-home-section-title">Five products. Two tracks. One intelligence engine.</h2>
          <p className="cs-home-section-sub" style={{ maxWidth: 680, margin: "0 auto 48px" }}>
            Every product serves a different stakeholder. All are powered by the
            same benchmark infrastructure — and every claim makes the network smarter.
          </p>

          {/* Track 1 — Providers & Revenue Cycle */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#8b5cf6", marginBottom: 16 }}>
              For Healthcare Providers &amp; Revenue Cycle
            </div>
          </div>
          <div className="cs-home-product-cards" style={{ marginBottom: 48 }}>
            {PRODUCT_CARDS.filter(c => ["provider", "billing"].includes(c.key)).map((card) => {
              const isExternal = card.to.startsWith("http");
              const Wrapper = isExternal ? "a" : Link;
              const linkProps = isExternal
                ? { href: card.to, target: "_blank", rel: "noopener noreferrer" }
                : { to: card.to };
              return (
              <Wrapper key={card.key} {...linkProps}
                className={`cs-home-product-card cs-home-product-card--${card.key}`}
                onMouseEnter={() => setHoveredProduct(card.key)} onMouseLeave={() => setHoveredProduct(null)}
                style={{ borderColor: hoveredProduct === card.key ? card.hoverBorder : undefined }}>
                <div className="cs-home-product-accent" style={{ background: card.accentGrad }} />
                <div className="cs-home-product-badge" style={{ background: card.badgeBg, color: card.accent }}>{card.label}</div>
                <h3 className="cs-home-product-heading">{card.heading}</h3>
                <p className="cs-home-product-body">{card.body}</p>
                <ul className="cs-home-product-bullets">
                  {card.bullets.map((b, i) => (<li key={i}><span className="cs-home-bullet-check" style={{ color: card.accent }}>&#10003;</span> {b}</li>))}
                </ul>
                <div className="cs-home-product-footer">
                  <span className="cs-home-product-cta" style={{ color: card.accent }}>{card.cta} <span>&rarr;</span></span>
                  {card.badge && <span className="cs-home-product-tier">{card.badge}</span>}
                </div>
              </Wrapper>);
            })}
          </div>

          {/* Track 2 — Employers & Brokers */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#f59e0b", marginBottom: 16 }}>
              For Employers &amp; Brokers
            </div>
          </div>
          <div className="cs-home-product-cards" style={{ marginBottom: 48 }}>
            {PRODUCT_CARDS.filter(c => ["employer", "broker"].includes(c.key)).map((card) => {
              const isExternal = card.to.startsWith("http");
              const Wrapper = isExternal ? "a" : Link;
              const linkProps = isExternal ? { href: card.to, target: "_blank", rel: "noopener noreferrer" } : { to: card.to };
              return (
              <Wrapper key={card.key} {...linkProps}
                className={`cs-home-product-card cs-home-product-card--${card.key}`}
                onMouseEnter={() => setHoveredProduct(card.key)} onMouseLeave={() => setHoveredProduct(null)}
                style={{ borderColor: hoveredProduct === card.key ? card.hoverBorder : undefined }}>
                <div className="cs-home-product-accent" style={{ background: card.accentGrad }} />
                <div className="cs-home-product-badge" style={{ background: card.badgeBg, color: card.accent }}>{card.label}</div>
                <h3 className="cs-home-product-heading">{card.heading}</h3>
                <p className="cs-home-product-body">{card.body}</p>
                <ul className="cs-home-product-bullets">
                  {card.bullets.map((b, i) => (<li key={i}><span className="cs-home-bullet-check" style={{ color: card.accent }}>&#10003;</span> {b}</li>))}
                </ul>
                <div className="cs-home-product-footer">
                  <span className="cs-home-product-cta" style={{ color: card.accent }}>{card.cta} <span>&rarr;</span></span>
                  {card.badge && <span className="cs-home-product-tier">{card.badge}</span>}
                </div>
              </Wrapper>);
            })}
          </div>

          {/* Track 3 — Consumers */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "#14b8a6", marginBottom: 16 }}>
              For Consumers
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 0 }}>
            {PRODUCT_CARDS.filter(c => c.key === "health").map((card) => {
              const isExternal = card.to.startsWith("http");
              const Wrapper = isExternal ? "a" : Link;
              const linkProps = isExternal ? { href: card.to, target: "_blank", rel: "noopener noreferrer" } : { to: card.to };
              return (
              <Wrapper key={card.key} {...linkProps}
                className={`cs-home-product-card cs-home-product-card--${card.key}`}
                onMouseEnter={() => setHoveredProduct(card.key)} onMouseLeave={() => setHoveredProduct(null)}
                style={{ borderColor: hoveredProduct === card.key ? card.hoverBorder : undefined, maxWidth: 560, width: "100%" }}>
                <div className="cs-home-product-accent" style={{ background: card.accentGrad }} />
                <div className="cs-home-product-badge" style={{ background: card.badgeBg, color: card.accent }}>{card.label}</div>
                <h3 className="cs-home-product-heading">{card.heading}</h3>
                <p className="cs-home-product-body">{card.body}</p>
                <ul className="cs-home-product-bullets">
                  {card.bullets.map((b, i) => (<li key={i}><span className="cs-home-bullet-check" style={{ color: card.accent }}>&#10003;</span> {b}</li>))}
                </ul>
                <div className="cs-home-product-footer">
                  <span className="cs-home-product-cta" style={{ color: card.accent }}>{card.cta} <span>&rarr;</span></span>
                  {card.badge && <span className="cs-home-product-tier">{card.badge}</span>}
                </div>
              </Wrapper>);
            })}
          </div>
        </div>
      </section>

      {/* ── Signal — The Intelligence Layer ── */}
      <section className="cs-home-section" style={{ paddingTop: 48, paddingBottom: 48 }}>
        <div className="cs-home-section-inner" style={{ maxWidth: 800 }}>
          <div style={{
            background: "rgba(13,148,136,0.06)", border: "1px solid rgba(13,148,136,0.2)",
            borderRadius: 16, padding: "36px 40px", textAlign: "center",
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#0d9488", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
              PARITY SIGNAL — THE INTELLIGENCE LAYER
            </div>
            <p style={{ fontSize: 16, lineHeight: 1.7, color: "#94a3b8", margin: "0 0 12px", fontFamily: "'DM Serif Display', serif" }}>
              The cross-product intelligence engine that benchmarks every denial, every payer behavior,
              and every contract rate across the full CivicScale network.
            </p>
            <p style={{ fontSize: 14, color: "#64748b", margin: 0 }}>
              Every product gets smarter with every claim.
            </p>
            <a href="https://signal.civicscale.ai" style={{
              display: "inline-block", marginTop: 16, fontSize: 14, color: "#0d9488",
              textDecoration: "none", fontWeight: 500,
            }}>
              Learn about Signal &rarr;
            </a>
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
            <a href="https://employer.civicscale.ai" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm an employer</div>
              <div className="cs-home-cta-path-action">Learn More &rarr;</div>
              <div className="cs-home-cta-path-note">30-day free trial, cancel anytime</div>
            </a>
            <a href="https://broker.civicscale.ai" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm a broker</div>
              <div className="cs-home-cta-path-action">Learn More &rarr;</div>
              <div className="cs-home-cta-path-note">30-day free trial, cancel anytime</div>
            </a>
            <a href="https://provider.civicscale.ai" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm a provider</div>
              <div className="cs-home-cta-path-action">Learn More &rarr;</div>
              <div className="cs-home-cta-path-note">30-day free trial, cancel anytime</div>
            </a>
            <a href="https://health.civicscale.ai" className="cs-home-cta-path">
              <div className="cs-home-cta-path-label">I'm a patient</div>
              <div className="cs-home-cta-path-action">Learn More &rarr;</div>
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
    icon: "\u{1F4CA}",
    role: "The RCM Company",
    desc: "Manages denials for dozens of practices but lacks portfolio-level intelligence to detect systematic payer behavior.",
  },
  {
    icon: "\u{1F3E2}",
    role: "The Employer",
    desc: "Pays a price that may be well above what comparable plans pay for the same procedure. No independent benchmark exists.",
  },
  {
    icon: "\u{1F4BC}",
    role: "The Broker",
    desc: "Advises on plan design with limited visibility into claims data. Carrier-provided analytics reflect carrier priorities.",
  },
  {
    icon: "\u{1F3E6}",
    role: "The Carrier",
    desc: "Has always had full visibility across all parties. CivicScale exists to rebalance that equation.",
    isCarrier: true,
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
    cta: "Learn More",
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
    cta: "Learn More",
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
    cta: "Learn More",
    badge: "30-day free trial, cancel anytime",
    to: "https://provider.civicscale.ai",
  },
  {
    key: "billing",
    label: "PARITY BILLING",
    accent: "#3b82f6",
    accentGrad: "linear-gradient(90deg, #3b82f6, #60a5fa)",
    badgeBg: "rgba(59,130,246,0.12)",
    hoverBorder: "rgba(59,130,246,0.4)",
    heading: "Portfolio intelligence for RCM companies",
    body: "Manage multiple practices from a single dashboard. Surface cross-practice denial patterns, generate branded client reports, and prove your value.",
    bullets: [
      "Aggregate denial and payer analytics across all practices",
      "Cross-practice escalation with evidence packages",
      "White-label PDF reports and client portal",
    ],
    cta: "Learn More",
    badge: "First practice free, no card required",
    to: "/billing",
    track: "provider",
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
    cta: "Learn More",
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
