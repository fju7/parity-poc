import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function EvidenceQA({ issueId, issueSlug, session, userTier }) {
  const navigate = useNavigate();
  const isPremium = userTier === "premium";
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  async function handleSubmit(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/signal/qa`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ issue_id: issueId, question: q }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to get answer");
      }

      const { answer } = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message || "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  // Gated state for non-premium users
  if (!isPremium) {
    return (
      <div className="border border-gray-200 rounded-xl p-5 font-[Arial,sans-serif]">
        <div className="flex items-center gap-2 mb-3">
          <svg className="w-4 h-4 text-[#0D7377]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <span className="text-sm font-bold text-[#1B3A5C]">Ask the Evidence</span>
          <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">
            Premium
          </span>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <input
            type="text"
            disabled
            placeholder="Ask a follow-up question about any claim..."
            className="w-full bg-transparent text-sm text-gray-400 placeholder-gray-400 border-none outline-none cursor-not-allowed"
          />
        </div>
        <p className="text-xs text-gray-400 mt-2">
          <button
            onClick={() => navigate(`/signal/pricing?from=/signal/${issueSlug || ""}`)}
            className="text-[#0D7377] hover:underline bg-transparent border-none cursor-pointer p-0 text-xs font-medium"
          >
            Upgrade to Premium
          </button>
          {" "}to ask follow-up questions about any claim.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden font-[Arial,sans-serif]">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100">
        <svg className="w-4 h-4 text-[#0D7377]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
        <span className="text-sm font-bold text-[#1B3A5C]">Ask the Evidence</span>
      </div>

      {/* Messages */}
      {messages.length > 0 && (
        <div ref={scrollRef} className="max-h-80 overflow-y-auto px-4 py-3 space-y-3">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-[#1B3A5C] text-white"
                    : msg.role === "error"
                      ? "bg-red-50 text-red-600 border border-red-200"
                      : "bg-gray-50 text-gray-700"
                }`}
              >
                {msg.text.split("\n").map((line, j) => (
                  <p key={j} className={j > 0 ? "mt-2" : ""}>{line}</p>
                ))}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-50 rounded-xl px-3.5 py-2.5">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2 px-4 py-3 border-t border-gray-100">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a follow-up question about any claim..."
          maxLength={1000}
          disabled={loading}
          className="flex-1 text-sm text-[#1B3A5C] placeholder-gray-400 bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-200 outline-none focus:border-[#0D7377] transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center border-none cursor-pointer transition-colors ${
            loading || !question.trim()
              ? "bg-gray-100 text-gray-300 cursor-not-allowed"
              : "bg-[#0D7377] hover:bg-[#0B6265] text-white"
          }`}
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </form>

      <div className="px-4 pb-3">
        <p className="text-[10px] text-gray-400">
          Answers are based on scored evidence data. Not medical advice. AI may make errors.
        </p>
      </div>
    </div>
  );
}
