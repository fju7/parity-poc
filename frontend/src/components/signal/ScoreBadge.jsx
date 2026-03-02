export default function ScoreBadge({ score, size = "md" }) {
  const num = Number(score);
  const display = isNaN(num) ? "—" : num.toFixed(1);

  let bg, text;
  if (num >= 4.0) {
    bg = "bg-emerald-100";
    text = "text-emerald-700";
  } else if (num >= 3.0) {
    bg = "bg-blue-100";
    text = "text-blue-700";
  } else if (num >= 2.0) {
    bg = "bg-amber-100";
    text = "text-amber-700";
  } else {
    bg = "bg-red-100";
    text = "text-red-700";
  }

  const sizeClass =
    size === "lg"
      ? "w-14 h-14 text-lg font-bold"
      : size === "sm"
        ? "w-8 h-8 text-xs font-semibold"
        : "w-10 h-10 text-sm font-bold";

  return (
    <div
      className={`${bg} ${text} ${sizeClass} rounded-full flex items-center justify-center shrink-0`}
    >
      {display}
    </div>
  );
}
