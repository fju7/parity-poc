import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIER_LABELS = {
  free: "Free",
  standard: "Standard",
  premium: "Premium",
  professional: "Professional",
};

const STATUS_STYLES = {
  active: { label: "Active", color: "bg-emerald-100 text-emerald-700" },
  past_due: { label: "Past Due", color: "bg-amber-100 text-amber-700" },
  canceled: { label: "Canceled", color: "bg-red-100 text-red-700" },
};

const REQUEST_STATUS_STYLES = {
  pending: { label: "Queued for research", color: "text-amber-600" },
  approved: { label: "Queued for research", color: "text-amber-600" },
  processing: { label: "Research in progress", color: "text-blue-600" },
  completed: { label: "Ready", color: "text-emerald-600" },
  clarification_needed: { label: "Needs your input", color: "text-orange-600" },
  rejected: { label: "Not available", color: "text-gray-400" },
};

function formatDate(epoch) {
  if (!epoch) return null;
  const d = typeof epoch === "number" ? new Date(epoch * 1000) : new Date(epoch);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatShortDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function AccountView({ session }) {
  const navigate = useNavigate();
  const [sub, setSub] = useState(null);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [topicRequests, setTopicRequests] = useState([]);

  useEffect(() => {
    if (!session?.access_token) {
      navigate("/signal/login");
      return;
    }

    const headers = { Authorization: `Bearer ${session.access_token}` };

    Promise.all([
      fetch(`${API_BASE}/api/signal/stripe/tier`, { headers })
        .then((res) => (res.ok ? res.json() : { tier: "free", status: "active", current_period_end: null }))
        .catch(() => ({ tier: "free", status: "active", current_period_end: null })),
      fetch(`${API_BASE}/api/signal/topic-requests`, { headers })
        .then((res) => (res.ok ? res.json() : { requests: [] }))
        .catch(() => ({ requests: [] })),
    ]).then(([tierData, reqData]) => {
      setSub(tierData);
      setTopicRequests(reqData.requests || []);
      setLoading(false);
    });
  }, [session, navigate]);

  async function handleManageSubscription() {
    if (!session?.access_token) return;
    setPortalLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/signal/stripe/portal`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (!res.ok) throw new Error();
      const { portal_url } = await res.json();
      window.location.href = portal_url;
    } catch {
      setPortalLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 font-[Arial,sans-serif] animate-pulse space-y-4">
        <div className="h-6 bg-gray-200 rounded w-1/3" />
        <div className="h-40 bg-gray-100 rounded-xl" />
      </div>
    );
  }

  const tier = sub?.tier || "free";
  const status = sub?.status || "active";
  const periodEnd = sub?.current_period_end;
  const renewalDate = formatDate(periodEnd);
  const statusStyle = STATUS_STYLES[status] || STATUS_STYLES.active;
  const isPaid = tier !== "free";
  const userEmail = session?.user?.email;
  const userPhone = session?.user?.phone;

  const limits = sub?.limits || {};
  const usage = sub?.usage || {};
  const topicLimit = limits.topics;
  const qaLimit = limits.qa_per_month || 0;
  const reqLimit = limits.topic_requests_per_month || 0;
  const qaUsed = usage.qa_questions_used || 0;
  const reqUsed = usage.topic_requests_used || 0;
  const qaReset = formatShortDate(usage.qa_reset_at);
  const reqReset = formatShortDate(usage.topic_requests_reset_at);

  return (
    <div className="max-w-lg mx-auto px-4 py-12 font-[Arial,sans-serif]">
      <h1 className="text-2xl font-bold text-[#1B3A5C] mb-8">Account</h1>

      {/* Profile */}
      <div className="bg-gray-50 rounded-xl p-5 mb-4">
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Profile
        </div>
        <div className="space-y-2">
          {userEmail && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Email</span>
              <span className="text-[#1B3A5C] font-medium">{userEmail}</span>
            </div>
          )}
          {userPhone && (
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Phone</span>
              <span className="text-[#1B3A5C] font-medium">{userPhone}</span>
            </div>
          )}
        </div>
      </div>

      {/* Subscription */}
      <div className="bg-gray-50 rounded-xl p-5 mb-4">
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Subscription
        </div>
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Current Plan</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-[#1B3A5C]">
                {TIER_LABELS[tier] || tier}
              </span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusStyle.color}`}>
                {statusStyle.label}
              </span>
            </div>
          </div>

          {isPaid && renewalDate && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">
                {status === "canceled" ? "Access Until" : "Next Renewal"}
              </span>
              <span className="text-sm text-[#1B3A5C]">{renewalDate}</span>
            </div>
          )}

          {isPaid && status === "past_due" && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mt-2">
              <p className="text-xs text-amber-700">
                Your last payment failed. Please update your payment method to avoid service interruption.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Monthly Usage */}
      <div className="bg-gray-50 rounded-xl p-5 mb-4">
        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
          Monthly Usage
        </div>
        <div className="space-y-3">
          {/* Topics */}
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-500">Topics subscribed</span>
            <span className="text-[#1B3A5C] font-medium">
              {topicLimit == null ? "Unlimited" : `${topicLimit} max`}
            </span>
          </div>

          {/* Q&A questions */}
          <div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Q&A questions</span>
              <span className="text-[#1B3A5C] font-medium">
                {qaUsed} of {qaLimit}
              </span>
            </div>
            <div className="mt-1.5 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#0D7377] rounded-full transition-all"
                style={{ width: `${qaLimit ? Math.min((qaUsed / qaLimit) * 100, 100) : 0}%` }}
              />
            </div>
            {qaReset && (
              <p className="text-[10px] text-gray-400 mt-1">Resets {qaReset}</p>
            )}
          </div>

          {/* Topic requests */}
          <div>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-500">Topic requests</span>
              <span className="text-[#1B3A5C] font-medium">
                {reqUsed} of {reqLimit}
              </span>
            </div>
            {reqLimit > 0 && (
              <div className="mt-1.5 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#0D7377] rounded-full transition-all"
                  style={{ width: `${Math.min((reqUsed / reqLimit) * 100, 100)}%` }}
                />
              </div>
            )}
            {reqReset && reqLimit > 0 && (
              <p className="text-[10px] text-gray-400 mt-1">Resets {reqReset}</p>
            )}
          </div>
        </div>
      </div>

      {/* Topic Requests History */}
      {topicRequests.length > 0 && (
        <div className="bg-gray-50 rounded-xl p-5 mb-4">
          <div className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Your Topic Requests
          </div>
          <div className="space-y-3">
            {topicRequests.map((req) => {
              const st = REQUEST_STATUS_STYLES[req.status] || REQUEST_STATUS_STYLES.pending;
              const slug = req.parsed_slug || req.issue_slug;
              return (
                <div key={req.id} className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[#1B3A5C] truncate">
                      {req.parsed_title || req.topic_name || req.raw_request}
                    </p>
                    <p className={`text-xs ${st.color}`}>{st.label}</p>
                    {req.status === "clarification_needed" && req.clarification_message && (
                      <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
                        {req.clarification_message}
                      </p>
                    )}
                  </div>
                  {req.status === "completed" && slug && (
                    <Link
                      to={`/signal/${slug}`}
                      className="shrink-0 text-xs text-[#0D7377] hover:underline no-underline whitespace-nowrap mt-0.5"
                    >
                      View &rarr;
                    </Link>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="space-y-3">
        {isPaid ? (
          <button
            onClick={handleManageSubscription}
            disabled={portalLoading}
            className={`w-full py-3 rounded-xl text-sm font-semibold border-none cursor-pointer transition-colors bg-[#1B3A5C] hover:bg-[#162f4a] text-white ${portalLoading ? "opacity-60 cursor-wait" : ""}`}
          >
            {portalLoading ? "Opening..." : "Manage Subscription"}
          </button>
        ) : (
          <button
            onClick={() => navigate("/signal/pricing")}
            className="w-full py-3 rounded-xl text-sm font-semibold border-none cursor-pointer transition-colors bg-[#0D7377] hover:bg-[#0B6265] text-white"
          >
            Upgrade Plan
          </button>
        )}

        {isPaid && (
          <p className="text-xs text-gray-400 text-center">
            Manage your payment method, change plans, or cancel your subscription through the Stripe Customer Portal.
          </p>
        )}
      </div>
    </div>
  );
}
