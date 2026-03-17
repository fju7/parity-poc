import { useState, useEffect } from "react";
import { API_BASE } from "../lib/apiBase";

export default function HealthOpenIssues() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/platform/cases?product=health&status=open`)
      .then(r => r.ok ? r.json() : { cases: [] })
      .then(d => { setCases(d.cases || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  async function resolve(caseId, outcome) {
    setResolving(caseId);
    try {
      await fetch(`${API_BASE}/api/platform/cases/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId, outcome }),
      });
      setCases(prev => prev.filter(c => c.id !== caseId));
    } catch { /* non-fatal */ }
    setResolving(null);
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center">
        <div className="text-gray-400 animate-pulse">Loading your issues...</div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 font-[Arial,sans-serif]">
      <h1 className="text-xl font-bold text-[#1B3A5C] mb-2">Open Issues</h1>
      <p className="text-sm text-gray-500 mb-6">
        Issues you're tracking from previous bill analyses. We'll remind you to follow up.
      </p>

      {cases.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-4xl mb-3">&#10003;</div>
          <p className="text-gray-500 font-medium">No open issues.</p>
          <p className="text-gray-400 text-sm mt-1">When you flag a billing concern, it will appear here for follow-up.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {cases.map(c => {
            const daysOpen = Math.floor((Date.now() - new Date(c.opened_at).getTime()) / 86400000);
            const stale = daysOpen >= 14;
            return (
              <div key={c.id} className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="flex justify-between items-start gap-3 mb-2">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-[#1B3A5C]">
                      {c.description || `CPT ${c.cpt_code || "Unknown"}`}
                    </p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                      <span>{daysOpen} days ago</span>
                      {c.payer && <span>{c.payer}</span>}
                      {c.signal_score && (
                        <span className="text-indigo-600 font-medium">Signal: {c.signal_score}/5.0</span>
                      )}
                      {stale && (
                        <span className="font-semibold text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                          Follow up
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => resolve(c.id, "won")}
                    disabled={resolving === c.id}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg border border-emerald-200 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 cursor-pointer"
                  >
                    Resolved (got refund/correction)
                  </button>
                  <button
                    onClick={() => resolve(c.id, "withdrawn")}
                    disabled={resolving === c.id}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-500 bg-white hover:bg-gray-50 cursor-pointer"
                  >
                    Dropped
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
