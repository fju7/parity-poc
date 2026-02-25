import { useState, useCallback, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { supabase } from "../lib/supabase.js";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

export default function EmployerLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("idle"); // idle | sending | sent | error | checking
  const [errorMsg, setErrorMsg] = useState("");

  // On mount, check if already authenticated and linked to an employer
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        checkEmployerAccess(session.user.email);
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        checkEmployerAccess(session.user.email);
      }
    });

    return () => subscription.unsubscribe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkEmployerAccess = useCallback(async (userEmail) => {
    setStatus("checking");
    try {
      const { data } = await supabase
        .from("employer_users")
        .select("employer_id, employer_accounts(company_name)")
        .eq("email", userEmail)
        .single();

      if (data && data.employer_id) {
        const companyName = data.employer_accounts?.company_name || "Your Company";
        localStorage.setItem("employer_session", JSON.stringify({
          employer_id: data.employer_id,
          company_name: companyName,
          email: userEmail,
        }));
        navigate("/employer/dashboard");
      } else {
        setStatus("error");
        setErrorMsg("This email is not registered as an employer account. Contact CivicScale at hello@civicscale.ai to get started.");
      }
    } catch {
      setStatus("error");
      setErrorMsg("This email is not registered as an employer account. Contact CivicScale at hello@civicscale.ai to get started.");
    }
  }, [navigate]);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    setStatus("sending");
    setErrorMsg("");

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin + "/employer/login" },
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

          {status === "checking" && (
            <div style={{
              padding: 24, borderRadius: 12, border: "1px solid var(--cs-border)",
              textAlign: "center", background: "var(--cs-mist)"
            }}>
              <p style={{ color: "var(--cs-navy)", fontWeight: 600 }}>Verifying access...</p>
            </div>
          )}

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
          ) : status !== "checking" && (
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
