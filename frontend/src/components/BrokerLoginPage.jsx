import { useState, useCallback, useEffect, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function BrokerLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
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
      const res = await fetch(`${API}/api/broker/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to send code.");
      }

      setStatus("code");
    } catch (err) {
      setStatus("error");
      setErrorMsg(err.message);
    }
  }, [email]);

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

      {/* LOGIN FORM */}
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
        <div style={{ width: "100%", maxWidth: 400, padding: "0 16px" }}>
          <div style={{ textAlign: "center", marginBottom: 40 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>
              Broker Portal
            </h1>
            <p style={{ color: "#64748b", marginTop: 8, fontSize: 15 }}>
              Sign in to manage your employer clients
            </p>
          </div>

          {status === "verifying" ? (
            <div style={{ textAlign: "center", padding: 32 }}>
              <div style={{
                width: 40, height: 40, border: "3px solid #e2e8f0", borderTopColor: "#0D7377",
                borderRadius: "50%", animation: "cs-spin 0.8s linear infinite", margin: "0 auto 16px",
              }} />
              <p style={{ color: "#1B3A5C", fontWeight: 600, fontSize: 15 }}>
                Verifying broker access...
              </p>
              <style>{`@keyframes cs-spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          ) : status === "code" ? (
            <BrokerOtpInput
              email={email}
              onVerified={(broker) => {
                localStorage.setItem("broker_session", JSON.stringify(broker));
                navigate("/broker/dashboard");
              }}
              onBack={() => { setStatus("idle"); setErrorMsg(""); }}
            />
          ) : (
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={{
                  display: "block", fontSize: 14, fontWeight: 500,
                  color: "#1B3A5C", marginBottom: 6,
                }}>
                  Email address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="broker@yourfirm.com"
                  style={{
                    width: "100%", padding: "10px 12px", borderRadius: 8,
                    border: "1px solid #e2e8f0", fontSize: 15,
                    outline: "none", boxSizing: "border-box",
                  }}
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

              <button
                type="submit"
                disabled={status === "sending"}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: status === "sending" ? 0.6 : 1,
                }}
              >
                {status === "sending" ? "Sending..." : "Send Code"}
              </button>

              <p style={{ textAlign: "center", fontSize: 13, color: "#64748b", marginTop: 16 }}>
                We'll send you a 6-digit code — no password needed.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}


// ---------------------------------------------------------------------------
// BrokerOtpInput — custom OTP component using backend endpoints (not Supabase)
// ---------------------------------------------------------------------------

function BrokerOtpInput({ email, onVerified, onBack }) {
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
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

    if (digit && index < 5) {
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
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;

    const next = [...otp];
    for (let i = 0; i < 6; i++) {
      next[i] = pasted[i] || "";
    }
    setOtp(next);

    const focusIdx = Math.min(pasted.length, 5);
    otpRefs.current[focusIdx]?.focus();

    if (pasted.length === 6) {
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
      setOtp(["", "", "", "", "", ""]);
      otpRefs.current[0]?.focus();
    }
  }

  async function handleResend() {
    if (resendCountdown > 0) return;
    setSending(true);
    setError(null);

    try {
      const res = await fetch(`${API}/api/broker/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to resend.");
      }

      setResendCountdown(60);
      setOtp(["", "", "", "", "", ""]);
      setResent(true);
      setTimeout(() => setResent(false), 3000);
      otpRefs.current[0]?.focus();
    } catch (err) {
      setError(err.message);
    }
    setSending(false);
  }

  const inputStyle = {
    width: 42, height: 48, textAlign: "center", fontSize: 18, fontWeight: 600,
    border: "1px solid #cbd5e1", borderRadius: 8, outline: "none",
    transition: "border-color 0.2s",
  };

  return (
    <div style={{
      padding: 24, borderRadius: 12, border: "1px solid #0D7377",
      background: "#f0fdfa", textAlign: "center",
    }}>
      <p style={{ fontSize: 14, color: "#475569", marginBottom: 4 }}>
        We sent a 6-digit code to <strong>{email}</strong>.
      </p>
      <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 20 }}>
        Check your inbox and enter it below. The code expires in 10 minutes.
      </p>

      {error && (
        <div style={{
          marginBottom: 16, padding: 10, background: "#fef2f2",
          border: "1px solid #fecaca", borderRadius: 8, fontSize: 13, color: "#991b1b",
        }}>
          {error}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "center", gap: 8, marginBottom: 16 }} onPaste={handleOtpPaste}>
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
            style={inputStyle}
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
