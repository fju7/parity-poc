import { useState } from "react";
import ScoreBadge from "./ScoreBadge";
import EvidenceBadge from "./EvidenceBadge";
import ClaimDetail from "./ClaimDetail";
import { evidenceCategory as getEvidenceCategory } from "./WeightAdjuster";
import { trackEvent } from "../../lib/signalAnalytics";

export default function ClaimCard({ claim, composite, customScore, divergent }) {
  const [expanded, setExpanded] = useState(false);

  const score = customScore != null ? customScore : composite?.composite_score;
  const evCat = customScore != null ? getEvidenceCategory(customScore) : composite?.evidence_category;
  const sourceCount = claim._sourceCount || 0;

  return (
    <div className={`rounded-xl overflow-hidden transition-shadow hover:shadow-sm font-[Arial,sans-serif] ${
      divergent ? "border-2 border-amber-300 ring-1 ring-amber-100" : "border border-gray-200"
    }`}>
      {/* Collapsed header — tap to expand */}
      <button
        onClick={() => {
          if (!expanded) {
            trackEvent("claim_expanded", {
              claim_id: claim.id,
              category: claim.category,
              composite_score: score ? Number(score) : null,
            });
          }
          setExpanded(!expanded);
        }}
        className="w-full flex items-center gap-3 p-4 bg-white text-left border-none cursor-pointer hover:bg-gray-50 transition-colors"
      >
        <ScoreBadge score={score} />

        <div className="flex-1 min-w-0">
          <p
            className={`text-sm text-[#1B3A5C] leading-snug font-medium ${
              expanded ? "" : "line-clamp-2"
            }`}
          >
            {claim.claim_text}
          </p>
          {claim.plain_summary && (
            <p className="text-xs text-gray-500 leading-relaxed mt-1 line-clamp-2">
              {claim.plain_summary}
            </p>
          )}
          <div className="flex items-center gap-2 mt-1.5">
            <EvidenceBadge category={evCat} />
            {sourceCount > 0 && (
              <span className="text-xs text-gray-400">
                {sourceCount} source{sourceCount !== 1 ? "s" : ""}
              </span>
            )}
            {divergent && (
              <span className="text-[10px] font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">
                Profile divergence
              </span>
            )}
          </div>
        </div>

        <svg
          className={`w-5 h-5 text-gray-400 shrink-0 transition-transform ${
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

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-100">
          <ClaimDetail claimId={claim.id} />
        </div>
      )}
    </div>
  );
}
