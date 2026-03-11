import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function BrokerLoginPage() {
  const navigate = useNavigate();
  const { login, isAuthenticated, company } = useAuth();

  // If already authenticated as broker, go to dashboard
  if (isAuthenticated && company?.type === "broker") {
    navigate("/broker/dashboard");
    return null;
  }

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState("email"); // email | otp
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

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
        // User verified but has no broker firm yet — redirect to signup to complete
        navigate("/broker/signup");
      } else {
        login(data.token, data.user, data.company);
        navigate("/broker/dashboard");
      }
    } catch {
      setErrorMsg("Verification failed. Please try again.");
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#e2e8f0", overflowX: "hidden", minHeight: "100vh", background: "#0a1628" }}>
      {/* NAV — matches EmployerProductPage header */}
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
          <Link to="/broker" style={{ color: "#94a3b8", textDecoration: "none" }}>For Brokers</Link>
        </nav>
      </header>

      {/* LOGIN FORM */}
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
        <div style={{ width: "100%", maxWidth: 400, padding: "0 16px" }}>
          <div style={{ textAlign: "center", marginBottom: 40 }}>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>
              Broker Portal
            </h1>
            <p style={{ color: "#94a3b8", marginTop: 8, fontSize: 15 }}>
              Sign in to manage your employer clients
            </p>
          </div>

          {step === "email" && (
            <form onSubmit={(e) => { e.preventDefault(); handleSendOtp(); }}>
              <div style={{ marginBottom: 16 }}>
                <label style={{
                  display: "block", fontSize: 14, fontWeight: 500,
                  color: "#cbd5e1", marginBottom: 6,
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
                    border: "1px solid rgba(255,255,255,0.12)", fontSize: 15,
                    outline: "none", boxSizing: "border-box",
                    background: "rgba(255,255,255,0.06)", color: "#f1f5f9",
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={sending}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: sending ? 0.6 : 1,
                }}
              >
                {sending ? "Sending..." : "Send Code"}
              </button>

              <p style={{ textAlign: "center", fontSize: 13, color: "#94a3b8", marginTop: 16 }}>
                We'll send you an 8-digit code — no password needed.
              </p>

              <p style={{ textAlign: "center", fontSize: 14, color: "#94a3b8", marginTop: 20 }}>
                Don't have an account?{" "}
                <Link to="/broker/signup" style={{ color: "#14b8a6", textDecoration: "none", fontWeight: 600 }}>
                  Start your free 30-day trial &rarr;
                </Link>
              </p>
            </form>
          )}

          {step === "otp" && (
            <div style={{
              padding: 24, borderRadius: 12, border: "1px solid #0d9488",
              background: "rgba(13,148,136,0.08)", textAlign: "center",
            }}>
              <p style={{ fontSize: 14, color: "#cbd5e1", marginBottom: 4 }}>
                We sent an 8-digit code to <strong>{email}</strong>.
              </p>
              <p style={{ fontSize: 12, color: "#94a3b8", marginBottom: 20 }}>
                Check your inbox and enter it below. The code expires in 10 minutes.
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
                {verifying ? "Verifying..." : "Sign In"}
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
