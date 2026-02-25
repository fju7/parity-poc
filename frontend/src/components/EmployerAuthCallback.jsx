import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase.js";

export default function EmployerAuthCallback() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("processing");

  useEffect(() => {
    handleCallback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCallback = async () => {
    // Supabase automatically picks up the token from the URL hash
    // and establishes the session. Wait for it.
    const { data: { session }, error: authError } = await supabase.auth.getSession();

    if (authError || !session) {
      // If no session yet, listen for the auth state change (magic link flow)
      const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, s) => {
        if (s) {
          subscription.unsubscribe();
          await verifyAndRedirect(s.user.email);
        }
      });

      // Timeout after 10s if no session arrives
      setTimeout(() => {
        subscription.unsubscribe();
        navigate("/employer/login?error=auth_timeout");
      }, 10000);
      return;
    }

    await verifyAndRedirect(session.user.email);
  };

  const verifyAndRedirect = async (email) => {
    setStatus("verifying");
    try {
      const { data } = await supabase
        .from("employer_users")
        .select("employer_id, employer_accounts(company_name)")
        .eq("email", email)
        .single();

      if (data && data.employer_id) {
        const companyName = data.employer_accounts?.company_name || "Your Company";
        localStorage.setItem("employer_session", JSON.stringify({
          employer_id: data.employer_id,
          company_name: companyName,
          email,
        }));
        navigate("/employer/dashboard");
      } else {
        navigate("/employer/login?error=not_registered");
      }
    } catch {
      navigate("/employer/login?error=not_registered");
    }
  };

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'DM Sans', sans-serif", background: "#f7f9fc",
    }}>
      <div style={{ textAlign: "center" }}>
        <div style={{
          width: 40, height: 40, border: "3px solid #e2e8f0", borderTopColor: "#0D7377",
          borderRadius: "50%", animation: "cs-spin 0.8s linear infinite", margin: "0 auto 16px",
        }} />
        <p style={{ color: "#1B3A5C", fontWeight: 600, fontSize: 15 }}>
          {status === "verifying" ? "Verifying employer access..." : "Completing sign-in..."}
        </p>
      </div>
      <style>{`@keyframes cs-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
