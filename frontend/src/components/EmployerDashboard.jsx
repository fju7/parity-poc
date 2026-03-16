import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthGate from "./AuthGate";
import EmployerTrialBanner from "./EmployerTrialBanner";
import { LogoIcon } from "./CivicScaleHomepage.jsx";

import { API_BASE as API } from "../lib/apiBase";
function fmt$(n) {
  if (n == null) return "\u2014";
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function EmployerDashboardInner() {
  const navigate = useNavigate();
  const { user, company, token, logout, isAdmin, refetch } = useAuth();
  const [claims, setClaims] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState("");
  const [trialToast, setTrialToast] = useState(false);

  // Handle ?trial_started=true — poll until plan shows "trial"
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("trial_started") === "true") {
      window.history.replaceState({}, "", "/billing/employer/dashboard");
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          await refetch();
          if (company?.plan === "trial" || attempts >= 10) {
            setTrialToast(true);
            setTimeout(() => setTrialToast(false), 6000);
            clearInterval(poll);
          }
        } catch {
          clearInterval(poll);
        }
      }, 2000);
      return () => clearInterval(poll);
    }
  }, [company?.plan]);

  const fetchData = useCallback(async () => {
    if (!user?.email || !token) return;
    setLoading(true);
    try {
      const [claimsRes, usersRes] = await Promise.all([
        fetch(`${API}/claims-history?email=${encodeURIComponent(user.email)}`),
        fetch(`${API}/api/auth/users`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      const claimsData = await claimsRes.json();
      const usersData = await usersRes.json();
      setClaims(claimsData.uploads || []);
      setTeamMembers(usersData.users || []);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    }
    setLoading(false);
  }, [user?.email, token]);

  useEffect(() => { fetchData(); }, [fetchData]);

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
      if (!res.ok) { setInviteMsg(data.detail || "Failed to send invite."); return; }
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

  const handleSignOut = async () => {
    await logout();
    navigate("/billing/employer");
  };

  const plan = company?.plan || "free";
  const trialEndsAt = company?.trial_ends_at;
  const daysRemaining = trialEndsAt ? Math.max(0, Math.ceil(
    (new Date(trialEndsAt) - new Date()) / (1000 * 60 * 60 * 24)
  )) : null;

  // Dynamic billing action card label
  const billingLabel = plan === "free" ? "Start Free Trial"
    : plan === "trial" ? `Trial \u2014 ${daysRemaining} day${daysRemaining !== 1 ? "s" : ""} left`
    : plan === "pro" ? "Pro Plan \u2014 Active"
    : plan === "read_only" || plan === "cancelled" ? "Resubscribe"
    : "Account & Billing";

  const quickActions = [
    { label: "Run Benchmark", desc: "Compare your plan costs to market", path: "/billing/employer/benchmark", icon: "\u{1F4CA}" },
    { label: "Upload Claims", desc: "Analyze claims against Medicare rates", path: "/billing/employer/claims-check", icon: "\u{1F4C4}" },
    { label: "Grade My Plan", desc: "Score your plan benefits", path: "/billing/employer/scorecard", icon: "\u{1F3AF}" },
    { label: billingLabel, desc: "Manage subscription and team", path: "/billing/employer/account", icon: "\u2699\uFE0F" },
  ];

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1e", color: "white" }}>
      {/* Trial toast */}
      {trialToast && (
        <div style={{ position: "fixed", top: 20, right: 24, zIndex: 1000, background: "#0D7377",
                      color: "#fff", borderRadius: 10, padding: "14px 24px", fontSize: 14,
                      fontWeight: 600, boxShadow: "0 4px 20px rgba(0,0,0,0.15)",
                      display: "flex", alignItems: "center", gap: 8, maxWidth: 440 }}>
          <span style={{ fontSize: 18 }}>&#10003;</span>
          Your 30-day trial has started. Full access is now active — no charge until day 30.
        </div>
      )}

      {/* Header */}
      <nav style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "16px 32px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <LogoIcon size={28} />
          <span style={{ fontSize: 16, fontWeight: 700, color: "#0d9488" }}>Parity Employer</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ color: "rgba(255,255,255,0.6)", fontSize: 14 }}>
            {company?.name}
          </span>
          <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 13 }}>
            {user?.full_name || user?.email}
          </span>
          <Link to="/billing/employer/account"
            style={{ color: "#0d9488", fontSize: 13, textDecoration: "none" }}>
            Account
          </Link>
          <button onClick={handleSignOut}
            style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                     borderRadius: 6, padding: "6px 14px", color: "rgba(255,255,255,0.6)",
                     fontSize: 13, cursor: "pointer" }}>
            Sign Out
          </button>
        </div>
      </nav>

      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "32px 24px" }}>
        {/* Trial Banner */}
        <EmployerTrialBanner />

        {/* Quick actions */}
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16, color: "rgba(255,255,255,0.9)" }}>
          Quick Actions
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                      gap: 16, marginBottom: 40 }}>
          {quickActions.map(a => (
            <Link key={a.path} to={a.path} style={{ textDecoration: "none" }}>
              <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                            borderRadius: 12, padding: "24px 20px", cursor: "pointer",
                            transition: "border-color 0.2s" }}
                   onMouseEnter={e => e.currentTarget.style.borderColor = "rgba(13,148,136,0.4)"}
                   onMouseLeave={e => e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"}>
                <div style={{ fontSize: 24, marginBottom: 8 }}>{a.icon}</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "white", marginBottom: 4 }}>{a.label}</div>
                <div style={{ fontSize: 13, color: "rgba(255,255,255,0.4)" }}>{a.desc}</div>
              </div>
            </Link>
          ))}
        </div>

        {/* Claims history */}
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16, color: "rgba(255,255,255,0.9)" }}>
          Claims History
        </h2>
        {claims.length === 0 ? (
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                        borderRadius: 12, padding: 32, textAlign: "center" }}>
            <p style={{ color: "rgba(255,255,255,0.4)", marginBottom: 16 }}>No claims uploaded yet.</p>
            <Link to="/billing/employer/claims-check"
              style={{ color: "#0d9488", fontWeight: 600, textDecoration: "none" }}>
              Upload New File
            </Link>
          </div>
        ) : (
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                        borderRadius: 12, overflow: "hidden", marginBottom: 40 }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                  <th style={{ padding: "12px 16px", textAlign: "left", fontSize: 12, color: "rgba(255,255,255,0.4)", fontWeight: 600 }}>Date</th>
                  <th style={{ padding: "12px 16px", textAlign: "left", fontSize: 12, color: "rgba(255,255,255,0.4)", fontWeight: 600 }}>File</th>
                  <th style={{ padding: "12px 16px", textAlign: "right", fontSize: 12, color: "rgba(255,255,255,0.4)", fontWeight: 600 }}>Claims</th>
                  <th style={{ padding: "12px 16px", textAlign: "right", fontSize: 12, color: "rgba(255,255,255,0.4)", fontWeight: 600 }}>Excess Identified</th>
                </tr>
              </thead>
              <tbody>
                {claims.map(c => (
                  <tr key={c.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                    <td style={{ padding: "12px 16px", fontSize: 13, color: "rgba(255,255,255,0.7)" }}>
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ padding: "12px 16px", fontSize: 13, color: "rgba(255,255,255,0.7)" }}>
                      {c.file_name || "\u2014"}
                    </td>
                    <td style={{ padding: "12px 16px", fontSize: 13, color: "rgba(255,255,255,0.7)", textAlign: "right" }}>
                      {c.claim_count || "\u2014"}
                    </td>
                    <td style={{ padding: "12px 16px", fontSize: 13, color: "#0d9488", textAlign: "right", fontWeight: 600 }}>
                      {c.total_excess != null ? fmt$(c.total_excess) : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Team Members */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, color: "rgba(255,255,255,0.9)", margin: 0 }}>
            Team Members
          </h2>
          {isAdmin && (
            <button onClick={() => setShowInviteModal(true)}
              style={{ background: "#0d9488", color: "white", border: "none", borderRadius: 8,
                       padding: "8px 16px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
              Invite Team Member
            </button>
          )}
        </div>
        <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
                      borderRadius: 12, overflow: "hidden" }}>
          {teamMembers.map(m => (
            <div key={m.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                                     padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "rgba(255,255,255,0.9)" }}>
                  {m.full_name || m.email}
                </div>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.4)" }}>{m.email}</div>
              </div>
              <span style={{ fontSize: 11, fontWeight: 600, color: m.role === "admin" ? "#F59E0B" : "#6B7280",
                             textTransform: "uppercase", letterSpacing: 1 }}>
                {m.role}
              </span>
            </div>
          ))}
          {teamMembers.length === 0 && (
            <div style={{ padding: 24, textAlign: "center", color: "rgba(255,255,255,0.4)", fontSize: 14 }}>
              No team members yet.
            </div>
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

export default function EmployerDashboard() {
  const navigate = useNavigate();

  return (
    <AuthGate product="employer" onNeedsCompany={() => navigate("/billing/employer/signup")}>
      <EmployerDashboardInner />
    </AuthGate>
  );
}
