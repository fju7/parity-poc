export default function AppHeader({ onNavigate, currentView, session, onSignOut }) {
  return (
    <header className="bg-white border-b border-gray-200 print:hidden">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        {/* Left: Logo */}
        <button
          onClick={() => onNavigate("upload")}
          className="hover:opacity-80 cursor-pointer text-left"
        >
          <span className="text-2xl font-bold text-[#1B3A5C] tracking-tight block leading-tight">Parity Health</span>
          <span className="text-[10px] text-gray-400 font-normal tracking-wide">by CivicScale</span>
        </button>

        {/* Center + Right */}
        <div className="flex items-center gap-2 sm:gap-4 flex-wrap justify-end">
          <button
            onClick={() => onNavigate("history")}
            className={`text-sm font-medium cursor-pointer ${
              currentView === "history"
                ? "text-[#0D7377]"
                : "text-gray-500 hover:text-[#1B3A5C]"
            }`}
          >
            Bill History
          </button>
          <button
            onClick={() => onNavigate("account")}
            className={`text-sm font-medium cursor-pointer ${
              currentView === "account"
                ? "text-[#0D7377]"
                : "text-gray-500 hover:text-[#1B3A5C]"
            }`}
          >
            My Account
          </button>
          <a
            href="mailto:admin@civicscale.ai?subject=Parity%20Health%20Support%20Request"
            className="text-sm font-medium text-gray-500 hover:text-[#1B3A5C] no-underline"
          >
            Get Help
          </a>
          {session && (
            <span className="text-xs text-gray-400 hidden sm:inline max-w-[140px] truncate">
              {session.user.email}
            </span>
          )}
          {onSignOut && (
            <button
              onClick={onSignOut}
              className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer"
            >
              Sign Out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
