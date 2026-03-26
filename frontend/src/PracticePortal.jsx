import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { API_BASE as API } from "./lib/apiBase";

export default function PracticePortal() {
  const [searchParams] = useSearchParams();
  const practiceId = searchParams.get("practice") || "";

  // Auth state
  const [token, setToken] = useState(() => localStorage.getItem("portal_token"));
  const [portalData, setPortalData] = useState(null);
  const [loading, setLoading] = useState(true);

  // OTP state
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [otpStep, setOtpStep] = useState("email");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState("");

  // Section data
  const [denialData, setDenialData] = useState(null);
  const [payerData, setPayerData] = useState(null);
  const [roiData, setRoiData] = useState(null);
  const [activeSection, setActiveSection] = useState(null);
  const [sectionLoading, setSectionLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Validate token on mount
  const fetchMe = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const res = await fetch(`${API}/api/billing/portal/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setPortalData(await res.json());
      } else {
        localStorage.removeItem("portal_token");
        setToken(null);
      }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetchMe(); }, [fetchMe]);

  // Fetch section data
  const fetchSection = useCallback(async (section) => {
    if (!token) return;
    setSectionLoading(true);
    try {
      const h = { Authorization: `Bearer ${token}` };
      if (section === "denial_summary") {
        const res = await fetch(`${API}/api/billing/portal/denial-summary?days=90`, { headers: h });
        if (res.ok) setDenialData(await res.json());
      } else if (section === "payer_performance") {
        const res = await fetch(`${API}/api/billing/portal/payer-performance?days=90`, { headers: h });
        if (res.ok) setPayerData(await res.json());
      } else if (section === "appeal_roi") {
        const res = await fetch(`${API}/api/billing/portal/appeal-roi?days=180`, { headers: h });
        if (res.ok) setRoiData(await res.json());
      }
    } catch { /* ignore */ }
    finally { setSectionLoading(false); }
  }, [token]);

  useEffect(() => {
    if (activeSection) fetchSection(activeSection);
  }, [activeSection, fetchSection]);

  // Auto-select first enabled section
  useEffect(() => {
    if (portalData && !activeSection) {
      const ps = portalData.portal_settings || {};
      if (ps.show_denial_summary) setActiveSection("denial_summary");
      else if (ps.show_payer_performance) setActiveSection("payer_performance");
      else if (ps.show_appeal_roi) setActiveSection("appeal_roi");
    }
  }, [portalData, activeSection]);

  const handleSendOtp = async () => {
    if (!email.includes("@")) { setError("Enter a valid email."); return; }
    if (!practiceId) { setError("Missing practice ID in URL."); return; }
    setSending(true); setError("");
    try {
      const res = await fetch(`${API}/api/billing/portal/send-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), practice_id: practiceId }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Failed to send code."); return; }
      setOtpStep("otp");
    } catch { setError("Failed to send code."); }
    finally { setSending(false); }
  };

  const handleVerify = async () => {
    if (code.length !== 8) { setError("Enter the 8-digit code."); return; }
    setVerifying(true); setError("");
    try {
      const res = await fetch(`${API}/api/billing/portal/verify-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: code.trim(), practice_id: practiceId }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || "Invalid code."); return; }
      localStorage.setItem("portal_token", data.token);
      setToken(data.token);
      setPortalData({
        practice_name: data.practice_name,
        billing_company_name: data.billing_company_name,
        portal_settings: data.portal_settings,
        email: data.email,
      });
    } catch { setError("Verification failed."); }
    finally { setVerifying(false); }
  };

  const handleLogout = () => {
    localStorage.removeItem("portal_token");
    setToken(null);
    setPortalData(null);
    setActiveSection(null);
  };

  const handleDownloadReport = async () => {
    setGenerating(true);
    try {
      const res = await fetch(`${API}/api/billing/portal/generate-report`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "practice_report.pdf";
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch { /* ignore */ }
    finally { setGenerating(false); }
  };

  // --- Loading ---
  if (loading) {
    return <PageShell><p style={{ color: "#94a3b8" }}>Loading...</p></PageShell>;
  }

  // --- OTP Login ---
  if (!token || !portalData) {
    return (
      <PageShell>
        <div style={{ maxWidth: 400, margin: "0 auto", paddingTop: 80 }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Practice Portal</h1>
            <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 14 }}>Sign in to view your billing data</p>
          </div>

          {otpStep === "email" && (
            <form onSubmit={(e) => { e.preventDefault(); handleSendOtp(); }}>
              <label style={labelSt}>Email address</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@practice.com" style={inputSt} />
              <button type="submit" disabled={sending} style={{
                ...btnSt, background: sending ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
              }}>{sending ? "Sending..." : "Send Code"}</button>
              <p style={{ textAlign: "center", fontSize: 13, color: "#94a3b8", marginTop: 12 }}>
                We'll send an 8-digit code to your email.
              </p>
            </form>
          )}

          {otpStep === "otp" && (
            <div style={{ padding: 20, borderRadius: 12, border: "1px solid #0d9488", background: "rgba(13,148,136,0.08)", textAlign: "center" }}>
              <p style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 16 }}>
                Code sent to <strong>{email}</strong>
              </p>
              <input type="text" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
                onKeyDown={(e) => e.key === "Enter" && handleVerify()}
                maxLength={8} placeholder="12345678" style={{
                  ...inputSt, fontSize: 20, letterSpacing: 6, textAlign: "center", marginBottom: 12,
                }} />
              <button onClick={handleVerify} disabled={verifying} style={{
                ...btnSt, background: verifying ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
              }}>{verifying ? "Verifying..." : "Sign In"}</button>
              <button onClick={() => { setOtpStep("email"); setCode(""); setError(""); }}
                style={{ fontSize: 12, color: "#94a3b8", background: "none", border: "none", cursor: "pointer", marginTop: 8 }}>
                Use a different email
              </button>
            </div>
          )}

          {error && (
            <div style={{ padding: 10, borderRadius: 8, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", marginTop: 12 }}>
              <p style={{ color: "#fca5a5", fontSize: 13, margin: 0 }}>{error}</p>
            </div>
          )}
        </div>
      </PageShell>
    );
  }

  // --- Portal Dashboard ---
  const ps = portalData.portal_settings || {};
  const sections = [
    ps.show_denial_summary && { id: "denial_summary", label: "Denial Summary" },
    ps.show_payer_performance && { id: "payer_performance", label: "Payer Performance" },
    ps.show_appeal_roi && { id: "appeal_roi", label: "Appeal & Recovery" },
  ].filter(Boolean);

  return (
    <div style={pageSt}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <header style={{
        padding: "0 32px", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between",
        borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(10,22,40,0.95)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: "#f1f5f9" }}>
            {portalData.billing_company_name}
          </span>
          <span style={{ color: "#475569", fontSize: 13 }}>|</span>
          <span style={{ color: "#94a3b8", fontSize: 13 }}>{portalData.practice_name}</span>
        </div>
        <button onClick={handleLogout} style={{ fontSize: 12, color: "#94a3b8", background: "none", border: "none", cursor: "pointer" }}>
          Sign Out
        </button>
      </header>

      {/* Section tabs */}
      {sections.length > 0 && (
        <nav style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "0 32px", display: "flex" }}>
          {sections.map(s => (
            <button key={s.id} onClick={() => setActiveSection(s.id)} style={{
              padding: "12px 16px", fontSize: 13, fontWeight: activeSection === s.id ? 600 : 400,
              color: activeSection === s.id ? "#f1f5f9" : "#64748b",
              background: "none", border: "none", cursor: "pointer",
              borderBottom: activeSection === s.id ? "2px solid #14b8a6" : "2px solid transparent",
            }}>
              {s.label}
            </button>
          ))}
        </nav>
      )}

      {/* Content */}
      <main style={{ padding: "24px 32px", maxWidth: 900, margin: "0 auto" }}>
        {sectionLoading ? (
          <p style={{ color: "#94a3b8", fontSize: 14 }}>Loading...</p>
        ) : activeSection === "denial_summary" && denialData ? (
          <DenialSummaryView data={denialData} />
        ) : activeSection === "payer_performance" && payerData ? (
          <PayerPerformanceView data={payerData} />
        ) : activeSection === "appeal_roi" && roiData ? (
          <AppealRoiView data={roiData} />
        ) : (
          <p style={{ color: "#94a3b8", fontSize: 14, textAlign: "center", paddingTop: 48 }}>
            Select a section above to view your data.
          </p>
        )}

        {/* Generate Report button */}
        {ps.show_generate_report && (
          <div style={{ marginTop: 32, textAlign: "center" }}>
            <button onClick={handleDownloadReport} disabled={generating} style={{
              padding: "10px 24px", borderRadius: 8, border: "none", cursor: "pointer",
              background: generating ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
              color: "#fff", fontWeight: 600, fontSize: 14,
            }}>
              {generating ? "Generating PDF..." : "Download Report (PDF)"}
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{
        padding: "24px 32px", textAlign: "center", borderTop: "1px solid rgba(255,255,255,0.04)",
        fontSize: 11, color: "#475569", marginTop: 48,
      }}>
        Powered by CivicScale
      </footer>
    </div>
  );
}

// --- Section views (read-only) ---
function DenialSummaryView({ data }) {
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        <Tile label="Total Lines" value={data.total_lines?.toLocaleString()} />
        <Tile label="Denied" value={data.denied_count?.toLocaleString()} />
        <Tile label="Denial Rate" value={`${data.denial_rate}%`} color={data.denial_rate > 10 ? "#fca5a5" : "#5eead4"} />
        <Tile label="Denied Amount" value={`$${Number(data.denied_amount || 0).toLocaleString()}`} />
      </div>
      {(data.denial_codes || []).length > 0 && (
        <>
          <h3 style={h3St}>Top Denial Codes</h3>
          <div style={tableSt}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr style={thrSt}><th style={thSt}>Code</th><th style={thSt}>Description</th><th style={thSt}>Count</th><th style={thSt}>Amount</th></tr></thead>
              <tbody>
                {data.denial_codes.map(d => (
                  <tr key={d.code} style={tbrSt}>
                    <td style={tdSt}><span style={codeBadge}>{d.code}</span></td>
                    <td style={{ ...tdSt, color: "#94a3b8", fontSize: 12 }}>{d.description || "—"}</td>
                    <td style={{ ...tdSt, color: "#f1f5f9" }}>{d.count}</td>
                    <td style={{ ...tdSt, color: "#94a3b8" }}>${Number(d.amount).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function PayerPerformanceView({ data }) {
  return (
    <div>
      <h3 style={h3St}>Payer Breakdown</h3>
      {(data.payers || []).length === 0 ? (
        <p style={{ color: "#94a3b8", fontSize: 14 }}>No payer data.</p>
      ) : (
        <div style={tableSt}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr style={thrSt}><th style={thSt}>Payer</th><th style={thSt}>Billed</th><th style={thSt}>Paid</th><th style={thSt}>Lines</th><th style={thSt}>Denial %</th></tr></thead>
            <tbody>
              {data.payers.map(p => (
                <tr key={p.payer_name} style={tbrSt}>
                  <td style={tdSt}>{p.payer_name}</td>
                  <td style={{ ...tdSt, color: "#94a3b8" }}>${Number(p.total_billed).toLocaleString()}</td>
                  <td style={{ ...tdSt, color: "#94a3b8" }}>${Number(p.total_paid).toLocaleString()}</td>
                  <td style={{ ...tdSt, color: "#94a3b8" }}>{p.line_count}</td>
                  <td style={{ ...tdSt, color: p.denial_rate > 10 ? "#fca5a5" : "#5eead4" }}>{p.denial_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AppealRoiView({ data }) {
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <Tile label="Total Denied" value={`$${Number(data.total_denied || 0).toLocaleString()}`} />
        <Tile label="Total Recovered" value={`$${Number(data.total_recovered || 0).toLocaleString()}`} color="#5eead4" />
        <Tile label="Recovery Rate" value={`${data.recovery_rate || 0}%`} color={data.recovery_rate >= 50 ? "#5eead4" : "#fbbf24"} />
        <Tile label="Recoveries" value={data.recovery_count || 0} />
      </div>
      {data.recovery_count === 0 && (
        <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 16, fontStyle: "italic" }}>
          No cross-file recoveries detected yet. Recoveries appear when denied claims are paid in subsequent remittance files.
        </p>
      )}
    </div>
  );
}

function Tile({ label, value, color }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 10, padding: 16,
    }}>
      <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 600, color: color || "#f1f5f9" }}>{value}</div>
    </div>
  );
}

function PageShell({ children }) {
  return (
    <div style={pageSt}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {children}
      </div>
      <footer style={{ padding: "16px 32px", textAlign: "center", fontSize: 11, color: "#475569" }}>
        Powered by CivicScale
      </footer>
    </div>
  );
}

// --- Shared styles ---
const pageSt = { margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0", minHeight: "100vh", background: "#0a1628" };
const labelSt = { display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 };
const inputSt = {
  width: "100%", padding: "10px 12px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.12)",
  fontSize: 15, outline: "none", boxSizing: "border-box", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", marginBottom: 12,
};
const btnSt = { width: "100%", padding: "12px", borderRadius: 8, border: "none", cursor: "pointer", color: "#fff", fontWeight: 700, fontSize: 15 };
const h3St = { fontSize: 14, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" };
const tableSt = { background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 10, overflow: "hidden" };
const thrSt = { borderBottom: "1px solid rgba(255,255,255,0.06)" };
const thSt = { padding: "10px 14px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" };
const tbrSt = { borderBottom: "1px solid rgba(255,255,255,0.04)" };
const tdSt = { padding: "10px 14px", fontSize: 13, color: "#e2e8f0" };
const codeBadge = { fontFamily: "monospace", fontSize: 11, fontWeight: 600, padding: "2px 6px", borderRadius: 4, background: "rgba(239,68,68,0.1)", color: "#fca5a5" };
