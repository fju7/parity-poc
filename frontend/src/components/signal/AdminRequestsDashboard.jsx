import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import { API_BASE } from "../../lib/apiBase";
const STATUS_COLORS = {
  approved: "bg-blue-50 text-blue-700 border-blue-200",
  processing: "bg-indigo-50 text-indigo-700 border-indigo-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  rejected: "bg-red-50 text-red-600 border-red-200",
  clarification_needed: "bg-amber-50 text-amber-700 border-amber-200",
};

const STATUS_LABELS = {
  approved: "Approved",
  processing: "Processing",
  completed: "Completed",
  rejected: "Rejected",
  clarification_needed: "Needs Clarification",
};

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
        STATUS_COLORS[status] || "bg-gray-50 text-gray-600 border-gray-200"
      }`}
    >
      {STATUS_LABELS[status] || status}
    </span>
  );
}

function RequestCard({ req, authHeaders, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [clarifyMessage, setClarifyMessage] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [showClarify, setShowClarify] = useState(false);
  const [issueId, setIssueId] = useState("");
  const [showComplete, setShowComplete] = useState(false);

  async function adminAction(endpoint, body) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/signal/admin/topic-requests/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Action failed");
        return;
      }
      onRefresh();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
      setShowReject(false);
      setShowClarify(false);
      setShowComplete(false);
    }
  }

  const canApprove = req.status === "approved" || req.status === "clarification_needed";
  const canReject = req.status !== "rejected" && req.status !== "completed";
  const canClarify = req.status !== "completed" && req.status !== "rejected";
  const canComplete = req.status === "processing";

  return (
    <div className="border border-gray-200 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-bold text-[#1B3A5C] truncate">
              {req.parsed_title || req.raw_request?.slice(0, 60) || "Untitled"}
            </h3>
            <StatusBadge status={req.status} />
          </div>
          {req.parsed_description && (
            <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">
              {req.parsed_description}
            </p>
          )}
        </div>
        <div className="text-[10px] text-gray-400 whitespace-nowrap tabular-nums">
          {new Date(req.submitted_at).toLocaleDateString()}
        </div>
      </div>

      {req.raw_request && (
        <div className="bg-gray-50 rounded-lg px-3 py-2">
          <div className="text-[10px] font-semibold text-gray-400 uppercase mb-1">Original Request</div>
          <p className="text-xs text-gray-600 leading-relaxed">{req.raw_request}</p>
        </div>
      )}

      <div className="flex items-center gap-3 text-[10px] text-gray-400">
        <span>User: {req.user_id?.slice(0, 8)}...</span>
        {req.parsed_slug && <span>Slug: {req.parsed_slug}</span>}
        {req.rejection_reason && (
          <span className="text-red-500">Reason: {req.rejection_reason}</span>
        )}
        {req.clarification_message && (
          <span className="text-amber-600">Clarification: {req.clarification_message}</span>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        {canApprove && (
          <button
            onClick={() => adminAction("approve", { request_id: req.id })}
            disabled={loading}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#0D7377] text-white border-none cursor-pointer hover:bg-[#0B6265] transition-colors disabled:opacity-50"
          >
            {loading ? "..." : "Start Processing"}
          </button>
        )}
        {canComplete && (
          <button
            onClick={() => setShowComplete(!showComplete)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-600 text-white border-none cursor-pointer hover:bg-emerald-700 transition-colors"
          >
            Mark Complete
          </button>
        )}
        {canClarify && (
          <button
            onClick={() => { setShowClarify(!showClarify); setShowReject(false); setShowComplete(false); }}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white text-amber-700 border border-amber-300 cursor-pointer hover:bg-amber-50 transition-colors"
          >
            Ask Clarification
          </button>
        )}
        {canReject && (
          <button
            onClick={() => { setShowReject(!showReject); setShowClarify(false); setShowComplete(false); }}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white text-red-600 border border-red-300 cursor-pointer hover:bg-red-50 transition-colors"
          >
            Reject
          </button>
        )}
      </div>

      {/* Reject form */}
      {showReject && (
        <div className="flex gap-2">
          <input
            type="text"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Rejection reason..."
            className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 outline-none focus:border-red-400"
          />
          <button
            onClick={() => adminAction("reject", { request_id: req.id, reason: rejectReason })}
            disabled={loading || !rejectReason.trim()}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-red-600 text-white border-none cursor-pointer hover:bg-red-700 disabled:opacity-50"
          >
            Confirm Reject
          </button>
        </div>
      )}

      {/* Clarify form */}
      {showClarify && (
        <div className="flex gap-2">
          <input
            type="text"
            value={clarifyMessage}
            onChange={(e) => setClarifyMessage(e.target.value)}
            placeholder="What do you need clarified?"
            className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 outline-none focus:border-amber-400"
          />
          <button
            onClick={() => adminAction("clarify", { request_id: req.id, message: clarifyMessage })}
            disabled={loading || !clarifyMessage.trim()}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-amber-600 text-white border-none cursor-pointer hover:bg-amber-700 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      )}

      {/* Complete form */}
      {showComplete && (
        <div className="flex gap-2">
          <input
            type="text"
            value={issueId}
            onChange={(e) => setIssueId(e.target.value)}
            placeholder="Issue UUID (from signal_issues table)..."
            className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-1.5 outline-none focus:border-emerald-400"
          />
          <button
            onClick={() => adminAction("complete", { request_id: req.id, issue_id: issueId })}
            disabled={loading || !issueId.trim()}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-600 text-white border-none cursor-pointer hover:bg-emerald-700 disabled:opacity-50"
          >
            Complete
          </button>
        </div>
      )}
    </div>
  );
}

function fmt$(val) {
  return "$" + Number(val || 0).toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

export default function AdminRequestsDashboard({ session }) {
  const [activeTab, setActiveTab] = useState("requests");
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [patterns, setPatterns] = useState([]);
  const [patternsLoading, setPatternsLoading] = useState(false);
  const [patternsError, setPatternsError] = useState(null);
  const [searchParams] = useSearchParams();

  const secret = searchParams.get("secret");
  const token = session?.access_token;

  // Build auth headers: Bearer token if signed in, or X-Cron-Secret from ?secret= param
  const authHeaders = token
    ? { Authorization: `Bearer ${token}` }
    : secret
    ? { "X-Cron-Secret": secret }
    : null;

  function fetchRequests() {
    // Recompute auth headers at call time to avoid stale closures
    const headers = token
      ? { Authorization: `Bearer ${token}` }
      : secret
      ? { "X-Cron-Secret": secret }
      : null;

    if (!headers) return;
    setLoading(true);
    setError(null);
    const url = filterStatus
      ? `${API_BASE}/api/signal/admin/topic-requests?status=${filterStatus}`
      : `${API_BASE}/api/signal/admin/topic-requests`;

    fetch(url, { headers })
      .then((r) => {
        if (r.status === 401) throw new Error("Unauthorized — admin access required");
        if (!r.ok) throw new Error("Failed to load requests");
        return r.json();
      })
      .then((data) => {
        setRequests(data.requests || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }

  function fetchPatterns() {
    const headers = token
      ? { Authorization: `Bearer ${token}` }
      : secret
      ? { "X-Cron-Secret": secret }
      : null;
    if (!headers) return;
    setPatternsLoading(true);
    setPatternsError(null);
    fetch(`${API_BASE}/api/signal/admin/denial-patterns`, { headers })
      .then((r) => {
        if (r.status === 401) throw new Error("Unauthorized — admin access required");
        if (!r.ok) throw new Error("Failed to load denial patterns");
        return r.json();
      })
      .then((data) => {
        setPatterns(data.patterns || []);
        setPatternsLoading(false);
      })
      .catch((err) => {
        setPatternsError(err.message);
        setPatternsLoading(false);
      });
  }

  useEffect(() => {
    if (activeTab === "requests") fetchRequests();
    else fetchPatterns();
  }, [token, secret, filterStatus, activeTab]);

  if (!authHeaders) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-gray-500 text-sm">Sign in or provide ?secret= to access the admin dashboard.</p>
      </div>
    );
  }

  if (error === "Unauthorized — admin access required") {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <p className="text-red-500 text-sm">You do not have admin access.</p>
      </div>
    );
  }

  const statusCounts = {};
  for (const req of requests) {
    statusCounts[req.status] = (statusCounts[req.status] || 0) + 1;
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 font-[Arial,sans-serif]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-[#1B3A5C]">Admin Dashboard</h1>
          <p className="text-xs text-gray-400 mt-1">Signal Administration</p>
        </div>
        <button
          onClick={activeTab === "requests" ? fetchRequests : fetchPatterns}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-gray-100 text-gray-600 border-none cursor-pointer hover:bg-gray-200 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Main tab navigation */}
      <div className="flex items-center gap-2 mb-6">
        {[
          { key: "requests", label: "Topic Requests" },
          { key: "patterns", label: "Denial Patterns" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`text-xs font-semibold px-4 py-2 rounded-full border cursor-pointer transition-colors ${
              activeTab === t.key
                ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "requests" && (
        <>
          {/* Status filter tabs */}
          <div className="flex items-center gap-2 mb-6 flex-wrap">
            <button
              onClick={() => setFilterStatus("")}
              className={`text-xs font-semibold px-3 py-1.5 rounded-full border cursor-pointer transition-colors ${
                !filterStatus
                  ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
            >
              All ({requests.length})
            </button>
            {["approved", "processing", "clarification_needed", "completed", "rejected"].map((s) => (
              <button
                key={s}
                onClick={() => setFilterStatus(filterStatus === s ? "" : s)}
                className={`text-xs font-semibold px-3 py-1.5 rounded-full border cursor-pointer transition-colors ${
                  filterStatus === s
                    ? "bg-[#1B3A5C] text-white border-[#1B3A5C]"
                    : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
                }`}
              >
                {STATUS_LABELS[s]} {statusCounts[s] ? `(${statusCounts[s]})` : ""}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-32 bg-gray-100 rounded-xl" />
              <div className="h-32 bg-gray-100 rounded-xl" />
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-sm">
                {filterStatus ? "No requests with this status." : "No topic requests yet."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {requests.map((req) => (
                <RequestCard
                  key={req.id}
                  req={req}
                  authHeaders={authHeaders}
                  onRefresh={fetchRequests}
                />
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === "patterns" && (
        <>
          {patternsLoading ? (
            <div className="animate-pulse space-y-4">
              <div className="h-12 bg-gray-100 rounded-xl" />
              <div className="h-12 bg-gray-100 rounded-xl" />
              <div className="h-12 bg-gray-100 rounded-xl" />
            </div>
          ) : patternsError ? (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg px-4 py-3">
              {patternsError}
            </div>
          ) : patterns.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-sm">No denial patterns recorded yet.</p>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-xl overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    {["Denial Code", "CPT Code", "Payer", "Occurrences", "Value at Risk", "Signal Coverage", "Topic Request"].map((h) => (
                      <th key={h} className="text-left px-3 py-2.5 font-semibold text-gray-500 uppercase tracking-wide" style={{ fontSize: 10 }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {patterns.map((p, i) => (
                    <tr
                      key={p.id || i}
                      className={`border-b border-gray-100 ${!p.signal_coverage ? "bg-amber-50" : ""}`}
                    >
                      <td className="px-3 py-2.5 font-semibold text-[#1B3A5C]">{p.denial_code}</td>
                      <td className="px-3 py-2.5 text-gray-700">{p.cpt_code}</td>
                      <td className="px-3 py-2.5 text-gray-600">{p.payer}</td>
                      <td className="px-3 py-2.5 font-semibold text-gray-800">{p.occurrence_count}</td>
                      <td className="px-3 py-2.5 font-semibold text-gray-800">{fmt$(p.total_value_at_risk)}</td>
                      <td className="px-3 py-2.5">
                        {p.signal_coverage ? (
                          <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">Yes</span>
                        ) : (
                          <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">No</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        {p.topic_request_created ? (
                          <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">Created</span>
                        ) : (
                          <span className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-50 text-gray-400 border border-gray-200">None</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
