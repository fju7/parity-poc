import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function EmployerSharedReport() {
  const { shareToken } = useParams();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!shareToken) return;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/employer/shared-report/${shareToken}`);
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || "Report not found");
        }
        setData(await res.json());
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    })();
  }, [shareToken]);

  if (loading) {
    return (
      <Page>
        <div style={{ textAlign: "center", paddingTop: 120 }}>
          <div style={{ width: 40, height: 40, border: "3px solid #e2e8f0", borderTopColor: "#0D7377", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
          <p style={{ color: "#64748b", fontSize: 15 }}>Loading your benchmark report...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </Page>
    );
  }

  if (error) {
    return (
      <Page>
        <div style={{ textAlign: "center", paddingTop: 120 }}>
          <p style={{ fontSize: 40, marginBottom: 16 }}>!</p>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: "#1B3A5C", marginBottom: 12 }}>Report Not Found</h2>
          <p style={{ fontSize: 14, color: "#64748b", marginBottom: 24 }}>{error}</p>
          <Link to="/billing/employer" style={{ color: "#0D7377", fontWeight: 600, textDecoration: "none" }}>
            Go to Parity Employer &rarr;
          </Link>
        </div>
      </Page>
    );
  }

  const bench = data.benchmark_result || {};
  const res = bench.result || {};
  const dist = bench.distribution || {};
  const benchmarks = bench.benchmarks || {};
  const input = bench.input || {};

  const percentile = res.percentile || 50;
  const pepm = input.pepm_input || data.estimated_pepm || 0;
  const gapMonthly = res.dollar_gap_monthly || 0;
  const gapAnnual = res.dollar_gap_annual || 0;
  const medianPepm = benchmarks.adjusted_median_pepm || 0;

  const fmt = (n) => n != null ? n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : "—";

  // Distribution markers for gauge
  const markers = [
    { label: "P10", value: dist.p10, pct: 10 },
    { label: "P25", value: dist.p25, pct: 25 },
    { label: "P50", value: dist.p50, pct: 50 },
    { label: "P75", value: dist.p75, pct: 75 },
    { label: "P90", value: dist.p90, pct: 90 },
  ];

  // Cost drivers
  const costDrivers = [];
  if (gapMonthly > 0 && data.industry) {
    costDrivers.push({
      label: "Industry positioning",
      detail: `${data.industry} employers in ${data.state || "your state"} face higher specialist and facility rates than the national median.`,
    });
  }
  if (percentile > 60) {
    costDrivers.push({
      label: "Network pricing premium",
      detail: "Your carrier's negotiated rates likely include significant markups over Medicare benchmarks, especially for outpatient procedures.",
    });
  }
  if (data.carrier && data.carrier !== "Self-insured/TPA") {
    costDrivers.push({
      label: "Carrier structure",
      detail: `Fully-insured plans with carriers like ${data.carrier} often include embedded margins that are opaque to employers.`,
    });
  }
  if (costDrivers.length < 3) {
    costDrivers.push({
      label: "Plan design gaps",
      detail: "Copay structures, out-of-network exposure, and missing steering incentives often compound cost variances.",
    });
  }

  return (
    <Page>
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 24px 80px" }}>
        {/* Broker Attribution Header */}
        {(data.broker_firm || data.broker_name) && (
          <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: "14px 20px", marginBottom: 28, display: "flex", alignItems: "center", gap: 14 }}>
            {data.broker_logo_url ? (
              <img src={data.broker_logo_url} alt="" style={{ height: 32, width: "auto", objectFit: "contain", borderRadius: 4 }} />
            ) : (
              <div style={{ width: 36, height: 36, borderRadius: 8, background: "#f0fdfa", border: "1px solid #99f6e4", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0D7377", flexShrink: 0 }}>
                {(data.broker_firm || "B")[0].toUpperCase()}
              </div>
            )}
            <div>
              <p style={{ margin: 0, fontSize: 13, color: "#475569" }}>
                Benefits analysis prepared by{" "}
                <strong>{data.broker_name || data.broker_firm}</strong>
                {data.broker_name && data.broker_firm && ` \u00B7 ${data.broker_firm}`}
              </p>
              {data.broker_email && (
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "#94a3b8" }}>
                  Questions? Contact{" "}
                  <a href={`mailto:${data.broker_email}`} style={{ color: "#0D7377", textDecoration: "none" }}>{data.broker_email}</a>
                </p>
              )}
            </div>
          </div>
        )}

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "#1B3A5C", margin: "0 0 8px" }}>
            Your Benefits Benchmark — {data.company_name}
          </h1>
          <p style={{ fontSize: 15, color: "#64748b", margin: 0 }}>
            Prepared by <strong>{data.broker_firm || "your broker"}</strong> using Parity Employer
          </p>
          <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 8 }}>
            Generated {new Date(data.created_at).toLocaleDateString()}
          </p>
        </div>

        {/* Percentile + Gap Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: 28, textAlign: "center" }}>
            <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 8px", fontWeight: 500 }}>PEPM PERCENTILE</p>
            <p style={{
              fontSize: 52, fontWeight: 700, margin: 0,
              color: percentile > 60 ? "#EF4444" : percentile > 40 ? "#f59e0b" : "#22c55e",
            }}>
              {Math.round(percentile)}<span style={{ fontSize: 20 }}>th</span>
            </p>
            <p style={{ fontSize: 14, color: "#475569", marginTop: 8, lineHeight: 1.6 }}>
              {res.interpretation}
            </p>
          </div>
          <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: 28, textAlign: "center" }}>
            <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 8px", fontWeight: 500 }}>MONTHLY GAP VS MEDIAN</p>
            <p style={{
              fontSize: 52, fontWeight: 700, margin: 0,
              color: gapMonthly > 0 ? "#EF4444" : "#22c55e",
            }}>
              {gapMonthly > 0 ? "+" : ""}{fmt(gapMonthly)}
            </p>
            <p style={{ fontSize: 14, color: "#475569", marginTop: 8, lineHeight: 1.6 }}>
              {fmt(pepm)} PEPM vs {fmt(medianPepm)} adjusted median
            </p>
          </div>
        </div>

        {/* Distribution Bar */}
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: 24, marginBottom: 28 }}>
          <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 16px", fontWeight: 500 }}>PEPM DISTRIBUTION — {data.industry || "All Industries"} in {data.state || "US"}</p>
          <div style={{ position: "relative", height: 48, background: "linear-gradient(90deg, #22c55e 0%, #f59e0b 50%, #EF4444 100%)", borderRadius: 8, marginBottom: 24 }}>
            {/* Your position marker */}
            <div style={{
              position: "absolute", left: `${Math.min(Math.max(percentile, 2), 98)}%`, top: -8,
              transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center",
            }}>
              <div style={{ width: 0, height: 0, borderLeft: "8px solid transparent", borderRight: "8px solid transparent", borderTop: "8px solid #1B3A5C" }} />
              <div style={{ background: "#1B3A5C", color: "#fff", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 700, marginTop: -2 }}>
                You: {fmt(pepm)}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            {markers.map((m) => (
              <div key={m.label} style={{ textAlign: "center", fontSize: 11 }}>
                <p style={{ color: "#94a3b8", margin: 0 }}>{m.label}</p>
                <p style={{ color: "#475569", fontWeight: 600, margin: "2px 0 0" }}>{m.value ? fmt(m.value) : "—"}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Annual Impact */}
        {gapAnnual !== 0 && (
          <div style={{
            background: gapAnnual > 0 ? "#fef2f2" : "#f0fdf4",
            border: `1px solid ${gapAnnual > 0 ? "#fecaca" : "#bbf7d0"}`,
            borderRadius: 14, padding: 20, marginBottom: 28, textAlign: "center",
          }}>
            <p style={{ fontSize: 13, color: gapAnnual > 0 ? "#991b1b" : "#166534", margin: 0 }}>
              Estimated annual gap per employee: <strong>{gapAnnual > 0 ? "+" : ""}{fmt(gapAnnual)}</strong>
              {data.employee_count && (
                <span> · Total estimated annual impact: <strong>{fmt(gapAnnual * data.employee_count)}</strong></span>
              )}
            </p>
          </div>
        )}

        {/* Top 3 Cost Drivers */}
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 14, padding: 24, marginBottom: 28 }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>Top Cost Drivers</p>
          {costDrivers.slice(0, 3).map((d, i) => (
            <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12, padding: "12px 16px", background: "#f8fafc", borderRadius: 8 }}>
              <div style={{ width: 24, height: 24, borderRadius: "50%", background: "#fef2f2", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#EF4444", flexShrink: 0 }}>
                {i + 1}
              </div>
              <div>
                <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "#1B3A5C" }}>{d.label}</p>
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b", lineHeight: 1.6 }}>{d.detail}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Data Source Badges */}
        <div style={{ display: "flex", gap: 8, justifyContent: "center", marginBottom: 28, flexWrap: "wrap" }}>
          {[
            "841K+ CMS Medicare rates",
            `${data.industry || "Industry"} benchmarks`,
            `${data.state || "State"} cost index`,
            "MEPS/KFF employer data",
          ].map((badge) => (
            <span key={badge} style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 20, padding: "4px 12px", fontSize: 11, color: "#0D7377", fontWeight: 500 }}>
              {badge}
            </span>
          ))}
        </div>

        {/* Framing Note */}
        <div style={{ background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 14, padding: 20, marginBottom: 32 }}>
          <p style={{ fontSize: 14, color: "#92400e", lineHeight: 1.7, margin: 0 }}>
            This benchmark reflects where your health spend sits relative to {data.industry || "similar"} employers
            in {data.state || "your state"} — it's a starting point for your renewal conversation, not a report card
            on your current plan. Costs above the median are common and driven by many factors including which providers
            your employees use, your plan's network structure, and regional market pricing. Your broker prepared this
            report to help identify the highest-leverage opportunities for your next renewal cycle.
          </p>
        </div>

        {/* Next Step CTAs */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>Next Steps</h3>

          <Link to="/billing/employer/scorecard" style={{ textDecoration: "none" }}>
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}>
              <div>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "#1B3A5C" }}>Upload your Summary of Benefits PDF</p>
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b" }}>Get your plan design grade in 60 seconds</p>
              </div>
              <span style={{ color: "#0D7377", fontWeight: 600, fontSize: 14 }}>&rarr;</span>
            </div>
          </Link>

          <Link to="/billing/employer/claims-check" style={{ textDecoration: "none" }}>
            <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}>
              <div>
                <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "#1B3A5C" }}>Upload one month of claims</p>
                <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b" }}>See exactly which procedures are driving your costs</p>
              </div>
              <span style={{ color: "#0D7377", fontWeight: 600, fontSize: 14 }}>&rarr;</span>
            </div>
          </Link>

          {data.broker_email && (
            <a href={`mailto:${data.broker_email}?subject=Questions about my Parity benchmark report&body=Hi — I reviewed the benchmark report for ${data.company_name}. I had some questions about the results.`} style={{ textDecoration: "none" }}>
              <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 12, padding: 20, display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}>
                <div>
                  <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "#0D7377" }}>Talk to your broker</p>
                  <p style={{ margin: "4px 0 0", fontSize: 13, color: "#64748b" }}>Share questions about this report with {data.broker_firm || "your broker"}</p>
                </div>
                <span style={{ color: "#0D7377", fontWeight: 600, fontSize: 14 }}>&rarr;</span>
              </div>
            </a>
          )}
        </div>

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: 48 }}>
          <p style={{ fontSize: 13, color: "#64748b", marginBottom: 8 }}>
            Questions about this report? Contact {data.broker_firm || "your broker"}{data.broker_email ? ` or reply to the email they sent you` : ""}.
          </p>
          <p style={{ fontSize: 12, color: "#94a3b8" }}>
            This analysis was prepared by {data.broker_firm || "your broker"} using <Link to="/" style={{ color: "#0D7377", textDecoration: "none" }}>Parity Employer</Link>, an independent benchmarking platform with no carrier relationships or commissions.
          </p>
        </div>
      </div>
    </Page>
  );
}

function Page({ children }) {
  return (
    <div style={{ minHeight: "100vh", background: "#f8fafc", fontFamily: "'DM Sans', sans-serif", color: "#2d3748" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      {/* Simple header */}
      <div style={{ borderBottom: "1px solid #e2e8f0", background: "#fff" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", padding: "16px 24px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link to="/" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "#1B3A5C" }}>
            <div style={{ width: 28, height: 28, borderRadius: 6, background: "linear-gradient(135deg, #0D7377, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 700, color: "#fff" }}>C</div>
            <span style={{ fontSize: 16, fontWeight: 600 }}>CivicScale</span>
          </Link>
          <Link to="/billing/employer" style={{ fontSize: 13, color: "#0D7377", textDecoration: "none", fontWeight: 500 }}>
            Parity Employer &rarr;
          </Link>
        </div>
      </div>
      {children}
    </div>
  );
}
