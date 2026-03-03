import { useState, useMemo, useEffect, useRef } from "react";
import CategoryTabs from "./CategoryTabs";
import ConsensusIndicator from "./ConsensusIndicator";
import ClaimCard from "./ClaimCard";
import ScoreBadge from "./ScoreBadge";
import { trackEvent } from "../../lib/signalAnalytics";

const CATEGORY_ORDER = [
  "efficacy",
  "safety",
  "cardiovascular",
  "pricing",
  "regulatory",
  "emerging",
];

const CATEGORY_DISPLAY = {
  efficacy: "Efficacy",
  safety: "Safety",
  cardiovascular: "Heart",
  pricing: "Pricing",
  regulatory: "Regulatory",
  emerging: "Emerging",
};

const STATUS_DOT_COLOR = {
  consensus: "bg-emerald-400",
  debated: "bg-amber-400",
  uncertain: "bg-gray-400",
};

/** Split text into sentences and return the first `count`. */
function getOverviewSentences(text, count = 2) {
  if (!text) return text;
  const sentences = text.match(/[^.!?]+[.!?]+/g);
  if (!sentences || sentences.length <= count) return text;
  return sentences.slice(0, count).join("").trim();
}

function SummaryThemeSection({ category, categoryData, consensusMap, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const displayName = CATEGORY_DISPLAY[category] || category;
  const status = consensusMap?.[category]?.consensus_status;
  const dotColor = STATUS_DOT_COLOR[status] || "bg-gray-300";

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => {
          if (!open) {
            trackEvent("summary_theme_expanded", { category });
          }
          setOpen(!open);
        }}
        className="w-full flex items-center gap-3 p-4 bg-white text-left border-none cursor-pointer hover:bg-gray-50 transition-colors"
      >
        <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />
        <span className="flex-1 text-sm font-semibold text-[#1B3A5C]">
          {displayName}
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <p className="text-sm text-gray-700 leading-relaxed mt-3">
            {categoryData?.key_takeaway || "No summary available for this theme."}
          </p>
        </div>
      )}
    </div>
  );
}

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
        <div className="flex items-center justify-center mb-1">
          <div
            className="h-3 rounded-l-full bg-emerald-400"
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
            className="h-3 rounded-r-full bg-red-400"
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
    <div className="max-w-3xl mx-auto px-4 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-gray-200 rounded w-2/3" />
      <div className="h-4 bg-gray-100 rounded w-full" />
      <div className="h-4 bg-gray-100 rounded w-5/6" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-xl" />
        ))}
      </div>
      <div className="flex gap-2 mt-6 overflow-hidden">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-11 w-24 bg-gray-100 rounded-full shrink-0" />
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
      const comp = claim.signal_claim_composites;
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
  const [summaryExpanded, setSummaryExpanded] = useState(false);

  // Track issue_viewed once on mount when data is ready
  const trackedIssueRef = useRef(null);
  useEffect(() => {
    if (issue && trackedIssueRef.current !== issue.id) {
      trackedIssueRef.current = issue.id;
      trackEvent("issue_viewed", {
        issue_slug: issue.slug,
        claim_count: claims?.length || 0,
        source_count: sources?.length || 0,
      });
    }
  }, [issue, claims, sources]);

  // Track summary scroll depth
  const summaryRef = useRef(null);
  useEffect(() => {
    const el = summaryRef.current;
    if (!el) return;

    let maxDepth = 0;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          const depth = Math.round(entry.intersectionRatio * 100);
          if (depth > maxDepth) maxDepth = depth;
        }
      },
      { threshold: [0, 0.25, 0.5, 0.75, 1] }
    );
    observer.observe(el);

    return () => {
      observer.disconnect();
      if (maxDepth > 0 && issue) {
        trackEvent("summary_scroll_depth", {
          issue_slug: issue.slug,
          max_depth_pct: maxDepth,
        });
      }
    };
  }, [issue]);

  function handleCategorySelect(cat) {
    setSelectedCategory(cat);
    if (issue) {
      trackEvent("category_selected", {
        issue_slug: issue.slug,
        category: cat,
      });
    }
  }

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
        <div ref={summaryRef} className="mb-6">
          <div className="bg-[#1B3A5C] text-white rounded-xl p-5">
            <div className="text-xs font-semibold text-teal-300 uppercase tracking-wide mb-2">
              Summary
            </div>
            <p className="text-sm leading-relaxed opacity-90">
              {summaryExpanded ? overallSummary : getOverviewSentences(overallSummary, 2)}
            </p>
            {overallSummary !== getOverviewSentences(overallSummary, 2) && (
              <button
                onClick={() => setSummaryExpanded(!summaryExpanded)}
                className="flex items-center gap-1 mt-3 text-teal-300 hover:text-teal-200 text-xs font-medium bg-transparent border-none cursor-pointer transition-colors p-0"
              >
                {summaryExpanded ? "Show less" : "Read full summary"}
                <svg
                  className={`w-3 h-3 transition-transform ${summaryExpanded ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            )}
          </div>

          {/* Theme sections */}
          {summaryData?.categories && (
            <div className="mt-3 space-y-2">
              {CATEGORY_ORDER.filter((cat) => summaryData.categories[cat]).map((cat, i) => (
                <SummaryThemeSection
                  key={cat}
                  category={cat}
                  categoryData={summaryData.categories[cat]}
                  consensusMap={consensusMap}
                  defaultOpen={i === 0}
                />
              ))}
            </div>
          )}
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
            onSelect={handleCategorySelect}
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
