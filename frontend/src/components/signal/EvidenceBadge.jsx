const STYLES = {
  strong: "bg-emerald-100 text-emerald-700",
  moderate: "bg-blue-100 text-blue-700",
  mixed: "bg-amber-100 text-amber-700",
  weak: "bg-red-100 text-red-700",
};

const LABELS = {
  strong: "Strong",
  moderate: "Moderate",
  mixed: "Mixed",
  weak: "Weak",
};

export default function EvidenceBadge({ category }) {
  const key = (category || "").toLowerCase();
  const style = STYLES[key] || "bg-gray-100 text-gray-600";
  const label = LABELS[key] || category || "Unknown";

  return (
    <span
      className={`${style} text-xs font-semibold px-2.5 py-0.5 rounded-full inline-block`}
    >
      {label}
    </span>
  );
}
