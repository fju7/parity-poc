import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const EMP_MIDPOINTS = { "<100": 50, "100-250": 175, "250-500": 375, "500-1000": 750, "1000+": 1500 };

function ordinalSuffix(n) {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

const fmt = (n) => n != null ? n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : "\u2014";

export default function RenewalPrepReport() {
  const { companySlug } = useParams();
  const { token } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Inline upload state
  const [claimsFile, setClaimsFile] = useState(null);
  const [claimsZip, setClaimsZip] = useState("");
  const [claimsUploading, setClaimsUploading] = useState(false);
  const [claimsResult, setClaimsResult] = useState(null);
  const [claimsError, setClaimsError] = useState("");
  const [scorecardFile, setScorecardFile] = useState(null);
  const [scorecardUploading, setScorecardUploading] = useState(false);
  const [scorecardResult, setScorecardResult] = useState(null);
  const [scorecardError, setScorecardError] = useState("");

  const handleClaimsUpload = async () => {
    if (!claimsFile || claimsZip.length !== 5 || !data?.client?.employer_email) return;
    setClaimsUploading(true); setClaimsError("");
    try {
      const fd = new FormData();
      fd.append("file", claimsFile);
      fd.append("zip_code", claimsZip.trim());
      const res = await fetch(`${API}/api/broker/clients/${encodeURIComponent(data.client.employer_email)}/claims-upload`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      const json = await res.json();
      if (!res.ok) { setClaimsError(json.detail || "Upload failed"); return; }
      setClaimsResult(json);
      setClaimsFile(null);
    } catch { setClaimsError("Upload failed. Please try again."); }
    setClaimsUploading(false);
  };

  const handleScorecardUpload = async () => {
    if (!scorecardFile || !data?.client?.employer_email) return;
    setScorecardUploading(true); setScorecardError("");
    try {
      const fd = new FormData();
      fd.append("file", scorecardFile);
      const res = await fetch(`${API}/api/broker/clients/${encodeURIComponent(data.client.employer_email)}/scorecard-upload`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      const json = await res.json();
      if (!res.ok) { setScorecardError(json.detail || "Upload failed"); return; }
      setScorecardResult(json);
      setScorecardFile(null);
    } catch { setScorecardError("Upload failed. Please try again."); }
    setScorecardUploading(false);
  };

  useEffect(() => {
    if (!companySlug || !token) return;
    (async () => {
      try {
        const res = await fetch(`${API}/api/broker/renewal-prep/${encodeURIComponent(companySlug)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || "Failed to load report");
        }
        setData(await res.json());
      } catch (err) { setError(err.message); }
      setLoading(false);
    })();
  }, [companySlug, token]);

  if (loading) {
    return (
      <Shell>
        <div style={{ textAlign: "center", paddingTop: 120 }}>
          <div style={{ width: 40, height: 40, border: "3px solid #e2e8f0", borderTopColor: "#0D7377", borderRadius: "50%", animation: "spin 0.8s linear infinite", margin: "0 auto 16px" }} />
          <p style={{ color: "#64748b", fontSize: 15 }}>Assembling renewal report...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </Shell>
    );
  }

  if (error) {
    return (
      <Shell>
        <div style={{ textAlign: "center", paddingTop: 120 }}>
          <h2 style={{ fontSize: 22, fontWeight: 600, color: "#1B3A5C", marginBottom: 12 }}>Report Not Found</h2>
          <p style={{ fontSize: 14, color: "#64748b", marginBottom: 24 }}>{error}</p>
          <Link to="/broker/dashboard" style={{ color: "#0D7377", fontWeight: 600, textDecoration: "none" }}>Back to Dashboard &rarr;</Link>
        </div>
      </Shell>
    );
  }

  const { broker, client, benchmark, claims, scorecard } = data;
  const empCount = EMP_MIDPOINTS[client.employee_count_range] || 200;
  const percentile = benchmark.available ? Math.round(benchmark.percentile) : null;
  const totalAnnualGap = benchmark.available && benchmark.annual_gap ? Math.round(benchmark.annual_gap * empCount) : null;
  const renewalDate = client.renewal_month ? new Date(client.renewal_month).toLocaleDateString("en-US", { month: "long", year: "numeric" }) : null;

  // Talking points
  const talkingPoints = [];
  if (percentile != null) {
    if (percentile > 75) {
      talkingPoints.push("Your costs are significantly above market. Use this data to negotiate a rate reduction or explore alternative carriers.");
    } else if (percentile >= 50) {
      talkingPoints.push("Your costs are above median. Focus renewal discussions on specific high-cost procedure categories.");
    } else {
      talkingPoints.push("Your costs are competitive. Protect your current plan design at renewal and focus on maintaining network quality.");
    }
  }
  talkingPoints.push("Request procedure-level utilization data from your carrier as part of renewal negotiations. You have a legal right to this data under CAA Section 201.");
  if (claims.available && claims.excess_amount > 0) {
    talkingPoints.push(`Claims analysis identified ${fmt(claims.excess_amount)} in potential excess spend. Use specific procedure findings as leverage in rate negotiations.`);
  }
  if (claims.available && claims.level2 && claims.level2.has_level2) {
    if (claims.level2.provider_variation.total_variation_opportunity > 0) {
      talkingPoints.push(`Level 2 analysis found ${fmt(claims.level2.provider_variation.total_variation_opportunity)} in provider price variation — selecting lower-cost providers for the same procedures represents a cost reduction opportunity.`);
    }
    if (claims.level2.network_leakage.flag !== "LOW") {
      talkingPoints.push(`Network leakage is ${claims.level2.network_leakage.flag.toLowerCase()} — ${claims.level2.network_leakage.out_of_network_pct}% of spend appears out-of-network. Review network adequacy with your carrier.`);
    }
  }
  if (scorecard.available && scorecard.grade && !["A", "B+", "B"].includes(scorecard.grade)) {
    const improvementCount = scorecard.scored_criteria ? scorecard.scored_criteria.filter(c => c.score < 60).length : 0;
    talkingPoints.push(`Plan design analysis identified ${improvementCount || "several"} improvement opportunities. These are common findings in plans due for renewal review and represent negotiable terms your advisor can address.`);
  }

  const pctColor = percentile == null ? "#64748b" : percentile > 75 ? "#EF4444" : percentile > 50 ? "#f59e0b" : "#22c55e";

  return (
    <Shell>
      {/* Print button */}
      <div className="no-print" style={{ position: "fixed", top: 16, right: 24, zIndex: 100 }}>
        <button onClick={() => window.print()} style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
          Download PDF
        </button>
      </div>

      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .report-page { padding: 0 !important; }
        }
      `}</style>

      <div className="report-page" style={{ maxWidth: 800, margin: "0 auto", padding: "0 24px 60px" }}>
        {/* Header Bar */}
        <div style={{ background: "#0D7377", color: "#fff", borderRadius: "0 0 12px 12px", padding: "24px 32px", marginBottom: 32, display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <p style={{ margin: 0, fontSize: 13, opacity: 0.8 }}>{broker.firm_name}</p>
            <p style={{ margin: "4px 0 0", fontSize: 20, fontWeight: 600 }}>Prepared for {client.company_name}</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>Renewal Analysis {renewalDate ? `\u00B7 ${renewalDate}` : ""}</p>
            <p style={{ margin: "4px 0 0", fontSize: 12, opacity: 0.7 }}>CivicScale Parity Employer</p>
          </div>
        </div>

        {/* Section 1 — Executive Summary */}
        <Section title="Executive Summary">
          <p style={{ fontSize: 15, color: "#475569", lineHeight: 1.8, margin: 0 }}>
            {client.company_name} is a {client.employee_count_range || ""} employee employer in {client.industry || "a general industry"} in {client.state || "the US"}.
            {benchmark.available && percentile != null && (
              <> Based on independent benchmark data, your health plan costs are at the {percentile}{ordinalSuffix(percentile)} percentile for employers of similar size and industry. {benchmark.interpretation}</>
            )}
            {client.carrier && <> Your renewal with {client.carrier} is{renewalDate ? ` in ${renewalDate}` : " upcoming"}.</>}
          </p>
        </Section>

        {/* Section 2 — Benchmark Position */}
        <Section title="Benchmark Position">
          {benchmark.available ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 20 }}>
                <StatCard label="Your Percentile" value={`${percentile}${ordinalSuffix(percentile)}`} color={pctColor} />
                <StatCard label="Your PEPM" value={fmt(benchmark.pepm)} />
                <StatCard label="Adjusted Median" value={fmt(benchmark.adjusted_median)} />
              </div>

              {totalAnnualGap != null && totalAnnualGap !== 0 && (
                <div style={{ background: totalAnnualGap > 0 ? "#fef2f2" : "#f0fdf4", border: `1px solid ${totalAnnualGap > 0 ? "#fecaca" : "#bbf7d0"}`, borderRadius: 10, padding: "14px 20px", marginBottom: 20, textAlign: "center" }}>
                  <p style={{ margin: 0, fontSize: 14, color: totalAnnualGap > 0 ? "#991b1b" : "#166534" }}>
                    Estimated total annual gap: <strong>{totalAnnualGap > 0 ? "+" : ""}{fmt(totalAnnualGap)}</strong>
                    <span style={{ fontSize: 12, color: "#64748b", marginLeft: 8 }}>({client.employee_count_range} employees &times; {fmt(benchmark.annual_gap)}/yr each)</span>
                  </p>
                </div>
              )}

              {/* Distribution bar */}
              {benchmark.distribution && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ position: "relative", height: 32, background: "linear-gradient(90deg, #22c55e 0%, #f59e0b 50%, #EF4444 100%)", borderRadius: 6, marginBottom: 20 }}>
                    {percentile != null && (
                      <div style={{ position: "absolute", left: `${Math.min(Math.max(percentile, 2), 98)}%`, top: -6, transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center" }}>
                        <div style={{ width: 0, height: 0, borderLeft: "6px solid transparent", borderRight: "6px solid transparent", borderTop: "6px solid #1B3A5C" }} />
                        <div style={{ background: "#1B3A5C", color: "#fff", padding: "1px 6px", borderRadius: 3, fontSize: 10, fontWeight: 700, marginTop: -1 }}>You</div>
                      </div>
                    )}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#64748b" }}>
                    {["p10", "p25", "p50", "p75", "p90"].map((k) => (
                      <div key={k} style={{ textAlign: "center" }}>
                        <div>{k.toUpperCase()}</div>
                        <div style={{ fontWeight: 600, color: "#475569" }}>{benchmark.distribution[k] ? fmt(benchmark.distribution[k]) : "\u2014"}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p style={{ fontSize: 11, color: "#94a3b8", margin: 0 }}>Source: MEPS-IC 2024, KFF EHBS 2025</p>
            </>
          ) : (
            <Placeholder text="Benchmark data not available. Run a benchmark for this client to populate this section." />
          )}
        </Section>

        {/* Section 3 — Claims Analysis */}
        <Section title="Claims Analysis">
          {claims.available ? (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 12, marginBottom: claims.level2 && claims.level2.has_level2 ? 16 : 0 }}>
                <StatCard label="Total Claims" value={claims.total_claims.toLocaleString()} small />
                <StatCard label="Total Paid" value={fmt(claims.total_paid)} small />
                <StatCard label="Excess Identified" value={fmt(claims.excess_amount)} color={claims.excess_amount > 0 ? "#EF4444" : "#475569"} small />
                <StatCard label="Top Procedure" value={claims.top_cpt || "\u2014"} small />
              </div>
              {claims.level2 && claims.level2.has_level2 && (
                <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 10, padding: "14px 20px" }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: "#0D7377", margin: "0 0 8px" }}>KEY FINDINGS</p>
                  <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "#475569", lineHeight: 1.8 }}>
                    {claims.level2.provider_variation.flagged_cpts.length > 0 && (
                      <li>Provider variation: estimated {fmt(claims.level2.provider_variation.total_variation_opportunity)} cost reduction opportunity if members select lower-cost providers</li>
                    )}
                    {claims.level2.site_of_care.total_site_opportunity > 0 && (
                      <li>Site of care: estimated {fmt(claims.level2.site_of_care.total_site_opportunity)} opportunity if members choose lower-cost care settings over hospital outpatient</li>
                    )}
                    <li>Network leakage: <strong style={{ color: claims.level2.network_leakage.flag === "HIGH" ? "#EF4444" : claims.level2.network_leakage.flag === "MODERATE" ? "#f59e0b" : "#166534" }}>{claims.level2.network_leakage.flag}</strong> ({claims.level2.network_leakage.out_of_network_pct}% out-of-network)</li>
                    {claims.level2.carrier_rates.avg_multiple_vs_medicare > 0 && (
                      <li>Average procedures paid at <strong>{claims.level2.carrier_rates.avg_multiple_vs_medicare}x Medicare</strong></li>
                    )}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <>{claimsResult ? (
              <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 10, padding: 16 }}>
                <p style={{ fontSize: 14, fontWeight: 600, color: "#0D7377", margin: "0 0 8px" }}>Claims analysis complete</p>
                <div style={{ display: "flex", gap: 24, fontSize: 13, color: "#475569" }}>
                  <span><strong>{claimsResult.summary?.total_claims}</strong> claims</span>
                  <span>Total paid: <strong>{fmt(claimsResult.summary?.total_paid)}</strong></span>
                  <span>Excess &gt;2x: <strong style={{ color: claimsResult.summary?.total_excess_2x > 0 ? "#EF4444" : "#475569" }}>{fmt(claimsResult.summary?.total_excess_2x)}</strong></span>
                </div>
                {claimsResult.narrative && <p style={{ fontSize: 12, color: "#475569", margin: "8px 0 0", lineHeight: 1.5 }}>{claimsResult.narrative}</p>}
              </div>
            ) : (
              <div style={{ background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 10, padding: "20px 24px" }} className="no-print">
                <p style={{ margin: "0 0 12px", fontSize: 14, color: "#94a3b8", textAlign: "center" }}>Not yet analyzed. Upload claims data to complete this section.</p>
                <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap", justifyContent: "center" }}>
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>Claims file (835/CSV/Excel/ZIP)</label>
                    <div
                      onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = "#0d9488"; e.currentTarget.style.background = "#f0fdfa"; }}
                      onDragLeave={(e) => { e.currentTarget.style.borderColor = "#cbd5e1"; e.currentTarget.style.background = "#f8fafc"; }}
                      onDrop={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = "#cbd5e1"; e.currentTarget.style.background = "#f8fafc"; const f = e.dataTransfer.files?.[0]; if (f) setClaimsFile(f); }}
                      onClick={() => document.getElementById("claims-file-input-report").click()}
                      style={{ border: "2px dashed #cbd5e1", borderRadius: 8, padding: "10px 14px", background: "#f8fafc", cursor: "pointer", textAlign: "center", fontSize: 12, color: "#94a3b8", transition: "all 0.15s", minWidth: 220 }}
                    >
                      {claimsFile ? <span style={{ color: "#0d9488", fontWeight: 500 }}>{claimsFile.name}</span> : "Drop file here or click to browse"}
                    </div>
                    <input id="claims-file-input-report" type="file" accept=".835,.edi,.csv,.xlsx,.xls,.zip,.txt" onChange={(e) => setClaimsFile(e.target.files?.[0] || null)} style={{ display: "none" }} />
                  </div>
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>ZIP code</label>
                    <input type="text" maxLength={5} value={claimsZip} onChange={(e) => setClaimsZip(e.target.value.replace(/\D/g, "").slice(0, 5))} placeholder="10001" style={{ width: 90, padding: "6px 10px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13 }} />
                  </div>
                  <button onClick={handleClaimsUpload} disabled={claimsUploading || !claimsFile || claimsZip.length !== 5} style={{ padding: "8px 18px", borderRadius: 8, border: "none", cursor: "pointer", background: claimsUploading || !claimsFile || claimsZip.length !== 5 ? "#cbd5e1" : "#0D7377", color: "#fff", fontWeight: 600, fontSize: 13 }}>
                    {claimsUploading ? "Analyzing..." : "Upload & Analyze"}
                  </button>
                </div>
                {claimsError && <p style={{ color: "#991b1b", fontSize: 12, marginTop: 8, textAlign: "center" }}>{claimsError}</p>}
              </div>
            )}</>
          )}
        </Section>

        {/* Section 4 — Plan Design Score */}
        <Section title="Plan Design Score">
          {scorecard.available ? (
            <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
              <div style={{ width: 80, height: 80, borderRadius: "50%", background: scorecard.grade === "A" ? "#f0fdf4" : scorecard.grade === "B" ? "#eff6ff" : scorecard.grade === "C" ? "#fffbeb" : "#fef2f2", border: `3px solid ${scorecard.grade === "A" ? "#22c55e" : scorecard.grade === "B" ? "#3b82f6" : scorecard.grade === "C" ? "#f59e0b" : "#EF4444"}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 36, fontWeight: 700, color: scorecard.grade === "A" ? "#166534" : scorecard.grade === "B" ? "#1d4ed8" : scorecard.grade === "C" ? "#92400e" : "#991b1b", flexShrink: 0 }}>
                {scorecard.grade}
              </div>
              <div>
                {scorecard.score != null && <p style={{ margin: "0 0 4px", fontSize: 14, color: "#475569" }}>Score: <strong>{scorecard.score}/100</strong></p>}
                {scorecard.savings_potential != null && <p style={{ margin: "0 0 8px", fontSize: 14, color: "#475569" }}>Estimated savings potential: <strong>{fmt(scorecard.savings_potential)}</strong> per employee per year</p>}
                {scorecard.interpretation && (
                  <p style={{ margin: 0, fontSize: 13, color: "#64748b", lineHeight: 1.7 }}>
                    {scorecard.interpretation.context}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <>{scorecardResult ? (
              <div style={{ background: "#f0fdfa", border: "1px solid #99f6e4", borderRadius: 10, padding: 16 }}>
                <p style={{ fontSize: 13, fontWeight: 600, color: "#0D7377", margin: "0 0 6px" }}>
                  Plan grade: <span style={{ fontSize: 20 }}>{scorecardResult.grade}</span>
                  <span style={{ fontWeight: 400, color: "#475569", marginLeft: 8 }}>({scorecardResult.score}/100)</span>
                </p>
                {scorecardResult.plan_name && <p style={{ fontSize: 12, color: "#475569", margin: 0 }}>{scorecardResult.plan_name}</p>}
                {scorecardResult.interpretation && (
                  <div style={{ marginTop: 6 }}>
                    {typeof scorecardResult.interpretation === "string" ? (
                      <p style={{ fontSize: 12, color: "#475569", margin: 0, lineHeight: 1.5 }}>{scorecardResult.interpretation}</p>
                    ) : (
                      <>
                        {scorecardResult.interpretation.context && <p style={{ fontSize: 12, color: "#475569", margin: "0 0 4px", lineHeight: 1.5 }}>{scorecardResult.interpretation.context}</p>}
                        {scorecardResult.interpretation.action && <p style={{ fontSize: 12, color: "#0D7377", margin: "0 0 4px", lineHeight: 1.5, fontWeight: 500 }}>{scorecardResult.interpretation.action}</p>}
                        {scorecardResult.interpretation.broker_framing && <p style={{ fontSize: 12, color: "#64748b", margin: 0, lineHeight: 1.5, fontStyle: "italic" }}>{scorecardResult.interpretation.broker_framing}</p>}
                      </>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 10, padding: "20px 24px" }} className="no-print">
                <p style={{ margin: "0 0 12px", fontSize: 14, color: "#94a3b8", textAlign: "center" }}>Not yet graded. Upload the plan SBC PDF to complete this section.</p>
                <div style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap", justifyContent: "center" }}>
                  <div>
                    <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 4 }}>Summary of Benefits and Coverage (PDF)</label>
                    <div
                      onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = "#0d9488"; e.currentTarget.style.background = "#f0fdfa"; }}
                      onDragLeave={(e) => { e.currentTarget.style.borderColor = "#cbd5e1"; e.currentTarget.style.background = "#f8fafc"; }}
                      onDrop={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = "#cbd5e1"; e.currentTarget.style.background = "#f8fafc"; const f = e.dataTransfer.files?.[0]; if (f) setScorecardFile(f); }}
                      onClick={() => document.getElementById("scorecard-file-input-report").click()}
                      style={{ border: "2px dashed #cbd5e1", borderRadius: 8, padding: "10px 14px", background: "#f8fafc", cursor: "pointer", textAlign: "center", fontSize: 12, color: "#94a3b8", transition: "all 0.15s", minWidth: 220 }}
                    >
                      {scorecardFile ? <span style={{ color: "#0d9488", fontWeight: 500 }}>{scorecardFile.name}</span> : "Drop PDF here or click to browse"}
                    </div>
                    <input id="scorecard-file-input-report" type="file" accept=".pdf" onChange={(e) => setScorecardFile(e.target.files?.[0] || null)} style={{ display: "none" }} />
                  </div>
                  <button onClick={handleScorecardUpload} disabled={scorecardUploading || !scorecardFile} style={{ padding: "8px 18px", borderRadius: 8, border: "none", cursor: "pointer", background: scorecardUploading || !scorecardFile ? "#cbd5e1" : "#0D7377", color: "#fff", fontWeight: 600, fontSize: 13 }}>
                    {scorecardUploading ? "Grading..." : "Upload & Grade Plan"}
                  </button>
                </div>
                {scorecardError && <p style={{ color: "#991b1b", fontSize: 12, marginTop: 8, textAlign: "center" }}>{scorecardError}</p>}
              </div>
            )}</>
          )}
        </Section>

        {/* Section 5 — Renewal Talking Points */}
        <Section title="Renewal Talking Points">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {talkingPoints.map((tp, i) => (
              <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div style={{ width: 22, height: 22, borderRadius: "50%", background: "#f0fdfa", border: "1px solid #99f6e4", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700, color: "#0D7377", flexShrink: 0 }}>{i + 1}</div>
                <p style={{ margin: 0, fontSize: 14, color: "#475569", lineHeight: 1.7 }}>{tp}</p>
              </div>
            ))}
          </div>
        </Section>

        {/* Footer */}
        <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: 20, marginTop: 32 }}>
          <p style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.7, margin: "0 0 8px" }}>
            This report was prepared using independent data from MEPS-IC 2024, KFF EHBS 2025, and BLS. It does not constitute financial or legal advice.
          </p>
          <p style={{ fontSize: 12, color: "#94a3b8", margin: 0 }}>
            Prepared by {broker.firm_name} using CivicScale Parity Employer &middot; civicscale.ai
          </p>
        </div>

        {/* Back link */}
        <div className="no-print" style={{ textAlign: "center", marginTop: 24 }}>
          <Link to="/broker/dashboard" style={{ color: "#64748b", fontSize: 14, textDecoration: "none" }}>&larr; Back to Broker Dashboard</Link>
        </div>
      </div>
    </Shell>
  );
}


function Shell({ children }) {
  return (
    <div style={{ minHeight: "100vh", background: "#fff", fontFamily: "'DM Sans', sans-serif", color: "#2d3748" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      {children}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, color: "#1B3A5C", margin: "0 0 14px", paddingBottom: 8, borderBottom: "2px solid #e2e8f0" }}>{title}</h2>
      {children}
    </div>
  );
}

function StatCard({ label, value, color, small }) {
  return (
    <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10, padding: small ? "14px 12px" : "18px 16px", textAlign: "center" }}>
      <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 4px", fontWeight: 500 }}>{label}</p>
      <p style={{ fontSize: small ? 18 : 28, fontWeight: 700, color: color || "#1B3A5C", margin: 0 }}>{value}</p>
    </div>
  );
}

function Placeholder({ text, cta, ctaLink }) {
  return (
    <div style={{ background: "#f8fafc", border: "1px dashed #cbd5e1", borderRadius: 10, padding: "20px 24px", textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: 14, color: "#94a3b8" }}>{text}</p>
      {cta && ctaLink && (
        <Link to={ctaLink} className="no-print" style={{ display: "inline-block", marginTop: 8, fontSize: 13, color: "#0D7377", textDecoration: "none", fontWeight: 500 }}>
          {cta} &rarr;
        </Link>
      )}
    </div>
  );
}
