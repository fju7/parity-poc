import { useNavigate } from "react-router-dom";

export const TIER_LIMITS = {
  free: 1,
  standard: 5,
  premium: Infinity,
};

/**
 * Gate component that shows an upgrade prompt when the user
 * has reached their tier's report limit.
 *
 * Props:
 *   userTier   — "free" | "standard" | "premium"
 *   usageCount — number of reports used this period
 *   children   — content to render when within limits
 */
export default function TierGate({ userTier = "free", usageCount = 0, children }) {
  const navigate = useNavigate();
  const limit = TIER_LIMITS[userTier] ?? TIER_LIMITS.free;
  const atLimit = usageCount >= limit;

  if (!atLimit) return children;

  const tierLabel = userTier.charAt(0).toUpperCase() + userTier.slice(1);
  const isFreeTier = userTier === "free";

  return (
    <div className="max-w-md mx-auto text-center py-16 px-4 font-[Arial,sans-serif]">
      <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-teal-50 flex items-center justify-center">
        <svg
          className="w-7 h-7 text-[#0D7377]"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
      </div>

      <h2 className="text-lg font-bold text-[#1B3A5C] mb-2">
        {isFreeTier ? "Upgrade to unlock more reports" : `${tierLabel} plan limit reached`}
      </h2>

      <p className="text-sm text-gray-500 mb-6 leading-relaxed">
        {isFreeTier
          ? "You've used your free report for this month. Upgrade to Standard for up to 5 reports, or Premium for unlimited access."
          : `You've used all ${limit} reports included in your ${tierLabel} plan this month. Upgrade to get more.`}
      </p>

      <button
        onClick={() => navigate("/signal/pricing")}
        className="bg-[#0D7377] hover:bg-[#0B6265] text-white font-semibold text-sm px-6 py-2.5 rounded-lg border-none cursor-pointer transition-colors"
      >
        View Plans
      </button>
    </div>
  );
}
