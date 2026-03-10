import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthGate from "./AuthGate";
import { LogoIcon } from "./CivicScaleHomepage.jsx";

const API = import.meta.env.VITE_API_URL || "https://parity-poc-api.onrender.com";

function EmployerAccountInner() {
  const navigate = useNavigate();
  const { user, company, token, logout, isAdmin, refetch } = useAuth();
  const [subscription, setSubscription] = useState(null);
  const [subActive, setSubActive] = useState(false);
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  // Company edit fields — pre-populated from auth context
  const [companyName, setCompanyName] = useState(company?.name || "");
  const [industry, setIndustry] = useState(company?.industry || "");
  const [state, setState] = useState(company?.state || "");
  const [sizeBand, setSizeBand] = useState(company?.size_band || "");

  // Invite modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");

  useEffect(() => {
    if (company) {
      setCompanyName(company.name || "");
      setIndustry(company.industry || "");
      setState(company.state || "");
      setSizeBand(company.size_band || "");
    }
  }, [company]);

  const fetchData = useCallback(async () => {
    if (!user?.email || !token) return;
    setLoading(true);
    try {
      const [subRes, usersRes] = await Promise.all([
        fetch(`${API}/subscription-status?email=${encodeURIComponent(user.email)}`),
        fetch(`${API}/api/auth/users`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      const subData = await subRes.json();
      const usersData = await usersRes.json();
      setSubscription(subData.subscription);
      setSubActive(subData.active === true);
      setTeamMembers(usersData.users || []);
    } catch (err) {
      console.error("Failed to fetch account data:", err);
    }
    setLoading(false);
  }, [user?.email, token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSaveCompany = async () => {
    setSaving(true);
    setSaveMsg("");
    try {
      const res = await fetch(`${API}/api/auth/company`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: companyName.trim() || null,
          industry: industry || null,
          state: state || null,
          size_band: sizeBand || null,
        }),
      });
      if (!res.ok) { const d = await res.json(); setSaveMsg(d.detail || "Failed to save."); return; }
      setSaveMsg("Saved!");
      refetch();
      setTimeout(() => setSaveMsg(""), 3000);
    } catch {
      setSaveMsg("Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  const handleBillingPortal = async () => {
    try {
      const res = await fetch(`${API}/billing-portal?email=${encodeURIComponent(user.email)}`, {
        method: "POST",
      });
      const data = await res.json();
      if (data.portal_url) window.location.href = data.portal_url;
      else alert(data.detail || "No billing account found.");
    } catch {
      alert("Failed to open billing portal.");
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail.includes("@")) { setInviteMsg("Enter a valid email."); return; }
    setInviting(true);
    setInviteMsg("");
    try {
      const res = await fetch(`${API}/api/auth/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ invited_email: inviteEmail.trim().toLowerCase(), role: inviteRole }),
      });
      const data = await res.json();
      if (!res.ok) { setInviteMsg(data.detail || "Failed."); return; }
      setInviteMsg("Invitation sent!");
      setInviteEmail("");
      setTimeout(() => { setShowInviteModal(false); setInviteMsg(""); }, 2000);
      fetchData();
    } catch {
      setInviteMsg("Failed to send invite.");
    } finally {
      setInviting(false);
    }
  };

  const handleUpdateRole = async (userId, newRole) => {
    try {
      await fetch(`${API}/api/auth/users/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ role: newRole }),
      });
      fetchData();
    } catch { /* ignore */ }
  };

  const handleRemoveUser = async (userId, email) => {
    if (!confirm(`Remove ${email} from this account?`)) return;
    try {
      await fetch(`${API}/api/auth/users/${userId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      fetchData();
    } catch { /* ignore */ }
  };

  const handleSignOut = async () => {
    await logout();
    navigate("/billing/employer");
  };

  const inputStyle = {
    width: "100%", padding: "10px 14px", background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "white",
    fontSize: 14, marginBottom: 12, boxSizing: "border-box",
  };

  const sectionStyle = {
    background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 12, padding: 24, marginBottom: 24,
  };

  const tierColors = { starter: "#3B82F6", growth: "#8B5CF6", scale: "#F59E0B" };
  const tierLabel = subscription?.tier ? subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1) : "Free";
  const tierColor = tierColors[subscription?.tier] || "#6B7280";

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1e", color: "white" }}>
      {/* Header */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "16px 32px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <LogoIcon size={28} />
          <span style={{ fontSize: 16, fontWeight: 700, color: "#0d9488" }}>Parity Employer</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Link to="/billing/employer/dashboard"
            style={{ color: "#0d9488", fontSize: 13, textDecoration: "none" }}>
            Dashboard
          </Link>
          <button onClick={handleSignOut}
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                     borderRadius: 6, padding: "6px 14px", color: "rgba(255,255,255,0.6)",
                     fontSize: 13, cursor: "pointer" }}>
            Sign Out
          </button>
        </div>
      </nav>

      <div style={{ maxWidth: 720, margin: "0 auto", padding: "32px 24px" }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8, color: "white" }}>Account Settings</h1>
        <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 14, marginBottom: 32 }}>{user?.email}</p>

        {/* Section 1: Company Information */}
        <div style={sectionStyle}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
            Company Information
          </h2>
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>Company Name</label>
          <input value={companyName} onChange={e => setCompanyName(e.target.value)}
            disabled={!isAdmin} style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6 }} />
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>Industry</label>
          <input value={industry} onChange={e => setIndustry(e.target.value)}
            disabled={!isAdmin} style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6 }} />
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>State</label>
          <input value={state} onChange={e => setState(e.target.value)}
            disabled={!isAdmin} style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6 }} />
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>Company Size</label>
          <input value={sizeBand} onChange={e => setSizeBand(e.target.value)}
            disabled={!isAdmin} style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6 }} />
          {isAdmin && (
            <button onClick={handleSaveCompany} disabled={saving}
              style={{ background: "#0d9488", color: "white", border: "none", borderRadius: 8,
                       padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: saving ? "not-allowed" : "pointer",
                       opacity: saving ? 0.7 : 1, marginTop: 4 }}>
              {saving ? "Saving..." : "Save Changes"}
            </button>
          )}
          {saveMsg && (
            <span style={{ marginLeft: 12, fontSize: 13, color: saveMsg === "Saved!" ? "#10B981" : "#f87171" }}>
              {saveMsg}
            </span>
          )}
        </div>

        {/* Section 2: Plan & Billing */}
        <div style={sectionStyle}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
            Plan & Billing
          </h2>
          {!subActive ? (
            <div>
              <div style={{ color: "rgba(255,255,255,0.5)", marginBottom: 16 }}>
                No active subscription
              </div>
              <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 14, marginBottom: 20 }}>
                Subscribe to unlock claims analysis, benchmarking, and plan grading.
              </p>
              <Link to="/billing/employer"
                style={{ display: "inline-block", background: "#0d9488", color: "white",
                         padding: "10px 20px", borderRadius: 8, textDecoration: "none",
                         fontWeight: 600, fontSize: 14 }}>
                View Plans
              </Link>
            </div>
          ) : (
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <span style={{ background: tierColor, color: "white", fontSize: 12, fontWeight: 700,
                               padding: "3px 12px", borderRadius: 20 }}>{tierLabel}</span>
                <span style={{ color: "#10B981", fontWeight: 600, fontSize: 14 }}>Active</span>
              </div>
              {subscription?.current_period_end && (
                <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, marginBottom: 12 }}>
                  Renews {new Date(subscription.current_period_end).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
                </p>
              )}
              <button onClick={handleBillingPortal}
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                         borderRadius: 8, padding: "10px 20px", color: "white", fontSize: 14,
                         fontWeight: 600, cursor: "pointer" }}>
                Manage Billing
              </button>
            </div>
          )}
        </div>

        {/* Section 3: Team Members */}
        <div style={sectionStyle}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "rgba(255,255,255,0.9)" }}>
              Team Members
            </h2>
            {isAdmin && (
              <button onClick={() => setShowInviteModal(true)}
                style={{ background: "#0d9488", color: "white", border: "none", borderRadius: 8,
                         padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                Invite
              </button>
            )}
          </div>
          {teamMembers.map(m => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                                     padding: "12px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "rgba(255,255,255,0.9)" }}>
                  {m.full_name || m.email}
                </div>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)" }}>{m.email}</div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {isAdmin && m.email !== user?.email ? (
                  <>
                    <select value={m.role} onChange={e => handleUpdateRole(m.id, e.target.value)}
                      style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                               borderRadius: 6, color: "white", fontSize: 12, padding: "4px 8px" }}>
                      <option value="admin">Admin</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>
                    <button onClick={() => handleRemoveUser(m.id, m.email)}
                      style={{ background: "none", border: "none", color: "#EF4444", fontSize: 12,
                               cursor: "pointer", padding: "4px 8px" }}>
                      Remove
                    </button>
                  </>
                ) : (
                  <span style={{ fontSize: 11, fontWeight: 600, color: m.role === "admin" ? "#F59E0B" : "#6B7280",
                                 textTransform: "uppercase", letterSpacing: 1 }}>
                    {m.role}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Section 4: Data & Privacy */}
        <div style={sectionStyle}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
            Data & Privacy
          </h2>
          <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, lineHeight: 1.6 }}>
            Your claims data and benchmark results are encrypted at rest and in transit. We use Supabase
            (PostgreSQL) with row-level security policies. Your data is never shared with third parties
            or used to train AI models. You can request a full data export or account deletion at any time
            by contacting support@civicscale.ai.
          </p>
        </div>
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000,
                      display: "flex", alignItems: "center", justifyContent: "center" }}
             onClick={() => setShowInviteModal(false)}>
          <div onClick={e => e.stopPropagation()}
               style={{ background: "#1a1f2e", border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 16, padding: 32, maxWidth: 400, width: "100%" }}>
            <h3 style={{ color: "white", fontSize: 18, fontWeight: 600, marginBottom: 16, marginTop: 0 }}>
              Invite Team Member
            </h3>
            <input type="email" placeholder="colleague@company.com" value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              style={{ width: "100%", padding: "12px 16px", background: "rgba(255,255,255,0.05)",
                       border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "white",
                       fontSize: 14, marginBottom: 12, boxSizing: "border-box" }} />
            <select value={inviteRole} onChange={e => setInviteRole(e.target.value)}
              style={{ width: "100%", padding: "12px 16px", background: "rgba(255,255,255,0.05)",
                       border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "white",
                       fontSize: 14, marginBottom: 16, boxSizing: "border-box" }}>
              <option value="member">Member</option>
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
            <button onClick={handleInvite} disabled={inviting}
              style={{ width: "100%", padding: 12, background: "#0d9488", color: "white",
                       border: "none", borderRadius: 8, fontSize: 14, fontWeight: 600,
                       cursor: inviting ? "not-allowed" : "pointer", opacity: inviting ? 0.7 : 1 }}>
              {inviting ? "Sending..." : "Send Invitation"}
            </button>
            {inviteMsg && (
              <p style={{ color: inviteMsg.includes("sent") ? "#10B981" : "#f87171",
                          fontSize: 13, textAlign: "center", marginTop: 12 }}>{inviteMsg}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function EmployerAccountPage() {
  const navigate = useNavigate();

  return (
    <AuthGate product="employer" onNeedsCompany={() => navigate("/billing/employer/signup")}>
      <EmployerAccountInner />
    </AuthGate>
  );
}
