import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function HealthSignupPage() {
  const navigate = useNavigate();

  // Check if already logged in
  const token = localStorage.getItem("health_token");
  if (token) {
    window.location.href = "/";
    return null;
  }

  const [step, setStep] = useState("email"); // email | otp | profile | plan
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState(null); // "monthly" | "yearly" | null

  // If redirected from login (OTP already verified, needs signup)
  useEffect(() => {
    const savedEmail = sessionStorage.getItem("health_signup_email");
    if (savedEmail) {
      setEmail(savedEmail);
      setStep("profile");
      sessionStorage.removeItem("health_signup_email");
    }
  }, []);

  const handleSendOtp = async () => {
    if (!email.includes("@")) { setErrorMsg("Enter a valid email address."); return; }
    setSending(true); setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/health/auth/send-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
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
      const res = await fetch(`${API}/api/health/auth/verify-otp`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: code.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Invalid code."); setVerifying(false); return; }
      if (!data.needs_signup) {
        // Already has account — log them in
        localStorage.setItem("health_token", data.token);
        localStorage.setItem("health_user", JSON.stringify(data.user));
        window.location.href = "/";
        return;
      }
      setStep("profile");
    } catch { setErrorMsg("Verification failed. Please try again."); }
    setVerifying(false);
  };

  const handleCreateAccount = async () => {
    if (!fullName.trim()) { setErrorMsg("Enter your name."); return; }
    setCreating(true); setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/health/auth/signup`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), full_name: fullName.trim() }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to create account."); setCreating(false); return; }
      localStorage.setItem("health_token", data.token);
      localStorage.setItem("health_user", JSON.stringify(data.user));
      setStep("plan");
    } catch { setErrorMsg("Failed to create account. Please try again."); }
    setCreating(false);
  };

  const handleSelectPlan = async (plan) => {
    setCheckoutLoading(plan); setErrorMsg("");
    const authToken = localStorage.getItem("health_token");
    try {
      const res = await fetch(`${API}/api/health/auth/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${authToken}` },
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to start checkout."); setCheckoutLoading(null); return; }
      window.location.href = data.checkout_url;
    } catch { setErrorMsg("Failed to start checkout. Please try again."); setCheckoutLoading(null); }
  };

  const handleSkipPlan = () => {
    window.location.href = "/";
  };

  const isHealthSubdomain = window.location.hostname === "health.civicscale.ai";
  const loginPath = isHealthSubdomain ? "/health/login" : "/parity-health/login";
  const homePath = isHealthSubdomain ? "/" : "/parity-health";

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
        <a href={homePath} style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>P</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em" }}>Parity Health</span>
        </a>
        <nav style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 14 }}>
          <Link to={loginPath} style={{ color: "#94a3b8", textDecoration: "none" }}>Sign In</Link>
        </nav>
      </header>

      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
        <div style={{ width: "100%", maxWidth: 440, padding: "0 16px" }}>

          {/* Step 1: Email */}
          {step === "email" && (
            <>
              <div style={{ textAlign: "center", marginBottom: 32 }}>
                <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Create your account</h1>
                <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 15, lineHeight: 1.6 }}>
                  Parity Health — AI-powered medical bill analysis
                </p>
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>Email *</label>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendOtp()}
                  placeholder="you@example.com" style={inputStyle} />
              </div>
              <button onClick={handleSendOtp} disabled={sending} style={{
                width: "100%", padding: "12px", borderRadius: 8, border: "none",
                cursor: sending ? "default" : "pointer",
                background: sending ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                color: "#fff", fontWeight: 700, fontSize: 15, marginBottom: 12,
              }}>{sending ? "Sending code..." : "Continue"}</button>
              <p style={{ textAlign: "center", fontSize: 14, color: "#64748b", marginTop: 16 }}>
                Already have an account?{" "}
                <Link to={loginPath} style={{ color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>Sign in &rarr;</Link>
              </p>
              <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  "3 free bill analyses — no credit card needed",
                  "Instant AI analysis of medical bills, EOBs, and denials",
                  "Subscribe for unlimited access from $9.95/mo",
                ].map(t => <p key={t} style={{ fontSize: 13, color: "#475569", margin: 0 }}>&#10003; {t}</p>)}
              </div>
            </>
          )}

          {/* Step 2: OTP */}
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

          {/* Step 3: Profile */}
          {step === "profile" && (
            <>
              <h3 style={{ fontSize: 20, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px", textAlign: "center" }}>Almost there</h3>
              <p style={{ fontSize: 14, color: "#94a3b8", textAlign: "center", marginBottom: 24 }}>Tell us your name so we can personalize your experience.</p>
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>Full name *</label>
                <input type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateAccount()}
                  placeholder="Jane Smith" style={inputStyle} />
              </div>
              <button onClick={handleCreateAccount} disabled={creating} style={{
                width: "100%", padding: "12px", borderRadius: 8, border: "none",
                cursor: creating ? "default" : "pointer",
                background: creating ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                color: "#fff", fontWeight: 700, fontSize: 15,
              }}>{creating ? "Creating account..." : "Create Account"}</button>
            </>
          )}

          {/* Step 4: Plan selection */}
          {step === "plan" && (
            <>
              <div style={{ textAlign: "center", marginBottom: 28 }}>
                <h2 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Choose your plan</h2>
                <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 14 }}>
                  You get 3 free analyses. Subscribe for unlimited access.
                </p>
              </div>

              <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
                {/* Monthly */}
                <div style={{
                  flex: 1, minWidth: 180, padding: 20, borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.12)", background: "rgba(255,255,255,0.04)",
                }}>
                  <p style={{ fontSize: 13, color: "#94a3b8", margin: "0 0 4px", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>Monthly</p>
                  <p style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px" }}>$9.95<span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 400 }}>/mo</span></p>
                  <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 16px" }}>30-day free trial</p>
                  <button onClick={() => handleSelectPlan("monthly")} disabled={checkoutLoading === "monthly"} style={{
                    width: "100%", padding: "10px", borderRadius: 8, border: "none",
                    cursor: checkoutLoading ? "default" : "pointer",
                    background: checkoutLoading === "monthly" ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                    color: "#fff", fontWeight: 700, fontSize: 14,
                  }}>{checkoutLoading === "monthly" ? "Loading..." : "Start Trial"}</button>
                </div>

                {/* Yearly */}
                <div style={{
                  flex: 1, minWidth: 180, padding: 20, borderRadius: 12,
                  border: "1px solid #0d9488", background: "rgba(13,148,136,0.08)",
                  position: "relative",
                }}>
                  <div style={{
                    position: "absolute", top: -10, right: 12, background: "#0d9488", color: "#fff",
                    fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
                  }}>BEST VALUE</div>
                  <p style={{ fontSize: 13, color: "#94a3b8", margin: "0 0 4px", fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>Yearly</p>
                  <p style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: "0 0 4px" }}>$29<span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 400 }}>/yr</span></p>
                  <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 16px" }}>Save 76% — 30-day trial</p>
                  <button onClick={() => handleSelectPlan("yearly")} disabled={checkoutLoading === "yearly"} style={{
                    width: "100%", padding: "10px", borderRadius: 8, border: "none",
                    cursor: checkoutLoading ? "default" : "pointer",
                    background: checkoutLoading === "yearly" ? "#334155" : "linear-gradient(135deg, #0d9488, #14b8a6)",
                    color: "#fff", fontWeight: 700, fontSize: 14,
                  }}>{checkoutLoading === "yearly" ? "Loading..." : "Start Trial"}</button>
                </div>
              </div>

              <button onClick={handleSkipPlan} style={{
                width: "100%", padding: "10px", borderRadius: 8,
                border: "1px solid rgba(255,255,255,0.12)", background: "transparent",
                color: "#94a3b8", fontSize: 14, cursor: "pointer",
              }}>Skip for now — use 3 free analyses</button>
            </>
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
