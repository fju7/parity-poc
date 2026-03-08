import { useState, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { supabase } from "../lib/supabase.js";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line, Cell,
} from "recharts";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const KEEPALIVE_INTERVAL_MS = 4 * 60 * 1000; // 4 minutes

function fmt$(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtScore(n) {
  if (n == null) return "—";
  return Number(n).toFixed(1) + "x";
}

const SCORE_COLORS = {
  "0-1": "#0D7377",
  "1-2": "#0D7377",
  "2-3": "#F59E0B",
  "3-5": "#EF4444",
  "5+": "#991B1B",
};

export default function EmployerDashboard() {
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [trends, setTrends] = useState(null);
  const [trendsLoading, setTrendsLoading] = useState(false);
  const [trendsRefreshing, setTrendsRefreshing] = useState(false);

  const fetchTrends = async (email) => {
    if (!email) return;
    setTrendsLoading(true);
    try {
      // Look up subscription by email to get subscription_id
      const subRes = await fetch(`${API_BASE}/api/employer/subscription-status?email=${encodeURIComponent(email)}`);
      if (!subRes.ok) return;
      const subData = await subRes.json();
      if (!subData.active || !subData.subscription?.id) return;

      const trendRes = await fetch(`${API_BASE}/api/employer/trends/${subData.subscription.id}`);
      if (trendRes.ok) {
        const trendData = await trendRes.json();
        trendData._subscription_id = subData.subscription.id;
        setTrends(trendData);
      }
    } catch (err) {
      console.log("[Trends] fetch failed:", err.message);
    } finally {
      setTrendsLoading(false);
    }
  };

  const refreshTrends = async () => {
    if (!trends?._subscription_id) return;
    setTrendsRefreshing(true);
    try {
      const res = await fetch(`${API_BASE}/api/employer/trends/${trends._subscription_id}/refresh`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        data._subscription_id = trends._subscription_id;
        setTrends(data);
      }
    } catch (err) {
      console.log("[Trends] refresh failed:", err.message);
    } finally {
      setTrendsRefreshing(false);
    }
  };

  useEffect(() => {
    const stored = localStorage.getItem("employer_session");
    if (!stored) {
      navigate("/employer/login");
      return;
    }
    const parsed = JSON.parse(stored);
    setSession(parsed);
    fetchDashboard(parsed.employer_id);
    fetchTrends(parsed.email);
  }, [navigate]);

  // Backend keepalive: ping every 4 min while tab is visible
  const keepaliveRef = useRef(null);

  useEffect(() => {
    if (!session) return;

    function startKeepalive() {
      stopKeepalive();
      keepaliveRef.current = setInterval(() => {
        fetch(`${API_BASE}/`).catch(() => {});
      }, KEEPALIVE_INTERVAL_MS);
    }

    function stopKeepalive() {
      if (keepaliveRef.current) {
        clearInterval(keepaliveRef.current);
        keepaliveRef.current = null;
      }
    }

    function onVisibilityChange() {
      if (document.visibilityState === "visible") {
        startKeepalive();
      } else {
        stopKeepalive();
      }
    }

    if (document.visibilityState === "visible") {
      startKeepalive();
    }

    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      stopKeepalive();
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [session]);

  const fetchDashboard = async (employerId) => {
    try {
      const res = await fetch(`${API_BASE}/api/employer/dashboard?employer_id=${employerId}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    localStorage.removeItem("employer_session");
    await supabase.auth.signOut();
    navigate("/employer/login");
  };

  if (!session) return null;

  return (
    <div style={{ fontFamily: "'DM Sans', Arial, sans-serif", background: "#f7f9fc", minHeight: "100vh" }}>
      {/* Header */}
      <header style={{
        background: "#1B3A5C", color: "#fff", padding: "0 32px",
        height: 56, display: "flex", alignItems: "center", justifyContent: "space-between",
        position: "sticky", top: 0, zIndex: 50,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link to="/" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
            <LogoIcon footer />
            <span style={{ color: "rgba(255,255,255,0.7)", fontWeight: 600, fontSize: 14 }}>CivicScale</span>
          </Link>
          <span style={{ color: "rgba(255,255,255,0.3)", margin: "0 4px" }}>|</span>
          <span style={{ fontWeight: 600, fontSize: 15 }}>Employer Dashboard</span>
          <span style={{ color: "rgba(255,255,255,0.6)", fontSize: 14 }}> — {session.company_name}</span>
        </div>
        <button
          onClick={handleSignOut}
          style={{
            background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)",
            color: "#fff", padding: "6px 14px", borderRadius: 6, cursor: "pointer", fontSize: 13,
          }}
        >
          Sign Out
        </button>
      </header>

      {/* Content */}
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "32px 24px" }}>
        {loading && (
          <div style={{ textAlign: "center", padding: 80 }}>
            <p style={{ color: "#4a5568", fontSize: 15 }}>Loading dashboard data...</p>
          </div>
        )}

        {error && (
          <div style={{
            textAlign: "center", padding: 40, background: "#fff",
            borderRadius: 12, border: "1px solid #fecaca",
          }}>
            <p style={{ color: "#991b1b", fontWeight: 600 }}>Failed to load dashboard</p>
            <p style={{ color: "#4a5568", fontSize: 14 }}>{error}</p>
          </div>
        )}

        {data && data.empty && (
          <div style={{
            textAlign: "center", padding: 80, background: "#fff",
            borderRadius: 12, border: "1px solid #e2e8f0",
          }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>📊</div>
            <h2 style={{ color: "#1B3A5C", marginBottom: 8 }}>No data yet</h2>
            <p style={{ color: "#4a5568", maxWidth: 400, margin: "0 auto", lineHeight: 1.6 }}>
              Contributions will appear here as employees opt in and analyze
              bills using your employer code: <strong>{session.company_name}</strong>
            </p>
          </div>
        )}

        {data && !data.empty && (
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Panel 1: Portfolio Overview */}
            <section>
              <SectionTitle>Portfolio Overview</SectionTitle>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
                <StatCard label="Total Claims" value={data.overview.totalClaims} />
                <StatCard label="Total Discrepancy" value={fmt$(data.overview.totalDiscrepancy)} highlight />
                <StatCard label="Avg Anomaly Score" value={fmtScore(data.overview.avgScore)} />
                <StatCard label="Providers Flagged" value={data.overview.providersFlagged} />
              </div>
            </section>

            {/* Panel 2: Top Flagged Providers */}
            {data.topProviders.length > 0 && (
              <section>
                <SectionTitle>Top Flagged Providers</SectionTitle>
                <Card>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                        <Th>Provider</Th>
                        <Th align="right">Avg Score</Th>
                        <Th align="right">Claims</Th>
                        <Th align="right">Total Discrepancy</Th>
                        <Th>Most Common CPT</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.topProviders.map((p, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <Td>{p.providerName}</Td>
                          <Td align="right">
                            <ScoreBadge score={p.avgScore} />
                          </Td>
                          <Td align="right">{p.claimCount}</Td>
                          <Td align="right" style={{ fontWeight: 600, color: p.totalDiscrepancy > 0 ? "#991b1b" : "#059669" }}>
                            {fmt$(p.totalDiscrepancy)}
                          </Td>
                          <Td><code style={{ fontSize: 13, background: "#f1f5f9", padding: "2px 6px", borderRadius: 4 }}>{p.mostCommonCpt}</code></Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </section>
            )}

            {/* Panel 3 + Panel 4 side by side */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
              {/* Panel 3: Score Distribution */}
              <section>
                <SectionTitle>Anomaly Score Distribution</SectionTitle>
                <Card style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.scoreDistribution} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="range" tick={{ fontSize: 13 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fontSize: 13 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13 }}
                        formatter={(val) => [val, "Claims"]}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {data.scoreDistribution.map((entry, i) => (
                          <Cell key={i} fill={SCORE_COLORS[entry.range] || "#0D7377"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </section>

              {/* Panel 4: Coding Intelligence */}
              <section>
                <SectionTitle>Coding Intelligence</SectionTitle>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <MiniStatCard label="NCCI Bundle Flags" value={data.codingIntelligence.ncciFlags} icon="🔗" />
                  <MiniStatCard label="MUE Flags" value={data.codingIntelligence.mueFlags} icon="📏" />
                  <MiniStatCard label="Site-of-Service" value={data.codingIntelligence.siteOfServiceFlags} icon="🏥" />
                  <MiniStatCard label="E&M Level Flags" value={data.codingIntelligence.emFlags} icon="📋" />
                </div>
              </section>
            </div>

            {/* Panel 5: CPT Code Hotspots */}
            {data.cptHotspots.length > 0 && (
              <section>
                <SectionTitle>CPT Code Hotspots</SectionTitle>
                <Card>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                    <thead>
                      <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                        <Th>CPT Code</Th>
                        <Th>Description</Th>
                        <Th align="right">Occurrences</Th>
                        <Th align="right">Avg Score</Th>
                        <Th align="right">Total Discrepancy</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.cptHotspots.map((c, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <Td><code style={{ fontSize: 13, background: "#f1f5f9", padding: "2px 6px", borderRadius: 4 }}>{c.cptCode}</code></Td>
                          <Td style={{ color: "#4a5568" }}>{c.description}</Td>
                          <Td align="right">{c.occurrences}</Td>
                          <Td align="right"><ScoreBadge score={c.avgScore} /></Td>
                          <Td align="right" style={{ fontWeight: 600, color: c.totalDiscrepancy > 0 ? "#991b1b" : "#059669" }}>
                            {fmt$(c.totalDiscrepancy)}
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </section>
            )}

            {/* Panel 6: Monthly Trend */}
            {data.monthlyTrend.length > 0 && (
              <section>
                <SectionTitle>Monthly Trend</SectionTitle>
                <Card style={{ height: 300 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.monthlyTrend} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="month" tick={{ fontSize: 13 }} axisLine={false} tickLine={false} />
                      <YAxis
                        tick={{ fontSize: 13 }}
                        axisLine={false}
                        tickLine={false}
                        tickFormatter={(v) => "$" + (v / 1000).toFixed(0) + "k"}
                      />
                      <Tooltip
                        contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13 }}
                        formatter={(val, name) => {
                          if (name === "totalDiscrepancy") return [fmt$(val), "Discrepancy"];
                          return [val, "Claims"];
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="totalDiscrepancy"
                        stroke="#1B3A5C"
                        strokeWidth={2}
                        dot={{ fill: "#1B3A5C", r: 4 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="claimCount"
                        stroke="#0D7377"
                        strokeWidth={2}
                        dot={{ fill: "#0D7377", r: 4 }}
                        yAxisId={0}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>
              </section>
            )}

            {/* Panel 7: PEPM Trend Analysis */}
            <section>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
                <SectionTitle>PEPM Trend Analysis</SectionTitle>
                {trends && trends.months_available >= 2 && (
                  <button
                    onClick={refreshTrends}
                    disabled={trendsRefreshing}
                    style={{
                      background: "#fff", border: "1px solid #e2e8f0", borderRadius: 6,
                      padding: "6px 14px", fontSize: 13, cursor: trendsRefreshing ? "not-allowed" : "pointer",
                      color: "#4a5568", fontWeight: 500, opacity: trendsRefreshing ? 0.6 : 1,
                    }}
                  >
                    {trendsRefreshing ? "Refreshing..." : "Refresh"}
                  </button>
                )}
              </div>

              {trendsLoading && (
                <Card>
                  <div style={{ textAlign: "center", padding: 32, color: "#4a5568", fontSize: 14 }}>
                    Loading trend data...
                  </div>
                </Card>
              )}

              {!trendsLoading && (!trends || trends.months_available < 2) && (
                <Card>
                  <div style={{ textAlign: "center", padding: 32, color: "#4a5568", fontSize: 14 }}>
                    Trend analysis will appear after your second monthly upload.
                  </div>
                </Card>
              )}

              {!trendsLoading && trends && trends.months_available >= 2 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  {/* PEPM Trend Bars */}
                  <Card>
                    <h4 style={{ fontSize: 14, fontWeight: 600, color: "#4a5568", margin: "0 0 16px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                      Per Employee Per Month (PEPM)
                    </h4>
                    {trends.monthly_summary.map((m, i) => {
                      const maxPepm = Math.max(...trends.monthly_summary.map(x => x.pepm));
                      const widthPct = maxPepm > 0 ? (m.pepm / maxPepm) * 100 : 0;
                      return (
                        <div key={i} style={{ marginBottom: 10 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
                            <span style={{ color: "#4a5568", fontWeight: 500 }}>{m.label}</span>
                            <span style={{ fontWeight: 700, color: "#1B3A5C" }}>{fmt$(m.pepm)}</span>
                          </div>
                          <div style={{ background: "#f1f5f9", borderRadius: 6, height: 24, overflow: "hidden" }}>
                            <div style={{
                              width: `${widthPct}%`, height: "100%",
                              background: i === trends.monthly_summary.length - 1 ? "#1B3A5C" : "#0D7377",
                              borderRadius: 6, transition: "width 0.5s ease",
                            }} />
                          </div>
                          {m.pepm_delta_pct != null && (
                            <div style={{ fontSize: 11, color: m.pepm_delta_pct > 0 ? "#991b1b" : "#059669", marginTop: 2, fontWeight: 600 }}>
                              {m.pepm_delta_pct > 0 ? "+" : ""}{m.pepm_delta_pct}% vs prior month
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </Card>

                  {/* Alert Cards */}
                  {trends.alerts && trends.alerts.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {trends.alerts.map((alert, i) => {
                        const isHigh = alert.severity === "high";
                        const isPositive = alert.severity === "positive";
                        const borderColor = isPositive ? "#059669" : isHigh ? "#EF4444" : "#F59E0B";
                        const bgColor = isPositive ? "#f0fdf4" : isHigh ? "#fef2f2" : "#fefce8";
                        const textColor = isPositive ? "#065f46" : isHigh ? "#991b1b" : "#92400e";
                        return (
                          <div key={i} style={{
                            background: bgColor, borderLeft: `4px solid ${borderColor}`,
                            borderRadius: 8, padding: "12px 16px",
                          }}>
                            <div style={{ fontSize: 11, fontWeight: 600, color: borderColor, textTransform: "uppercase", marginBottom: 4 }}>
                              {alert.type.replace(/_/g, " ")}
                            </div>
                            <div style={{ fontSize: 14, color: textColor, lineHeight: 1.5 }}>
                              {alert.detail}
                            </div>
                            {alert.financial_impact != null && (
                              <div style={{ fontSize: 12, color: "#4a5568", marginTop: 4 }}>
                                Financial impact: {fmt$(alert.financial_impact)}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* AI Narrative */}
                  {trends.trend_narrative && (
                    <div style={{
                      background: "#fff", borderLeft: "4px solid #3b82f6",
                      borderRadius: 8, padding: 20, border: "1px solid #e2e8f0",
                      borderLeftColor: "#3b82f6",
                    }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: "#3b82f6", marginBottom: 10, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                        AI TREND SUMMARY
                      </div>
                      <div style={{ fontSize: 15, color: "#1e293b", fontWeight: 400, lineHeight: 1.6 }}>
                        {trends.trend_narrative}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{
        textAlign: "center", padding: "32px 24px", fontSize: 13,
        color: "#4a5568", borderTop: "1px solid #e2e8f0", marginTop: 40,
      }}>
        <p>Parity Health is powered by CivicScale benchmark infrastructure.
        Benchmark comparisons use publicly available CMS Medicare data. Not legal advice.
        &copy; CivicScale 2026.</p>
        <p style={{ fontSize: 11, color: "#718096", marginTop: 8 }}>
          Data sources: CMS Medicare Physician Fee Schedule (2026), CMS Outpatient Prospective
          Payment System (2026), CMS Clinical Laboratory Fee Schedule (2026 Q1).
        </p>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared sub-components
// ---------------------------------------------------------------------------

function SectionTitle({ children }) {
  return (
    <h3 style={{
      fontSize: 16, fontWeight: 700, color: "#1B3A5C",
      marginBottom: 12, marginTop: 0,
    }}>
      {children}
    </h3>
  );
}

function Card({ children, style = {} }) {
  return (
    <div style={{
      background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0",
      padding: 20, ...style,
    }}>
      {children}
    </div>
  );
}

function StatCard({ label, value, highlight }) {
  return (
    <div style={{
      background: highlight ? "#1B3A5C" : "#fff",
      borderRadius: 12, border: highlight ? "none" : "1px solid #e2e8f0",
      padding: "20px 24px",
    }}>
      <p style={{
        fontSize: 13, color: highlight ? "rgba(255,255,255,0.7)" : "#4a5568",
        margin: "0 0 4px", fontWeight: 500,
      }}>
        {label}
      </p>
      <p style={{
        fontSize: 28, fontWeight: 700,
        color: highlight ? "#fff" : "#1B3A5C", margin: 0,
      }}>
        {value}
      </p>
    </div>
  );
}

function MiniStatCard({ label, value, icon }) {
  return (
    <div style={{
      background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0",
      padding: "16px 20px", display: "flex", alignItems: "center", gap: 12,
    }}>
      <span style={{ fontSize: 24 }}>{icon}</span>
      <div>
        <p style={{ fontSize: 22, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>{value}</p>
        <p style={{ fontSize: 12, color: "#4a5568", margin: 0, fontWeight: 500 }}>{label}</p>
      </div>
    </div>
  );
}

function ScoreBadge({ score }) {
  let bg = "#dcfce7";
  let color = "#059669";
  if (score >= 3) { bg = "#fef2f2"; color = "#991b1b"; }
  else if (score >= 2) { bg = "#fefce8"; color = "#92400e"; }

  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 12,
      background: bg, color, fontWeight: 600, fontSize: 13,
    }}>
      {fmtScore(score)}
    </span>
  );
}

function Th({ children, align = "left" }) {
  return (
    <th style={{
      textAlign: align, padding: "10px 12px", fontWeight: 600,
      color: "#4a5568", fontSize: 12, textTransform: "uppercase",
      letterSpacing: "0.05em",
    }}>
      {children}
    </th>
  );
}

function Td({ children, align = "left", style = {} }) {
  return (
    <td style={{ textAlign: align, padding: "10px 12px", ...style }}>
      {children}
    </td>
  );
}
