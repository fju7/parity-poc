import { useState, useEffect } from "react";
import { API_BASE } from "../../lib/apiBase";

const REVIEW_COLORS = {
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  pending: "bg-amber-50 text-amber-700 border-amber-200",
  rejected: "bg-red-50 text-red-600 border-red-200",
};

const REVIEW_LABELS = {
  approved: "Approved",
  pending: "Pending Review",
  rejected: "Rejected",
};

function ReviewBadge({ status }) {
  return (
    <span
      className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
        REVIEW_COLORS[status] || "bg-gray-50 text-gray-600 border-gray-200"
      }`}
    >
      {REVIEW_LABELS[status] || status || "pending"}
    </span>
  );
}

const SUMMARY_COLORS = {
  approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  generated: "bg-blue-50 text-blue-700 border-blue-200",
  pending: "bg-gray-50 text-gray-500 border-gray-200",
};

const SUMMARY_LABELS = {
  approved: "Summary Approved",
  generated: "Summary Pending Review",
  pending: "No Summary",
};

function TopicReviewCard({ topic, onAction }) {
  const [loading, setLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [previewSummary, setPreviewSummary] = useState(topic.plain_summary || "");
  const [summaryStatus, setSummaryStatus] = useState(topic.plain_summary_status || "pending");
  const status = topic.quality_review_status || "pending";

  async function handleAction(newStatus) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/signal/admin/review-topic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ issue_id: topic.id, status: newStatus }),
      });
      if (res.ok) {
        onAction();
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.error || "Action failed");
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-bold text-[#1B3A5C] truncate">{topic.title}</h3>
            <ReviewBadge status={status} />
          </div>
          <p className="text-xs text-gray-500 line-clamp-2">{topic.description}</p>
        </div>
        <a
          href={`/signal/${topic.slug}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-[#0D7377] hover:underline shrink-0"
        >
          View Dashboard
        </a>
      </div>

      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span>{topic.claim_count} claims</span>
        <span>{topic.source_count} sources</span>
        <span>Slug: {topic.slug}</span>
        {topic.created_at && (
          <span>{new Date(topic.created_at).toLocaleDateString()}</span>
        )}
      </div>

      <div className="flex items-center gap-2 pt-1">
        {status !== "approved" && (
          <button
            onClick={() => handleAction("approved")}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            Approve
          </button>
        )}
        {status !== "pending" && (
          <button
            onClick={() => handleAction("pending")}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 cursor-pointer bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Reset to Pending
          </button>
        )}
        {status !== "rejected" && (
          <button
            onClick={() => handleAction("rejected")}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-red-200 cursor-pointer bg-white text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            Reject
          </button>
        )}
      </div>

      {/* Plain Summary Section */}
      <div className="border-t border-gray-100 pt-3 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-500">Plain Summary</span>
          <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full border ${SUMMARY_COLORS[summaryStatus] || SUMMARY_COLORS.pending}`}>
            {SUMMARY_LABELS[summaryStatus] || "No Summary"}
          </span>
        </div>

        {previewSummary && summaryStatus !== "pending" && (
          <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-700 leading-relaxed max-h-40 overflow-y-auto whitespace-pre-line">
            {previewSummary}
          </div>
        )}

        <div className="flex items-center gap-2">
          <button
            onClick={async () => {
              setSummaryLoading(true);
              try {
                const res = await fetch(`${API_BASE}/api/signal/admin/generate-plain-summary`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ issue_id: topic.id }),
                });
                if (res.ok) {
                  const data = await res.json();
                  setPreviewSummary(data.plain_summary || "");
                  setSummaryStatus("generated");
                } else {
                  const data = await res.json().catch(() => ({}));
                  alert(data.error || "Generation failed");
                }
              } catch (err) { alert(err.message); }
              finally { setSummaryLoading(false); }
            }}
            disabled={summaryLoading}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-blue-200 cursor-pointer bg-white text-blue-600 hover:bg-blue-50 disabled:opacity-50 transition-colors"
          >
            {summaryLoading ? "Generating..." : summaryStatus === "pending" ? "Generate Plain Summary" : "Regenerate"}
          </button>

          {summaryStatus === "generated" && (
            <button
              onClick={async () => {
                setSummaryLoading(true);
                try {
                  const res = await fetch(`${API_BASE}/api/signal/admin/approve-plain-summary`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ issue_id: topic.id }),
                  });
                  if (res.ok) {
                    setSummaryStatus("approved");
                    onAction();
                  }
                } catch (err) { alert(err.message); }
                finally { setSummaryLoading(false); }
              }}
              disabled={summaryLoading}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              Approve Summary
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AdminReviewDashboard({ session }) {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  async function loadTopics() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/signal/admin/review-topics`);
      if (res.ok) {
        const data = await res.json();
        setTopics(data);
      }
    } catch (err) {
      console.error("Failed to load topics:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTopics();
  }, []);

  const filtered =
    filter === "all"
      ? topics
      : topics.filter((t) => (t.quality_review_status || "pending") === filter);

  const counts = {
    all: topics.length,
    pending: topics.filter((t) => (t.quality_review_status || "pending") === "pending").length,
    approved: topics.filter((t) => t.quality_review_status === "approved").length,
    rejected: topics.filter((t) => t.quality_review_status === "rejected").length,
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-lg font-bold text-white mb-1">Quality Review Gate</h1>
        <p className="text-sm text-gray-400">
          Review and approve topics before they appear publicly on Parity Signal.
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-4">
        {["all", "pending", "approved", "rejected"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border-none cursor-pointer transition-colors ${
              filter === f
                ? "bg-[#0D7377] text-white"
                : "bg-[#1B3A5C] text-gray-300 hover:text-white"
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)} ({counts[f]})
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-800/50 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500 text-sm">
          No topics matching this filter.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((topic) => (
            <TopicReviewCard key={topic.id} topic={topic} onAction={loadTopics} />
          ))}
        </div>
      )}
    </div>
  );
}
