import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function TopicRequestForm({ session, userTier }) {
  const navigate = useNavigate();
  const isPremium = userTier === "premium";
  const [topicName, setTopicName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceUrls, setSourceUrls] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!topicName.trim() || !description.trim() || loading) return;

    if (!session?.access_token) {
      setError("Please sign in to submit a topic request.");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const urls = sourceUrls
        .split("\n")
        .map((u) => u.trim())
        .filter(Boolean);

      const res = await fetch(`${API_BASE}/api/signal/topic-requests`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          topic_name: topicName.trim(),
          description: description.trim(),
          reference_urls: urls,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to submit request");
      }

      setSuccess(true);
      setTopicName("");
      setDescription("");
      setSourceUrls("");
    } catch (err) {
      const msg = err.message || "";
      if (msg === "Failed to fetch") {
        setError("Unable to reach the server. Please try again in a moment.");
      } else {
        setError(msg || "Something went wrong. Please try again.");
      }
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <span className="text-sm font-bold text-[#1B3A5C]">Request a Topic</span>
          <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">
            Premium
          </span>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <input
            type="text"
            disabled
            placeholder="Topic name..."
            className="w-full bg-transparent text-sm text-gray-400 placeholder-gray-400 border-none outline-none cursor-not-allowed"
          />
          <textarea
            disabled
            placeholder="Describe what you'd like us to investigate..."
            rows={2}
            className="w-full bg-transparent text-sm text-gray-400 placeholder-gray-400 border-none outline-none cursor-not-allowed resize-none"
          />
        </div>
        <p className="text-xs text-gray-400 mt-2">
          <button
            onClick={() => navigate("/signal/pricing")}
            className="text-[#0D7377] hover:underline bg-transparent border-none cursor-pointer p-0 text-xs font-medium"
          >
            Upgrade to Premium
          </button>
          {" "}to request topics for investigation.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-xl p-5 font-[Arial,sans-serif]">
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-4 h-4 text-[#0D7377]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <span className="text-sm font-bold text-[#1B3A5C]">Request a Topic</span>
      </div>

      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3 mb-4">
          Topic request submitted! We'll review it and follow up.
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-semibold text-gray-500 mb-1">
            Topic Name <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={topicName}
            onChange={(e) => setTopicName(e.target.value)}
            placeholder='e.g. "Ozempic for PCOS management"'
            maxLength={200}
            required
            disabled={loading}
            className="w-full text-sm text-[#1B3A5C] placeholder-gray-400 bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-200 outline-none focus:border-[#0D7377] transition-colors"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-500 mb-1">
            Description <span className="text-red-400">*</span>
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What specific question or angle should we investigate? What would be most useful for you?"
            maxLength={2000}
            rows={3}
            required
            disabled={loading}
            className="w-full text-sm text-[#1B3A5C] placeholder-gray-400 bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-200 outline-none focus:border-[#0D7377] transition-colors resize-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-500 mb-1">
            Source URLs <span className="text-gray-400 font-normal">(optional, one per line)</span>
          </label>
          <textarea
            value={sourceUrls}
            onChange={(e) => setSourceUrls(e.target.value)}
            placeholder={"https://pubmed.ncbi.nlm.nih.gov/...\nhttps://www.fda.gov/..."}
            rows={2}
            disabled={loading}
            className="w-full text-sm text-[#1B3A5C] placeholder-gray-400 bg-gray-50 rounded-lg px-3 py-2.5 border border-gray-200 outline-none focus:border-[#0D7377] transition-colors resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !topicName.trim() || !description.trim()}
          className={`w-full text-sm font-semibold py-2.5 rounded-lg border-none cursor-pointer transition-colors ${
            loading || !topicName.trim() || !description.trim()
              ? "bg-gray-100 text-gray-400 cursor-not-allowed"
              : "bg-[#0D7377] hover:bg-[#0B6265] text-white"
          }`}
        >
          {loading ? "Submitting..." : "Submit Request"}
        </button>
      </form>
    </div>
  );
}
