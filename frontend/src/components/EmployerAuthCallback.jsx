import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

/**
 * Legacy callback route for old magic link emails still in inboxes.
 * Now that we use OTP codes, this simply redirects to the login page.
 */
export default function EmployerAuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate("/employer/login", { replace: true });
  }, [navigate]);

  return null;
}
