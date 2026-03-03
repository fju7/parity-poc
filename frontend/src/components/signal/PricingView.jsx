import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIERS = [
  {
    name: "Free",
    key: "free",
    monthlyPrice: 0,
    annualPrice: 0,
    features: [
      "1 evidence report per month",
      "Summary & key takeaways",
      "Basic anomaly scores",
    ],
    cta: "Current Plan",
    accent: false,
  },
  {
    name: "Standard",
    key: "standard",
    monthlyPrice: 4.99,
    annualPrice: 39.99,
    features: [
      "5 evidence reports per month",
      "Full claim-level detail",
      "Source citations & links",
      "Consensus indicators",
      "Email support",
    ],
    cta: "Get Started",
    accent: true,
  },
  {
    name: "Premium",
    key: "premium",
    monthlyPrice: 19.99,
    annualPrice: 149.99,
    features: [
      "Unlimited evidence reports",
      "Everything in Standard",
      "Custom topic requests",
      "API access (coming soon)",
      "Priority support",
    ],
    cta: "Get Started",
    accent: false,
  },
];

export default function PricingView({ session, userTier }) {
  const navigate = useNavigate();
  const [annual, setAnnual] = useState(false);
  const [loadingKey, setLoadingKey] = useState(null);

  const currentTier = userTier || "free";

  async function handleCheckout(tierKey) {
    if (!session) {
      navigate("/signal/login");
      return;
    }

    const priceKey = `${tierKey}_${annual ? "annual" : "monthly"}`;
    setLoadingKey(priceKey);

    try {
      const res = await fetch(`${API_BASE}/api/signal/stripe/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ price_key: priceKey }),
      });

      if (!res.ok) throw new Error("Checkout failed");

      const { checkout_url } = await res.json();
      window.location.href = checkout_url;
    } catch {
      setLoadingKey(null);
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-12 font-[Arial,sans-serif]">
      <div className="text-center mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold text-[#1B3A5C] mb-3">
          Choose your plan
        </h1>
        <p className="text-gray-500 text-sm max-w-md mx-auto">
          Get deeper evidence intelligence with Parity Signal.
          Upgrade or downgrade at any time.
        </p>

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-3 mt-6">
          <span className={`text-sm ${!annual ? "text-[#1B3A5C] font-semibold" : "text-gray-400"}`}>
            Monthly
          </span>
          <button
            onClick={() => setAnnual(!annual)}
            className={`relative w-12 h-6 rounded-full border-none cursor-pointer transition-colors ${
              annual ? "bg-[#0D7377]" : "bg-gray-300"
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                annual ? "translate-x-6" : ""
              }`}
            />
          </button>
          <span className={`text-sm ${annual ? "text-[#1B3A5C] font-semibold" : "text-gray-400"}`}>
            Annual
          </span>
          {annual && (
            <span className="text-xs font-semibold text-[#0D7377] bg-teal-50 px-2 py-0.5 rounded-full">
              Save ~17%
            </span>
          )}
        </div>
      </div>

      {/* Tier cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {TIERS.map((tier) => {
          const price = annual ? tier.annualPrice : tier.monthlyPrice;
          const isCurrentTier = currentTier === tier.key;
          const priceKey = `${tier.key}_${annual ? "annual" : "monthly"}`;
          const isLoading = loadingKey === priceKey;

          return (
            <div
              key={tier.key}
              className={`rounded-2xl p-6 flex flex-col ${
                tier.accent
                  ? "border-2 border-[#0D7377] shadow-lg ring-1 ring-[#0D7377]/20"
                  : "border border-gray-200"
              }`}
            >
              {tier.accent && (
                <div className="text-xs font-bold text-[#0D7377] uppercase tracking-wide mb-2">
                  Most Popular
                </div>
              )}

              <h2 className="text-lg font-bold text-[#1B3A5C]">{tier.name}</h2>

              <div className="mt-3 mb-5">
                {price === 0 ? (
                  <span className="text-3xl font-bold text-[#1B3A5C]">Free</span>
                ) : (
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold text-[#1B3A5C]">
                      ${annual ? (price / 12).toFixed(2) : price.toFixed(2)}
                    </span>
                    <span className="text-gray-400 text-sm">/mo</span>
                    {annual && (
                      <span className="text-xs text-gray-400 ml-1">
                        (${price.toFixed(2)}/yr)
                      </span>
                    )}
                  </div>
                )}
              </div>

              <ul className="space-y-2.5 mb-6 flex-1">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-600">
                    <svg
                      className="w-4 h-4 text-[#0D7377] shrink-0 mt-0.5"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>

              {tier.key === "free" ? (
                <div className="text-center text-sm text-gray-400 py-2.5">
                  {isCurrentTier ? "Current Plan" : "Free forever"}
                </div>
              ) : (
                <button
                  onClick={() => handleCheckout(tier.key)}
                  disabled={isCurrentTier || isLoading}
                  className={`w-full py-2.5 rounded-lg text-sm font-semibold border-none cursor-pointer transition-colors ${
                    isCurrentTier
                      ? "bg-gray-100 text-gray-400 cursor-default"
                      : tier.accent
                        ? "bg-[#0D7377] hover:bg-[#0B6265] text-white"
                        : "bg-[#1B3A5C] hover:bg-[#162f4a] text-white"
                  } ${isLoading ? "opacity-60 cursor-wait" : ""}`}
                >
                  {isCurrentTier ? "Current Plan" : isLoading ? "Redirecting..." : tier.cta}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-gray-400 text-center mt-8 max-w-md mx-auto">
        All plans include access to publicly available CMS Medicare benchmark data.
        Prices in USD. Cancel anytime from your billing portal.
      </p>
    </div>
  );
}
