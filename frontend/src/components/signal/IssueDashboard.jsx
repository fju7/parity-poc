import { useState, useMemo } from "react";
import CategoryTabs from "./CategoryTabs";
import ConsensusIndicator from "./ConsensusIndicator";
import ClaimCard from "./ClaimCard";
import ScoreBadge from "./ScoreBadge";

const CATEGORY_ORDER = [
  "efficacy",
  "safety",
  "cardiovascular",
  "pricing",
  "regulatory",
  "emerging",
];

function StatsBar({ sources, claims, composites }) {
  const sourceCount = sources?.length || 0;
  const claimCount = claims?.length || 0;
  const scoredCount = composites?.size || 0;

  const distribution = useMemo(() => {
    const dist = { strong: 0, moderate: 0, mixed: 0, weak: 0 };
    if (!composites) return dist;
    for (const c of composites.values()) {
      const cat = (c.evidence_category || "").toLowerCase();
      if (cat in dist) dist[cat]++;
    }
    return dist;
  }, [composites]);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <div className="bg-gray-50 rounded-xl p-3 text-center">
        <div className="text-2xl font-bold text-[#1B3A5C]">{sourceCount}</div>
        <div className="text-xs text-gray-500">Sources</div>
      </div>
      <div className="bg-gray-50 rounded-xl p-3 text-center">
        <div className="text-2xl font-bold text-[#1B3A5C]">{claimCount}</div>
        <div className="text-xs text-gray-500">Claims</div>
      </div>
      <div className="bg-gray-50 rounded-xl p-3 text-center">
        <div className="text-2xl font-bold text-[#1B3A5C]">{scoredCount}</div>
        <div className="text-xs text-gray-500">Scored</div>
      </div>
      <div className="bg-gray-50 rounded-xl p-3">
        <div className="flex items-center justify-center gap-1 mb-1">
          <div
            className="h-3 rounded-l bg-emerald-400"
            style={{
              width: `${((distribution.strong / (scoredCount || 1)) * 100).toFixed(0)}%`,
              minWidth: distribution.strong > 0 ? 4 : 0,
            }}
          />
          <div
            className="h-3 bg-blue-400"
            style={{
              width: `${((distribution.moderate / (scoredCount || 1)) * 100).toFixed(0)}%`,
              minWidth: distribution.moderate > 0 ? 4 : 0,
            }}
          />
          <div
            className="h-3 bg-amber-400"
            style={{
              width: `${((distribution.mixed / (scoredCount || 1)) * 100).toFixed(0)}%`,
              minWidth: distribution.mixed > 0 ? 4 : 0,
            }}
          />
          <div
            className="h-3 rounded-r bg-red-400"
            style={{
              width: `${((distribution.weak / (scoredCount || 1)) * 100).toFixed(0)}%`,
              minWidth: distribution.weak > 0 ? 4 : 0,
            }}
          />
        </div>
        <div className="text-xs text-gray-500 text-center">Strength</div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 py-8">
      <div className="h-6 bg-gray-200 rounded w-2/3" />
      <div className="h-4 bg-gray-100 rounded w-full" />
      <div className="h-4 bg-gray-100 rounded w-5/6" />
      <div className="grid grid-cols-4 gap-3 mt-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-xl" />
        ))}
      </div>
      <div className="flex gap-2 mt-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 w-24 bg-gray-100 rounded-full" />
        ))}
      </div>
      <div className="space-y-3 mt-6">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-20 bg-gray-100 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

export default function IssueDashboard({
  issue,
  summary,
  claims,
  consensus,
  sources,
  loading,
  error,
}) {
  // Build composite map: claim_id -> composite
  const compositeMap = useMemo(() => {
    const map = new Map();
    if (!claims) return map;
    for (const claim of claims) {
      const comp = claim.signal_claim_composites?.[0];
      if (comp) map.set(claim.id, comp);
    }
    return map;
  }, [claims]);

  // Build source count per claim (from claim_sources join if available, else fallback)
  const claimSourceCounts = useMemo(() => {
    const map = new Map();
    if (!claims) return map;
    for (const claim of claims) {
      // We'll count from the claim_sources relation if loaded, otherwise 0
      map.set(claim.id, claim._sourceCount || 0);
    }
    return map;
  }, [claims]);

  // Build consensus map: category -> consensus row
  const consensusMap = useMemo(() => {
    const map = {};
    if (!consensus) return map;
    for (const c of consensus) {
      map[c.category] = c;
    }
    return map;
  }, [consensus]);

  // Determine available categories (only those with claims)
  const categories = useMemo(() => {
    if (!claims) return [];
    const catSet = new Set(claims.map((c) => c.category));
    return CATEGORY_ORDER.filter((cat) => catSet.has(cat));
  }, [claims]);

  const [selectedCategory, setSelectedCategory] = useState(null);

  // Auto-select first category
  const activeCategory = selectedCategory || categories[0];

  // Filter claims for active category, sorted by composite score desc
  const filteredClaims = useMemo(() => {
    if (!claims || !activeCategory) return [];
    return claims
      .filter((c) => c.category === activeCategory)
      .sort((a, b) => {
        const sa = compositeMap.get(a.id)?.composite_score ?? 0;
        const sb = compositeMap.get(b.id)?.composite_score ?? 0;
        return sb - sa;
      });
  }, [claims, activeCategory, compositeMap]);

  // Summary data
  const summaryData = summary?.summary_json;
  const overallSummary = summaryData?.overall_summary;
  const categoryKey = summaryData?.categories?.[activeCategory];

  // Average composite for the active category
  const avgScore = useMemo(() => {
    if (filteredClaims.length === 0) return null;
    const scores = filteredClaims
      .map((c) => compositeMap.get(c.id)?.composite_score)
      .filter((s) => s != null);
    if (scores.length === 0) return null;
    return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
  }, [filteredClaims, compositeMap]);

  if (loading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="py-12 text-center font-[Arial,sans-serif]">
        <div className="text-red-500 text-lg font-bold mb-2">
          Unable to load evidence data
        </div>
        <p className="text-gray-500 text-sm">{error}</p>
      </div>
    );
  }

  if (!issue) {
    return (
      <div className="py-12 text-center font-[Arial,sans-serif]">
        <div className="text-gray-400 text-lg">Topic not found</div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 font-[Arial,sans-serif]">
      {/* Issue header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-[#0D7377] bg-teal-50 px-2.5 py-0.5 rounded-full uppercase tracking-wide">
            Evidence Review
          </span>
          {summary && (
            <span className="text-xs text-gray-400">
              v{summary.version}
            </span>
          )}
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-[#1B3A5C] mb-2">
          {issue.title}
        </h1>
        {issue.description && (
          <p className="text-sm text-gray-500 leading-relaxed">
            {issue.description}
          </p>
        )}
      </div>

      {/* Overall summary */}
      {overallSummary && (
        <div className="bg-[#1B3A5C] text-white rounded-xl p-5 mb-6">
          <div className="text-xs font-semibold text-teal-300 uppercase tracking-wide mb-2">
            Summary
          </div>
          <p className="text-sm leading-relaxed opacity-90">{overallSummary}</p>
        </div>
      )}

      {/* Stats */}
      <StatsBar sources={sources} claims={claims} composites={compositeMap} />

      {/* Category tabs */}
      {categories.length > 0 && (
        <div className="mb-6">
          <CategoryTabs
            categories={categories}
            consensusMap={consensusMap}
            selected={activeCategory}
            onSelect={setSelectedCategory}
          />
        </div>
      )}

      {/* Active category section */}
      {activeCategory && (
        <div className="space-y-4">
          {/* Consensus for this category */}
          {consensusMap[activeCategory] && (
            <ConsensusIndicator consensus={consensusMap[activeCategory]} />
          )}

          {/* Category takeaway from summary */}
          {categoryKey?.key_takeaway && (
            <div className="bg-gray-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-1">
                {avgScore && <ScoreBadge score={avgScore} size="sm" />}
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wide">
                  Key Takeaway
                </span>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed">
                {categoryKey.key_takeaway}
              </p>
            </div>
          )}

          {/* Claims list */}
          <div className="space-y-3">
            {filteredClaims.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-6">
                No claims in this category.
              </p>
            ) : (
              filteredClaims.map((claim) => (
                <ClaimCard
                  key={claim.id}
                  claim={claim}
                  composite={compositeMap.get(claim.id)}
                />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
