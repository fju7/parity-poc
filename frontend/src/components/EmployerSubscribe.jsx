import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export default function EmployerSubscribe() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate("/billing/employer/dashboard", { replace: true });
  }, [navigate]);
  return null;
}
