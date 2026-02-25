import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  LineChart, Line, Cell,
} from "recharts";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

  useEffect(() => {
    const stored = localStorage.getItem("employer_session");
    if (!stored) {
      navigate("/employer/login");
      return;
    }
    const parsed = JSON.parse(stored);
    setSession(parsed);
    fetchDashboard(parsed.employer_id);
  }, [navigate]);

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

  const handleSignOut = () => {
    localStorage.removeItem("employer_session");
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
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{
        textAlign: "center", padding: "32px 24px", fontSize: 13,
        color: "#4a5568", borderTop: "1px solid #e2e8f0", marginTop: 40,
      }}>
        Parity Health is powered by CivicScale benchmark infrastructure.
        Benchmark comparisons use publicly available CMS Medicare data. Not legal advice.
        &copy; CivicScale 2026.
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
