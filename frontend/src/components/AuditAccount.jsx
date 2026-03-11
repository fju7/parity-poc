import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AuthGate from "./AuthGate";

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

function AuditAccountInner() {
  const { token, user, logout: authLogout } = useAuth();
  const [audits, setAudits] = useState([]);
  const [fetchError, setFetchError] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [dataLoading, setDataLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  const authHeaders = { Authorization: `Bearer ${token}` };

  // Fetch audits + subscription when token is available
  useEffect(() => {
    if (!token) return;
    const isCheckoutReturn = new URLSearchParams(window.location.search).get("checkout_success");

    async function loadData() {
      setDataLoading(true);
      await Promise.all([
        fetchAudits(),
        fetchSubscription(),
      ]);
      setDataLoading(false);

      // After checkout, the webhook may not have created the subscription yet.
      // Poll a few times with increasing delays until the new subscription appears.
      if (isCheckoutReturn) {
        const delays = [2000, 3000, 5000];
        for (const delay of delays) {
          await new Promise((r) => setTimeout(r, delay));
          const res = await fetch(`${API_BASE}/api/provider/my-subscription`, {
            headers: authHeaders,
          });
          if (!res.ok) continue;
          const json = await res.json();
          const subs = json.subscriptions || [];
          setSubscription(subs[0] || null);
          setSubscriptions(subs);
          // Also refresh audits to get updated state
          await fetchAudits();
          // Stop polling once we have a recently created subscription
          const recent = subs.some((s) => {
            const age = Date.now() - new Date(s.created_at).getTime();
            return age < 60000;
          });
          if (recent) break;
        }
      }
    }
    loadData();
  }, [token]);

  async function fetchAudits() {
    try {
      const res = await fetch(`${API_BASE}/api/provider/my-audits`, {
        headers: authHeaders,
      });
      if (!res.ok) throw new Error("Failed to load audits");
      const json = await res.json();
      setAudits(json.audits || []);
    } catch (e) {
      console.error("[AuditAccount] Fetch failed:", e);
      setFetchError(e.message);
    }
  }

  async function fetchSubscription() {
    try {
      const res = await fetch(`${API_BASE}/api/provider/my-subscription`, {
        headers: authHeaders,
      });
      if (!res.ok) return;
      const json = await res.json();
      setSubscription(json.subscription || null);
      setSubscriptions(json.subscriptions || []);
    } catch (e) {
      console.error("[AuditAccount] Subscription fetch failed:", e);
    }
  }

  async function handleManageSubscription() {
    setPortalLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/provider/subscription/portal`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to open billing portal");
        return;
      }
      const json = await res.json();
      if (json.portal_url) {
        window.location.href = json.portal_url;
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setPortalLoading(false);
    }
  }

  async function handleStartMonitoring(auditId) {
    setCheckoutLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/provider/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
        body: JSON.stringify({ audit_id: auditId }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Failed to start checkout");
        return;
      }
      const json = await res.json();
      if (json.checkout_url) {
        window.location.href = json.checkout_url;
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setCheckoutLoading(false);
    }
  }

  function handleSignOut() {
    authLogout();
  }

  // Check for checkout_success param
  const checkoutSuccess = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("checkout_success");

  return (
    <div>
      <Nav onSignOut={handleSignOut} userEmail={user?.email} />
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 24px" }}>

        {checkoutSuccess && (
          <div style={{
            background: "#ECFDF5", border: "1px solid #A7F3D0", borderRadius: 8,
            padding: 16, marginBottom: 24, color: "#059669", fontSize: 14,
          }}>
            Your monitoring subscription is now active! We'll notify you when your first monthly analysis is ready.
          </div>
        )}

        {/* Active subscription dashboard */}
        {subscription && subscription.status === "active" && (
          <div style={{
            border: "1px solid #C4B5FD", borderRadius: 12, padding: 24,
            marginBottom: 32, background: "#FAF5FF",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1E293B", margin: "0 0 4px" }}>
                  {subscription.practice_name} — Monthly Monitoring
                </h2>
                <span style={{
                  display: "inline-block", fontSize: 11, fontWeight: 600,
                  padding: "3px 10px", borderRadius: 20,
                  background: "#ECFDF5", color: "#059669", border: "1px solid #A7F3D0",
                }}>
                  Active
                </span>
              </div>
              {subscription.stripe_subscription_id && (
                <button
                  onClick={handleManageSubscription}
                  disabled={portalLoading}
                  style={{
                    padding: "6px 14px", fontSize: 12, fontWeight: 600,
                    border: "1px solid #C4B5FD", borderRadius: 6,
                    background: "#fff", color: "#7C3AED",
                    cursor: portalLoading ? "not-allowed" : "pointer",
                    opacity: portalLoading ? 0.7 : 1,
                  }}
                >
                  {portalLoading ? "Loading..." : "Manage Subscription"}
                </button>
              )}
            </div>
            <div style={{ fontSize: 13, color: "#64748B", marginBottom: 12 }}>
              {(subscription.monthly_analyses || []).length} month{(subscription.monthly_analyses || []).length !== 1 ? "s" : ""} analyzed
              {subscription.created_at && ` · Started ${formatDate(subscription.created_at)}`}
            </div>
            {(subscription.monthly_analyses || []).length > 0 && (
              <div style={{
                borderTop: "1px solid #E9D5FF", paddingTop: 12,
              }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#7C3AED", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Monthly Analyses
                </div>
                {(subscription.monthly_analyses || []).map((m, i) => (
                  <div key={i} style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "8px 0", borderBottom: i < (subscription.monthly_analyses || []).length - 1 ? "1px solid #F3E8FF" : "none",
                  }}>
                    <span style={{ fontSize: 14, color: "#1E293B" }}>
                      {m.label || m.month}
                    </span>
                    <span style={{ fontSize: 13, color: "#64748B" }}>
                      {m.added_at ? formatDate(m.added_at) : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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

        {dataLoading ? (
          <div style={{ textAlign: "center", padding: "48px 0" }}>
            <Spinner />
            <p style={{ color: "#64748B", fontSize: 14 }}>Loading your audits...</p>
          </div>
        ) : audits.length === 0 && !fetchError ? (
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
          <>
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
                  <tr key={a.id} style={{ borderBottom: "1px solid #F1F5F9", verticalAlign: "top" }}>
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

          {/* Per-practice monitoring CTA or "Already Monitoring" badge */}
          {(() => {
            const monitoredPractices = new Set(subscriptions.map(s => s.practice_name));
            const seen = new Set();
            const deliveredByPractice = audits.filter(a => {
              if (a.status !== "delivered" || seen.has(a.practice_name)) return false;
              seen.add(a.practice_name);
              return true;
            });
            return deliveredByPractice.map((a) => {
              const alreadyMonitoring = monitoredPractices.has(a.practice_name);
              return (
                <div key={`cta-${a.id}`} style={{
                  marginTop: 16, padding: 20, borderRadius: 12,
                  background: alreadyMonitoring ? "#F8FAFC" : "linear-gradient(135deg, #FAF5FF, #F0FDFA)",
                  border: alreadyMonitoring ? "1px solid #E2E8F0" : "1px solid #C4B5FD",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 16 }}>
                    <div>
                      <h3 style={{ fontSize: 15, fontWeight: 700, color: "#1E293B", margin: "0 0 4px" }}>
                        {a.practice_name}
                      </h3>
                      {alreadyMonitoring ? (
                        <p style={{ fontSize: 14, color: "#059669", margin: 0, fontWeight: 600 }}>
                          Already Monitoring
                        </p>
                      ) : (
                        <p style={{ fontSize: 14, color: "#64748B", margin: 0 }}>
                          {a.total_underpayment > 0
                            ? `Your audit found $${a.total_underpayment.toLocaleString()} in recoverable revenue. `
                            : ""}
                          Keep watching your payer payments — $300/month.
                        </p>
                      )}
                    </div>
                    {!alreadyMonitoring && (
                      <button
                        onClick={() => handleStartMonitoring(a.id)}
                        disabled={checkoutLoading}
                        style={{
                          padding: "10px 24px", borderRadius: 8, fontSize: 14, fontWeight: 600,
                          border: "none", background: "#7C3AED", color: "#fff",
                          cursor: checkoutLoading ? "not-allowed" : "pointer",
                          opacity: checkoutLoading ? 0.7 : 1, whiteSpace: "nowrap",
                        }}
                      >
                        {checkoutLoading ? "Redirecting..." : "Start Monthly Monitoring \u2192"}
                      </button>
                    )}
                  </div>
                </div>
              );
            });
          })()}
          </>
        )}
      </div>
    </div>
  );
}

export default function AuditAccount() {
  return (
    <AuthGate product="provider">
      <AuditAccountInner />
    </AuthGate>
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
        <Link to="/audit" style={{ fontSize: 13, color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>Free Audit</Link>
        {userEmail && (
          <button onClick={onSignOut} style={{ background: "none", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6, padding: "6px 14px", fontSize: 13, color: "#94a3b8", cursor: "pointer" }}>
            Sign out
          </button>
        )}
      </div>
    </header>
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
