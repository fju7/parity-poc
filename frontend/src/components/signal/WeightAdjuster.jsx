import { useMemo } from "react";

const DIMENSIONS = [
  { key: "source_quality", label: "Source Quality" },
  { key: "data_support", label: "Data Support" },
  { key: "reproducibility", label: "Reproducibility" },
  { key: "consensus", label: "Consensus" },
  { key: "recency", label: "Recency" },
  { key: "rigor", label: "Rigor" },
];

export const DEFAULT_WEIGHTS = {
  source_quality: 0.25,
  data_support: 0.20,
  reproducibility: 0.20,
  consensus: 0.15,
  recency: 0.10,
  rigor: 0.10,
};

export const PRESETS = [
  { name: "Balanced", weights: DEFAULT_WEIGHTS },
  {
    name: "Prioritize Rigor",
    weights: {
      source_quality: 0.15,
      data_support: 0.15,
      reproducibility: 0.15,
      consensus: 0.10,
      recency: 0.05,
      rigor: 0.40,
    },
  },
  {
    name: "Prioritize Recency",
    weights: {
      source_quality: 0.15,
      data_support: 0.15,
      reproducibility: 0.10,
      consensus: 0.10,
      recency: 0.40,
      rigor: 0.10,
    },
  },
];

export function evidenceCategory(score) {
  if (score >= 4.0) return "strong";
  if (score >= 3.0) return "moderate";
  if (score >= 2.0) return "mixed";
  return "weak";
}

export function computeCustomComposite(claimId, weights, dimensionScores) {
  const dims = dimensionScores?.get(claimId);
  if (!dims) return null;
  let weightedSum = 0;
  let totalWeight = 0;
  for (const [dim, weight] of Object.entries(weights)) {
    if (dims[dim] != null) {
      weightedSum += dims[dim] * weight;
      totalWeight += weight;
    }
  }
  return totalWeight > 0 ? weightedSum / totalWeight : null;
}

const DIMENSION_LABELS = Object.fromEntries(DIMENSIONS.map((d) => [d.key, d.label]));

/**
 * Compute a narrative describing which claims moved most and why
 * when custom weights differ from the default (Balanced) profile.
 *
 * Returns null if weights are null (Balanced), or:
 * { topDimension, moversUp: [{claim, oldRank, newRank, drivingDim}], moversDown: [...] }
 */
export function computeRankingNarrative(claims, dimensionScores, compositeMap, customWeights) {
  if (!claims || !dimensionScores || !compositeMap || !customWeights) return null;

  // Build original ranking from compositeMap (Balanced weights)
  const withOriginal = claims
    .map((c) => ({
      claim: c,
      originalScore: compositeMap.get(c.id)?.composite_score ?? 0,
    }))
    .sort((a, b) => b.originalScore - a.originalScore);

  const originalRank = new Map();
  withOriginal.forEach((item, i) => originalRank.set(item.claim.id, i + 1));

  // Build new ranking from custom weights
  const withCustom = claims
    .map((c) => ({
      claim: c,
      customScore: computeCustomComposite(c.id, customWeights, dimensionScores) ?? 0,
    }))
    .sort((a, b) => b.customScore - a.customScore);

  const newRank = new Map();
  withCustom.forEach((item, i) => newRank.set(item.claim.id, i + 1));

  // Compute rank deltas and find driving dimension per claim
  const movers = claims.map((c) => {
    const oldR = originalRank.get(c.id) || 0;
    const newR = newRank.get(c.id) || 0;
    const delta = oldR - newR; // positive = moved up

    // Find which dimension's weight change contributed most
    const dims = dimensionScores.get(c.id);
    let drivingDim = null;
    let maxContribution = 0;
    if (dims) {
      for (const [dim, weight] of Object.entries(customWeights)) {
        const defaultW = DEFAULT_WEIGHTS[dim] || 0;
        const dimScore = dims[dim] ?? 0;
        const contribution = Math.abs((weight - defaultW) * dimScore);
        if (contribution > maxContribution) {
          maxContribution = contribution;
          drivingDim = dim;
        }
      }
    }

    return { claim: c, oldRank: oldR, newRank: newR, delta, drivingDim };
  });

  // Find top dimension (highest total weight increase)
  let topDimension = null;
  let maxWeightIncrease = 0;
  for (const [dim, weight] of Object.entries(customWeights)) {
    const diff = weight - (DEFAULT_WEIGHTS[dim] || 0);
    if (diff > maxWeightIncrease) {
      maxWeightIncrease = diff;
      topDimension = dim;
    }
  }

  const significantMovers = movers.filter((m) => Math.abs(m.delta) >= 2);
  const moversUp = significantMovers
    .filter((m) => m.delta > 0)
    .sort((a, b) => b.delta - a.delta)
    .slice(0, 3);
  const moversDown = significantMovers
    .filter((m) => m.delta < 0)
    .sort((a, b) => a.delta - b.delta)
    .slice(0, 3);

  if (moversUp.length === 0 && moversDown.length === 0) return null;

  return { topDimension, moversUp, moversDown };
}

function RankingNarrative({ narrative }) {
  if (!narrative) return null;

  const { topDimension, moversUp, moversDown } = narrative;
  const totalMovers = moversUp.length + moversDown.length;
  const topLabel = DIMENSION_LABELS[topDimension] || topDimension;

  return (
    <div className="bg-gray-50 rounded-lg p-3 mt-3 text-xs">
      <p className="font-semibold text-[#1B3A5C] mb-2">
        Prioritizing {topLabel} moved {totalMovers} claim{totalMovers !== 1 ? "s" : ""} significantly.
      </p>

      {moversUp.length > 0 && (
        <div className="space-y-1 mb-2">
          {moversUp.map((m) => (
            <div key={m.claim.id} className="flex items-start gap-1.5">
              <span className="text-emerald-600 shrink-0">&#x25B2;</span>
              <span className="text-gray-700 leading-snug">
                <span className="font-medium line-clamp-1 inline">{m.claim.claim_text}</span>
                {" "}
                <span className="text-gray-500">
                  #{m.oldRank} → #{m.newRank}
                  {m.drivingDim && ` (${DIMENSION_LABELS[m.drivingDim] || m.drivingDim})`}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}

      {moversDown.length > 0 && (
        <div className="space-y-1">
          {moversDown.map((m) => (
            <div key={m.claim.id} className="flex items-start gap-1.5">
              <span className="text-red-500 shrink-0">&#x25BC;</span>
              <span className="text-gray-700 leading-snug">
                <span className="font-medium line-clamp-1 inline">{m.claim.claim_text}</span>
                {" "}
                <span className="text-gray-500">
                  #{m.oldRank} → #{m.newRank}
                  {m.drivingDim && ` (${DIMENSION_LABELS[m.drivingDim] || m.drivingDim})`}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function weightsMatch(a, b) {
  for (const key of Object.keys(a)) {
    if (Math.abs(a[key] - b[key]) > 0.001) return false;
  }
  return true;
}

export default function WeightAdjuster({ weights, onChange, onReset, isOpen, onToggle, claims, dimensionScores, compositeMap }) {
  const activePreset = useMemo(() => {
    if (!weights) return "Balanced";
    for (const p of PRESETS) {
      if (weightsMatch(p.weights, weights)) return p.name;
    }
    return null;
  }, [weights]);

  const currentWeights = weights || DEFAULT_WEIGHTS;
  const isCustom = weights != null && activePreset !== "Balanced";

  const narrative = useMemo(() => {
    if (!isCustom) return null;
    return computeRankingNarrative(claims, dimensionScores, compositeMap, weights);
  }, [isCustom, claims, dimensionScores, compositeMap, weights]);

  function handleSliderChange(dimKey, rawValue) {
    const newWeights = { ...currentWeights, [dimKey]: rawValue / 100 };
    // Normalize so all weights sum to 1
    const total = Object.values(newWeights).reduce((a, b) => a + b, 0);
    if (total > 0) {
      for (const k of Object.keys(newWeights)) {
        newWeights[k] = newWeights[k] / total;
      }
    }
    onChange(newWeights);
  }

  function handlePreset(preset) {
    if (preset.name === "Balanced") {
      onReset();
    } else {
      onChange({ ...preset.weights });
    }
  }

  return (
    <div className="mb-6">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 p-3 bg-gray-50 hover:bg-gray-100 rounded-xl text-left border border-gray-200 cursor-pointer transition-colors"
      >
        {/* Beaker icon */}
        <svg className="w-4 h-4 text-[#0D7377] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 00-2 2v10a2 2 0 002 2h6a2 2 0 002-2V7a2 2 0 00-2-2" />
        </svg>
        <span className="flex-1 text-sm font-semibold text-[#1B3A5C]">
          Analytical Paths
        </span>
        {isCustom && (
          <span className="text-[10px] font-semibold text-[#0D7377] bg-teal-50 px-2 py-0.5 rounded-full">
            Custom weights active
          </span>
        )}
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="mt-2 border border-gray-200 rounded-xl p-4 bg-white">
          <p className="text-xs text-gray-500 mb-4 leading-relaxed">
            Different analytical priorities produce different rankings. Adjust weights to explore how the evidence picture changes.
          </p>

          {/* Preset buttons */}
          <div className="flex flex-wrap gap-2 mb-4">
            {PRESETS.map((preset) => (
              <button
                key={preset.name}
                onClick={() => handlePreset(preset)}
                className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors cursor-pointer ${
                  activePreset === preset.name
                    ? "bg-[#0D7377] text-white border-[#0D7377]"
                    : "bg-white text-gray-600 border-gray-300 hover:border-[#0D7377] hover:text-[#0D7377]"
                }`}
              >
                {preset.name}
              </button>
            ))}
            {isCustom && activePreset === null && (
              <button
                onClick={onReset}
                className="text-xs font-medium px-3 py-1.5 rounded-full border border-gray-300 bg-white text-gray-500 hover:text-red-500 hover:border-red-300 transition-colors cursor-pointer"
              >
                Reset
              </button>
            )}
          </div>

          {/* Sliders */}
          <div className="space-y-3">
            {DIMENSIONS.map((dim) => {
              const pct = Math.round(currentWeights[dim.key] * 100);
              return (
                <div key={dim.key}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-[#1B3A5C]">{dim.label}</span>
                    <span className="text-xs text-gray-400 tabular-nums w-8 text-right">{pct}%</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={pct}
                    onChange={(e) => handleSliderChange(dim.key, Number(e.target.value))}
                    className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-gray-200
                      [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#0D7377] [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:cursor-pointer
                      [&::-moz-range-thumb]:w-3.5 [&::-moz-range-thumb]:h-3.5 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-[#0D7377] [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:shadow-sm [&::-moz-range-thumb]:cursor-pointer"
                  />
                </div>
              );
            })}
          </div>

          {/* Ranking narrative — visible when custom weights are active */}
          <RankingNarrative narrative={narrative} />
        </div>
      )}
    </div>
  );
}
