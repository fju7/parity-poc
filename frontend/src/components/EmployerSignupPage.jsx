import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LogoIcon } from "./CivicScaleHomepage.jsx";

import { API_BASE as API } from "../lib/apiBase";
const INDUSTRIES = [
  "Agriculture, forestry, fishing",
  "Mining",
  "Construction",
  "Manufacturing",
  "Wholesale trade",
  "Retail trade",
  "Finance, insurance, real estate",
  "Services",
  "Public administration",
];

const STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN",
  "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
  "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
  "VT","VA","WA","WV","WI","WY",
];

const SIZE_BANDS = [
  "Under 50 employees",
  "50-199 employees",
  "200-999 employees",
  "1,000-4,999 employees",
  "5,000+ employees",
];

export default function EmployerSignupPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  // Step: "email" | "otp" | "company"
  const [step, setStep] = useState("email");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [usePhone, setUsePhone] = useState(false);
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Company fields
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [industry, setIndustry] = useState("");
  const [state, setState] = useState("");
  const [sizeBand, setSizeBand] = useState("");

  const handleSendOtp = async () => {
    if (usePhone) {
      if (!phone.trim()) { setErrorMsg("Enter your phone number."); return; }
    } else {
      if (!email.includes("@")) { setErrorMsg("Enter a valid email address."); return; }
    }
    setSending(true);
    setErrorMsg("");
    try {
      const payload = usePhone
        ? { phone: phone.trim(), product: "employer" }
        : { email: email.trim().toLowerCase(), product: "employer" };
      const res = await fetch(`${API}/api/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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
    if (code.length !== 8) { setErrorMsg(`Enter the 8-digit code from your ${usePhone ? "phone" : "email"}.`); return; }
    setVerifying(true);
    setErrorMsg("");
    try {
      const payload = usePhone
        ? { phone: phone.trim(), code: code.trim(), product: "employer" }
        : { email: email.trim().toLowerCase(), code: code.trim(), product: "employer" };
      const res = await fetch(`${API}/api/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Invalid code."); return; }

      if (data.needs_company) {
        setStep("company");
      } else {
        // Already has a company — log in and redirect
        login(data.token, data.user, data.company);
        navigate("/billing/employer/dashboard");
      }
    } catch {
      setErrorMsg("Verification failed. Please try again.");
    } finally {
      setVerifying(false);
    }
  };

  const handleCreateCompany = async () => {
    if (!fullName.trim()) { setErrorMsg("Enter your full name."); return; }
    if (!companyName.trim()) { setErrorMsg("Enter your company name."); return; }
    setCreating(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/auth/company`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          full_name: fullName.trim(),
          company_name: companyName.trim(),
          company_type: "employer",
          industry: industry || null,
          state: state || null,
          size_band: sizeBand || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) { setErrorMsg(data.detail || "Failed to create account."); return; }

      // Token returned from company creation — log in immediately
      login(data.token, data.user, data.company);
      navigate("/billing/employer/dashboard");
    } catch {
      setErrorMsg("Failed to create account. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  const inputStyle = {
    width: "100%", padding: "12px 16px", background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px",
    color: "white", fontSize: "16px", marginBottom: "12px", boxSizing: "border-box",
  };

  const selectStyle = {
    ...inputStyle, appearance: "none", cursor: "pointer",
  };

  const btnStyle = (disabled) => ({
    width: "100%", padding: "12px", background: "#0d9488", color: "white",
    border: "none", borderRadius: "8px", fontSize: "16px", fontWeight: "600",
    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.7 : 1,
  });

  return (
    <div style={{ minHeight: "100vh", background: "#0a0f1e", display: "flex",
                   alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "16px", padding: "48px", maxWidth: "480px", width: "100%" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
          <LogoIcon size={28} />
          <span style={{ color: "#0d9488", fontSize: 14, fontWeight: 600, textTransform: "uppercase", letterSpacing: 1 }}>
            Parity Employer
          </span>
        </div>

        {step === "email" && (
          <>
            <h2 style={{ color: "white", fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
              Create your account
            </h2>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginBottom: 32 }}>
              {usePhone ? "Enter your phone number to get started." : "Enter your work email to get started."}
            </p>
            {usePhone ? (
              <input type="tel" placeholder="+1 (555) 555-5555" value={phone}
                onChange={e => setPhone(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSendOtp()}
                style={inputStyle} />
            ) : (
              <input type="email" placeholder="your@company.com" value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSendOtp()}
                style={inputStyle} />
            )}
            <button type="button" onClick={() => { setUsePhone(!usePhone); setErrorMsg(""); }}
              style={{ fontSize: 12, color: "#14b8a6", background: "none", border: "none", cursor: "pointer", marginTop: 6, padding: 0, marginBottom: 12 }}>
              {usePhone ? "Use email instead \u2192" : "Use phone number instead \u2192"}
            </button>
            <button onClick={handleSendOtp} disabled={sending} style={btnStyle(sending)}>
              {sending ? "Sending..." : "Send Verification Code"}
            </button>
            <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 13, textAlign: "center", marginTop: 16 }}>
              Already have an account?{" "}
              <span onClick={() => navigate("/billing/employer/dashboard")}
                style={{ color: "#0d9488", cursor: "pointer" }}>Sign in</span>
            </p>
          </>
        )}

        {step === "otp" && (
          <>
            <h2 style={{ color: "white", fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
              {usePhone ? "Check your phone" : "Check your email"}
            </h2>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginBottom: 32 }}>
              We sent an 8-digit code to {usePhone ? phone : email}.
            </p>
            <input type="text" placeholder="12345678" value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
              onKeyDown={e => e.key === "Enter" && handleVerifyOtp()}
              maxLength={8}
              style={{ ...inputStyle, fontSize: 24, letterSpacing: 8, textAlign: "center" }} />
            <button onClick={handleVerifyOtp} disabled={verifying} style={btnStyle(verifying)}>
              {verifying ? "Verifying..." : "Continue"}
            </button>
            <button onClick={() => { setStep("email"); setCode(""); setErrorMsg(""); }}
              style={{ width: "100%", padding: 10, background: "transparent",
                       color: "rgba(255,255,255,0.4)", border: "none", fontSize: 14,
                       cursor: "pointer", marginTop: 8 }}>
              {usePhone ? "Use a different phone number" : "Use a different email"}
            </button>
          </>
        )}

        {step === "company" && (
          <>
            <h2 style={{ color: "white", fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
              Set up your Parity Employer account
            </h2>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 14, marginBottom: 24 }}>
              Tell us about your company so we can customize your experience.
            </p>
            <input type="text" placeholder="Your full name" value={fullName}
              onChange={e => setFullName(e.target.value)} style={inputStyle} />
            <input type="text" placeholder="Company name" value={companyName}
              onChange={e => setCompanyName(e.target.value)} style={inputStyle} />
            <select value={industry} onChange={e => setIndustry(e.target.value)} style={selectStyle}>
              <option value="">Industry (optional)</option>
              {INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
            </select>
            <select value={state} onChange={e => setState(e.target.value)} style={selectStyle}>
              <option value="">State (optional)</option>
              {STATES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={sizeBand} onChange={e => setSizeBand(e.target.value)} style={selectStyle}>
              <option value="">Company size (optional)</option>
              {SIZE_BANDS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <button onClick={handleCreateCompany} disabled={creating} style={btnStyle(creating)}>
              {creating ? "Creating..." : "Create Account"}
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
