import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import ScoreBadge from "./ScoreBadge";
import TopicRequestForm from "./TopicRequestForm";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function TopicCard({ topic }) {
  return (
    <Link
      to={`/${topic.slug}`}
      className="block border border-white/[0.08] rounded-2xl p-6 hover:border-white/[0.15] transition-colors no-underline group bg-white/[0.02]"
    >
      <h2 className="text-lg font-bold text-[#cbd5e1] mb-2 group-hover:text-[#0D7377] transition-colors">
        {topic.title}
      </h2>

      {topic.description && (
        <p className="text-sm text-gray-300 leading-relaxed mb-4">
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

function fetchWithRetry(url, retries = 2) {
  return fetch(url).then((r) => {
    if (!r.ok && retries > 0) {
      return new Promise((res) => setTimeout(res, 1500)).then(() =>
        fetchWithRetry(url, retries - 1)
      );
    }
    return r;
  }).catch((err) => {
    if (retries > 0) {
      return new Promise((res) => setTimeout(res, 1500)).then(() =>
        fetchWithRetry(url, retries - 1)
      );
    }
    throw err;
  });
}

export default function SignalLanding({ session, userTier, tierData }) {
  const [metrics, setMetrics] = useState(null);
  const [topics, setTopics] = useState([]);
  const [topicsLoading, setTopicsLoading] = useState(true);

  useEffect(() => {
    fetchWithRetry(`${API_BASE}/api/signal/metrics`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setMetrics)
      .catch(() => {});

    fetchWithRetry(`${API_BASE}/api/signal/topics`)
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
        <div className="inline-flex items-center gap-1.5 bg-[#0D7377]/10 text-[#0D7377] text-xs font-semibold px-3 py-1 rounded-full mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-[#0D7377]" />
          Decision Engineering
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-[#f1f5f9] mb-3 leading-tight">
          Evidence should be
          <br />
          <span className="text-[#0D7377]">accessible to everyone.</span>
        </h1>
        <p className="text-gray-300 text-sm sm:text-base leading-relaxed max-w-xl mx-auto">
          Parity Signal scores medical evidence claims across six dimensions of
          credibility — source quality, data support, reproducibility,
          consensus, recency, and rigor — so you can see the strength of the
          evidence, not just the headlines.
        </p>
      </div>

      {/* About Signal */}
      <div className="mb-10 rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6">
        <h2 className="text-lg font-bold text-[#f1f5f9] mb-3">The engine behind Parity</h2>
        <p className="text-sm text-gray-300 leading-relaxed mb-3">
          Signal is the decision-engineering engine that powers all four Parity products — Employer, Broker, Provider, and Health. It ingests public benchmark data, normalizes it across geographies and time, applies multi-dimensional scoring, and generates transparent, plain-language explanations.
        </p>
        <p className="text-sm text-gray-300 leading-relaxed">
          While healthcare is where we start — because a discoverable public reference price exists (Medicare) and regulatory tailwinds are forcing data into the open — Signal's analytical architecture extends to any domain with information asymmetry: insurance premiums, property tax assessments, policy claims in public debate.
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
          <div key={step.num} className="bg-white/[0.03] rounded-xl border border-white/[0.06] p-4">
            <div className="text-xs font-bold text-[#0D7377] mb-1">
              {step.num}
            </div>
            <div className="text-sm font-bold text-[#f1f5f9] mb-1">
              {step.title}
            </div>
            <p className="text-xs text-gray-400 leading-relaxed">
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
            <div key={m.label} className="bg-white/[0.03] rounded-xl border border-white/[0.06] p-3 text-center">
              <div className="text-2xl font-bold text-[#f1f5f9]">
                {m.value?.toLocaleString() || "0"}
              </div>
              <div className="text-xs text-gray-400">{m.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Topics */}
      {topicsLoading ? (
        <div className="animate-pulse">
          <div className="h-6 bg-white/[0.06] rounded w-40 mb-4" />
          <div className="grid grid-cols-1 gap-4">
            <div className="h-48 bg-white/[0.03] rounded-2xl" />
            <div className="h-48 bg-white/[0.03] rounded-2xl" />
          </div>
        </div>
      ) : topics.length > 0 ? (
        <div>
          <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wide mb-3">
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
          <p className="text-gray-300 text-sm">
            No topics available yet. Check back soon.
          </p>
        </div>
      )}

      {/* Topic request */}
      <div className="mt-10">
        <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wide mb-3">
          Have a topic you'd like us to investigate?
        </h2>
        <TopicRequestForm session={session} userTier={userTier} tierData={tierData} />
      </div>

      {/* Score example */}
      <div className="mt-10 bg-white/[0.03] rounded-xl border border-white/[0.06] p-5">
        <h3 className="text-sm font-bold text-[#f1f5f9] mb-3">
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
              <span className="text-xs text-gray-300">{ex.label}</span>
            </div>
          ))}
        </div>
        <Link
          to="/methodology"
          className="text-xs text-[#0D7377] hover:underline mt-2 inline-flex items-center min-h-[44px]"
        >
          View full methodology &rarr;
        </Link>
      </div>
    </div>
  );
}
