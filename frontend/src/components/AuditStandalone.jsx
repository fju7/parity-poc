import { Link } from "react-router-dom";
import ProviderAuditPage from "./ProviderAuditPage";

function LogoIcon() {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: 8,
      background: "linear-gradient(135deg, #0d9488, #14b8a6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 16, fontWeight: 700, color: "#fff",
    }}>C</div>
  );
}

export default function AuditStandalone() {
  return (
    <div>
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div className="cs-nav-links">
          <Link to="/audit" style={{ fontWeight: 600 }}>Free Audit</Link>
          <Link to="/billing">Billing Products</Link>
          <Link to="/signal">Parity Signal</Link>
        </div>
      </nav>
      <ProviderAuditPage session={null} profile={null} />
    </div>
  );
}
