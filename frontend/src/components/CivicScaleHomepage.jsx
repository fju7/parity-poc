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

export default function CivicScaleHomepage() {
  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
      {/* NAV */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div className="cs-nav-links">
          <a href="#platform">Platform</a>
          <a href="#data">Data</a>
          <Link to="/employer">For Employers</Link>
          <Link to="/provider">For Providers</Link>
          <Link to="/investors">Investors</Link>
        </div>
      </nav>

      {/* HERO */}
      <section className="cs-hero">
        <div className="cs-hero-grid" />
        <div className="cs-hero-glow" />
        <div className="cs-hero-glow-2" />
        <div className="cs-hero-content cs-hero-content--wide">
          <div className="cs-hero-eyebrow">
            <span className="cs-hero-eyebrow-dot" />
            Institutional Benchmark Infrastructure
          </div>
          <h1>The data layer for<br /><em>institutional transparency</em></h1>
          <p className="cs-hero-sub">
            Normalizing healthcare costs, detecting billing anomalies, and surfacing pricing intelligence — across every market where institutional data asymmetry creates consumer harm.
          </p>

          {/* Two CTA cards */}
          <div className="cs-hero-cards">
            <Link to="/parity-health/" className="cs-hero-card">
              <div className="cs-hero-card-badge">
                <span className="cs-hero-card-dot" />
                Live
              </div>
              <div className="cs-hero-card-title">Parity Health</div>
              <div className="cs-hero-card-subtitle">For individuals &amp; families</div>
              <p className="cs-hero-card-desc">
                Analyze your medical bills against CMS benchmark rates. Detect coding anomalies. Request itemized bills with one click.
              </p>
              <span className="cs-hero-card-btn">
                Open Parity Health <span>&rarr;</span>
              </span>
            </Link>

            <Link to="/employer" className="cs-hero-card">
              <div className="cs-hero-card-badge">
                <span className="cs-hero-card-dot" />
                Live
              </div>
              <div className="cs-hero-card-title">Employer Dashboard</div>
              <div className="cs-hero-card-subtitle">For self-insured employers</div>
              <p className="cs-hero-card-desc">
                Anonymous aggregate billing intelligence across your workforce. Identify outlier providers and coding patterns.
              </p>
              <span className="cs-hero-card-btn">
                View Demo Dashboard <span>&rarr;</span>
              </span>
            </Link>

            <Link to="/provider" className="cs-hero-card">
              <div className="cs-hero-card-badge">
                <span className="cs-hero-card-dot" />
                Live
              </div>
              <div className="cs-hero-card-title">Parity Provider</div>
              <div className="cs-hero-card-subtitle">For independent practices</div>
              <p className="cs-hero-card-desc">
                Audit your payer contracts. Find what they owe you.
              </p>
              <span className="cs-hero-card-btn">
                Open Parity Provider <span>&rarr;</span>
              </span>
            </Link>
          </div>
        </div>
      </section>

      {/* STATS */}
      <div className="cs-stats-bar">
        <div className="cs-stat">
          <div className="cs-stat-num">96<span>%</span></div>
          <div className="cs-stat-label">US hospital coverage in benchmark database</div>
        </div>
        <div className="cs-stat">
          <div className="cs-stat-num">$1,300<span>+</span></div>
          <div className="cs-stat-label">Average overcharge per erroneous medical bill</div>
        </div>
        <div className="cs-stat">
          <div className="cs-stat-num">60<span>%</span></div>
          <div className="cs-stat-label">Of large employers self-insure healthcare claims</div>
        </div>
      </div>

      {/* PLATFORM PRODUCTS */}
      <section id="platform" className="cs-section cs-products-section">
        <div className="cs-products-header">
          <div className="cs-section-label">The Parity Engine</div>
          <h2 className="cs-section-title">One platform. Multiple markets.</h2>
          <p className="cs-section-sub">
            Every vertical where institutional pricing data creates systematic consumer disadvantage is an expansion opportunity.
          </p>
        </div>
        <div className="cs-products-grid-2x3">
          {/* LIVE: Parity Health */}
          <Link to="/parity-health/" className="cs-product-card cs-live">
            <div className="cs-card-accent cs-accent-live" />
            <div className="cs-card-badge cs-badge-live">
              <span className="cs-badge-live-dot" />
              Live
            </div>
            <div className="cs-card-icon cs-icon-health">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
            </div>
            <div className="cs-card-name">Parity Health</div>
            <p className="cs-card-desc">
              Medical bill analysis. Benchmark against CMS rates. Detect coding anomalies.
            </p>
            <span className="cs-card-link">
              Open App
              <span className="cs-card-link-arrow">&rarr;</span>
            </span>
          </Link>

          {/* LIVE: Employer Intelligence */}
          <Link to="/employer" className="cs-product-card cs-live">
            <div className="cs-card-accent cs-accent-live" />
            <div className="cs-card-badge cs-badge-live">
              <span className="cs-badge-live-dot" />
              Live
            </div>
            <div className="cs-card-icon cs-icon-employer">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/></svg>
            </div>
            <div className="cs-card-name">Employer Intelligence</div>
            <p className="cs-card-desc">
              Anonymous workforce billing analytics for self-insured employers.
            </p>
            <span className="cs-card-link">
              View Dashboard
              <span className="cs-card-link-arrow">&rarr;</span>
            </span>
          </Link>

          {/* LIVE: Parity Provider */}
          <Link to="/provider" className="cs-product-card cs-live">
            <div className="cs-card-accent cs-accent-live" />
            <div className="cs-card-badge cs-badge-live">
              <span className="cs-badge-live-dot" />
              Live
            </div>
            <div className="cs-card-icon cs-icon-provider">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4"/><line x1="20" y1="10" x2="20" y2="6"/><line x1="18" y1="8" x2="22" y2="8"/></svg>
            </div>
            <div className="cs-card-name">Parity Provider</div>
            <p className="cs-card-desc">
              For independent practices. Audit your payer contracts and find what they owe you.
            </p>
            <span className="cs-card-link">
              Open App
              <span className="cs-card-link-arrow">&rarr;</span>
            </span>
          </Link>

          {/* COMING SOON: Parity Property */}
          <div className="cs-product-card cs-soon">
            <div className="cs-card-accent cs-accent-soon" />
            <div className="cs-card-badge cs-badge-soon">Phase 3 — 2027</div>
            <div className="cs-card-icon cs-icon-property">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div className="cs-card-name">Parity Property</div>
            <p className="cs-card-desc">
              Property tax assessment anomaly detection. Benchmark residential assessments against comparable sales.
            </p>
            <span className="cs-card-soon-text">Coming Soon</span>
          </div>

          {/* COMING SOON: Parity Insurance */}
          <div className="cs-product-card cs-soon">
            <div className="cs-card-accent cs-accent-soon" />
            <div className="cs-card-badge cs-badge-soon">Phase 3 — 2027</div>
            <div className="cs-card-icon cs-icon-insurance">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <div className="cs-card-name">Parity Insurance</div>
            <p className="cs-card-desc">
              Auto and homeowner claim settlement benchmarking. Flag lowball offers against comparable settlements.
            </p>
            <span className="cs-card-soon-text">Coming Soon</span>
          </div>

          {/* COMING SOON: Parity Utility */}
          <div className="cs-product-card cs-soon">
            <div className="cs-card-accent cs-accent-soon" />
            <div className="cs-card-badge cs-badge-soon">Phase 4 — 2028</div>
            <div className="cs-card-icon cs-icon-utility">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            </div>
            <div className="cs-card-name">Parity Utility</div>
            <p className="cs-card-desc">
              Utility rate anomaly detection. Benchmark residential rates against regulatory filings and comparable accounts.
            </p>
            <span className="cs-card-soon-text">Coming Soon</span>
          </div>

          {/* COMING SOON: Parity Finance */}
          <div className="cs-product-card cs-soon">
            <div className="cs-card-accent cs-accent-soon" />
            <div className="cs-card-badge cs-badge-soon">Phase 4 — 2028</div>
            <div className="cs-card-icon cs-icon-finance">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            </div>
            <div className="cs-card-name">Parity Finance</div>
            <p className="cs-card-desc">
              Consumer lending rate benchmarking. Detect above-market rates on mortgages, auto loans, and credit.
            </p>
            <span className="cs-card-soon-text">Coming Soon</span>
          </div>
        </div>
      </section>

      {/* THREE-PATH CTA */}
      <section className="cs-section cs-paths-section">
        <div className="cs-paths-grid">
          <div className="cs-path-card">
            <div className="cs-path-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <div className="cs-path-title">I have a medical bill</div>
            <p className="cs-path-desc">Upload your bill and get a benchmark analysis in minutes.</p>
            <Link to="/parity-health/" className="cs-btn-primary cs-path-btn">
              Analyze My Bill <span>&rarr;</span>
            </Link>
          </div>

          <div className="cs-path-card">
            <div className="cs-path-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/></svg>
            </div>
            <div className="cs-path-title">I manage employee benefits</div>
            <p className="cs-path-desc">See anonymous billing intelligence across your workforce.</p>
            <Link to="/employer" className="cs-btn-primary cs-path-btn">
              Request Employer Access <span>&rarr;</span>
            </Link>
          </div>

          <div className="cs-path-card">
            <div className="cs-path-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3"/><path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4"/><line x1="20" y1="10" x2="20" y2="6"/><line x1="18" y1="8" x2="22" y2="8"/></svg>
            </div>
            <div className="cs-path-title">I run a medical practice</div>
            <p className="cs-path-desc">Audit your payer contracts and find what they owe you.</p>
            <Link to="/provider" className="cs-btn-primary cs-path-btn">
              Open Parity Provider <span>&rarr;</span>
            </Link>
          </div>

          <div className="cs-path-card">
            <div className="cs-path-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            </div>
            <div className="cs-path-title">I&apos;m an investor or advisor</div>
            <p className="cs-path-desc">Learn about CivicScale&apos;s platform architecture and expansion roadmap.</p>
            <Link to="/investors" className="cs-btn-ghost cs-path-btn">
              Investor Overview <span>&rarr;</span>
            </Link>
          </div>
        </div>
      </section>

      {/* DATA INFRASTRUCTURE */}
      <section id="data" className="cs-section" style={{ background: "#fff" }}>
        <div className="cs-data-header">
          <div className="cs-section-label">Data Infrastructure</div>
          <h2 className="cs-section-title">Three layers of<br />benchmark accuracy</h2>
        </div>
        <div className="cs-data-grid">
          <div className="cs-data-card">
            <div className="cs-data-card-accent cs-data-accent-public" />
            <div className="cs-data-num">01</div>
            <div className="cs-data-name">Public Foundation</div>
            <p className="cs-data-desc">
              CMS Medicare Physician Fee Schedule and OPPS rates. 841,000+ procedure rates updated annually. The floor benchmark for every analysis. Free and publicly available.
            </p>
          </div>
          <div className="cs-data-card">
            <div className="cs-data-card-accent cs-data-accent-licensed" />
            <div className="cs-data-num">02</div>
            <div className="cs-data-name">Licensed Intelligence</div>
            <p className="cs-data-desc">
              Turquoise Health Clear Rates — negotiated rate data from 96% of US hospitals and 95% of commercial lives. The difference between Medicare floor rates and what your insurer actually contracted to pay. Phase 1 integration.
            </p>
          </div>
          <div className="cs-data-card">
            <div className="cs-data-card-accent cs-data-accent-proprietary" />
            <div className="cs-data-num">03</div>
            <div className="cs-data-name">Proprietary Network</div>
            <p className="cs-data-desc">
              User-consented, de-identified EOB aggregation. Every analysis contributes to a proprietary benchmark database that grows more accurate over time. The long-term data moat no competitor can replicate from a standing start.
            </p>
          </div>
        </div>
      </section>

      {/* PRINCIPLES */}
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
