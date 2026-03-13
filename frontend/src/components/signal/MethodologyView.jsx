import { Link } from "react-router-dom";

const DIMENSIONS = [
  {
    name: "Source Quality",
    key: "source_quality",
    weight: "25%",
    description:
      "Evaluates the credibility and tier of the underlying source. Peer-reviewed Phase III trials and FDA regulatory filings score highest. News articles and opinion pieces score lowest.",
    scale: [
      "1 — Blog post or unverified claim",
      "2 — News reporting without primary source",
      "3 — Government report or industry analysis",
      "4 — Peer-reviewed observational study",
      "5 — Peer-reviewed RCT or FDA filing",
    ],
  },
  {
    name: "Data Support",
    key: "data_support",
    weight: "20%",
    description:
      "Measures whether the claim is backed by quantitative data — sample sizes, effect sizes, confidence intervals, or measurable outcomes.",
    scale: [
      "1 — No data cited",
      "2 — Anecdotal evidence only",
      "3 — Limited quantitative data",
      "4 — Robust data with statistical measures",
      "5 — Large-scale data with strong statistical significance",
    ],
  },
  {
    name: "Reproducibility",
    key: "reproducibility",
    weight: "15%",
    description:
      "Assesses whether findings have been replicated across independent studies, populations, or geographies.",
    scale: [
      "1 — Single unreplicated finding",
      "2 — Single study with no replication attempt",
      "3 — Replicated in limited settings",
      "4 — Replicated across multiple independent studies",
      "5 — Widely replicated with consistent results",
    ],
  },
  {
    name: "Consensus",
    key: "consensus",
    weight: "15%",
    description:
      "Reflects the degree of expert and institutional agreement on the claim. Unanimous FDA approval signals strong consensus; active scientific debate signals lower consensus.",
    scale: [
      "1 — Actively disputed by experts",
      "2 — Significant disagreement",
      "3 — Emerging agreement with caveats",
      "4 — Broad agreement among experts",
      "5 — Unanimous institutional consensus",
    ],
  },
  {
    name: "Recency",
    key: "recency",
    weight: "15%",
    description:
      "Weights more recent evidence higher. In fast-moving fields like GLP-1 research, a 2024 study is more relevant than a 2019 study, even if the older study is well-designed.",
    scale: [
      "1 — Over 5 years old",
      "2 — 3-5 years old",
      "3 — 1-3 years old",
      "4 — Within the last year",
      "5 — Within the last 6 months",
    ],
  },
  {
    name: "Rigor",
    key: "rigor",
    weight: "10%",
    description:
      "Evaluates methodological quality — study design, control groups, blinding, bias mitigation, and appropriate statistical methods.",
    scale: [
      "1 — No discernible methodology",
      "2 — Weak methodology or high bias risk",
      "3 — Acceptable methodology with limitations",
      "4 — Strong methodology with minor gaps",
      "5 — Gold-standard methodology (double-blind RCT, pre-registered)",
    ],
  },
];

const EVIDENCE_CATEGORIES = [
  {
    name: "Strong",
    range: "4.0 — 5.0",
    color: "bg-emerald-100 text-emerald-700",
    description:
      "Claim is well-supported by high-quality, recent, replicated evidence with broad expert consensus.",
  },
  {
    name: "Moderate",
    range: "3.0 — 3.9",
    color: "bg-blue-100 text-blue-700",
    description:
      "Claim has meaningful support but may lack replication, have mixed data quality, or be relatively recent with limited follow-up.",
  },
  {
    name: "Mixed",
    range: "2.0 — 2.9",
    color: "bg-amber-100 text-amber-700",
    description:
      "Evidence is conflicting, limited, or from lower-quality sources. The claim may be plausible but is not yet well-established.",
  },
  {
    name: "Weak",
    range: "1.0 — 1.9",
    color: "bg-red-100 text-red-700",
    description:
      "Minimal or no credible evidence supports this claim. May be speculative, anecdotal, or contradicted by stronger evidence.",
  },
];

export default function MethodologyView() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 font-[Arial,sans-serif]">
      <Link
        to="/signal"
        className="text-sm text-[#0D7377] hover:underline mb-4 inline-flex items-center gap-1 min-h-[44px]"
      >
        &larr; Back to Signal
      </Link>

      <h1 className="text-2xl font-bold text-white mb-2">
        Scoring Methodology
      </h1>
      <p className="text-gray-300 text-sm leading-relaxed mb-8">
        Parity Signal evaluates medical evidence claims across six dimensions.
        Each claim receives a score of 1-5 on every dimension. The composite
        score is a weighted average that determines the overall evidence
        strength.
      </p>

      {/* Composite formula */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 mb-8">
        <h2 className="text-sm font-bold text-[#1B3A5C] mb-2">
          Composite Score Formula
        </h2>
        <p className="text-sm text-gray-600 leading-relaxed mb-3">
          The composite score is a weighted average of six dimension scores:
        </p>
        <div className="bg-white rounded-lg p-3 font-mono text-xs text-[#1B3A5C] leading-loose border border-gray-100 overflow-x-auto">
          <div className="min-w-0">
            composite =<br />
            &nbsp;&nbsp;(source_quality × 0.25)<br />
            &nbsp;&nbsp;+ (data_support × 0.20)<br />
            &nbsp;&nbsp;+ (reproducibility × 0.15)<br />
            &nbsp;&nbsp;+ (consensus × 0.15)<br />
            &nbsp;&nbsp;+ (recency × 0.15)<br />
            &nbsp;&nbsp;+ (rigor × 0.10)
          </div>
        </div>
      </div>

      {/* Dimensions */}
      <h2 className="text-lg font-bold text-white mb-4">
        Scoring Dimensions
      </h2>
      <div className="space-y-5 mb-10">
        {DIMENSIONS.map((dim) => (
          <div
            key={dim.key}
            className="border border-white/[0.1] rounded-xl p-4"
          >
            <div className="flex items-center justify-between mb-1">
              <h3 className="font-bold text-[#f1f5f9] text-sm">{dim.name}</h3>
              <span className="text-xs font-semibold text-[#0D7377] bg-[#0D7377]/10 px-2 py-0.5 rounded-full">
                Weight: {dim.weight}
              </span>
            </div>
            <p className="text-sm text-gray-300 leading-relaxed mb-3">
              {dim.description}
            </p>
            <div className="space-y-1">
              {dim.scale.map((level, i) => (
                <div key={i} className="text-xs text-gray-400 leading-relaxed">
                  {level}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Evidence categories */}
      <h2 className="text-lg font-bold text-white mb-4">
        Evidence Categories
      </h2>
      <p className="text-sm text-gray-300 leading-relaxed mb-4">
        The composite score maps to an evidence category:
      </p>
      <div className="space-y-3 mb-10">
        {EVIDENCE_CATEGORIES.map((cat) => (
          <div
            key={cat.name}
            className="flex items-start gap-3 border border-white/[0.1] rounded-lg p-3"
          >
            <span
              className={`${cat.color} text-xs font-semibold px-2.5 py-0.5 rounded-full shrink-0 mt-0.5`}
            >
              {cat.name}
            </span>
            <div>
              <span className="text-xs font-semibold text-gray-400">
                {cat.range}
              </span>
              <p className="text-sm text-gray-300 leading-relaxed mt-0.5">
                {cat.description}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Consensus mapping */}
      <h2 className="text-lg font-bold text-white mb-4">
        Consensus Mapping
      </h2>
      <p className="text-sm text-gray-300 leading-relaxed mb-4">
        Claims are grouped by category (e.g., efficacy, safety, pricing) and an
        AI model assesses the overall consensus status for each category:
      </p>
      <div className="space-y-2 mb-10">
        {[
          {
            status: "Consensus",
            dot: "bg-emerald-400",
            desc: "Evidence overwhelmingly supports a single position within the category.",
          },
          {
            status: "Debated",
            dot: "bg-amber-400",
            desc: "Credible evidence exists on multiple sides. Key arguments for and against are presented.",
          },
          {
            status: "Uncertain",
            dot: "bg-gray-400",
            desc: "Insufficient or too early-stage evidence to determine a clear direction.",
          },
        ].map((s) => (
          <div key={s.status} className="flex items-start gap-2.5 py-2">
            <span className={`w-2.5 h-2.5 rounded-full ${s.dot} shrink-0 mt-1`} />
            <div>
              <span className="text-sm font-bold text-[#f1f5f9]">
                {s.status}
              </span>
              <p className="text-sm text-gray-300">{s.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Disclaimer */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-xs text-gray-500 leading-relaxed">
        <strong className="text-gray-700">Disclaimer:</strong> Parity Signal
        provides automated evidence assessments based on publicly available
        research. Scores are generated by AI models and reflect the quality and
        quantity of available evidence — not clinical recommendations. Always
        consult healthcare professionals for medical decisions. Source data is
        updated periodically; individual scores may change as new evidence
        becomes available.
      </div>
    </div>
  );
}
