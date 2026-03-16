import { useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

import { API_BASE as API } from "../lib/apiBase";
export default function BrokerSignupPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const refCode = searchParams.get("ref") || "";
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
          ...(refCode ? { referral_code: refCode } : {}),
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
    border: "1px solid rgba(255,255,255,0.12)", fontSize: 15,
    outline: "none", boxSizing: "border-box",
    background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
  };

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0", overflowX: "hidden", minHeight: "100vh", background: "#0a1628" }}>
      {/* NAV */}
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
          <a href="https://broker.civicscale.ai" style={{ color: "#94a3b8", textDecoration: "none" }}>For Brokers</a>
        </nav>
      </header>

      {/* SIGNUP FORM */}
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
        <div style={{ width: "100%", maxWidth: 420, padding: "0 16px" }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>
              Join Parity Broker
            </h1>
            <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 15, lineHeight: 1.6 }}>
              Start your 30-day free trial. $99/mo after trial &mdash; cancel anytime.
            </p>
          </div>

          {refCode && (
            <div style={{ background: "rgba(13,115,119,0.15)", border: "1px solid rgba(13,115,119,0.3)", borderRadius: 10, padding: "10px 16px", marginBottom: 16, textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: 13, color: "#5eead4" }}>You were referred by a colleague. Welcome to Parity Broker.</p>
            </div>
          )}

          {step === "email" && (
            <>
              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>
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
                  "\u2713 30-day free trial \u2014 cancel anytime",
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
              padding: 24, borderRadius: 12, border: "1px solid #0d9488",
              background: "rgba(13,148,136,0.08)", textAlign: "center",
            }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "0 0 8px" }}>
                Check your email
              </h3>
              <p style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 4 }}>
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
                  textAlign: "center", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8,
                  outline: "none", boxSizing: "border-box", marginBottom: 12,
                  background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
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
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "#cbd5e1", margin: "0 0 4px", textAlign: "center" }}>
                Set up your broker account
              </h3>
              <p style={{ fontSize: 14, color: "#64748b", textAlign: "center", marginBottom: 20 }}>
                Tell us about yourself and your firm.
              </p>

              <div style={{ marginBottom: 14 }}>
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>
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
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>
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
                <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#cbd5e1", marginBottom: 6 }}>
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
              padding: 12, borderRadius: 8, background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)", marginTop: 16,
            }}>
              <p style={{ color: "#fca5a5", fontSize: 13, margin: 0 }}>{errorMsg}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
