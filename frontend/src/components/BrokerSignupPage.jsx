import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function BrokerSignupPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, company } = useAuth();

  // If already authenticated as broker, go to dashboard
  if (isAuthenticated && company?.type === "broker") {
    navigate("/broker/dashboard");
    return null;
  }

  // Step: "email" | "otp" | "company"
  const [step, setStep] = useState("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Company fields
  const [fullName, setFullName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [phone, setPhone] = useState("");

  const handleSendOtp = async () => {
    if (!email.includes("@")) { setErrorMsg("Enter a valid email address."); return; }
    setSending(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), product: "broker" }),
      });
      if (!res.ok) throw new Error();
      setStep("otp");
    } catch {
      setErrorMsg("Failed to send code. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (code.length !== 8) { setErrorMsg("Enter the 8-digit code from your email."); return; }
    setVerifying(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: code.trim(), product: "broker" }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Invalid code."); return; }

      if (data.needs_company) {
        setStep("company");
      } else {
        // Already has a broker firm — log in and redirect
        login(data.token, data.user, data.company);
        navigate("/broker/dashboard");
      }
    } catch {
      setErrorMsg("Verification failed. Please try again.");
    } finally {
      setVerifying(false);
    }
  };

  const handleCreateCompany = async () => {
    if (!fullName.trim()) { setErrorMsg("Enter your full name."); return; }
    if (!firmName.trim()) { setErrorMsg("Enter your firm name."); return; }
    setCreating(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/company`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          full_name: fullName.trim(),
          company_name: firmName.trim(),
          company_type: "broker",
        }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to create account."); return; }

      // Token returned from company creation — log in immediately
      login(data.token, data.user, data.company);
      navigate("/broker/dashboard");
    } catch {
      setErrorMsg("Failed to create account. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  const inputStyle = {
    width: "100%", padding: "10px 12px", borderRadius: 8,
    border: "1px solid #e2e8f0", fontSize: 15,
    outline: "none", boxSizing: "border-box",
  };

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
      {/* NAV */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div className="cs-nav-links">
          <Link to="/employer">For Employers</Link>
        </div>
      </nav>

      {/* SIGNUP FORM */}
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
        <div style={{ width: "100%", maxWidth: 420, padding: "0 16px" }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>
              Join Parity Broker
            </h1>
            <p style={{ color: "#64748b", marginTop: 8, fontSize: 15, lineHeight: 1.6 }}>
              Start your 30-day free trial. $99/mo after trial &mdash; cancel anytime.
            </p>
          </div>

          {step === "email" && (
            <>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#1B3A5C", marginBottom: 6 }}>
                  Email *
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSendOtp()}
                  placeholder="jane@acmebenefits.com"
                  style={inputStyle}
                />
              </div>

              <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 12px", textAlign: "center" }}>
                We will never contact your clients directly. Your book of business is yours.
              </p>

              <button
                onClick={handleSendOtp}
                disabled={sending}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: sending ? 0.6 : 1,
                }}
              >
                {sending ? "Sending code..." : "Continue \u2192"}
              </button>

              <p style={{ textAlign: "center", fontSize: 14, color: "#64748b", marginTop: 20 }}>
                Already have an account?{" "}
                <Link to="/broker/login" style={{ color: "#0D7377", textDecoration: "none", fontWeight: 600 }}>
                  Sign in &rarr;
                </Link>
              </p>

              <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  "\u2713 30-day free trial \u2014 no credit card required",
                  "\u2713 Unlimited clients and benchmark analyses",
                  "\u2713 CAA letter generation, renewal prep, and Level 2 claims insights",
                ].map((text) => (
                  <p key={text} style={{ fontSize: 13, color: "#94a3b8", margin: 0 }}>{text}</p>
                ))}
              </div>
            </>
          )}

          {step === "otp" && (
            <div style={{
              padding: 24, borderRadius: 12, border: "1px solid #0D7377",
              background: "#f0fdfa", textAlign: "center",
            }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: "0 0 8px" }}>
                Check your email
              </h3>
              <p style={{ fontSize: 14, color: "#475569", marginBottom: 4 }}>
                We sent an 8-digit code to <strong>{email}</strong>.
              </p>
              <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 20 }}>
                Enter it below to verify your account. The code expires in 10 minutes.
              </p>

              <input
                type="text"
                placeholder="12345678"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
                onKeyDown={(e) => e.key === "Enter" && handleVerifyOtp()}
                maxLength={8}
                style={{
                  width: "100%", padding: "12px 16px", fontSize: 24, letterSpacing: 8,
                  textAlign: "center", border: "1px solid #cbd5e1", borderRadius: 8,
                  outline: "none", boxSizing: "border-box", marginBottom: 12,
                }}
              />

              <button
                onClick={handleVerifyOtp}
                disabled={verifying}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: verifying ? 0.6 : 1,
                }}
              >
                {verifying ? "Verifying..." : "Verify Code"}
              </button>

              <button
                onClick={() => { setStep("email"); setCode(""); setErrorMsg(""); }}
                style={{
                  fontSize: 12, color: "#94a3b8", background: "none",
                  border: "none", cursor: "pointer", marginTop: 12,
                }}
              >
                Use a different email
              </button>
            </div>
          )}

          {step === "company" && (
            <>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: "0 0 4px", textAlign: "center" }}>
                Set up your broker account
              </h3>
              <p style={{ fontSize: 14, color: "#64748b", textAlign: "center", marginBottom: 20 }}>
                Tell us about yourself and your firm.
              </p>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#1B3A5C", marginBottom: 6 }}>
                  Full name *
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jane Smith"
                  style={inputStyle}
                />
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#1B3A5C", marginBottom: 6 }}>
                  Firm name *
                </label>
                <input
                  type="text"
                  required
                  value={firmName}
                  onChange={(e) => setFirmName(e.target.value)}
                  placeholder="Acme Benefits Group"
                  style={inputStyle}
                />
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#1B3A5C", marginBottom: 6 }}>
                  Phone <span style={{ color: "#94a3b8", fontWeight: 400 }}>(optional)</span>
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="(555) 123-4567"
                  style={inputStyle}
                />
              </div>

              <button
                onClick={handleCreateCompany}
                disabled={creating}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: creating ? 0.6 : 1,
                }}
              >
                {creating ? "Creating account..." : "Start Free Trial \u2192"}
              </button>
            </>
          )}

          {errorMsg && (
            <div style={{
              padding: 12, borderRadius: 8, background: "#fef2f2",
              border: "1px solid #fecaca", marginTop: 16,
            }}>
              <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{errorMsg}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
