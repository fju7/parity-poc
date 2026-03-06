import { useState, useCallback, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { supabase } from "../lib/supabase.js";
import EmailOtpInput from "./EmailOtpInput.jsx";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const ERROR_MESSAGES = {
  not_registered: "This email is not registered as an employer account. Contact CivicScale at hello@civicscale.ai to get started.",
  auth_timeout: "Sign-in timed out. Please try again.",
};

export default function EmployerLoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | code | verifying | error
  const [errorMsg, setErrorMsg] = useState("");

  // Check for error params from callback redirect
  useEffect(() => {
    const errorCode = searchParams.get("error");
    if (errorCode && ERROR_MESSAGES[errorCode]) {
      setStatus("error");
      setErrorMsg(ERROR_MESSAGES[errorCode]);
    }
  }, [searchParams]);

  // If there's already an employer session in localStorage, go to dashboard
  useEffect(() => {
    const stored = localStorage.getItem("employer_session");
    if (stored) {
      navigate("/employer/dashboard");
    }
  }, [navigate]);

  // After OTP verification succeeds, Supabase fires onAuthStateChange.
  // We listen for it here to verify employer access inline.
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session && status === "code") {
        setStatus("verifying");
        try {
          const { data } = await supabase
            .from("employer_users")
            .select("employer_id, employer_accounts(company_name)")
            .eq("email", session.user.email)
            .single();

          if (data && data.employer_id) {
            const companyName = data.employer_accounts?.company_name || "Your Company";
            localStorage.setItem("employer_session", JSON.stringify({
              employer_id: data.employer_id,
              company_name: companyName,
              email: session.user.email,
            }));
            navigate("/employer/dashboard");
          } else {
            setStatus("error");
            setErrorMsg(ERROR_MESSAGES.not_registered);
          }
        } catch {
          setStatus("error");
          setErrorMsg(ERROR_MESSAGES.not_registered);
        }
      }
    });
    return () => subscription.unsubscribe();
  }, [navigate, status]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setStatus("sending");
    setErrorMsg("");

    const { error } = await supabase.auth.signInWithOtp({
      email,
    });

    if (error) {
      setStatus("error");
      setErrorMsg(error.message);
    } else {
      setStatus("code");
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
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
              Employer Dashboard
            </h1>
            <p style={{ color: "var(--cs-slate)", marginTop: 8, fontSize: 15 }}>
              Sign in to access your benefits analytics
            </p>
          </div>

          {status === "verifying" ? (
            <div style={{ textAlign: "center", padding: 32 }}>
              <div style={{
                width: 40, height: 40, border: "3px solid #e2e8f0", borderTopColor: "#0D7377",
                borderRadius: "50%", animation: "cs-spin 0.8s linear infinite", margin: "0 auto 16px",
              }} />
              <p style={{ color: "#1B3A5C", fontWeight: 600, fontSize: 15 }}>
                Verifying employer access...
              </p>
              <style>{`@keyframes cs-spin { to { transform: rotate(360deg); } }`}</style>
            </div>
          ) : status === "code" ? (
            <div style={{
              padding: 24, borderRadius: 12, border: "1px solid var(--cs-teal)",
              background: "var(--cs-teal-pale)", textAlign: "center"
            }}>
              <EmailOtpInput
                email={email}
                onBack={() => { setStatus("idle"); setErrorMsg(""); }}
              />
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={{
                  display: "block", fontSize: 14, fontWeight: 500,
                  color: "var(--cs-navy)", marginBottom: 6,
                }}>
                  Email address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="benefits@yourcompany.com"
                  style={{
                    width: "100%", padding: "10px 12px", borderRadius: 8,
                    border: "1px solid var(--cs-border)", fontSize: 15,
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

              <p style={{ textAlign: "center", fontSize: 13, color: "var(--cs-slate)", marginTop: 16 }}>
                We'll send you a secure code — no password needed.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
