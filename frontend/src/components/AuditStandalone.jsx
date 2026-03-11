import { Link } from "react-router-dom";
import ProviderAuditPage from "./ProviderAuditPage";

export default function AuditStandalone() {
  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", minHeight: "100vh", background: "#f8fafc" }}>
      <header style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        padding: "0 40px", height: "64px", display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(10,22,40,0.96)", backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        <a href="https://civicscale.ai" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span style={{ fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em", color: "#f1f5f9" }}>CivicScale</span>
        </a>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <Link to="/provider/login" style={{ fontSize: 13, color: "#94a3b8", textDecoration: "none" }}>Sign In</Link>
          <Link to="/provider/signup" style={{ fontSize: 13, background: "linear-gradient(135deg, #0d9488, #14b8a6)", color: "#fff", textDecoration: "none", fontWeight: 600, padding: "8px 18px", borderRadius: 8 }}>Start Free Trial</Link>
        </div>
      </header>
      <div style={{ paddingTop: 64 }}>
        <ProviderAuditPage />
      </div>
    </div>
  );
}
