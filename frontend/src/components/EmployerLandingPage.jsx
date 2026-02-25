import { Link } from "react-router-dom";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

export default function EmployerLandingPage() {
  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
      {/* NAV */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div className="cs-nav-links">
          <Link to="/">Platform</Link>
          <Link to="/employer/login" className="cs-nav-cta">Employer Login &rarr;</Link>
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
            For Self-Insured Employers
          </div>
          <h1>See what your<br />health plan <em>really</em> costs</h1>
          <p className="cs-hero-sub">
            Your employees already use Parity Health to analyze their medical bills.
            With their consent, de-identified billing patterns flow into a private
            employer dashboard — giving you visibility into outlier providers, coding
            anomalies, and spend trends across your population.
          </p>
          <div className="cs-hero-actions">
            <Link to="/employer/login" className="cs-btn-primary">
              Open Dashboard
              <span>&rarr;</span>
            </Link>
            <a href="mailto:employers@civicscale.ai" className="cs-btn-ghost">
              Request a Demo
            </a>
          </div>
        </div>
      </section>

      {/* VALUE PROPS */}
      <section id="value" className="cs-section" style={{ background: "#fff" }}>
        <div className="cs-data-header">
          <div className="cs-section-label">Why CivicScale</div>
          <h2 className="cs-section-title">Benchmark intelligence<br />for benefits teams</h2>
        </div>
        <div className="cs-data-grid">
          <div className="cs-data-card">
            <div className="cs-data-card-accent cs-data-accent-public" />
            <div className="cs-data-num">01</div>
            <div className="cs-data-name">Zero PHI Risk</div>
            <p className="cs-data-desc">
              All data is de-identified before it ever reaches your dashboard.
              No names, no dates of birth, no diagnosis codes. Only CPT codes,
              anomaly scores, and aggregate trends. Privacy by architecture, not
              just by policy.
            </p>
          </div>
          <div className="cs-data-card">
            <div className="cs-data-card-accent cs-data-accent-licensed" />
            <div className="cs-data-num">02</div>
            <div className="cs-data-name">Identify Outlier Providers</div>
            <p className="cs-data-desc">
              See which providers consistently bill above CMS Medicare benchmarks.
              Spot coding patterns — unbundling, upcoding, site-of-service
              differentials — aggregated across your employee population.
            </p>
          </div>
          <div className="cs-data-card">
            <div className="cs-data-card-accent cs-data-accent-proprietary" />
            <div className="cs-data-num">03</div>
            <div className="cs-data-name">Powered by Your Employees</div>
            <p className="cs-data-desc">
              When employees opt in with their employer code, every bill analysis
              contributes de-identified data to your dashboard. The more employees
              participate, the richer your insight becomes.
            </p>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="cs-section cs-principles-section">
        <div className="cs-section-label">How It Works</div>
        <h2 className="cs-section-title">Three steps to<br />population-level insight</h2>
        <div className="cs-principles-grid" style={{ maxWidth: 900 }}>
          <div className="cs-principle">
            <div className="cs-principle-num">01</div>
            <div className="cs-principle-title">Distribute Your Code</div>
            <p className="cs-principle-desc">
              Share your unique employer code with employees. They enter it in
              Parity Health&apos;s settings when they opt into the employer dashboard.
            </p>
          </div>
          <div className="cs-principle">
            <div className="cs-principle-num">02</div>
            <div className="cs-principle-title">Employees Analyze Bills</div>
            <p className="cs-principle-desc">
              Each time an opted-in employee runs a bill analysis, de-identified
              line-item data is contributed to your dashboard. The employee&apos;s
              identity is cryptographically hashed.
            </p>
          </div>
          <div className="cs-principle">
            <div className="cs-principle-num">03</div>
            <div className="cs-principle-title">Review Your Dashboard</div>
            <p className="cs-principle-desc">
              Log in with your employer credentials to see aggregated trends,
              outlier providers, coding flags, and monthly spend patterns — all
              without any PHI.
            </p>
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
          <Link to="/employer/login">Employer Login</Link>
        </div>
      </footer>
    </div>
  );
}
