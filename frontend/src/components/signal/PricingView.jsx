import { useState } from "react";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIER_RANK = { free: 0, standard: 1, premium: 2, professional: 3 };

const TIERS = [
  {
    name: "Free",
    key: "free",
    monthlyPrice: 0,
    annualPrice: 0,
    features: [
      "3 existing topics",
      "5 Q&A questions/month",
      "Summary & key takeaways",
      "Basic anomaly scores",
    ],
    badge: null,
    accent: false,
  },
  {
    name: "Standard",
    key: "standard",
    monthlyPrice: 4.99,
    annualPrice: 39.99,
    features: [
      "10 existing topics",
      "30 Q&A questions/month",
      "1 new topic request/month",
      "Full claim-level detail",
      "Source citations & links",
    ],
    extra: "Additional requests: $7.99 each",
    badge: null,
    accent: false,
  },
  {
    name: "Premium",
    key: "premium",
    monthlyPrice: 19.99,
    annualPrice: 149.99,
    features: [
      "Unlimited existing topics",
      "30 Q&A questions/month",
      "3 new topic requests/month",
      "Everything in Standard",
      "Consensus indicators",
      "Priority support",
    ],
    extra: "Additional requests: $4.99 each",
    badge: "Most Popular",
    accent: true,
  },
  {
    name: "Professional",
    key: "professional",
    monthlyPrice: 99,
    annualPrice: 950,
    features: [
      "Unlimited existing topics",
      "200 Q&A questions/month",
      "10 new topic requests/month",
      "Everything in Premium",
      "API access (coming soon)",
    ],
    extra: "Additional requests: $2.99 each",
    badge: "For Organizations",
    accent: false,
  },
];

export default function PricingView({ session, userTier }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [annual, setAnnual] = useState(false);
  const [loadingKey, setLoadingKey] = useState(null);
  const [message, setMessage] = useState(null);

  const currentTier = userTier || "free";
  const returnPath = searchParams.get("from") || "/pricing";

  function getCta(tierKey) {
    if (tierKey === currentTier) return "Current Plan";
    if (TIER_RANK[tierKey] > TIER_RANK[currentTier]) return "Upgrade";
    return "Downgrade";
  }

  async function handleCheckout(tierKey) {
    if (!session) {
      navigate("/login?returnTo=" + encodeURIComponent(location.pathname + location.search));
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
        window.location.href = data.checkout_url;
        return;
      }

      if (data.action === "upgraded") {
        setMessage({
          type: "success",
          text: `Upgraded to ${data.tier.charAt(0).toUpperCase() + data.tier.slice(1)}! Your new features are available now.`,
        });
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
    <div className="max-w-5xl mx-auto px-4 py-12 font-[Arial,sans-serif]">
      <div className="text-center mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-3">
          Choose your plan
        </h1>
        <p className="text-gray-300 text-sm max-w-md mx-auto">
          Get deeper evidence intelligence with Parity Signal.
          Upgrade or downgrade at any time.
        </p>

        {/* Billing toggle */}
        <div className="flex items-center justify-center gap-3 mt-6">
          <span className={`text-sm ${!annual ? "text-white font-semibold" : "text-gray-400"}`}>
            Monthly
          </span>
          <button
            onClick={() => setAnnual(!annual)}
            className={`relative w-12 h-6 rounded-full border-none cursor-pointer transition-colors ${
              annual ? "bg-[#0D7377]" : "bg-gray-600"
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                annual ? "translate-x-6" : ""
              }`}
            />
          </button>
          <span className={`text-sm ${annual ? "text-white font-semibold" : "text-gray-400"}`}>
            Annual
          </span>
          {annual && (
            <span className="text-xs font-semibold text-[#0D7377] bg-[#0D7377]/10 px-2 py-0.5 rounded-full">
              Save up to 20%
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
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
              className={`rounded-2xl p-5 flex flex-col ${
                tier.accent
                  ? "border-2 border-[#0D7377] shadow-lg ring-1 ring-[#0D7377]/20"
                  : "border border-white/[0.1]"
              }`}
            >
              {tier.badge && (
                <div className={`text-[10px] font-bold uppercase tracking-wide mb-2 ${
                  tier.accent ? "text-[#0D7377]" : "text-white"
                }`}>
                  {tier.badge}
                </div>
              )}

              <h2 className="text-lg font-bold text-white">{tier.name}</h2>

              <div className="mt-2 mb-4">
                {price === 0 ? (
                  <span className="text-2xl font-bold text-white">Free</span>
                ) : (
                  <div className="flex items-baseline gap-1">
                    <span className="text-2xl font-bold text-white">
                      ${annual ? (price / 12).toFixed(2) : price.toFixed(2)}
                    </span>
                    <span className="text-gray-400 text-sm">/mo</span>
                    {annual && (
                      <span className="text-[10px] text-gray-400 ml-0.5">
                        (${price.toFixed(2)}/yr)
                      </span>
                    )}
                  </div>
                )}
              </div>

              <ul className="space-y-2 mb-4 flex-1">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-xs text-gray-200">
                    <svg
                      className="w-3.5 h-3.5 text-[#0D7377] shrink-0 mt-0.5"
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

              {tier.extra && (
                <p className="text-[10px] text-gray-400 mb-3">{tier.extra}</p>
              )}

              {tier.key === "free" ? (
                <div className="text-center text-sm text-gray-400 py-2">
                  {isCurrentTier ? "Current Plan" : "Free forever"}
                </div>
              ) : (
                <button
                  onClick={() => handleCheckout(tier.key)}
                  disabled={isCurrentTier || isLoading}
                  className={`w-full py-2.5 rounded-lg text-sm font-semibold border-none cursor-pointer transition-colors ${
                    isCurrentTier
                      ? "bg-white/[0.06] text-gray-500 cursor-default"
                      : isDowngrade
                        ? "bg-white/[0.1] hover:bg-white/[0.15] text-gray-300"
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
