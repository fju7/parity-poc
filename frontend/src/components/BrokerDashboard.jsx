import { useState, useEffect, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { LogoIcon } from "./CivicScaleHomepage.jsx";
import "./CivicScaleHomepage.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function BrokerDashboard() {
  const navigate = useNavigate();
  const [broker, setBroker] = useState(null);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientSummary, setClientSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // Add client form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState("");
  const [addSuccess, setAddSuccess] = useState("");

  // Auth check
  useEffect(() => {
    const stored = localStorage.getItem("broker_session");
    if (!stored) {
      navigate("/broker/login");
      return;
    }
    try {
      setBroker(JSON.parse(stored));
    } catch {
      localStorage.removeItem("broker_session");
      navigate("/broker/login");
    }
  }, [navigate]);

  // Fetch clients
  const fetchClients = useCallback(async () => {
    if (!broker) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/broker/clients?broker_email=${encodeURIComponent(broker.email)}`);
      if (!res.ok) throw new Error("Failed to load clients");
      const data = await res.json();
      setClients(data.clients || []);
    } catch (err) {
      console.error("Failed to fetch clients:", err);
    }
    setLoading(false);
  }, [broker]);

  useEffect(() => { fetchClients(); }, [fetchClients]);

  // Fetch client summary
  const fetchSummary = useCallback(async (employerEmail) => {
    if (!broker) return;
    setSummaryLoading(true);
    setClientSummary(null);
    try {
      const res = await fetch(
        `${API}/api/broker/clients/${encodeURIComponent(employerEmail)}/summary?broker_email=${encodeURIComponent(broker.email)}`
      );
      if (!res.ok) throw new Error("Failed to load summary");
      const data = await res.json();
      setClientSummary(data);
    } catch (err) {
      console.error("Failed to fetch summary:", err);
    }
    setSummaryLoading(false);
  }, [broker]);

  // Select client
  const handleSelectClient = (client) => {
    setSelectedClient(client);
    fetchSummary(client.employer_email);
  };

  // Add client
  const handleAddClient = async (e) => {
    e.preventDefault();
    setAddLoading(true);
    setAddError("");
    setAddSuccess("");

    try {
      const res = await fetch(`${API}/api/broker/clients/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ broker_email: broker.email, employer_email: addEmail }),
      });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to add client.");
      }

      if (data.added) {
        setAddSuccess("Client added successfully.");
        setAddEmail("");
        setShowAddForm(false);
        fetchClients();
      } else {
        setAddError(data.message || "Client already linked.");
      }
    } catch (err) {
      setAddError(err.message);
    }
    setAddLoading(false);
  };

  // Remove client
  const handleRemoveClient = async (employerEmail) => {
    if (!confirm("Remove this employer from your client list?")) return;

    try {
      const res = await fetch(
        `${API}/api/broker/clients/${encodeURIComponent(employerEmail)}?broker_email=${encodeURIComponent(broker.email)}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        setClients((prev) => prev.filter((c) => c.employer_email !== employerEmail));
        if (selectedClient?.employer_email === employerEmail) {
          setSelectedClient(null);
          setClientSummary(null);
        }
      }
    } catch (err) {
      console.error("Failed to remove client:", err);
    }
  };

  // Logout
  const handleLogout = () => {
    localStorage.removeItem("broker_session");
    navigate("/broker/login");
  };

  const fmt = (n) => n != null ? n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }) : "—";

  if (!broker) return null;

  return (
    <div style={{ margin: 0, padding: 0, fontFamily: "'DM Sans', sans-serif", color: "#2d3748", overflowX: "hidden", minHeight: "100vh", background: "#f8fafc" }}>
      {/* NAV */}
      <nav className="cs-nav">
        <Link className="cs-nav-logo" to="/">
          <LogoIcon />
          <span className="cs-nav-wordmark">CivicScale</span>
        </Link>
        <div className="cs-nav-links">
          <span style={{ fontSize: 14, color: "#64748b" }}>{broker.firm_name}</span>
          <button
            onClick={handleLogout}
            style={{
              background: "none", border: "1px solid #e2e8f0", borderRadius: 6,
              padding: "6px 14px", fontSize: 13, color: "#64748b", cursor: "pointer",
            }}
          >
            Sign Out
          </button>
        </div>
      </nav>

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "88px 24px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
          <div>
            <h1 style={{ fontSize: 28, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>
              Broker Dashboard
            </h1>
            <p style={{ color: "#64748b", fontSize: 15, marginTop: 4 }}>
              {broker.contact_name ? `${broker.contact_name} · ` : ""}{broker.firm_name}
            </p>
          </div>
          <button
            onClick={() => { setShowAddForm(true); setAddError(""); setAddSuccess(""); }}
            style={{
              background: "#0D7377", color: "#fff", border: "none", borderRadius: 8,
              padding: "10px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer",
            }}
          >
            + Add Client
          </button>
        </div>

        {/* Add Client Form */}
        {showAddForm && (
          <div style={{
            background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
            padding: 24, marginBottom: 24,
          }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>
              Link an Employer Client
            </h3>
            <form onSubmit={handleAddClient} style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "#475569", marginBottom: 4 }}>
                  Employer email
                </label>
                <input
                  type="email"
                  required
                  value={addEmail}
                  onChange={(e) => setAddEmail(e.target.value)}
                  placeholder="hr@employer.com"
                  style={{
                    width: "100%", padding: "8px 12px", borderRadius: 8,
                    border: "1px solid #e2e8f0", fontSize: 14, outline: "none", boxSizing: "border-box",
                  }}
                />
              </div>
              <button
                type="submit"
                disabled={addLoading}
                style={{
                  background: "#1B3A5C", color: "#fff", border: "none", borderRadius: 8,
                  padding: "8px 20px", fontSize: 14, fontWeight: 600, cursor: "pointer",
                  opacity: addLoading ? 0.6 : 1,
                }}
              >
                {addLoading ? "Adding..." : "Add"}
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                style={{
                  background: "none", border: "1px solid #e2e8f0", borderRadius: 8,
                  padding: "8px 16px", fontSize: 14, color: "#64748b", cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </form>
            {addError && (
              <p style={{ color: "#991b1b", fontSize: 13, marginTop: 8 }}>{addError}</p>
            )}
            {addSuccess && (
              <p style={{ color: "#0D7377", fontSize: 13, marginTop: 8 }}>{addSuccess}</p>
            )}
          </div>
        )}

        {/* Main Layout: Client List + Detail Panel */}
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          {/* Client List */}
          <div style={{ width: 380, flexShrink: 0 }}>
            <div style={{
              background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
              overflow: "hidden",
            }}>
              <div style={{
                padding: "16px 20px", borderBottom: "1px solid #e2e8f0",
                fontSize: 14, fontWeight: 600, color: "#1B3A5C",
              }}>
                Employer Clients ({clients.length})
              </div>

              {loading ? (
                <div style={{ padding: 32, textAlign: "center", color: "#94a3b8" }}>
                  Loading clients...
                </div>
              ) : clients.length === 0 ? (
                <div style={{ padding: 32, textAlign: "center", color: "#94a3b8", fontSize: 14 }}>
                  No clients linked yet. Click "Add Client" to get started.
                </div>
              ) : (
                clients.map((client) => {
                  const isSelected = selectedClient?.employer_email === client.employer_email;
                  return (
                    <div
                      key={client.employer_email}
                      onClick={() => handleSelectClient(client)}
                      style={{
                        padding: "14px 20px", borderBottom: "1px solid #f1f5f9",
                        cursor: "pointer", transition: "background 0.15s",
                        background: isSelected ? "#f0fdfa" : "#fff",
                        borderLeft: isSelected ? "3px solid #0D7377" : "3px solid transparent",
                      }}
                      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = "#f8fafc"; }}
                      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "#fff"; }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div>
                          <p style={{ margin: 0, fontWeight: 600, fontSize: 14, color: "#1B3A5C" }}>
                            {client.company_name}
                          </p>
                          <p style={{ margin: "2px 0 0", fontSize: 12, color: "#94a3b8" }}>
                            {client.employer_email}
                          </p>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <span style={{
                            display: "inline-block", padding: "2px 8px", borderRadius: 12,
                            fontSize: 11, fontWeight: 600,
                            background: client.subscription_status === "active" ? "#dcfce7" : "#f1f5f9",
                            color: client.subscription_status === "active" ? "#166534" : "#64748b",
                          }}>
                            {client.tier || "free"}
                          </span>
                          <p style={{ margin: "4px 0 0", fontSize: 11, color: "#94a3b8" }}>
                            {client.claims_uploads} upload{client.claims_uploads !== 1 ? "s" : ""}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Detail Panel */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {!selectedClient ? (
              <div style={{
                background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
                padding: 48, textAlign: "center", color: "#94a3b8",
              }}>
                <p style={{ fontSize: 16, margin: "0 0 8px" }}>Select a client to view details</p>
                <p style={{ fontSize: 13 }}>Click on an employer from the list to see their claims summary and analytics.</p>
              </div>
            ) : summaryLoading ? (
              <div style={{
                background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
                padding: 48, textAlign: "center",
              }}>
                <div style={{
                  width: 36, height: 36, border: "3px solid #e2e8f0", borderTopColor: "#0D7377",
                  borderRadius: "50%", animation: "cs-spin 0.8s linear infinite",
                  margin: "0 auto 16px",
                }} />
                <p style={{ color: "#64748b", fontSize: 14 }}>Loading summary...</p>
                <style>{`@keyframes cs-spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            ) : clientSummary ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {/* Client Header */}
                <div style={{
                  background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
                  padding: 24, display: "flex", justifyContent: "space-between", alignItems: "center",
                }}>
                  <div>
                    <h2 style={{ fontSize: 22, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>
                      {clientSummary.company_name}
                    </h2>
                    <p style={{ fontSize: 13, color: "#94a3b8", marginTop: 4 }}>{clientSummary.employer_email}</p>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span style={{
                      padding: "4px 12px", borderRadius: 16, fontSize: 12, fontWeight: 600,
                      background: clientSummary.subscription.status === "active" ? "#dcfce7" : "#f1f5f9",
                      color: clientSummary.subscription.status === "active" ? "#166534" : "#64748b",
                    }}>
                      {clientSummary.subscription.tier} · {clientSummary.subscription.status}
                    </span>
                    <button
                      onClick={() => handleRemoveClient(clientSummary.employer_email)}
                      style={{
                        background: "none", border: "1px solid #fecaca", borderRadius: 6,
                        padding: "4px 10px", fontSize: 11, color: "#991b1b", cursor: "pointer",
                      }}
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {/* Claims Summary Cards */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
                  {[
                    { label: "Total Uploads", value: clientSummary.claims_summary.total_uploads },
                    { label: "Total Claims", value: clientSummary.claims_summary.total_claims.toLocaleString() },
                    { label: "Total Paid", value: fmt(clientSummary.claims_summary.total_paid) },
                    { label: "Excess > 2x", value: fmt(clientSummary.claims_summary.total_excess_2x), color: clientSummary.claims_summary.total_excess_2x > 0 ? "#EF4444" : "#1B3A5C" },
                  ].map((card) => (
                    <div key={card.label} style={{
                      background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
                      padding: 20, textAlign: "center",
                    }}>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 8px", fontWeight: 500 }}>
                        {card.label}
                      </p>
                      <p style={{
                        fontSize: 22, fontWeight: 700, margin: 0,
                        color: card.color || "#1B3A5C",
                      }}>
                        {card.value}
                      </p>
                    </div>
                  ))}
                </div>

                {/* Upload Timeline */}
                {clientSummary.upload_timeline && clientSummary.upload_timeline.length > 0 && (
                  <div style={{
                    background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
                    padding: 24,
                  }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 16px" }}>
                      Claims Upload History
                    </h3>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                      <thead>
                        <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
                          <th style={{ textAlign: "left", padding: "8px 12px", color: "#64748b", fontWeight: 600 }}>Date</th>
                          <th style={{ textAlign: "left", padding: "8px 12px", color: "#64748b", fontWeight: 600 }}>File</th>
                          <th style={{ textAlign: "right", padding: "8px 12px", color: "#64748b", fontWeight: 600 }}>Claims</th>
                          <th style={{ textAlign: "right", padding: "8px 12px", color: "#64748b", fontWeight: 600 }}>Total Paid</th>
                          <th style={{ textAlign: "right", padding: "8px 12px", color: "#64748b", fontWeight: 600 }}>Excess &gt; 2x</th>
                          <th style={{ textAlign: "left", padding: "8px 12px", color: "#64748b", fontWeight: 600 }}>Top CPT</th>
                        </tr>
                      </thead>
                      <tbody>
                        {clientSummary.upload_timeline.map((u) => (
                          <tr key={u.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "10px 12px", color: "#475569" }}>
                              {new Date(u.created_at).toLocaleDateString()}
                            </td>
                            <td style={{ padding: "10px 12px", color: "#475569", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {u.filename || "—"}
                            </td>
                            <td style={{ padding: "10px 12px", textAlign: "right", color: "#475569" }}>
                              {(u.total_claims || 0).toLocaleString()}
                            </td>
                            <td style={{ padding: "10px 12px", textAlign: "right", color: "#475569" }}>
                              {fmt(u.total_paid)}
                            </td>
                            <td style={{ padding: "10px 12px", textAlign: "right", color: u.total_excess_2x > 0 ? "#EF4444" : "#475569", fontWeight: u.total_excess_2x > 0 ? 600 : 400 }}>
                              {fmt(u.total_excess_2x)}
                            </td>
                            <td style={{ padding: "10px 12px", color: "#475569" }}>
                              {u.top_flagged_cpt || "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Trends Summary */}
                {clientSummary.trends && (
                  <div style={{
                    background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
                    padding: 24,
                  }}>
                    <h3 style={{ fontSize: 16, fontWeight: 600, color: "#1B3A5C", margin: "0 0 4px" }}>
                      PEPM Trend Summary
                    </h3>
                    {clientSummary.trends_computed_at && (
                      <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 16px" }}>
                        Computed {new Date(clientSummary.trends_computed_at).toLocaleDateString()}
                      </p>
                    )}

                    {clientSummary.trends.months && clientSummary.trends.months.length > 0 && (
                      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                        {clientSummary.trends.months.slice(-6).map((m) => (
                          <div key={m.month} style={{
                            padding: "12px 16px", background: "#f8fafc", borderRadius: 8,
                            border: "1px solid #e2e8f0", minWidth: 100, textAlign: "center",
                          }}>
                            <p style={{ fontSize: 11, color: "#94a3b8", margin: "0 0 4px" }}>{m.month}</p>
                            <p style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>
                              ${(m.pepm || 0).toFixed(0)}
                            </p>
                            <p style={{ fontSize: 11, color: "#64748b", margin: "2px 0 0" }}>
                              PEPM
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    {clientSummary.trends.narrative && (
                      <div style={{
                        marginTop: 16, padding: 16, background: "#f0fdfa", borderRadius: 8,
                        border: "1px solid #99f6e4", fontSize: 13, color: "#1B3A5C", lineHeight: 1.6,
                      }}>
                        {clientSummary.trends.narrative}
                      </div>
                    )}
                  </div>
                )}

                {/* Subscription Info */}
                {clientSummary.subscription.employee_count && (
                  <div style={{
                    background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
                    padding: 20, display: "flex", gap: 32,
                  }}>
                    <div>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 4px" }}>Employee Count</p>
                      <p style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>
                        {clientSummary.subscription.employee_count.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 4px" }}>Subscription Tier</p>
                      <p style={{ fontSize: 18, fontWeight: 700, color: "#1B3A5C", margin: 0 }}>
                        {clientSummary.subscription.tier}
                      </p>
                    </div>
                    <div>
                      <p style={{ fontSize: 12, color: "#94a3b8", margin: "0 0 4px" }}>Status</p>
                      <p style={{
                        fontSize: 18, fontWeight: 700, margin: 0,
                        color: clientSummary.subscription.status === "active" ? "#0D7377" : "#64748b",
                      }}>
                        {clientSummary.subscription.status}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
