import { useState, useCallback, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { supabase } from "../lib/supabase.js";
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
  const [status, setStatus] = useState("idle"); // idle | sending | sent | error
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

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setStatus("sending");
    setErrorMsg("");

    const redirectUrl = window.location.origin + "/employer/auth/callback";
    console.log("[EmployerLogin] Sending magic link with redirect:", redirectUrl);

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: redirectUrl },
    });

    if (error) {
      setStatus("error");
      setErrorMsg(error.message);
    } else {
      setStatus("sent");
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

          {status === "sent" ? (
            <div style={{
              padding: 24, borderRadius: 12, border: "1px solid var(--cs-teal)",
              background: "var(--cs-teal-pale)", textAlign: "center"
            }}>
              <p style={{ color: "var(--cs-navy)", fontWeight: 600, marginBottom: 4 }}>
                Check your email
              </p>
              <p style={{ color: "var(--cs-slate)", fontSize: 14 }}>
                We sent a login link to <strong>{email}</strong>. Click it to sign in.
              </p>
              <button
                onClick={() => setStatus("idle")}
                style={{
                  marginTop: 16, background: "none", border: "none",
                  color: "var(--cs-teal)", cursor: "pointer", fontSize: 14,
                  textDecoration: "underline",
                }}
              >
                Use a different email
              </button>
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
                {status === "sending" ? "Sending..." : "Send Magic Link"}
              </button>

              <p style={{ textAlign: "center", fontSize: 13, color: "var(--cs-slate)", marginTop: 16 }}>
                We'll send you a secure login link — no password needed.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
