import { useState } from "react";
import { useAuth } from "../context/AuthContext";

import { API_BASE as API } from "../lib/apiBase";
export default function EmployerTrialBanner() {
  const { token, company, refetch } = useAuth();
  const [loading, setLoading] = useState(false);
  const [showCancel, setShowCancel] = useState(false);

  if (!company) return null;

  const plan = company.plan || "free";
  const trialEndsAt = company.trial_ends_at;

  // Calculate days remaining in trial
  const daysRemaining = trialEndsAt ? Math.max(0, Math.ceil(
    (new Date(trialEndsAt) - new Date()) / (1000 * 60 * 60 * 24)
  )) : null;

  const handleStartTrial = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/employer/start-trial`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.checkout_url) window.location.href = data.checkout_url;
      if (data.already_active) refetch();
    } catch {
      alert("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/api/employer/cancel-trial`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      await refetch();
      setShowCancel(false);
    } finally {
      setLoading(false);
    }
  };

  // Free tier — show trial CTA
  if (plan === "free") {
    return (
      <div style={{
        background: "rgba(13,148,136,0.08)", border: "1px solid rgba(13,148,136,0.3)",
        borderRadius: "12px", padding: "20px 24px", marginBottom: "24px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: "16px"
      }}>
        <div>
          <div style={{ color: "white", fontWeight: "600", marginBottom: "4px" }}>
            Start your free 30-day trial
          </div>
          <div style={{ color: "rgba(255,255,255,0.5)", fontSize: "14px" }}>
            Full access to all features. $99/mo after trial — introductory price
            locked for 24 months. Cancel anytime before day 30, no charge.
          </div>
        </div>
        <button
          onClick={handleStartTrial}
          disabled={loading}
          style={{
            background: "#0d9488", color: "white", border: "none",
            borderRadius: "8px", padding: "10px 20px", fontWeight: "600",
            fontSize: "14px", cursor: loading ? "not-allowed" : "pointer",
            whiteSpace: "nowrap", opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Loading..." : "Start Free Trial"}
        </button>
      </div>
    );
  }

  // Trial active — show days remaining
  if (plan === "trial") {
    const urgency = daysRemaining <= 7;
    return (
      <div style={{
        background: urgency ? "rgba(251,191,36,0.08)" : "rgba(13,148,136,0.08)",
        border: `1px solid ${urgency ? "rgba(251,191,36,0.3)" : "rgba(13,148,136,0.3)"}`,
        borderRadius: "12px", padding: "16px 24px", marginBottom: "24px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: "12px"
      }}>
        <div style={{ color: urgency ? "#fbbf24" : "#0d9488", fontWeight: "600" }}>
          {daysRemaining > 0
            ? `Trial active \u2014 ${daysRemaining} day${daysRemaining !== 1 ? "s" : ""} remaining`
            : "Trial period ended \u2014 converting to paid plan"}
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "13px" }}>
            $99/mo after trial
          </span>
          <button
            onClick={() => setShowCancel(true)}
            style={{
              background: "transparent", color: "rgba(255,255,255,0.3)",
              border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px",
              padding: "6px 12px", fontSize: "12px", cursor: "pointer",
            }}
          >
            Cancel Trial
          </button>
        </div>

        {showCancel && (
          <div style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000
          }}>
            <div style={{
              background: "#1a2235", border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "16px", padding: "32px", maxWidth: "420px", width: "90%"
            }}>
              <h3 style={{ color: "white", marginBottom: "12px" }}>Cancel your trial?</h3>
              <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "14px", marginBottom: "24px" }}>
                You won't be charged. Your saved analysis results will remain accessible
                in read-only mode. You can resubscribe at any time.
              </p>
              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  onClick={() => setShowCancel(false)}
                  style={{
                    flex: 1, padding: "10px", background: "rgba(255,255,255,0.05)",
                    color: "white", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px", cursor: "pointer", fontWeight: "600",
                  }}
                >
                  Keep Trial
                </button>
                <button
                  onClick={handleCancel}
                  disabled={loading}
                  style={{
                    flex: 1, padding: "10px", background: "#ef4444", color: "white",
                    border: "none", borderRadius: "8px", cursor: "pointer", fontWeight: "600",
                  }}
                >
                  {loading ? "Cancelling..." : "Yes, Cancel"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Pro — show plan status quietly
  if (plan === "pro") {
    return (
      <div style={{
        background: "rgba(13,148,136,0.05)", border: "1px solid rgba(13,148,136,0.15)",
        borderRadius: "8px", padding: "10px 16px", marginBottom: "16px",
        display: "flex", alignItems: "center", gap: "8px"
      }}>
        <span style={{ color: "#0d9488", fontSize: "13px" }}>{"\u2713"}</span>
        <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "13px" }}>
          Pro Plan &middot; $99/mo &middot; Introductory price locked
        </span>
      </div>
    );
  }

  // Read-only
  if (plan === "read_only" || plan === "cancelled") {
    return (
      <div style={{
        background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
        borderRadius: "12px", padding: "20px 24px", marginBottom: "24px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: "16px"
      }}>
        <div>
          <div style={{ color: "#f87171", fontWeight: "600", marginBottom: "4px" }}>
            Subscription ended — read-only access
          </div>
          <div style={{ color: "rgba(255,255,255,0.4)", fontSize: "14px" }}>
            Your saved results are still here. Resubscribe to run new analyses.
          </div>
        </div>
        <button
          onClick={handleStartTrial}
          disabled={loading}
          style={{
            background: "#0d9488", color: "white", border: "none",
            borderRadius: "8px", padding: "10px 20px", fontWeight: "600",
            fontSize: "14px", cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          Resubscribe — $99/mo
        </button>
      </div>
    );
  }

  return null;
}
