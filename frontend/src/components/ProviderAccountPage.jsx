import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthGate from "./AuthGate";
import { LogoIcon } from "./CivicScaleHomepage.jsx";

import { API_BASE as API } from "../lib/apiBase";

const isProviderSubdomain = window.location.hostname === 'provider.civicscale.ai' || window.location.hostname === 'staging-provider.civicscale.ai';

function ProviderAccountInner() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, company, token, logout, isAdmin, refetch } = useAuth();
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  // Practice edit fields — loaded from provider_profiles
  const [practiceName, setPracticeName] = useState("");
  const [specialty, setSpecialty] = useState("");
  const [npi, setNpi] = useState("");
  const [zipCode, setZipCode] = useState("");

  // Invite modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");

  // Deletion modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmName, setDeleteConfirmName] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState("");

  // Billing
  const [portalLoading, setPortalLoading] = useState(false);
  const [subscription, setSubscription] = useState(null);

  // Checkout success polling
  const [checkoutConfirmed, setCheckoutConfirmed] = useState(false);

  const authHeaders = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    if (!user?.email || !token) return;
    setLoading(true);
    try {
      const [usersRes, profileRes, subRes] = await Promise.all([
        fetch(`${API}/api/auth/users`, { headers: authHeaders }),
        fetch(`${API}/api/provider/my-profile`, { headers: authHeaders }),
        fetch(`${API}/api/provider/my-subscription`, { headers: authHeaders }),
      ]);
      const usersData = await usersRes.json();
      setTeamMembers(usersData.users || []);

      if (profileRes.ok) {
        const profileData = await profileRes.json();
        if (profileData.profile) {
          setPracticeName(profileData.profile.practice_name || "");
          setSpecialty(profileData.profile.specialty || "");
          setNpi(profileData.profile.npi || "");
          setZipCode(profileData.profile.zip_code || "");
        }
      }

      if (subRes.ok) {
        const subData = await subRes.json();
        setSubscription(subData.subscription || null);
      }
    } catch (err) {
      console.error("Failed to fetch account data:", err);
    }
    setLoading(false);
  }, [user?.email, token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Poll trial-status after checkout until subscription_active=true
  useEffect(() => {
    if (searchParams.get("checkout_success") !== "1" || checkoutConfirmed) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/provider/trial-status`, { headers: authHeaders });
        if (res.ok) {
          const data = await res.json();
          if (data.subscription_active) {
            setCheckoutConfirmed(true);
            clearInterval(interval);
            fetchData(); // refresh subscription display
          }
        }
      } catch { /* ignore */ }
    }, 3000);
    return () => clearInterval(interval);
  }, [searchParams, checkoutConfirmed, token]);

  const handleSaveProfile = async () => {
    if (!practiceName.trim()) { setSaveMsg("Practice name is required."); return; }
    setSaving(true);
    setSaveMsg("");
    try {
      const res = await fetch(`${API}/api/provider/save-profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({
          practice_name: practiceName.trim(),
          specialty: specialty || "",
          npi: npi.trim() || "",
          zip_code: zipCode.trim() || "",
        }),
      });
      if (!res.ok) { const d = await res.json(); setSaveMsg(d.detail || "Failed to save."); return; }
      setSaveMsg("Saved!");
      setTimeout(() => setSaveMsg(""), 3000);
    } catch {
      setSaveMsg("Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  const handleBillingPortal = async () => {
    setPortalLoading(true);
    try {
      const res = await fetch(`${API}/api/provider/subscription/portal`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to open billing portal");
        return;
      }
      const json = await res.json();
      if (json.portal_url) window.location.href = json.portal_url;
    } catch {
      alert("Failed to open billing portal.");
    } finally {
      setPortalLoading(false);
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail.includes("@")) { setInviteMsg("Enter a valid email."); return; }
    setInviting(true);
    setInviteMsg("");
    try {
      const res = await fetch(`${API}/api/auth/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
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

  const handleUpdateRole = async (userId, newRole) => {
    try {
      await fetch(`${API}/api/auth/users/${userId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders },
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
        headers: authHeaders,
      });
      fetchData();
    } catch { /* ignore */ }
  };

  const handleSignOut = async () => {
    await logout();
    navigate(isProviderSubdomain ? "/" : "/billing/provider");
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

  const SPECIALTIES = [
    "Internal Medicine", "Family Medicine", "Cardiology", "Orthopedics",
    "Dermatology", "Radiology", "Pathology/Lab", "Other",
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1e", color: "white" }}>
      {/* Header */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "16px 32px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <LogoIcon size={28} />
          <span style={{ fontSize: 16, fontWeight: 700, color: "#0d9488" }}>Parity Provider</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Link to={isProviderSubdomain ? "/dashboard" : "/provider/dashboard"}
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

        {searchParams.get("checkout_success") === "1" && (
          <div style={{
            background: checkoutConfirmed ? "rgba(20,184,166,0.12)" : "rgba(59,130,246,0.12)",
            border: `1px solid ${checkoutConfirmed ? "rgba(20,184,166,0.3)" : "rgba(59,130,246,0.3)"}`,
            borderRadius: 8, padding: 16, marginBottom: 24,
            color: checkoutConfirmed ? "#14b8a6" : "#60a5fa", fontSize: 14,
          }}>
            {checkoutConfirmed
              ? "Your subscription is now active! You have full access to Parity Provider."
              : "Confirming your subscription… this may take a few seconds."}
          </div>
        )}

        {/* Section 1: Practice Information */}
        <div style={sectionStyle}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
            Practice Information
          </h2>
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>Practice Name</label>
          <input value={practiceName} onChange={e => setPracticeName(e.target.value)}
            disabled={!isAdmin} style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6 }} />
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>Specialty</label>
          <select value={specialty} onChange={e => setSpecialty(e.target.value)}
            disabled={!isAdmin}
            style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6, appearance: "auto" }}>
            <option value="">Select a specialty</option>
            {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>NPI Number</label>
          <input value={npi} onChange={e => setNpi(e.target.value)}
            disabled={!isAdmin} maxLength={10} placeholder="10-digit NPI"
            style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6 }} />
          <label style={{ fontSize: 12, color: "rgba(255,255,255,0.4)", display: "block", marginBottom: 4 }}>ZIP Code</label>
          <input value={zipCode} onChange={e => setZipCode(e.target.value)}
            disabled={!isAdmin} maxLength={5} placeholder="e.g. 33701"
            style={{ ...inputStyle, opacity: isAdmin ? 1 : 0.6 }} />
          {isAdmin && (
            <button onClick={handleSaveProfile} disabled={saving}
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

        {/* Section 2: Subscription */}
        <div style={sectionStyle}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, marginTop: 0, color: "rgba(255,255,255,0.9)" }}>
            Subscription
          </h2>

          {/* Trial active */}
          {subscription && subscription.stripe_status === "trialing" ? (
            <div>
              <div style={{ display: "inline-block", padding: "4px 12px", borderRadius: 20,
                           background: "rgba(13,148,136,0.15)", border: "1px solid rgba(13,148,136,0.3)", marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#0d9488" }}>
                  Free Trial &mdash; {subscription.trial_ends_at ? Math.max(0, Math.ceil((new Date(subscription.trial_ends_at) - new Date()) / (1000 * 60 * 60 * 24))) : 30} days remaining
                </span>
              </div>
              <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, margin: "0 0 16px", lineHeight: 1.6 }}>
                Your free trial ends on {subscription.trial_ends_at ? new Date(subscription.trial_ends_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) : ""}.
                You won't be charged until then. After your trial, monitoring continues at $99/mo.
              </p>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <button onClick={handleBillingPortal} disabled={portalLoading}
                  style={{ background: "#0d9488", border: "none", borderRadius: 8, padding: "10px 20px",
                           color: "white", fontSize: 14, fontWeight: 600,
                           cursor: portalLoading ? "not-allowed" : "pointer", opacity: portalLoading ? 0.7 : 1 }}>
                  {portalLoading ? "Opening..." : "Manage billing"}
                </button>
                <button onClick={handleBillingPortal} disabled={portalLoading}
                  style={{ background: "none", border: "none", color: "rgba(255,255,255,0.3)", fontSize: 13,
                           cursor: portalLoading ? "default" : "pointer", textDecoration: "underline", padding: 0 }}>
                  Cancel trial
                </button>
              </div>
            </div>

          /* Active paid subscription */
          ) : subscription && subscription.status === "active" ? (
            <div>
              <div style={{ display: "inline-block", padding: "4px 12px", borderRadius: 20,
                           background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)", marginBottom: 12 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#10B981" }}>
                  Monthly Monitoring
                </span>
              </div>
              {subscription.current_period_end && (
                <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, margin: "0 0 12px" }}>
                  Next billing date: {new Date(subscription.current_period_end).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
                </p>
              )}
              <button onClick={handleBillingPortal} disabled={portalLoading}
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                         borderRadius: 8, padding: "10px 20px", color: "white", fontSize: 14,
                         fontWeight: 600, cursor: portalLoading ? "not-allowed" : "pointer",
                         opacity: portalLoading ? 0.7 : 1 }}>
                {portalLoading ? "Opening..." : "Manage billing"}
              </button>
            </div>

          /* No subscription */
          ) : (
            <div>
              <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, margin: "0 0 12px" }}>
                No active subscription. Run a free audit to get started, then upgrade to monthly monitoring.
              </p>
              <Link to="/audit"
                style={{ display: "inline-block", padding: "10px 20px", background: "#0d9488",
                         color: "white", borderRadius: 8, fontSize: 14, fontWeight: 600,
                         textDecoration: "none" }}>
                Start Free Audit
              </Link>
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
            Your claims data and audit results are encrypted at rest and in transit. We use Supabase
            (PostgreSQL) with row-level security policies. Your data is never shared with third parties
            or used to train AI models. You can request a full data export or account deletion at any time.
          </p>
          {isAdmin && (
            <button onClick={() => setShowDeleteModal(true)}
              style={{ background: "none", border: "1px solid rgba(248,113,113,0.3)", borderRadius: 8,
                       padding: "8px 16px", color: "#f87171", fontSize: 13, fontWeight: 600,
                       cursor: "pointer", marginTop: 8 }}>
              Request Data Deletion
            </button>
          )}
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
            <input type="email" placeholder="colleague@yourpractice.com" value={inviteEmail}
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

      {/* Deletion Confirmation Modal */}
      {showDeleteModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000,
                      display: "flex", alignItems: "center", justifyContent: "center" }}
             onClick={() => { setShowDeleteModal(false); setDeleteMsg(""); setDeleteConfirmName(""); }}>
          <div onClick={e => e.stopPropagation()}
               style={{ background: "#1a1f2e", border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 16, padding: 32, maxWidth: 440, width: "100%" }}>
            <h3 style={{ color: "#f87171", fontSize: 18, fontWeight: 600, marginBottom: 8, marginTop: 0 }}>
              Request Data Deletion
            </h3>
            <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 14, lineHeight: 1.6, marginBottom: 16 }}>
              This will permanently delete all your practice data including audit results,
              contract analyses, and team accounts. This action cannot be undone.
            </p>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, marginBottom: 8 }}>
              Type <strong style={{ color: "white" }}>{company?.name}</strong> to confirm:
            </p>
            <input value={deleteConfirmName} onChange={e => setDeleteConfirmName(e.target.value)}
              placeholder="Type practice name"
              style={{ width: "100%", padding: "12px 16px", background: "rgba(255,255,255,0.05)",
                       border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "white",
                       fontSize: 14, marginBottom: 16, boxSizing: "border-box" }} />
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => { setShowDeleteModal(false); setDeleteMsg(""); setDeleteConfirmName(""); }}
                style={{ flex: 1, padding: 12, background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.6)",
                         border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, fontSize: 14, cursor: "pointer" }}>
                Cancel
              </button>
              <button onClick={handleDeletionRequest}
                disabled={deleting || deleteConfirmName.trim().toLowerCase() !== (company?.name || "").trim().toLowerCase()}
                style={{ flex: 1, padding: 12, background: "#DC2626", color: "white",
                         border: "none", borderRadius: 8, fontSize: 14, fontWeight: 600,
                         cursor: deleting ? "not-allowed" : "pointer",
                         opacity: (deleting || deleteConfirmName.trim().toLowerCase() !== (company?.name || "").trim().toLowerCase()) ? 0.5 : 1 }}>
                {deleting ? "Submitting..." : "Delete All Data"}
              </button>
            </div>
            {deleteMsg && (
              <p style={{ color: deleteMsg.includes("submitted") ? "#10B981" : "#f87171",
                          fontSize: 13, textAlign: "center", marginTop: 12 }}>{deleteMsg}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ProviderAccountPage() {
  const navigate = useNavigate();

  return (
    <AuthGate product="provider" onNeedsCompany={() => navigate(isProviderSubdomain ? "/signup" : "/provider/signup")}>
      <ProviderAccountInner />
    </AuthGate>
  );
}
