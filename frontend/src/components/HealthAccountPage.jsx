import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function HealthAccountPage({ healthUser, onProfileSaved }) {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState(healthUser?.full_name || "");
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    if (!fullName.trim()) { setErrorMsg("Please enter your name."); return; }
    setSaving(true); setErrorMsg(""); setSaved(false);
    const token = localStorage.getItem("health_token");
    try {
      const res = await fetch(`${API}/api/health/auth/update-profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ full_name: fullName.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to save."); setSaving(false); return; }
      // Update localStorage
      const stored = JSON.parse(localStorage.getItem("health_user") || "{}");
      stored.full_name = fullName.trim();
      localStorage.setItem("health_user", JSON.stringify(stored));
      setSaved(true);
      if (onProfileSaved) onProfileSaved(fullName.trim());
    } catch { setErrorMsg("Failed to save. Please try again."); }
    setSaving(false);
  };

  const isFirstTime = !healthUser?.full_name;

  return (
    <div style={{ maxWidth: 440, margin: "0 auto", padding: "48px 16px", fontFamily: "'DM Sans', sans-serif" }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, color: "#1B3A5C", margin: "0 0 8px" }}>
        {isFirstTime ? "Complete Your Profile" : "My Account"}
      </h2>
      {isFirstTime && (
        <p style={{ color: "#64748b", fontSize: 14, marginBottom: 28 }}>
          Tell us your name to get started.
        </p>
      )}
      {!isFirstTime && (
        <p style={{ color: "#64748b", fontSize: 14, marginBottom: 28 }}>
          Manage your Parity Health account.
        </p>
      )}

      <div style={{ marginBottom: 20 }}>
        <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#334155", marginBottom: 6 }}>Email</label>
        <input type="email" value={healthUser?.email || ""} readOnly style={{
          width: "100%", padding: "10px 12px", borderRadius: 8,
          border: "1px solid #e2e8f0", fontSize: 15, boxSizing: "border-box",
          background: "#f8fafc", color: "#94a3b8", cursor: "not-allowed",
        }} />
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#334155", marginBottom: 6 }}>Full name</label>
        <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSave()}
          placeholder="Jane Smith" style={{
            width: "100%", padding: "10px 12px", borderRadius: 8,
            border: "1px solid #e2e8f0", fontSize: 15, boxSizing: "border-box",
            background: "#fff", color: "#1e293b", outline: "none",
          }} />
      </div>

      <button onClick={handleSave} disabled={saving} style={{
        width: "100%", padding: "12px", borderRadius: 8, border: "none",
        cursor: saving ? "default" : "pointer",
        background: saving ? "#94a3b8" : "#0d9488",
        color: "#fff", fontWeight: 700, fontSize: 15,
      }}>{saving ? "Saving..." : "Save"}</button>

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
    </div>
  );
}
