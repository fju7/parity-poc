import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabase";
import SourceCard from "./SourceCard";

const DIMENSION_LABELS = {
  source_quality: "Source Quality",
  data_support: "Data Support",
  reproducibility: "Reproducibility",
  consensus: "Consensus",
  recency: "Recency",
  rigor: "Rigor",
};

const DIMENSION_ORDER = [
  "source_quality",
  "data_support",
  "reproducibility",
  "consensus",
  "recency",
  "rigor",
];

function ScoreBar({ score }) {
  const pct = ((score || 0) / 5) * 100;
  let barColor;
  if (score >= 4) barColor = "bg-emerald-400";
  else if (score >= 3) barColor = "bg-blue-400";
  else if (score >= 2) barColor = "bg-amber-400";
  else barColor = "bg-red-400";

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-gray-600 w-4 text-right">
        {score}
      </span>
    </div>
  );
}

export default function ClaimDetail({ claimId }) {
  const [scores, setScores] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      const [scoresRes, sourcesRes] = await Promise.all([
        supabase
          .from("signal_claim_scores")
          .select("*")
          .eq("claim_id", claimId),
        supabase
          .from("signal_claim_sources")
          .select("source_context, signal_sources(*)")
          .eq("claim_id", claimId),
      ]);

      if (cancelled) return;
      setScores(scoresRes.data || []);
      setSources(sourcesRes.data || []);
      setLoading(false);
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [claimId]);

  if (loading) {
    return (
      <div className="py-4 space-y-3 animate-pulse">
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-10 bg-gray-100 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const orderedScores = DIMENSION_ORDER.map((dim) =>
    scores.find((s) => s.dimension === dim)
  ).filter(Boolean);

  return (
    <div className="pt-3 pb-1 space-y-4 font-[Arial,sans-serif]">
      {/* Dimension scores grid */}
      {orderedScores.length > 0 && (
        <div>
          <div className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">
            Dimension Scores
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-3">
            {orderedScores.map((s) => (
              <div key={s.dimension}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-semibold text-[#1B3A5C]">
                    {DIMENSION_LABELS[s.dimension] || s.dimension}
                  </span>
                </div>
                <ScoreBar score={s.score} />
                {s.rationale && (
                  <p className="text-[11px] text-gray-500 mt-0.5 leading-snug">
                    {s.rationale}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Linked sources */}
      {sources.length > 0 && (
        <div>
          <div className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">
            Sources ({sources.length})
          </div>
          <div className="space-y-2">
            {sources.map((cs, i) => (
              <SourceCard
                key={cs.signal_sources?.id || i}
                source={cs.signal_sources || {}}
                context={cs.source_context}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
