import { useState } from "react";
import ScoreBadge from "./ScoreBadge";
import EvidenceBadge from "./EvidenceBadge";
import ClaimDetail from "./ClaimDetail";
import { evidenceCategory as getEvidenceCategory } from "./WeightAdjuster";
import { trackEvent } from "../../lib/signalAnalytics";

/* ── Claim Type badge styles ── */
const CLAIM_TYPE_STYLES = {
  efficacy: { bg: "bg-blue-100", text: "text-blue-700", label: "Efficacy" },
  safety: { bg: "bg-red-100", text: "text-red-700", label: "Safety" },
  institutional: { bg: "bg-purple-100", text: "text-purple-700", label: "Institutional" },
  values_embedded: { bg: "bg-amber-100", text: "text-amber-700", label: "Values-Embedded" },
  foundational_values: { bg: "bg-gray-100", text: "text-gray-600", label: "Values" },
};

/* ── Consensus Type indicator ── */
const CONSENSUS_TYPE_CONFIG = {
  strong_consensus: {
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    color: "text-emerald-600",
    title: "Strong consensus",
  },
  active_debate: {
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
    color: "text-orange-500",
    title: "Active debate",
  },
  manufactured_controversy: {
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2z" />
      </svg>
    ),
    color: "text-red-500",
    title: "Manufactured controversy",
  },
  genuine_uncertainty: {
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    color: "text-gray-400",
    title: "Genuine uncertainty",
  },
};

function ClaimTypeBadge({ claimType }) {
  const style = CLAIM_TYPE_STYLES[claimType];
  if (!style) return null;
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

function ConsensusTypeIcon({ consensusType }) {
  const config = CONSENSUS_TYPE_CONFIG[consensusType];
  if (!config) return null;
  return (
    <span className={`${config.color} shrink-0`} title={config.title}>
      {config.icon}
    </span>
  );
}

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
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <EvidenceBadge category={evCat} />
            {claim.claim_type && <ClaimTypeBadge claimType={claim.claim_type} />}
            {claim.consensus_type && <ConsensusTypeIcon consensusType={claim.consensus_type} />}
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
