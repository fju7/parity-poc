import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function BrokerSignupPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [firmName, setFirmName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | code | verifying | error
  const [errorMsg, setErrorMsg] = useState("");

  // If there's already a broker session, go to dashboard
  useEffect(() => {
    const stored = localStorage.getItem("broker_session");
    if (stored) {
      navigate("/broker/dashboard");
    }
  }, [navigate]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setStatus("sending");
    setErrorMsg("");

    try {
      const res = await fetch(`${API}/api/broker/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, firm_name: firmName, phone: phone || null }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to create account.");
      }

      setStatus("code");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err.message);
    }
  }, [email, name, firmName, phone]);

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
              Join Parity Employer
            </h1>
            <p style={{ color: "#64748b", marginTop: 8, fontSize: 15, lineHeight: 1.6 }}>
              Free for benefits brokers. Benchmark your clients' plans and share results before renewal.
            </p>
          </div>

          {status === "verifying" ? (
            <div style={{ textAlign: "center", padding: 32 }}>
              <div style={{
                width: 40, height: 40, border: "3px solid #e2e8f0", borderTopColor: "#0D7377",
                borderRadius: "50%", animation: "cs-spin 0.8s linear infinite", margin: "0 auto 16px",
              }} />
              <p style={{ color: "#1B3A5C", fontWeight: 600, fontSize: 15 }}>
                Verifying your account...
              </p>
              <style>{`@keyframes cs-spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          ) : status === "code" ? (
            <SignupOtpInput
              email={email}
              onVerified={(broker) => {
                localStorage.setItem("broker_session", JSON.stringify(broker));
                navigate("/broker/dashboard");
              }}
              onBack={() => { setStatus("idle"); setErrorMsg(""); }}
            />
          ) : (
            <>
              <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: 14 }}>
                  <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#1B3A5C", marginBottom: 6 }}>
                    Full name *
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
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

                <div style={{ marginBottom: 14 }}>
                  <label style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#1B3A5C", marginBottom: 6 }}>
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane@acmebenefits.com"
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

                {status === "error" && (
                  <div style={{
                    padding: 12, borderRadius: 8, background: "#fef2f2",
                    border: "1px solid #fecaca", marginBottom: 16,
                  }}>
                    <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{errorMsg}</p>
                  </div>
                )}

                <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 12px", textAlign: "center" }}>
                  We will never contact your clients directly. Your book of business is yours.
                </p>

                <button
                  type="submit"
                  disabled={status === "sending"}
                  className="cs-btn-primary"
                  style={{
                    width: "100%", justifyContent: "center",
                    opacity: status === "sending" ? 0.6 : 1,
                  }}
                >
                  {status === "sending" ? "Creating account..." : "Create Free Account \u2192"}
                </button>
              </form>

              <p style={{ textAlign: "center", fontSize: 14, color: "#64748b", marginTop: 20 }}>
                Already have an account?{" "}
                <Link to="/broker/login" style={{ color: "#0D7377", textDecoration: "none", fontWeight: 600 }}>
                  Sign in &rarr;
                </Link>
              </p>

              <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  "\u2713 Free for brokers \u2014 your clients pay if they subscribe",
                  "\u2713 Benchmark any employer in 60 seconds",
                  "\u2713 Share results with no login required for your clients",
                ].map((text) => (
                  <p key={text} style={{ fontSize: 13, color: "#94a3b8", margin: 0 }}>{text}</p>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1px solid #e2e8f0", fontSize: 15,
  outline: "none", boxSizing: "border-box",
};


// ---------------------------------------------------------------------------
// SignupOtpInput — 8-digit OTP verification for signup flow
// ---------------------------------------------------------------------------

function SignupOtpInput({ email, onVerified, onBack }) {
  const OTP_LENGTH = 8;
  const [otp, setOtp] = useState(Array(OTP_LENGTH).fill(""));
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [resendCountdown, setResendCountdown] = useState(60);
  const [resent, setResent] = useState(false);
  const otpRefs = useRef([]);

  useEffect(() => {
    if (resendCountdown <= 0) return;
    const t = setTimeout(() => setResendCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCountdown]);

  useEffect(() => {
    setTimeout(() => otpRefs.current[0]?.focus(), 50);
  }, []);

  function handleOtpChange(index, value) {
    const digit = value.replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[index] = digit;
    setOtp(next);

    if (digit && index < OTP_LENGTH - 1) {
      otpRefs.current[index + 1]?.focus();
    }

    if (next.every((d) => d)) {
      verifyOtp(next.join(""));
    }
  }

  function handleOtpKeyDown(index, e) {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
  }

  function handleOtpPaste(e) {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LENGTH);
    if (!pasted) return;

    const next = [...otp];
    for (let i = 0; i < OTP_LENGTH; i++) {
      next[i] = pasted[i] || "";
    }
    setOtp(next);

    const focusIdx = Math.min(pasted.length, OTP_LENGTH - 1);
    otpRefs.current[focusIdx]?.focus();

    if (pasted.length === OTP_LENGTH) {
      verifyOtp(pasted);
    }
  }

  async function verifyOtp(code) {
    setSending(true);
    setError(null);

    try {
      const res = await fetch(`${API}/api/broker/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid code.");
      }

      const data = await res.json();
      setSending(false);
      onVerified(data.broker);
    } catch (err) {
      setSending(false);
      setError(err.message);
      setOtp(Array(OTP_LENGTH).fill(""));
      otpRefs.current[0]?.focus();
    }
  }

  async function handleResend() {
    if (resendCountdown > 0) return;
    setSending(true);
    setError(null);

    try {
      const res = await fetch(`${API}/api/broker/auth/resend-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to resend.");
      }

      setResendCountdown(60);
      setOtp(Array(OTP_LENGTH).fill(""));
      setResent(true);
      setTimeout(() => setResent(false), 3000);
      otpRefs.current[0]?.focus();
    } catch (err) {
      setError(err.message);
    }
    setSending(false);
  }

  const otpInputStyle = {
    width: 36, height: 44, textAlign: "center", fontSize: 17, fontWeight: 600,
    border: "1px solid #cbd5e1", borderRadius: 8, outline: "none",
    transition: "border-color 0.2s",
  };

  return (
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

      {error && (
        <div style={{
          marginBottom: 16, padding: 10, background: "#fef2f2",
          border: "1px solid #fecaca", borderRadius: 8, fontSize: 13, color: "#991b1b",
        }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "center", gap: 6, marginBottom: 16 }} onPaste={handleOtpPaste}>
        {otp.map((digit, i) => (
          <input
            key={i}
            ref={(el) => (otpRefs.current[i] = el)}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={digit}
            onChange={(e) => handleOtpChange(i, e.target.value)}
            onKeyDown={(e) => handleOtpKeyDown(i, e)}
            style={otpInputStyle}
            onFocus={(e) => { e.target.style.borderColor = "#0D7377"; }}
            onBlur={(e) => { e.target.style.borderColor = "#cbd5e1"; }}
          />
        ))}
      </div>

      {sending && (
        <p style={{ fontSize: 14, color: "#94a3b8", marginBottom: 12 }}>Verifying...</p>
      )}

      {resent && !error && (
        <p style={{ fontSize: 14, color: "#0D7377", marginBottom: 12 }}>New code sent!</p>
      )}

      <div style={{ fontSize: 14, marginBottom: 12 }}>
        {resendCountdown > 0 ? (
          <span style={{ color: "#94a3b8" }}>Resend code in {resendCountdown}s</span>
        ) : (
          <button
            onClick={handleResend}
            disabled={sending}
            style={{
              color: "#0D7377", background: "none", border: "none",
              cursor: "pointer", fontSize: 14, textDecoration: "underline",
            }}
          >
            {sending ? "Sending..." : "Resend code"}
          </button>
        )}
      </div>

      <button
        onClick={onBack}
        style={{
          fontSize: 12, color: "#94a3b8", background: "none",
          border: "none", cursor: "pointer",
        }}
      >
        Use a different email
      </button>
    </div>
  );
}
