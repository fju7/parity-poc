import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import ScoreBadge from "./ScoreBadge";
import TopicRequestForm from "./TopicRequestForm";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function TopicCard({ topic }) {
  return (
    <Link
      to={`/signal/${topic.slug}`}
      className="block border border-gray-200 rounded-2xl p-6 hover:shadow-lg transition-shadow no-underline group"
    >
      <h2 className="text-lg font-bold text-[#1B3A5C] mb-2 group-hover:text-[#0D7377] transition-colors">
        {topic.title}
      </h2>

      {topic.description && (
        <p className="text-sm text-gray-600 leading-relaxed mb-4">
          {topic.description}
        </p>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">
          {topic.claim_count} claims scored
        </span>
        <span className="text-sm font-semibold text-[#0D7377] group-hover:underline">
          View Dashboard &rarr;
        </span>
      </div>
    </Link>
  );
}

export default function SignalLanding({ session, userTier }) {
  const [metrics, setMetrics] = useState(null);
  const [topics, setTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/signal/metrics`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setMetrics)
      .catch(() => {});

    fetch(`${API_BASE}/api/signal/topics`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        setTopics(data);
        setTopicsLoading(false);
      })
      .catch(() => setTopicsLoading(false));
  }, []);

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

      {/* Platform metrics */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-10">
          {[
            { value: metrics.claims_scored, label: "Claims Scored" },
            { value: metrics.topics_tracked, label: "Topics Tracked" },
            { value: metrics.sources_monitored, label: "Sources Indexed" },
            { value: metrics.updates_this_month, label: "Updates This Month" },
          ].map((m) => (
            <div key={m.label} className="bg-gray-50 rounded-xl p-3 text-center">
              <div className="text-2xl font-bold text-[#1B3A5C]">
                {m.value?.toLocaleString() || "0"}
              </div>
              <div className="text-xs text-gray-500">{m.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Topics */}
      {topicsLoading ? (
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-40 mb-4" />
          <div className="grid grid-cols-1 gap-4">
            <div className="h-48 bg-gray-100 rounded-2xl" />
            <div className="h-48 bg-gray-100 rounded-2xl" />
          </div>
        </div>
      ) : topics.length > 0 ? (
        <div>
          <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">
            Topics
          </h2>
          <div className="grid grid-cols-1 gap-4">
            {topics.map((topic) => (
              <TopicCard key={topic.id} topic={topic} />
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-gray-400 text-sm">
            No topics available yet. Check back soon.
          </p>
        </div>
      )}

      {/* Topic request */}
      <div className="mt-10">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wide mb-3">
          Have a topic you'd like us to investigate?
        </h2>
        <TopicRequestForm session={session} userTier={userTier} />
      </div>

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
          className="text-xs text-[#0D7377] hover:underline mt-2 inline-flex items-center min-h-[44px]"
        >
          View full methodology &rarr;
        </Link>
      </div>
    </div>
  );
}
