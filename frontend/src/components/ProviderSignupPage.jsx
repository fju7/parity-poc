import { useState } from "react";
import { useNavigate, Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

import { API_BASE as API } from "../lib/apiBase";
export default function ProviderSignupPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, company } = useAuth();

  const [step, setStep] = useState("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [fullName, setFullName] = useState("");
  const [practiceName, setPracticeName] = useState("");

  if (isAuthenticated && company?.type === "provider") {
    return <Navigate to="/provider/dashboard" replace />;
  }

  const handleSendOtp = async () => {
    if (!email.includes("@")) { setErrorMsg("Enter a valid email address."); return; }
    setSending(true); setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/send-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), product: "provider" }),
      });
      if (!res.ok) throw new Error();
      setStep("otp");
    } catch { setErrorMsg("Failed to send code. Please try again."); }
    setSending(false);
  };

  const handleVerifyOtp = async () => {
    if (code.length !== 8) { setErrorMsg("Enter the 8-digit code from your email."); return; }
    setVerifying(true); setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/verify-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: code.trim(), product: "provider" }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Invalid code."); return; }
      if (data.needs_company) {
        setStep("company");
      } else {
        login(data.token, data.user, data.company);
        navigate("/provider/dashboard");
      }
    } catch { setErrorMsg("Verification failed. Please try again."); }
    finally { setVerifying(false); }
  };

  const handleCreateCompany = async () => {
    if (!fullName.trim()) { setErrorMsg("Enter your full name."); return; }
    if (!practiceName.trim()) { setErrorMsg("Enter your practice name."); return; }
    setCreating(true); setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/company`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          full_name: fullName.trim(),
          company_name: practiceName.trim(),
          company_type: "provider",
        }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to create account."); return; }
      login(data.token, data.user, data.company);
      navigate("/provider/dashboard");
    } catch { setErrorMsg("Failed to create account. Please try again."); }
    setCreating(false);
  };

  const inputStyle = {
    width: "100%", padding: "10px 12px", borderRadius: 8,
    border: "1px solid rgba(255,255,255,0.12)", fontSize: 15,
    outline: "none", boxSizing: "border-box",
    background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
  };

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", minHeight: "100vh", background: "#0a1628", color: "#e2e8f0" }}>
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.92)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" }}>CivicScale</span>
        </a>
        <nav style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 14 }}>
          <Link to="/billing/provider" style={{ color: "#94a3b8", textDecoration: "none" }}>Parity Provider</Link>
        </nav>
      </header>

      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
        <div style={{ width: "100%", maxWidth: 420, padding: "0 16px" }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Start your free trial</h1>
            <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 15, lineHeight: 1.6 }}>
              Parity Provider &mdash; $99/mo after 30 days. Cancel anytime.
            </p>
          </div>

          {step === "email" && (
            <>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>Email *</label>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendOtp()}
                  placeholder="you@yourpractice.com" style={inputStyle} />
              </div>
              <button onClick={handleSendOtp} disabled={sending} style={{
                width: "100%", padding: "12px", borderRadius: 8, border: "none",
                cursor: sending ? "default" : "pointer",
                background: sending ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                color: "#fff", fontWeight: 700, fontSize: 15, marginBottom: 12,
              }}>{sending ? "Sending code..." : "Continue →"}</button>
              <p style={{ textAlign: "center", fontSize: 14, color: "#64748b", marginTop: 16 }}>
                Already have an account?{" "}
                <Link to="/provider/login" style={{ color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>Sign in &rarr;</Link>
              </p>
              <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  "✓ 30-day free trial — cancel anytime",
                  "✓ Automatic contract compliance checks every month",
                  "✓ Denial pattern analysis and one-click appeal letters",
                ].map(t => <p key={t} style={{ fontSize: 13, color: "#475569", margin: 0 }}>{t}</p>)}
              </div>
            </>
          )}

          {step === "otp" && (
            <div style={{ padding: 24, borderRadius: 12, border: "1px solid #0d9488", background: "rgba(13,148,136,0.08)", textAlign: "center" }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "0 0 8px" }}>Check your email</h3>
              <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 4 }}>We sent an 8-digit code to <strong style={{ color: "#f1f5f9" }}>{email}</strong>.</p>
              <p style={{ fontSize: 12, color: "#64748b", marginBottom: 20 }}>Enter it below. The code expires in 10 minutes.</p>
              <input type="text" placeholder="12345678" value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
                onKeyDown={(e) => e.key === "Enter" && handleVerifyOtp()}
                maxLength={8} style={{
                  width: "100%", padding: "12px 16px", fontSize: 24, letterSpacing: 8,
                  textAlign: "center", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8,
                  outline: "none", boxSizing: "border-box", marginBottom: 12,
                  background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
                }} />
              <button onClick={handleVerifyOtp} disabled={verifying} style={{
                width: "100%", padding: "12px", borderRadius: 8, border: "none",
                cursor: verifying ? "default" : "pointer",
                background: verifying ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                color: "#fff", fontWeight: 700, fontSize: 15,
              }}>{verifying ? "Verifying..." : "Verify Code"}</button>
              <button onClick={() => { setStep("email"); setCode(""); setErrorMsg(""); }}
                style={{ fontSize: 12, color: "#64748b", background: "none", border: "none", cursor: "pointer", marginTop: 12 }}>
                Use a different email
              </button>
            </div>
          )}

          {step === "company" && (
            <>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px", textAlign: "center" }}>Set up your account</h3>
              <p style={{ fontSize: 14, color: "#94a3b8", textAlign: "center", marginBottom: 20 }}>Tell us about your practice.</p>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>Full name *</label>
                <input type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)}
                  placeholder="Dr. Jane Smith" style={inputStyle} />
              </div>
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>Practice name *</label>
                <input type="text" required value={practiceName} onChange={(e) => setPracticeName(e.target.value)}
                  placeholder="Riverside Family Medicine" style={inputStyle} />
              </div>
              <button onClick={handleCreateCompany} disabled={creating} style={{
                width: "100%", padding: "12px", borderRadius: 8, border: "none",
                cursor: creating ? "default" : "pointer",
                background: creating ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                color: "#fff", fontWeight: 700, fontSize: 15,
              }}>{creating ? "Creating account..." : "Start Free Trial →"}</button>
            </>
          )}

          {errorMsg && (
            <div style={{ padding: 12, borderRadius: 8, background: "#fef2f2", border: "1px solid #fecaca", marginTop: 16 }}>
              <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{errorMsg}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
