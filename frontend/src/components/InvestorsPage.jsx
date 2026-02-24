import { Link } from "react-router-dom";
import "./CivicScaleHomepage.css";
import "./InvestorsPage.css";

function LogoIcon({ footer }) {
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

export default function InvestorsPage() {
  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
      {/* NAV */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div className="cs-nav-links">
          <Link to="/">Home</Link>
          <Link to="/investors">Investors</Link>
          <Link to="/parity-health/" className="cs-nav-cta">Open Parity Health &rarr;</Link>
        </div>
      </nav>

      {/* HERO */}
      <section className="inv-hero">
        <div className="cs-hero-grid" />
        <div className="cs-hero-glow" />
        <div className="cs-hero-glow-2" />
        <div className="inv-hero-content">
          <div className="cs-hero-eyebrow">
            <span className="cs-hero-eyebrow-dot" />
            Investor Overview
          </div>
          <h1>Institutional Benchmark Infrastructure</h1>
          <p className="inv-hero-sub">
            CivicScale builds AI-powered normalization and anomaly detection systems across regulated institutional data domains. Parity Health is the first vertical implementation.
          </p>
        </div>
      </section>

      {/* SECTION 1 — THE OPPORTUNITY */}
      <section className="cs-section" style={{ background: "#fff" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">The Opportunity</div>
          <h2 className="cs-section-title">A structural inefficiency<br />in institutional billing</h2>
        </div>
        <div className="inv-opp-grid" style={{ marginTop: 40 }}>
          <div className="inv-opp-card">
            <div className="inv-opp-num">$1,300<span>+</span></div>
            <div className="inv-opp-label">Average overcharge per erroneous medical bill</div>
          </div>
          <div className="inv-opp-card">
            <div className="inv-opp-num">25,000<span>+</span></div>
            <div className="inv-opp-label">Self-insured US employers with direct claims exposure</div>
          </div>
          <div className="inv-opp-card">
            <div className="inv-opp-num">$2–4M</div>
            <div className="inv-opp-label">Estimated total capital to sustained profitability</div>
          </div>
        </div>
      </section>

      {/* SECTION 2 — PLATFORM ARCHITECTURE */}
      <section className="cs-section cs-platform-section">
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">Platform Architecture</div>
          <h2 className="cs-section-title">One engine. Four layers.</h2>
          <p className="cs-section-sub">
            CivicScale is structured as a vertical SaaS platform with a shared intelligence core and domain-specific product layers.
          </p>
        </div>
        <div className="inv-arch-grid">
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-navy" />
            <div className="inv-arch-name">CivicScale</div>
            <p className="inv-arch-desc">
              Parent infrastructure company. Owns the benchmark datasets, normalization pipelines, and anomaly detection engine.
            </p>
          </div>
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-teal" />
            <div className="inv-arch-name">Parity Engine</div>
            <p className="inv-arch-desc">
              AI-powered benchmark intelligence layer. Normalizes institutional data and scores anomalies across all verticals.
            </p>
          </div>
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-teal" />
            <div className="inv-arch-name">Parity Health</div>
            <p className="inv-arch-desc">
              First vertical product. Medical bill benchmark analysis for consumers and self-insured employers. Live at civicscale.ai/parity-health.
            </p>
          </div>
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-muted" />
            <div className="inv-arch-name">Future Verticals</div>
            <p className="inv-arch-desc">
              Parity Insurance, Parity Property, Parity Finance. Same engine, new data domains. Phase 3 target.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 3 — PHASED ROADMAP */}
      <section className="cs-section" style={{ background: "#fff" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">Phased Roadmap</div>
          <h2 className="cs-section-title">Capital-efficient path<br />to profitability</h2>
          <p className="cs-section-sub">
            Each phase has a clear validation gate before proceeding. Capital deployment is staged against demonstrated traction.
          </p>
        </div>
        <div className="inv-timeline">
          {/* Phase 0 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot inv-tl-active" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 0 — Proof of Concept</span>
              <span className="inv-tl-badge inv-tl-badge-done">Complete</span>
            </div>
            <p className="inv-tl-desc">
              Browser-based PDF parsing, CMS benchmark lookup, anomaly scoring, plain-language report. Live at civicscale.ai.
            </p>
          </div>

          {/* Phase 1 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot inv-tl-current" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 1 — Consumer Launch</span>
              <span className="inv-tl-badge inv-tl-badge-current">In Progress</span>
              <span style={{ fontSize: 12, color: "#4a5568", fontWeight: 300 }}>Months 3–6</span>
            </div>
            <p className="inv-tl-desc">
              User accounts, bill history, Turquoise Health API integration, enhanced anomaly scoring, employer dashboard MVP, attorney referral capture. Validation gate: 1,000 active users.
            </p>
          </div>

          {/* Phase 2 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 2 — Employer Platform</span>
              <span className="inv-tl-badge inv-tl-badge-future">Months 7–18</span>
            </div>
            <p className="inv-tl-desc">
              Employer analytics dashboard, TPA claims feed integration, first employer contracts. Validation gate: $500K annualized employer ARR.
            </p>
          </div>

          {/* Phase 3 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 3 — Multi-Vertical</span>
              <span className="inv-tl-badge inv-tl-badge-future">Months 19–36</span>
            </div>
            <p className="inv-tl-desc">
              Parity Insurance and Parity Property launch. Same Parity engine, new data domains. Validation gate: $3M ARR.
            </p>
          </div>

          {/* Phase 4 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 4 — Data Platform</span>
              <span className="inv-tl-badge inv-tl-badge-future">Months 37+</span>
            </div>
            <p className="inv-tl-desc">
              Proprietary benchmark database licensed to TPAs, insurers, researchers, and regulators. Validation gate: $1M+ data licensing revenue.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 4 — ILLUSTRATIVE YEAR 3 REVENUE */}
      <section className="cs-section cs-platform-section">
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">Revenue Model</div>
          <h2 className="cs-section-title">Illustrative Year 3 revenue</h2>
          <p className="cs-section-sub">
            Multiple revenue streams across consumer, employer, referral, and data licensing channels.
          </p>
        </div>
        <div className="inv-rev-table">
          <div className="inv-rev-header">
            <div>Revenue Stream</div>
            <div>Driver</div>
            <div style={{ textAlign: "right" }}>Annual Revenue</div>
          </div>
          <div className="inv-rev-row">
            <div className="inv-rev-cell-label">Consumer Access (Parity Health)</div>
            <div className="inv-rev-cell">50,000 active users</div>
            <div className="inv-rev-cell-amount">$750K–$1.5M</div>
          </div>
          <div className="inv-rev-row">
            <div className="inv-rev-cell-label">Employer Platform</div>
            <div className="inv-rev-cell">20 contracts avg $72K ACV</div>
            <div className="inv-rev-cell-amount">$1.44M</div>
          </div>
          <div className="inv-rev-row">
            <div className="inv-rev-cell-label">Attorney Referral Network</div>
            <div className="inv-rev-cell">200 referrals @ ~$400 avg</div>
            <div className="inv-rev-cell-amount">$80K</div>
          </div>
          <div className="inv-rev-row">
            <div className="inv-rev-cell-label">Property &amp; Insurance Verticals</div>
            <div className="inv-rev-cell">Early stage</div>
            <div className="inv-rev-cell-amount">$200K–$400K</div>
          </div>
          <div className="inv-rev-row inv-rev-row-total">
            <div className="inv-rev-cell-label">Total</div>
            <div className="inv-rev-cell"></div>
            <div className="inv-rev-cell-amount">$2.47M–$3.42M</div>
          </div>
          <div className="inv-rev-note">
            Projections are illustrative, not a financial forecast. Revenue optimization begins in Phase 2. Phase 0 and 1 are optimized for user adoption and benchmark database growth.
          </div>
        </div>
      </section>

      {/* SECTION 5 — DESIGN PRINCIPLES */}
      <section className="cs-section cs-principles-section">
        <div className="cs-section-label">Design Principles</div>
        <h2 className="cs-section-title">Built differently,<br />by design</h2>
        <p className="cs-section-sub">Every CivicScale product is built on four architectural principles that address regulatory, legal, and trust challenges simultaneously.</p>
        <div className="cs-principles-grid">
          <div className="cs-principle">
            <div className="cs-principle-num">01</div>
            <div className="cs-principle-title">Privacy by Architecture</div>
            <p className="cs-principle-desc">Documents are processed locally on the user&apos;s device. Analysis results are stored locally. Only anonymized procedure codes reach our servers. This makes certain privacy violations technically impossible — not merely prohibited.</p>
          </div>
          <div className="cs-principle">
            <div className="cs-principle-num">02</div>
            <div className="cs-principle-title">Analysis, Not Advocacy</div>
            <p className="cs-principle-desc">CivicScale products produce anomaly reports and cite benchmarks. They do not generate legal arguments, draft dispute letters, or advise on strategy. CivicScale is the calculator. The professional decides what to do with the result.</p>
          </div>
          <div className="cs-principle">
            <div className="cs-principle-num">03</div>
            <div className="cs-principle-title">Benchmark Transparency</div>
            <p className="cs-principle-desc">Every flagged item cites its source. Users can verify every finding independently. This transparency protects CivicScale and makes the anomaly report credible to billing departments, legal counsel, and reviewing attorneys.</p>
          </div>
          <div className="cs-principle">
            <div className="cs-principle-num">04</div>
            <div className="cs-principle-title">Data Network Effects</div>
            <p className="cs-principle-desc">Every consented user interaction contributes to a proprietary benchmark database that grows more accurate over time — a compounding data asset that no competitor can replicate from a standing start.</p>
          </div>
        </div>
      </section>

      {/* SECTION 6 — CTA */}
      <section className="cs-section inv-cta-section">
        <div className="inv-cta-content">
          <h2>Interested in CivicScale?</h2>
          <p>
            CivicScale is currently in active development. We welcome conversations with investors, healthcare industry experts, and potential employer partners.
          </p>
          <a href="mailto:privacy@civicscale.ai" className="inv-cta-btn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="20" height="16" x="2" y="4" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
            privacy@civicscale.ai
          </a>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="cs-footer">
        <div className="cs-footer-logo">
          <LogoIcon footer />
          <span className="cs-footer-wordmark">CivicScale</span>
        </div>
        <div className="cs-footer-meta">
          Operated by U.S. Photovoltaics, Inc. &middot; Florida &middot; civicscale.ai<br />
          privacy@civicscale.ai
        </div>
        <div className="cs-footer-links">
          <Link to="/privacy">Privacy Policy</Link>
          <Link to="/terms">Terms of Service</Link>
          <Link to="/investors">Investors</Link>
        </div>
      </footer>
    </div>
  );
}
