import { useState, useEffect } from "react";
import { API_BASE } from "../../lib/apiBase";

const ADMIN_USER_ID = "4c62234e-86cc-4b8d-a782-c54fe1d11eb0";

export default function AdminAnalytics({ session }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const isAdmin = session?.user?.id === ADMIN_USER_ID;

  useEffect(() => {
    if (!isAdmin) return;
    fetch(`${API_BASE}/api/signal/admin/analytics`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
    })
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [isAdmin, session]);

  if (!isAdmin) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <div className="text-red-400 text-lg font-bold">Access denied</div>
        <p className="text-gray-400 text-sm mt-2">Admin access required.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <div className="text-gray-400 animate-pulse">Loading analytics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 font-[Arial,sans-serif]">
      <h1 className="text-xl font-bold text-white mb-6">Signal Analytics</h1>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="bg-[#1B3A5C] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-white">{data?.total_events || 0}</div>
          <div className="text-xs text-gray-400">Total Events</div>
        </div>
        <div className="bg-[#1B3A5C] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-white">{data?.unique_sessions || 0}</div>
          <div className="text-xs text-gray-400">Unique Sessions</div>
        </div>
        <div className="bg-[#1B3A5C] rounded-xl p-4 text-center">
          <div className="text-2xl font-bold text-white">{data?.question_count || 0}</div>
          <div className="text-xs text-gray-400">Questions Asked</div>
        </div>
      </div>

      {/* Per-topic breakdown */}
      {data?.topics && data.topics.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wide mb-3">By Topic</h2>
          <div className="space-y-2">
            {data.topics.map((t) => (
              <div key={t.topic_slug} className="bg-white rounded-xl p-3 border border-gray-100">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-[#1B3A5C]">{t.topic_slug || "unknown"}</span>
                  <span className="text-xs text-gray-400">{t.event_count} events</span>
                </div>
                {t.top_sections && t.top_sections.length > 0 && (
                  <div className="text-xs text-gray-500">
                    Most expanded: {t.top_sections.join(", ")}
                  </div>
                )}
                {t.question_count > 0 && (
                  <div className="text-xs text-gray-500">{t.question_count} questions</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Depth distribution */}
      {data?.event_types && data.event_types.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wide mb-3">Event Types</h2>
          <div className="space-y-1.5">
            {data.event_types.map((et) => (
              <div key={et.event_type} className="flex items-center gap-3 bg-white rounded-lg border border-gray-100 px-3 py-2">
                <span className="flex-1 text-xs text-gray-600">{et.event_type}</span>
                <span className="text-xs font-medium text-[#1B3A5C] tabular-nums">{et.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* Provider Cases (Platform) */}
      {data?.provider_cases?.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wide mb-3">Provider Appeals (Data Flywheel)</h2>
          <div className="space-y-2">
            {data.provider_cases.map((pc) => (
              <div key={pc.topic_slug} className="bg-white rounded-xl p-3 border border-gray-100">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-[#1B3A5C]">{pc.topic_slug}</span>
                  <span className="text-xs text-gray-400">{pc.total} case{pc.total !== 1 ? "s" : ""} ({pc.open} open)</span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-emerald-600 font-semibold">{pc.won} won</span>
                  <span className="text-red-500 font-semibold">{pc.lost} lost</span>
                  {pc.win_rate != null && (
                    <span className={`font-bold ${pc.win_rate >= 50 ? "text-emerald-600" : "text-amber-600"}`}>
                      {pc.win_rate}% win rate
                    </span>
                  )}
                </div>
                {pc.top_codes?.length > 0 && (
                  <div className="text-xs text-gray-400 mt-1">
                    Top codes: {pc.top_codes.map(c => `${c.code} (${c.count})`).join(", ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Health Disputes (Platform) */}
      {data?.health_cases?.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wide mb-3">Health Disputes (Data Flywheel)</h2>
          <div className="space-y-2">
            {data.health_cases.map((hc) => (
              <div key={hc.topic_slug} className="bg-white rounded-xl p-3 border border-gray-100">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-[#1B3A5C]">{hc.topic_slug}</span>
                  <span className="text-xs text-gray-400">{hc.total} issue{hc.total !== 1 ? "s" : ""} ({hc.open} open)</span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-emerald-600 font-semibold">{hc.won} resolved</span>
                  <span className="text-gray-500 font-semibold">{hc.withdrawn} dropped</span>
                  {hc.win_rate != null && (
                    <span className={`font-bold ${hc.win_rate >= 50 ? "text-emerald-600" : "text-amber-600"}`}>
                      {hc.win_rate}% resolution rate
                    </span>
                  )}
                </div>
                {hc.top_codes?.length > 0 && (
                  <div className="text-xs text-gray-400 mt-1">
                    Top CPTs: {hc.top_codes.map(c => `${c.code} (${c.count})`).join(", ")}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Legacy Appeal Outcomes */}
      {data?.appeal_outcomes?.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wide mb-3">Legacy Appeal Outcomes</h2>
          <div className="space-y-2">
            {data.appeal_outcomes.map((ao) => (
              <div key={ao.topic_slug} className="bg-white rounded-xl p-3 border border-gray-100">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-[#1B3A5C]">{ao.topic_slug}</span>
                  <span className="text-xs text-gray-400">{ao.total_appeals} appeal{ao.total_appeals !== 1 ? "s" : ""}</span>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-emerald-600 font-semibold">{ao.won} won</span>
                  <span className="text-red-500 font-semibold">{ao.lost} lost</span>
                  {ao.win_rate != null && (
                    <span className={`font-bold ${ao.win_rate >= 50 ? "text-emerald-600" : "text-amber-600"}`}>
                      {ao.win_rate}% win rate
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
