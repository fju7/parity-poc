import { useState } from "react";
import { useAuth } from "../context/AuthContext";

const API = import.meta.env.VITE_API_URL || "https://parity-poc-api.onrender.com";

/**
 * Wraps any protected page. If not authenticated, shows OTP login inline.
 * Props:
 *   product: 'employer' | 'broker' | 'provider'
 *   onNeedsCompany: callback when user verified but has no company yet
 *   children: rendered when authenticated
 */
export default function AuthGate({ product, onNeedsCompany, children }) {
  const { isAuthenticated, loading, login, company } = useAuth();
  const [step, setStep] = useState("email"); // email | otp | done
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // If product type doesn't match current session company type, still show login
  const productMatches = company?.type === product ||
    (product === "broker" && company?.type === "broker");

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: "#0a0f1e", display: "flex",
                     alignItems: "center", justifyContent: "center" }}>
        <div style={{ color: "#0d9488", fontSize: "18px" }}>Loading...</div>
      </div>
    );
  }

  if (isAuthenticated && productMatches) return children;

  const handleSendOtp = async () => {
    if (!email.includes("@")) { setErrorMsg("Enter a valid email address."); return; }
    setSending(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), product }),
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
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: code.trim(), product }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Invalid code."); return; }

      if (data.needs_company) {
        // User verified but no company yet — hand off to signup flow
        if (onNeedsCompany) onNeedsCompany(email.trim().toLowerCase());
        return;
      }

      login(data.token, data.user, data.company);
    } catch {
      setErrorMsg("Verification failed. Please try again.");
    } finally {
      setVerifying(false);
    }
  };

  const productLabels = {
    employer: "Parity Employer",
    broker: "Broker Portal",
    provider: "Parity Provider",
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1e", display: "flex",
                   alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "16px", padding: "48px", maxWidth: "420px", width: "100%" }}>
        <div style={{ color: "#0d9488", fontSize: "14px", fontWeight: "600",
                       textTransform: "uppercase", letterSpacing: "1px", marginBottom: "8px" }}>
          {productLabels[product] || "CivicScale"}
        </div>
        <h2 style={{ color: "white", fontSize: "24px", fontWeight: "700", marginBottom: "8px" }}>
          {step === "email" ? "Sign in to your account" : "Check your email"}
        </h2>
        <p style={{ color: "rgba(255,255,255,0.5)", fontSize: "14px", marginBottom: "32px" }}>
          {step === "email"
            ? "Enter your email to receive a sign-in code."
            : `We sent an 8-digit code to ${email}. Enter it below.`}
        </p>

        {step === "email" && (
          <>
            <input
              type="email"
              placeholder="your@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSendOtp()}
              style={{ width: "100%", padding: "12px 16px", background: "rgba(255,255,255,0.05)",
                       border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px",
                        color: "white", fontSize: "16px", marginBottom: "12px", boxSizing: "border-box" }}
            />
            <button
              onClick={handleSendOtp}
              disabled={sending}
              style={{ width: "100%", padding: "12px", background: "#0d9488", color: "white",
                       border: "none", borderRadius: "8px", fontSize: "16px", fontWeight: "600",
                       cursor: sending ? "not-allowed" : "pointer", opacity: sending ? 0.7 : 1 }}
            >
              {sending ? "Sending..." : "Send Sign-In Code"}
            </button>
          </>
        )}

        {step === "otp" && (
          <>
            <input
              type="text"
              placeholder="12345678"
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
              onKeyDown={e => e.key === "Enter" && handleVerifyOtp()}
              maxLength={8}
              style={{ width: "100%", padding: "12px 16px", background: "rgba(255,255,255,0.05)",
                       border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "white",
                       fontSize: "24px", letterSpacing: "8px", textAlign: "center",
                        marginBottom: "12px", boxSizing: "border-box" }}
            />
            <button
              onClick={handleVerifyOtp}
              disabled={verifying}
              style={{ width: "100%", padding: "12px", background: "#0d9488", color: "white",
                       border: "none", borderRadius: "8px", fontSize: "16px", fontWeight: "600",
                       cursor: verifying ? "not-allowed" : "pointer", opacity: verifying ? 0.7 : 1 }}
            >
              {verifying ? "Verifying..." : "Sign In"}
            </button>
            <button
              onClick={() => { setStep("email"); setCode(""); setErrorMsg(""); }}
              style={{ width: "100%", padding: "10px", background: "transparent", color: "rgba(255,255,255,0.4)",
                       border: "none", fontSize: "14px", cursor: "pointer", marginTop: "8px" }}
            >
              Use a different email
            </button>
          </>
        )}

        {errorMsg && (
          <p style={{ color: "#f87171", fontSize: "14px", marginTop: "12px", textAlign: "center" }}>
            {errorMsg}
          </p>
        )}

        <p style={{ color: "rgba(255,255,255,0.3)", fontSize: "12px", textAlign: "center",
                     marginTop: "24px" }}>
          No password required. We use secure one-time codes.
        </p>
      </div>
    </div>
  );
}
