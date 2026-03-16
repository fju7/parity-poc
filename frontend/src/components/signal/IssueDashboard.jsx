import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import CategoryTabs from "./CategoryTabs";
import ConsensusIndicator from "./ConsensusIndicator";
import ClaimCard from "./ClaimCard";
import ScoreBadge from "./ScoreBadge";
import EvidenceQA from "./EvidenceQA";
import GlossaryText from "./GlossaryText";
import WeightAdjuster, { computeCustomComposite, evidenceCategory } from "./WeightAdjuster";
import ProfileSelector from "./ProfileSelector";
import { trackEvent } from "../../lib/signalAnalytics";

/** Format a snake_case category key into a display name. */
function displayName(key) {
  if (!key) return key;
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_DOT_COLOR = {
  consensus: "bg-emerald-400",
  debated: "bg-amber-400",
  uncertain: "bg-gray-400",
};

/** Score ring color: green 4+, amber 3-4, red <3 */
function scoreRingColor(score) {
  const n = parseFloat(score);
  if (n >= 4) return { border: "#EAF3DE", text: "#3B6D11", bg: "#f0f7e6", fill: "#3B6D11" };
  if (n >= 3) return { border: "#FAEEDA", text: "#854F0B", bg: "#fdf6eb", fill: "#854F0B" };
  return { border: "#FCEBEB", text: "#A32D2D", bg: "#fdf0f0", fill: "#A32D2D" };
}

/** Score bar fill color (Tailwind classes) */
function scoreBarClasses(score) {
  const n = parseFloat(score);
  if (n >= 4) return "bg-emerald-500";
  if (n >= 3) return "bg-amber-500";
  return "bg-red-500";
}

/** Split text into sentences and return the first `count`.
 *  Avoids splitting on abbreviations like "U.S.", "Dr.", "vs." */
function getOverviewSentences(text, count = 2) {
  if (!text) return text;
  // Match sentence boundaries: a period/!/? followed by whitespace then an
  // uppercase letter or end-of-string, but NOT when the period follows a
  // single uppercase letter (abbreviation like U. S. Dr.) or common short abbrevs.
  const parts = text.split(/(?<=[.!?])\s+(?=[A-Z])/g);
  // Rejoin fragments that were split on abbreviations (e.g. "...U." + "S. data...")
  const sentences = [];
  for (const part of parts) {
    if (sentences.length > 0 && /[A-Z]\.$/.test(sentences[sentences.length - 1])) {
      // Previous fragment ended with an abbreviation like "U." — rejoin
      sentences[sentences.length - 1] += " " + part;
    } else {
      sentences.push(part);
    }
  }
  if (sentences.length <= count) return text;
  return sentences.slice(0, count).join(" ").trim();
}

function SummaryThemeSection({ category, categoryData, consensusMap, glossary, defaultOpen = false, sourceCount, avgScore, onGoDeeper, sectionRef }) {
  const [open, setOpen] = useState(defaultOpen);
  const label = displayName(category);
  const status = consensusMap?.[category]?.consensus_status;
  const dotColor = STATUS_DOT_COLOR[status] || "bg-gray-300";

  return (
    <div ref={sectionRef} className="border border-gray-200 rounded-xl overflow-hidden bg-white">
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
          {label}
        </span>
        {/* Metadata: source count + score */}
        <span className="text-[11px] text-gray-400 shrink-0 tabular-nums">
          {sourceCount > 0 ? `${sourceCount} source${sourceCount !== 1 ? "s" : ""}` : ""}
          {sourceCount > 0 && avgScore ? " · " : ""}
          {avgScore ? `Score ${avgScore}` : ""}
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${open ? "rotate-90" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
      {open && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <p className="text-sm text-gray-700 leading-relaxed mt-3">
            <GlossaryText text={categoryData?.key_takeaway || "No summary available for this theme."} glossary={glossary} />
          </p>
          {onGoDeeper && (
            <button
              onClick={() => onGoDeeper(category)}
              className="mt-3 text-xs font-medium text-[#0D7377] hover:text-[#0B6265] bg-transparent border-none cursor-pointer p-0 transition-colors"
            >
              Go deeper on this section &#8599;
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function DebateItem({ item, glossary }) {
  const [expanded, setExpanded] = useState(false);
  const isDebated = item.consensus_status === "debated";
  const label = displayName(item.category);

  return (
    <div
      className={`rounded-xl overflow-hidden border bg-white ${
        isDebated ? "border-amber-200" : "border-gray-200"
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className={`w-full flex items-center gap-3 p-4 text-left border-none cursor-pointer transition-colors ${
          isDebated
            ? "bg-amber-50 hover:bg-amber-100/60"
            : "bg-gray-50 hover:bg-gray-100"
        }`}
      >
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${
            isDebated ? "bg-amber-400" : "bg-gray-400"
          }`}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-[#1B3A5C]">{label}</span>
            <span
              className={`text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full ${
                isDebated
                  ? "bg-amber-100 text-amber-700"
                  : "bg-gray-200 text-gray-500"
              }`}
            >
              {isDebated ? "Debated" : "Uncertain"}
            </span>
          </div>
          {item.summary_text && (
            <p className="text-xs text-gray-600 leading-relaxed">
              <GlossaryText text={item.summary_text} glossary={glossary} />
            </p>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {expanded && (
        <div
          className={`px-4 pb-4 pt-3 border-t ${
            isDebated ? "border-amber-200" : "border-gray-200"
          }`}
        >
          {isDebated && (item.arguments_for || item.arguments_against) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {item.arguments_for && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                  <div className="text-xs font-bold text-emerald-700 mb-1">
                    Supporting Evidence
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    <GlossaryText text={item.arguments_for} glossary={glossary} />
                  </p>
                </div>
              )}
              {item.arguments_against && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <div className="text-xs font-bold text-red-700 mb-1">
                    Opposing Evidence
                  </div>
                  <p className="text-xs text-gray-700 leading-relaxed">
                    <GlossaryText text={item.arguments_against} glossary={glossary} />
                  </p>
                </div>
              )}
            </div>
          )}

          {!isDebated && (
            <div className="bg-gray-100 rounded-lg p-3">
              <div className="text-xs font-bold text-gray-500 mb-1">
                Why This Remains Uncertain
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">
                The evidence in this area is too early-stage or insufficient to establish a clear direction. More research is needed before conclusions can be drawn.
              </p>
            </div>
          )}
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
  dimensionScores,
  loading,
  error,
  session,
  userTier,
  tierData,
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

  // Debated + uncertain consensus items (ordered: debated first, then uncertain)
  const debateItems = useMemo(() => {
    if (!consensus) return [];
    return consensus
      .filter((c) => c.consensus_status === "debated" || c.consensus_status === "uncertain")
      .sort((a, b) => {
        // debated before uncertain
        if (a.consensus_status === "debated" && b.consensus_status !== "debated") return -1;
        if (a.consensus_status !== "debated" && b.consensus_status === "debated") return 1;
        return 0;
      });
  }, [consensus]);

  // Summary data — declared early because summaryCatMap and categories depend on it
  const summaryData = summary?.summary_json;
  const glossary = summaryData?.glossary || null;

  // Build a lookup from the summary categories list: name -> category object
  const summaryCatMap = useMemo(() => {
    const map = {};
    const cats = summaryData?.categories;
    if (Array.isArray(cats)) {
      for (const c of cats) {
        if (c?.name) map[c.name] = c;
      }
    }
    return map;
  }, [summaryData]);

  // Determine available categories (only those with claims), ordered by summary list
  const categories = useMemo(() => {
    if (!claims) return [];
    const catSet = new Set(claims.map((c) => c.category));
    // Use summary category order if available, then append any extras from claims
    const ordered = [];
    const seen = new Set();
    const cats = summaryData?.categories;
    if (Array.isArray(cats)) {
      for (const c of cats) {
        if (c?.name && catSet.has(c.name) && !seen.has(c.name)) {
          ordered.push(c.name);
          seen.add(c.name);
        }
      }
    }
    for (const cat of catSet) {
      if (!seen.has(cat)) ordered.push(cat);
    }
    return ordered;
  }, [claims, summaryData]);

  const [selectedCategory, setSelectedCategory] = useState(null);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [claimsExpanded, setClaimsExpanded] = useState(false);
  const [customWeights, setCustomWeights] = useState(null);
  const [weightsOpen, setWeightsOpen] = useState(false);
  const [profileScoreData, setProfileScoreData] = useState(null);
  const [activePanel, setActivePanel] = useState("overview");
  const [claimFilter, setClaimFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");

  // Build a set of divergent claim IDs for visual flagging
  const divergentClaimIds = useMemo(() => {
    const set = new Set();
    if (profileScoreData?.divergences) {
      for (const d of profileScoreData.divergences) {
        set.add(d.claim_id);
      }
    }
    return set;
  }, [profileScoreData]);

  const handleProfileWeightsChange = useCallback((weights) => {
    setCustomWeights(weights);
    if (!weights) setProfileScoreData(null);
  }, []);

  const handleProfileScoresChange = useCallback((data) => {
    setProfileScoreData(data);
  }, []);

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
    setClaimsExpanded(false);
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
        const sa = customWeights
          ? (computeCustomComposite(a.id, customWeights, dimensionScores) ?? 0)
          : (compositeMap.get(a.id)?.composite_score ?? 0);
        const sb = customWeights
          ? (computeCustomComposite(b.id, customWeights, dimensionScores) ?? 0)
          : (compositeMap.get(b.id)?.composite_score ?? 0);
        return sb - sa;
      });
  }, [claims, activeCategory, compositeMap, customWeights, dimensionScores]);

  const overallSummary = summaryData?.overall_summary;
  const categoryKey = summaryCatMap[activeCategory];

  // Average composite for the active category
  const avgScore = useMemo(() => {
    if (filteredClaims.length === 0) return null;
    const scores = filteredClaims
      .map((c) =>
        customWeights
          ? computeCustomComposite(c.id, customWeights, dimensionScores)
          : compositeMap.get(c.id)?.composite_score
      )
      .filter((s) => s != null);
    if (scores.length === 0) return null;
    return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
  }, [filteredClaims, compositeMap, customWeights, dimensionScores]);

  // ── Layer 1: Overall consensus score (avg of all composite scores) ──
  const overallScore = useMemo(() => {
    if (!compositeMap || compositeMap.size === 0) return null;
    const scores = [];
    for (const c of compositeMap.values()) {
      if (c.composite_score != null) scores.push(c.composite_score);
    }
    if (scores.length === 0) return null;
    return (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
  }, [compositeMap]);

  // ── Layer 2: Per-category average scores + source counts ──
  const categoryScores = useMemo(() => {
    if (!claims || !categories.length) return {};
    const map = {};
    for (const cat of categories) {
      const catClaims = claims.filter((c) => c.category === cat);
      const scores = catClaims
        .map((c) => compositeMap.get(c.id)?.composite_score)
        .filter((s) => s != null);
      const sourceCounts = catClaims.reduce((sum, c) => sum + (c._sourceCount || 0), 0);
      map[cat] = {
        avg: scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : null,
        sources: sourceCounts,
        claims: catClaims.length,
      };
    }
    return map;
  }, [claims, categories, compositeMap]);

  // Refs for scrolling to sections
  const sectionRefs = useRef({});
  const navRailRef = useRef(null);

  // ── Change 5: Contested topic banner detection ──
  const isContested = summaryData?.topic_type === "contested" || summaryData?.has_values_dimension === true;
  const empiricalQuestion = summaryData?.empirical_question || issue?.title || "this topic";

  if (loading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="py-12 text-center font-[Arial,sans-serif]">
        <div className="text-red-500 text-lg font-bold mb-2">
          Unable to load evidence data
        </div>
        <p className="text-gray-400 text-sm">{error}</p>
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
      <div className="mb-4">
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
        <h1 className="text-xl sm:text-2xl font-bold text-white mb-2">
          {issue.title}
        </h1>
      </div>

      {/* ── Change 5: Contested Topic Banner ── */}
      {isContested && (
        <div className="mb-4 rounded-lg p-4" style={{ background: "#FEF9E7", borderLeft: "3px solid #EF9F27" }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full" style={{ background: "#FAEEDA", color: "#854F0B" }}>
              Empirical + Values
            </span>
          </div>
          <p className="text-xs text-gray-700 leading-relaxed">
            This topic has both empirical and values components. Signal evaluates the evidence on {empiricalQuestion}. The values dimensions are addressed in the full analysis below.
          </p>
        </div>
      )}

      {/* ── Layer 1: Score Ring + Verdict ── */}
      {overallSummary && (
        <div ref={summaryRef} className="mb-6">
          <div className="bg-[#1B3A5C] rounded-xl p-5">
            <div className="flex items-start gap-4">
              {/* Score ring */}
              {overallScore && (
                <div
                  className="shrink-0 flex items-center justify-center rounded-full"
                  style={{
                    width: 44,
                    height: 44,
                    border: `2px solid ${scoreRingColor(overallScore).border}`,
                    background: scoreRingColor(overallScore).bg,
                  }}
                >
                  <span
                    className="font-medium tabular-nums"
                    style={{ fontSize: 14, color: scoreRingColor(overallScore).text }}
                  >
                    {overallScore}
                  </span>
                </div>
              )}
              {/* Verdict */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white leading-relaxed opacity-95">
                  <GlossaryText
                    text={getOverviewSentences(overallSummary, 2)}
                    glossary={glossary}
                  />
                </p>
                {issue.description && (
                  <p className="text-xs text-gray-400 leading-relaxed mt-1.5 italic">
                    {getOverviewSentences(issue.description, 1)}
                  </p>
                )}
                {overallSummary !== getOverviewSentences(overallSummary, 2) && (
                  <button
                    onClick={() => setSummaryExpanded(!summaryExpanded)}
                    className="flex items-center gap-1 mt-2 text-teal-300 hover:text-teal-200 text-xs font-medium bg-transparent border-none cursor-pointer transition-colors p-0"
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
                {summaryExpanded && (
                  <p className="text-sm text-white leading-relaxed opacity-90 mt-2">
                    <GlossaryText text={overallSummary} glossary={glossary} />
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* ── Layer 2: Score Bars ── */}
          {categories.length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] text-gray-400 uppercase tracking-wide mb-2 px-1">
                Click any category to explore the evidence
              </div>
              <div className="space-y-1.5">
                {categories.map((cat) => {
                  const cs = categoryScores[cat] || {};
                  const score = cs.avg ? parseFloat(cs.avg) : 0;
                  return (
                    <button
                      key={cat}
                      title={`View ${displayName(cat)} claims`}
                      onClick={() => {
                        handleCategorySelect(cat);
                        setActivePanel("claims");
                        setTimeout(() => {
                          navRailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                        }, 50);
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg bg-white hover:bg-gray-50 border border-gray-100 hover:border-[#0D7377]/30 cursor-pointer transition-colors group text-left"
                    >
                      <span className="text-xs font-medium text-[#1B3A5C] shrink-0" style={{ width: 120 }}>
                        {displayName(cat)}
                      </span>
                      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${scoreBarClasses(cs.avg || 0)}`}
                          style={{ width: `${(score / 5) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-500 tabular-nums shrink-0" style={{ minWidth: 32 }}>
                        {cs.avg || "–"}/5
                      </span>
                      <span className="text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity text-xs">
                        &#8594;
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Theme sections (Change 3: updated with metadata + go deeper) */}
          {categories.length > 0 && (
            <div className="mt-3 space-y-2">
              {categories.map((cat, i) => {
                const cs = categoryScores[cat] || {};
                return (
                  <SummaryThemeSection
                    key={cat}
                    category={cat}
                    categoryData={summaryCatMap[cat]}
                    consensusMap={consensusMap}
                    glossary={glossary}
                    defaultOpen={i === 0}
                    sourceCount={cs.sources || 0}
                    avgScore={cs.avg}
                    sectionRef={(el) => { sectionRefs.current[cat] = el; }}
                    onGoDeeper={(c) => {
                      handleCategorySelect(c);
                      // Scroll to the EvidenceQA section
                      setTimeout(() => {
                        const qaEl = document.querySelector("[data-evidence-qa]");
                        if (qaEl) qaEl.scrollIntoView({ behavior: "smooth", block: "start" });
                      }, 100);
                    }}
                  />
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Layer 3: Navigation Rail ── */}
      <div ref={navRailRef} className="mb-4 overflow-x-auto scrollbar-hide -mx-4 px-4">
        <div className="flex gap-1.5 min-w-max py-1">
          {[
            { id: "overview", label: "Overview" },
            { id: "claims", label: `All Claims (${claims?.length || 0})` },
            { id: "paths", label: "Analytical Paths" },
            { id: "debates", label: "Key Debates" },
            { id: "roadmap", label: "Evidence Roadmap" },
            { id: "sources", label: `Sources (${sources?.length || 0})` },
            { id: "methodology", label: "Methodology" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActivePanel(tab.id);
                trackEvent("nav_click", { panel: tab.id }, issue?.slug, tab.id);
              }}
              className={`px-3.5 py-2 rounded-full text-xs font-semibold border-none cursor-pointer transition-colors whitespace-nowrap ${
                activePanel === tab.id
                  ? "bg-[#0D7377] text-white"
                  : "bg-[#1B3A5C] text-gray-300 hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Panel: Overview ── */}
      {activePanel === "overview" && (
        <div className="space-y-4">
          <StatsBar sources={sources} claims={claims} composites={compositeMap} />

          {/* Q&A */}
          {issue && (
            <EvidenceQA issueId={issue.id} issueSlug={issue.slug} session={session} userTier={userTier} qaUsage={tierData?.usage} />
          )}
        </div>
      )}

      {/* ── Panel: All Claims ── */}
      {activePanel === "claims" && (
        <div className="space-y-3">
          {/* Filters */}
          <div className="flex gap-2 flex-wrap">
            {["all", "strong", "moderate", "mixed", "weak"].map((f) => (
              <button
                key={f}
                onClick={() => setClaimFilter(f)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border-none cursor-pointer transition-colors ${
                  claimFilter === f
                    ? "bg-[#0D7377] text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
                {f !== "all" && (() => {
                  const count = (claims || []).filter((c) => {
                    const comp = compositeMap.get(c.id);
                    return (comp?.evidence_category || "").toLowerCase() === f;
                  }).length;
                  return ` (${count})`;
                })()}
              </button>
            ))}
          </div>

          {/* Category tabs */}
          {categories.length > 0 && (
            <CategoryTabs
              categories={categories}
              consensusMap={consensusMap}
              selected={activeCategory}
              onSelect={handleCategorySelect}
            />
          )}

          {/* Claim cards */}
          {(claimFilter === "all" ? filteredClaims : filteredClaims.filter((c) => {
            const comp = compositeMap.get(c.id);
            return (comp?.evidence_category || "").toLowerCase() === claimFilter;
          })).map((claim) => (
            <ClaimCard
              key={claim.id}
              claim={claim}
              composite={compositeMap.get(claim.id)}
              customScore={customWeights ? computeCustomComposite(claim.id, customWeights, dimensionScores) : undefined}
              divergent={divergentClaimIds.has(claim.id)}
            />
          ))}

          {filteredClaims.length === 0 && (
            <div className="text-center py-8 text-gray-400 text-sm">No claims in this category.</div>
          )}
        </div>
      )}

      {/* ── Panel: Analytical Paths ── */}
      {activePanel === "paths" && (
        <div className="space-y-4">
          {issue && dimensionScores && dimensionScores.size > 0 && (
            <ProfileSelector
              issueId={issue.id}
              userTier={userTier}
              onProfileWeightsChange={handleProfileWeightsChange}
              onProfileScoresChange={handleProfileScoresChange}
            />
          )}

          {dimensionScores && dimensionScores.size > 0 && (
            <WeightAdjuster
              weights={customWeights}
              onChange={(w) => {
                setCustomWeights(w);
                trackEvent("weights_adjusted", { preset: null }, issue?.slug);
              }}
              onReset={() => {
                setCustomWeights(null);
                trackEvent("weights_reset", {}, issue?.slug);
              }}
              isOpen={weightsOpen}
              onToggle={() => {
                if (!weightsOpen) trackEvent("analytical_paths_opened", {}, issue?.slug);
                setWeightsOpen(!weightsOpen);
              }}
              claims={claims}
              dimensionScores={dimensionScores}
              compositeMap={compositeMap}
            />
          )}

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs font-bold text-[#1B3A5C] uppercase tracking-wide mb-3">How Analytical Paths Work</div>
            <p className="text-sm text-gray-600 leading-relaxed">
              Different rigorous analysts weighing the same evidence can reach different conclusions by
              prioritizing different dimensions. Select a profile above to see how emphasis on regulatory
              authority, clinical rigor, or patient relevance shifts the overall assessment.
            </p>
          </div>
        </div>
      )}

      {/* ── Panel: Key Debates ── */}
      {activePanel === "debates" && (
        <div className="space-y-3">
          {debateItems.length > 0 ? (
            <>
              <p className="text-xs text-gray-400 mb-2">
                Areas where the evidence is actively contested or insufficient — worth watching as new data emerges.
              </p>
              {debateItems.map((item) => {
                const affectedCount = (claims || []).filter((c) => c.category === item.category).length;
                return (
                  <div key={item.id || item.category}>
                    <DebateItem item={item} glossary={glossary} />
                    <div className="text-[10px] text-gray-400 mt-1 px-4">
                      {affectedCount} claim{affectedCount !== 1 ? "s" : ""} affected
                    </div>
                  </div>
                );
              })}
            </>
          ) : (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
              <div className="text-sm font-medium text-emerald-700">No active debates</div>
              <p className="text-xs text-emerald-600 mt-1">All categories show consensus on this topic.</p>
            </div>
          )}
        </div>
      )}

      {/* ── Panel: Evidence Roadmap ── */}
      {activePanel === "roadmap" && (
        <div className="space-y-3">
          <p className="text-xs text-gray-400 mb-2">What we know, what's being studied, and what remains unexplored.</p>
          {categories.map((cat) => {
            const cons = consensusMap[cat];
            const status = cons?.consensus_status || "uncertain";
            const dotCls = status === "consensus" ? "bg-emerald-400" : status === "debated" ? "bg-amber-400" : "bg-gray-400";
            const label = status === "consensus" ? "Data available" : status === "debated" ? "Actively studied" : "Not yet studied";
            return (
              <div key={cat} className="flex items-center gap-3 bg-white rounded-lg border border-gray-100 px-4 py-3">
                <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${dotCls}`} />
                <span className="flex-1 text-sm font-medium text-[#1B3A5C]">{displayName(cat)}</span>
                <span className="text-[10px] text-gray-400 uppercase tracking-wide">{label}</span>
              </div>
            );
          })}
          {categories.length === 0 && (
            <div className="text-center py-8 text-gray-400 text-sm">No roadmap data available.</div>
          )}
        </div>
      )}

      {/* ── Panel: Sources ── */}
      {activePanel === "sources" && (
        <div className="space-y-3">
          {/* Source type filter */}
          <div className="flex gap-2 flex-wrap">
            {["all", ...new Set((sources || []).map((s) => s.source_type).filter(Boolean))].map((st) => (
              <button
                key={st}
                onClick={() => setSourceFilter(st)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border-none cursor-pointer transition-colors ${
                  sourceFilter === st
                    ? "bg-[#0D7377] text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {st === "all" ? "All" : st.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </button>
            ))}
          </div>

          {(sources || [])
            .filter((s) => sourceFilter === "all" || s.source_type === sourceFilter)
            .map((src) => (
              <div key={src.id} className="bg-white rounded-xl border border-gray-100 p-3">
                <div className="flex items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[#1B3A5C] leading-snug">
                      {src.url ? (
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className="hover:underline text-[#0D7377]">
                          {src.title || "Untitled source"}
                        </a>
                      ) : (
                        src.title || "Untitled source"
                      )}
                    </div>
                    {src.publication_date && (
                      <div className="text-[10px] text-gray-400 mt-0.5">
                        {new Date(src.publication_date).toLocaleDateString("en-US", { year: "numeric", month: "short" })}
                      </div>
                    )}
                  </div>
                  {src.source_type && (
                    <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                      {src.source_type.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
              </div>
            ))}

          {(sources || []).length === 0 && (
            <div className="text-center py-8 text-gray-400 text-sm">No sources available.</div>
          )}
        </div>
      )}

      {/* ── Panel: Methodology ── */}
      {activePanel === "methodology" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs font-bold text-[#1B3A5C] uppercase tracking-wide mb-3">Version History</div>
            {summary && (
              <div className="text-sm text-gray-600">
                Current version: <strong>v{summary.version}</strong>
                {summary.generated_at && (
                  <span className="text-gray-400"> · Generated {new Date(summary.generated_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}</span>
                )}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs font-bold text-[#1B3A5C] uppercase tracking-wide mb-3">Claim Classification</div>
            <p className="text-sm text-gray-600 leading-relaxed">
              Claims are extracted from source documents and categorized by topic area. Each claim is scored
              across six dimensions: source quality, data support, reproducibility, rigor, consensus, and recency.
              The composite score (1-5) is a weighted average of these dimensions.
            </p>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs font-bold text-[#1B3A5C] uppercase tracking-wide mb-3">Evidence Categories</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-400" /> <span className="text-gray-600">Strong (4.0+)</span></div>
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-400" /> <span className="text-gray-600">Moderate (3.0–3.9)</span></div>
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-amber-400" /> <span className="text-gray-600">Mixed (2.0–2.9)</span></div>
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-400" /> <span className="text-gray-600">Weak (&lt;2.0)</span></div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-xs font-bold text-[#1B3A5C] uppercase tracking-wide mb-3">Limitations</div>
            <ul className="text-sm text-gray-600 leading-relaxed space-y-1.5 list-disc list-inside">
              <li>Signal evaluates published evidence — it cannot account for unpublished studies or ongoing trials not yet in the literature.</li>
              <li>Scores reflect evidence strength, not clinical recommendation. A high score means well-supported, not necessarily actionable.</li>
              <li>AI extraction and scoring may contain errors. All claims can be traced to their source documents.</li>
            </ul>
          </div>

          <button
            onClick={() => {
              setActivePanel("overview");
              setTimeout(() => {
                const qaEl = document.querySelector("[data-evidence-qa]");
                if (qaEl) {
                  qaEl.scrollIntoView({ behavior: "smooth", block: "start" });
                  const input = qaEl.querySelector("input");
                  if (input) {
                    input.value = "I want to challenge a methodological choice in this topic:";
                    input.dispatchEvent(new Event("input", { bubbles: true }));
                    input.focus();
                  }
                }
              }, 100);
            }}
            className="text-xs font-medium text-[#0D7377] hover:text-[#0B6265] bg-transparent border-none cursor-pointer p-0 transition-colors"
          >
            Dispute a methodological choice &#8599;
          </button>
        </div>
      )}
    </div>
  );
}
