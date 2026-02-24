export default function AppHeader({ onNavigate, currentView, session, onSignOut }) {
  return (
    <header className="bg-white border-b border-gray-200 print:hidden">
      <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        {/* Left: Logo */}
        <button
          onClick={() => onNavigate("upload")}
          className="text-2xl font-bold text-[#1B3A5C] tracking-tight hover:opacity-80 cursor-pointer"
        >
          Parity
        </button>

        {/* Center + Right */}
        <div className="flex items-center gap-4">
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
          {session && (
            <span className="text-xs text-gray-400 hidden sm:inline">
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
