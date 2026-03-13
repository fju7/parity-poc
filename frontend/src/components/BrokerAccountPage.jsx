import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthGate from "./AuthGate";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function BrokerAccountInner() {
  const navigate = useNavigate();
  const { token, user, company, logout: authLogout, refetch } = useAuth();

  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  // Editable fields
  const [contactName, setContactName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [phone, setPhone] = useState("");

  // Upgrade toast
  const [upgradeToast, setUpgradeToast] = useState(false);
  const [upgradeMessage, setUpgradeMessage] = useState("Welcome to Broker Pro! Your account has been upgraded.");

  // Cancel modal
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);

  // Reactivate
  const [reactivateLoading, setReactivateLoading] = useState(false);

  // Team management
  const [teamMembers, setTeamMembers] = useState([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");

  // Deletion modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmName, setDeleteConfirmName] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState("");

  // Referral
  const [referralCode, setReferralCode] = useState("");
  const [referralUrl, setReferralUrl] = useState("");
  const [referralCount, setReferralCount] = useState(0);
  const [convertedCount, setConvertedCount] = useState(0);
  const [referralCopied, setReferralCopied] = useState(false);
  const [colleagueEmail, setColleagueEmail] = useState("");
  const [colleagueName, setColleagueName] = useState("");
  const [referralSending, setReferralSending] = useState(false);
  const [referralMsg, setReferralMsg] = useState("");
  const [showEmailPreview, setShowEmailPreview] = useState(false);

  const authHeaders = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    if (!token) return;
    fetchAccount();
    fetchTeam();
    fetchReferral();
  }, [token]);

  // Handle ?upgraded=true — poll until plan shows "pro"
  useEffect(() => {
    if (!token) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("upgraded") === "true") {
      window.history.replaceState({}, "", "/broker/account");
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const res = await fetch(`${API}/api/broker/plan`, { headers: authHeaders });
          const data = await res.json();
          if (data.plan === "pro" || data.plan === "pro_cancelling") {
            setAccount(prev => ({ ...prev, plan: data.plan, client_count: data.client_count, client_limit: data.client_limit, subscription_period_end: data.subscription_period_end }));
            setUpgradeMessage("Welcome to Broker Pro! Your account has been upgraded.");
            setUpgradeToast(true);
            setTimeout(() => setUpgradeToast(false), 5000);
            clearInterval(poll);
          } else if (attempts >= 10) {
            setUpgradeMessage("Upgrade processing \u2014 your plan will update shortly. Refresh in a moment if it hasn\u2019t changed.");
            setUpgradeToast(true);
            setTimeout(() => setUpgradeToast(false), 8000);
            clearInterval(poll);
          }
        } catch {
          clearInterval(poll);
        }
      }, 2000);
    }
  }, [token]);

  const fetchAccount = async () => {
    setLoading(true);
    try {
      const [acctRes, planRes] = await Promise.all([
        fetch(`${API}/api/broker/account`, { headers: authHeaders }),
        fetch(`${API}/api/broker/plan`, { headers: authHeaders }),
      ]);
      const acctData = await acctRes.json();
      const planData = await planRes.json();
      setAccount({ ...acctData, ...planData });
      setContactName(acctData.contact_name || "");
      setFirmName(acctData.firm_name || "");
      setPhone(acctData.phone || "");
    } catch (err) { console.error("Failed to load account:", err); }
    setLoading(false);
  };

  const fetchTeam = async () => {
    try {
      const res = await fetch(`${API}/api/auth/users`, { headers: authHeaders });
      if (res.ok) {
        const data = await res.json();
        setTeamMembers(data.users || []);
      }
    } catch (err) { console.error("Failed to load team:", err); }
  };

  const fetchReferral = async () => {
    try {
      const res = await fetch(`${API}/api/broker/referral`, { headers: authHeaders });
      if (res.ok) {
        const data = await res.json();
        setReferralCode(data.referral_code || "");
        setReferralUrl(data.referral_url || "");
        setReferralCount(data.referral_count || 0);
        setConvertedCount(data.converted_count || 0);
      }
    } catch (err) { console.error("Failed to load referral:", err); }
  };

  const handleSendReferral = async () => {
    if (!colleagueEmail.trim()) return;
    setReferralSending(true);
    setReferralMsg("");
    try {
      const res = await fetch(`${API}/api/broker/referral/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ colleague_email: colleagueEmail.trim(), colleague_name: colleagueName.trim() }),
      });
      const data = await res.json();
      if (data.sent) {
        setReferralMsg(`Email sent to ${data.colleague_email}`);
        setColleagueEmail("");
        setColleagueName("");
        fetchReferral();
      } else if (data.reason === "already_referred") {
        setReferralMsg("You've already referred this person.");
      } else {
        setReferralMsg(data.detail || "Failed to send.");
      }
    } catch (err) { setReferralMsg("Failed to send referral email."); }
    setReferralSending(false);
  };

  const handleSave = async () => {
    if (!token) return;
    setSaving(true);
    setSaveMsg("");
    try {
      const res = await fetch(`${API}/api/broker/account`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({
          contact_name: contactName,
          firm_name: firmName,
          phone: phone,
        }),
      });
      if (res.ok) {
        setSaveMsg("Changes saved.");
        refetch();
        setTimeout(() => setSaveMsg(""), 3000);
      } else {
        setSaveMsg("Failed to save changes.");
      }
    } catch { setSaveMsg("Failed to save changes."); }
    setSaving(false);
  };

  const handleCancel = async () => {
    if (!token) return;
    setCancelLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/cancel-subscription`, {
        method: "POST",
        headers: authHeaders,
      });
      const data = await res.json();
      if (data.status === "cancelled") {
        setAccount(prev => ({ ...prev, plan: "pro_cancelling", subscription_period_end: data.period_end }));
        setShowCancelModal(false);
      }
    } catch (err) { console.error("Cancel failed:", err); }
    setCancelLoading(false);
  };

  const handleReactivate = async () => {
    if (!token) return;
    setReactivateLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/reactivate-subscription`, {
        method: "POST",
        headers: authHeaders,
      });
      const data = await res.json();
      if (data.status === "reactivated") {
        setAccount(prev => ({ ...prev, plan: "pro", subscription_period_end: null }));
      }
    } catch (err) { console.error("Reactivate failed:", err); }
    setReactivateLoading(false);
  };

  const handleUpgrade = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API}/api/broker/subscribe`, {
        method: "POST",
        headers: authHeaders,
      });
      const data = await res.json();
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (err) { console.error("Upgrade failed:", err); }
  };

  const [portalLoading, setPortalLoading] = useState(false);
  const handlePortal = async () => {
    if (!token) return;
    setPortalLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/portal`, {
        method: "POST",
        headers: authHeaders,
      });
      const data = await res.json();
      if (data.portal_url) window.location.href = data.portal_url;
      else alert(data.detail || "No billing account found.");
    } catch { alert("Failed to open billing portal."); }
    setPortalLoading(false);
  };

  const handleInviteTeamMember = async () => {
    if (!inviteEmail.includes("@")) { setInviteMsg("Enter a valid email."); return; }
    setInviteLoading(true);
    setInviteMsg("");
    try {
      const res = await fetch(`${API}/api/auth/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ invited_email: inviteEmail.trim().toLowerCase(), role: inviteRole }),
      });
      const data = await res.json();
      if (res.ok) {
        setInviteMsg("Invitation sent!");
        setInviteEmail("");
        setInviteRole("member");
        fetchTeam();
        setTimeout(() => setInviteMsg(""), 3000);
      } else {
        setInviteMsg(data.detail || "Failed to send invite.");
      }
    } catch { setInviteMsg("Failed to send invite."); }
    setInviteLoading(false);
  };

  const handleUpdateRole = async (userId, newRole) => {
    try {
      await fetch(`${API}/api/auth/users/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ role: newRole }),
      });
      fetchTeam();
    } catch { /* ignore */ }
  };

  const handleRemoveUser = async (userId, email) => {
    if (!confirm(`Remove ${email} from this account?`)) return;
    try {
      await fetch(`${API}/api/auth/users/${userId}`, {
        method: "DELETE",
        headers: authHeaders,
      });
      fetchTeam();
    } catch { /* ignore */ }
  };

  const handleDeletionRequest = async () => {
    setDeleting(true);
    setDeleteMsg("");
    try {
      const res = await fetch(`${API}/api/auth/deletion-request`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ confirm_company_name: deleteConfirmName }),
      });
      const data = await res.json();
      if (!res.ok) { setDeleteMsg(data.detail || "Request failed."); return; }
      setDeleteMsg("Deletion request submitted. Check your email for confirmation.");
      setTimeout(() => { setShowDeleteModal(false); setDeleteMsg(""); setDeleteConfirmName(""); }, 4000);
    } catch {
      setDeleteMsg("Failed to submit request.");
    } finally {
      setDeleting(false);
    }
  };

  const handleLogout = () => {
    authLogout();
    navigate("/broker/login");
  };

  const formatDate = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  };

  if (!token || loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans', sans-serif" }}>
      <p style={{ color: "#64748b" }}>Loading...</p>
    </div>
  );

  const isPro = account?.plan === "pro";
  const isCancelling = account?.plan === "pro_cancelling";
  const isTrial = isPro && account?.stripe_status === "trialing";
  const isStarter = !isPro && !isCancelling;
  const isAdmin = user?.role === "admin";

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", minHeight: "100vh", background: "#f8fafc" }}>
      {/* NAV */}
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.96)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em", color: "#f1f5f9" }}>CivicScale</span>
        </a>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <Link to="/broker/dashboard" style={{ fontSize: 13, color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>
            &larr; Dashboard
          </Link>
          <button onClick={handleLogout} style={{ background: "none", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "6px 14px", fontSize: 13, color: "#94a3b8", cursor: "pointer" }}>
            Sign Out
          </button>
        </div>
      </header>

      <div style={{ maxWidth: 720, margin: "0 auto", padding: "88px 24px 48px" }}>
        {/* Upgrade Toast */}
        {upgradeToast && (
          <div style={{ position: "fixed", top: 20, right: 24, zIndex: 1000, background: "#0D7377", color: "#fff", borderRadius: 10, padding: "14px 24px", fontSize: 14, fontWeight: 600, boxShadow: "0 4px 20px rgba(0,0,0,0.15)", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 18 }}>&#10003;</span> {upgradeMessage}
          </div>
        )}

        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 8px" }}>Account Settings</h1>
        <p style={{ color: "#64748b", fontSize: 14, marginBottom: 32 }}>{user?.email}</p>

        {/* Account Info Section */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1B3A5C", margin: "0 0 20px" }}>Account Information</h2>

          <div style={{ display: "grid", gap: 16 }}>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Contact Name</label>
              <input
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14, fontFamily: "inherit", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Firm Name</label>
              <input
                value={firmName}
                onChange={(e) => setFirmName(e.target.value)}
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14, fontFamily: "inherit", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Phone</label>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Optional"
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14, fontFamily: "inherit", boxSizing: "border-box" }}
              />
            </div>
            <div>
              <label style={{ fontSize: 13, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Email</label>
              <input
                value={user?.email || ""}
                disabled
                style={{ width: "100%", padding: "10px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 14, fontFamily: "inherit", background: "#f8fafc", color: "#94a3b8", boxSizing: "border-box" }}
              />
            </div>
          </div>

          <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 12 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: saving ? "default" : "pointer", opacity: saving ? 0.7 : 1 }}
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            {saveMsg && <span style={{ fontSize: 13, color: saveMsg.includes("Failed") ? "#dc2626" : "#16a34a", fontWeight: 500 }}>{saveMsg}</span>}
          </div>
        </div>

        {/* Team Management Section */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1B3A5C", margin: "0 0 20px" }}>Team Members</h2>

          {/* Current members */}
          <div style={{ marginBottom: 20 }}>
            {teamMembers.map((m) => (
              <div key={m.id || m.email} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #f1f5f9" }}>
                <div>
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 500, color: "#1B3A5C" }}>{m.full_name || m.email}</p>
                  <p style={{ margin: "2px 0 0", fontSize: 12, color: "#94a3b8" }}>{m.email}</p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {isAdmin && m.email !== user?.email ? (
                    <>
                      <select value={m.role} onChange={e => handleUpdateRole(m.id, e.target.value)}
                        style={{ border: "1px solid #d1d5db", borderRadius: 6, fontSize: 12, padding: "4px 8px",
                                 background: "#fff", color: "#475569" }}>
                        <option value="admin">Admin</option>
                        <option value="member">Member</option>
                        <option value="viewer">Viewer</option>
                      </select>
                      <button onClick={() => handleRemoveUser(m.id, m.email)}
                        style={{ background: "none", border: "none", color: "#dc2626", fontSize: 12,
                                 cursor: "pointer", padding: "4px 8px" }}>
                        Remove
                      </button>
                    </>
                  ) : (
                    <span style={{
                      fontSize: 11, fontWeight: 600, textTransform: "uppercase",
                      padding: "2px 8px", borderRadius: 10,
                      background: m.role === "admin" ? "#f0fdfa" : "#f1f5f9",
                      color: m.role === "admin" ? "#0D7377" : "#64748b",
                    }}>
                      {m.role}
                    </span>
                  )}
                </div>
              </div>
            ))}
            {teamMembers.length === 0 && (
              <p style={{ fontSize: 13, color: "#94a3b8", margin: 0 }}>No team members yet.</p>
            )}
          </div>

          {/* Invite form (admin only) */}
          {isAdmin && (
            <>
              <div style={{ display: "flex", gap: 10, alignItems: "flex-end" }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 13, fontWeight: 600, color: "#475569", display: "block", marginBottom: 4 }}>Invite team member</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleInviteTeamMember()}
                    placeholder="colleague@firm.com"
                    style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14, fontFamily: "inherit", boxSizing: "border-box" }}
                  />
                </div>
                <select value={inviteRole} onChange={e => setInviteRole(e.target.value)}
                  style={{ padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8, fontSize: 14, background: "#fff" }}>
                  <option value="member">Member</option>
                  <option value="viewer">Viewer</option>
                  <option value="admin">Admin</option>
                </select>
                <button
                  onClick={handleInviteTeamMember}
                  disabled={inviteLoading}
                  style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: inviteLoading ? "default" : "pointer", opacity: inviteLoading ? 0.7 : 1, whiteSpace: "nowrap" }}
                >
                  {inviteLoading ? "Sending..." : "Send Invite"}
                </button>
              </div>
              {inviteMsg && (
                <p style={{ fontSize: 13, marginTop: 8, marginBottom: 0, color: inviteMsg.includes("Failed") || inviteMsg.includes("valid") ? "#dc2626" : "#16a34a", fontWeight: 500 }}>{inviteMsg}</p>
              )}
            </>
          )}
        </div>

        {/* Plan & Billing Section */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1B3A5C", margin: "0 0 20px" }}>Plan & Billing</h2>

          {/* Starter Plan */}
          {isStarter && (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <span style={{ background: "#f1f5f9", color: "#475569", fontSize: 12, fontWeight: 700, padding: "3px 10px", borderRadius: 20, textTransform: "uppercase" }}>Starter</span>
                <span style={{ fontSize: 14, color: "#64748b" }}>Free &mdash; up to {account?.client_limit || 10} clients</span>
              </div>
              <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>
                You're on the free Starter plan with {account?.client_count || 0} of {account?.client_limit || 10} client slots used.
                Upgrade to Pro for unlimited clients, renewal prep reports, and Level 2 insights.
              </p>
              <button
                onClick={handleUpgrade}
                style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
              >
                Start Free Trial &mdash; $99/mo after 30 days &rarr;
              </button>
            </div>
          )}

          {/* Pro Trial */}
          {isTrial && (
            <div>
              <div style={{ display: "inline-block", padding: "4px 12px", borderRadius: 20, background: "#f0fdfa", border: "1px solid #99f6e4", marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#0D7377" }}>
                  Free Trial &mdash; {account?.trial_ends_at ? Math.max(0, Math.ceil((new Date(account.trial_ends_at) - new Date()) / (1000 * 60 * 60 * 24))) : 30} days remaining
                </span>
              </div>
              <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>
                Your free trial ends on {formatDate(account?.trial_ends_at)}. You won't be charged until then.
                After your trial, your Pro subscription continues at $99/mo.
              </p>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <button onClick={handlePortal} disabled={portalLoading}
                  style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: portalLoading ? "default" : "pointer", opacity: portalLoading ? 0.7 : 1 }}>
                  {portalLoading ? "Opening..." : "Manage billing"}
                </button>
                <button onClick={handlePortal} disabled={portalLoading}
                  style={{ background: "none", border: "none", color: "#94a3b8", fontSize: 13, cursor: portalLoading ? "default" : "pointer", textDecoration: "underline", padding: 0 }}>
                  Cancel trial
                </button>
              </div>
            </div>
          )}

          {/* Pro Plan (active, not trialing) */}
          {isPro && !isTrial && (
            <div>
              <div style={{ display: "inline-block", padding: "4px 12px", borderRadius: 20, background: "#f0fdfa", border: "1px solid #99f6e4", marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#0D7377" }}>Broker Pro</span>
              </div>
              {account?.subscription_period_end && (
                <p style={{ fontSize: 14, color: "#64748b", margin: "0 0 12px" }}>
                  Next billing date: {formatDate(account.subscription_period_end)}
                </p>
              )}
              <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>
                Your Pro subscription is active. You have {account?.client_count || 0} clients with no limit.
              </p>
              <button onClick={handlePortal} disabled={portalLoading}
                style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: portalLoading ? "default" : "pointer", opacity: portalLoading ? 0.7 : 1 }}>
                {portalLoading ? "Opening..." : "Manage billing"}
              </button>
            </div>
          )}

          {/* Pro Cancelling */}
          {isCancelling && (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <span style={{ background: "#fffbeb", color: "#92400e", fontSize: 12, fontWeight: 700, padding: "3px 10px", borderRadius: 20, textTransform: "uppercase" }}>Pro &mdash; Cancelling</span>
                <span style={{ fontSize: 14, color: "#64748b" }}>Access until {formatDate(account?.subscription_period_end)}</span>
              </div>
              <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>
                Your Pro subscription is set to cancel at the end of your billing period. You'll retain full Pro access until then, after which your account will revert to the Starter plan ({account?.client_limit || 10} client limit).
              </p>
              <button
                onClick={handleReactivate}
                disabled={reactivateLoading}
                style={{ background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, padding: "10px 24px", fontSize: 14, fontWeight: 600, cursor: reactivateLoading ? "default" : "pointer", opacity: reactivateLoading ? 0.7 : 1 }}
              >
                {reactivateLoading ? "Reactivating..." : "Reactivate Pro"}
              </button>
            </div>
          )}
        </div>

        {/* Share Parity Broker — Referral Section */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1B3A5C", margin: "0 0 4px" }}>Share Parity Broker</h2>
          <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 16px" }}>Brokers who find this useful tend to tell other brokers.</p>

          {/* Referral URL copy box */}
          {referralUrl && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  readOnly
                  value={referralUrl.replace("https://", "")}
                  style={{ flex: 1, padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 13, color: "#475569", background: "#f8fafc" }}
                />
                <button
                  onClick={async () => {
                    try { await navigator.clipboard.writeText(referralUrl); setReferralCopied(true); setTimeout(() => setReferralCopied(false), 2000); } catch {}
                  }}
                  style={{ padding: "8px 16px", background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}
                >
                  {referralCopied ? "Copied!" : "Copy Link"}
                </button>
              </div>
              <p style={{ fontSize: 12, color: "#94a3b8", margin: "6px 0 0" }}>
                {referralCount} broker{referralCount !== 1 ? "s" : ""} signed up using your link &middot; {convertedCount} active
              </p>
            </div>
          )}

          {/* Send colleague email */}
          <p style={{ fontSize: 13, fontWeight: 600, color: "#475569", margin: "0 0 10px" }}>Send a colleague an email</p>
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input
              value={colleagueEmail}
              onChange={e => setColleagueEmail(e.target.value)}
              placeholder="colleague@example.com"
              style={{ flex: 1, padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 13 }}
            />
            <input
              value={colleagueName}
              onChange={e => setColleagueName(e.target.value)}
              placeholder="First name (optional)"
              style={{ width: 150, padding: "8px 12px", border: "1px solid #e2e8f0", borderRadius: 8, fontSize: 13 }}
            />
            <button
              onClick={handleSendReferral}
              disabled={referralSending || !colleagueEmail.trim()}
              style={{ padding: "8px 16px", background: "#0D7377", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: referralSending ? "wait" : "pointer", opacity: (referralSending || !colleagueEmail.trim()) ? 0.6 : 1, whiteSpace: "nowrap" }}
            >
              {referralSending ? "Sending..." : "Send Introduction"}
            </button>
          </div>
          {referralMsg && (
            <p style={{ fontSize: 12, margin: "4px 0 0", color: referralMsg.includes("sent") ? "#16a34a" : "#dc2626", fontWeight: 500 }}>
              {referralMsg.includes("sent") ? "\u2713 " : ""}{referralMsg}
            </p>
          )}

          {/* Email preview toggle */}
          <button
            onClick={() => setShowEmailPreview(!showEmailPreview)}
            style={{ background: "none", border: "none", color: "#0D7377", fontSize: 12, cursor: "pointer", padding: "8px 0 0", textDecoration: "underline" }}
          >
            {showEmailPreview ? "Hide email preview" : "Preview the email"}
          </button>
          {showEmailPreview && (
            <div style={{ marginTop: 10, background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 8, padding: 16, fontSize: 13, color: "#475569", lineHeight: 1.7 }}>
              <p style={{ margin: "0 0 8px" }}><strong>Subject:</strong> {user?.full_name || "You"} thinks you should see this benefits platform</p>
              <hr style={{ border: "none", borderTop: "1px solid #e2e8f0", margin: "8px 0" }} />
              <p>Hi{colleagueName ? ` ${colleagueName}` : ""},</p>
              <p>{user?.full_name || "Your colleague"} at {company?.name || "your firm"} asked us to send you a quick note.</p>
              <p>They've been using <strong>Parity Broker</strong> to benchmark their book of business against MEPS-IC data and generate CAA data request letters — and thought it might be useful for your practice too.</p>
              <p>It benchmarks any client against industry/region/size peers in about 60 seconds. The CAA letter generator alone saves about an hour per renewal.</p>
              <p style={{ color: "#0D7377", fontWeight: 600 }}>[See a 4-step demo first →]</p>
              <p style={{ fontSize: 11, color: "#94a3b8", marginTop: 12 }}>This is the only email they'll receive unless they sign up.</p>
            </div>
          )}
        </div>

        {/* Data & Privacy Section */}
        <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1B3A5C", margin: "0 0 12px" }}>Data & Privacy</h2>
          <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>
            Your data is stored securely and never shared with third parties.
            You can request a full data export or account deletion at any time.
          </p>
          {isAdmin && (
            <button onClick={() => setShowDeleteModal(true)}
              style={{ background: "none", border: "1px solid #fecaca", borderRadius: 8,
                       padding: "8px 16px", color: "#dc2626", fontSize: 13, fontWeight: 600,
                       cursor: "pointer" }}>
              Request Data Deletion
            </button>
          )}
        </div>

        {/* Account created */}
        {account?.created_at && (
          <p style={{ fontSize: 12, color: "#94a3b8", textAlign: "center" }}>
            Account created {formatDate(account.created_at)}
          </p>
        )}
      </div>

      {/* Cancel Confirmation Modal */}
      {showCancelModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ background: "#fff", borderRadius: 16, padding: 32, maxWidth: 440, width: "90%", boxShadow: "0 20px 60px rgba(0,0,0,0.15)" }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: "0 0 12px" }}>Cancel Pro Subscription?</h3>
            <p style={{ fontSize: 14, color: "#64748b", lineHeight: 1.6, margin: "0 0 8px" }}>
              Your Pro access will continue until the end of your current billing period. After that:
            </p>
            <ul style={{ fontSize: 13, color: "#64748b", lineHeight: 1.8, paddingLeft: 20, margin: "0 0 20px" }}>
              <li>Your account will revert to the Starter plan (10-client limit)</li>
              <li>If you have more than 10 clients, you won't be able to add new ones</li>
              <li>Existing client data will be preserved</li>
            </ul>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button
                onClick={() => setShowCancelModal(false)}
                style={{ background: "#f1f5f9", color: "#475569", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}
              >
                Keep Pro
              </button>
              <button
                onClick={handleCancel}
                disabled={cancelLoading}
                style={{ background: "#dc2626", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: cancelLoading ? "default" : "pointer", opacity: cancelLoading ? 0.7 : 1 }}
              >
                {cancelLoading ? "Cancelling..." : "Confirm Cancellation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deletion Confirmation Modal */}
      {showDeleteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 2000, display: "flex", alignItems: "center", justifyContent: "center" }}
             onClick={() => { setShowDeleteModal(false); setDeleteMsg(""); setDeleteConfirmName(""); }}>
          <div onClick={e => e.stopPropagation()}
               style={{ background: "#fff", borderRadius: 16, padding: 32, maxWidth: 440, width: "90%", boxShadow: "0 20px 60px rgba(0,0,0,0.15)" }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: "#dc2626", margin: "0 0 8px" }}>
              Request Data Deletion
            </h3>
            <p style={{ fontSize: 14, color: "#64748b", lineHeight: 1.6, marginBottom: 16 }}>
              This will permanently delete all your firm's data including client benchmarks,
              reports, and team accounts. This action cannot be undone.
            </p>
            <p style={{ fontSize: 13, color: "#64748b", marginBottom: 8 }}>
              Type <strong style={{ color: "#1B3A5C" }}>{company?.name}</strong> to confirm:
            </p>
            <input value={deleteConfirmName} onChange={e => setDeleteConfirmName(e.target.value)}
              placeholder="Type company name"
              style={{ width: "100%", padding: "10px 12px", border: "1px solid #d1d5db", borderRadius: 8,
                       fontSize: 14, marginBottom: 16, boxSizing: "border-box" }} />
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <button onClick={() => { setShowDeleteModal(false); setDeleteMsg(""); setDeleteConfirmName(""); }}
                style={{ background: "#f1f5f9", color: "#475569", border: "none", borderRadius: 8,
                         padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer" }}>
                Cancel
              </button>
              <button onClick={handleDeletionRequest}
                disabled={deleting || deleteConfirmName.trim().toLowerCase() !== (company?.name || "").trim().toLowerCase()}
                style={{ background: "#dc2626", color: "#fff", border: "none", borderRadius: 8,
                         padding: "10px 20px", fontSize: 14, fontWeight: 600,
                         cursor: deleting ? "not-allowed" : "pointer",
                         opacity: (deleting || deleteConfirmName.trim().toLowerCase() !== (company?.name || "").trim().toLowerCase()) ? 0.5 : 1 }}>
                {deleting ? "Submitting..." : "Delete All Data"}
              </button>
            </div>
            {deleteMsg && (
              <p style={{ fontSize: 13, textAlign: "center", marginTop: 12,
                          color: deleteMsg.includes("submitted") ? "#16a34a" : "#dc2626", fontWeight: 500 }}>{deleteMsg}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function BrokerAccountPage() {
  return (
    <AuthGate product="broker">
      <BrokerAccountInner />
    </AuthGate>
  );
}
