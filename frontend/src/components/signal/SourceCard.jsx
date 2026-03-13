import { trackEvent } from "../../lib/signalAnalytics";

const TYPE_LABELS = {
  clinical_trial: "Clinical Trial",
  fda: "FDA",
  cms: "CMS",
  pricing: "Pricing",
  public_reporting: "Public Reporting",
};

const TYPE_COLORS = {
  clinical_trial: "bg-purple-100 text-purple-700",
  fda: "bg-blue-100 text-blue-700",
  cms: "bg-teal-100 text-teal-700",
  pricing: "bg-amber-100 text-amber-700",
  public_reporting: "bg-gray-100 text-gray-600",
};

export default function SourceCard({ source, context }) {
  const typeLabel = TYPE_LABELS[source.source_type] || source.source_type;
  const typeColor =
    TYPE_COLORS[source.source_type] || "bg-gray-100 text-gray-600";
  const date = source.publication_date
    ? new Date(source.publication_date).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
      })
    : null;

  return (
    <div className="border border-gray-200 rounded-lg p-3 text-sm">
      <div className="flex items-center gap-2 mb-1.5">
        <span
          className={`${typeColor} text-[11px] font-semibold px-2 py-0.5 rounded-full`}
        >
          {typeLabel}
        </span>
        {date && <span className="text-gray-400 text-xs">{date}</span>}
      </div>

      {source.url ? (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#0D7377] font-medium hover:underline leading-snug block break-words"
          onClick={() =>
            trackEvent("source_clicked", {
              source_id: source.id,
              source_type: source.source_type,
              url: source.url,
            })
          }
        >
          {source.title}
        </a>
      ) : (
        <span className="text-[#1B3A5C] font-medium leading-snug block break-words">
          {source.title}
        </span>
      )}

      {context && (
        <p className="mt-2 text-gray-400 text-xs leading-relaxed border-l-2 border-gray-200 pl-2.5 italic">
          {context}
        </p>
      )}
    </div>
  );
}
