import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TOPIC_REQUEST_LIMITS = {
  free: 0,
  standard: 1,
  premium: 3,
  professional: 10,
};

export default function TopicRequestForm({ session, userTier, tierData }) {
  const navigate = useNavigate();
  const tier = userTier || "free";
  const limit = TOPIC_REQUEST_LIMITS[tier] ?? 0;
  const used = tierData?.usage?.topic_requests_used ?? 0;
  const remaining = Math.max(0, limit - used);

  const [requestText, setRequestText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // {status, ...}
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!requestText.trim() || loading) return;

    if (!session?.access_token) {
      setError("Please sign in to submit a topic request.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/api/signal/topic-request`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ request_text: requestText.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = data.detail;
        if (typeof detail === "object") {
          if (detail.error === "topic_request_not_available") {
            setError("Topic requests require a Standard plan or above.");
            return;
          }
          if (detail.error === "topic_request_limit_reached") {
            setError(`You've used all ${detail.limit} topic requests this month.`);
            return;
          }
        }
        throw new Error(typeof detail === "string" ? detail : "Failed to submit request");
      }

      const data = await res.json();
      setResult(data);

      if (data.status === "approved") {
        setRequestText("");
      }
    } catch (err) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm(requestId) {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/signal/topic-request/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          request_id: requestId,
          confirmed_title: result?.parsed_title,
        }),
      });

      if (!res.ok) throw new Error("Failed to confirm request");

      const data = await res.json();
      setResult(data);
      setRequestText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Gated state: free tier (no topic requests)
  if (limit === 0) {
    return (
      <div className="border border-white/[0.1] rounded-xl p-5 font-[Arial,sans-serif]">
        <div className="flex items-center gap-2 mb-3">
          <svg className="w-4 h-4 text-[#0D7377]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <span className="text-sm font-bold text-[#f1f5f9]">Request a New Topic</span>
        </div>
        <div className="bg-white/[0.05] rounded-lg p-4">
          <input
            type="text"
            disabled
            placeholder="What topic would you like us to research?"
            className="w-full bg-transparent text-sm text-gray-400 placeholder-gray-500 border-none outline-none cursor-not-allowed"
          />
        </div>
        <p className="text-xs text-gray-400 mt-2">
          <button
            onClick={() => navigate("/pricing")}
            className="text-[#0D7377] hover:underline bg-transparent border-none cursor-pointer p-0 text-xs font-medium"
          >
            Upgrade to Standard
          </button>
          {" "}to request topics for investigation.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-white/[0.1] rounded-xl p-5 font-[Arial,sans-serif]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-[#0D7377]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <span className="text-sm font-bold text-[#f1f5f9]">Request a New Topic</span>
        </div>
        <span className="text-[10px] text-gray-400 tabular-nums">
          {used} of {limit} used this month
        </span>
      </div>

      {/* Approved result */}
      {result?.status === "approved" && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-lg px-4 py-3 mb-4">
          <span className="font-semibold">{result.title}</span> has been queued for research.
          We'll notify you when it's ready.
        </div>
      )}

      {/* Rejected result */}
      {result?.status === "rejected" && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg px-4 py-3 mb-4">
          {result.reason}
        </div>
      )}

      {/* Clarification needed */}
      {result?.status === "clarification_needed" && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg px-4 py-3 mb-4">
          <p className="font-semibold mb-1">We have a suggestion:</p>
          <p className="text-xs leading-relaxed mb-3">{result.suggestion}</p>
          {result.parsed_title && (
            <p className="text-xs text-amber-700 mb-3">
              Suggested topic: <span className="font-semibold">{result.parsed_title}</span>
            </p>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => handleConfirm(result.request_id)}
              disabled={loading}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#0D7377] text-white border-none cursor-pointer hover:bg-[#0B6265] transition-colors"
            >
              {loading ? "Confirming..." : "Accept Suggestion"}
            </button>
            <button
              onClick={() => setResult(null)}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white text-gray-600 border border-gray-300 cursor-pointer hover:bg-gray-50 transition-colors"
            >
              Edit & Resubmit
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {/* Input form — hidden when showing clarification */}
      {result?.status !== "clarification_needed" && (
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <textarea
              value={requestText}
              onChange={(e) => setRequestText(e.target.value)}
              placeholder="What topic would you like us to research? E.g., 'I want to understand the evidence on intermittent fasting and longevity'"
              maxLength={2000}
              rows={3}
              required
              disabled={loading || remaining <= 0}
              className="w-full text-sm text-[#f1f5f9] placeholder-gray-500 bg-white/[0.05] rounded-lg px-3 py-2.5 border border-white/[0.1] outline-none focus:border-[#0D7377] transition-colors resize-none disabled:cursor-not-allowed disabled:opacity-60"
            />
          </div>

          {remaining <= 0 ? (
            <div className="text-xs text-amber-700 bg-amber-50 rounded-lg p-3">
              You've used all {limit} topic requests this month.
              {" "}
              <button
                onClick={() => navigate("/pricing")}
                className="text-[#0D7377] hover:underline bg-transparent border-none cursor-pointer p-0 text-xs font-medium"
              >
                Upgrade
              </button>
              {" "}for more, or purchase additional requests.
            </div>
          ) : (
            <button
              type="submit"
              disabled={loading || !requestText.trim()}
              className={`w-full text-sm font-semibold py-2.5 rounded-lg border-none cursor-pointer transition-colors ${
                loading || !requestText.trim()
                  ? "bg-white/[0.06] text-gray-500 cursor-not-allowed"
                  : "bg-[#0D7377] hover:bg-[#0B6265] text-white"
              }`}
            >
              {loading ? "Analyzing..." : "Submit Request"}
            </button>
          )}
        </form>
      )}
    </div>
  );
}
