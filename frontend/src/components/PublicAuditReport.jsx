import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import ProviderAuditReport from "./ProviderAuditReport.jsx";
import "./CivicScaleHomepage.css";

import { API_BASE } from "../lib/apiBase";
export default function PublicAuditReport() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchReport() {
      try {
        const res = await fetch(`${API_BASE}/api/provider/report/${token}`);
        if (!res.ok) {
          setError(res.status === 404 ? "not_found" : "error");
          setLoading(false);
          return;
        }
        const json = await res.json();
        setData(json);
      } catch (e) {
        console.error("[PublicReport] Fetch failed:", e);
        setError("error");
      } finally {
        setLoading(false);
      }
    }
    fetchReport();
  }, [token]);

  if (loading) {
    return (
      <div>
        <Nav />
        <div style={{ textAlign: "center", padding: "120px 24px" }}>
          <div style={{
            width: 48, height: 48, border: "4px solid #E2E8F0",
            borderTopColor: "#0D9488", borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            margin: "0 auto 24px",
          }} />
          <p style={{ color: "#64748B", fontSize: 16 }}>Loading your report...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        </div>
      </div>
    );
  }

  if (error === "not_found") {
    return (
      <div>
        <Nav />
        <div style={{ textAlign: "center", padding: "120px 24px", maxWidth: 480, margin: "0 auto" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>&#128269;</div>
          <h2 style={{ color: "#1E293B", margin: "0 0 12px" }}>Report Not Found</h2>
          <p style={{ color: "#64748B", fontSize: 15, lineHeight: 1.6 }}>
            This report link may have expired or is invalid. If you believe this is an error,
            please contact <a href="mailto:fred@civicscale.ai" style={{ color: "#0D9488" }}>fred@civicscale.ai</a>.
          </p>
        </div>
      </div>
    );
  }

  if (error === "error") {
    return (
      <div>
        <Nav />
        <div style={{ textAlign: "center", padding: "120px 24px", maxWidth: 480, margin: "0 auto" }}>
          <h2 style={{ color: "#1E293B", margin: "0 0 12px" }}>Something went wrong</h2>
          <p style={{ color: "#64748B", fontSize: 15, lineHeight: 1.6 }}>
            We couldn't load this report. Please try again in a moment or
            contact <a href="mailto:fred@civicscale.ai" style={{ color: "#0D9488" }}>fred@civicscale.ai</a>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Nav />
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        <ProviderAuditReport
          analysisResults={data.payer_results}
          practiceInfo={{
            practice_name: data.practice_name,
            specialty: data.practice_specialty,
          }}
          onClose={null}
        />
      </div>
    </div>
  );
}

function Nav() {
  return (
    <nav className="cs-nav">
      <Link className="cs-nav-logo" to="/">
        <LogoIcon />
        <span className="cs-nav-wordmark">CivicScale</span>
      </Link>
      <div className="cs-nav-links">
        <Link to="/audit">Free Audit</Link>
        <Link to="/billing">Billing Products</Link>
        <Link to="/signal">Parity Signal</Link>
      </div>
    </nav>
  );
}
