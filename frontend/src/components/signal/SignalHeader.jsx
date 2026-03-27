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

const ADMIN_USER_ID = "4c62234e-86cc-4b8d-a782-c54fe1d11eb0";

export default function SignalHeader({ session, onSignOut }) {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const userDisplay = formatUserDisplay(session);
  const isAdmin = session?.user?.id === ADMIN_USER_ID;

  return (
    <header className="sticky top-0 z-50 bg-[#0a1628]/95 backdrop-blur border-b border-white/[0.06]">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <a href="https://civicscale.ai" className="flex items-center gap-3 no-underline">
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, color: "#0a1628" }}>C</div>
          <span className="text-[#f1f5f9] font-bold text-lg tracking-tight">CivicScale</span>
        </a>

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
          {session ? (
            <>
              <button
                onClick={() => navigate("/account")}
                className="text-gray-400 hover:text-[#f1f5f9] transition-colors bg-transparent border-none cursor-pointer text-xs truncate max-w-[140px]"
              >
                {userDisplay || "Account"}
              </button>
              {isAdmin && (
                <button
                  onClick={() => navigate("/admin/requests")}
                  className="text-gray-400 hover:text-[#f1f5f9] transition-colors bg-transparent border-none cursor-pointer"
                >
                  Admin
                </button>
              )}
              <button
                onClick={onSignOut}
                className="text-gray-400 hover:text-red-500 transition-colors bg-transparent border-none cursor-pointer text-xs"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="text-gray-400 hover:text-[#f1f5f9] transition-colors no-underline font-medium"
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                style={{ background: "#14b8a6", color: "#0a1628", textDecoration: "none", borderRadius: 6, padding: "8px 20px", fontWeight: 500, fontSize: 14 }}
              >
                Start Free Trial
              </Link>
            </>
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
              {isAdmin && (
                <button
                  onClick={() => {
                    navigate("/admin/requests");
                    setMenuOpen(false);
                  }}
                  className="text-left text-gray-400 hover:text-[#f1f5f9] hover:bg-white/[0.04] bg-transparent border-none cursor-pointer py-2.5 px-2 rounded-lg transition-colors"
                >
                  Admin
                </button>
              )}
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
            <>
              <Link
                to="/login"
                onClick={() => setMenuOpen(false)}
                className="text-gray-400 hover:text-[#f1f5f9] hover:bg-white/[0.04] no-underline py-2.5 px-2 rounded-lg transition-colors font-medium"
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                onClick={() => setMenuOpen(false)}
                className="no-underline py-2.5 px-4 rounded-lg font-medium text-center"
                style={{ background: "#14b8a6", color: "#0a1628" }}
              >
                Start Free Trial
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
