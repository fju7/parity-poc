import { Link } from "react-router-dom";
import ScoreBadge from "./ScoreBadge";

function FeatureCard({ issue, summary, claimCount, sourceCount }) {
  const summaryData = summary?.summary_json;
  const overallSummary = summaryData?.overall_summary;
  const categories = summaryData?.categories
    ? Object.keys(summaryData.categories)
    : [];

  return (
    <Link
      to={`/signal/${issue.slug}`}
      className="block border border-gray-200 rounded-2xl p-6 hover:shadow-lg transition-shadow no-underline group"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-semibold text-[#0D7377] bg-teal-50 px-2.5 py-0.5 rounded-full uppercase tracking-wide">
          Featured
        </span>
        <span className="text-xs text-gray-400">
          {sourceCount} sources &middot; {claimCount} claims
        </span>
      </div>

      <h2 className="text-lg font-bold text-[#1B3A5C] mb-2 group-hover:text-[#0D7377] transition-colors">
        {issue.title}
      </h2>

      {overallSummary && (
        <p className="text-sm text-gray-600 leading-relaxed line-clamp-3 mb-4">
          {overallSummary}
        </p>
      )}

      {categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {categories.map((cat) => (
            <span
              key={cat}
              className="text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full capitalize"
            >
              {cat === "cardiovascular" ? "Heart" : cat}
            </span>
          ))}
        </div>
      )}

      <span className="text-sm font-semibold text-[#0D7377] group-hover:underline">
        View Evidence Dashboard &rarr;
      </span>
    </Link>
  );
}

export default function SignalLanding({
  issue,
  summary,
  claims,
  sources,
  loading,
}) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 font-[Arial,sans-serif]">
      {/* Hero */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-1.5 bg-teal-50 text-[#0D7377] text-xs font-semibold px-3 py-1 rounded-full mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0D7377]" />
          Public Evidence Intelligence
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-[#1B3A5C] mb-3 leading-tight">
          Evidence should be
          <br />
          <span className="text-[#0D7377]">accessible to everyone.</span>
        </h1>
        <p className="text-gray-500 text-sm sm:text-base leading-relaxed max-w-xl mx-auto">
          Parity Signal scores medical evidence claims across six dimensions of
          credibility — source quality, data support, reproducibility,
          consensus, recency, and rigor — so you can see the strength of the
          evidence, not just the headlines.
        </p>
      </div>

      {/* How it works */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        {[
          {
            num: "01",
            title: "Curate Sources",
            desc: "We index peer-reviewed trials, FDA filings, CMS data, and pricing reports on key health topics.",
          },
          {
            num: "02",
            title: "Extract & Score Claims",
            desc: "AI extracts specific claims from each source and scores them across six evidence dimensions.",
          },
          {
            num: "03",
            title: "Map Consensus",
            desc: "Claims are grouped by category and assessed for expert consensus, debate, or uncertainty.",
          },
        ].map((step) => (
          <div key={step.num} className="bg-gray-50 rounded-xl p-4">
            <div className="text-xs font-bold text-[#0D7377] mb-1">
              {step.num}
            </div>
            <div className="text-sm font-bold text-[#1B3A5C] mb-1">
              {step.title}
            </div>
            <p className="text-xs text-gray-500 leading-relaxed">
              {step.desc}
            </p>
          </div>
        ))}
      </div>

      {/* Featured topic */}
      {loading ? (
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-40 mb-4" />
          <div className="h-48 bg-gray-100 rounded-2xl" />
        </div>
      ) : issue ? (
        <div>
          <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">
            Featured Topic
          </h2>
          <FeatureCard
            issue={issue}
            summary={summary}
            claimCount={claims?.length || 0}
            sourceCount={sources?.length || 0}
          />
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-gray-400 text-sm">
            No topics available yet. Check back soon.
          </p>
        </div>
      )}

      {/* Score example */}
      <div className="mt-10 bg-gray-50 rounded-xl p-5">
        <h3 className="text-sm font-bold text-[#1B3A5C] mb-3">
          Understanding Scores
        </h3>
        <div className="flex items-center gap-4 flex-wrap">
          {[
            { score: 4.5, label: "Strong" },
            { score: 3.5, label: "Moderate" },
            { score: 2.5, label: "Mixed" },
            { score: 1.5, label: "Weak" },
          ].map((ex) => (
            <div key={ex.label} className="flex items-center gap-2">
              <ScoreBadge score={ex.score} size="sm" />
              <span className="text-xs text-gray-600">{ex.label}</span>
            </div>
          ))}
        </div>
        <Link
          to="/signal/methodology"
          className="text-xs text-[#0D7377] hover:underline mt-3 inline-block"
        >
          View full methodology &rarr;
        </Link>
      </div>
    </div>
  );
}
