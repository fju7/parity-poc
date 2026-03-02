import { Link, useNavigate } from "react-router-dom";

export default function SignalHeader() {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-gray-100">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/signal" className="flex items-center gap-2 no-underline">
          <div className="flex items-center gap-0.5">
            <div className="flex flex-col gap-[2px]">
              <div className="w-[3px] h-[10px] rounded-sm bg-[#1B3A5C]" />
              <div className="w-[3px] h-[7px] rounded-sm bg-[#0D7377]" />
              <div className="w-[3px] h-[4px] rounded-sm bg-[#1B3A5C]" />
            </div>
            <div className="flex flex-col gap-[2px]">
              <div className="w-[3px] h-[4px] rounded-sm bg-[#0D7377]" />
              <div className="w-[3px] h-[7px] rounded-sm bg-[#1B3A5C]" />
              <div className="w-[3px] h-[10px] rounded-sm bg-[#0D7377]" />
            </div>
          </div>
          <span className="text-[#1B3A5C] font-bold text-lg tracking-tight font-[Arial,sans-serif]">
            Parity Signal
          </span>
        </Link>

        <nav className="flex items-center gap-4 text-sm font-[Arial,sans-serif]">
          <button
            onClick={() => navigate("/signal/methodology")}
            className="text-gray-500 hover:text-[#1B3A5C] transition-colors bg-transparent border-none cursor-pointer"
          >
            Methodology
          </button>
          <Link
            to="/"
            className="text-gray-400 hover:text-gray-600 transition-colors no-underline text-xs"
          >
            CivicScale
          </Link>
        </nav>
      </div>
    </header>
  );
}
