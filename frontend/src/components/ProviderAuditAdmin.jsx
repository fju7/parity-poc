import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TEAL = "#0D9488";
const NAVY = "#1E293B";
const SLATE = "#64748B";

const STATUS_COLORS = {
  submitted: { bg: "#EFF6FF", text: "#2563EB", border: "#BFDBFE" },
  processing: { bg: "#EEF2FF", text: "#4F46E5", border: "#C7D2FE" },
  review: { bg: "#FFFBEB", text: "#D97706", border: "#FDE68A" },
  delivered: { bg: "#ECFDF5", text: "#059669", border: "#A7F3D0" },
};

const STATUS_LABELS = {
  submitted: "Submitted",
  processing: "Processing",
  review: "Ready for Review",
  delivered: "Delivered",
};

function StatusBadge({ status }) {
  const c = STATUS_COLORS[status] || { bg: "#F3F4F6", text: "#6B7280", border: "#D1D5DB" };
  return (
    <span style={{
      display: "inline-block", fontSize: 11, fontWeight: 600,
      padding: "3px 10px", borderRadius: 20,
      background: c.bg, color: c.text, border: `1px solid ${c.border}`,
    }}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

function AuditRow({ audit, authHeaders, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState(audit.admin_notes || "");
  const [showNotes, setShowNotes] = useState(false);
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [viewResults, setViewResults] = useState(null); // fetched payer_results
  const [showBackfill, setShowBackfill] = useState(false);
  const [backfillZip, setBackfillZip] = useState("");
  const [backfillPct, setBackfillPct] = useState("120");
  const [uploading835, setUploading835] = useState(false);

  async function adminAction(endpoint, body) {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/provider/admin/audits/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders },
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
      setShowNotes(false);
    }
  }

  const payers = audit.payer_list || [];
  const payerNames = payers.map(p => p.payer_name || "Unknown").join(", ") || "None";
  const createdAt = audit.created_at
    ? new Date(audit.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "—";
  const deliveredAt = audit.delivered_at
    ? new Date(audit.delivered_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : null;

  return (
    <div style={{
      border: "1px solid #E2E8F0", borderRadius: 12, marginBottom: 12,
      background: "#fff", overflow: "hidden",
    }}>
      {/* Summary row */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "grid", gridTemplateColumns: "2fr 1fr 1fr 100px 100px",
          gap: 12, padding: "14px 20px", cursor: "pointer",
          alignItems: "center",
          background: expanded ? "#F8FAFC" : "#fff",
          transition: "background 0.1s",
        }}
      >
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>{audit.practice_name}</div>
          <div style={{ fontSize: 12, color: SLATE }}>{audit.practice_specialty || "—"}</div>
        </div>
        <div style={{ fontSize: 13, color: NAVY }}>{payerNames}</div>
        <div style={{ fontSize: 13, color: SLATE }}>{audit.contact_email}</div>
        <div><StatusBadge status={audit.status} /></div>
        <div style={{ fontSize: 12, color: SLATE }}>{createdAt}</div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div style={{ padding: "0 20px 20px", borderTop: "1px solid #E2E8F0" }}>
          {/* Details grid */}
          <div style={{
            display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
            gap: 16, marginTop: 16, marginBottom: 16,
          }}>
            <div>
              <div style={{ fontSize: 11, color: SLATE, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Audit ID</div>
              <div style={{ fontSize: 12, fontFamily: "monospace", color: NAVY }}>{audit.id}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: SLATE, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Providers</div>
              <div style={{ fontSize: 14, color: NAVY }}>{audit.num_providers || 1}</div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: SLATE, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Billing Company</div>
              <div style={{ fontSize: 14, color: NAVY }}>{audit.billing_company || "In-house"}</div>
            </div>
            {deliveredAt && (
              <div>
                <div style={{ fontSize: 11, color: SLATE, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Delivered</div>
                <div style={{ fontSize: 14, color: NAVY }}>{deliveredAt}</div>
              </div>
            )}
            {audit.follow_up_sent && (
              <div>
                <div style={{ fontSize: 11, color: SLATE, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4 }}>Follow-up</div>
                <div style={{ fontSize: 14, color: "#059669" }}>Sent</div>
              </div>
            )}
          </div>

          {/* Payer details */}
          {payers.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: NAVY, marginBottom: 8 }}>Payers</div>
              {payers.map((p, i) => (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "8px 12px", borderRadius: 6, marginBottom: 4,
                  background: "#F0FDFA", border: `1px solid #99F6E4`, fontSize: 13,
                }}>
                  <span style={{ fontWeight: 500, color: NAVY }}>{p.payer_name}</span>
                  <span style={{ color: SLATE }}>
                    {p.fee_schedule_method || p.method || "—"} &middot; {p.code_count || "?"} codes
                    {p.fee_schedule_data && Object.keys(p.fee_schedule_data).length > 0
                      ? <span style={{ color: "#059669", marginLeft: 8 }}>rates stored</span>
                      : <span style={{ color: "#DC2626", marginLeft: 8 }}>no rates stored</span>}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Remittance data status */}
          <div style={{ marginBottom: 16, fontSize: 12 }}>
            <span style={{ fontWeight: 600, color: NAVY }}>835 Remittance: </span>
            {(audit.remittance_data || []).length > 0 ? (
              <span style={{ color: "#059669" }}>
                {audit.remittance_data.length} file(s) stored
                ({audit.remittance_data.reduce((n, f) => n + (f.claims || []).reduce((n2, c) => n2 + (c.lines || []).length, 0), 0)} lines)
              </span>
            ) : (
              <span style={{ color: "#DC2626" }}>No 835 data stored — upload below</span>
            )}
          </div>

          {/* Backfill panel — upload 835 and configure analysis */}
          {showBackfill && (
            <div style={{
              padding: 16, borderRadius: 8, background: "#FEFCE8",
              border: "1px solid #FDE68A", marginBottom: 16,
            }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#92400E", marginBottom: 12 }}>
                Backfill Data for Analysis
              </div>

              {/* Upload 835 */}
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: NAVY, marginBottom: 4 }}>
                  Upload 835 File
                </label>
                <input
                  type="file"
                  accept=".835,.edi,.txt"
                  disabled={uploading835}
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    setUploading835(true);
                    try {
                      const formData = new FormData();
                      formData.append("file", f);
                      formData.append("audit_id", audit.id);
                      // Auto-assign payer from first payer in list
                      const firstPayer = payers[0]?.payer_name || "";
                      formData.append("payer_name", firstPayer);
                      const res = await fetch(`${API_BASE}/api/provider/admin/audits/upload-835?audit_id=${audit.id}&payer_name=${encodeURIComponent(firstPayer)}`, {
                        method: "POST",
                        headers: authHeaders,
                        body: formData,
                      });
                      if (!res.ok) {
                        const data = await res.json().catch(() => ({}));
                        alert(data.detail || "Upload failed");
                        return;
                      }
                      const result = await res.json();
                      alert(`835 uploaded: ${result.claims_parsed} claims, ${result.total_lines} lines parsed.`);
                      onRefresh();
                    } catch (err) {
                      alert(err.message);
                    } finally {
                      setUploading835(false);
                    }
                  }}
                  style={{ fontSize: 13 }}
                />
                {uploading835 && <div style={{ fontSize: 12, color: TEAL, marginTop: 4 }}>Uploading and parsing...</div>}
              </div>

              {/* ZIP + Percentage for medicare-pct fallback */}
              {payers.some(p => (p.fee_schedule_method || p.method) === "medicare-pct" && !p.fee_schedule_data) && (
                <div style={{ marginBottom: 12 }}>
                  <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: NAVY, marginBottom: 4 }}>
                    Medicare Percentage Settings (for rate regeneration)
                  </label>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input
                      value={backfillZip}
                      onChange={e => setBackfillZip(e.target.value)}
                      placeholder="ZIP code"
                      style={{
                        padding: "6px 10px", borderRadius: 6, border: "1px solid #CBD5E1",
                        fontSize: 13, width: 100,
                      }}
                    />
                    <input
                      value={backfillPct}
                      onChange={e => setBackfillPct(e.target.value)}
                      placeholder="% of Medicare"
                      style={{
                        padding: "6px 10px", borderRadius: 6, border: "1px solid #CBD5E1",
                        fontSize: 13, width: 120,
                      }}
                    />
                    <span style={{ fontSize: 12, color: SLATE, alignSelf: "center" }}>% of Medicare</span>
                  </div>
                </div>
              )}

              <button
                onClick={() => setShowBackfill(false)}
                style={{
                  padding: "6px 14px", borderRadius: 6, border: `1px solid ${SLATE}`,
                  background: "none", color: SLATE, fontSize: 12, cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
          )}

          {/* Admin notes */}
          {audit.admin_notes && !showNotes && (
            <div style={{
              padding: 12, borderRadius: 8, background: "#EFF6FF",
              border: "1px solid #BFDBFE", marginBottom: 16,
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#1E40AF", marginBottom: 4 }}>Review Notes</div>
              <div style={{ fontSize: 13, color: "#1E40AF", whiteSpace: "pre-wrap" }}>{audit.admin_notes}</div>
            </div>
          )}

          {/* Notes editor */}
          {showNotes && (
            <div style={{ marginBottom: 16 }}>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Add review notes (visible in delivery email)..."
                style={{
                  width: "100%", minHeight: 80, padding: 12, borderRadius: 8,
                  border: "1px solid #CBD5E1", fontSize: 13, resize: "vertical",
                  boxSizing: "border-box", fontFamily: "Arial, sans-serif",
                }}
              />
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button
                  onClick={() => adminAction("notes", { audit_id: audit.id, notes })}
                  disabled={loading}
                  style={{
                    padding: "6px 16px", borderRadius: 6, border: "none",
                    background: NAVY, color: "#fff", fontSize: 13, fontWeight: 600,
                    cursor: "pointer", opacity: loading ? 0.6 : 1,
                  }}
                >
                  Save Notes
                </button>
                <button
                  onClick={() => setShowNotes(false)}
                  style={{
                    padding: "6px 16px", borderRadius: 6, border: `1px solid ${SLATE}`,
                    background: "none", color: SLATE, fontSize: 13, cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {audit.status === "submitted" && (
              <ActionButton
                label="Mark Processing"
                loading={loading}
                color="#4F46E5"
                onClick={() => adminAction("status", { audit_id: audit.id, status: "processing" })}
              />
            )}

            {audit.status === "processing" && (
              <ActionButton
                label="Mark Ready for Review"
                loading={loading}
                color="#D97706"
                onClick={() => adminAction("status", { audit_id: audit.id, status: "review" })}
              />
            )}

            {/* Backfill Data — for pre-fix audits missing 835 or fee schedule data */}
            <ActionButton
              label={showBackfill ? "Hide Backfill" : "Backfill Data"}
              loading={false}
              color="#D97706"
              outline
              onClick={() => setShowBackfill(!showBackfill)}
            />

            {/* Run Analysis — available when audit has data to analyze */}
            <ActionButton
              label={analysisRunning ? "Running Analysis..." : "Run Analysis"}
              loading={analysisRunning}
              color="#7C3AED"
              onClick={async () => {
                if (!confirm("Run the full analysis pipeline (contract integrity + denial intelligence) for this audit? This may take 1-2 minutes.")) return;
                setAnalysisRunning(true);
                try {
                  const payload = { audit_id: audit.id };
                  if (backfillZip) payload.zip_code = backfillZip;
                  if (backfillPct) payload.percentage = parseFloat(backfillPct) || 120;
                  const res = await fetch(`${API_BASE}/api/provider/admin/audits/run-analysis`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", ...authHeaders },
                    body: JSON.stringify(payload),
                  });
                  if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    alert(data.detail || "Analysis failed");
                    return;
                  }
                  const result = await res.json();
                  alert(`Analysis complete! ${result.payer_count || 0} payer(s) analyzed, ${result.analysis_ids?.length || 0} result(s) stored.`);
                  onRefresh();
                } catch (err) {
                  alert(err.message);
                } finally {
                  setAnalysisRunning(false);
                }
              }}
            />

            {/* View Results — fetch and display analysis results */}
            {(audit.analysis_ids?.length > 0 || viewResults) && (
              <ActionButton
                label={viewResults ? "Hide Results" : "View Results"}
                loading={false}
                color="#2563EB"
                onClick={async () => {
                  if (viewResults) {
                    setViewResults(null);
                    return;
                  }
                  try {
                    const res = await fetch(
                      `${API_BASE}/api/provider/admin/audits/results?audit_id=${audit.id}`,
                      { headers: authHeaders }
                    );
                    if (!res.ok) throw new Error("Failed to load results");
                    const data = await res.json();
                    setViewResults(data.payer_results || []);
                  } catch (err) {
                    alert(err.message);
                  }
                }}
              />
            )}

            {!showNotes && (
              <ActionButton
                label={audit.admin_notes ? "Edit Notes" : "Add Notes"}
                loading={false}
                color={NAVY}
                outline
                onClick={() => setShowNotes(true)}
              />
            )}

            {audit.status === "review" && (
              <ActionButton
                label="Deliver Report"
                loading={loading}
                color="#059669"
                onClick={() => {
                  if (confirm(`Deliver audit report to ${audit.contact_email}?`)) {
                    adminAction("deliver", { audit_id: audit.id });
                  }
                }}
              />
            )}

            {audit.status === "delivered" && !audit.follow_up_sent && (
              <ActionButton
                label="Send Follow-up"
                loading={loading}
                color={TEAL}
                onClick={() => {
                  if (confirm(`Send follow-up email to ${audit.contact_email}?`)) {
                    adminAction("follow-up", { audit_id: audit.id });
                  }
                }}
              />
            )}

            <ActionButton
              label="Generate PDF"
              loading={loading}
              color={TEAL}
              outline
              onClick={async () => {
                try {
                  const res = await fetch(`${API_BASE}/api/provider/audit-report`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ audit_id: audit.id }),
                  });
                  if (!res.ok) throw new Error("PDF generation failed");
                  const blob = await res.blob();
                  const url = URL.createObjectURL(blob);
                  window.open(url, "_blank");
                } catch (err) {
                  alert(err.message);
                }
              }}
            />
          </div>

          {/* Analysis Results Panel */}
          {viewResults && (
            <div style={{ marginTop: 16, borderTop: "1px solid #E2E8F0", paddingTop: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: NAVY, marginBottom: 12 }}>
                Analysis Results ({viewResults.length} payer{viewResults.length !== 1 ? "s" : ""})
              </div>

              {viewResults.length === 0 && (
                <div style={{ fontSize: 13, color: SLATE, padding: 12, background: "#F8FAFC", borderRadius: 8 }}>
                  No analysis results found. Click "Run Analysis" to execute the pipeline.
                </div>
              )}

              {viewResults.map((pr, pi) => (
                <div key={pi} style={{
                  border: "1px solid #E2E8F0", borderRadius: 10, marginBottom: 12,
                  overflow: "hidden",
                }}>
                  {/* Payer header */}
                  <div style={{
                    padding: "12px 16px", background: "#F0FDFA",
                    borderBottom: "1px solid #E2E8F0",
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                  }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>
                      {pr.payer_name || `Payer ${pi + 1}`}
                    </span>
                    <span style={{ fontSize: 12, color: TEAL, fontWeight: 600 }}>
                      {pr.summary?.total_underpaid_amount != null
                        ? `$${Number(pr.summary.total_underpaid_amount).toLocaleString("en-US", { minimumFractionDigits: 2 })} underpaid`
                        : ""}
                    </span>
                  </div>

                  {/* Summary stats */}
                  {pr.summary && (
                    <div style={{
                      display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
                      gap: 1, background: "#E2E8F0",
                    }}>
                      {[
                        { label: "Total Claims", value: pr.summary.total_lines || pr.summary.total_claims || 0 },
                        { label: "Underpaid", value: pr.summary.underpaid_count || 0, color: "#DC2626" },
                        { label: "Denied", value: pr.summary.denied_count || 0, color: "#D97706" },
                        { label: "Correct", value: pr.summary.correct_count || 0, color: "#059669" },
                      ].map((s, si) => (
                        <div key={si} style={{
                          padding: "10px 12px", background: "#fff", textAlign: "center",
                        }}>
                          <div style={{ fontSize: 20, fontWeight: 700, color: s.color || NAVY }}>{s.value}</div>
                          <div style={{ fontSize: 10, color: SLATE, textTransform: "uppercase", letterSpacing: 0.5 }}>{s.label}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Flagged line items (underpaid + denied) */}
                  {pr.line_items?.filter(li => li.flag === "UNDERPAID" || li.flag === "DENIED").length > 0 && (
                    <div style={{ padding: 16 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: NAVY, marginBottom: 8 }}>
                        Flagged Items ({pr.line_items.filter(li => li.flag === "UNDERPAID" || li.flag === "DENIED").length})
                      </div>
                      <div style={{ overflowX: "auto" }}>
                        <table style={{
                          width: "100%", fontSize: 12, borderCollapse: "collapse",
                        }}>
                          <thead>
                            <tr style={{ borderBottom: "2px solid #E2E8F0" }}>
                              {["CPT", "Description", "Billed", "Paid", "Expected", "Diff", "Flag"].map(h => (
                                <th key={h} style={{
                                  padding: "6px 8px", textAlign: "left", fontWeight: 600,
                                  color: SLATE, fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5,
                                }}>{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {pr.line_items
                              .filter(li => li.flag === "UNDERPAID" || li.flag === "DENIED")
                              .slice(0, 20)
                              .map((li, li_i) => (
                                <tr key={li_i} style={{
                                  borderBottom: "1px solid #F1F5F9",
                                  background: li.flag === "DENIED" ? "#FFFBEB" : li.flag === "UNDERPAID" ? "#FEF2F2" : "#fff",
                                }}>
                                  <td style={{ padding: "6px 8px", fontFamily: "monospace", fontWeight: 600 }}>{li.cpt_code}</td>
                                  <td style={{ padding: "6px 8px", color: SLATE, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{li.description || "—"}</td>
                                  <td style={{ padding: "6px 8px" }}>${Number(li.billed_amount || 0).toFixed(2)}</td>
                                  <td style={{ padding: "6px 8px" }}>${Number(li.paid_amount || 0).toFixed(2)}</td>
                                  <td style={{ padding: "6px 8px" }}>${Number(li.expected_rate || 0).toFixed(2)}</td>
                                  <td style={{ padding: "6px 8px", fontWeight: 600, color: "#DC2626" }}>
                                    ${Number(li.difference || 0).toFixed(2)}
                                  </td>
                                  <td style={{ padding: "6px 8px" }}>
                                    <span style={{
                                      fontSize: 10, fontWeight: 600, padding: "2px 6px", borderRadius: 4,
                                      background: li.flag === "DENIED" ? "#FDE68A" : "#FECACA",
                                      color: li.flag === "DENIED" ? "#92400E" : "#991B1B",
                                    }}>
                                      {li.flag}
                                    </span>
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                        {pr.line_items.filter(li => li.flag === "UNDERPAID" || li.flag === "DENIED").length > 20 && (
                          <div style={{ fontSize: 12, color: SLATE, padding: "8px 0" }}>
                            + {pr.line_items.filter(li => li.flag === "UNDERPAID" || li.flag === "DENIED").length - 20} more flagged items
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Denial intel summary */}
                  {pr.denial_intel && (
                    <div style={{
                      padding: "12px 16px", borderTop: "1px solid #E2E8F0",
                      background: "#FFFBEB",
                    }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: "#92400E", marginBottom: 4 }}>
                        Denial Intelligence
                      </div>
                      <div style={{ fontSize: 12, color: "#78350F", whiteSpace: "pre-wrap" }}>
                        {typeof pr.denial_intel === "string"
                          ? pr.denial_intel
                          : pr.denial_intel?.summary || pr.denial_intel?.top_denial_codes?.map(d =>
                              `${d.code}: ${d.description} (${d.count} claims, $${d.total_amount})`
                            ).join("\n") || "No denial data"}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ActionButton({ label, loading, color, outline, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        padding: "7px 16px", borderRadius: 6, fontSize: 12, fontWeight: 600,
        cursor: loading ? "wait" : "pointer",
        border: outline ? `1px solid ${color}` : "none",
        background: outline ? "none" : color,
        color: outline ? color : "#fff",
        opacity: loading ? 0.6 : 1,
        transition: "opacity 0.15s",
      }}
    >
      {label}
    </button>
  );
}

export default function ProviderAuditAdmin({ session }) {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [searchParams] = useSearchParams();

  const secret = searchParams.get("secret");
  const token = session?.access_token;

  const authHeaders = token
    ? { Authorization: `Bearer ${token}` }
    : secret
    ? { "X-Cron-Secret": secret }
    : null;

  function fetchAudits() {
    const headers = token
      ? { Authorization: `Bearer ${token}` }
      : secret
      ? { "X-Cron-Secret": secret }
      : null;

    if (!headers) return;
    setLoading(true);
    setError(null);

    const url = filterStatus
      ? `${API_BASE}/api/provider/admin/audits?status=${filterStatus}`
      : `${API_BASE}/api/provider/admin/audits`;

    fetch(url, { headers })
      .then(r => {
        if (r.status === 401) throw new Error("Unauthorized — admin access required");
        if (!r.ok) throw new Error("Failed to load audits");
        return r.json();
      })
      .then(data => {
        setAudits(data.audits || []);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }

  useEffect(() => {
    fetchAudits();
  }, [token, secret, filterStatus]);

  if (!authHeaders) {
    return (
      <div style={{
        maxWidth: 600, margin: "120px auto", textAlign: "center",
        fontFamily: "'DM Sans', Arial, sans-serif",
      }}>
        <p style={{ color: SLATE, fontSize: 14 }}>
          Sign in or provide <code>?secret=</code> to access the admin dashboard.
        </p>
      </div>
    );
  }

  if (error === "Unauthorized — admin access required") {
    return (
      <div style={{
        maxWidth: 600, margin: "120px auto", textAlign: "center",
        fontFamily: "'DM Sans', Arial, sans-serif",
      }}>
        <p style={{ color: "#DC2626", fontSize: 14 }}>You do not have admin access.</p>
      </div>
    );
  }

  // Count by status
  const statusCounts = {};
  for (const a of audits) {
    statusCounts[a.status] = (statusCounts[a.status] || 0) + 1;
  }

  return (
    <div style={{
      maxWidth: 1000, margin: "0 auto", padding: "32px 24px",
      fontFamily: "'DM Sans', Arial, sans-serif",
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: NAVY, margin: 0 }}>Parity Audit Admin</h1>
          <p style={{ fontSize: 12, color: SLATE, marginTop: 4 }}>Manage submitted audits</p>
        </div>
        <button
          onClick={fetchAudits}
          style={{
            padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600,
            border: `1px solid #CBD5E1`, background: "#fff", color: NAVY,
            cursor: "pointer",
          }}
        >
          Refresh
        </button>
      </div>

      {/* Status filter tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        {[
          { key: "", label: "All" },
          { key: "submitted", label: "Submitted" },
          { key: "processing", label: "Processing" },
          { key: "review", label: "Review" },
          { key: "delivered", label: "Delivered" },
        ].map(tab => {
          const count = tab.key ? (statusCounts[tab.key] || 0) : audits.length;
          const active = filterStatus === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setFilterStatus(tab.key)}
              style={{
                padding: "6px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                border: active ? `1px solid ${NAVY}` : "1px solid #CBD5E1",
                background: active ? NAVY : "#fff",
                color: active ? "#fff" : SLATE,
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {tab.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Table header */}
      <div style={{
        display: "grid", gridTemplateColumns: "2fr 1fr 1fr 100px 100px",
        gap: 12, padding: "10px 20px", marginBottom: 4,
        fontSize: 11, fontWeight: 600, color: SLATE,
        textTransform: "uppercase", letterSpacing: 1,
      }}>
        <div>Practice</div>
        <div>Payers</div>
        <div>Contact</div>
        <div>Status</div>
        <div>Submitted</div>
      </div>

      {/* Audit list */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 48 }}>
          <div style={{
            width: 40, height: 40, border: "3px solid #E2E8F0",
            borderTopColor: TEAL, borderRadius: "50%",
            margin: "0 auto", animation: "spin 0.8s linear infinite",
          }}>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          </div>
          <p style={{ color: SLATE, marginTop: 12, fontSize: 14 }}>Loading audits...</p>
        </div>
      ) : error ? (
        <div style={{
          textAlign: "center", padding: 48, color: "#DC2626", fontSize: 14,
        }}>
          {error}
        </div>
      ) : audits.length === 0 ? (
        <div style={{
          textAlign: "center", padding: 48, color: SLATE, fontSize: 14,
          border: "1px solid #E2E8F0", borderRadius: 12,
        }}>
          {filterStatus
            ? `No audits with status "${filterStatus}"`
            : "No audits submitted yet"}
        </div>
      ) : (
        audits.map(audit => (
          <AuditRow
            key={audit.id}
            audit={audit}
            authHeaders={authHeaders}
            onRefresh={fetchAudits}
          />
        ))
      )}

      {/* Footer */}
      <div style={{
        borderTop: "1px solid #E2E8F0", marginTop: 32, paddingTop: 16,
        fontSize: 12, color: SLATE, textAlign: "center",
      }}>
        Parity Audit Admin &middot; CivicScale
      </div>
    </div>
  );
}
