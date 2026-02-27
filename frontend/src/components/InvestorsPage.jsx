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

      {/* SECTION — THE PARITY INTELLIGENCE ENGINE */}
      <section className="cs-section" style={{ background: "#fff" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">The Parity Intelligence Engine</div>
          <h2 className="cs-section-title">Four levels of clinical intelligence</h2>
          <p className="cs-section-sub">
            Each level catches what the level below cannot. The combination is what makes Parity Health defensible.
          </p>
        </div>

        {/* PART 1 — Four-Level Ladder */}
        <div className="inv-intel-ladder">
          {/* Level 1 */}
          <div className="inv-intel-card inv-intel-card-live">
            <div className="inv-intel-connector inv-intel-connector-teal" />
            <div className="inv-intel-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
              </svg>
            </div>
            <div className="inv-intel-body">
              <div className="inv-intel-header">
                <span className="inv-intel-level">Level 1</span>
                <span className="inv-intel-label">Pattern Matching</span>
                <span className="inv-intel-badge inv-intel-badge-live">Live</span>
              </div>
              <div className="inv-intel-sublabel">Rules-Based Coding Checks</div>
              <p className="inv-intel-desc">
                Flags known high-risk codes, site-of-service mismatches, and E&amp;M complexity levels against hardcoded clinical rules. Fast, deterministic, zero false positives on covered cases.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> High-complexity billing codes, procedure/setting mismatches
              </div>
            </div>
          </div>

          {/* Level 2 */}
          <div className="inv-intel-card inv-intel-card-dev">
            <div className="inv-intel-connector inv-intel-connector-teal" />
            <div className="inv-intel-icon inv-intel-icon-navy">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M12 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M3.375 15h7.5m0 0c.621 0 1.125-.504 1.125-1.125M12 15v1.5" />
              </svg>
            </div>
            <div className="inv-intel-body">
              <div className="inv-intel-header">
                <span className="inv-intel-level">Level 2</span>
                <span className="inv-intel-label">CMS Rules Engine</span>
                <span className="inv-intel-badge inv-intel-badge-dev">In Development</span>
              </div>
              <div className="inv-intel-sublabel">NCCI &amp; MUE Table Validation</div>
              <p className="inv-intel-desc">
                Applies CMS&apos;s 250,000+ National Correct Coding Initiative edit pairs and Medically Unlikely Edit limits. Identifies unbundling violations and unit limit breaches against published government coding rules.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> Unbundling, impossible code combinations, unit limit violations
              </div>
            </div>
          </div>

          {/* Level 3 */}
          <div className="inv-intel-card inv-intel-card-future">
            <div className="inv-intel-connector inv-intel-connector-muted" />
            <div className="inv-intel-icon inv-intel-icon-muted">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
              </svg>
            </div>
            <div className="inv-intel-body">
              <div className="inv-intel-header">
                <span className="inv-intel-level">Level 3</span>
                <span className="inv-intel-label">Statistical Intelligence</span>
                <span className="inv-intel-badge inv-intel-badge-future">Phase 2</span>
              </div>
              <div className="inv-intel-sublabel">Population-Level Anomaly Detection</div>
              <p className="inv-intel-desc">
                Compares provider billing patterns against CMS utilization norms across millions of real claims. A provider billing the highest complexity code for 95% of patients when the national average is 30% is a detectable outlier.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> Systematic upcoding, provider-level billing pattern anomalies
              </div>
            </div>
          </div>

          {/* Level 4 */}
          <div className="inv-intel-card inv-intel-card-future inv-intel-card-last">
            <div className="inv-intel-icon inv-intel-icon-muted">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
              </svg>
            </div>
            <div className="inv-intel-body">
              <div className="inv-intel-header">
                <span className="inv-intel-level">Level 4</span>
                <span className="inv-intel-label">Clinical AI Reasoning</span>
                <span className="inv-intel-badge inv-intel-badge-future">Phase 2–3</span>
              </div>
              <div className="inv-intel-sublabel">LLM-Powered Clinical Plausibility</div>
              <p className="inv-intel-desc">
                Claude AI reasons about whether procedure combinations, diagnosis codes, and complexity levels are clinically coherent for a given encounter. Catches implausible combinations that no lookup table can identify.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> Clinically impossible combinations, diagnosis-procedure mismatches, specialty anomalies
              </div>
            </div>
          </div>
        </div>

        {/* PART 2 — Competitive Moat */}
        <div style={{ maxWidth: 1100, margin: "0 auto", paddingTop: 80 }}>
          <h3 className="inv-intel-moat-title">Why this is hard to replicate</h3>
          <div className="inv-intel-moat-table">
            <div className="inv-intel-moat-header">
              <div>Capability</div>
              <div>Parity Health</div>
              <div>Human Services (Goodbill etc.)</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Rate benchmark comparison</div>
              <div className="inv-intel-moat-parity">Automated, instant</div>
              <div className="inv-intel-moat-human">Manual review, days</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">CMS coding rules (NCCI/MUE)</div>
              <div className="inv-intel-moat-parity">Automated, 250K+ rules</div>
              <div className="inv-intel-moat-human">Partial, manual</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Statistical pattern detection</div>
              <div className="inv-intel-moat-parity">AI-powered at scale</div>
              <div className="inv-intel-moat-human">Not available</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Clinical plausibility reasoning</div>
              <div className="inv-intel-moat-parity">LLM inference, Phase 2</div>
              <div className="inv-intel-moat-human">Human reviewer, expensive</div>
            </div>
            <div className="inv-intel-moat-row inv-intel-moat-row-last">
              <div className="inv-intel-moat-cap">Cost per analysis</div>
              <div className="inv-intel-moat-parity">Near zero at scale</div>
              <div className="inv-intel-moat-human">25–30% of savings recovered</div>
            </div>
          </div>
          <p className="inv-intel-moat-note">
            Human billing advocacy services validate the market demand. CivicScale automates the same intelligence at a fraction of the cost.
          </p>
        </div>

        {/* PART 3 — Investor Summary Box */}
        <div style={{ maxWidth: 1100, margin: "0 auto", paddingTop: 56 }}>
          <div className="inv-intel-callout">
            <p>
              Most billing analysis tools catch overcharges. Parity Health also catches miscoding — wrong codes, impossible code combinations, and clinically implausible procedure patterns — using a layered intelligence system that starts with CMS&apos;s published coding rules and scales to LLM-powered clinical reasoning. The rate comparison layer is table stakes. The Parity Intelligence Engine is the moat: its accuracy compounds with every claim analyzed, and the false-positive calibration built from real claims cannot be replicated from a standing start.
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
              User accounts, bill history, commercial rate benchmark integration, enhanced anomaly scoring, employer dashboard MVP, attorney referral capture. Validation gate: 1,000 active users.
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
