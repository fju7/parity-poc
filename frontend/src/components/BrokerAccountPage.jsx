import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthGate from "./AuthGate";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
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

  const authHeaders = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    if (!token) return;
    fetchAccount();
    fetchTeam();
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
      const res = await fetch(`${API}/api/broker/account`, { headers: authHeaders });
      const data = await res.json();
      setAccount(data);
      setContactName(data.contact_name || "");
      setFirmName(data.firm_name || "");
      setPhone(data.phone || "");
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
  const isStarter = !isPro && !isCancelling;
  const isAdmin = user?.role === "admin";

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", minHeight: "100vh", background: "#f8fafc" }}>
      {/* NAV */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div className="cs-nav-links">
          <Link to="/broker/dashboard" style={{ fontSize: 13, color: "#0D7377", textDecoration: "none", fontWeight: 600 }}>
            &larr; Dashboard
          </Link>
          <button onClick={handleLogout} style={{ background: "none", border: "1px solid #e2e8f0", borderRadius: 6, padding: "6px 14px", fontSize: 13, color: "#64748b", cursor: "pointer" }}>
            Sign Out
          </button>
        </div>
      </nav>

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
                Upgrade to Pro &mdash; $99/mo &rarr;
              </button>
            </div>
          )}

          {/* Pro Plan */}
          {isPro && (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                <span style={{ background: "#f0fdfa", color: "#0D7377", fontSize: 12, fontWeight: 700, padding: "3px 10px", borderRadius: 20, textTransform: "uppercase" }}>Pro</span>
                <span style={{ fontSize: 14, color: "#64748b" }}>$99/mo &mdash; Unlimited clients</span>
              </div>
              <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6, margin: "0 0 16px" }}>
                Your Pro subscription is active. You have {account?.client_count || 0} clients with no limit.
              </p>
              <button
                onClick={() => setShowCancelModal(true)}
                style={{ background: "none", color: "#dc2626", border: "1px solid #fecaca", borderRadius: 8, padding: "8px 20px", fontSize: 13, fontWeight: 500, cursor: "pointer" }}
              >
                Cancel Subscription
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
