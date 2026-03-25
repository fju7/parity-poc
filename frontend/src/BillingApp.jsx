import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { API_BASE as API } from "./lib/apiBase";
import "./components/CivicScaleHomepage.css";

const TABS = [
  { id: "practices", label: "Practices" },
  { id: "ingestion", label: "835 Ingestion" },
  { id: "portfolio", label: "Portfolio Dashboard" },
  { id: "team", label: "Team" },
  { id: "settings", label: "Settings" },
];

export default function BillingApp() {
  const navigate = useNavigate();
  const { token, user, company, login, logout: authLogout, isAuthenticated, loading } = useAuth();

  // --- All hooks declared at top, before any conditional returns ---
  const [activeTab, setActiveTab] = useState("practices");
  const [billingCompany, setBillingCompany] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [meLoading, setMeLoading] = useState(false);

  // OTP state
  const [otpEmail, setOtpEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [otpStep, setOtpStep] = useState("email"); // "email" | "otp"
  const [otpSending, setOtpSending] = useState(false);
  const [otpVerifying, setOtpVerifying] = useState(false);
  const [otpError, setOtpError] = useState("");

  // Registration state
  const [regCompanyName, setRegCompanyName] = useState("");
  const [regFullName, setRegFullName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regSaving, setRegSaving] = useState(false);
  const [regError, setRegError] = useState("");
  const [needsRegistration, setNeedsRegistration] = useState(false);

  // Settings state
  const [settingsCompanyName, setSettingsCompanyName] = useState("");
  const [settingsContactEmail, setSettingsContactEmail] = useState("");
  const [settingsUserName, setSettingsUserName] = useState("");
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsMsg, setSettingsMsg] = useState("");

  // Ingestion state
  const [ingestPracticeId, setIngestPracticeId] = useState("");
  const [ingestFiles, setIngestFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [jobs, setJobs] = useState([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [expandedJobId, setExpandedJobId] = useState(null);
  const [expandedJobDetail, setExpandedJobDetail] = useState(null);
  const pollRef = useRef(null);

  // Practices state
  const [practices, setPractices] = useState([]);
  const [practicesLoading, setPracticesLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPracticeName, setNewPracticeName] = useState("");
  const [newPracticeEmail, setNewPracticeEmail] = useState("");
  const [addingPractice, setAddingPractice] = useState(false);
  const [practiceError, setPracticeError] = useState("");

  // Fetch billing /me on auth
  const fetchMe = useCallback(async () => {
    if (!token) return;
    setMeLoading(true);
    try {
      const res = await fetch(`${API}/api/billing/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setBillingCompany(data.billing_company);
        setSubscription(data.subscription);
        setNeedsRegistration(false);
      } else if (res.status === 404) {
        // Has auth session but no billing company — needs registration
        setNeedsRegistration(true);
      } else if (res.status === 401 || res.status === 403) {
        // Not a billing user — might need registration
        setNeedsRegistration(true);
      }
    } catch {
      // ignore
    } finally {
      setMeLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (isAuthenticated && company?.type === "billing") {
      fetchMe();
    } else if (isAuthenticated && company?.type !== "billing") {
      setNeedsRegistration(true);
    }
  }, [isAuthenticated, company, fetchMe]);

  // Fetch practices
  const fetchPractices = useCallback(async () => {
    if (!token || !billingCompany) return;
    setPracticesLoading(true);
    try {
      const res = await fetch(`${API}/api/billing/practices`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPractices(data.practices || []);
      }
    } catch {
      // ignore
    } finally {
      setPracticesLoading(false);
    }
  }, [token, billingCompany]);

  useEffect(() => {
    if (billingCompany) fetchPractices();
  }, [billingCompany, fetchPractices]);

  // Fetch ingestion jobs
  const fetchJobs = useCallback(async () => {
    if (!token || !billingCompany) return;
    try {
      const res = await fetch(`${API}/api/billing/ingest/jobs`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
      }
    } catch { /* ignore */ }
  }, [token, billingCompany]);

  useEffect(() => {
    if (billingCompany && activeTab === "ingestion") fetchJobs();
  }, [billingCompany, activeTab, fetchJobs]);

  // Auto-poll while any job is queued or processing
  useEffect(() => {
    const hasActive = jobs.some(j => j.status === "queued" || j.status === "processing");
    if (hasActive && activeTab === "ingestion") {
      pollRef.current = setInterval(fetchJobs, 5000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobs, activeTab, fetchJobs]);

  // Seed settings fields when data loads
  useEffect(() => {
    if (billingCompany) {
      setSettingsCompanyName(billingCompany.company_name || "");
      setSettingsContactEmail(billingCompany.contact_email || "");
    }
  }, [billingCompany]);

  useEffect(() => {
    if (user) {
      setSettingsUserName(user.full_name || "");
    }
  }, [user]);

  // --- Loading state ---
  if (loading) {
    return (
      <div style={styles.page}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
          <p style={{ color: "#94a3b8" }}>Loading...</p>
        </div>
      </div>
    );
  }

  // --- OTP Sign-In ---
  if (!isAuthenticated) {
    const handleSendOtp = async () => {
      if (!otpEmail.includes("@")) { setOtpError("Enter a valid email address."); return; }
      setOtpSending(true); setOtpError("");
      try {
        const res = await fetch(`${API}/api/billing/send-otp`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: otpEmail.trim().toLowerCase() }),
        });
        if (!res.ok) throw new Error();
        setOtpStep("otp");
      } catch { setOtpError("Failed to send code. Please try again."); }
      setOtpSending(false);
    };

    const handleVerifyOtp = async () => {
      if (otpCode.length !== 8) { setOtpError("Enter the 8-digit code from your email."); return; }
      setOtpVerifying(true); setOtpError("");
      try {
        const res = await fetch(`${API}/api/billing/verify-otp`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: otpEmail.trim().toLowerCase(), code: otpCode.trim() }),
        });
        const data = await res.json();
        if (!res.ok) { setOtpError(data.detail || "Invalid code."); return; }
        if (data.needs_company) {
          setRegEmail(otpEmail.trim().toLowerCase());
          setNeedsRegistration(true);
          // Still need a token for registration — user verified OTP but has no company
          return;
        }
        login(data.token, data.user, data.company);
        if (data.billing_company) setBillingCompany(data.billing_company);
      } catch { setOtpError("Verification failed. Please try again."); }
      finally { setOtpVerifying(false); }
    };

    return (
      <div style={styles.page}>
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <header style={styles.header}>
          <a href="https://civicscale.ai" style={styles.logoLink}>
            <div style={styles.logoIcon}>C</div>
            <span style={styles.logoText}>CivicScale</span>
          </a>
        </header>

        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 400, padding: "0 16px" }}>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Parity Billing</h1>
              <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 15 }}>Sign in to your account</p>
            </div>

            {!needsRegistration && otpStep === "email" && (
              <form onSubmit={(e) => { e.preventDefault(); handleSendOtp(); }}>
                <div style={{ marginBottom: 16 }}>
                  <label style={styles.label}>Email address</label>
                  <input type="email" required value={otpEmail}
                    onChange={(e) => setOtpEmail(e.target.value)}
                    placeholder="you@company.com" style={styles.input} />
                </div>
                <button type="submit" disabled={otpSending} style={{
                  ...styles.btn, background: otpSending ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                }}>
                  {otpSending ? "Sending..." : "Send Code"}
                </button>
                <p style={{ textAlign: "center", fontSize: 13, color: "#94a3b8", marginTop: 16 }}>
                  We'll send you an 8-digit code — no password needed.
                </p>
              </form>
            )}

            {!needsRegistration && otpStep === "otp" && (
              <div style={styles.otpBox}>
                <p style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 4 }}>
                  We sent an 8-digit code to <strong>{otpEmail}</strong>.
                </p>
                <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 20 }}>
                  Check your inbox and enter it below. The code expires in 10 minutes.
                </p>
                <input type="text" placeholder="12345678" value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
                  onKeyDown={(e) => e.key === "Enter" && handleVerifyOtp()}
                  maxLength={8} style={styles.otpInput} />
                <button onClick={handleVerifyOtp} disabled={otpVerifying} style={{
                  ...styles.btn, background: otpVerifying ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                }}>
                  {otpVerifying ? "Verifying..." : "Sign In"}
                </button>
                <button onClick={() => { setOtpStep("email"); setOtpCode(""); setOtpError(""); }}
                  style={styles.linkBtn}>Use a different email</button>
              </div>
            )}

            {needsRegistration && renderRegistrationForm()}

            {otpError && (
              <div style={styles.errorBox}>
                <p style={{ color: "#fca5a5", fontSize: 13, margin: 0 }}>{otpError}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // --- Registration form (verified OTP but no billing company) ---
  if (needsRegistration || (isAuthenticated && !billingCompany && !meLoading)) {
    return (
      <div style={styles.page}>
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
        <header style={styles.header}>
          <a href="https://civicscale.ai" style={styles.logoLink}>
            <div style={styles.logoIcon}>C</div>
            <span style={styles.logoText}>CivicScale</span>
          </a>
          <button onClick={() => { authLogout(); setNeedsRegistration(false); setOtpStep("email"); }}
            style={styles.linkBtn}>Sign Out</button>
        </header>
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 440, padding: "0 16px" }}>
            {renderRegistrationForm()}
          </div>
        </div>
      </div>
    );
  }

  // --- Loading billing data ---
  if (meLoading) {
    return (
      <div style={styles.page}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh" }}>
          <p style={{ color: "#94a3b8" }}>Loading billing dashboard...</p>
        </div>
      </div>
    );
  }

  // --- Registration form helper ---
  function renderRegistrationForm() {
    const handleRegister = async () => {
      const email = regEmail || otpEmail || user?.email || "";
      if (!regCompanyName.trim()) { setRegError("Company name is required."); return; }
      if (!regFullName.trim()) { setRegError("Your name is required."); return; }
      if (!email || !email.includes("@")) { setRegError("Valid email is required."); return; }

      setRegSaving(true); setRegError("");
      try {
        const res = await fetch(`${API}/api/billing/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.trim().toLowerCase(),
            full_name: regFullName.trim(),
            company_name: regCompanyName.trim(),
          }),
        });
        const data = await res.json();
        if (!res.ok) { setRegError(data.detail || "Registration failed."); return; }
        login(data.token, data.user, data.company);
        setBillingCompany(data.billing_company);
        setNeedsRegistration(false);
      } catch { setRegError("Registration failed. Please try again."); }
      finally { setRegSaving(false); }
    };

    return (
      <div>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Register Your Billing Company</h1>
          <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 14 }}>
            Set up your account to start managing practice billing.
          </p>
        </div>
        <form onSubmit={(e) => { e.preventDefault(); handleRegister(); }}>
          <div style={{ marginBottom: 16 }}>
            <label style={styles.label}>Company name</label>
            <input type="text" required value={regCompanyName}
              onChange={(e) => setRegCompanyName(e.target.value)}
              placeholder="Acme Billing Co" style={styles.input} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={styles.label}>Your name</label>
            <input type="text" required value={regFullName}
              onChange={(e) => setRegFullName(e.target.value)}
              placeholder="Jane Smith" style={styles.input} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={styles.label}>Email</label>
            <input type="email" required value={regEmail || otpEmail || user?.email || ""}
              onChange={(e) => setRegEmail(e.target.value)}
              placeholder="you@company.com" style={styles.input} />
          </div>
          <button type="submit" disabled={regSaving} style={{
            ...styles.btn, background: regSaving ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
          }}>
            {regSaving ? "Creating..." : "Create Billing Company"}
          </button>
          {regError && (
            <div style={styles.errorBox}>
              <p style={{ color: "#fca5a5", fontSize: 13, margin: 0 }}>{regError}</p>
            </div>
          )}
        </form>
      </div>
    );
  }

  // --- Dashboard ---
  const handleAddPractice = async () => {
    if (!newPracticeName.trim()) { setPracticeError("Practice name required."); return; }
    if (!newPracticeEmail.includes("@")) { setPracticeError("Valid contact email required."); return; }
    setAddingPractice(true); setPracticeError("");
    try {
      const res = await fetch(`${API}/api/billing/practices`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ practice_name: newPracticeName.trim(), contact_email: newPracticeEmail.trim().toLowerCase() }),
      });
      const data = await res.json();
      if (!res.ok) { setPracticeError(data.detail || "Failed to add practice."); return; }
      setNewPracticeName(""); setNewPracticeEmail(""); setShowAddForm(false);
      fetchPractices();
    } catch { setPracticeError("Failed to add practice."); }
    finally { setAddingPractice(false); }
  };

  const handleDeactivate = async (practiceId) => {
    try {
      await fetch(`${API}/api/billing/practices/${practiceId}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchPractices();
    } catch { /* ignore */ }
  };

  const trialDays = subscription?.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(subscription.trial_ends_at) - new Date()) / (1000 * 60 * 60 * 24)))
    : null;

  return (
    <div style={styles.page}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <header style={{ ...styles.header, justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <a href="https://civicscale.ai" style={styles.logoLink}>
            <div style={styles.logoIcon}>C</div>
            <span style={styles.logoText}>CivicScale</span>
          </a>
          <span style={{ color: "#475569", fontSize: 14 }}>|</span>
          <span style={{ color: "#94a3b8", fontSize: 14, fontWeight: 500 }}>
            {billingCompany?.company_name || "Parity Billing"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ color: "#64748b", fontSize: 13 }}>{user?.email}</span>
          <button onClick={authLogout} style={{ ...styles.linkBtn, color: "#94a3b8", fontSize: 13 }}>Sign Out</button>
        </div>
      </header>

      {/* Trial banner */}
      {subscription?.tier === "trial" && trialDays !== null && (
        <div style={{
          background: "rgba(13,148,136,0.1)", borderBottom: "1px solid rgba(13,148,136,0.2)",
          padding: "10px 40px", textAlign: "center", fontSize: 14, color: "#5eead4", marginTop: 64,
        }}>
          Your 30-day free trial has started. {trialDays} days remaining.
        </div>
      )}

      {/* Nav tabs */}
      <nav style={{
        marginTop: subscription?.tier === "trial" ? 0 : 64,
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "0 40px", display: "flex", gap: 0,
      }}>
        {TABS.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            padding: "14px 20px", fontSize: 14, fontWeight: activeTab === tab.id ? 600 : 400,
            color: activeTab === tab.id ? "#f1f5f9" : "#64748b",
            background: "none", border: "none", cursor: "pointer",
            borderBottom: activeTab === tab.id ? "2px solid #14b8a6" : "2px solid transparent",
          }}>
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Content */}
      <main style={{ padding: "32px 40px", maxWidth: 1000, margin: "0 auto" }}>
        {activeTab === "practices" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
              <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Practices</h2>
              <button onClick={() => setShowAddForm(true)} style={{
                padding: "8px 16px", borderRadius: 8, border: "none", cursor: "pointer",
                background: "linear-gradient(135deg, #0d9488, #14b8a6)", color: "#fff",
                fontWeight: 600, fontSize: 14,
              }}>
                + Add Practice
              </button>
            </div>

            {/* Add practice form */}
            {showAddForm && (
              <div style={{
                background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 12, padding: 24, marginBottom: 24,
              }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Add Practice</h3>
                <div style={{ display: "flex", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <label style={styles.label}>Practice name</label>
                    <input type="text" value={newPracticeName}
                      onChange={(e) => setNewPracticeName(e.target.value)}
                      placeholder="Sunrise Family Medicine" style={styles.input} />
                  </div>
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <label style={styles.label}>Contact email</label>
                    <input type="email" value={newPracticeEmail}
                      onChange={(e) => setNewPracticeEmail(e.target.value)}
                      placeholder="admin@sunrise.com" style={styles.input} />
                  </div>
                </div>
                <div style={{ display: "flex", gap: 12 }}>
                  <button onClick={handleAddPractice} disabled={addingPractice} style={{
                    padding: "8px 20px", borderRadius: 8, border: "none", cursor: "pointer",
                    background: addingPractice ? "#334155" : "#0d9488", color: "#fff", fontWeight: 600, fontSize: 14,
                  }}>
                    {addingPractice ? "Adding..." : "Add"}
                  </button>
                  <button onClick={() => { setShowAddForm(false); setPracticeError(""); }}
                    style={{ padding: "8px 20px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)",
                      background: "none", color: "#94a3b8", cursor: "pointer", fontSize: 14 }}>
                    Cancel
                  </button>
                </div>
                {practiceError && (
                  <div style={{ ...styles.errorBox, marginTop: 12 }}>
                    <p style={{ color: "#fca5a5", fontSize: 13, margin: 0 }}>{practiceError}</p>
                  </div>
                )}
              </div>
            )}

            {/* Practices table */}
            {practicesLoading ? (
              <p style={{ color: "#94a3b8" }}>Loading practices...</p>
            ) : practices.length === 0 ? (
              <div style={{
                background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
                borderRadius: 12, padding: 48, textAlign: "center",
              }}>
                <p style={{ color: "#94a3b8", fontSize: 15, margin: 0 }}>No practices yet. Click "Add Practice" to get started.</p>
              </div>
            ) : (
              <div style={{
                background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 12, overflow: "hidden",
              }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                      <th style={styles.th}>Practice Name</th>
                      <th style={styles.th}>Contact Email</th>
                      <th style={styles.th}>Status</th>
                      <th style={styles.th}>Added</th>
                      <th style={styles.th}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {practices.map((p) => (
                      <tr key={p.link_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                        <td style={styles.td}>{p.practice_name}</td>
                        <td style={{ ...styles.td, color: "#94a3b8" }}>{p.contact_email}</td>
                        <td style={styles.td}>
                          <span style={{
                            display: "inline-block", padding: "2px 10px", borderRadius: 12, fontSize: 12, fontWeight: 600,
                            background: p.active ? "rgba(13,148,136,0.15)" : "rgba(239,68,68,0.1)",
                            color: p.active ? "#5eead4" : "#fca5a5",
                          }}>
                            {p.active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td style={{ ...styles.td, color: "#64748b", fontSize: 13 }}>
                          {p.added_at ? new Date(p.added_at).toLocaleDateString() : "—"}
                        </td>
                        <td style={styles.td}>
                          {p.active && (
                            <button onClick={() => handleDeactivate(p.practice_id)}
                              style={{ fontSize: 12, color: "#f87171", background: "none", border: "none", cursor: "pointer" }}>
                              Deactivate
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === "ingestion" && (
          <IngestionPanel
            token={token}
            practices={practices}
            jobs={jobs}
            jobsLoading={jobsLoading}
            ingestPracticeId={ingestPracticeId}
            setIngestPracticeId={setIngestPracticeId}
            ingestFiles={ingestFiles}
            setIngestFiles={setIngestFiles}
            uploading={uploading}
            setUploading={setUploading}
            uploadError={uploadError}
            setUploadError={setUploadError}
            expandedJobId={expandedJobId}
            setExpandedJobId={setExpandedJobId}
            expandedJobDetail={expandedJobDetail}
            setExpandedJobDetail={setExpandedJobDetail}
            fetchJobs={fetchJobs}
          />
        )}

        {activeTab === "settings" && (
          <SettingsPanel
            billingCompany={billingCompany}
            subscription={subscription}
            user={user}
            token={token}
            settingsCompanyName={settingsCompanyName}
            setSettingsCompanyName={setSettingsCompanyName}
            settingsContactEmail={settingsContactEmail}
            setSettingsContactEmail={setSettingsContactEmail}
            settingsUserName={settingsUserName}
            setSettingsUserName={setSettingsUserName}
            settingsSaving={settingsSaving}
            setSettingsSaving={setSettingsSaving}
            settingsMsg={settingsMsg}
            setSettingsMsg={setSettingsMsg}
            fetchMe={fetchMe}
          />
        )}

        {activeTab !== "practices" && activeTab !== "ingestion" && activeTab !== "settings" && (
          <div style={{
            background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
            borderRadius: 12, padding: 48, textAlign: "center",
          }}>
            <p style={{ color: "#94a3b8", fontSize: 15, margin: 0 }}>Coming soon</p>
          </div>
        )}
      </main>
    </div>
  );
}

// --- Ingestion Panel ---
function IngestionPanel({
  token, practices, jobs, jobsLoading,
  ingestPracticeId, setIngestPracticeId,
  ingestFiles, setIngestFiles,
  uploading, setUploading,
  uploadError, setUploadError,
  expandedJobId, setExpandedJobId,
  expandedJobDetail, setExpandedJobDetail,
  fetchJobs,
}) {
  const fileInputRef = useRef(null);
  const activePractices = practices.filter(p => p.active);

  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files).filter(f => {
      const ext = f.name.split(".").pop().toLowerCase();
      return ["835", "txt", "edi"].includes(ext);
    });
    setIngestFiles(prev => [...prev, ...dropped]);
  };

  const handleFileSelect = (e) => {
    const selected = Array.from(e.target.files || []);
    setIngestFiles(prev => [...prev, ...selected]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleUpload = async () => {
    if (!ingestPracticeId) { setUploadError("Select a practice."); return; }
    if (ingestFiles.length === 0) { setUploadError("Add at least one 835 file."); return; }
    if (ingestFiles.length > 20) { setUploadError("Maximum 20 files per upload."); return; }

    setUploading(true); setUploadError("");
    try {
      const fd = new FormData();
      fd.append("practice_id", ingestPracticeId);
      ingestFiles.forEach(f => fd.append("files", f));

      const res = await fetch(`${API}/api/billing/ingest/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) { setUploadError(data.detail || "Upload failed."); return; }

      setIngestFiles([]);

      // Auto-process all queued jobs
      await fetch(`${API}/api/billing/ingest/process-all`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      fetchJobs();
    } catch { setUploadError("Upload failed."); }
    finally { setUploading(false); }
  };

  const handleRowClick = async (job) => {
    if (job.status !== "complete") return;
    if (expandedJobId === job.id) { setExpandedJobId(null); setExpandedJobDetail(null); return; }
    setExpandedJobId(job.id);
    try {
      const res = await fetch(`${API}/api/billing/ingest/jobs/${job.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setExpandedJobDetail(data);
      }
    } catch { /* ignore */ }
  };

  const statusBadge = (status) => {
    const map = {
      queued: { bg: "rgba(148,163,184,0.15)", color: "#94a3b8" },
      processing: { bg: "rgba(59,130,246,0.15)", color: "#60a5fa" },
      complete: { bg: "rgba(13,148,136,0.15)", color: "#5eead4" },
      error: { bg: "rgba(239,68,68,0.1)", color: "#fca5a5" },
    };
    const s = map[status] || map.queued;
    return (
      <span style={{
        display: "inline-block", padding: "2px 10px", borderRadius: 12,
        fontSize: 12, fontWeight: 600, textTransform: "uppercase",
        background: s.bg, color: s.color,
      }}>
        {status}
      </span>
    );
  };

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 24px" }}>835 Ingestion</h2>

      {/* Upload panel */}
      <div style={{
        background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 12, padding: 24, marginBottom: 24,
      }}>
        <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap", alignItems: "flex-end" }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>Practice</label>
            <select value={ingestPracticeId} onChange={(e) => setIngestPracticeId(e.target.value)}
              style={{
                width: "100%", padding: "10px 12px", borderRadius: 8,
                border: "1px solid rgba(255,255,255,0.12)", fontSize: 14,
                background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
                appearance: "auto", boxSizing: "border-box",
              }}>
              <option value="">Select practice...</option>
              {activePractices.map(p => (
                <option key={p.practice_id} value={p.practice_id}>{p.practice_name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: "2px dashed rgba(255,255,255,0.12)", borderRadius: 12,
            padding: 32, textAlign: "center", cursor: "pointer",
            background: "rgba(255,255,255,0.02)", marginBottom: 16,
            transition: "border-color 0.2s",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(13,148,136,0.4)"; }}
          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)"; }}
        >
          <input ref={fileInputRef} type="file" multiple accept=".835,.txt,.edi"
            onChange={handleFileSelect} style={{ display: "none" }} />
          <p style={{ color: "#94a3b8", fontSize: 14, margin: 0 }}>
            Drop .835 / .edi / .txt files here, or click to browse
          </p>
          <p style={{ color: "#64748b", fontSize: 12, margin: "8px 0 0" }}>Maximum 20 files per upload</p>
        </div>

        {/* File list */}
        {ingestFiles.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            {ingestFiles.map((f, i) => (
              <div key={i} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "6px 12px", background: "rgba(255,255,255,0.03)",
                borderRadius: 6, marginBottom: 4, fontSize: 13, color: "#cbd5e1",
              }}>
                <span>{f.name}</span>
                <button onClick={() => setIngestFiles(prev => prev.filter((_, idx) => idx !== i))}
                  style={{ color: "#f87171", background: "none", border: "none", cursor: "pointer", fontSize: 12 }}>
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button onClick={handleUpload} disabled={uploading || ingestFiles.length === 0}
            style={{
              padding: "10px 20px", borderRadius: 8, border: "none", cursor: "pointer",
              background: uploading ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
              color: "#fff", fontWeight: 600, fontSize: 14,
              opacity: (uploading || ingestFiles.length === 0) ? 0.6 : 1,
            }}>
            {uploading ? "Uploading..." : `Upload & Queue (${ingestFiles.length})`}
          </button>
          {uploadError && <span style={{ color: "#fca5a5", fontSize: 13 }}>{uploadError}</span>}
        </div>
      </div>

      {/* Jobs table */}
      <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Job Queue</h3>
      {jobs.length === 0 ? (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 15, margin: 0 }}>No ingestion jobs yet. Upload 835 files above.</p>
        </div>
      ) : (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 12, overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th style={styles.th}>Filename</th>
                <th style={styles.th}>Practice</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Lines</th>
                <th style={styles.th}>Denial Rate</th>
                <th style={styles.th}>Total Billed</th>
                <th style={styles.th}>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <React.Fragment key={j.id}>
                  <tr
                    onClick={() => handleRowClick(j)}
                    style={{
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                      cursor: j.status === "complete" ? "pointer" : "default",
                      background: expandedJobId === j.id ? "rgba(13,148,136,0.05)" : "transparent",
                    }}
                  >
                    <td style={styles.td}>{j.filename}</td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>{j.practice_name}</td>
                    <td style={styles.td}>{statusBadge(j.status)}</td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>{j.line_count ?? "—"}</td>
                    <td style={{ ...styles.td, color: j.denial_rate > 10 ? "#fca5a5" : "#94a3b8" }}>
                      {j.denial_rate != null ? `${j.denial_rate}%` : "—"}
                    </td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>
                      {j.total_billed != null ? `$${Number(j.total_billed).toLocaleString()}` : "—"}
                    </td>
                    <td style={{ ...styles.td, color: "#64748b", fontSize: 13 }}>
                      {j.created_at ? new Date(j.created_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                  {expandedJobId === j.id && expandedJobDetail?.result_json && (
                    <tr>
                      <td colSpan={7} style={{ padding: 0 }}>
                        <JobResultSummary result={expandedJobDetail.result_json} />
                      </td>
                    </tr>
                  )}
                  {expandedJobId === j.id && j.status === "error" && (
                    <tr>
                      <td colSpan={7} style={{ padding: "12px 16px", background: "rgba(239,68,68,0.05)" }}>
                        <p style={{ color: "#fca5a5", fontSize: 13, margin: 0 }}>Error: {j.error_message}</p>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// --- Job Result Summary (inline) ---
function JobResultSummary({ result }) {
  if (!result) return null;
  return (
    <div style={{
      padding: "16px 24px", background: "rgba(13,148,136,0.04)",
      borderTop: "1px solid rgba(13,148,136,0.1)",
    }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 16, marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Payer</div>
          <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}>{result.payer_name || "—"}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Claims</div>
          <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}>{result.claim_count ?? "—"}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Lines</div>
          <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}>{result.line_count ?? "—"}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Billed</div>
          <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}>
            {result.total_billed != null ? `$${Number(result.total_billed).toLocaleString()}` : "—"}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Total Paid</div>
          <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}>
            {result.total_paid != null ? `$${Number(result.total_paid).toLocaleString()}` : "—"}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Denial Rate</div>
          <div style={{ fontSize: 14, color: result.denial_rate > 10 ? "#fca5a5" : "#5eead4", fontWeight: 500 }}>
            {result.denial_rate != null ? `${result.denial_rate}%` : "—"}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Denied Lines</div>
          <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}>{result.denied_lines ?? "—"}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Production Date</div>
          <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}>{result.production_date || "—"}</div>
        </div>
      </div>
    </div>
  );
}


// --- Settings Panel ---
function SettingsPanel({
  billingCompany, subscription, user, token,
  settingsCompanyName, setSettingsCompanyName,
  settingsContactEmail, setSettingsContactEmail,
  settingsUserName, setSettingsUserName,
  settingsSaving, setSettingsSaving,
  settingsMsg, setSettingsMsg,
  fetchMe,
}) {
  const sectionStyle = {
    background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 12, padding: 24, marginBottom: 24,
  };
  const inputStyle = {
    width: "100%", padding: "10px 14px", background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "white",
    fontSize: 14, marginBottom: 12, boxSizing: "border-box",
  };
  const labelStyle = {
    fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4,
  };

  const handleSave = async () => {
    setSettingsSaving(true);
    setSettingsMsg("");
    try {
      const res = await fetch(`${API}/api/billing/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          company_name: settingsCompanyName.trim() || undefined,
          contact_email: settingsContactEmail.trim() || undefined,
          user_full_name: settingsUserName.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        setSettingsMsg(d.detail || "Failed to save.");
        return;
      }
      setSettingsMsg("Saved!");
      fetchMe();
      setTimeout(() => setSettingsMsg(""), 3000);
    } catch {
      setSettingsMsg("Failed to save.");
    } finally {
      setSettingsSaving(false);
    }
  };

  const trialEnd = subscription?.trial_ends_at
    ? new Date(subscription.trial_ends_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })
    : null;
  const trialDays = subscription?.trial_ends_at
    ? Math.max(0, Math.ceil((new Date(subscription.trial_ends_at) - new Date()) / (1000 * 60 * 60 * 24)))
    : null;

  return (
    <div style={{ maxWidth: 640 }}>
      <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 8px" }}>Settings</h2>
      <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 14, marginBottom: 32 }}>{user?.email}</p>

      {/* Section 1: Company Profile */}
      <div style={sectionStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
          Company Profile
        </h3>
        <label style={labelStyle}>Company Name</label>
        <input value={settingsCompanyName} onChange={(e) => setSettingsCompanyName(e.target.value)}
          style={inputStyle} />
        <label style={labelStyle}>Contact Email</label>
        <input value={settingsContactEmail} onChange={(e) => setSettingsContactEmail(e.target.value)}
          type="email" style={inputStyle} />
      </div>

      {/* Section 2: My Account */}
      <div style={sectionStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
          My Account
        </h3>
        <label style={labelStyle}>Full Name</label>
        <input value={settingsUserName} onChange={(e) => setSettingsUserName(e.target.value)}
          style={inputStyle} />
        <label style={labelStyle}>Email</label>
        <input value={user?.email || ""} disabled
          style={{ ...inputStyle, opacity: 0.5, cursor: "not-allowed" }} />
      </div>

      {/* Save button */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <button onClick={handleSave} disabled={settingsSaving}
          style={{
            background: settingsSaving ? "#334155" : "#0d9488", color: "white", border: "none",
            borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600,
            cursor: settingsSaving ? "not-allowed" : "pointer", opacity: settingsSaving ? 0.7 : 1,
          }}>
          {settingsSaving ? "Saving..." : "Save Changes"}
        </button>
        {settingsMsg && (
          <span style={{ fontSize: 13, color: settingsMsg === "Saved!" ? "#10B981" : "#f87171" }}>
            {settingsMsg}
          </span>
        )}
      </div>

      {/* Section 3: Subscription (read-only) */}
      <div style={sectionStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
          Subscription
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <label style={labelStyle}>Plan</label>
            <div style={{ fontSize: 14, color: "#f1f5f9", textTransform: "capitalize" }}>
              {subscription?.tier || "—"}
              {subscription?.tier === "trial" && (
                <span style={{
                  display: "inline-block", marginLeft: 8, padding: "2px 8px", borderRadius: 10,
                  background: "rgba(13,148,136,0.15)", color: "#5eead4", fontSize: 11, fontWeight: 600,
                }}>
                  {trialDays} days left
                </span>
              )}
            </div>
          </div>
          <div>
            <label style={labelStyle}>Status</label>
            <div style={{ fontSize: 14, color: subscription?.status === "active" ? "#5eead4" : "#f87171" }}>
              {subscription?.status || "—"}
            </div>
          </div>
          <div>
            <label style={labelStyle}>Trial Ends</label>
            <div style={{ fontSize: 14, color: "#94a3b8" }}>
              {trialEnd || "—"}
            </div>
          </div>
          <div>
            <label style={labelStyle}>Practice Limit</label>
            <div style={{ fontSize: 14, color: "#f1f5f9" }}>
              {subscription?.practice_count_limit ?? "—"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


// --- Shared styles ---
const styles = {
  page: {
    margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif",
    color: "#e2e8f0", overflowX: "hidden", minHeight: "100vh", background: "#0a1628",
  },
  header: {
    position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
    padding: "0 40px", height: 64, display: "flex", alignItems: "center",
    background: "rgba(10,22,40,0.92)", backdropFilter: "blur(16px)",
    borderBottom: "1px solid rgba(255,255,255,0.06)",
  },
  logoLink: { display: "flex", alignItems: "center", gap: 12, textDecoration: "none", color: "inherit" },
  logoIcon: {
    width: 32, height: 32, borderRadius: 8,
    background: "linear-gradient(135deg, #0d9488, #14b8a6)",
    display: "flex", alignItems: "center", justifyContent: "center",
    fontSize: 16, fontWeight: 700, color: "#0a1628",
  },
  logoText: { fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" },
  label: { display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 },
  input: {
    width: "100%", padding: "10px 12px", borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.12)", fontSize: 15,
    outline: "none", boxSizing: "border-box",
    background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
  },
  btn: {
    width: "100%", padding: "12px", borderRadius: 8, border: "none",
    cursor: "pointer", color: "#fff", fontWeight: 700, fontSize: 15,
  },
  linkBtn: { fontSize: 12, color: "#94a3b8", background: "none", border: "none", cursor: "pointer", marginTop: 12 },
  otpBox: {
    padding: 24, borderRadius: 12, border: "1px solid #0d9488",
    background: "rgba(13,148,136,0.08)", textAlign: "center",
  },
  otpInput: {
    width: "100%", padding: "12px 16px", fontSize: 24, letterSpacing: 8,
    textAlign: "center", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8,
    outline: "none", boxSizing: "border-box", marginBottom: 12,
    background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
  },
  errorBox: {
    padding: 12, borderRadius: 8, background: "rgba(239,68,68,0.1)",
    border: "1px solid rgba(239,68,68,0.3)", marginTop: 16,
  },
  th: { padding: "12px 16px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" },
  td: { padding: "12px 16px", fontSize: 14, color: "#e2e8f0" },
};
