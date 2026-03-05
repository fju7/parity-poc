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
                  </span>
                </div>
              ))}
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
