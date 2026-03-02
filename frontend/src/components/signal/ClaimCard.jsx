import { useState } from "react";
import ScoreBadge from "./ScoreBadge";
import EvidenceBadge from "./EvidenceBadge";
import ClaimDetail from "./ClaimDetail";

export default function ClaimCard({ claim, composite }) {
  const [expanded, setExpanded] = useState(false);

  const score = composite?.composite_score;
  const evidenceCategory = composite?.evidence_category;
  const sourceCount = claim._sourceCount || 0;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden transition-shadow hover:shadow-sm font-[Arial,sans-serif]">
      {/* Collapsed header — tap to expand */}
      <button
        onClick={() => setExpanded(!expanded)}
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
          <div className="flex items-center gap-2 mt-1.5">
            <EvidenceBadge category={evidenceCategory} />
            {sourceCount > 0 && (
              <span className="text-xs text-gray-400">
                {sourceCount} source{sourceCount !== 1 ? "s" : ""}
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
