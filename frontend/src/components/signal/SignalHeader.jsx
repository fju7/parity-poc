import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

function formatUserDisplay(session) {
  if (!session?.user) return null;
  const { phone, email } = session.user;
  if (phone) {
    // Format +1XXXXXXXXXX → (XXX) XXX-XXXX
    const digits = phone.replace(/\D/g, "").slice(-10);
    if (digits.length === 10) {
      return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
    }
    return phone;
  }
  if (email) {
    return email.length > 20 ? email.slice(0, 20) + "..." : email;
  }
  return "Account";
}

export default function SignalHeader({ session, onSignOut }) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const userDisplay = formatUserDisplay(session);

  return (
    <header className="sticky top-0 z-50 bg-[#0a1628]/95 backdrop-blur border-b border-white/[0.06]">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 no-underline">
          <div className="flex items-center gap-0.5">
            <div className="flex flex-col gap-[2px]">
              <div className="w-[3px] h-[10px] rounded-sm bg-[#94a3b8]" />
              <div className="w-[3px] h-[7px] rounded-sm bg-[#0D7377]" />
              <div className="w-[3px] h-[4px] rounded-sm bg-[#94a3b8]" />
            </div>
            <div className="flex flex-col gap-[2px]">
              <div className="w-[3px] h-[4px] rounded-sm bg-[#0D7377]" />
              <div className="w-[3px] h-[7px] rounded-sm bg-[#94a3b8]" />
              <div className="w-[3px] h-[10px] rounded-sm bg-[#0D7377]" />
            </div>
          </div>
          <span className="text-[#f1f5f9] font-bold text-lg tracking-tight font-[Arial,sans-serif]">
            Parity Signal
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-4 text-sm font-[Arial,sans-serif]">
          <button
            onClick={() => navigate("/methodology")}
            className="text-gray-400 hover:text-[#f1f5f9] transition-colors bg-transparent border-none cursor-pointer"
          >
            Methodology
          </button>
          <button
            onClick={() => navigate("/pricing")}
            className="text-gray-400 hover:text-[#f1f5f9] transition-colors bg-transparent border-none cursor-pointer"
          >
            Pricing
          </button>
          <a
            href="https://civicscale.ai"
            className="text-gray-500 hover:text-gray-300 transition-colors no-underline text-xs"
          >
            CivicScale
          </a>
          {session ? (
            <>
              <button
                onClick={() => navigate("/account")}
                className="text-gray-400 hover:text-[#f1f5f9] transition-colors bg-transparent border-none cursor-pointer text-xs truncate max-w-[140px]"
              >
                {userDisplay || "Account"}
              </button>
              <button
                onClick={onSignOut}
                className="text-gray-400 hover:text-red-500 transition-colors bg-transparent border-none cursor-pointer text-xs"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="text-[#0D7377] hover:text-[#0B6265] transition-colors no-underline font-medium"
            >
              Sign in
            </Link>
          )}
        </nav>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="md:hidden flex flex-col justify-center gap-[5px] w-11 h-11 bg-transparent border-none cursor-pointer p-2.5"
          aria-label="Toggle menu"
        >
          <span
            className={`block h-[2px] w-full bg-[#94a3b8] rounded transition-transform origin-center ${menuOpen ? "translate-y-[7px] rotate-45" : ""}`}
          />
          <span
            className={`block h-[2px] w-full bg-[#94a3b8] rounded transition-opacity ${menuOpen ? "opacity-0" : ""}`}
          />
          <span
            className={`block h-[2px] w-full bg-[#94a3b8] rounded transition-transform origin-center ${menuOpen ? "-translate-y-[7px] -rotate-45" : ""}`}
          />
        </button>
      </div>

      {/* Mobile slide-down menu */}
      <div
        className={`md:hidden overflow-hidden transition-[max-height] duration-200 ease-in-out ${menuOpen ? "max-h-60" : "max-h-0"}`}
      >
        <nav className="flex flex-col gap-1 px-4 pb-3 pt-1 font-[Arial,sans-serif] text-sm border-t border-white/[0.06]">
          <button
            onClick={() => {
              navigate("/methodology");
              setMenuOpen(false);
            }}
            className="text-left text-gray-400 hover:text-[#f1f5f9] hover:bg-white/[0.04] bg-transparent border-none cursor-pointer py-2.5 px-2 rounded-lg transition-colors"
          >
            Methodology
          </button>
          <button
            onClick={() => {
              navigate("/pricing");
              setMenuOpen(false);
            }}
            className="text-left text-gray-400 hover:text-[#f1f5f9] hover:bg-white/[0.04] bg-transparent border-none cursor-pointer py-2.5 px-2 rounded-lg transition-colors"
          >
            Pricing
          </button>
          <a
            href="https://civicscale.ai"
            onClick={() => setMenuOpen(false)}
            className="text-gray-500 hover:text-gray-300 hover:bg-white/[0.04] no-underline py-2.5 px-2 rounded-lg transition-colors"
          >
            CivicScale
          </a>
          {session ? (
            <>
              <button
                onClick={() => {
                  navigate("/account");
                  setMenuOpen(false);
                }}
                className="text-left text-gray-400 hover:text-[#f1f5f9] hover:bg-white/[0.04] bg-transparent border-none cursor-pointer py-2.5 px-2 rounded-lg transition-colors"
              >
                Account
              </button>
              <button
                onClick={() => {
                  onSignOut?.();
                  setMenuOpen(false);
                }}
                className="text-left text-red-400 hover:bg-red-500/10 bg-transparent border-none cursor-pointer py-2.5 px-2 rounded-lg transition-colors"
              >
                Sign out
              </button>
            </>
          ) : (
            <Link
              to="/login"
              onClick={() => setMenuOpen(false)}
              className="text-[#0D7377] hover:bg-white/[0.04] no-underline py-2.5 px-2 rounded-lg transition-colors font-medium"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
