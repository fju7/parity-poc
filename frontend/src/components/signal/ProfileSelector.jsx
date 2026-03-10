import { useState, useEffect, useMemo, useCallback } from "react";
import { evidenceCategory } from "./WeightAdjuster";
import { trackEvent } from "../../lib/signalAnalytics";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CAT_COLORS = {
  strong: { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", dot: "bg-emerald-400" },
  moderate: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", dot: "bg-blue-400" },
  mixed: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", dot: "bg-amber-400" },
  weak: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", dot: "bg-red-400" },
};

function catLabel(cat) {
  if (!cat) return "";
  return cat.charAt(0).toUpperCase() + cat.slice(1);
}

function DivergenceBadge({ defaultCat, profileCat }) {
  const from = CAT_COLORS[defaultCat] || CAT_COLORS.mixed;
  const to = CAT_COLORS[profileCat] || CAT_COLORS.mixed;

  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold">
      <span className={`px-1.5 py-0.5 rounded ${from.bg} ${from.text}`}>{catLabel(defaultCat)}</span>
      <span className="text-gray-400">&rarr;</span>
      <span className={`px-1.5 py-0.5 rounded ${to.bg} ${to.text}`}>{catLabel(profileCat)}</span>
    </span>
  );
}

export default function ProfileSelector({
  issueId,
  userTier,
  onProfileWeightsChange,
  onProfileScoresChange,
}) {
  const [profiles, setProfiles] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [scoreData, setScoreData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const isPremium = userTier === "premium" || userTier === "professional";

  // Fetch profiles on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/signal/profiles`)
      .then((r) => r.ok ? r.json() : [])
      .then(setProfiles)
      .catch(() => setProfiles([]));
  }, []);

  const defaultProfile = useMemo(() => profiles.find((p) => p.is_default), [profiles]);
  const selectedProfile = useMemo(() => profiles.find((p) => p.id === selectedId), [profiles, selectedId]);

  const handleSelect = useCallback(async (profileId) => {
    if (!isPremium) return;

    const profile = profiles.find((p) => p.id === profileId);
    if (!profile) return;

    // If selecting the default (Balanced), clear custom weights
    if (profile.is_default) {
      setSelectedId(null);
      setScoreData(null);
      onProfileWeightsChange?.(null);
      onProfileScoresChange?.(null);
      trackEvent("profile_selected", { profile_name: profile.name, issue_id: issueId });
      return;
    }

    setSelectedId(profileId);
    setLoading(true);

    trackEvent("profile_selected", { profile_name: profile.name, issue_id: issueId });

    // Apply weights locally for immediate visual feedback
    onProfileWeightsChange?.(profile.weights);

    // Fetch server-side scores for divergence data
    try {
      const res = await fetch(
        `${API_BASE}/api/signal/profiles/score?profile_id=${profileId}&issue_id=${issueId}`,
        { method: "POST" }
      );
      if (res.ok) {
        const data = await res.json();
        setScoreData(data);
        onProfileScoresChange?.(data);
      }
    } catch {
      // Silently fail — local weight computation still works
    }
    setLoading(false);
  }, [profiles, isPremium, issueId, onProfileWeightsChange, onProfileScoresChange]);

  const divergences = scoreData?.divergences || [];

  if (profiles.length === 0) return null;

  return (
    <div className="mb-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2.5 p-3 bg-gradient-to-r from-gray-50 to-teal-50/30 hover:from-gray-100 hover:to-teal-50/50 rounded-xl text-left border border-gray-200 cursor-pointer transition-colors"
      >
        <svg className="w-4 h-4 text-[#0D7377] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
        <span className="flex-1 text-sm font-semibold text-[#1B3A5C]">
          Analytical Profiles
        </span>
        {selectedProfile && !selectedProfile.is_default && (
          <span className="text-[10px] font-semibold text-[#0D7377] bg-teal-50 px-2 py-0.5 rounded-full">
            {selectedProfile.name}
          </span>
        )}
        {divergences.length > 0 && (
          <span className="text-[10px] font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">
            {divergences.length} divergence{divergences.length !== 1 ? "s" : ""}
          </span>
        )}
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="mt-2 border border-gray-200 rounded-xl p-4 bg-white">
          {!isPremium && (
            <div className="bg-gradient-to-r from-teal-50 to-blue-50 border border-teal-200 rounded-lg p-3 mb-4">
              <p className="text-xs font-semibold text-[#0D7377] mb-1">Premium Feature</p>
              <p className="text-xs text-gray-600 leading-relaxed">
                Analytical profiles let you see how different evaluation priorities change the evidence picture.
                Upgrade to Premium to unlock this feature.
              </p>
            </div>
          )}

          <p className="text-xs text-gray-500 mb-3 leading-relaxed">
            Different stakeholders evaluate evidence through different lenses. Select a profile to see how conclusions shift.
          </p>

          {/* Profile buttons */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            {profiles.map((profile) => {
              const isActive = profile.is_default ? !selectedId : selectedId === profile.id;
              return (
                <button
                  key={profile.id}
                  onClick={() => handleSelect(profile.id)}
                  disabled={!isPremium}
                  className={`text-left p-3 rounded-lg border transition-all cursor-pointer ${
                    isActive
                      ? "bg-[#0D7377] text-white border-[#0D7377] shadow-sm"
                      : isPremium
                        ? "bg-white text-gray-700 border-gray-200 hover:border-[#0D7377] hover:shadow-sm"
                        : "bg-gray-50 text-gray-400 border-gray-100 cursor-not-allowed"
                  }`}
                >
                  <div className={`text-xs font-bold mb-0.5 ${isActive ? "text-white" : ""}`}>
                    {profile.name}
                  </div>
                  <div className={`text-[10px] leading-snug ${isActive ? "text-teal-100" : "text-gray-400"}`}>
                    {profile.description?.split("—")[0]?.trim() || ""}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Trade-off explanation */}
          {selectedProfile && !selectedProfile.is_default && (
            <div className="bg-gray-50 rounded-lg p-3 mb-4">
              <p className="text-xs text-gray-700 leading-relaxed">
                {selectedProfile.trade_off_summary}
              </p>
            </div>
          )}

          {/* Divergences */}
          {divergences.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-3.5 h-3.5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 3a9 9 0 100 18 9 9 0 000-18z" />
                </svg>
                <span className="text-xs font-bold text-[#1B3A5C] uppercase tracking-wide">
                  Conclusion Divergences
                </span>
              </div>
              <p className="text-[11px] text-gray-500 mb-2">
                These claims reach a different evidence strength under the {selectedProfile?.name} profile compared to the default scoring.
              </p>
              <div className="space-y-2">
                {divergences.map((d) => (
                  <div
                    key={d.claim_id}
                    className="border border-amber-200 bg-amber-50/50 rounded-lg p-3"
                  >
                    <p className="text-xs text-gray-700 leading-relaxed mb-2 line-clamp-2">
                      {d.claim_text}
                    </p>
                    <div className="flex items-center justify-between">
                      <DivergenceBadge defaultCat={d.default_category} profileCat={d.profile_category} />
                      <span className={`text-[10px] font-semibold ${
                        d.direction === "stronger" ? "text-emerald-600" : "text-red-500"
                      }`}>
                        {d.direction === "stronger" ? "▲ Stronger" : "▼ Weaker"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {loading && (
            <div className="flex items-center gap-2 mt-3 text-xs text-gray-400">
              <div className="w-3 h-3 border-2 border-gray-300 border-t-[#0D7377] rounded-full animate-spin" />
              Computing divergences...
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Hook for use in ClaimCard: returns divergence info for a claim if active.
 * Import the scoreData from parent and call this.
 */
export function getClaimDivergence(claimId, scoreData) {
  if (!scoreData?.divergences) return null;
  return scoreData.divergences.find((d) => d.claim_id === claimId) || null;
}
