import GlossaryText from "./GlossaryText";

const STATUS_CONFIG = {
  consensus: {
    dot: "bg-emerald-400",
    label: "Consensus",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
  },
  debated: {
    dot: "bg-amber-400",
    label: "Debated",
    bg: "bg-amber-50",
    border: "border-amber-200",
  },
  uncertain: {
    dot: "bg-gray-400",
    label: "Uncertain",
    bg: "bg-gray-50",
    border: "border-gray-200",
  },
};

export default function ConsensusIndicator({ consensus, glossary }) {
  if (!consensus) return null;

  const config = STATUS_CONFIG[consensus.consensus_status] || STATUS_CONFIG.uncertain;

  return (
    <div className={`${config.bg} border ${config.border} rounded-xl p-4 font-[Arial,sans-serif]`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2.5 h-2.5 rounded-full ${config.dot}`} />
        <span className="text-sm font-bold text-[#1B3A5C]">{config.label}</span>
      </div>

      {consensus.summary_text && (
        <p className="text-sm text-gray-700 leading-relaxed mb-3">
          <GlossaryText text={consensus.summary_text} glossary={glossary} />
        </p>
      )}

      {consensus.consensus_status === "debated" &&
        (consensus.arguments_for || consensus.arguments_against) && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
            {consensus.arguments_for && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <div className="text-xs font-bold text-emerald-700 mb-1">
                  Supporting Evidence
                </div>
                <p className="text-xs text-gray-700 leading-relaxed">
                  <GlossaryText text={consensus.arguments_for} glossary={glossary} />
                </p>
              </div>
            )}
            {consensus.arguments_against && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <div className="text-xs font-bold text-red-700 mb-1">
                  Opposing Evidence
                </div>
                <p className="text-xs text-gray-700 leading-relaxed">
                  <GlossaryText text={consensus.arguments_against} glossary={glossary} />
                </p>
              </div>
            )}
          </div>
        )}
    </div>
  );
}
