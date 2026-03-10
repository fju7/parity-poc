import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIERS = [
  {
    key: "starter",
    name: "Starter",
    price: "$149",
    period: "/mo",
    threshold: "Under $200K annual excess",
    tier: "starter",
    highlight: false,
    features: [
      "Claims Check with Medicare benchmarking",
      "RBP Calculator & savings modeling",
      "Contract Parser rate analysis",
      "Plan Scorecard with AI narrative",
      "Monthly monitoring dashboard",
      "Email summary reports",
    ],
    roi: "3x",
  },
  {
    key: "growth",
    name: "Growth",
    price: "$349",
    period: "/mo",
    threshold: "$200K\u2013$750K annual excess",
    tier: "growth",
    highlight: true,
    features: [
      "Everything in Starter, plus:",
      "Unlimited claims uploads",
      "Provider-level cost analysis",
      "Category-level benchmarking",
      "Quarterly trend reports",
      "Priority email support",
    ],
    roi: "5x",
  },
  {
    key: "scale",
    name: "Scale",
    price: "$699",
    period: "/mo",
    threshold: "Over $750K annual excess",
    tier: "scale",
    highlight: false,
    features: [
      "Everything in Growth, plus:",
      "Dedicated account manager",
      "Custom benchmark cohorts",
      "EDI 837/835 direct integration",
      "Board-ready analytics deck",
      "Network optimization modeling",
    ],
    roi: "10x",
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

  // Auto-select tier from claims analysis stored in localStorage
  const [recommendedTier, setRecommendedTier] = useState(null);
  const [annualizedExcess, setAnnualizedExcess] = useState(null);

  useEffect(() => {
    const stored = localStorage.getItem("employer_pricing_tier");
    const storedExcess = localStorage.getItem("employer_annualized_excess");
    if (stored) {
      setRecommendedTier(stored);
    }
    if (storedExcess) {
      setAnnualizedExcess(parseFloat(storedExcess));
    }
  }, []);

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
            <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>VALUE-BASED PRICING</span>
          </div>
          <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(28px, 3.5vw, 40px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
            Priced by what we find, not your headcount
          </h1>
          <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "600px", margin: "0 auto" }}>
            Your tier is based on how much excess spend our analysis identifies in your claims.
            The more we find, the more value you get — and every plan pays for itself.
          </p>
        </div>

        {/* Recommended tier banner */}
        {recommendedTier && annualizedExcess != null && (
          <div style={{
            background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.25)",
            borderRadius: "12px", padding: "16px 24px", marginBottom: "32px",
            display: "flex", alignItems: "center", justifyContent: "center", gap: "12px", flexWrap: "wrap",
          }}>
            <span style={{ fontSize: "14px", color: "#94a3b8" }}>Based on your claims analysis:</span>
            <span style={{ fontSize: "14px", fontWeight: "600", color: "#60a5fa" }}>
              ${Math.round(annualizedExcess).toLocaleString()} annual excess identified
            </span>
            <span style={{ fontSize: "13px", color: "#64748b" }}>&rarr;</span>
            <span style={{
              background: "#3b82f6", color: "#fff", fontSize: "12px", fontWeight: "700",
              padding: "4px 10px", borderRadius: "6px", textTransform: "uppercase",
            }}>
              {recommendedTier} recommended
            </span>
          </div>
        )}

        {/* Pricing Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "24px", marginBottom: "32px" }}>
          {TIERS.map((tier) => {
            const isRecommended = recommendedTier === tier.key;
            const isHighlight = tier.highlight || isRecommended;
            return (
              <div key={tier.tier} style={{
                background: isHighlight ? "rgba(59,130,246,0.06)" : "rgba(255,255,255,0.02)",
                border: isHighlight ? "2px solid rgba(59,130,246,0.4)" : "1px solid rgba(59,130,246,0.18)",
                borderRadius: "16px",
                padding: "32px 28px",
                position: "relative",
                display: "flex",
                flexDirection: "column",
              }}>
                {isRecommended && (
                  <div style={{
                    position: "absolute", top: "-12px", left: "50%", transform: "translateX(-50%)",
                    background: "#3b82f6", color: "#fff", fontSize: "11px", fontWeight: "700",
                    padding: "4px 14px", borderRadius: "20px", textTransform: "uppercase", letterSpacing: "0.5px",
                  }}>
                    Your Plan
                  </div>
                )}
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa", marginBottom: "8px" }}>{tier.name}</div>
                <div style={{ marginBottom: "4px" }}>
                  <span style={{ fontSize: "36px", fontWeight: "700", color: "#f1f5f9" }}>{tier.price}</span>
                  <span style={{ fontSize: "15px", color: "#64748b" }}>{tier.period}</span>
                </div>
                <div style={{ fontSize: "13px", color: "#64748b", marginBottom: "16px" }}>{tier.threshold}</div>
                <div style={{
                  background: "rgba(59,130,246,0.08)", borderRadius: "8px", padding: "8px 12px",
                  marginBottom: "20px", fontSize: "13px", color: "#60a5fa", fontWeight: "500",
                }}>
                  Typical ROI: {tier.roi} annual subscription cost in identified savings
                </div>
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
                    background: isHighlight ? "#3b82f6" : "transparent",
                    color: isHighlight ? "#fff" : "#60a5fa",
                    border: isHighlight ? "none" : "1px solid rgba(59,130,246,0.4)",
                    borderRadius: "8px",
                    padding: "12px",
                    fontWeight: "600",
                    fontSize: "14px",
                    cursor: loadingTier === tier.tier ? "wait" : "pointer",
                  }}
                >
                  {loadingTier === tier.tier ? "Redirecting..." : "Subscribe"}
                </button>
              </div>
            );
          })}
        </div>

        {/* Guarantee */}
        <div style={{
          background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.2)",
          borderRadius: "12px", padding: "20px 28px", marginBottom: "32px", textAlign: "center",
        }}>
          <p style={{ fontSize: "15px", color: "#10b981", fontWeight: "600", marginBottom: "6px" }}>
            Savings Guarantee
          </p>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: 0, maxWidth: "560px", marginLeft: "auto", marginRight: "auto" }}>
            If the savings we identify don't exceed your subscription cost, we'll refund the difference. No questions asked.
          </p>
        </div>

        {/* Free tools callout */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <p style={{ fontSize: "14px", color: "#64748b" }}>
            Not sure which tier fits? Run a free{" "}
            <Link to="/billing/employer/claims-check" style={{ color: "#60a5fa", textDecoration: "none" }}>Claims Check</Link>{" "}
            first — we'll recommend a tier based on your results.
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
            <h3 style={{ fontSize: "18px", fontWeight: "600", color: "#f1f5f9", marginBottom: "4px" }}>
              Subscribe to {selectedTier?.name}
            </h3>
            <p style={{ fontSize: "22px", fontWeight: "700", color: "#60a5fa", marginBottom: "4px" }}>
              {selectedTier?.price}<span style={{ fontSize: "14px", color: "#64748b", fontWeight: "400" }}>/mo</span>
            </p>
            <p style={{ fontSize: "13px", color: "#94a3b8", marginBottom: "20px" }}>
              {selectedTier?.threshold}
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
