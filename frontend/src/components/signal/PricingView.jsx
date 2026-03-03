import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIER_RANK = { free: 0, standard: 1, premium: 2 };

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
    accent: false,
  },
];

export default function PricingView({ session, userTier }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [annual, setAnnual] = useState(false);
  const [loadingKey, setLoadingKey] = useState(null);
  const [message, setMessage] = useState(null);

  const currentTier = userTier || "free";
  // Return path: use ?from= param if present, otherwise default to pricing
  const returnPath = searchParams.get("from") || "/signal/pricing";

  function getCta(tierKey) {
    if (tierKey === currentTier) return "Current Plan";
    if (TIER_RANK[tierKey] > TIER_RANK[currentTier]) return "Upgrade";
    return "Downgrade";
  }

  async function handleCheckout(tierKey) {
    if (!session) {
      navigate("/signal/login");
      return;
    }

    const priceKey = `${tierKey}_${annual ? "annual" : "monthly"}`;
    setLoadingKey(priceKey);
    setMessage(null);

    try {
      const res = await fetch(`${API_BASE}/api/signal/stripe/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ price_key: priceKey, return_path: returnPath }),
      });

      if (!res.ok) throw new Error("Checkout failed");

      const data = await res.json();

      if (data.checkout_url) {
        // New subscription — redirect to Stripe Checkout
        window.location.href = data.checkout_url;
        return;
      }

      if (data.action === "upgraded") {
        setMessage({
          type: "success",
          text: `Upgraded to ${data.tier.charAt(0).toUpperCase() + data.tier.slice(1)}! Your new features are available now.`,
        });
        // Tier will refresh via the checkout_success flow or page reload
        setTimeout(() => window.location.reload(), 1500);
        return;
      }

      if (data.action === "downgraded_scheduled") {
        const effectiveDate = data.effective_date
          ? new Date(data.effective_date * 1000).toLocaleDateString()
          : "the end of your billing period";
        setMessage({
          type: "info",
          text: `Plan change scheduled. You'll keep ${data.tier.charAt(0).toUpperCase() + data.tier.slice(1)} access until ${effectiveDate}, then switch to ${data.new_tier.charAt(0).toUpperCase() + data.new_tier.slice(1)}.`,
        });
      }
    } catch {
      setMessage({ type: "error", text: "Something went wrong. Please try again." });
    } finally {
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

      {/* Status message */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-xl text-sm ${
            message.type === "success"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : message.type === "error"
                ? "bg-red-50 text-red-700 border border-red-200"
                : "bg-blue-50 text-blue-700 border border-blue-200"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Tier cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {TIERS.map((tier) => {
          const price = annual ? tier.annualPrice : tier.monthlyPrice;
          const isCurrentTier = currentTier === tier.key;
          const priceKey = `${tier.key}_${annual ? "annual" : "monthly"}`;
          const isLoading = loadingKey === priceKey;
          const cta = getCta(tier.key);
          const isDowngrade = TIER_RANK[tier.key] < TIER_RANK[currentTier];

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
                      : isDowngrade
                        ? "bg-gray-200 hover:bg-gray-300 text-gray-600"
                        : tier.accent
                          ? "bg-[#0D7377] hover:bg-[#0B6265] text-white"
                          : "bg-[#1B3A5C] hover:bg-[#162f4a] text-white"
                  } ${isLoading ? "opacity-60 cursor-wait" : ""}`}
                >
                  {isCurrentTier ? "Current Plan" : isLoading ? "Processing..." : cta}
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
