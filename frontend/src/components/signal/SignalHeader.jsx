import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function SignalHeader() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

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

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-4 text-sm font-[Arial,sans-serif]">
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

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="md:hidden flex flex-col justify-center gap-[5px] w-8 h-8 bg-transparent border-none cursor-pointer p-1"
          aria-label="Toggle menu"
        >
          <span
            className={`block h-[2px] w-full bg-[#1B3A5C] rounded transition-transform origin-center ${menuOpen ? "translate-y-[7px] rotate-45" : ""}`}
          />
          <span
            className={`block h-[2px] w-full bg-[#1B3A5C] rounded transition-opacity ${menuOpen ? "opacity-0" : ""}`}
          />
          <span
            className={`block h-[2px] w-full bg-[#1B3A5C] rounded transition-transform origin-center ${menuOpen ? "-translate-y-[7px] -rotate-45" : ""}`}
          />
        </button>
      </div>

      {/* Mobile slide-down menu */}
      <div
        className={`md:hidden overflow-hidden transition-[max-height] duration-200 ease-in-out ${menuOpen ? "max-h-40" : "max-h-0"}`}
      >
        <nav className="flex flex-col gap-1 px-4 pb-3 pt-1 font-[Arial,sans-serif] text-sm border-t border-gray-100">
          <button
            onClick={() => {
              navigate("/signal/methodology");
              setMenuOpen(false);
            }}
            className="text-left text-gray-600 hover:text-[#1B3A5C] hover:bg-gray-50 bg-transparent border-none cursor-pointer py-2.5 px-2 rounded-lg transition-colors"
          >
            Methodology
          </button>
          <Link
            to="/"
            onClick={() => setMenuOpen(false)}
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-50 no-underline py-2.5 px-2 rounded-lg transition-colors"
          >
            CivicScale
          </Link>
        </nav>
      </div>
    </header>
  );
}
