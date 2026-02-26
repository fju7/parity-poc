import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { supabase } from "./lib/supabase.js";
import { LogoIcon } from "./components/CivicScaleHomepage.jsx";
import "./components/CivicScaleHomepage.css";

const SPECIALTIES = [
  "Internal Medicine",
  "Family Medicine",
  "Cardiology",
  "Orthopedics",
  "Dermatology",
  "Radiology",
  "Pathology/Lab",
  "Other",
];

export default function ProviderApp() {
  // "landing" | "sent" | "onboarding" | "dashboard"
  const [view, setView] = useState(null);
  const [session, setSession] = useState(null);
  const [profile, setProfile] = useState(null);
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [authError, setAuthError] = useState("");
  const [activeTab, setActiveTab] = useState("contract");

  // Onboarding form state
  const [formData, setFormData] = useState({
    practice_name: "",
    specialty: "",
    npi: "",
    zip_code: "",
  });
  const [formError, setFormError] = useState("");
  const [formSaving, setFormSaving] = useState(false);

  // Auth bootstrap
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      if (s) {
        setSession(s);
        loadProfile(s.user.id);
      } else {
        setView("landing");
      }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, s) => {
      if (s) {
        setSession(s);
        loadProfile(s.user.id);
      } else {
        setSession(null);
        setProfile(null);
        setView("landing");
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  async function loadProfile(userId) {
    const { data, error } = await supabase
      .from("provider_profiles")
      .select("*")
      .eq("user_id", userId)
      .maybeSingle();

    if (error) {
      console.error("[ProviderApp] Error loading profile:", error);
      setView("onboarding");
      return;
    }

    if (data) {
      setProfile(data);
      setView("dashboard");
    } else {
      setView("onboarding");
    }
  }

  // Magic link send
  const handleSendLink = useCallback(async (e) => {
    e.preventDefault();
    setSending(true);
    setAuthError("");

    const origin = window.location.hostname === "localhost"
      ? window.location.origin
      : "https://civicscale.ai";

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: origin + "/provider" },
    });

    setSending(false);
    if (error) {
      setAuthError(error.message);
    } else {
      setView("sent");
    }
  }, [email]);

  // Onboarding submit
  const handleOnboardingSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!formData.practice_name.trim()) {
      setFormError("Practice name is required.");
      return;
    }
    setFormSaving(true);
    setFormError("");

    const { data, error } = await supabase
      .from("provider_profiles")
      .insert({
        user_id: session.user.id,
        practice_name: formData.practice_name.trim(),
        specialty: formData.specialty || null,
        npi: formData.npi.trim() || null,
        zip_code: formData.zip_code.trim() || null,
      })
      .select()
      .single();

    setFormSaving(false);
    if (error) {
      setFormError(error.message);
    } else {
      setProfile(data);
      setView("dashboard");
    }
  }, [session, formData]);

  // Sign out
  const handleSignOut = useCallback(async () => {
    await supabase.auth.signOut();
    setSession(null);
    setProfile(null);
    setView("landing");
  }, []);

  // ── Shared nav ──
  const nav = (
    <nav className="cs-nav">
      <Link className="cs-nav-logo" to="/">
        <LogoIcon />
        <span className="cs-nav-wordmark">CivicScale</span>
      </Link>
      <div className="cs-nav-links">
        <Link to="/provider">For Providers</Link>
      </div>
    </nav>
  );

  // Don't render until auth check completes
  if (view === null) {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p style={{ color: "var(--cs-slate)" }}>Loading...</p>
        </div>
      </div>
    );
  }

  // ── LANDING VIEW ──
  if (view === "landing" || view === "sent") {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 420, padding: "0 16px" }}>
            <div style={{ textAlign: "center", marginBottom: 40 }}>
              <h1 style={{ fontSize: 28, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
                Parity Provider
              </h1>
              <p style={{ color: "var(--cs-slate)", marginTop: 8, fontSize: 15 }}>
                Audit your payer contracts. Find what they owe you.
              </p>
            </div>

            {view === "sent" ? (
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
                  onClick={() => setView("landing")}
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
              <form onSubmit={handleSendLink}>
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
                    placeholder="doctor@yourpractice.com"
                    style={{
                      width: "100%", padding: "10px 12px", borderRadius: 8,
                      border: "1px solid var(--cs-border)", fontSize: 15,
                      outline: "none", boxSizing: "border-box",
                    }}
                  />
                </div>

                {authError && (
                  <div style={{
                    padding: 12, borderRadius: 8, background: "#fef2f2",
                    border: "1px solid #fecaca", marginBottom: 16,
                  }}>
                    <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{authError}</p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={sending}
                  className="cs-btn-primary"
                  style={{
                    width: "100%", justifyContent: "center",
                    opacity: sending ? 0.6 : 1,
                  }}
                >
                  {sending ? "Sending..." : "Send Login Link"}
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

  // ── ONBOARDING VIEW ──
  if (view === "onboarding") {
    return (
      <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
        {nav}
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", paddingTop: 64 }}>
          <div style={{ width: "100%", maxWidth: 460, padding: "0 16px" }}>
            <div style={{ textAlign: "center", marginBottom: 32 }}>
              <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
                Set up your practice
              </h1>
              <p style={{ color: "var(--cs-slate)", marginTop: 8, fontSize: 14 }}>
                Tell us about your practice so we can tailor the analysis.
              </p>
            </div>

            <form onSubmit={handleOnboardingSubmit}>
              {/* Practice Name */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Practice name *</label>
                <input
                  type="text"
                  required
                  value={formData.practice_name}
                  onChange={(e) => setFormData(d => ({ ...d, practice_name: e.target.value }))}
                  placeholder="e.g. Sunshine Internal Medicine"
                  style={inputStyle}
                />
              </div>

              {/* Specialty */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>Specialty</label>
                <select
                  value={formData.specialty}
                  onChange={(e) => setFormData(d => ({ ...d, specialty: e.target.value }))}
                  style={{ ...inputStyle, appearance: "auto" }}
                >
                  <option value="">Select a specialty</option>
                  {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {/* NPI */}
              <div style={{ marginBottom: 16 }}>
                <label style={labelStyle}>NPI number</label>
                <input
                  type="text"
                  value={formData.npi}
                  onChange={(e) => setFormData(d => ({ ...d, npi: e.target.value }))}
                  placeholder="Optional — 10-digit NPI"
                  maxLength={10}
                  style={inputStyle}
                />
              </div>

              {/* ZIP Code */}
              <div style={{ marginBottom: 24 }}>
                <label style={labelStyle}>Practice ZIP code</label>
                <input
                  type="text"
                  value={formData.zip_code}
                  onChange={(e) => setFormData(d => ({ ...d, zip_code: e.target.value }))}
                  placeholder="e.g. 33701"
                  maxLength={5}
                  style={inputStyle}
                />
              </div>

              {formError && (
                <div style={{
                  padding: 12, borderRadius: 8, background: "#fef2f2",
                  border: "1px solid #fecaca", marginBottom: 16,
                }}>
                  <p style={{ color: "#991b1b", fontSize: 13, margin: 0 }}>{formError}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={formSaving}
                className="cs-btn-primary"
                style={{
                  width: "100%", justifyContent: "center",
                  opacity: formSaving ? 0.6 : 1,
                }}
              >
                {formSaving ? "Saving..." : "Continue to Dashboard"}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // ── DASHBOARD VIEW ──
  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden" }}>
      {/* Dashboard nav with practice info */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: "var(--cs-navy)" }}>
              {profile?.practice_name}
            </div>
            {profile?.specialty && (
              <span style={{
                fontSize: 11, fontWeight: 500, color: "var(--cs-teal)",
                background: "var(--cs-teal-pale)", padding: "2px 8px",
                borderRadius: 4, display: "inline-block", marginTop: 2,
              }}>
                {profile.specialty}
              </span>
            )}
          </div>
          <button
            onClick={handleSignOut}
            style={{
              background: "none", border: "1px solid var(--cs-border)",
              borderRadius: 8, padding: "6px 14px", fontSize: 13,
              color: "var(--cs-slate)", cursor: "pointer",
            }}
          >
            Sign out
          </button>
        </div>
      </nav>

      <div style={{ paddingTop: 88, maxWidth: 900, margin: "0 auto", padding: "88px 24px 60px" }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, color: "var(--cs-navy)", margin: 0 }}>
            Parity Provider
          </h1>
          <p style={{ color: "var(--cs-slate)", marginTop: 4, fontSize: 14 }}>
            Contract integrity and coding intelligence for your practice.
          </p>
        </div>

        {/* Tab buttons */}
        <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
          <button
            onClick={() => setActiveTab("contract")}
            style={{
              padding: "10px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600,
              cursor: "pointer", border: "1px solid",
              ...(activeTab === "contract"
                ? { background: "var(--cs-navy)", color: "#fff", borderColor: "var(--cs-navy)" }
                : { background: "#fff", color: "var(--cs-slate)", borderColor: "var(--cs-border)" }
              ),
            }}
          >
            Contract Integrity
          </button>
          <button
            onClick={() => setActiveTab("coding")}
            style={{
              padding: "10px 20px", borderRadius: 8, fontSize: 14, fontWeight: 600,
              cursor: "pointer", border: "1px solid",
              ...(activeTab === "coding"
                ? { background: "var(--cs-navy)", color: "#fff", borderColor: "var(--cs-navy)" }
                : { background: "#fff", color: "var(--cs-slate)", borderColor: "var(--cs-border)" }
              ),
            }}
          >
            Coding Analysis
          </button>
        </div>

        {/* Tab content */}
        {activeTab === "contract" ? (
          <div style={{
            border: "1px solid var(--cs-border)", borderRadius: 12,
            padding: 40, textAlign: "center", background: "var(--cs-mist)",
          }}>
            <div style={{ marginBottom: 16 }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--cs-teal)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
              Contract Integrity Audit
            </h3>
            <p style={{ color: "var(--cs-slate)", fontSize: 14, maxWidth: 480, margin: "0 auto 20px" }}>
              Upload a remittance (ERA/835) and we'll check if your payers are applying the correct contracted rates to each line item.
            </p>
            <div style={{
              display: "inline-block", padding: "6px 14px", borderRadius: 6,
              background: "var(--cs-teal-pale)", color: "var(--cs-teal)",
              fontSize: 13, fontWeight: 500,
            }}>
              Coming in next step
            </div>
          </div>
        ) : (
          <div style={{
            border: "1px solid var(--cs-border)", borderRadius: 12,
            padding: 40, textAlign: "center", background: "var(--cs-mist)",
          }}>
            <div style={{ marginBottom: 16 }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--cs-teal)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
              </svg>
            </div>
            <h3 style={{ fontSize: 18, fontWeight: 600, color: "var(--cs-navy)", margin: "0 0 8px" }}>
              Coding Pattern Analysis
            </h3>
            <p style={{ color: "var(--cs-slate)", fontSize: 14, maxWidth: 480, margin: "0 auto 20px" }}>
              We'll analyze your coding patterns across claims to identify undercoding opportunities and compliance risks.
            </p>
            <div style={{
              display: "inline-block", padding: "6px 14px", borderRadius: 6,
              background: "var(--cs-teal-pale)", color: "var(--cs-teal)",
              fontSize: 13, fontWeight: 500,
            }}>
              Coming in next step
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Shared styles ──
const labelStyle = {
  display: "block", fontSize: 14, fontWeight: 500,
  color: "var(--cs-navy)", marginBottom: 6,
};

const inputStyle = {
  width: "100%", padding: "10px 12px", borderRadius: 8,
  border: "1px solid var(--cs-border)", fontSize: 15,
  outline: "none", boxSizing: "border-box",
};
