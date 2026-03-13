import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import "./CivicScaleHomepage.css";
import "./InvestorsPage.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

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
  const [stats, setStats] = useState(null);
  const [topicCount, setTopicCount] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/signal/stats`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setStats)
      .catch(() => setStats(null));

    fetch(`${API_BASE}/api/signal/topics`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setTopicCount(Array.isArray(data) ? data.length : null))
      .catch(() => setTopicCount(null));
  }, []);

  const claimsCount = stats?.evidence_claims ?? null;
  const sourcesCount = stats?.evidence_sources ?? null;

  return (
    <div className="inv-dark-root" style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0", overflowX: "hidden", background: "#0a1628", minHeight: "100vh" }}>
      {/* NAV */}
      <header style={{ position: "sticky", top: 0, zIndex: 50, background: "rgba(10,22,40,0.95)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 2 }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ width: 3, height: 10, borderRadius: 2, background: "#94a3b8" }} />
                <div style={{ width: 3, height: 7, borderRadius: 2, background: "#0D7377" }} />
                <div style={{ width: 3, height: 4, borderRadius: 2, background: "#94a3b8" }} />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                <div style={{ width: 3, height: 4, borderRadius: 2, background: "#0D7377" }} />
                <div style={{ width: 3, height: 7, borderRadius: 2, background: "#94a3b8" }} />
                <div style={{ width: 3, height: 10, borderRadius: 2, background: "#0D7377" }} />
              </div>
            </div>
            <span style={{ color: "#f1f5f9", fontWeight: 700, fontSize: 18, letterSpacing: "-0.02em", fontFamily: "'DM Sans', sans-serif" }}>CivicScale</span>
          </a>
          <nav style={{ display: "flex", alignItems: "center", gap: 24, fontSize: 14, fontFamily: "'DM Sans', sans-serif" }}>
            <a href="https://employer.civicscale.ai" style={{ color: "#94a3b8", textDecoration: "none" }}>Employer</a>
            <a href="https://broker.civicscale.ai" style={{ color: "#94a3b8", textDecoration: "none" }}>Broker</a>
            <a href="https://provider.civicscale.ai" style={{ color: "#94a3b8", textDecoration: "none" }}>Provider</a>
            <a href="https://health.civicscale.ai" style={{ color: "#94a3b8", textDecoration: "none" }}>Health</a>
            <a href="https://signal.civicscale.ai" style={{ color: "#94a3b8", textDecoration: "none" }}>Signal</a>
            <Link to="/investors" style={{ color: "#f1f5f9", textDecoration: "none", fontWeight: 500 }}>Investors</Link>
          </nav>
        </div>
      </header>

      {/* HERO */}
      <section style={{ background: "#0a1628", padding: "100px 24px 60px", position: "relative", overflow: "hidden" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", textAlign: "center" }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "rgba(13,115,119,0.1)", color: "#0D7377", fontSize: 12, fontWeight: 600, padding: "4px 12px", borderRadius: 100, marginBottom: 20 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#0D7377" }} />
            Investor Overview
          </div>
          <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(32px, 4vw, 52px)", fontWeight: 400, color: "#f1f5f9", lineHeight: 1.15, letterSpacing: -1, marginBottom: 20 }}>
            The evidence should be clear.<br />The numbers should be right.
          </h1>
          <p style={{ fontSize: 17, fontWeight: 300, color: "rgba(255,255,255,0.6)", lineHeight: 1.7, maxWidth: 680, margin: "0 auto" }}>
            CivicScale builds AI-powered benchmark intelligence across domains where information asymmetry creates systematic cost inefficiency across the healthcare system. Four products live across two tracks &mdash; billing intelligence and evidence intelligence &mdash; powered by a single analytical engine.
          </p>
        </div>
      </section>

      {/* SECTION 1 — THE OPPORTUNITY */}
      <section className="cs-section" style={{ background: "#fff" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">The Opportunity</div>
          <h2 className="cs-section-title">Information asymmetry<br />is a structural problem</h2>
        </div>
        <div className="inv-opp-grid" style={{ marginTop: 40 }}>
          <div className="inv-opp-card">
            <div className="inv-opp-num">1 in 7</div>
            <div className="inv-opp-label">Medicare claims contain a billing error, according to the HHS Office of Inspector General &mdash; a rate that costs the system billions annually and falls disproportionately on patients and providers least equipped to challenge it</div>
          </div>
          <div className="inv-opp-card">
            <div className="inv-opp-num">4</div>
            <div className="inv-opp-label">Live products across billing intelligence and evidence intelligence</div>
          </div>
          <div className="inv-opp-card">
            <div className="inv-opp-num">{claimsCount != null ? claimsCount.toLocaleString() : "\u2014"}</div>
            <div className="inv-opp-label">Evidence claims scored across {sourcesCount != null ? sourcesCount.toLocaleString() : "\u2014"} sources with six-dimension methodology</div>
          </div>
        </div>
      </section>

      {/* SECTION 2 — PLATFORM ARCHITECTURE */}
      <section className="cs-section cs-platform-section">
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">Platform Architecture</div>
          <h2 className="cs-section-title">One engine. Two tracks. Four products.</h2>
          <p className="cs-section-sub">
            CivicScale is structured as a platform with a shared analytical core and domain-specific product layers. Healthcare billing is where it starts. It is not where it ends.
          </p>
        </div>
        <div className="inv-arch-grid">
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-navy" />
            <div className="inv-arch-name">CivicScale</div>
            <p className="inv-arch-desc">
              Parent infrastructure company. Benchmark datasets, normalization pipelines, anomaly detection, evidence scoring, and Analytical Paths methodology.
            </p>
          </div>
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-teal" />
            <div className="inv-arch-name">Parity Engine</div>
            <p className="inv-arch-desc">
              AI-powered benchmark intelligence layer. Normalizes data, scores anomalies, maps analytical choices, and generates plain-language explanations across all verticals.
            </p>
          </div>
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-teal" />
            <div className="inv-arch-name">Billing Intelligence</div>
            <p className="inv-arch-desc">
              Three products addressing healthcare billing from three positions: Parity Health (consumers), Parity Employer (self-insured employers), and Parity Provider (physician practices). All live.
            </p>
          </div>
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-teal" />
            <div className="inv-arch-name">Evidence Intelligence</div>
            <p className="inv-arch-desc">
              Parity Signal: six-dimension evidence scoring, consensus mapping, and Analytical Paths for complex public issues. {topicCount != null ? topicCount : "\u2014"} topics live with subscription billing. Parity Signal now classifies disagreements by type &mdash; weighting, completeness, or factual &mdash; surfaces which evidence is shared vs. asymmetric vs. contested, shows explicit weight delta statements, and identifies resolution pathways for contested facts.
            </p>
          </div>
          <div className="inv-arch-card">
            <div className="inv-arch-card-accent inv-arch-accent-muted" />
            <div className="inv-arch-name">Future Verticals</div>
            <p className="inv-arch-desc">
              Parity Property, Parity Insurance, Parity Finance. Same engine, new data domains. Phase 3 target.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION — THE PARITY INTELLIGENCE ENGINE */}
      <section className="cs-section" style={{ background: "#fff" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div className="cs-section-label">The Parity Intelligence Engine</div>
          <h2 className="cs-section-title">Four levels of intelligence</h2>
          <p className="cs-section-sub">
            Each level catches what the level below cannot. The combination &mdash; applied across both billing and evidence analysis &mdash; is what makes CivicScale defensible.
          </p>
        </div>

        {/* PART 1 — Four-Level Ladder */}
        <div className="inv-intel-ladder">
          {/* Level 1 — Detect */}
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
                <span className="inv-intel-label">Detect</span>
                <span className="inv-intel-badge inv-intel-badge-live">Live</span>
              </div>
              <div className="inv-intel-sublabel">Benchmark Comparison &amp; Evidence Extraction</div>
              <p className="inv-intel-desc">
                <strong>Billing:</strong> Compares every charge against 841K CMS rates, 2.2M NCCI edit pairs, 15K MUE limits, plus comprehensive NADAC drug pricing codes. Flags overcharges, unbundling, and coding violations. Accepts PDF, pasted text, and photo input.<br />
                <strong>Evidence:</strong> Extracts claims from {sourcesCount != null ? `${sourcesCount.toLocaleString()}+` : "\u2014"} sources and scores each across six dimensions: methodological rigor, sample size, recency, source authority, consistency, and effect magnitude.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> Overcharges, coding violations, weak or conflicting evidence claims
              </div>
            </div>
          </div>

          {/* Level 2 — Explain */}
          <div className="inv-intel-card inv-intel-card-live">
            <div className="inv-intel-connector inv-intel-connector-teal" />
            <div className="inv-intel-icon inv-intel-icon-navy">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
              </svg>
            </div>
            <div className="inv-intel-body">
              <div className="inv-intel-header">
                <span className="inv-intel-level">Level 2</span>
                <span className="inv-intel-label">Explain</span>
                <span className="inv-intel-badge inv-intel-badge-live">Live</span>
              </div>
              <div className="inv-intel-sublabel">Plain-Language Intelligence</div>
              <p className="inv-intel-desc">
                <strong>Billing:</strong> Interprets denial codes in plain language, explains why a charge diverges from benchmarks, and identifies whether a denial is a payer error or a contractual adjustment.<br />
                <strong>Evidence:</strong> Auto-generated glossaries (44&ndash;64 terms per topic) with inline tooltip definitions. Every technical term defined on first use. Statistics followed by plain-language translations.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> Misunderstood denials, opaque evidence claims, inaccessible technical language
              </div>
            </div>
          </div>

          {/* Level 3 — Prioritize & Act */}
          <div className="inv-intel-card inv-intel-card-live">
            <div className="inv-intel-connector inv-intel-connector-teal" />
            <div className="inv-intel-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
              </svg>
            </div>
            <div className="inv-intel-body">
              <div className="inv-intel-header">
                <span className="inv-intel-level">Level 3</span>
                <span className="inv-intel-label">Prioritize &amp; Act</span>
                <span className="inv-intel-badge inv-intel-badge-live">Live</span>
              </div>
              <div className="inv-intel-sublabel">Scoring, Appeals &amp; Consensus Mapping</div>
              <p className="inv-intel-desc">
                <strong>Billing:</strong> Scores denial appeal worthiness (high/medium/low), estimates revenue gaps in dollars, drafts appeal letters citing specific CMS guidelines, and benchmarks billing contractor performance.<br />
                <strong>Evidence:</strong> Maps consensus across hundreds of claims &mdash; where evidence agrees, where it diverges, and why. Key Debates section surfaces active disagreements with arguments for and against. Premium AI Q&amp;A answers questions from the scored evidence base. Disagreement-type classification distinguishes weighting disputes from completeness gaps from factual contests. Contested claims include resolution pathways identifying what category of evidence &mdash; empirical, definitional, disclosure, or methodological &mdash; would move the dispute toward resolution.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> Low-value appeals, missed revenue, hidden evidence disagreements
              </div>
            </div>
          </div>

          {/* Level 4 — Predict */}
          <div className="inv-intel-card inv-intel-card-future inv-intel-card-last">
            <div className="inv-intel-icon inv-intel-icon-muted">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
              </svg>
            </div>
            <div className="inv-intel-body">
              <div className="inv-intel-header">
                <span className="inv-intel-level">Level 4</span>
                <span className="inv-intel-label">Predict</span>
                <span className="inv-intel-badge inv-intel-badge-future">Phase 2</span>
              </div>
              <div className="inv-intel-sublabel">Proactive Intelligence &amp; Change Detection</div>
              <p className="inv-intel-desc">
                <strong>Billing:</strong> Pre-submission denial risk scoring flags high-risk claims before they reach the payer. Proactive underpayment alerts notify practices when payer behavior shifts.<br />
                <strong>Evidence:</strong> Continuous monitoring with automated re-scoring as new sources publish. Change detection alerts notify subscribers when new evidence shifts consensus on topics they follow.
              </p>
              <div className="inv-intel-catches">
                <span className="inv-intel-catches-label">Catches:</span> Preventable denials, emerging payer patterns, consensus shifts in real time
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
              <div>CivicScale</div>
              <div>General-Purpose AI</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Rate benchmark comparison</div>
              <div className="inv-intel-moat-parity">841K CMS rates, automated, instant</div>
              <div className="inv-intel-moat-human">No persistent data, hallucination risk</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Denial pattern intelligence</div>
              <div className="inv-intel-moat-parity">Cross-claim analysis, appeal generation</div>
              <div className="inv-intel-moat-human">Single-query, no historical context</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Evidence scoring infrastructure</div>
              <div className="inv-intel-moat-parity">{claimsCount != null ? claimsCount.toLocaleString() : "\u2014"} claims, 6 dimensions, persistent scores</div>
              <div className="inv-intel-moat-human">No persistent scoring, no versioning</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Analytical Paths</div>
              <div className="inv-intel-moat-parity">Shows invisible analytical choices</div>
              <div className="inv-intel-moat-human">Black box &mdash; no visibility into reasoning</div>
            </div>
            <div className="inv-intel-moat-row">
              <div className="inv-intel-moat-cap">Proprietary data moat</div>
              <div className="inv-intel-moat-parity">Crowdsourced commercial rates, growing</div>
              <div className="inv-intel-moat-human">No proprietary data accumulation</div>
            </div>
            <div className="inv-intel-moat-row inv-intel-moat-row-last">
              <div className="inv-intel-moat-cap">Cost per analysis</div>
              <div className="inv-intel-moat-parity">Near zero at scale</div>
              <div className="inv-intel-moat-human">Per-query cost, no compounding</div>
            </div>
          </div>
          <p className="inv-intel-moat-note">
            The proliferation of AI makes CivicScale&apos;s position stronger, not weaker. General-purpose AI gives institutions more tools. CivicScale gives individuals equivalent infrastructure. The gap widens without a platform on the other side.
          </p>
        </div>

        {/* PART 3 — Investor Summary Box */}
        <div style={{ maxWidth: 1100, margin: "0 auto", paddingTop: 56 }}>
          <div className="inv-intel-callout">
            <p>
              <strong>Analytical Paths</strong> is CivicScale&apos;s deepest differentiator: making invisible analytical choices visible. A payer denying a claim is making analytical choices about which rules to weight. A news outlet covering a drug trial is making analytical choices about which findings to emphasize. CivicScale shows these choices &mdash; in billing, it transforms appeals from &ldquo;we disagree&rdquo; into &ldquo;here is the specific choice you made and the evidence that undermines it.&rdquo; In evidence intelligence, it shows why different sources reach different conclusions about the same data. This is persistent infrastructure, not a prompt &mdash; and it compounds with every analysis. Historically, this level of analysis required teams of specialists and weeks of work. AI makes it available instantly, at a cost that puts individual patients, small employers, and independent providers on equal footing with large institutions &mdash; not by replacing expert judgment, but by giving everyone access to the same quality of evidence.
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
              <span className="inv-tl-phase">Phase 0 &mdash; Platform Build</span>
              <span className="inv-tl-badge inv-tl-badge-done">Complete</span>
            </div>
            <p className="inv-tl-desc">
              Four products live: Parity Health (multi-input bill analysis), Parity Employer (claims analytics with demo), Parity Provider (contract integrity with demo), Parity Signal (evidence intelligence with 3 scored topics). Analytical Paths with configurable weighting profiles. Stripe subscription billing. Benchmark observations database. Homepage with dual-track positioning. Authentication, privacy architecture, event analytics.
            </p>
          </div>

          {/* Phase 1 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot inv-tl-current" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 1 &mdash; Validation &amp; Commercialization</span>
              <span className="inv-tl-badge inv-tl-badge-current">In Progress</span>
              <span style={{ fontSize: 12, color: "#4a5568", fontWeight: 300 }}>Months 5&ndash;8</span>
            </div>
            <p className="inv-tl-desc">
              Provider validation with real 835 data from 3&ndash;5 practices. Turquoise Health commercial rate integration. Signal topic expansion to 10+. Founding team hire (Head of Clinical Accuracy + Head of Commercial). Validation gate: 1,000 active Health users, 3 Provider pilots, 10+ Signal topics.
            </p>
          </div>

          {/* Phase 2 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 2 &mdash; Revenue Scale</span>
              <span className="inv-tl-badge inv-tl-badge-future">Months 9&ndash;18</span>
            </div>
            <p className="inv-tl-desc">
              First 3&ndash;5 employer contracts. Provider trend analysis and full appeal generator. Signal change detection alerts. Community benchmark display (100+ observations per metro). Attorney referral network. Validation gate: $500K annualized employer ARR, 50+ provider practices.
            </p>
          </div>

          {/* Phase 3 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 3 &mdash; Multi-Vertical</span>
              <span className="inv-tl-badge inv-tl-badge-future">Months 19&ndash;36</span>
            </div>
            <p className="inv-tl-desc">
              Parity Property and Parity Insurance launch. Proprietary rate database at scale. PM system integrations. Signal expansion beyond healthcare. Validation gate: $3M ARR across all verticals.
            </p>
          </div>

          {/* Phase 4 */}
          <div className="inv-tl-item">
            <div className="inv-tl-dot" />
            <div className="inv-tl-header">
              <span className="inv-tl-phase">Phase 4 &mdash; Data Platform</span>
              <span className="inv-tl-badge inv-tl-badge-future">Months 37+</span>
            </div>
            <p className="inv-tl-desc">
              Proprietary benchmark database licensed to TPAs, insurers, researchers, and regulators. Combined provider contract + consumer EOB + crowdsourced observation data. Validation gate: $1M+ data licensing revenue.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 5 — DESIGN PRINCIPLES */}
      <section style={{ padding: "80px 24px", background: "#0f1a2e" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto", textAlign: "center" }}>
          <div style={{ color: "#0D7377", fontSize: 12, fontWeight: 600, letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 12 }}>Design Principles</div>
          <h2 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(28px, 3vw, 40px)", color: "#f1f5f9", letterSpacing: -0.5, marginBottom: 16, lineHeight: 1.2 }}>Built differently,<br />by design</h2>
          <p style={{ fontSize: 16, color: "#94a3b8", lineHeight: 1.7, fontWeight: 300, maxWidth: 700, margin: "0 auto 48px" }}>Every CivicScale product is built on four architectural principles that address regulatory, legal, and trust challenges simultaneously.</p>
        </div>
        <div className="inv-principles-grid">
          {[
            { num: "01", title: "Privacy by Architecture", desc: "Documents uploaded for analysis are processed in-memory on CivicScale servers and never stored \u2014 no raw files are written to disk or persisted in any database. Only structured, anonymized analytical results (such as extracted line items, scores, and benchmark comparisons) are retained. Original documents are discarded immediately after processing. This architecture ensures that sensitive patient, employer, and provider data cannot be exposed in a breach because it is never held." },
            { num: "02", title: "Analysis, Not Advocacy", desc: "CivicScale products produce benchmark reports and cite sources. They do not generate legal arguments or advise on strategy. In evidence intelligence, they show why sources disagree \u2014 they do not tell users what to believe. CivicScale is the infrastructure. The professional or individual decides what to do with the result." },
            { num: "03", title: "Transparent Methodology", desc: "Every flagged billing item cites its benchmark source. Every evidence score shows six dimension ratings. Analytical Paths makes invisible analytical choices visible. Users can verify every finding independently. Transparency protects CivicScale and builds compounding institutional trust." },
            { num: "04", title: "Data Network Effects", desc: "Every bill analyzed contributes anonymized data to a crowdsourced commercial rate database. Every evidence topic scored produces structured analytical metadata. These proprietary data assets grow more accurate over time \u2014 a compounding moat that no competitor can replicate from a standing start." },
          ].map((p) => (
            <div key={p.num} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: 32 }}>
              <div style={{ color: "#0D7377", fontSize: 13, fontWeight: 700, marginBottom: 8 }}>{p.num}</div>
              <div style={{ color: "#f1f5f9", fontSize: 17, fontWeight: 600, marginBottom: 10 }}>{p.title}</div>
              <p style={{ color: "#94a3b8", fontSize: 14, lineHeight: 1.7, fontWeight: 300, margin: 0 }}>{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* SECTION 6 — CTA */}
      <section className="cs-section inv-cta-section">
        <div className="inv-cta-content">
          <h2>Interested in CivicScale?</h2>
          <p>
            CivicScale is live and in active validation. We welcome conversations with investors, healthcare industry experts, potential employer partners, and anyone who recognizes the information asymmetry problem from their own experience.
          </p>
          <a href="mailto:fred@civicscale.ai" className="inv-cta-btn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect width="20" height="16" x="2" y="4" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
            fred@civicscale.ai
          </a>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ borderTop: "1px solid rgba(255,255,255,0.06)", padding: "32px 24px", textAlign: "center", background: "#060d1a" }}>
        <p style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.8, maxWidth: 600, margin: "0 auto" }}>
          CivicScale is operated by U.S. Photovoltaics, Inc. &middot; Florida &middot;{" "}
          <a href="https://civicscale.ai" style={{ color: "#0D7377", textDecoration: "none" }}>civicscale.ai</a>
          <br />
          <a href="mailto:fred@civicscale.ai" style={{ color: "#94a3b8", textDecoration: "none" }}>fred@civicscale.ai</a>
          {" "}&middot;{" "}
          <Link to="/privacy" style={{ color: "#94a3b8", textDecoration: "none" }}>Privacy</Link>
          {" "}&middot;{" "}
          <Link to="/terms" style={{ color: "#94a3b8", textDecoration: "none" }}>Terms</Link>
          <br />
          &copy; CivicScale 2026.
        </p>
      </footer>
    </div>
  );
}
