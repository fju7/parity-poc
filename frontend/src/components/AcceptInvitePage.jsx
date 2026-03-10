import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogoIcon } from "./CivicScaleHomepage.jsx";

const API = import.meta.env.VITE_API_URL || "https://parity-poc-api.onrender.com";

const PRODUCT_DASHBOARDS = {
  employer: "/billing/employer/dashboard",
  broker: "/broker/dashboard",
  provider: "/provider",
};

export default function AcceptInvitePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const inviteToken = searchParams.get("token") || "";

  // Steps: "email" | "otp" | "name" | "done"
  const [step, setStep] = useState("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [accepting, setAccepting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [companyName, setCompanyName] = useState("");

  useEffect(() => {
    if (!inviteToken) setErrorMsg("No invitation token found. Please check the link in your email.");
  }, [inviteToken]);

  const inputStyle = {
    width: "100%", padding: "12px 16px", background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px",
    color: "white", fontSize: "16px", marginBottom: "12px", boxSizing: "border-box",
  };

  const btnStyle = (disabled) => ({
    width: "100%", padding: "12px", background: "#0d9488", color: "white",
    border: "none", borderRadius: "8px", fontSize: "16px", fontWeight: "600",
    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.7 : 1,
  });

  const handleSendOtp = async () => {
    if (!email.includes("@")) { setErrorMsg("Enter a valid email address."); return; }
    setSending(true);
    setErrorMsg("");
    try {
      // We use "employer" as default product for OTP — the invite will determine actual product
      const res = await fetch(`${API}/api/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), product: "employer" }),
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
    if (code.length !== 8) { setErrorMsg("Enter the 8-digit code."); return; }
    setVerifying(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), code: code.trim(), product: "employer" }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Invalid code."); return; }
      // Email verified — move to name step
      setStep("name");
    } catch {
      setErrorMsg("Verification failed. Please try again.");
    } finally {
      setVerifying(false);
    }
  };

  const handleAcceptInvite = async () => {
    if (!fullName.trim()) { setErrorMsg("Enter your full name."); return; }
    setAccepting(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/accept-invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: inviteToken,
          email: email.trim().toLowerCase(),
          full_name: fullName.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to accept invitation."); return; }

      const companyType = data.company?.type || "employer";
      setCompanyName(data.company?.name || "");

      login(data.token, { email: data.email, full_name: fullName.trim() }, data.company);

      const dashboard = PRODUCT_DASHBOARDS[companyType] || "/billing/employer/dashboard";
      navigate(dashboard);
    } catch {
      setErrorMsg("Failed to accept invitation. Please try again.");
    } finally {
      setAccepting(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1e", display: "flex",
                   alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "16px", padding: "48px", maxWidth: "420px", width: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
          <LogoIcon size={28} />
          <span style={{ color: "#0d9488", fontSize: 14, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
            CivicScale
          </span>
        </div>

        {step === "email" && (
          <>
            <h2 style={{ color: "white", fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
              You've been invited
            </h2>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginBottom: 32 }}>
              Verify your email to accept the invitation.
            </p>
            <input type="email" placeholder="your@email.com" value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSendOtp()}
              style={inputStyle} />
            <button onClick={handleSendOtp} disabled={sending || !inviteToken} style={btnStyle(sending || !inviteToken)}>
              {sending ? "Sending..." : "Send Verification Code"}
            </button>
          </>
        )}

        {step === "otp" && (
          <>
            <h2 style={{ color: "white", fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
              Check your email
            </h2>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginBottom: 32 }}>
              Enter the 8-digit code sent to {email}.
            </p>
            <input type="text" placeholder="12345678" value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
              onKeyDown={e => e.key === "Enter" && handleVerifyOtp()}
              maxLength={8}
              style={{ ...inputStyle, fontSize: 24, letterSpacing: 8, textAlign: "center" }} />
            <button onClick={handleVerifyOtp} disabled={verifying} style={btnStyle(verifying)}>
              {verifying ? "Verifying..." : "Continue"}
            </button>
          </>
        )}

        {step === "name" && (
          <>
            <h2 style={{ color: "white", fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
              Complete your profile
            </h2>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginBottom: 32 }}>
              Enter your name to join the team.
            </p>
            <input type="text" placeholder="Your full name" value={fullName}
              onChange={e => setFullName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAcceptInvite()}
              style={inputStyle} />
            <button onClick={handleAcceptInvite} disabled={accepting} style={btnStyle(accepting)}>
              {accepting ? "Joining..." : "Accept Invitation"}
            </button>
          </>
        )}

        {errorMsg && (
          <p style={{ color: "#f87171", fontSize: 14, marginTop: 12, textAlign: "center" }}>
            {errorMsg}
          </p>
        )}
      </div>
    </div>
  );
}
