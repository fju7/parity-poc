import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function BrokerAccountPage() {
  const navigate = useNavigate();
  const [broker, setBroker] = useState(null);
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

  // Editable fields
  const [contactName, setContactName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [phone, setPhone] = useState("");

  // Cancel modal
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);

  // Reactivate
  const [reactivateLoading, setReactivateLoading] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("broker_session");
    if (!stored) { navigate("/broker/login"); return; }
    const session = JSON.parse(stored);
    setBroker(session);
    fetchAccount(session.email);
  }, []);

  const fetchAccount = async (email) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/account?broker_email=${encodeURIComponent(email)}`);
      const data = await res.json();
      setAccount(data);
      setContactName(data.contact_name || "");
      setFirmName(data.firm_name || "");
      setPhone(data.phone || "");
    } catch (err) { console.error("Failed to load account:", err); }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!broker) return;
    setSaving(true);
    setSaveMsg("");
    try {
      const res = await fetch(`${API}/api/broker/account`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          broker_email: broker.email,
          contact_name: contactName,
          firm_name: firmName,
          phone: phone,
        }),
      });
      if (res.ok) {
        setSaveMsg("Changes saved.");
        // Update local session
        const session = JSON.parse(localStorage.getItem("broker_session") || "{}");
        session.contact_name = contactName;
        session.firm_name = firmName;
        localStorage.setItem("broker_session", JSON.stringify(session));
        setTimeout(() => setSaveMsg(""), 3000);
      } else {
        setSaveMsg("Failed to save changes.");
      }
    } catch { setSaveMsg("Failed to save changes."); }
    setSaving(false);
  };

  const handleCancel = async () => {
    if (!broker) return;
    setCancelLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/cancel-subscription?broker_email=${encodeURIComponent(broker.email)}`, { method: "POST" });
      const data = await res.json();
      if (data.status === "cancelled") {
        setAccount(prev => ({ ...prev, plan: "pro_cancelling", subscription_period_end: data.period_end }));
        setShowCancelModal(false);
      }
    } catch (err) { console.error("Cancel failed:", err); }
    setCancelLoading(false);
  };

  const handleReactivate = async () => {
    if (!broker) return;
    setReactivateLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/reactivate-subscription?broker_email=${encodeURIComponent(broker.email)}`, { method: "POST" });
      const data = await res.json();
      if (data.status === "reactivated") {
        setAccount(prev => ({ ...prev, plan: "pro", subscription_period_end: null }));
      }
    } catch (err) { console.error("Reactivate failed:", err); }
    setReactivateLoading(false);
  };

  const handleUpgrade = async () => {
    if (!broker) return;
    try {
      const res = await fetch(`${API}/api/broker/subscribe?broker_email=${encodeURIComponent(broker.email)}`, { method: "POST" });
      const data = await res.json();
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (err) { console.error("Upgrade failed:", err); }
  };

  const handleLogout = () => {
    localStorage.removeItem("broker_session");
    navigate("/broker/login");
  };

  const formatDate = (iso) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  };

  if (!broker || loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans', sans-serif" }}>
      <p style={{ color: "#64748b" }}>Loading...</p>
    </div>
  );

  const isPro = account?.plan === "pro";
  const isCancelling = account?.plan === "pro_cancelling";
  const isStarter = !isPro && !isCancelling;

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
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 8px" }}>Account Settings</h1>
        <p style={{ color: "#64748b", fontSize: 14, marginBottom: 32 }}>{broker.email}</p>

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
                value={broker.email}
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
          <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.6, margin: 0 }}>
            Your data is stored securely and never shared with third parties.
            To request data export or account deletion, contact <a href="mailto:support@civicscale.ai" style={{ color: "#0D7377" }}>support@civicscale.ai</a>.
          </p>
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
    </div>
  );
}
