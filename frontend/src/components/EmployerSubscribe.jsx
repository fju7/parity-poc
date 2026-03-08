import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIERS = [
  {
    name: "Small",
    price: "$299",
    period: "/mo",
    employees: "Up to 100 employees",
    tier: "small",
    features: [
      "Monthly PEPM benchmarking",
      "Claims file analysis (1 upload/mo)",
      "Plan scorecard",
      "Email summary reports",
      "Medicare benchmark comparisons",
    ],
  },
  {
    name: "Mid-Market",
    price: "$799",
    period: "/mo",
    employees: "100\u20131,000 employees",
    tier: "standard",
    features: [
      "Everything in Small, plus:",
      "Unlimited claims uploads",
      "Provider-level cost analysis",
      "Category-level benchmarking",
      "Quarterly savings report",
      "Priority email support",
    ],
  },
  {
    name: "Employer+",
    price: "$1,999",
    period: "/mo",
    employees: "1,000+ employees",
    tier: "premium",
    features: [
      "Everything in Mid-Market, plus:",
      "Dedicated account manager",
      "Custom benchmark cohorts",
      "EDI 837/835 direct integration",
      "Board-ready analytics deck",
      "Network optimization modeling",
      "API access",
    ],
  },
];

export default function EmployerSubscribe() {
  const [searchParams] = useSearchParams();
  const checkoutSuccess = searchParams.get("checkout_success") === "1";
  const [loadingTier, setLoadingTier] = useState(null);
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [selectedTier, setSelectedTier] = useState(null);

  const handleSelectTier = (tier) => {
    setSelectedTier(tier);
    setShowEmailModal(true);
  };

  const handleCheckout = async (e) => {
    e.preventDefault();
    if (!email || !selectedTier) return;

    setLoadingTier(selectedTier.tier);
    setShowEmailModal(false);

    try {
      const res = await fetch(`${API_BASE}/api/employer/create-checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          company_name: companyName || null,
          tier: selectedTier.tier,
          billing_period: "monthly",
        }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      console.error("Checkout failed:", err);
      setLoadingTier(null);
    }
  };

  // Success view
  if (checkoutSuccess) {
    return (
      <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
        <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />
        <header className="cs-home-header">
          <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
            <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", fontWeight: "700", color: "#0a1628" }}>C</div>
            <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>CivicScale</span>
          </Link>
        </header>
        <div className="cs-home-section" style={{ maxWidth: "500px", margin: "0 auto", paddingTop: "100px", textAlign: "center" }}>
          <div style={{ fontSize: "48px", marginBottom: "16px" }}>&#10003;</div>
          <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "30px", fontWeight: "400", color: "#f1f5f9", marginBottom: "16px" }}>
            You're all set
          </h1>
          <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", marginBottom: "32px" }}>
            Your Parity Employer subscription is active. We'll send a welcome email with your dashboard access and next steps.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <Link to="/billing/employer/benchmark" style={{ ...btnPrimary, textAlign: "center", textDecoration: "none" }}>
              Run Your First Benchmark &rarr;
            </Link>
            <Link to="/billing/employer" style={{ textAlign: "center", color: "#64748b", fontSize: "14px", textDecoration: "none" }}>
              &larr; Back to Parity Employer
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      {/* Header */}
      <header className="cs-home-header">
        <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", fontWeight: "700", color: "#0a1628" }}>C</div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>CivicScale</span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/billing/employer" style={{ color: "#60a5fa", textDecoration: "none" }}>Parity Employer</Link>
        </nav>
      </header>

      <div className="cs-home-section" style={{ maxWidth: "1000px", margin: "0 auto", paddingTop: "60px", paddingBottom: "80px" }}>
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
            <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>PRICING</span>
          </div>
          <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(28px, 3.5vw, 40px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
            Plans that pay for themselves
          </h1>
          <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "560px", margin: "0 auto" }}>
            Most employers find more in savings opportunities on the first analysis than the annual subscription cost.
          </p>
        </div>

        {/* Pricing Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "24px", marginBottom: "48px" }}>
          {TIERS.map((tier) => (
            <div key={tier.tier} style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(59,130,246,0.18)",
              borderRadius: "16px",
              padding: "32px 28px",
              position: "relative",
              display: "flex",
              flexDirection: "column",
            }}>
              <div style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa", marginBottom: "8px" }}>{tier.name}</div>
              <div style={{ marginBottom: "4px" }}>
                <span style={{ fontSize: "36px", fontWeight: "700", color: "#f1f5f9" }}>{tier.price}</span>
                <span style={{ fontSize: "15px", color: "#64748b" }}>{tier.period}</span>
              </div>
              <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "24px" }}>{tier.employees}</div>
              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 24px", flex: 1 }}>
                {tier.features.map((f, i) => (
                  <li key={i} style={{ fontSize: "14px", color: "#94a3b8", padding: "5px 0", display: "flex", gap: "8px", alignItems: "flex-start" }}>
                    <span style={{ color: "#60a5fa", flexShrink: 0 }}>{"\u2713"}</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleSelectTier(tier)}
                disabled={loadingTier === tier.tier}
                style={{
                  width: "100%",
                  background: "transparent",
                  color: "#60a5fa",
                  border: "1px solid rgba(59,130,246,0.4)",
                  borderRadius: "8px",
                  padding: "12px",
                  fontWeight: "600",
                  fontSize: "14px",
                  cursor: loadingTier === tier.tier ? "wait" : "pointer",
                }}
              >
                {loadingTier === tier.tier ? "Redirecting..." : "Get Started"}
              </button>
            </div>
          ))}
        </div>

        {/* Free tools callout */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <p style={{ fontSize: "14px", color: "#64748b" }}>
            Not ready to subscribe? Try our free tools first: {" "}
            <Link to="/billing/employer/benchmark" style={{ color: "#60a5fa", textDecoration: "none" }}>Benchmark</Link> &middot; {" "}
            <Link to="/billing/employer/claims-check" style={{ color: "#60a5fa", textDecoration: "none" }}>Claims Check</Link> &middot; {" "}
            <Link to="/billing/employer/scorecard" style={{ color: "#60a5fa", textDecoration: "none" }}>Scorecard</Link>
          </p>
        </div>

        <div style={{ textAlign: "center" }}>
          <Link to="/billing/employer" style={{ color: "#64748b", fontSize: "14px", textDecoration: "none" }}>
            &larr; Back to Parity Employer
          </Link>
        </div>
      </div>

      {/* Email Modal */}
      {showEmailModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }} onClick={() => setShowEmailModal(false)}>
          <div style={{ background: "#1e293b", borderRadius: "16px", padding: "32px", maxWidth: "400px", width: "90%", border: "1px solid rgba(59,130,246,0.2)" }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "18px", fontWeight: "600", color: "#f1f5f9", marginBottom: "8px" }}>
              Subscribe to {selectedTier?.name}
            </h3>
            <p style={{ fontSize: "14px", color: "#94a3b8", marginBottom: "20px" }}>
              Enter your details to proceed to checkout.
            </p>
            <form onSubmit={handleCheckout} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <input type="email" required placeholder="Work email" value={email} onChange={(e) => setEmail(e.target.value)} style={inputStyle} />
              <input type="text" placeholder="Company name (optional)" value={companyName} onChange={(e) => setCompanyName(e.target.value)} style={inputStyle} />
              <button type="submit" style={btnPrimary}>Continue to Checkout</button>
              <button type="button" onClick={() => setShowEmailModal(false)} style={{ background: "none", border: "none", color: "#64748b", fontSize: "13px", cursor: "pointer" }}>Cancel</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const inputStyle = {
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.12)",
  borderRadius: "8px",
  padding: "12px 14px",
  fontSize: "15px",
  color: "#f1f5f9",
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const btnPrimary = {
  display: "block",
  width: "100%",
  background: "#3b82f6",
  color: "#fff",
  border: "none",
  borderRadius: "8px",
  padding: "14px 28px",
  fontWeight: "600",
  fontSize: "15px",
  cursor: "pointer",
};
