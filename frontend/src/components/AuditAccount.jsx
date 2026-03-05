import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { supabase } from "../lib/supabase.js";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const STATUS_COLORS = {
  submitted: { bg: "#EFF6FF", text: "#2563EB", border: "#BFDBFE" },
  processing: { bg: "#EEF2FF", text: "#4F46E5", border: "#C7D2FE" },
  review: { bg: "#FFFBEB", text: "#D97706", border: "#FDE68A" },
  delivered: { bg: "#ECFDF5", text: "#059669", border: "#A7F3D0" },
};

const STATUS_LABELS = {
  submitted: "Submitted",
  processing: "Processing",
  review: "Under Review",
  delivered: "Delivered",
};

export default function AuditAccount() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [audits, setAudits] = useState([]);
  const [fetchError, setFetchError] = useState(null);

  // Login form state
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [linkSent, setLinkSent] = useState(false);
  const [authError, setAuthError] = useState("");

  // Auth bootstrap
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Fetch audits when session is available
  useEffect(() => {
    if (!session) return;
    fetchAudits(session.access_token);
  }, [session]);

  async function fetchAudits(token) {
    try {
      const res = await fetch(`${API_BASE}/api/provider/my-audits`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load audits");
      const json = await res.json();
      setAudits(json.audits || []);
    } catch (e) {
      console.error("[AuditAccount] Fetch failed:", e);
      setFetchError(e.message);
    }
  }

  const handleSendLink = useCallback(async (e) => {
    e.preventDefault();
    setSending(true);
    setAuthError("");

    const origin = window.location.hostname === "localhost"
      ? window.location.origin
      : "https://civicscale.ai";

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: origin + "/audit/account" },
    });

    setSending(false);
    if (error) {
      setAuthError(error.message);
    } else {
      setLinkSent(true);
    }
  }, [email]);

  const handleSignOut = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setAudits([]);
  }, []);

  if (loading) {
    return (
      <div>
        <Nav />
        <div style={{ textAlign: "center", padding: "120px 24px" }}>
          <Spinner />
          <p style={{ color: "#64748B", fontSize: 16 }}>Loading...</p>
        </div>
      </div>
    );
  }

  // Not logged in — show magic link form
  if (!session) {
    return (
      <div>
        <Nav />
        <div style={{ maxWidth: 420, margin: "80px auto", padding: "0 24px" }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#1E293B", margin: "0 0 8px", textAlign: "center" }}>
            Sign in to your account
          </h1>
          <p style={{ color: "#64748B", fontSize: 15, textAlign: "center", margin: "0 0 32px" }}>
            Enter the email you used to submit your audit.
          </p>

          {linkSent ? (
            <div style={{
              background: "#F0FDFA", border: "1px solid #99F6E4", borderRadius: 12,
              padding: 24, textAlign: "center",
            }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>&#9993;</div>
              <h3 style={{ color: "#1E293B", margin: "0 0 8px" }}>Check your email</h3>
              <p style={{ color: "#64748B", fontSize: 14, lineHeight: 1.6 }}>
                We sent a sign-in link to <strong>{email}</strong>. Click the link in your email to access your account.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSendLink}>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@practice.com"
                style={{
                  width: "100%", padding: "12px 16px", fontSize: 15,
                  border: "1px solid #CBD5E1", borderRadius: 8,
                  outline: "none", boxSizing: "border-box",
                }}
              />
              {authError && (
                <p style={{ color: "#EF4444", fontSize: 13, margin: "8px 0 0" }}>{authError}</p>
              )}
              <button
                type="submit"
                disabled={sending}
                style={{
                  width: "100%", marginTop: 16, padding: "12px 0",
                  background: "#0D9488", color: "#fff", fontWeight: 600,
                  fontSize: 15, border: "none", borderRadius: 8,
                  cursor: sending ? "not-allowed" : "pointer",
                  opacity: sending ? 0.7 : 1,
                }}
              >
                {sending ? "Sending..." : "Send sign-in link"}
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  // Logged in — show audits
  return (
    <div>
      <Nav onSignOut={handleSignOut} userEmail={session.user?.email} />
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 24px" }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#1E293B", margin: "0 0 24px" }}>
          Your Audits
        </h1>

        {fetchError && (
          <div style={{
            background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 8,
            padding: 16, marginBottom: 24, color: "#B91C1C", fontSize: 14,
          }}>
            {fetchError}
          </div>
        )}

        {audits.length === 0 && !fetchError ? (
          <div style={{ textAlign: "center", padding: "48px 0" }}>
            <div style={{ fontSize: 48, marginBottom: 16 }}>&#128203;</div>
            <h3 style={{ color: "#1E293B", margin: "0 0 8px" }}>No audits yet</h3>
            <p style={{ color: "#64748B", fontSize: 15, margin: "0 0 24px" }}>
              Start your free Parity Audit to identify underpayments across your payers.
            </p>
            <Link
              to="/audit"
              style={{
                display: "inline-block", padding: "12px 28px",
                background: "#0D9488", color: "#fff", fontWeight: 600,
                fontSize: 15, borderRadius: 8, textDecoration: "none",
              }}
            >
              Start Your Free Audit
            </Link>
          </div>
        ) : (
          <div style={{ border: "1px solid #E2E8F0", borderRadius: 12, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
                  <th style={thStyle}>Practice</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Submitted</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {audits.map((a) => (
                  <tr key={a.id} style={{ borderBottom: "1px solid #F1F5F9" }}>
                    <td style={tdStyle}>
                      <span style={{ fontWeight: 600, color: "#1E293B" }}>{a.practice_name}</span>
                    </td>
                    <td style={tdStyle}>
                      <StatusBadge status={a.status} />
                    </td>
                    <td style={{ ...tdStyle, color: "#64748B" }}>
                      {formatDate(a.created_at)}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {a.status === "delivered" && a.report_token ? (
                        <Link
                          to={`/report/${a.report_token}`}
                          style={{
                            display: "inline-block", padding: "6px 16px",
                            background: "#0D9488", color: "#fff", fontWeight: 600,
                            fontSize: 13, borderRadius: 6, textDecoration: "none",
                          }}
                        >
                          View Report
                        </Link>
                      ) : (
                        <span style={{ color: "#94A3B8", fontSize: 13 }}>Pending</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const thStyle = {
  padding: "12px 16px", textAlign: "left", fontSize: 12,
  fontWeight: 600, color: "#64748B", textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const tdStyle = {
  padding: "14px 16px",
};

function StatusBadge({ status }) {
  const c = STATUS_COLORS[status] || { bg: "#F3F4F6", text: "#6B7280", border: "#D1D5DB" };
  return (
    <span style={{
      display: "inline-block", fontSize: 11, fontWeight: 600,
      padding: "3px 10px", borderRadius: 20,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

function Nav({ onSignOut, userEmail }) {
  return (
    <nav className="cs-nav">
      <Link className="cs-nav-logo" to="/">
        <LogoIcon />
        <span className="cs-nav-wordmark">CivicScale</span>
      </Link>
      <div className="cs-nav-links">
        <Link to="/audit">Free Audit</Link>
        {userEmail && (
          <button
            onClick={onSignOut}
            style={{
              background: "none", border: "none", color: "#64748B",
              fontSize: 14, cursor: "pointer", padding: 0,
            }}
          >
            Sign out
          </button>
        )}
      </div>
    </nav>
  );
}

function Spinner() {
  return (
    <>
      <div style={{
        width: 48, height: 48, border: "4px solid #E2E8F0",
        borderTopColor: "#0D9488", borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
        margin: "0 auto 24px",
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </>
  );
}

function formatDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
