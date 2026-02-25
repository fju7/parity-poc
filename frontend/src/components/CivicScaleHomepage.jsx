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
          <Link to="/investors">Investors</Link>
          <Link to="/parity-health/" className="cs-nav-cta">Open Parity Health &rarr;</Link>
        </div>
      </nav>

      {/* HERO */}
      <section className="cs-hero">
        <div className="cs-hero-grid" />
        <div className="cs-hero-glow" />
        <div className="cs-hero-glow-2" />
        <div className="cs-hero-content">
          <div className="cs-hero-eyebrow">
            <span className="cs-hero-eyebrow-dot" />
            Institutional Benchmark Infrastructure
          </div>
          <h1>The data layer for<br /><em>institutional transparency</em></h1>
          <p className="cs-hero-sub">
            CivicScale normalizes publicly mandated institutional rate disclosures, applies AI anomaly scoring, and enables verifiable benchmark comparisons across regulated data domains.
          </p>
          <div className="cs-hero-actions">
            <Link to="/parity-health/" className="cs-btn-primary">
              Open Parity Health
              <span>&rarr;</span>
            </Link>
            <Link to="/investors" className="cs-btn-ghost">
              Project Overview
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

      {/* PLATFORM */}
      <section id="platform" className="cs-section cs-platform-section">
        <div className="cs-platform-grid">
          <div>
            <div className="cs-section-label">The Platform</div>
            <h2 className="cs-section-title">One engine.<br />Every domain.</h2>
            <p className="cs-section-sub">
              The Parity engine normalizes institutional data, scores anomalies, and powers vertical products across healthcare, insurance, property, and finance.
            </p>
          </div>
          <div>
            <div className="cs-platform-diagram">
              <div className="cs-diagram-row">
                <div className="cs-diagram-dot cs-dot-teal" />
                <div className="cs-diagram-label">Publicly mandated institutional data</div>
                <div className="cs-diagram-sublabel">MRF &middot; CMS &middot; FOIA</div>
              </div>
              <div className="cs-diagram-arrow">&darr;</div>
              <div className="cs-diagram-row">
                <div className="cs-diagram-dot cs-dot-teal" />
                <div className="cs-diagram-label">Machine-readable file ingestion &amp; normalization</div>
                <div className="cs-diagram-sublabel">CivicScale pipeline</div>
              </div>
              <div className="cs-diagram-arrow">&darr;</div>
              <div className="cs-diagram-row cs-highlight">
                <div className="cs-diagram-dot cs-dot-navy" />
                <div className="cs-diagram-label">Parity Engine — anomaly scoring &amp; benchmark comparison</div>
                <div className="cs-diagram-sublabel">AI-powered</div>
              </div>
              <div className="cs-diagram-arrow">&darr;</div>
              <div className="cs-diagram-row">
                <div className="cs-diagram-dot cs-dot-teal" />
                <div className="cs-diagram-label">Vertical product layer</div>
                <div className="cs-diagram-sublabel">Parity Health &middot; Insurance &middot; Property</div>
              </div>
            </div>
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

      {/* PRODUCTS */}
      <section className="cs-section cs-products-section">
        <div className="cs-products-header">
          <div className="cs-section-label">Products</div>
          <h2 className="cs-section-title">Benchmark intelligence<br />across institutional domains</h2>
          <p className="cs-section-sub">Each vertical applies the Parity engine to a distinct domain of publicly mandated rate disclosure.</p>
        </div>
        <div className="cs-products-grid">
          {/* Parity Health */}
          <Link to="/parity-health/" className="cs-product-card cs-live">
            <div className="cs-card-accent cs-accent-live" />
            <div className="cs-card-badge cs-badge-live">
              <span className="cs-badge-live-dot" />
              Live
            </div>
            <div className="cs-card-icon cs-icon-health">🏥</div>
            <div className="cs-card-name">Parity Health</div>
            <p className="cs-card-desc">
              Medical bill benchmark analysis against CMS Medicare rates and negotiated hospital rate data. Identifies anomalous charges with full source citations.
            </p>
            <span className="cs-card-link">
              Open Parity Health
              <span className="cs-card-link-arrow">&rarr;</span>
            </span>
          </Link>

          {/* Parity Insurance */}
          <div className="cs-product-card cs-soon">
            <div className="cs-card-accent cs-accent-soon" />
            <div className="cs-card-badge cs-badge-soon">Coming Soon</div>
            <div className="cs-card-icon cs-icon-insurance">📋</div>
            <div className="cs-card-name">Parity Insurance</div>
            <p className="cs-card-desc">
              Commercial insurance premium audit against industry classification benchmarks. Workers&apos; compensation and general liability misclassification detection.
            </p>
            <span className="cs-card-soon-text">Phase 3 — 2027</span>
          </div>

          {/* Parity Property */}
          <div className="cs-product-card cs-soon">
            <div className="cs-card-accent cs-accent-soon" />
            <div className="cs-card-badge cs-badge-soon">Coming Soon</div>
            <div className="cs-card-icon cs-icon-property">🏠</div>
            <div className="cs-card-name">Parity Property</div>
            <p className="cs-card-desc">
              Property tax assessment benchmark analysis against comparable sales data. Identifies likely over-assessments with attorney referral to tax appeal specialists.
            </p>
            <span className="cs-card-soon-text">Phase 3 — 2027</span>
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
