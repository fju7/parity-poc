import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { API_BASE } from "../../lib/apiBase";
const QA_LIMITS = {
  free: 5,
  standard: 30,
  premium: 30,
  professional: 200,
};

const NEXT_TIER = {
  free: "Standard",
  standard: "Professional",
  premium: "Professional",
};

const DEFAULT_CHIPS = [
  "What is the strongest evidence on this topic?",
  "Where do researchers disagree?",
  "What would change our understanding of this?",
  "What should I actually do with this information?",
];

export default function EvidenceQA({ issueId, issueSlug, session, userTier, qaUsage, suggestedQuestions }) {
  const navigate = useNavigate();
  const tier = userTier || "free";
  const limit = QA_LIMITS[tier] ?? QA_LIMITS.free;
  const used = qaUsage?.qa_questions_used ?? 0;
  const resetAt = qaUsage?.qa_reset_at;
  const remaining = Math.max(0, limit - used);
  const atLimit = remaining <= 0;

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [localUsed, setLocalUsed] = useState(used);
  const scrollRef = useRef(null);

  useEffect(() => {
    setLocalUsed(used);
  }, [used]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const localRemaining = Math.max(0, limit - localUsed);
  const localAtLimit = localRemaining <= 0;

  async function handleSubmit(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading || localAtLimit) return;

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
        if (err.detail?.error === "qa_limit_reached") {
          setMessages((prev) => [
            ...prev,
            { role: "error", text: `You've used all ${limit} questions this month. Upgrade for more.` },
          ]);
          setLocalUsed(limit);
          return;
        }
        throw new Error(err.detail || "Failed to get answer");
      }

      const { answer } = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: answer }]);
      setLocalUsed((prev) => prev + 1);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", text: err.message || "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const resetDate = resetAt
    ? new Date(resetAt).toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : null;

  const chips = suggestedQuestions?.length ? suggestedQuestions : DEFAULT_CHIPS;

  return (
    <div data-evidence-qa className="border border-gray-200 rounded-xl overflow-hidden font-[Arial,sans-serif]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-[#0D7377]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <span className="text-sm font-bold text-[#1B3A5C]">Ask the Evidence</span>
        </div>
        <span className="text-xs font-semibold tabular-nums" style={{ color: localRemaining <= 2 ? "#A32D2D" : "#0D7377" }}>
          {localRemaining} of {limit} questions remaining
        </span>
      </div>

      {/* Suggested question chips */}
      {messages.length === 0 && !localAtLimit && (
        <div className="px-4 py-3 flex flex-wrap gap-2 border-b border-gray-100">
          {chips.map((chip, i) => (
            <button
              key={i}
              onClick={() => setQuestion(chip)}
              className="text-xs px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-[#0D7377] hover:text-[#0D7377] bg-white cursor-pointer transition-colors"
            >
              {chip}
            </button>
          ))}
        </div>
      )}

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

      {/* At-limit message */}
      {localAtLimit && (
        <div className="px-4 py-3 bg-amber-50 border-t border-amber-200">
          <p className="text-xs text-amber-700">
            You've used all {limit} questions this month.
            {resetDate && ` Resets ${resetDate}.`}
            {NEXT_TIER[tier] && (
              <>
                {" "}
                <button
                  onClick={() => navigate(`/pricing?from=/${issueSlug || ""}`)}
                  className="text-[#0D7377] hover:underline bg-transparent border-none cursor-pointer p-0 text-xs font-medium"
                >
                  Upgrade to {NEXT_TIER[tier]}
                </button>
                {" "}for more questions.
              </>
            )}
          </p>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex items-center gap-2 px-4 py-3 border-t border-gray-100">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={localAtLimit ? "Question limit reached" : "Ask a follow-up question about any claim..."}
          maxLength={1000}
          disabled={loading || localAtLimit}
          className="flex-1 text-sm text-[#1B3A5C] placeholder-gray-400 bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-200 outline-none focus:border-[#0D7377] transition-colors disabled:cursor-not-allowed disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={loading || !question.trim() || localAtLimit}
          className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center border-none cursor-pointer transition-colors ${
            loading || !question.trim() || localAtLimit
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
        <p className="text-[10px] text-gray-400 mt-0.5">
          Questions help us improve Signal. They are anonymized.
        </p>
      </div>
    </div>
  );
}
