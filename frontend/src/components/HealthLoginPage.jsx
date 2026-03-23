import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { API_BASE as API } from "../lib/apiBase";
export default function HealthLoginPage() {
  const navigate = useNavigate();

  // Check if already logged in
  const token = localStorage.getItem("health_token");
  if (token) {
    window.location.href = "/parity-health/";
    return null;
  }

  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [usePhone, setUsePhone] = useState(false);
  const [code, setCode] = useState("");
  const [step, setStep] = useState("email");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSendOtp = async () => {
    if (usePhone) {
      if (!phone.trim()) { setErrorMsg("Enter your phone number."); return; }
    } else {
      if (!email.includes("@")) { setErrorMsg("Enter a valid email address."); return; }
    }
    setSending(true); setErrorMsg("");
    try {
      const payload = usePhone
        ? { phone: phone.trim(), product: "health" }
        : { email: email.trim().toLowerCase() };
      const res = await fetch(`${API}/api/health/auth/send-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error();
      setStep("otp");
    } catch { setErrorMsg("Failed to send code. Please try again."); }
    setSending(false);
  };

  const handleVerifyOtp = async () => {
    if (code.length !== 8) { setErrorMsg(`Enter the 8-digit code from your ${usePhone ? "phone" : "email"}.`); return; }
    setVerifying(true); setErrorMsg("");
    try {
      const payload = usePhone
        ? { phone: phone.trim(), code: code.trim(), product: "health" }
        : { email: email.trim().toLowerCase(), code: code.trim() };
      const res = await fetch(`${API}/api/health/auth/verify-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Invalid code."); setVerifying(false); return; }
      if (data.needs_signup) {
        // Store email for signup page
        sessionStorage.setItem("health_signup_email", email.trim().toLowerCase());
        navigate("/health/signup");
        return;
      }
      // Store token and redirect based on profile completeness
      localStorage.setItem("health_token", data.token);
      localStorage.setItem("health_user", JSON.stringify(data.user));
      if (!data.user.full_name) {
        window.location.href = "/parity-health/account";
      } else {
        window.location.href = "/parity-health/";
      }
    } catch { setErrorMsg("Verification failed. Please try again."); }
    setVerifying(false);
  };

  const isHealthSubdomain = window.location.hostname === "health.civicscale.ai";
  const signupPath = isHealthSubdomain ? "/health/signup" : "/parity-health/signup";
  const homePath = isHealthSubdomain ? "/" : "/parity-health";

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0", overflowX: "hidden", minHeight: "100vh", background: "#0a1628" }}>
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.92)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href={homePath} style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>P</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" }}>Parity Health</span>
        </a>
        <nav style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 14 }}>
          <Link to={signupPath} style={{
            background: "linear-gradient(135deg, #0d9488, #14b8a6)", color: "#fff",
            textDecoration: "none", fontWeight: 600, padding: "7px 16px",
            borderRadius: 8, fontSize: 13, whiteSpace: "nowrap",
          }}>Start Free Trial</Link>
        </nav>
      </header>

      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
        <div style={{ width: "100%", maxWidth: 400, padding: "0 16px" }}>
          <div style={{ textAlign: "center", marginBottom: 40 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Parity Health</h1>
            <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 15 }}>Sign in to your account</p>
          </div>

          {step === "email" && (
            <form onSubmit={(e) => { e.preventDefault(); handleSendOtp(); }}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>
                  {usePhone ? "Phone number" : "Email address"}
                </label>
                {usePhone ? (
                  <input type="tel" required value={phone} onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 (555) 555-5555" style={{
                      width: "100%", padding: "10px 12px", borderRadius: 8,
                      border: "1px solid rgba(255,255,255,0.12)", fontSize: 15,
                      outline: "none", boxSizing: "border-box",
                      background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
                    }} />
                ) : (
                  <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com" style={{
                      width: "100%", padding: "10px 12px", borderRadius: 8,
                      border: "1px solid rgba(255,255,255,0.12)", fontSize: 15,
                      outline: "none", boxSizing: "border-box",
                      background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
                    }} />
                )}
                <button type="button" onClick={() => { setUsePhone(!usePhone); setErrorMsg(""); }}
                  style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer", marginTop: 6, padding: 0 }}>
                  {usePhone ? "Use email instead \u2192" : "Use phone number instead \u2192"}
                </button>
              </div>
              <button type="submit" disabled={sending} style={{
                width: "100%", padding: "12px", borderRadius: 8, border: "none",
                cursor: sending ? "default" : "pointer",
                background: sending ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                color: "#fff", fontWeight: 700, fontSize: 15,
              }}>{sending ? "Sending..." : "Send Code"}</button>
              <p style={{ textAlign: "center", fontSize: 13, color: "#94a3b8", marginTop: 16 }}>
                {usePhone ? "We'll text you an 8-digit code — no password needed." : "We'll send you an 8-digit code — no password needed."}
              </p>
              <p style={{ textAlign: "center", fontSize: 14, color: "#94a3b8", marginTop: 20 }}>
                Don't have an account?{" "}
                <Link to={signupPath} style={{ color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>
                  Create one free &rarr;
                </Link>
              </p>
            </form>
          )}

          {step === "otp" && (
            <div style={{ padding: 24, borderRadius: 12, border: "1px solid #0d9488", background: "rgba(13,148,136,0.08)", textAlign: "center" }}>
              <p style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 4 }}>
                We sent an 8-digit code to <strong>{usePhone ? phone : email}</strong>.
              </p>
              <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 20 }}>
                {usePhone ? "Check your texts" : "Check your inbox"} and enter it below. The code expires in 10 minutes.
              </p>
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
              }}>{verifying ? "Verifying..." : "Sign In"}</button>
              <button onClick={() => { setStep("email"); setCode(""); setErrorMsg(""); }}
                style={{ fontSize: 12, color: "#94a3b8", background: "none", border: "none", cursor: "pointer", marginTop: 12 }}>
                {usePhone ? "Use a different phone number" : "Use a different email"}
              </button>
            </div>
          )}

          {errorMsg && (
            <div style={{ padding: 12, borderRadius: 8, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", marginTop: 16 }}>
              <p style={{ color: "#fca5a5", fontSize: 13, margin: 0 }}>{errorMsg}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
