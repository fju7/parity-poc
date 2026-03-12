import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

function daysUntil(iso) {
  if (!iso) return 0;
  const now = new Date();
  const end = new Date(iso);
  return Math.max(0, Math.ceil((end - now) / (1000 * 60 * 60 * 24)));
}

export default function HealthAccountPage({ healthUser, onProfileSaved }) {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState(healthUser?.full_name || "");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [saved, setSaved] = useState(false);

  // Subscription state
  const [sub, setSub] = useState(null);
  const [subLoading, setSubLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [checkoutPolling, setCheckoutPolling] = useState(
    () => new URLSearchParams(window.location.search).get("checkout") === "success"
  );

  const token = localStorage.getItem("health_token");

  const fetchSubStatus = () =>
    fetch(`${API}/api/health/auth/subscription-status`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => r.ok ? r.json() : Promise.reject());

  useEffect(() => {
    if (!token) return;

    const params = new URLSearchParams(window.location.search);
    const isCheckoutReturn = params.get("checkout") === "success";

    if (isCheckoutReturn) {
      // Remove query param from URL
      window.history.replaceState({}, "", window.location.pathname);

      // Poll until subscription shows active/trialing
      let attempts = 0;
      setSubLoading(true);
      const poll = setInterval(async () => {
        attempts++;
        try {
          const data = await fetchSubStatus();
          if (data.has_subscription && (data.status === "active" || data.status === "trialing")) {
            setSub(data);
            setSubLoading(false);
            setCheckoutPolling(false);
            clearInterval(poll);
          } else if (attempts >= 5) {
            setSub(data);
            setSubLoading(false);
            setCheckoutPolling(false);
            clearInterval(poll);
          }
        } catch {
          if (attempts >= 5) {
            setSub(null);
            setSubLoading(false);
            setCheckoutPolling(false);
            clearInterval(poll);
          }
        }
      }, 2000);
      return () => clearInterval(poll);
    }

    // Normal load — single fetch
    fetchSubStatus()
      .then((data) => setSub(data))
      .catch(() => setSub(null))
      .finally(() => setSubLoading(false));
  }, [token]);

  const handleSave = async () => {
    if (!fullName.trim()) { setErrorMsg("Please enter your name."); return; }
    setSaving(true); setErrorMsg(""); setSaved(false);
    try {
      const res = await fetch(`${API}/api/health/auth/update-profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ full_name: fullName.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to save."); setSaving(false); return; }
      const stored = JSON.parse(localStorage.getItem("health_user") || "{}");
      stored.full_name = fullName.trim();
      localStorage.setItem("health_user", JSON.stringify(stored));
      setSaved(true);
      setEditing(false);
      if (onProfileSaved) onProfileSaved(fullName.trim());
      setTimeout(() => setSaved(false), 3000);
    } catch { setErrorMsg("Failed to save. Please try again."); }
    setSaving(false);
  };

  const handleCancelEdit = () => {
    setFullName(healthUser?.full_name || "");
    setEditing(false);
    setErrorMsg("");
  };

  const handleCheckout = async (plan) => {
    setCheckoutLoading(plan); setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/health/auth/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to start checkout."); setCheckoutLoading(null); return; }
      window.location.href = data.checkout_url;
    } catch { setErrorMsg("Failed to start checkout. Please try again."); setCheckoutLoading(null); }
  };

  const handlePortal = async () => {
    setPortalLoading(true); setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/health/auth/portal`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to open billing portal."); setPortalLoading(false); return; }
      window.location.href = data.portal_url;
    } catch { setErrorMsg("Failed to open billing portal. Please try again."); setPortalLoading(false); }
  };

  const isFirstTime = !healthUser?.full_name;

  const inputStyle = {
    width: "100%", padding: "10px 12px", borderRadius: 8,
    border: "1px solid #e2e8f0", fontSize: 15, boxSizing: "border-box",
    background: "#fff", color: "#1e293b", outline: "none",
  };

  const cardStyle = {
    padding: 24, borderRadius: 12, border: "1px solid #e2e8f0",
    background: "#fff", marginTop: 32,
  };

  const btnTeal = (loading) => ({
    padding: "10px 20px", borderRadius: 8, border: "none",
    cursor: loading ? "default" : "pointer",
    background: loading ? "#94a3b8" : "#0d9488",
    color: "#fff", fontWeight: 600, fontSize: 14,
  });

  const btnOutline = (loading) => ({
    padding: "10px 20px", borderRadius: 8,
    border: "1px solid #0d9488", background: "transparent",
    cursor: loading ? "default" : "pointer",
    color: "#0d9488", fontWeight: 600, fontSize: 14,
  });

  // Determine subscription display state
  const hasSub = sub?.has_subscription;
  const isTrial = sub?.status === "trialing";
  const isActive = hasSub && (sub?.status === "active" || isTrial);
  const isExpired = hasSub && (sub?.status === "expired" || sub?.status === "canceled");

  return (
    <div style={{ maxWidth: 440, margin: "0 auto", padding: "48px 16px", fontFamily: "'DM Sans', sans-serif" }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 8px" }}>
        {isFirstTime ? "Complete Your Profile" : "My Account"}
      </h2>
      <p style={{ color: "#64748b", fontSize: 14, marginBottom: 28 }}>
        {isFirstTime ? "Tell us your name to get started." : "Manage your Parity Health account."}
      </p>

      {/* Profile section */}
      {isFirstTime ? (
        /* First-time: always show editable form */
        <>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#334155", marginBottom: 6 }}>Email</label>
            <input type="email" value={healthUser?.email || ""} readOnly style={{
              ...inputStyle, background: "#f8fafc", color: "#94a3b8", cursor: "not-allowed",
            }} />
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#334155", marginBottom: 6 }}>Full name</label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              placeholder="Jane Smith" style={inputStyle} />
          </div>
          <button onClick={handleSave} disabled={saving} style={{
            width: "100%", padding: "12px", borderRadius: 8, border: "none",
            cursor: saving ? "default" : "pointer",
            background: saving ? "#94a3b8" : "#0d9488",
            color: "#fff", fontWeight: 700, fontSize: 15,
          }}>{saving ? "Saving..." : "Save"}</button>
        </>
      ) : editing ? (
        /* Edit mode */
        <>
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#334155", marginBottom: 6 }}>Email</label>
            <input type="email" value={healthUser?.email || ""} readOnly style={{
              ...inputStyle, background: "#f8fafc", color: "#94a3b8", cursor: "not-allowed",
            }} />
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#334155", marginBottom: 6 }}>Full name</label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSave()}
              placeholder="Jane Smith" autoFocus style={inputStyle} />
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={handleSave} disabled={saving} style={{
              padding: "10px 24px", borderRadius: 8, border: "none",
              cursor: saving ? "default" : "pointer",
              background: saving ? "#94a3b8" : "#0d9488",
              color: "#fff", fontWeight: 600, fontSize: 14,
            }}>{saving ? "Saving..." : "Save"}</button>
            <button onClick={handleCancelEdit} style={{
              padding: "10px 24px", borderRadius: 8, border: "1px solid #e2e8f0",
              background: "transparent", color: "#64748b", fontWeight: 600,
              fontSize: 14, cursor: "pointer",
            }}>Cancel</button>
          </div>
        </>
      ) : (
        /* Read mode */
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontSize: 13, fontWeight: 500, color: "#94a3b8", margin: "0 0 2px" }}>Email</p>
                <p style={{ fontSize: 15, color: "#1e293b", margin: 0 }}>{healthUser?.email || ""}</p>
              </div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 500, color: "#94a3b8", margin: "0 0 2px" }}>Name</p>
                <p style={{ fontSize: 15, color: "#1e293b", margin: 0 }}>{fullName || "—"}</p>
              </div>
            </div>
            <button onClick={() => { setEditing(true); setSaved(false); setErrorMsg(""); }} style={{
              padding: "6px 16px", borderRadius: 8, border: "1px solid #e2e8f0",
              background: "transparent", color: "#475569", fontWeight: 600,
              fontSize: 13, cursor: "pointer",
            }}>Edit</button>
          </div>
        </>
      )}

      {errorMsg && (
        <div style={{ padding: 12, borderRadius: 8, background: "#fef2f2", border: "1px solid #fecaca", marginTop: 16 }}>
          <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{errorMsg}</p>
        </div>
      )}

      {saved && (
        <div style={{ padding: 12, borderRadius: 8, background: "#f0fdf4", border: "1px solid #bbf7d0", marginTop: 16 }}>
          <p style={{ color: "#166534", fontSize: 13, margin: 0 }}>Profile saved.</p>
        </div>
      )}

      {/* Your Plan section */}
      {!isFirstTime && (
        <div style={cardStyle}>
          <h3 style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: "0 0 16px" }}>Your Plan</h3>

          {subLoading && (
            <p style={{ color: "#94a3b8", fontSize: 14 }}>
              {checkoutPolling ? "Setting up your account..." : "Loading..."}
            </p>
          )}

          {/* Trial active */}
          {!subLoading && isTrial && (
            <>
              <div style={{
                display: "inline-block", padding: "4px 12px", borderRadius: 20,
                background: "#f0fdfa", border: "1px solid #99f6e4", marginBottom: 16,
              }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#0d9488" }}>
                  Free Trial — {daysUntil(sub.trial_ends_at)} days remaining
                </span>
              </div>
              <p style={{ fontSize: 14, color: "#475569", margin: "0 0 20px", lineHeight: 1.6 }}>
                Your trial ends on {formatDate(sub.trial_ends_at)}. You won't be charged until then.
              </p>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
                <button onClick={() => handleCheckout("monthly")}
                  disabled={checkoutLoading === "monthly"} style={btnTeal(checkoutLoading === "monthly")}>
                  {checkoutLoading === "monthly" ? "Loading..." : "Upgrade to Monthly ($9.95/mo)"}
                </button>
                <button onClick={() => handleCheckout("yearly")}
                  disabled={checkoutLoading === "yearly"} style={btnOutline(checkoutLoading === "yearly")}>
                  {checkoutLoading === "yearly" ? "Loading..." : "Upgrade to Annual ($29/yr — save 75%)"}
                </button>
              </div>
              <button onClick={handlePortal} disabled={portalLoading} style={{
                background: "none", border: "none", color: "#94a3b8", fontSize: 13,
                cursor: portalLoading ? "default" : "pointer", padding: 0,
                textDecoration: "underline",
              }}>{portalLoading ? "Opening..." : "Cancel trial"}</button>
            </>
          )}

          {/* Active paid subscription */}
          {!subLoading && isActive && !isTrial && (
            <>
              <div style={{
                display: "inline-block", padding: "4px 12px", borderRadius: 20,
                background: "#f0fdfa", border: "1px solid #99f6e4", marginBottom: 16,
              }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#0d9488" }}>
                  Parity Health {sub.plan === "yearly" ? "Annual" : "Monthly"}
                </span>
              </div>
              {sub.current_period_end && (
                <p style={{ fontSize: 14, color: "#475569", margin: "0 0 20px" }}>
                  Next billing date: {formatDate(sub.current_period_end)}
                </p>
              )}
              <button onClick={handlePortal} disabled={portalLoading} style={btnTeal(portalLoading)}>
                {portalLoading ? "Opening..." : "Manage billing"}
              </button>
            </>
          )}

          {/* No subscription or expired */}
          {!subLoading && (!hasSub || isExpired) && (
            <>
              <p style={{ fontSize: 14, color: "#64748b", margin: "0 0 16px" }}>
                No active plan. Start a free trial to get unlimited bill analyses.
              </p>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button onClick={() => handleCheckout("monthly")}
                  disabled={checkoutLoading === "monthly"} style={btnTeal(checkoutLoading === "monthly")}>
                  {checkoutLoading === "monthly" ? "Loading..." : "Start Free Trial — $9.95/mo"}
                </button>
                <button onClick={() => handleCheckout("yearly")}
                  disabled={checkoutLoading === "yearly"} style={btnOutline(checkoutLoading === "yearly")}>
                  {checkoutLoading === "yearly" ? "Loading..." : "Start Free Trial — $29/yr (save 75%)"}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
