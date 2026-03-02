import { Link } from "react-router-dom";

export default function SignalFooter() {
  return (
    <footer className="border-t border-gray-100 py-6 px-4 text-center font-[Arial,sans-serif]">
      <p className="text-xs text-gray-400 leading-relaxed max-w-2xl mx-auto">
        Parity Signal is powered by CivicScale benchmark infrastructure.
        Evidence assessments use publicly available research, FDA filings, and
        CMS data. Scores reflect automated analysis and should not replace
        professional medical or financial advice.{" "}
        <Link
          to="/signal/methodology"
          className="text-[#0D7377] hover:underline"
        >
          View methodology
        </Link>
        . &copy; CivicScale 2026.
      </p>
    </footer>
  );
}
