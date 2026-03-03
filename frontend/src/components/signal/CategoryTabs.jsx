function formatCategory(key) {
  if (!key) return key;
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const STATUS_DOT = {
  consensus: "bg-emerald-400",
  debated: "bg-amber-400",
  uncertain: "bg-gray-400",
};

export default function CategoryTabs({
  categories,
  consensusMap,
  selected,
  onSelect,
}) {
  return (
    <div className="overflow-x-auto scrollbar-hide -mx-4 px-4">
      <div className="flex gap-2 min-w-max py-1">
        {categories.map((cat) => {
          const active = cat === selected;
          const status = consensusMap?.[cat]?.consensus_status;
          const dotColor = STATUS_DOT[status] || "bg-gray-300";

          return (
            <button
              key={cat}
              onClick={() => onSelect(cat)}
              className={`flex items-center gap-1.5 px-4 min-h-[44px] rounded-full text-sm font-semibold transition-colors whitespace-nowrap border-none cursor-pointer font-[Arial,sans-serif] ${
                active
                  ? "bg-[#1B3A5C] text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${active ? "bg-white/60" : dotColor}`} />
              {formatCategory(cat)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
