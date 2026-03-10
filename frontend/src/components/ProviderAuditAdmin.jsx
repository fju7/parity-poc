import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import ProviderAuditReport from "./ProviderAuditReport";
import { useAuth } from "../context/AuthContext";

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
  const [analysisStatus, setAnalysisStatus] = useState(null); // null | "running" | {success message}
  const fileInputRef = useRef(null);

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
                <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: NAVY, marginBottom: 8 }}>
                  Upload 835 File
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".835,.edi,.txt"
                  disabled={uploading835}
                  style={{ display: "none" }}
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (!f) return;
                    setUploading835(true);
                    try {
                      const formData = new FormData();
                      formData.append("file", f);
                      const firstPayer = payers[0]?.payer_name || "";
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
                      if (fileInputRef.current) fileInputRef.current.value = "";
                    }
                  }}
                />
                <div
                  onClick={() => !uploading835 && fileInputRef.current?.click()}
                  onDragOver={e => { e.preventDefault(); e.stopPropagation(); }}
                  onDrop={async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const f = e.dataTransfer.files?.[0];
                    if (!f || uploading835) return;
                    // Trigger same upload flow
                    const dt = new DataTransfer();
                    dt.items.add(f);
                    if (fileInputRef.current) {
                      fileInputRef.current.files = dt.files;
                      fileInputRef.current.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                  }}
                  style={{
                    border: `2px dashed ${uploading835 ? "#CBD5E1" : TEAL}`,
                    borderRadius: 8, padding: "20px 16px", textAlign: "center",
                    cursor: uploading835 ? "wait" : "pointer",
                    background: uploading835 ? "#F8FAFC" : "#F0FDFA",
                    transition: "border-color 0.15s, background 0.15s",
                  }}
                >
                  {uploading835 ? (
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                      <div style={{
                        width: 16, height: 16, border: "2px solid #CBD5E1",
                        borderTopColor: TEAL, borderRadius: "50%",
                        animation: "spin 0.8s linear infinite",
                      }} />
                      <span style={{ fontSize: 13, color: TEAL, fontWeight: 600 }}>Uploading and parsing...</span>
                    </div>
                  ) : (
                    <>
                      <div style={{ fontSize: 13, fontWeight: 600, color: TEAL, marginBottom: 4 }}>
                        Choose 835 File or Drag & Drop
                      </div>
                      <div style={{ fontSize: 11, color: SLATE }}>
                        Accepts .835, .edi, .txt files
                      </div>
                    </>
                  )}
                </div>
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
            {analysisRunning ? (
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "7px 16px", borderRadius: 6, background: "#7C3AED",
                opacity: 0.85,
              }}>
                <div style={{
                  width: 14, height: 14, border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "#fff", borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: "#fff" }}>
                  Analyzing... this may take 1-2 minutes
                </span>
              </div>
            ) : (
              <ActionButton
                label="Run Analysis"
                loading={false}
                color="#7C3AED"
                onClick={async () => {
                  if (!confirm("Run the full analysis pipeline (contract integrity + denial intelligence) for this audit? This may take 1-2 minutes.")) return;
                  setAnalysisRunning(true);
                  setAnalysisStatus(null);
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
                      setAnalysisStatus(`Error: ${data.detail || "Analysis failed"}`);
                      return;
                    }
                    const result = await res.json();
                    // Build detailed summary
                    const pr = result.payer_results || [];
                    const totalLines = pr.reduce((n, p) => n + (p.line_count || 0), 0);
                    const totalUnderpaid = pr.reduce((n, p) => n + (p.summary?.underpaid_count || 0), 0);
                    const totalDenied = pr.reduce((n, p) => n + (p.summary?.denied_count || 0), 0);
                    const totalAmount = pr.reduce((n, p) => n + (p.underpayment || 0), 0);
                    setAnalysisStatus(
                      `Analysis complete: ${totalLines} line items analyzed, ` +
                      `${totalUnderpaid} underpayment${totalUnderpaid !== 1 ? "s" : ""} found` +
                      (totalAmount > 0 ? ` ($${totalAmount.toFixed(2)})` : "") +
                      `, ${totalDenied} denial${totalDenied !== 1 ? "s" : ""} identified.`
                    );
                    onRefresh();
                  } catch (err) {
                    setAnalysisStatus(`Error: ${err.message}`);
                  } finally {
                    setAnalysisRunning(false);
                  }
                }}
              />
            )}

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

            {audit.status === "delivered" && (
              <ActionButton
                label="Convert to Subscription"
                loading={loading}
                color="#7C3AED"
                onClick={() => {
                  if (confirm(`Convert ${audit.practice_name} to a monitoring subscription?`)) {
                    adminAction("convert-subscription", { audit_id: audit.id });
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

            {/* Archive / Unarchive */}
            {audit.archived ? (
              <ActionButton
                label="Unarchive"
                loading={loading}
                color="#6B7280"
                outline
                onClick={() => adminAction("archive", { audit_id: audit.id, archived: false })}
              />
            ) : (
              <ActionButton
                label="Archive"
                loading={loading}
                color="#6B7280"
                outline
                onClick={() => {
                  if (confirm("Archive this audit? It will be hidden from the default view.")) {
                    adminAction("archive", { audit_id: audit.id, archived: true });
                  }
                }}
              />
            )}

            {/* Delete — only on archived audits */}
            {audit.archived && (
              <ActionButton
                label="Delete"
                loading={loading}
                color="#DC2626"
                onClick={() => {
                  if (confirm("Permanently delete this audit and all associated data? This cannot be undone.")) {
                    adminAction("delete", { audit_id: audit.id });
                  }
                }}
              />
            )}
          </div>

          {/* Analysis status message */}
          {analysisStatus && (
            <div style={{
              marginTop: 12, padding: "10px 16px", borderRadius: 8, fontSize: 13,
              background: analysisStatus.startsWith("Error") ? "#FEF2F2" : "#ECFDF5",
              color: analysisStatus.startsWith("Error") ? "#DC2626" : "#059669",
              border: `1px solid ${analysisStatus.startsWith("Error") ? "#FECACA" : "#A7F3D0"}`,
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <span>{analysisStatus}</span>
              <button
                onClick={() => setAnalysisStatus(null)}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  fontSize: 16, color: SLATE, padding: "0 4px",
                }}
              >
                &times;
              </button>
            </div>
          )}

          {/* Analysis Results — reuse full ProviderAuditReport component */}
          {viewResults && (
            <div style={{ marginTop: 16, borderTop: "2px solid #E2E8F0", paddingTop: 16 }}>
              {viewResults.length === 0 ? (
                <div style={{ fontSize: 13, color: SLATE, padding: 12, background: "#F8FAFC", borderRadius: 8 }}>
                  No analysis results found. Click "Run Analysis" to execute the pipeline.
                </div>
              ) : (
                <ProviderAuditReport
                  analysisResults={viewResults}
                  practiceInfo={{ practice_name: audit.practice_name }}
                  onClose={() => setViewResults(null)}
                />
              )}
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

function SubscriptionRow({ sub }) {
  const months = sub.monthly_analyses || [];
  const createdAt = sub.created_at
    ? new Date(sub.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "—";
  const statusColor = sub.status === "active"
    ? { bg: "#ECFDF5", text: "#059669", border: "#A7F3D0" }
    : sub.status === "past_due"
    ? { bg: "#FEF2F2", text: "#DC2626", border: "#FECACA" }
    : { bg: "#F3F4F6", text: "#6B7280", border: "#D1D5DB" };

  return (
    <div style={{
      border: "1px solid #E2E8F0", borderRadius: 12, marginBottom: 12,
      background: "#fff", padding: "16px 20px",
    }}>
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr", gap: 12, alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: NAVY }}>{sub.practice_name}</div>
          <div style={{ fontSize: 12, color: SLATE }}>{sub.contact_email}</div>
        </div>
        <div>
          <span style={{
            display: "inline-block", fontSize: 11, fontWeight: 600,
            padding: "3px 10px", borderRadius: 20,
            background: statusColor.bg, color: statusColor.text, border: `1px solid ${statusColor.border}`,
          }}>
            {sub.status}
          </span>
        </div>
        <div style={{ fontSize: 13, color: SLATE }}>
          {months.length} month{months.length !== 1 ? "s" : ""}
        </div>
        <div style={{ fontSize: 13, color: SLATE }}>{createdAt}</div>
      </div>
      {months.length > 0 && (
        <div style={{ marginTop: 12, borderTop: "1px solid #F1F5F9", paddingTop: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: SLATE, marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>
            Monthly Analyses
          </div>
          {months.map((m, i) => (
            <div key={i} style={{ fontSize: 13, color: NAVY, padding: "3px 0" }}>
              {m.label || m.month} — {m.claims_count != null ? `${m.claims_count} claims` : (m.analysis_ids?.length ? `${m.analysis_ids.length} analyses` : "baseline")}
              <span style={{ color: SLATE, marginLeft: 8 }}>
                {m.added_at ? new Date(m.added_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ProviderAuditAdmin() {
  const { token } = useAuth();
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [activeTab, setActiveTab] = useState("audits"); // "audits" | "subscriptions"
  const [subscriptions, setSubscriptions] = useState([]);
  const [subsLoading, setSubsLoading] = useState(false);
  const [searchParams] = useSearchParams();

  const secret = searchParams.get("secret");

  const authHeaders = token
    ? { Authorization: `Bearer ${token}` }
    : secret
    ? { "X-Cron-Secret": secret }
    : null;

  function fetchAudits(silent = false) {
    const headers = token
      ? { Authorization: `Bearer ${token}` }
      : secret
      ? { "X-Cron-Secret": secret }
      : null;

    if (!headers) return;
    if (!silent) setLoading(true);
    setError(null);

    const params = new URLSearchParams();
    if (filterStatus === "archived") {
      params.set("archived", "true");
    } else {
      params.set("archived", "false");
      if (filterStatus) params.set("status", filterStatus);
    }
    const url = `${API_BASE}/api/provider/admin/audits?${params.toString()}`;

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

  function fetchSubscriptions() {
    const headers = authHeaders;
    if (!headers) return;
    setSubsLoading(true);
    fetch(`${API_BASE}/api/provider/admin/subscriptions`, { headers })
      .then(r => {
        if (!r.ok) throw new Error("Failed to load subscriptions");
        return r.json();
      })
      .then(data => {
        setSubscriptions(data.subscriptions || []);
        setSubsLoading(false);
      })
      .catch(() => setSubsLoading(false));
  }

  useEffect(() => {
    if (activeTab === "subscriptions") {
      fetchSubscriptions();
    } else {
      fetchAudits();
    }
  }, [token, secret, filterStatus, activeTab]);

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
          onClick={() => activeTab === "subscriptions" ? fetchSubscriptions() : fetchAudits()}
          style={{
            padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600,
            border: `1px solid #CBD5E1`, background: "#fff", color: NAVY,
            cursor: "pointer",
          }}
        >
          Refresh
        </button>
      </div>

      {/* Main tabs: Audits vs Subscriptions */}
      <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "2px solid #E2E8F0" }}>
        {[
          { key: "audits", label: "Audits" },
          { key: "subscriptions", label: "Subscriptions" },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: "10px 20px", fontSize: 13, fontWeight: 600,
              border: "none", borderBottom: activeTab === tab.key ? "2px solid #7C3AED" : "2px solid transparent",
              background: "none", color: activeTab === tab.key ? "#7C3AED" : SLATE,
              cursor: "pointer", marginBottom: -2,
            }}
          >
            {tab.label}
            {tab.key === "subscriptions" && subscriptions.length > 0 && (
              <span style={{
                marginLeft: 6, fontSize: 11, background: "#EDE9FE", color: "#7C3AED",
                padding: "1px 6px", borderRadius: 10,
              }}>
                {subscriptions.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {activeTab === "subscriptions" ? (
        /* ===== Subscriptions Tab ===== */
        <div>
          <div style={{
            display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr",
            gap: 12, padding: "10px 20px", marginBottom: 4,
            fontSize: 11, fontWeight: 600, color: SLATE,
            textTransform: "uppercase", letterSpacing: 1,
          }}>
            <div>Practice</div>
            <div>Status</div>
            <div>Months</div>
            <div>Created</div>
          </div>
          {subsLoading ? (
            <div style={{ textAlign: "center", padding: 48 }}>
              <div style={{
                width: 40, height: 40, border: "3px solid #E2E8F0",
                borderTopColor: "#7C3AED", borderRadius: "50%",
                margin: "0 auto", animation: "spin 0.8s linear infinite",
              }}>
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              </div>
              <p style={{ color: SLATE, marginTop: 12, fontSize: 14 }}>Loading subscriptions...</p>
            </div>
          ) : subscriptions.length === 0 ? (
            <div style={{
              textAlign: "center", padding: 48, color: SLATE, fontSize: 14,
              border: "1px solid #E2E8F0", borderRadius: 12,
            }}>
              No subscriptions yet. Convert a delivered audit to create one.
            </div>
          ) : (
            subscriptions.map(sub => (
              <SubscriptionRow key={sub.id} sub={sub} />
            ))
          )}
        </div>
      ) : (
        /* ===== Audits Tab ===== */
        <>
      {/* Status filter tabs */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        {[
          { key: "", label: "All" },
          { key: "submitted", label: "Submitted" },
          { key: "processing", label: "Processing" },
          { key: "review", label: "Review" },
          { key: "delivered", label: "Delivered" },
          { key: "archived", label: "Archived" },
        ].map(tab => {
          const count = tab.key && tab.key !== "archived" ? (statusCounts[tab.key] || 0) : audits.length;
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
            onRefresh={() => fetchAudits(true)}
          />
        ))
      )}
        </>
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
