import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { API_BASE as API } from "./lib/apiBase";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import "./components/CivicScaleHomepage.css";

const TABS = [
  { id: "portfolio", label: "Portfolio Dashboard" },
  { id: "practices", label: "Practices" },
  { id: "contracts", label: "Contracts" },
  { id: "escalations", label: "Escalations" },
  { id: "ingestion", label: "835 Ingestion" },
  { id: "team", label: "Team" },
  { id: "settings", label: "Settings" },
];

export default function BillingApp() {
  const navigate = useNavigate();
  const { token, user, company, login, logout: authLogout, isAuthenticated, loading } = useAuth();

  // --- All hooks declared at top, before any conditional returns ---
  const [activeTab, setActiveTab] = useState("portfolio");
  const [billingCompany, setBillingCompany] = useState(null);
  const [billingRole, setBillingRole] = useState("admin");
  const [subStatus, setSubStatus] = useState(null); // from /subscription/status
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [upgradeContext, setUpgradeContext] = useState(null); // 'subscription_required' or 'limit_reached'
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

  // Provider status + portal settings
  const [providerStatuses, setProviderStatuses] = useState({});
  const [portalSettings, setPortalSettings] = useState([]);

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
        setBillingRole(data.role || "admin");
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

  // Fetch subscription status
  useEffect(() => {
    if (!token || !billingCompany) return;
    fetch(`${API}/api/billing/subscription/status`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setSubStatus(d); })
      .catch(() => {});
  }, [token, billingCompany]);

  // Fetch provider statuses + portal settings
  useEffect(() => {
    if (!token || !billingCompany) return;
    const h = { Authorization: `Bearer ${token}` };
    fetch(`${API}/api/billing/practices/provider-status`, { headers: h })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) {
          const map = {};
          (d.statuses || []).forEach(s => { map[s.practice_id] = s.has_provider_subscription; });
          setProviderStatuses(map);
        }
      }).catch(() => {});
    fetch(`${API}/api/billing/portal-settings`, { headers: h })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setPortalSettings(d.portal_settings || []); })
      .catch(() => {});
  }, [token, billingCompany]);

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
      if (res.status === 402) {
        // Subscription required or limit reached
        setUpgradeContext(data.error);
        setShowUpgradeModal(true);
        return;
      }
      if (!res.ok) { setPracticeError(data.detail || data.message || "Failed to add practice."); return; }
      setNewPracticeName(""); setNewPracticeEmail(""); setShowAddForm(false);
      fetchPractices();
    } catch { setPracticeError("Failed to add practice."); }
    finally { setAddingPractice(false); }
  };

  const handleCheckout = async (tier) => {
    try {
      const res = await fetch(`${API}/api/billing/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ tier }),
      });
      const data = await res.json();
      if (res.ok && data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch { /* ignore */ }
  };

  const handlePortal = async () => {
    try {
      const res = await fetch(`${API}/api/billing/subscription/portal`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok && data.portal_url) {
        window.location.href = data.portal_url;
      }
    } catch { /* ignore */ }
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

      {/* Subscription banners */}
      {subStatus?.status === "past_due" && (
        <div style={{
          background: "rgba(245,158,11,0.1)", borderBottom: "1px solid rgba(245,158,11,0.3)",
          padding: "10px 40px", textAlign: "center", fontSize: 14, color: "#fbbf24", marginTop: 64,
          display: "flex", justifyContent: "center", alignItems: "center", gap: 12,
        }}>
          Your last payment failed. Update your payment method to maintain full access.
          <button onClick={handlePortal} style={{ fontSize: 13, padding: "4px 12px", borderRadius: 6, border: "1px solid #fbbf24", background: "none", color: "#fbbf24", cursor: "pointer" }}>Update Payment</button>
        </div>
      )}
      {subStatus?.status === "cancelled" && (
        <div style={{
          background: "rgba(245,158,11,0.1)", borderBottom: "1px solid rgba(245,158,11,0.3)",
          padding: "10px 40px", textAlign: "center", fontSize: 14, color: "#fbbf24", marginTop: 64,
          display: "flex", justifyContent: "center", alignItems: "center", gap: 12,
        }}>
          Your subscription has been cancelled. You can still access your first practice.
          <button onClick={() => setShowUpgradeModal(true)} style={{ fontSize: 13, padding: "4px 12px", borderRadius: 6, border: "1px solid #fbbf24", background: "none", color: "#fbbf24", cursor: "pointer" }}>Resubscribe</button>
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
      <main style={{ padding: "32px 40px", maxWidth: activeTab === "portfolio" ? 1200 : 1000, margin: "0 auto" }}>
        {activeTab === "portfolio" && (
          <PortfolioPanel token={token} billingCompany={billingCompany} allPractices={practices} />
        )}

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
                        <td style={styles.td}>
                          {p.practice_name}
                          {providerStatuses[p.practice_id] && (
                            <span title="This practice has an active Parity Provider subscription and manages their own denial appeals" style={{
                              display: "inline-block", marginLeft: 8, padding: "1px 6px", borderRadius: 4,
                              background: "rgba(13,148,136,0.15)", color: "#5eead4",
                              fontSize: 10, fontWeight: 600, cursor: "help",
                            }}>
                              Parity Provider
                            </span>
                          )}
                        </td>
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

        {activeTab === "contracts" && (
          <ContractsPanel token={token} practices={practices} billingRole={billingRole} />
        )}

        {activeTab === "escalations" && (
          <EscalationsPanel token={token} billingRole={billingRole} />
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
            portalSettings={portalSettings}
            setPortalSettings={setPortalSettings}
            providerStatuses={providerStatuses}
          />
        )}

        {activeTab === "team" && (
          <TeamPanel token={token} billingRole={billingRole} allPractices={practices} />
        )}
      </main>

      {/* Upgrade modal */}
      {showUpgradeModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 200,
          background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center",
        }} onClick={() => setShowUpgradeModal(false)}>
          <div style={{
            background: "#1e293b", borderRadius: 16, padding: 32, width: 560, maxWidth: "90vw",
            border: "1px solid rgba(255,255,255,0.1)",
          }} onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontSize: 20, fontWeight: 700, color: "#f1f5f9", margin: "0 0 8px", textAlign: "center" }}>
              {upgradeContext === "limit_reached" ? "Upgrade Your Plan" : "Unlock Multi-Practice Management"}
            </h2>
            <p style={{ color: "#94a3b8", fontSize: 14, textAlign: "center", marginBottom: 24 }}>
              {upgradeContext === "limit_reached"
                ? "You've reached your practice limit. Choose a plan with more capacity."
                : "Your first practice is free. Subscribe to manage multiple practices with full portfolio intelligence."}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              {/* Starter */}
              <div style={{
                border: "1px solid rgba(13,148,136,0.3)", borderRadius: 12, padding: 20,
                background: "rgba(13,148,136,0.05)",
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#5eead4", textTransform: "uppercase", marginBottom: 4 }}>Starter</div>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", marginBottom: 4 }}>$299<span style={{ fontSize: 14, fontWeight: 400, color: "#94a3b8" }}>/mo</span></div>
                <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: 16 }}>Up to 10 practices</p>
                <button onClick={() => handleCheckout("starter")} style={{
                  width: "100%", padding: "10px", borderRadius: 8, border: "none", cursor: "pointer",
                  background: "linear-gradient(135deg, #0d9488, #14b8a6)", color: "#fff", fontWeight: 600, fontSize: 14,
                }}>Subscribe</button>
              </div>
              {/* Growth */}
              <div style={{
                border: "1px solid rgba(59,130,246,0.3)", borderRadius: 12, padding: 20,
                background: "rgba(59,130,246,0.05)",
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#60a5fa", textTransform: "uppercase", marginBottom: 4 }}>Growth</div>
                <div style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", marginBottom: 4 }}>$699<span style={{ fontSize: 14, fontWeight: 400, color: "#94a3b8" }}>/mo</span></div>
                <p style={{ fontSize: 13, color: "#94a3b8", marginBottom: 16 }}>Up to 30 practices</p>
                <button onClick={() => handleCheckout("growth")} style={{
                  width: "100%", padding: "10px", borderRadius: 8, border: "none", cursor: "pointer",
                  background: "linear-gradient(135deg, #3b82f6, #60a5fa)", color: "#fff", fontWeight: 600, fontSize: 14,
                }}>Subscribe</button>
              </div>
            </div>
            <button onClick={() => setShowUpgradeModal(false)} style={{
              display: "block", margin: "16px auto 0", fontSize: 13, color: "#94a3b8",
              background: "none", border: "none", cursor: "pointer",
            }}>Maybe later</button>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Portfolio Panel ---
function PortfolioPanel({ token, billingCompany, allPractices }) {
  const [days, setDays] = useState(90);
  const [summary, setSummary] = useState(null);
  const [practices, setPractices] = useState([]);
  const [payers, setPayers] = useState([]);
  const [denialReasons, setDenialReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [practiceSortField, setPracticeSortField] = useState("total_billed");
  const [practiceSortDir, setPracticeSortDir] = useState("desc");

  // Payer benchmark state
  const [benchmarkPayers, setBenchmarkPayers] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [specialties, setSpecialties] = useState([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState("");
  const [benchmarkSortField, setBenchmarkSortField] = useState("adherence_rate");
  const [benchmarkSortDir, setBenchmarkSortDir] = useState("asc");
  const [anomalyDismissed, setAnomalyDismissed] = useState(false);

  // Comparison state
  const [compareA, setCompareA] = useState("");
  const [compareB, setCompareB] = useState("");
  const [comparison, setComparison] = useState(null);
  const [compLoading, setCompLoading] = useState(false);

  // Report generation state
  const [reportPracticeId, setReportPracticeId] = useState(null);
  const [reportType, setReportType] = useState("denial_summary");
  const [reportDays, setReportDays] = useState(90);
  const [generating, setGenerating] = useState(false);

  const fetchComparison = useCallback(async () => {
    if (!token || !compareA || !compareB || compareA === compareB) { setComparison(null); return; }
    setCompLoading(true);
    try {
      const res = await fetch(
        `${API}/api/billing/portfolio/comparison?practice_a_id=${compareA}&practice_b_id=${compareB}&days=${days}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) setComparison(await res.json());
    } catch { /* ignore */ }
    finally { setCompLoading(false); }
  }, [token, compareA, compareB, days]);

  useEffect(() => { fetchComparison(); }, [fetchComparison]);

  const handleGenerateReport = async () => {
    if (!reportPracticeId) return;
    setGenerating(true);
    try {
      const res = await fetch(`${API}/api/billing/portfolio/reports/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          practice_id: reportPracticeId,
          report_type: reportType,
          date_range_days: reportDays,
        }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = res.headers.get("content-disposition")?.split("filename=")[1]?.replace(/"/g, "") || "report.pdf";
        a.click();
        URL.revokeObjectURL(url);
        setReportPracticeId(null);
      }
    } catch { /* ignore */ }
    finally { setGenerating(false); }
  };

  const fetchAll = useCallback(async () => {
    if (!token || !billingCompany) return;
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const specParam = selectedSpecialty ? `&specialty=${encodeURIComponent(selectedSpecialty)}` : "";
      const [sumRes, pracRes, payRes, denRes, benchRes, anomRes, specRes] = await Promise.all([
        fetch(`${API}/api/billing/portfolio/summary?days=${days}`, { headers }),
        fetch(`${API}/api/billing/portfolio/practices?days=${days}`, { headers }),
        fetch(`${API}/api/billing/portfolio/payers?days=${days}`, { headers }),
        fetch(`${API}/api/billing/portfolio/denial-reasons?days=${days}`, { headers }),
        fetch(`${API}/api/billing/portfolio/payer-benchmark?days=${days}${specParam}`, { headers }),
        fetch(`${API}/api/billing/portfolio/payer-anomalies`, { headers }),
        fetch(`${API}/api/billing/portfolio/specialties`, { headers }),
      ]);
      if (sumRes.ok) setSummary(await sumRes.json());
      if (pracRes.ok) { const d = await pracRes.json(); setPractices(d.practices || []); }
      if (payRes.ok) { const d = await payRes.json(); setPayers(d.payers || []); }
      if (denRes.ok) { const d = await denRes.json(); setDenialReasons(d.denial_reasons || []); }
      if (benchRes.ok) { const d = await benchRes.json(); setBenchmarkPayers(d.payers || []); }
      if (anomRes.ok) { const d = await anomRes.json(); setAnomalies(d.anomalies || []); }
      if (specRes.ok) { const d = await specRes.json(); setSpecialties(d.specialties || []); }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [token, billingCompany, days, selectedSpecialty]);

  useEffect(() => { fetchAll(); }, [fetchAll]);
  useEffect(() => { setAnomalyDismissed(false); }, [days, selectedSpecialty]);

  const sortedPractices = [...practices].sort((a, b) => {
    const av = a[practiceSortField] ?? 0;
    const bv = b[practiceSortField] ?? 0;
    return practiceSortDir === "desc" ? bv - av : av - bv;
  });

  const handlePracticeSort = (field) => {
    if (practiceSortField === field) {
      setPracticeSortDir(d => d === "desc" ? "asc" : "desc");
    } else {
      setPracticeSortField(field);
      setPracticeSortDir("desc");
    }
  };

  const sortArrow = (field) => {
    if (practiceSortField !== field) return "";
    return practiceSortDir === "desc" ? " \u2193" : " \u2191";
  };

  if (loading) {
    return (
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Portfolio Dashboard</h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
          {[1,2,3,4].map(i => (
            <div key={i} style={{
              background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 12, padding: 24, height: 90,
            }}>
              <div style={{ width: 80, height: 14, background: "rgba(255,255,255,0.06)", borderRadius: 4, marginBottom: 12 }} />
              <div style={{ width: 120, height: 24, background: "rgba(255,255,255,0.06)", borderRadius: 4 }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!summary || summary.analysis_count === 0) {
    return (
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 24px" }}>Portfolio Dashboard</h2>
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 15, margin: 0 }}>
            No analysis data yet. Upload 835 files in the Ingestion tab to populate your portfolio.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header + date filter */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Portfolio Dashboard</h2>
        <div style={{ display: "flex", gap: 4 }}>
          {[30, 90, 180].map(d => (
            <button key={d} onClick={() => setDays(d)} style={{
              padding: "6px 14px", borderRadius: 6, border: "1px solid",
              borderColor: days === d ? "#0d9488" : "rgba(255,255,255,0.1)",
              background: days === d ? "rgba(13,148,136,0.15)" : "transparent",
              color: days === d ? "#5eead4" : "#94a3b8",
              fontSize: 13, fontWeight: 500, cursor: "pointer",
            }}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
        <KpiTile label="Total Billed" value={`$${Number(summary.total_billed).toLocaleString()}`} />
        <KpiTile label="Overall Denial Rate"
          value={`${summary.overall_denial_rate}%`}
          valueColor={summary.overall_denial_rate > 10 ? "#fca5a5" : "#5eead4"} />
        <KpiTile label="Active Practices" value={summary.practice_count} />
        <KpiTile label="Payers Tracked" value={summary.payer_count} />
      </div>

      {/* Practice breakdown */}
      <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" }}>Practice Breakdown</h3>
      <div style={{
        background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 12, overflow: "hidden", marginBottom: 32,
      }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              <th style={styles.th}>Practice</th>
              <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handlePracticeSort("total_billed")}>
                Total Billed{sortArrow("total_billed")}
              </th>
              <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handlePracticeSort("denial_rate")}>
                Denial Rate{sortArrow("denial_rate")}
              </th>
              <th style={styles.th}>Lines</th>
              <th style={styles.th}>Analyses</th>
              <th style={styles.th}>Last Upload</th>
              <th style={styles.th}>Report</th>
            </tr>
          </thead>
          <tbody>
            {sortedPractices.map(p => (
              <tr key={p.practice_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <td style={styles.td}>{p.practice_name}</td>
                <td style={{ ...styles.td, color: "#94a3b8" }}>${Number(p.total_billed).toLocaleString()}</td>
                <td style={{ ...styles.td, color: p.denial_rate > 10 ? "#fca5a5" : "#5eead4" }}>
                  {p.denial_rate}%
                </td>
                <td style={{ ...styles.td, color: "#94a3b8" }}>{p.line_count.toLocaleString()}</td>
                <td style={{ ...styles.td, color: "#94a3b8" }}>{p.analysis_count}</td>
                <td style={{ ...styles.td, color: "#64748b", fontSize: 13 }}>
                  {p.last_upload ? new Date(p.last_upload).toLocaleDateString() : "—"}
                </td>
                <td style={styles.td}>
                  <button onClick={() => setReportPracticeId(p.practice_id)}
                    style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer" }}>
                    Generate
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Report generation modal */}
      {reportPracticeId && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 200,
          background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center",
        }} onClick={() => !generating && setReportPracticeId(null)}>
          <div style={{
            background: "#1e293b", borderRadius: 12, padding: 24, width: 380,
            border: "1px solid rgba(255,255,255,0.1)",
          }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Generate Report</h3>
            <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>Report Type</label>
            <select value={reportType} onChange={(e) => setReportType(e.target.value)} style={{
              width: "100%", padding: "8px 12px", borderRadius: 8, fontSize: 14, marginBottom: 12,
              border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)",
              color: "#f1f5f9", appearance: "auto", boxSizing: "border-box",
            }}>
              <option value="denial_summary">Denial Summary</option>
              <option value="payer_performance">Payer Performance</option>
              <option value="appeal_roi">Appeal & Recovery</option>
            </select>
            <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>Date Range</label>
            <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
              {[30, 90, 180, 365].map(d => (
                <button key={d} onClick={() => setReportDays(d)} style={{
                  padding: "5px 12px", borderRadius: 6, border: "1px solid",
                  borderColor: reportDays === d ? "#0d9488" : "rgba(255,255,255,0.1)",
                  background: reportDays === d ? "rgba(13,148,136,0.15)" : "transparent",
                  color: reportDays === d ? "#5eead4" : "#94a3b8", fontSize: 13, cursor: "pointer",
                }}>
                  {d}d
                </button>
              ))}
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <button onClick={handleGenerateReport} disabled={generating} style={{
                flex: 1, padding: "10px", borderRadius: 8, border: "none", cursor: "pointer",
                background: generating ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                color: "#fff", fontWeight: 600, fontSize: 14,
              }}>
                {generating ? "Generating..." : "Download PDF"}
              </button>
              <button onClick={() => setReportPracticeId(null)} disabled={generating} style={{
                padding: "10px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)",
                background: "none", color: "#94a3b8", cursor: "pointer", fontSize: 14,
              }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Payer Performance + Denial Reasons side by side */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        {/* Payer Performance */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" }}>Payer Performance</h3>
          <div style={{
            background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 12, overflow: "hidden",
          }}>
            {payers.length === 0 ? (
              <p style={{ color: "#94a3b8", fontSize: 14, padding: 24, margin: 0, textAlign: "center" }}>No payer data</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    <th style={styles.th}>Payer</th>
                    <th style={styles.th}>Billed</th>
                    <th style={styles.th}>Denial %</th>
                    <th style={styles.th}>Practices</th>
                  </tr>
                </thead>
                <tbody>
                  {payers.map(p => (
                    <tr key={p.payer_name} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={{ ...styles.td, fontSize: 13 }}>{p.payer_name}</td>
                      <td style={{ ...styles.td, color: "#94a3b8", fontSize: 13 }}>
                        ${Number(p.total_billed).toLocaleString()}
                      </td>
                      <td style={{ ...styles.td, color: p.denial_rate > 10 ? "#fca5a5" : "#5eead4", fontSize: 13 }}>
                        {p.denial_rate}%
                      </td>
                      <td style={{ ...styles.td, color: "#94a3b8", fontSize: 13 }}>{p.practice_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Top Denial Reasons */}
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" }}>Top Denial Reasons</h3>
          <div style={{
            background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 12, overflow: "hidden",
          }}>
            {denialReasons.length === 0 ? (
              <p style={{ color: "#94a3b8", fontSize: 14, padding: 24, margin: 0, textAlign: "center" }}>No denial data</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    <th style={styles.th}>Code</th>
                    <th style={styles.th}>Description</th>
                    <th style={styles.th}>Count</th>
                    <th style={styles.th}>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {denialReasons.map(d => (
                    <tr key={d.denial_code} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={styles.td}>
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: 6,
                          background: "rgba(239,68,68,0.1)", color: "#fca5a5",
                          fontSize: 12, fontWeight: 600, fontFamily: "monospace",
                        }}>
                          {d.denial_code}
                        </span>
                      </td>
                      <td style={{ ...styles.td, fontSize: 12, color: "#94a3b8", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {d.denial_description || "—"}
                      </td>
                      <td style={{ ...styles.td, color: "#f1f5f9" }}>{d.count}</td>
                      <td style={{ ...styles.td, color: "#94a3b8", fontSize: 13 }}>
                        ${Number(d.total_amount).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Payer Benchmarking section */}
      <PayerBenchmarkSection
        token={token}
        benchmarkPayers={benchmarkPayers}
        anomalies={anomalies}
        specialties={specialties}
        selectedSpecialty={selectedSpecialty}
        setSelectedSpecialty={setSelectedSpecialty}
        benchmarkSortField={benchmarkSortField}
        setBenchmarkSortField={setBenchmarkSortField}
        benchmarkSortDir={benchmarkSortDir}
        setBenchmarkSortDir={setBenchmarkSortDir}
        anomalyDismissed={anomalyDismissed}
        setAnomalyDismissed={setAnomalyDismissed}
        days={days}
      />

      {/* Practice Comparison */}
      <PracticeComparisonSection
        allPractices={(allPractices || []).filter(p => p.active)}
        compareA={compareA} setCompareA={setCompareA}
        compareB={compareB} setCompareB={setCompareB}
        comparison={comparison} compLoading={compLoading}
        days={days}
      />

      {/* Appeal ROI */}
      <AppealROISection token={token} billingCompany={billingCompany} />
    </div>
  );
}

function AppealROISection({ token, billingCompany }) {
  const [roiDays, setRoiDays] = useState(180);
  const [summary, setSummary] = useState(null);
  const [byPayer, setByPayer] = useState([]);
  const [byDenial, setByDenial] = useState([]);
  const [trend, setTrend] = useState([]);
  const [loading, setLoading] = useState(true);
  const [payerSortField, setPayerSortField] = useState("recovery_rate");
  const [payerSortDir, setPayerSortDir] = useState("asc");
  const [denialSortField, setDenialSortField] = useState("count");
  const [denialSortDir, setDenialSortDir] = useState("desc");

  const fetchROI = useCallback(async () => {
    if (!token || !billingCompany) return;
    setLoading(true);
    try {
      const h = { Authorization: `Bearer ${token}` };
      const [sRes, pRes, dRes, tRes] = await Promise.all([
        fetch(`${API}/api/billing/portfolio/appeal-roi?days=${roiDays}`, { headers: h }),
        fetch(`${API}/api/billing/portfolio/appeal-roi/by-payer?days=${roiDays}`, { headers: h }),
        fetch(`${API}/api/billing/portfolio/appeal-roi/by-denial-type?days=${roiDays}`, { headers: h }),
        fetch(`${API}/api/billing/portfolio/appeal-roi/trend?days=${roiDays}`, { headers: h }),
      ]);
      if (sRes.ok) setSummary(await sRes.json());
      if (pRes.ok) { const d = await pRes.json(); setByPayer(d.payers || []); }
      if (dRes.ok) { const d = await dRes.json(); setByDenial(d.denial_types || []); }
      if (tRes.ok) { const d = await tRes.json(); setTrend(d.trend || []); }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [token, billingCompany, roiDays]);

  useEffect(() => { fetchROI(); }, [fetchROI]);

  const sortedPayers = [...byPayer].sort((a, b) => {
    const av = a[payerSortField] ?? 0; const bv = b[payerSortField] ?? 0;
    return payerSortDir === "asc" ? av - bv : bv - av;
  });
  const sortedDenials = [...byDenial].sort((a, b) => {
    const av = a[denialSortField] ?? 0; const bv = b[denialSortField] ?? 0;
    return denialSortDir === "asc" ? av - bv : bv - av;
  });

  const handlePayerSort = (f) => {
    if (payerSortField === f) setPayerSortDir(d => d === "asc" ? "desc" : "asc");
    else { setPayerSortField(f); setPayerSortDir(f === "recovery_rate" ? "asc" : "desc"); }
  };
  const handleDenialSort = (f) => {
    if (denialSortField === f) setDenialSortDir(d => d === "asc" ? "desc" : "asc");
    else { setDenialSortField(f); setDenialSortDir("desc"); }
  };
  const arrow = (field, active, dir) => active !== field ? "" : dir === "desc" ? " \u2193" : " \u2191";

  if (loading) {
    return (
      <div style={{ marginTop: 32 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" }}>Appeal ROI</h3>
        <p style={{ color: "#94a3b8", fontSize: 14 }}>Loading...</p>
      </div>
    );
  }

  if (!summary || summary.total_billed === 0) {
    return (
      <div style={{ marginTop: 32 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" }}>Appeal ROI</h3>
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 14, margin: 0 }}>No appeal data available yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 32 }}>
      {/* Header + date selector */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Appeal ROI</h3>
        <div style={{ display: "flex", gap: 4 }}>
          {[90, 180, 365].map(d => (
            <button key={d} onClick={() => setRoiDays(d)} style={{
              padding: "6px 14px", borderRadius: 6, border: "1px solid",
              borderColor: roiDays === d ? "#0d9488" : "rgba(255,255,255,0.1)",
              background: roiDays === d ? "rgba(13,148,136,0.15)" : "transparent",
              color: roiDays === d ? "#5eead4" : "#94a3b8", fontSize: 13, fontWeight: 500, cursor: "pointer",
            }}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* KPI tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        <KpiTile label="Total Recovered" value={`$${Number(summary.total_recovered).toLocaleString()}`} />
        <KpiTile label="Recovery Rate" value={`${summary.recovery_rate}%`}
          valueColor={summary.recovery_rate >= 90 ? "#5eead4" : summary.recovery_rate >= 75 ? "#fbbf24" : "#fca5a5"} />
        <KpiTile label="Avg Days to Payment" value={summary.avg_days_to_payment ?? "—"}
          valueColor={summary.avg_days_to_payment && summary.avg_days_to_payment > 30 ? "#fca5a5" : "#5eead4"} />
        <KpiTile label="Top Payer (Recovery)" value={summary.top_payer || "—"} />
      </div>

      {/* Trend chart */}
      {trend.length > 0 && <AppealTrendChart data={trend} />}

      {/* By Payer + By Denial side by side */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 24 }}>
        {/* By Payer */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            By Payer
          </div>
          <div style={{
            background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 12, overflow: "hidden",
          }}>
            {sortedPayers.length === 0 ? (
              <p style={{ color: "#94a3b8", fontSize: 13, padding: 24, margin: 0, textAlign: "center" }}>No payer data</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    <th style={styles.th}>Payer</th>
                    <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handlePayerSort("total_billed")}>
                      Billed{arrow("total_billed", payerSortField, payerSortDir)}
                    </th>
                    <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handlePayerSort("total_denied")}>
                      Denied{arrow("total_denied", payerSortField, payerSortDir)}
                    </th>
                    <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handlePayerSort("recovery_rate")}>
                      Recovery{arrow("recovery_rate", payerSortField, payerSortDir)}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedPayers.map(p => (
                    <tr key={p.payer_name} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={{ ...styles.td, fontSize: 13 }}>{p.payer_name}</td>
                      <td style={{ ...styles.td, color: "#94a3b8", fontSize: 13 }}>
                        ${Number(p.total_billed).toLocaleString()}
                      </td>
                      <td style={{ ...styles.td, color: "#fca5a5", fontSize: 13 }}>
                        ${Number(p.total_denied).toLocaleString()}
                      </td>
                      <td style={{
                        ...styles.td, fontSize: 13, fontWeight: 600,
                        color: p.recovery_rate >= 90 ? "#5eead4" : p.recovery_rate >= 75 ? "#fbbf24" : "#fca5a5",
                      }}>
                        {p.recovery_rate}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* By Denial Type */}
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            By Denial Type
          </div>
          <div style={{
            background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 12, overflow: "hidden",
          }}>
            {sortedDenials.length === 0 ? (
              <p style={{ color: "#94a3b8", fontSize: 13, padding: 24, margin: 0, textAlign: "center" }}>No denial data</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    <th style={styles.th}>Code</th>
                    <th style={styles.th}>Description</th>
                    <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handleDenialSort("count")}>
                      Count{arrow("count", denialSortField, denialSortDir)}
                    </th>
                    <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handleDenialSort("total_denied")}>
                      Amount{arrow("total_denied", denialSortField, denialSortDir)}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedDenials.map(d => (
                    <tr key={d.denial_code} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={styles.td}>
                        <span style={{
                          fontFamily: "monospace", fontSize: 12, fontWeight: 600,
                          padding: "2px 6px", borderRadius: 4,
                          background: "rgba(239,68,68,0.1)", color: "#fca5a5",
                        }}>
                          {d.denial_code}
                        </span>
                      </td>
                      <td style={{ ...styles.td, fontSize: 12, color: "#94a3b8", maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {d.description || "—"}
                      </td>
                      <td style={{ ...styles.td, color: "#f1f5f9" }}>{d.count}</td>
                      <td style={{ ...styles.td, color: "#fca5a5", fontSize: 13 }}>
                        ${Number(d.total_denied).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      <p style={{ fontSize: 11, color: "#475569", marginTop: 12, fontStyle: "italic" }}>
        Recovery Rate = denied claims later paid in subsequent remittance files, matched by claim number + CPT + date of service.
      </p>
    </div>
  );
}

function AppealTrendChart({ data }) {
  const chartData = data.map(d => ({
    month: d.month,
    Recovered: d.total_recovered,
    Denied: d.total_denied,
  }));

  return (
    <div style={{
      background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 12, padding: "20px 16px 8px", marginTop: 0,
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em", paddingLeft: 8 }}>
        Monthly Recovery Trend
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 4, right: 12, left: 12, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.06)" }} />
          <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
            tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            contentStyle={{ background: "#1e293b", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: "#94a3b8" }}
            formatter={(value) => [`$${Number(value).toLocaleString()}`, undefined]}
          />
          <Bar dataKey="Recovered" fill="#0d9488" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Denied" fill="#ef4444" opacity={0.4} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}


function PracticeComparisonSection({
  allPractices, compareA, setCompareA, compareB, setCompareB,
  comparison, compLoading, days,
}) {
  if (allPractices.length < 2) {
    return (
      <div style={{ marginTop: 32 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 12px" }}>Practice Comparison</h3>
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 14, margin: 0 }}>Fewer than 2 practices available for comparison.</p>
        </div>
      </div>
    );
  }

  const selectStyle = {
    padding: "8px 12px", borderRadius: 8, fontSize: 14, flex: 1, minWidth: 200,
    border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)",
    color: "#f1f5f9", appearance: "auto", boxSizing: "border-box",
  };

  const metricRows = comparison ? [
    { label: "Denial Rate", key: "denial_rate", fmt: v => `${v}%`, better: "lower" },
    { label: "Total Billed", key: "total_billed", fmt: v => `$${Number(v).toLocaleString()}`, better: "higher" },
    { label: "Total Lines", key: "line_count", fmt: v => v.toLocaleString(), better: "higher" },
    { label: "Top Payer", key: "top_payer", fmt: v => v, better: null },
    { label: "Top Denial Reason", key: "top_denial_reason", fmt: v => v, better: null },
  ] : [];

  const deltaIndicator = (val, avg, better) => {
    if (better === null || avg === 0 || avg === "—" || val === "—") return null;
    const diff = val - avg;
    if (Math.abs(diff) < 0.5) return null;
    const isGood = better === "lower" ? diff < 0 : diff > 0;
    return (
      <span style={{ fontSize: 11, marginLeft: 4, color: isGood ? "#5eead4" : "#fca5a5" }}>
        {isGood ? "\u2191" : "\u2193"}
      </span>
    );
  };

  return (
    <div style={{ marginTop: 32 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Practice Comparison</h3>

      <div style={{ display: "flex", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
        <select value={compareA} onChange={(e) => setCompareA(e.target.value)} style={selectStyle}>
          <option value="">Select Practice A...</option>
          {allPractices.map(p => (
            <option key={p.practice_id} value={p.practice_id}>{p.practice_name}</option>
          ))}
        </select>
        <span style={{ color: "#64748b", alignSelf: "center", fontSize: 14 }}>vs</span>
        <select value={compareB} onChange={(e) => setCompareB(e.target.value)} style={selectStyle}>
          <option value="">Select Practice B...</option>
          {allPractices.map(p => (
            <option key={p.practice_id} value={p.practice_id}>{p.practice_name}</option>
          ))}
        </select>
      </div>

      {!compareA || !compareB || compareA === compareB ? (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 32, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 14, margin: 0 }}>
            {compareA === compareB && compareA ? "Select two different practices." : "Select two practices to compare."}
          </p>
        </div>
      ) : compLoading ? (
        <p style={{ color: "#94a3b8", fontSize: 14 }}>Loading comparison...</p>
      ) : comparison ? (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 12, overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th style={styles.th}>Metric</th>
                <th style={styles.th}>{comparison.practice_a?.practice_name || "Practice A"}</th>
                <th style={styles.th}>{comparison.practice_b?.practice_name || "Practice B"}</th>
                <th style={styles.th}>Portfolio Avg</th>
              </tr>
            </thead>
            <tbody>
              {metricRows.map(m => {
                const va = comparison.practice_a?.[m.key];
                const vb = comparison.practice_b?.[m.key];
                const vavg = comparison.portfolio_avg?.[m.key];
                return (
                  <tr key={m.key} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={{ ...styles.td, fontWeight: 500 }}>{m.label}</td>
                    <td style={styles.td}>
                      {m.fmt(va ?? "—")}
                      {typeof va === "number" && typeof vavg === "number" && deltaIndicator(va, vavg, m.better)}
                    </td>
                    <td style={styles.td}>
                      {m.fmt(vb ?? "—")}
                      {typeof vb === "number" && typeof vavg === "number" && deltaIndicator(vb, vavg, m.better)}
                    </td>
                    <td style={{ ...styles.td, color: "#64748b" }}>{m.fmt(vavg ?? "—")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function PayerBenchmarkSection({
  token, benchmarkPayers, anomalies, specialties,
  selectedSpecialty, setSelectedSpecialty,
  benchmarkSortField, setBenchmarkSortField,
  benchmarkSortDir, setBenchmarkSortDir,
  anomalyDismissed, setAnomalyDismissed,
  days,
}) {
  const [expandedPayer, setExpandedPayer] = useState(null);
  const [payerDetail, setPayerDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const handlePayerClick = async (payerName) => {
    if (expandedPayer === payerName) { setExpandedPayer(null); setPayerDetail(null); return; }
    setExpandedPayer(payerName);
    setPayerDetail(null);
    setDetailLoading(true);
    try {
      const res = await fetch(
        `${API}/api/billing/portfolio/payer-detail?payer_name=${encodeURIComponent(payerName)}&days=${days}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) setPayerDetail(await res.json());
    } catch { /* ignore */ }
    finally { setDetailLoading(false); }
  };

  const anomalyPayers = new Set(anomalies.map(a => a.payer_name));

  const sorted = [...benchmarkPayers].sort((a, b) => {
    const av = a[benchmarkSortField] ?? 0;
    const bv = b[benchmarkSortField] ?? 0;
    return benchmarkSortDir === "asc" ? av - bv : bv - av;
  });

  const handleSort = (field) => {
    if (benchmarkSortField === field) {
      setBenchmarkSortDir(d => d === "asc" ? "desc" : "asc");
    } else {
      setBenchmarkSortField(field);
      setBenchmarkSortDir(field === "adherence_rate" ? "asc" : "desc");
    }
  };

  const arrow = (field) => {
    if (benchmarkSortField !== field) return "";
    return benchmarkSortDir === "desc" ? " \u2193" : " \u2191";
  };

  return (
    <div style={{ marginTop: 32 }}>
      {/* Header + controls */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Payer Benchmarking</h3>
        {specialties.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <label style={{ fontSize: 12, color: "#64748b" }}>Specialty:</label>
            <select value={selectedSpecialty} onChange={(e) => setSelectedSpecialty(e.target.value)}
              style={{
                padding: "5px 10px", borderRadius: 6, fontSize: 13,
                border: "1px solid rgba(255,255,255,0.12)",
                background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
                appearance: "auto",
              }}>
              <option value="">All specialties</option>
              {specialties.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        )}
      </div>

      {/* Anomaly alert */}
      {anomalies.length > 0 && !anomalyDismissed && (
        <div style={{
          background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)",
          borderRadius: 8, padding: "10px 16px", marginBottom: 16,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <span style={{ color: "#fbbf24", fontSize: 13 }}>
            {anomalies.length} payer{anomalies.length > 1 ? "s" : ""} show significant adherence decline in the last 90 days
          </span>
          <button onClick={() => setAnomalyDismissed(true)}
            style={{ color: "#fbbf24", background: "none", border: "none", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>
            &times;
          </button>
        </div>
      )}

      {/* Benchmark table */}
      {benchmarkPayers.length === 0 ? (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 14, margin: 0 }}>
            {selectedSpecialty
              ? `No payer data for specialty "${selectedSpecialty}" in the last ${days} days.`
              : "Insufficient data for payer benchmarking."}
          </p>
        </div>
      ) : (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 12, overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th style={styles.th}>Payer Name</th>
                <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handleSort("adherence_rate")}>
                  Adherence Rate{arrow("adherence_rate")}
                </th>
                <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handleSort("practice_count")}>
                  Practices{arrow("practice_count")}
                </th>
                <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handleSort("claim_count")}>
                  Claims{arrow("claim_count")}
                </th>
                <th style={{ ...styles.th, cursor: "pointer" }} onClick={() => handleSort("total_billed")}>
                  Total Billed{arrow("total_billed")}
                </th>
                <th style={styles.th}>Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(p => {
                const isAnomaly = anomalyPayers.has(p.payer_name);
                const anomalyData = isAnomaly ? anomalies.find(a => a.payer_name === p.payer_name) : null;
                const isExpanded = expandedPayer === p.payer_name;
                return (
                  <React.Fragment key={p.payer_name}>
                  <tr onClick={() => handlePayerClick(p.payer_name)} style={{
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    background: isExpanded ? "rgba(13,148,136,0.05)" : isAnomaly ? "rgba(245,158,11,0.05)" : "transparent",
                    cursor: "pointer",
                  }}>
                    <td style={styles.td}>
                      {p.payer_name}
                      {isAnomaly && (
                        <span style={{
                          display: "inline-block", marginLeft: 8, padding: "1px 6px", borderRadius: 4,
                          background: "rgba(245,158,11,0.15)", color: "#fbbf24",
                          fontSize: 10, fontWeight: 600,
                        }}>
                          DECLINING
                        </span>
                      )}
                    </td>
                    <td style={{
                      ...styles.td, fontWeight: 600,
                      color: p.adherence_rate < 85 ? "#fca5a5" : p.adherence_rate < 95 ? "#fbbf24" : "#5eead4",
                    }}>
                      {p.adherence_rate}%
                      {anomalyData && (
                        <span style={{ fontSize: 11, color: "#f87171", marginLeft: 6 }}>
                          ({anomalyData.delta > 0 ? "+" : ""}{anomalyData.delta}pp)
                        </span>
                      )}
                    </td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>{p.practice_count}</td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>{p.claim_count.toLocaleString()}</td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>
                      ${Number(p.total_billed).toLocaleString()}
                    </td>
                    <td style={styles.td}>
                      {isAnomaly ? (
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: 10,
                          background: "rgba(245,158,11,0.15)", color: "#fbbf24",
                          fontSize: 11, fontWeight: 600, cursor: "pointer",
                        }}>
                          Watch
                        </span>
                      ) : p.adherence_rate >= 95 ? (
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: 10,
                          background: "rgba(13,148,136,0.15)", color: "#5eead4",
                          fontSize: 11, fontWeight: 600, cursor: "pointer",
                        }}>
                          Good
                        </span>
                      ) : (
                        <span style={{
                          display: "inline-block", padding: "2px 8px", borderRadius: 10,
                          background: "rgba(148,163,184,0.15)", color: "#94a3b8",
                          fontSize: 11, fontWeight: 600, cursor: "pointer",
                        }}>
                          Review
                        </span>
                      )}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={6} style={{ padding: 0 }}>
                        <PayerDetailPanel detail={payerDetail} loading={detailLoading} />
                      </td>
                    </tr>
                  )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {selectedSpecialty && (
        <p style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>
          Filtered by specialty: {selectedSpecialty}
        </p>
      )}
    </div>
  );
}

function PayerDetailPanel({ detail, loading }) {
  if (loading) {
    return (
      <div style={{ padding: "16px 24px", background: "rgba(13,148,136,0.03)" }}>
        <p style={{ color: "#94a3b8", fontSize: 13, margin: 0 }}>Loading payer detail...</p>
      </div>
    );
  }
  if (!detail) return null;

  return (
    <div style={{
      padding: "20px 24px", background: "rgba(13,148,136,0.03)",
      borderTop: "1px solid rgba(13,148,136,0.1)",
    }}>
      {/* Summary stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 16, marginBottom: 20 }}>
        {[
          { label: "Total Billed", value: `$${Number(detail.total_billed || 0).toLocaleString()}` },
          { label: "Total Paid", value: `$${Number(detail.total_paid || 0).toLocaleString()}` },
          { label: "Lines", value: (detail.line_count || 0).toLocaleString() },
          { label: "Denied", value: detail.denied_lines || 0 },
          { label: "Denial Rate", value: `${detail.denial_rate || 0}%`,
            color: (detail.denial_rate || 0) > 10 ? "#fca5a5" : "#5eead4" },
          { label: "Practices", value: detail.practice_count || 0 },
        ].map(s => (
          <div key={s.label}>
            <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>{s.label}</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: s.color || "#f1f5f9" }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Per-practice breakdown */}
      {(detail.practices || []).length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Per-Practice Breakdown
          </div>
          <div style={{ display: "grid", gap: 8 }}>
            {detail.practices.map(pr => (
              <div key={pr.practice_id} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "8px 12px", background: "rgba(255,255,255,0.02)",
                borderRadius: 6, border: "1px solid rgba(255,255,255,0.04)",
              }}>
                <span style={{ fontSize: 13, color: "#f1f5f9" }}>{pr.practice_name}</span>
                <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#94a3b8" }}>
                  <span>${Number(pr.total_billed || 0).toLocaleString()} billed</span>
                  <span style={{ color: (pr.denial_rate || 0) > 10 ? "#fca5a5" : "#5eead4" }}>
                    {pr.denial_rate || 0}% denial
                  </span>
                  <span>{(pr.line_count || 0).toLocaleString()} lines</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top denial codes for this payer */}
      {(detail.denial_codes || []).length > 0 && (
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Top Denial Codes
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {detail.denial_codes.map(dc => (
              <div key={dc.code} style={{
                padding: "4px 10px", borderRadius: 6,
                background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)",
                fontSize: 12,
              }}>
                <span style={{ fontFamily: "monospace", color: "#fca5a5", fontWeight: 600 }}>{dc.code}</span>
                {dc.description && (
                  <span style={{ color: "#94a3b8", marginLeft: 6 }}>{dc.description}</span>
                )}
                <span style={{ color: "#64748b", marginLeft: 6 }}>({dc.count}x, ${Number(dc.total_amount).toLocaleString()})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


function KpiTile({ label, value, valueColor }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 12, padding: 24,
    }}>
      <div style={{ fontSize: 12, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontSize: 24, fontWeight: 600, color: valueColor || "#f1f5f9" }}>
        {value}
      </div>
    </div>
  );
}


// --- Escalations Panel ---
function EscalationsPanel({ token, billingRole }) {
  const [patterns, setPatterns] = useState([]);
  const [detecting, setDetecting] = useState(false);
  const [patternDays, setPatternDays] = useState(180);
  const [escalations, setEscalations] = useState([]);
  const [escLoading, setEscLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedEsc, setExpandedEsc] = useState(null);
  const [escDetail, setEscDetail] = useState(null);
  const [creating, setCreating] = useState(null);
  const [createdIds, setCreatedIds] = useState(new Set());
  const [updateStatus, setUpdateStatus] = useState("");
  const [updateNotes, setUpdateNotes] = useState("");
  const [updateAmount, setUpdateAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");

  const fetchEscalations = useCallback(async () => {
    if (!token) return;
    setEscLoading(true);
    try {
      const url = statusFilter
        ? `${API}/api/billing/escalations?status=${statusFilter}`
        : `${API}/api/billing/escalations`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) { const d = await res.json(); setEscalations(d.escalations || []); }
    } catch { /* ignore */ }
    finally { setEscLoading(false); }
  }, [token, statusFilter]);

  useEffect(() => { fetchEscalations(); }, [fetchEscalations]);

  const handleDetect = async () => {
    setDetecting(true);
    try {
      const res = await fetch(`${API}/api/billing/escalations/detect-patterns?days=${patternDays}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) { const d = await res.json(); setPatterns(d.patterns || []); }
    } catch { /* ignore */ }
    finally { setDetecting(false); }
  };

  const handleCreate = async (p) => {
    setCreating(`${p.payer_name}|${p.denial_code}`);
    try {
      const res = await fetch(`${API}/api/billing/escalations`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ payer_name: p.payer_name, denial_code: p.denial_code, denial_description: p.denial_description, days: patternDays }),
      });
      if (res.ok) {
        setCreatedIds(prev => new Set(prev).add(`${p.payer_name}|${p.denial_code}`));
        setToast("Escalation created"); setTimeout(() => setToast(""), 3000);
        fetchEscalations();
      }
    } catch { /* ignore */ }
    finally { setCreating(null); }
  };

  const handleViewDetail = async (esc) => {
    if (expandedEsc === esc.id) { setExpandedEsc(null); setEscDetail(null); return; }
    setExpandedEsc(esc.id); setEscDetail(null);
    setUpdateStatus(esc.status); setUpdateNotes(""); setUpdateAmount("");
    try {
      const res = await fetch(`${API}/api/billing/escalations/${esc.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setEscDetail(await res.json());
    } catch { /* ignore */ }
  };

  const [exporting, setExporting] = useState(null);

  const handleExport = async (escId) => {
    setExporting(escId);
    try {
      const res = await fetch(`${API}/api/billing/escalations/${escId}/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = res.headers.get("content-disposition")?.split("filename=")[1]?.replace(/"/g, "") || "escalation.pdf";
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch { /* ignore */ }
    finally { setExporting(null); }
  };

  const handleStatusUpdate = async () => {
    if (!expandedEsc || !updateStatus) return;
    setSaving(true);
    try {
      const body = { status: updateStatus };
      if (updateNotes) body.resolution_notes = updateNotes;
      if (updateStatus === "resolved" && updateAmount) body.recovered_amount = parseFloat(updateAmount);
      const res = await fetch(`${API}/api/billing/escalations/${expandedEsc}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        setToast("Status updated"); setTimeout(() => setToast(""), 3000);
        setExpandedEsc(null); setEscDetail(null); fetchEscalations();
      } else { const d = await res.json(); setToast(d.detail || "Update failed."); setTimeout(() => setToast(""), 4000); }
    } catch { /* ignore */ }
    finally { setSaving(false); }
  };

  const statusBadge = (s) => {
    const map = {
      open: { bg: "rgba(59,130,246,0.15)", color: "#60a5fa" },
      in_progress: { bg: "rgba(245,158,11,0.15)", color: "#fbbf24" },
      resolved: { bg: "rgba(13,148,136,0.15)", color: "#5eead4" },
      closed: { bg: "rgba(148,163,184,0.15)", color: "#94a3b8" },
    };
    const st = map[s] || map.open;
    return <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: st.bg, color: st.color, textTransform: "capitalize" }}>{s?.replace("_", " ")}</span>;
  };

  return (
    <div>
      {toast && (
        <div style={{ position: "fixed", top: 80, right: 40, zIndex: 300, padding: "10px 20px", borderRadius: 8, background: toast.includes("fail") ? "rgba(239,68,68,0.9)" : "rgba(13,148,136,0.9)", color: "#fff", fontSize: 13, fontWeight: 500 }}>
          {toast}
        </div>
      )}

      {/* Section 1: Pattern Detection */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Systematic Denial Patterns</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <div style={{ display: "flex", gap: 4 }}>
              {[90, 180, 365].map(d => (
                <button key={d} onClick={() => setPatternDays(d)} style={{
                  padding: "5px 12px", borderRadius: 6, border: "1px solid",
                  borderColor: patternDays === d ? "#0d9488" : "rgba(255,255,255,0.1)",
                  background: patternDays === d ? "rgba(13,148,136,0.15)" : "transparent",
                  color: patternDays === d ? "#5eead4" : "#94a3b8", fontSize: 12, cursor: "pointer",
                }}>{d}d</button>
              ))}
            </div>
            <button onClick={handleDetect} disabled={detecting} style={{
              padding: "6px 16px", borderRadius: 6, border: "none", cursor: "pointer",
              background: detecting ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
              color: "#fff", fontWeight: 600, fontSize: 13,
            }}>
              {detecting ? "Detecting..." : "Detect Patterns"}
            </button>
          </div>
        </div>

        {patterns.length === 0 ? (
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)", borderRadius: 12, padding: 40, textAlign: "center" }}>
            <p style={{ color: "#94a3b8", fontSize: 14, margin: 0 }}>
              {detecting ? "Scanning..." : "Click \"Detect Patterns\" to find cross-practice denial patterns."}
            </p>
          </div>
        ) : (
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th style={styles.th}>Payer</th><th style={styles.th}>Code</th>
                <th style={styles.th}>Description</th><th style={styles.th}>Practices</th>
                <th style={styles.th}>Total Denied</th><th style={styles.th}>Claims</th>
                <th style={styles.th}>Action</th>
              </tr></thead>
              <tbody>
                {patterns.map(p => {
                  const key = `${p.payer_name}|${p.denial_code}`;
                  const isCreated = createdIds.has(key);
                  return (
                    <tr key={key} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                      <td style={styles.td}>{p.payer_name}</td>
                      <td style={styles.td}><span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600, padding: "2px 6px", borderRadius: 4, background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}>{p.denial_code}</span></td>
                      <td style={{ ...styles.td, fontSize: 12, color: "#94a3b8", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.denial_description || "—"}</td>
                      <td style={styles.td} title={p.practice_names?.join(", ")}>
                        <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: "rgba(59,130,246,0.15)", color: "#60a5fa" }}>{p.practice_count}</span>
                      </td>
                      <td style={{ ...styles.td, color: "#fca5a5" }}>${Number(p.total_denied_amount).toLocaleString()}</td>
                      <td style={{ ...styles.td, color: "#94a3b8" }}>{p.claim_count}</td>
                      <td style={styles.td}>
                        {billingRole === "admin" && (
                          isCreated ? (
                            <span style={{ fontSize: 12, color: "#5eead4" }}>Created</span>
                          ) : (
                            <button onClick={() => handleCreate(p)} disabled={creating === key}
                              style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer" }}>
                              {creating === key ? "..." : "Escalate"}
                            </button>
                          )
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 2: Active Escalations */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Escalations</h2>
          <div style={{ display: "flex", gap: 4 }}>
            {["", "open", "in_progress", "resolved", "closed"].map(s => (
              <button key={s} onClick={() => setStatusFilter(s)} style={{
                padding: "5px 12px", borderRadius: 6, border: "1px solid",
                borderColor: statusFilter === s ? "#0d9488" : "rgba(255,255,255,0.1)",
                background: statusFilter === s ? "rgba(13,148,136,0.15)" : "transparent",
                color: statusFilter === s ? "#5eead4" : "#94a3b8", fontSize: 12, cursor: "pointer",
              }}>
                {s ? s.replace("_", " ").replace(/\b\w/g, c => c.toUpperCase()) : "All"}
              </button>
            ))}
          </div>
        </div>

        {escLoading ? (
          <p style={{ color: "#94a3b8" }}>Loading...</p>
        ) : escalations.length === 0 ? (
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)", borderRadius: 12, padding: 40, textAlign: "center" }}>
            <p style={{ color: "#94a3b8", fontSize: 14, margin: 0 }}>No escalations yet — use Detect Patterns above to identify cross-practice denial patterns.</p>
          </div>
        ) : (
          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th style={styles.th}>Payer</th><th style={styles.th}>Code</th>
                <th style={styles.th}>Practices</th><th style={styles.th}>Total Denied</th>
                <th style={styles.th}>Status</th><th style={styles.th}>Created</th>
                <th style={styles.th}>Actions</th>
              </tr></thead>
              <tbody>
                {escalations.map(esc => (
                  <React.Fragment key={esc.id}>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.04)", cursor: "pointer" }} onClick={() => handleViewDetail(esc)}>
                      <td style={styles.td}>{esc.payer_name}</td>
                      <td style={styles.td}><span style={{ fontFamily: "monospace", fontSize: 12, fontWeight: 600, padding: "2px 6px", borderRadius: 4, background: "rgba(239,68,68,0.1)", color: "#fca5a5" }}>{esc.denial_code}</span></td>
                      <td style={styles.td}><span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: "rgba(59,130,246,0.15)", color: "#60a5fa" }}>{esc.affected_practice_count}</span></td>
                      <td style={{ ...styles.td, color: "#fca5a5" }}>${Number(esc.total_denied_amount || 0).toLocaleString()}</td>
                      <td style={styles.td}>{statusBadge(esc.status)}</td>
                      <td style={{ ...styles.td, color: "#64748b", fontSize: 13 }}>{esc.created_at ? new Date(esc.created_at).toLocaleDateString() : "—"}</td>
                      <td style={styles.td}>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer" }}>
                            {expandedEsc === esc.id ? "Close" : "Details"}
                          </button>
                          <button onClick={(ev) => { ev.stopPropagation(); handleExport(esc.id); }}
                            disabled={exporting === esc.id}
                            style={{ fontSize: 12, color: "#60a5fa", background: "none", border: "none", cursor: "pointer" }}>
                            {exporting === esc.id ? "..." : "Export"}
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedEsc === esc.id && escDetail && (
                      <tr><td colSpan={7} style={{ padding: "16px 20px", background: "rgba(13,148,136,0.03)" }}>
                        {/* Export button */}
                        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
                          <button onClick={() => handleExport(esc.id)} disabled={exporting === esc.id}
                            style={{
                              padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer",
                              background: exporting === esc.id ? "#334155" : "linear-gradient(135deg, #3b82f6, #60a5fa)",
                              color: "#fff", fontWeight: 600, fontSize: 13,
                            }}>
                            {exporting === esc.id ? "Generating..." : "Export Evidence Package"}
                          </button>
                        </div>
                        {/* Evidence */}
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>Evidence Summary</div>
                          <div style={{ display: "flex", gap: 24, fontSize: 13, color: "#cbd5e1", marginBottom: 12 }}>
                            <span>Date Range: <strong>{escDetail.evidence_summary?.date_range || "—"}</strong></span>
                            <span>Total Denied: <strong style={{ color: "#fca5a5" }}>${Number(escDetail.total_denied_amount || 0).toLocaleString()}</strong></span>
                            <span>Claims: <strong>{escDetail.evidence_summary?.claim_count || 0}</strong></span>
                          </div>
                          {(escDetail.practices || []).length > 0 && (
                            <div style={{ display: "grid", gap: 6 }}>
                              {escDetail.practices.map(p => (
                                <div key={p.practice_id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 10px", background: "rgba(255,255,255,0.02)", borderRadius: 6, fontSize: 13 }}>
                                  <span style={{ color: "#f1f5f9" }}>{p.practice_name}</span>
                                  <div style={{ display: "flex", gap: 16, color: "#94a3b8", fontSize: 12 }}>
                                    <span>${Number(p.denied_amount || 0).toLocaleString()}</span>
                                    <span>{p.claim_count} claims</span>
                                    {(p.sample_claim_numbers || []).length > 0 && (
                                      <span style={{ color: "#64748b" }}>e.g. {p.sample_claim_numbers.join(", ")}</span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        {/* Resolution */}
                        {escDetail.status === "resolved" && escDetail.recovered_amount != null && (
                          <div style={{ padding: "10px 12px", background: "rgba(13,148,136,0.08)", borderRadius: 8, marginBottom: 12 }}>
                            <span style={{ fontSize: 13, color: "#5eead4" }}>Recovered: <strong>${Number(escDetail.recovered_amount).toLocaleString()}</strong></span>
                            {escDetail.resolution_notes && <span style={{ fontSize: 12, color: "#94a3b8", marginLeft: 16 }}>{escDetail.resolution_notes}</span>}
                          </div>
                        )}
                        {/* Status update (admin only) */}
                        {billingRole === "admin" && escDetail.status !== "closed" && (
                          <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12, marginTop: 12 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8 }}>Update Status</div>
                            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
                              <select value={updateStatus} onChange={(e) => setUpdateStatus(e.target.value)}
                                style={{ padding: "6px 10px", borderRadius: 6, fontSize: 13, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", appearance: "auto" }}>
                                <option value="open">Open</option>
                                <option value="in_progress">In Progress</option>
                                <option value="resolved">Resolved</option>
                                <option value="closed">Closed</option>
                              </select>
                              {updateStatus === "resolved" && (
                                <input type="number" value={updateAmount} onChange={(e) => setUpdateAmount(e.target.value)}
                                  placeholder="Recovered $" style={{ padding: "6px 10px", borderRadius: 6, fontSize: 13, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", width: 120 }} />
                              )}
                              <input value={updateNotes} onChange={(e) => setUpdateNotes(e.target.value)}
                                placeholder="Notes..." style={{ padding: "6px 10px", borderRadius: 6, fontSize: 13, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", flex: 1, minWidth: 150 }} />
                              <button onClick={handleStatusUpdate} disabled={saving}
                                style={{ padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer", background: saving ? "#334155" : "#0d9488", color: "#fff", fontWeight: 600, fontSize: 13 }}>
                                {saving ? "..." : "Save"}
                              </button>
                            </div>
                          </div>
                        )}
                      </td></tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


// --- Contracts Panel ---
function ContractsPanel({ token, practices, billingRole }) {
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [analysisView, setAnalysisView] = useState(null);
  const [analyzing, setAnalyzing] = useState(null);
  const [analyzingAll, setAnalyzingAll] = useState(false);
  const [filterPractice, setFilterPractice] = useState("");
  const [alertDismissed, setAlertDismissed] = useState(false);

  // Upload form
  const [upPractice, setUpPractice] = useState("");
  const [upPayer, setUpPayer] = useState("");
  const [upEffDate, setUpEffDate] = useState("");
  const [upExpDate, setUpExpDate] = useState("");
  const [upFile, setUpFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const activePractices = (practices || []).filter(p => p.active);

  const fetchContracts = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const url = filterPractice
        ? `${API}/api/billing/contracts?practice_id=${filterPractice}`
        : `${API}/api/billing/contracts`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) { const d = await res.json(); setContracts(d.contracts || []); }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [token, filterPractice]);

  useEffect(() => { fetchContracts(); }, [fetchContracts]);

  const expiringSoon = contracts.filter(c => c.status === "expiring_soon");

  const handleUpload = async () => {
    if (!upPractice || !upPayer.trim() || !upFile) { setUploadError("Fill all required fields."); return; }
    setUploading(true); setUploadError("");
    try {
      const fd = new FormData();
      fd.append("practice_id", upPractice);
      fd.append("payer_name", upPayer.trim());
      if (upEffDate) fd.append("effective_date", upEffDate);
      if (upExpDate) fd.append("expiry_date", upExpDate);
      fd.append("file", upFile);
      const res = await fetch(`${API}/api/billing/contracts/upload`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      if (res.ok) {
        setShowUpload(false); setUpPractice(""); setUpPayer(""); setUpEffDate(""); setUpExpDate(""); setUpFile(null);
        fetchContracts();
      } else { const d = await res.json(); setUploadError(d.detail || "Upload failed."); }
    } catch { setUploadError("Upload failed."); }
    finally { setUploading(false); }
  };

  const handleAnalyze = async (contractId) => {
    setAnalyzing(contractId);
    try {
      const res = await fetch(`${API}/api/billing/contracts/${contractId}/analyze`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const d = await res.json();
        setAnalysisView({ id: contractId, data: d.analysis });
        fetchContracts();
      }
    } catch { /* ignore */ }
    finally { setAnalyzing(null); }
  };

  const handleAnalyzeAll = async () => {
    setAnalyzingAll(true);
    try {
      await fetch(`${API}/api/billing/contracts/analyze-all`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      fetchContracts();
    } catch { /* ignore */ }
    finally { setAnalyzingAll(false); }
  };

  const handleHistory = async (contract) => {
    if (expandedId === contract.id && historyData) { setExpandedId(null); setHistoryData(null); return; }
    setExpandedId(contract.id); setHistoryData(null);
    try {
      const res = await fetch(`${API}/api/billing/contracts/${contract.id}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) { const d = await res.json(); setHistoryData(d.versions || []); }
    } catch { /* ignore */ }
  };

  const statusBadge = (status) => {
    const map = {
      active: { bg: "rgba(13,148,136,0.15)", color: "#5eead4", label: "Active" },
      expiring_soon: { bg: "rgba(245,158,11,0.15)", color: "#fbbf24", label: "Expiring Soon" },
      expired: { bg: "rgba(239,68,68,0.1)", color: "#fca5a5", label: "Expired" },
    };
    const s = map[status] || map.active;
    return <span style={{ display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: s.bg, color: s.color }}>{s.label}</span>;
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: 0 }}>Contracts</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={filterPractice} onChange={(e) => setFilterPractice(e.target.value)}
            style={{ padding: "6px 10px", borderRadius: 6, fontSize: 13, border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.06)", color: "#f1f5f9", appearance: "auto" }}>
            <option value="">All practices</option>
            {activePractices.map(p => <option key={p.practice_id} value={p.practice_id}>{p.practice_name}</option>)}
          </select>
          {billingRole === "admin" && (
            <button onClick={handleAnalyzeAll} disabled={analyzingAll} style={{
              padding: "6px 14px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.1)",
              background: analyzingAll ? "#334155" : "rgba(255,255,255,0.06)", color: "#94a3b8",
              fontSize: 13, cursor: "pointer",
            }}>
              {analyzingAll ? "Analyzing..." : "Analyze All"}
            </button>
          )}
          <button onClick={() => setShowUpload(true)} style={{
            padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer",
            background: "linear-gradient(135deg, #0d9488, #14b8a6)", color: "#fff", fontWeight: 600, fontSize: 13,
          }}>
            Upload Contract
          </button>
        </div>
      </div>

      {/* Expiry alert */}
      {expiringSoon.length > 0 && !alertDismissed && (
        <div style={{
          background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)",
          borderRadius: 8, padding: "10px 16px", marginBottom: 16,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div>
            <span style={{ color: "#fbbf24", fontSize: 13, fontWeight: 500 }}>
              {expiringSoon.length} contract{expiringSoon.length > 1 ? "s" : ""} expiring within 90 days:
            </span>
            <span style={{ color: "#fbbf24", fontSize: 12, marginLeft: 8 }}>
              {expiringSoon.map(c => `${c.practice_name} / ${c.payer_name}`).join(", ")}
            </span>
          </div>
          <button onClick={() => setAlertDismissed(true)} style={{ color: "#fbbf24", background: "none", border: "none", cursor: "pointer", fontSize: 16 }}>&times;</button>
        </div>
      )}

      {/* Upload modal */}
      {showUpload && (
        <div style={{
          background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 24, marginBottom: 24,
        }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f1f5f9", margin: "0 0 16px" }}>Upload Contract</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
            <div>
              <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Practice *</label>
              <select value={upPractice} onChange={(e) => setUpPractice(e.target.value)} style={styles.input}>
                <option value="">Select...</option>
                {activePractices.map(p => <option key={p.practice_id} value={p.practice_id}>{p.practice_name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Payer Name *</label>
              <input value={upPayer} onChange={(e) => setUpPayer(e.target.value)} placeholder="e.g. Aetna" style={styles.input} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Effective Date</label>
              <input type="date" value={upEffDate} onChange={(e) => setUpEffDate(e.target.value)} style={styles.input} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Expiry Date</label>
              <input type="date" value={upExpDate} onChange={(e) => setUpExpDate(e.target.value)} style={styles.input} />
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: "#94a3b8", display: "block", marginBottom: 4 }}>Contract PDF *</label>
            <div
              onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = "rgba(13,148,136,0.5)"; }}
              onDragLeave={(e) => { e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)"; }}
              onDrop={(e) => {
                e.preventDefault(); e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)";
                const f = e.dataTransfer.files[0];
                if (f && f.name.toLowerCase().endsWith(".pdf")) setUpFile(f);
              }}
              onClick={() => { const i = document.createElement("input"); i.type = "file"; i.accept = ".pdf"; i.onchange = (e) => { if (e.target.files[0]) setUpFile(e.target.files[0]); }; i.click(); }}
              style={{
                border: "2px dashed rgba(255,255,255,0.12)", borderRadius: 10, padding: upFile ? "12px 16px" : "24px 16px",
                textAlign: "center", cursor: "pointer", background: "rgba(255,255,255,0.02)", transition: "border-color 0.2s",
              }}
            >
              {upFile ? (
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 13, color: "#5eead4" }}>{upFile.name}</span>
                  <button onClick={(e) => { e.stopPropagation(); setUpFile(null); }}
                    style={{ fontSize: 11, color: "#f87171", background: "none", border: "none", cursor: "pointer" }}>Remove</button>
                </div>
              ) : (
                <p style={{ color: "#94a3b8", fontSize: 13, margin: 0 }}>
                  Drag & drop your PDF here, or click to browse
                  <br /><span style={{ fontSize: 11, color: "#64748b" }}>PDF only, max 10MB</span>
                </p>
              )}
            </div>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={handleUpload} disabled={uploading} style={{
              padding: "8px 20px", borderRadius: 8, border: "none", cursor: "pointer",
              background: uploading ? "#334155" : "#0d9488", color: "#fff", fontWeight: 600, fontSize: 14,
            }}>{uploading ? "Uploading..." : "Upload"}</button>
            <button onClick={() => { setShowUpload(false); setUploadError(""); }}
              style={{ padding: "8px 20px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)", background: "none", color: "#94a3b8", cursor: "pointer", fontSize: 14 }}>Cancel</button>
          </div>
          {uploadError && <p style={{ color: "#fca5a5", fontSize: 13, marginTop: 8 }}>{uploadError}</p>}
        </div>
      )}

      {/* Contracts table */}
      {loading ? (
        <p style={{ color: "#94a3b8" }}>Loading contracts...</p>
      ) : contracts.length === 0 ? (
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)", borderRadius: 12, padding: 48, textAlign: "center" }}>
          <p style={{ color: "#94a3b8", fontSize: 15, margin: 0 }}>No contracts yet. Upload a contract PDF to get started.</p>
        </div>
      ) : (
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th style={styles.th}>Practice</th>
                <th style={styles.th}>Payer</th>
                <th style={styles.th}>Effective</th>
                <th style={styles.th}>Expiry</th>
                <th style={styles.th}>Ver</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Analyzed</th>
                <th style={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map(c => (
                <React.Fragment key={c.id}>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={styles.td}>{c.practice_name}</td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>{c.payer_name}</td>
                    <td style={{ ...styles.td, color: "#64748b", fontSize: 13 }}>{c.effective_date || "—"}</td>
                    <td style={{ ...styles.td, color: "#64748b", fontSize: 13 }}>{c.expiry_date || "—"}</td>
                    <td style={{ ...styles.td, color: "#94a3b8" }}>v{c.version}</td>
                    <td style={styles.td}>{statusBadge(c.status)}</td>
                    <td style={{ ...styles.td, color: "#64748b", fontSize: 13 }}>
                      {c.analyzed_at ? new Date(c.analyzed_at).toLocaleDateString() : "—"}
                    </td>
                    <td style={styles.td}>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button onClick={() => handleAnalyze(c.id)} disabled={analyzing === c.id}
                          style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer" }}>
                          {analyzing === c.id ? "..." : "Analyze"}
                        </button>
                        <button onClick={() => handleHistory(c)}
                          style={{ fontSize: 12, color: "#60a5fa", background: "none", border: "none", cursor: "pointer" }}>
                          History
                        </button>
                      </div>
                    </td>
                  </tr>
                  {/* History expansion */}
                  {expandedId === c.id && historyData && (
                    <tr><td colSpan={8} style={{ padding: "12px 16px", background: "rgba(59,130,246,0.03)" }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8 }}>Version History</div>
                      {historyData.map(v => (
                        <div key={v.id} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", fontSize: 13, color: "#cbd5e1", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                          <span>v{v.version} {v.is_current ? "(current)" : ""}</span>
                          <span style={{ color: "#64748b" }}>{v.filename} — {new Date(v.created_at).toLocaleDateString()} by {v.uploaded_by_email || "—"}</span>
                        </div>
                      ))}
                    </td></tr>
                  )}
                  {/* Analysis expansion */}
                  {analysisView?.id === c.id && analysisView.data && (
                    <tr><td colSpan={8} style={{ padding: "16px 20px", background: "rgba(13,148,136,0.03)" }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", marginBottom: 8 }}>Analysis Result</div>
                      {analysisView.data.extraction?.rates?.length > 0 ? (
                        <>
                          <p style={{ fontSize: 13, color: "#5eead4", margin: "0 0 8px" }}>
                            {analysisView.data.rates_extracted} rate{analysisView.data.rates_extracted !== 1 ? "s" : ""} extracted
                            {analysisView.data.extraction?.payer_name ? ` for ${analysisView.data.extraction.payer_name}` : ""}
                          </p>
                          <div style={{ maxHeight: 200, overflow: "auto" }}>
                            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                              <thead><tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                                <th style={{ ...styles.th, fontSize: 10 }}>CPT</th>
                                <th style={{ ...styles.th, fontSize: 10 }}>Rate</th>
                                <th style={{ ...styles.th, fontSize: 10 }}>Description</th>
                              </tr></thead>
                              <tbody>
                                {analysisView.data.extraction.rates.slice(0, 30).map((r, i) => (
                                  <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                    <td style={{ ...styles.td, fontSize: 12, fontFamily: "monospace" }}>{r.cpt}</td>
                                    <td style={{ ...styles.td, fontSize: 12, color: "#5eead4" }}>${Number(r.rate || 0).toFixed(2)}</td>
                                    <td style={{ ...styles.td, fontSize: 11, color: "#94a3b8" }}>{r.description || "—"}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      ) : (
                        <p style={{ fontSize: 13, color: "#94a3b8" }}>No rates could be extracted from this document.</p>
                      )}
                    </td></tr>
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
  portalSettings, setPortalSettings, providerStatuses,
}) {
  // Branding state
  const [headerText, setHeaderText] = useState(billingCompany?.report_header_text || "");
  const [footerText, setFooterText] = useState(billingCompany?.report_footer_text || "");
  const [logoUrl, setLogoUrl] = useState(billingCompany?.logo_url || "");
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [brandingSaving, setBrandingSaving] = useState(false);
  const [brandingMsg, setBrandingMsg] = useState("");

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

  const handleLogoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingLogo(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API}/api/billing/settings/logo`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` }, body: fd,
      });
      if (res.ok) {
        const data = await res.json();
        setLogoUrl(data.logo_url);
        setBrandingMsg("Logo uploaded!");
        fetchMe();
        setTimeout(() => setBrandingMsg(""), 3000);
      } else {
        const d = await res.json();
        setBrandingMsg(d.detail || "Upload failed.");
      }
    } catch { setBrandingMsg("Upload failed."); }
    finally { setUploadingLogo(false); }
  };

  const handleBrandingSave = async () => {
    setBrandingSaving(true); setBrandingMsg("");
    try {
      const res = await fetch(`${API}/api/billing/settings/report-text`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ report_header_text: headerText, report_footer_text: footerText }),
      });
      if (res.ok) {
        setBrandingMsg("Saved!"); fetchMe();
        setTimeout(() => setBrandingMsg(""), 3000);
      } else { setBrandingMsg("Failed to save."); }
    } catch { setBrandingMsg("Failed to save."); }
    finally { setBrandingSaving(false); }
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

      {/* Section 3: Subscription */}
      <SubscriptionSection sectionStyle={sectionStyle} labelStyle={labelStyle} subscription={subscription} token={token} />

      {/* Section 4: Report Branding */}
      <div style={sectionStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
          Report Branding
        </h3>
        <label style={labelStyle}>Company Logo</label>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
          {logoUrl && (
            <div style={{
              width: 60, height: 60, borderRadius: 8, background: "rgba(255,255,255,0.06)",
              display: "flex", alignItems: "center", justifyContent: "center",
              border: "1px solid rgba(255,255,255,0.1)", overflow: "hidden",
            }}>
              <span style={{ fontSize: 10, color: "#5eead4" }}>Logo set</span>
            </div>
          )}
          <label style={{
            padding: "6px 14px", borderRadius: 6, fontSize: 13, cursor: "pointer",
            background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
            color: "#94a3b8",
          }}>
            {uploadingLogo ? "Uploading..." : logoUrl ? "Replace Logo" : "Upload Logo (PNG/JPG)"}
            <input type="file" accept=".png,.jpg,.jpeg" onChange={handleLogoUpload}
              style={{ display: "none" }} />
          </label>
        </div>

        <label style={labelStyle}>Report Header Text</label>
        <input value={headerText} onChange={(e) => setHeaderText(e.target.value)}
          placeholder="e.g. Prepared by Acme Billing Co." style={inputStyle} />

        <label style={labelStyle}>Report Footer Text</label>
        <input value={footerText} onChange={(e) => setFooterText(e.target.value)}
          placeholder="e.g. Confidential — for practice use only" style={inputStyle} />

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4 }}>
          <button onClick={handleBrandingSave} disabled={brandingSaving}
            style={{
              background: brandingSaving ? "#334155" : "#0d9488", color: "white", border: "none",
              borderRadius: 8, padding: "8px 16px", fontSize: 13, fontWeight: 600,
              cursor: brandingSaving ? "not-allowed" : "pointer",
            }}>
            {brandingSaving ? "Saving..." : "Save Branding"}
          </button>
          {brandingMsg && (
            <span style={{ fontSize: 13, color: brandingMsg === "Saved!" || brandingMsg === "Logo uploaded!" ? "#10B981" : "#f87171" }}>
              {brandingMsg}
            </span>
          )}
        </div>
      </div>

      {/* Section 5: Practice Portals */}
      <div style={sectionStyle}>
        <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
          Practice Portals
        </h3>
        {(portalSettings || []).length === 0 ? (
          <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 14 }}>No practices linked yet.</p>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            {portalSettings.map(ps => (
              <PortalSettingsRow key={ps.practice_id} ps={ps} token={token}
                providerStatuses={providerStatuses} setPortalSettings={setPortalSettings}
                portalSettings={portalSettings} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SubscriptionSection({ sectionStyle, labelStyle, subscription, token }) {
  const tier = subscription?.tier || "free";
  const status = subscription?.status || "active";
  const limit = subscription?.practice_count_limit ?? 1;
  const isFree = tier === "free" || tier === "trial";

  const handleCheckout = async (t) => {
    try {
      const res = await fetch(`${API}/api/billing/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ tier: t }),
      });
      const data = await res.json();
      if (res.ok && data.checkout_url) window.location.href = data.checkout_url;
    } catch { /* ignore */ }
  };

  const handlePortal = async () => {
    try {
      const res = await fetch(`${API}/api/billing/subscription/portal`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok && data.portal_url) window.location.href = data.portal_url;
    } catch { /* ignore */ }
  };

  // Check URL for payment result
  const params = new URLSearchParams(window.location.search);
  const paymentResult = params.get("payment");

  return (
    <div style={sectionStyle}>
      <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
        Subscription
      </h3>

      {paymentResult === "success" && (
        <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(13,148,136,0.1)", border: "1px solid rgba(13,148,136,0.3)", marginBottom: 16, color: "#5eead4", fontSize: 13 }}>
          Subscription activated — you can now add more practices.
        </div>
      )}
      {paymentResult === "cancelled" && (
        <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", marginBottom: 16, color: "#fbbf24", fontSize: 13 }}>
          Checkout cancelled — your plan was not changed.
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label style={labelStyle}>Plan</label>
          <div style={{ fontSize: 14, color: "#f1f5f9", textTransform: "capitalize" }}>
            {tier}
            {isFree && <span style={{ display: "inline-block", marginLeft: 8, padding: "2px 8px", borderRadius: 10, background: "rgba(148,163,184,0.15)", color: "#94a3b8", fontSize: 11, fontWeight: 600 }}>Free</span>}
          </div>
        </div>
        <div>
          <label style={labelStyle}>Status</label>
          <div style={{ fontSize: 14, color: status === "active" ? "#5eead4" : status === "past_due" ? "#fbbf24" : "#fca5a5", textTransform: "capitalize" }}>
            {status.replace("_", " ")}
          </div>
        </div>
        <div>
          <label style={labelStyle}>Practice Limit</label>
          <div style={{ fontSize: 14, color: "#f1f5f9" }}>{limit === 1 && isFree ? "1 (free)" : limit}</div>
        </div>
      </div>

      {isFree ? (
        <div>
          <p style={{ fontSize: 13, color: "#94a3b8", margin: "0 0 12px" }}>Managing 1 practice free. Subscribe to manage more.</p>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => handleCheckout("starter")} style={{
              padding: "8px 16px", borderRadius: 8, border: "none", cursor: "pointer",
              background: "linear-gradient(135deg, #0d9488, #14b8a6)", color: "#fff", fontWeight: 600, fontSize: 13,
            }}>Starter — $299/mo</button>
            <button onClick={() => handleCheckout("growth")} style={{
              padding: "8px 16px", borderRadius: 8, border: "none", cursor: "pointer",
              background: "linear-gradient(135deg, #3b82f6, #60a5fa)", color: "#fff", fontWeight: 600, fontSize: 13,
            }}>Growth — $699/mo</button>
          </div>
        </div>
      ) : tier === "starter" ? (
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => handleCheckout("growth")} style={{
            padding: "8px 16px", borderRadius: 8, border: "1px solid rgba(59,130,246,0.3)",
            background: "none", color: "#60a5fa", cursor: "pointer", fontSize: 13, fontWeight: 500,
          }}>Upgrade to Growth</button>
          <button onClick={handlePortal} style={{
            padding: "8px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)",
            background: "none", color: "#94a3b8", cursor: "pointer", fontSize: 13,
          }}>Manage Billing</button>
        </div>
      ) : (
        <button onClick={handlePortal} style={{
          padding: "8px 16px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)",
          background: "none", color: "#94a3b8", cursor: "pointer", fontSize: 13,
        }}>Manage Billing</button>
      )}
    </div>
  );
}

function PortalSettingsRow({ ps, token, providerStatuses, setPortalSettings, portalSettings }) {
  const [localEmail, setLocalEmail] = useState(ps.portal_contact_email || "");
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");

  const updateSetting = async (updates) => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/billing/portal-settings/${ps.practice_id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        setPortalSettings(prev => prev.map(p =>
          p.practice_id === ps.practice_id ? { ...p, ...updates } : p
        ));
      }
    } catch { /* ignore */ }
    finally { setSaving(false); }
  };

  const handleToggle = (field) => {
    if (field === "portal_enabled" && !ps.portal_enabled && !localEmail && !ps.portal_contact_email) {
      alert("Add a contact email before enabling the portal.");
      return;
    }
    updateSetting({ [field]: !ps[field] });
  };

  const handleEmailBlur = () => {
    if (localEmail !== (ps.portal_contact_email || "")) {
      updateSetting({ portal_contact_email: localEmail.trim().toLowerCase() });
    }
  };

  const portalUrl = `https://billing.civicscale.ai/portal?practice=${ps.practice_id}`;
  const handleCopy = () => {
    navigator.clipboard.writeText(portalUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const canInvite = ps.portal_enabled && (localEmail || ps.portal_contact_email);
  const handleSendInvite = async () => {
    setInviting(true); setInviteMsg("");
    try {
      const res = await fetch(`${API}/api/billing/portal/send-invite/${ps.practice_id}`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        setInviteMsg(`Invite sent to ${data.email}`);
        setTimeout(() => setInviteMsg(""), 4000);
      } else {
        setInviteMsg(data.detail || "Failed to send.");
        setTimeout(() => setInviteMsg(""), 4000);
      }
    } catch { setInviteMsg("Failed to send."); }
    finally { setInviting(false); }
  };

  return (
    <div style={{
      background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 8, padding: "12px 16px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 500, color: "#f1f5f9" }}>{ps.practice_name}</span>
          {providerStatuses?.[ps.practice_id] && (
            <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 3, background: "rgba(13,148,136,0.15)", color: "#5eead4", fontWeight: 600 }}>
              Provider
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer", fontSize: 12, color: ps.portal_enabled ? "#5eead4" : "#64748b" }}>
            <input type="checkbox" checked={ps.portal_enabled} onChange={() => handleToggle("portal_enabled")}
              style={{ accentColor: "#0d9488" }} />
            {ps.portal_enabled ? "Enabled" : "Disabled"}
          </label>
          {ps.portal_enabled && (
            <>
              <button onClick={handleSendInvite} disabled={!canInvite || inviting}
                title={!canInvite ? "Enable the portal and add a contact email first" : ""}
                style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 4,
                  cursor: canInvite && !inviting ? "pointer" : "not-allowed",
                  background: inviteMsg && !inviteMsg.startsWith("Failed") ? "rgba(13,148,136,0.15)" : "rgba(59,130,246,0.1)",
                  border: "1px solid rgba(59,130,246,0.2)", color: inviteMsg && !inviteMsg.startsWith("Failed") ? "#5eead4" : "#60a5fa",
                  opacity: canInvite ? 1 : 0.5,
                }}>
                {inviting ? "Sending..." : inviteMsg || "Send Invite"}
              </button>
              <button onClick={handleCopy} style={{
                fontSize: 11, padding: "2px 8px", borderRadius: 4, cursor: "pointer",
                background: copied ? "rgba(13,148,136,0.15)" : "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.1)", color: copied ? "#5eead4" : "#94a3b8",
              }}>
                {copied ? "Copied!" : "Copy Link"}
              </button>
            </>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
        <input type="email" value={localEmail} onChange={(e) => setLocalEmail(e.target.value)}
          onBlur={handleEmailBlur} placeholder="portal contact email"
          style={{ flex: 1, padding: "5px 8px", borderRadius: 6, fontSize: 12,
            border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.04)",
            color: "#f1f5f9", boxSizing: "border-box" }} />
      </div>

      {ps.portal_enabled && (
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {[
            { key: "show_denial_summary", label: "Denials" },
            { key: "show_payer_performance", label: "Payers" },
            { key: "show_appeal_roi", label: "ROI" },
            { key: "show_generate_report", label: "PDF" },
          ].map(s => (
            <label key={s.key} style={{
              display: "flex", alignItems: "center", gap: 3, cursor: "pointer", fontSize: 11,
              color: ps[s.key] ? "#5eead4" : "#64748b",
            }}>
              <input type="checkbox" checked={ps[s.key] || false}
                onChange={() => handleToggle(s.key)} style={{ accentColor: "#0d9488" }} />
              {s.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}


// --- Team Panel ---
function TeamPanel({ token, billingRole, allPractices }) {
  const [analysts, setAnalysts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingUserId, setEditingUserId] = useState(null);
  const [editPracticeIds, setEditPracticeIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  const activePractices = (allPractices || []).filter(p => p.active);

  const fetchAnalysts = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/billing/team/analysts`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setAnalysts(data.analysts || []);
      }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetchAnalysts(); }, [fetchAnalysts]);

  if (billingRole !== "admin") {
    return (
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 24px" }}>Team</h2>
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 15, margin: 0 }}>
            Contact your administrator to manage team assignments.
          </p>
        </div>
      </div>
    );
  }

  const startEdit = (analyst) => {
    setEditingUserId(analyst.user_id);
    setEditPracticeIds(analyst.assigned_practices.map(p => p.practice_id));
    setSaveMsg("");
  };

  const togglePractice = (pid) => {
    setEditPracticeIds(prev =>
      prev.includes(pid) ? prev.filter(id => id !== pid) : [...prev, pid]
    );
  };

  const handleSave = async () => {
    setSaving(true); setSaveMsg("");
    try {
      const res = await fetch(`${API}/api/billing/team/assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ analyst_user_id: editingUserId, practice_ids: editPracticeIds }),
      });
      if (res.ok) {
        setSaveMsg("Saved!");
        setEditingUserId(null);
        fetchAnalysts();
        setTimeout(() => setSaveMsg(""), 3000);
      } else {
        const d = await res.json();
        setSaveMsg(d.detail || "Failed.");
      }
    } catch { setSaveMsg("Failed to save."); }
    finally { setSaving(false); }
  };

  return (
    <div>
      <h2 style={{ fontSize: 20, fontWeight: 600, color: "#f1f5f9", margin: "0 0 24px" }}>Analyst Assignments</h2>

      {saveMsg && (
        <div style={{
          padding: "8px 16px", borderRadius: 8, marginBottom: 16,
          background: saveMsg === "Saved!" ? "rgba(13,148,136,0.1)" : "rgba(239,68,68,0.1)",
          border: `1px solid ${saveMsg === "Saved!" ? "rgba(13,148,136,0.3)" : "rgba(239,68,68,0.3)"}`,
          color: saveMsg === "Saved!" ? "#5eead4" : "#fca5a5", fontSize: 13,
        }}>
          {saveMsg}
        </div>
      )}

      {loading ? (
        <p style={{ color: "#94a3b8" }}>Loading team...</p>
      ) : analysts.length === 0 ? (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.1)",
          borderRadius: 12, padding: 48, textAlign: "center",
        }}>
          <p style={{ color: "#94a3b8", fontSize: 15, margin: 0 }}>No team members yet. Invite users from Settings.</p>
        </div>
      ) : (
        <div style={{
          background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 12, overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <th style={styles.th}>Name</th>
                <th style={styles.th}>Email</th>
                <th style={styles.th}>Role</th>
                <th style={styles.th}>Assigned Practices</th>
                <th style={styles.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {analysts.map(a => (
                <React.Fragment key={a.user_id}>
                  <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td style={styles.td}>{a.full_name || "—"}</td>
                    <td style={{ ...styles.td, color: "#94a3b8", fontSize: 13 }}>{a.email}</td>
                    <td style={styles.td}>
                      <span style={{
                        display: "inline-block", padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600,
                        background: a.role === "admin" ? "rgba(59,130,246,0.15)" : "rgba(148,163,184,0.15)",
                        color: a.role === "admin" ? "#60a5fa" : "#94a3b8",
                        textTransform: "capitalize",
                      }}>
                        {a.role}
                      </span>
                    </td>
                    <td style={{ ...styles.td, fontSize: 13 }}>
                      {a.role === "admin" ? (
                        <span style={{ color: "#64748b", fontStyle: "italic" }}>All practices</span>
                      ) : a.assigned_practices.length === 0 ? (
                        <span style={{ color: "#64748b" }}>None</span>
                      ) : (
                        a.assigned_practices.map(p => p.practice_name).join(", ")
                      )}
                    </td>
                    <td style={styles.td}>
                      {a.role !== "admin" && (
                        <button onClick={() => editingUserId === a.user_id ? setEditingUserId(null) : startEdit(a)}
                          style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer" }}>
                          {editingUserId === a.user_id ? "Cancel" : "Edit"}
                        </button>
                      )}
                    </td>
                  </tr>
                  {editingUserId === a.user_id && (
                    <tr>
                      <td colSpan={5} style={{ padding: "12px 16px", background: "rgba(13,148,136,0.03)" }}>
                        <div style={{ marginBottom: 8 }}>
                          <span style={{ fontSize: 13, color: "#cbd5e1", fontWeight: 500 }}>
                            Assign practices to {a.full_name || a.email}:
                          </span>
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
                          {activePractices.map(p => {
                            const checked = editPracticeIds.includes(p.practice_id);
                            return (
                              <label key={p.practice_id} style={{
                                display: "flex", alignItems: "center", gap: 6, cursor: "pointer",
                                padding: "4px 10px", borderRadius: 6, fontSize: 13,
                                background: checked ? "rgba(13,148,136,0.15)" : "rgba(255,255,255,0.03)",
                                border: `1px solid ${checked ? "rgba(13,148,136,0.3)" : "rgba(255,255,255,0.08)"}`,
                                color: checked ? "#5eead4" : "#94a3b8",
                              }}>
                                <input type="checkbox" checked={checked}
                                  onChange={() => togglePractice(p.practice_id)}
                                  style={{ accentColor: "#0d9488" }} />
                                {p.practice_name}
                              </label>
                            );
                          })}
                        </div>
                        <button onClick={handleSave} disabled={saving}
                          style={{
                            padding: "6px 16px", borderRadius: 6, border: "none", cursor: "pointer",
                            background: saving ? "#334155" : "#0d9488", color: "#fff",
                            fontWeight: 600, fontSize: 13,
                          }}>
                          {saving ? "Saving..." : "Save Assignments"}
                        </button>
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
