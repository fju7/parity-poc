import { useState } from "react";
import { useAuth } from "../context/AuthContext";

import { API_BASE } from "../lib/apiBase";
const TEAL = "#0D9488";
const NAVY = "#1E293B";
const LIGHT_TEAL = "#F0FDFA";
const SLATE = "#64748B";
const RED = "#DC2626";
const AMBER = "#D97706";
const GREEN = "#059669";

const sectionStyle = {
  marginBottom: 32,
};

const headingStyle = {
  fontSize: 20,
  fontWeight: 700,
  color: NAVY,
  margin: "0 0 16px",
  paddingBottom: 8,
  borderBottom: `2px solid ${TEAL}`,
};

const bodyStyle = {
  fontSize: 14,
  lineHeight: 1.7,
  color: NAVY,
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
};

const thStyle = {
  padding: "10px 12px",
  textAlign: "left",
  fontWeight: 600,
  fontSize: 12,
  color: "#fff",
  background: NAVY,
  borderBottom: "2px solid #334155",
};

const tdStyle = {
  padding: "8px 12px",
  borderBottom: "1px solid #E2E8F0",
  fontSize: 13,
};

function flagColor(flag) {
  if (flag === "UNDERPAID") return { bg: "#FEF2F2", text: RED };
  if (flag === "DENIED") return { bg: "#FFFBEB", text: AMBER };
  if (flag === "CORRECT") return { bg: "#ECFDF5", text: GREEN };
  if (flag === "BILLED_BELOW") return { bg: "#FFF7ED", text: "#EA580C" };
  if (flag === "OVERPAID") return { bg: "#EFF6FF", text: "#2563EB" };
  return { bg: "#F3F4F6", text: "#6B7280" };
}

export default function ProviderAuditReport({ analysisResults, practiceInfo, onClose, trendData }) {
  const { token } = useAuth();
  const [downloading, setDownloading] = useState(false);
  const [appealModal, setAppealModal] = useState(null); // {loading, letter_html, letter_text, pdf_base64, appeal_strength, appeal_strength_reason, cms_references, editText}
  const [appealGenerating, setAppealGenerating] = useState(null); // key of denial being generated

  const practiceName = practiceInfo?.practice_name || practiceInfo?.name || "Practice";
  const reportDate = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const dateRange = practiceInfo?.date_range || "";

  // Aggregate totals
  const totalUnderpayment = analysisResults.reduce(
    (s, r) => s + (r.result?.summary?.total_underpayment || 0), 0
  );
  const totalDeniedValue = analysisResults.reduce(
    (s, r) => s + (r.denial_intel?.total_recoverable_value || 0), 0
  );
  const totalLineItems = analysisResults.reduce(
    (s, r) => s + (r.result?.summary?.line_count || 0), 0
  );

  async function handleDownloadPdf() {
    setDownloading(true);
    try {
      const payload = {
        analysis_data: {
          practice_name: practiceName,
          report_date: reportDate,
          date_range: dateRange,
          payer_results: analysisResults.map((r) => ({
            payer_name: r.payer_name,
            summary: r.result?.summary || {},
            line_items: r.result?.line_items || [],
            scorecard: r.result?.scorecard || {},
            denial_intel: r.denial_intel || null,
          })),
        },
      };

      const res = await fetch(`${API_BASE}/api/provider/audit-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("PDF generation failed");

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Parity_Audit_${practiceName.replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
      alert("Failed to generate PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  }

  async function handleDraftAppeal(denialType, payerName) {
    const key = `${payerName}-${denialType.adjustment_code}`;
    setAppealGenerating(key);
    try {
      if (!token) { alert("Please log in to generate appeals."); return; }

      const res = await fetch(`${API_BASE}/api/provider/generate-appeal`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          claim_id: denialType.adjustment_code,
          denial_code: denialType.adjustment_code,
          cpt_code: (denialType.affected_cpts || []).join(", "),
          billed_amount: denialType.total_value || 0,
          payer_name: payerName,
          date_of_service: denialType.sample_date_of_service || "",
          practice_name: practiceName,
          practice_address: practiceInfo?.practice_address || "",
          provider_name: practiceInfo?.provider_name || "",
          npi: practiceInfo?.npi || "",
          patient_name: "",
          audit_id: practiceInfo?.audit_id || null,
          subscription_id: practiceInfo?.subscription_id || null,
        }),
      });

      if (!res.ok) throw new Error("Failed to generate appeal");
      const data = await res.json();
      setAppealModal({
        ...data,
        editText: data.letter_text || "",
        payer_name: payerName,
        denial_code: denialType.adjustment_code,
      });
    } catch (err) {
      console.error("Appeal generation error:", err);
      alert("Failed to generate appeal letter. Please try again.");
    } finally {
      setAppealGenerating(null);
    }
  }

  function handleCopyAppeal() {
    if (!appealModal?.editText) return;
    navigator.clipboard.writeText(appealModal.editText).then(() => {
      alert("Appeal letter copied to clipboard.");
    });
  }

  function handleDownloadAppealPdf() {
    if (!appealModal?.pdf_base64) return;
    const byteChars = atob(appealModal.pdf_base64);
    const byteArray = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) byteArray[i] = byteChars.charCodeAt(i);
    const blob = new Blob([byteArray], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Appeal_${appealModal.payer_name}_${appealModal.denial_code}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handlePrintAppeal() {
    if (!appealModal?.editText) return;
    const w = window.open("", "_blank");
    w.document.write(`<html><head><title>Appeal Letter</title><style>body{font-family:Arial,sans-serif;font-size:12px;line-height:1.6;padding:40px;max-width:700px;margin:0 auto;}</style></head><body><pre style="white-space:pre-wrap;font-family:Arial,sans-serif;">${appealModal.editText}</pre></body></html>`);
    w.document.close();
    w.print();
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "32px 24px", fontFamily: "'DM Sans', Arial, sans-serif" }}>
      {/* Appeal Modal */}
      {appealModal && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.5)", zIndex: 1000,
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: 24,
        }} onClick={() => setAppealModal(null)}>
          <div style={{
            background: "#fff", borderRadius: 12, maxWidth: 800, width: "100%",
            maxHeight: "90vh", overflow: "auto", padding: 32,
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 18, color: NAVY }}>
                Appeal Letter — {appealModal.payer_name} ({appealModal.denial_code})
              </h2>
              <button onClick={() => setAppealModal(null)} style={{
                background: "none", border: "none", fontSize: 24, cursor: "pointer", color: SLATE,
              }}>&times;</button>
            </div>

            {/* Appeal strength badge */}
            {appealModal.appeal_strength && (
              <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{
                  padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600,
                  background: appealModal.appeal_strength === "high" ? "#ECFDF5" : appealModal.appeal_strength === "medium" ? "#FFFBEB" : "#FEF2F2",
                  color: appealModal.appeal_strength === "high" ? GREEN : appealModal.appeal_strength === "medium" ? AMBER : RED,
                }}>
                  Appeal Strength: {appealModal.appeal_strength}
                </span>
                {appealModal.appeal_strength_reason && (
                  <span style={{ fontSize: 13, color: SLATE }}>{appealModal.appeal_strength_reason}</span>
                )}
              </div>
            )}

            {/* CMS references */}
            {appealModal.cms_references?.length > 0 && (
              <div style={{ marginBottom: 16, padding: 12, background: LIGHT_TEAL, borderRadius: 8, fontSize: 12 }}>
                <strong style={{ color: NAVY }}>CMS References:</strong>
                <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                  {appealModal.cms_references.map((ref, i) => (
                    <li key={i} style={{ color: SLATE, marginBottom: 2 }}>{ref}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Editable letter text */}
            <textarea
              value={appealModal.editText}
              onChange={e => setAppealModal(prev => ({ ...prev, editText: e.target.value }))}
              style={{
                width: "100%", minHeight: 400, padding: 16, borderRadius: 8,
                border: "1px solid #CBD5E1", fontFamily: "Arial, sans-serif",
                fontSize: 13, lineHeight: 1.6, resize: "vertical", color: NAVY,
              }}
            />

            {/* Action buttons */}
            <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
              <button onClick={handleCopyAppeal} style={{
                padding: "10px 20px", borderRadius: 8, border: "1px solid #CBD5E1",
                background: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, color: NAVY,
              }}>
                Copy
              </button>
              <button onClick={handleDownloadAppealPdf} style={{
                padding: "10px 20px", borderRadius: 8, border: "none",
                background: TEAL, color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600,
              }}>
                Download PDF
              </button>
              <button onClick={handlePrintAppeal} style={{
                padding: "10px 20px", borderRadius: 8, border: "1px solid #CBD5E1",
                background: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600, color: NAVY,
              }}>
                Print
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action bar */}
      <div className="no-print" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        {onClose ? (
          <button
            onClick={onClose}
            style={{
              background: "none", border: `1px solid ${SLATE}`, borderRadius: 8,
              padding: "8px 20px", fontSize: 14, color: SLATE, cursor: "pointer",
            }}
          >
            &larr; Back to Dashboard
          </button>
        ) : <div />}
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          style={{
            background: TEAL, border: "none", borderRadius: 8,
            padding: "10px 24px", fontSize: 14, fontWeight: 600,
            color: "#fff", cursor: downloading ? "wait" : "pointer",
            opacity: downloading ? 0.7 : 1,
          }}
        >
          {downloading ? "Generating PDF..." : "Download PDF"}
        </button>
      </div>

      {/* === 1. Cover / Header === */}
      <div style={{ textAlign: "center", marginBottom: 48, paddingBottom: 32, borderBottom: `3px solid ${TEAL}` }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: TEAL, letterSpacing: 2, textTransform: "uppercase", marginBottom: 8 }}>
          Parity Audit
        </div>
        <h1 style={{ fontSize: 32, fontWeight: 700, color: NAVY, margin: "0 0 8px" }}>
          Contract Integrity Report
        </h1>
        <p style={{ fontSize: 16, color: SLATE, margin: 0 }}>{practiceName}</p>
        {dateRange && <p style={{ fontSize: 14, color: SLATE, margin: "4px 0 0" }}>Period: {dateRange}</p>}
        <p style={{ fontSize: 14, color: SLATE, margin: "4px 0 0" }}>Report Date: {reportDate}</p>
        <p style={{ fontSize: 14, color: SLATE, margin: "4px 0 0" }}>
          {analysisResults.length} Payer{analysisResults.length !== 1 ? "s" : ""} Analyzed &middot; {totalLineItems} Line Items
        </p>
      </div>

      {/* === 2. Executive Summary (placeholder — will be in PDF) === */}
      <div style={sectionStyle}>
        <h2 style={headingStyle}>Executive Summary</h2>
        <p style={bodyStyle}>
          This audit analyzed {totalLineItems} remittance line items across {analysisResults.length} payer{analysisResults.length !== 1 ? "s" : ""} for {practiceName}.
          {totalUnderpayment > 0 && (
            <> Total identified underpayment: <strong style={{ color: RED }}>${totalUnderpayment.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong>.</>
          )}
          {totalDeniedValue > 0 && (
            <> Estimated denial recovery opportunity: <strong>${totalDeniedValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong>.</>
          )}
          {" "}The full AI-generated executive summary and recommended actions are included in the downloadable PDF report.
        </p>
      </div>

      {/* === 2b. Changes Since Last Month (only when trendData provided with alerts) === */}
      {trendData && trendData.alerts && trendData.alerts.length > 0 && (
        <div style={sectionStyle}>
          <h2 style={headingStyle}>Changes Since Last Month</h2>
          {trendData.trend_narrative && (
            <p style={{ ...bodyStyle, fontStyle: "italic", color: SLATE, marginBottom: 16 }}>
              {trendData.trend_narrative}
            </p>
          )}
          {(() => {
            const highAlerts = trendData.alerts.filter(a => a.severity === "high");
            const positiveAlerts = trendData.alerts.filter(a => a.severity === "positive");
            const trajectory = trendData.alerts.find(a => a.type === "revenue_gap_trajectory");
            return (
              <>
                {highAlerts.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: RED, margin: "0 0 8px" }}>New &amp; Worsening Issues</h3>
                    {highAlerts.map((a, i) => (
                      <div key={i} style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: 6, padding: "8px 12px", marginBottom: 6, fontSize: 13 }}>
                        {a.detail}
                        {a.financial_impact != null && <span style={{ fontWeight: 600, color: RED, marginLeft: 8 }}>(${a.financial_impact.toLocaleString("en-US", { minimumFractionDigits: 2 })})</span>}
                      </div>
                    ))}
                  </div>
                )}
                {positiveAlerts.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: GREEN, margin: "0 0 8px" }}>Resolved Issues</h3>
                    {positiveAlerts.map((a, i) => (
                      <div key={i} style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 6, padding: "8px 12px", marginBottom: 6, fontSize: 13 }}>
                        {a.detail}
                      </div>
                    ))}
                  </div>
                )}
                {trajectory && trajectory.financial_impact && (
                  <div style={{ background: NAVY, color: "#fff", borderRadius: 8, padding: 16, textAlign: "center", marginTop: 12 }}>
                    <div style={{ fontSize: 13, opacity: 0.8, marginBottom: 4 }}>Projected Annual Revenue Gap</div>
                    <div style={{ fontSize: 24, fontWeight: 700 }}>${trajectory.financial_impact.toLocaleString("en-US", { minimumFractionDigits: 2 })}</div>
                  </div>
                )}
              </>
            );
          })()}
        </div>
      )}

      {/* === 3. Contract Integrity Findings === */}
      <div style={sectionStyle}>
        <h2 style={headingStyle}>Contract Integrity Findings</h2>

        {analysisResults.map((ar, pi) => {
          const s = ar.result?.summary || {};
          const lines = ar.result?.line_items || [];
          const adherenceColor = s.adherence_rate >= 97 ? GREEN : s.adherence_rate >= 90 ? AMBER : RED;

          return (
            <div key={pi} style={{ marginBottom: 32 }}>
              <h3 style={{ fontSize: 17, fontWeight: 600, color: NAVY, margin: "0 0 12px" }}>
                {ar.payer_name}
              </h3>

              {/* Summary cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
                {[
                  { label: "Total Contracted", value: `$${(s.total_contracted || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}` },
                  { label: "Total Paid", value: `$${(s.total_paid || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}` },
                  { label: "Underpayment", value: `$${(s.total_underpayment || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`, color: s.total_underpayment > 0 ? RED : undefined },
                  { label: "Adherence", value: `${s.adherence_rate || 0}%`, color: adherenceColor },
                ].map((card, ci) => (
                  <div key={ci} style={{
                    padding: "14px 16px", borderRadius: 8, background: "#fff",
                    border: "1px solid #E2E8F0", textAlign: "center",
                  }}>
                    <div style={{ fontSize: 12, color: SLATE, marginBottom: 4 }}>{card.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, color: card.color || NAVY }}>{card.value}</div>
                  </div>
                ))}
              </div>

              {/* Flag breakdown */}
              <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
                {[
                  { label: "Correct", count: s.correct_count, flag: "CORRECT" },
                  { label: "Underpaid", count: s.underpaid_count, flag: "UNDERPAID" },
                  { label: "Denied", count: s.denied_count, flag: "DENIED" },
                  ...(s.billed_below_count ? [{ label: "Below Contract", count: s.billed_below_count, flag: "BILLED_BELOW" }] : []),
                  { label: "Overpaid", count: s.overpaid_count, flag: "OVERPAID" },
                  { label: "No Contract", count: s.no_contract_count, flag: "NO_CONTRACT" },
                ].filter(b => b.count > 0).map((b, bi) => {
                  const fc = flagColor(b.flag);
                  return (
                    <span key={bi} style={{
                      padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                      background: fc.bg, color: fc.text,
                    }}>
                      {b.label}: {b.count}
                    </span>
                  );
                })}
              </div>

              {/* Line items table */}
              {lines.length > 0 && (
                <div style={{ overflowX: "auto" }}>
                  <table style={tableStyle}>
                    <thead>
                      <tr>
                        <th style={thStyle}>CPT</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Billed</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Paid</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Expected</th>
                        <th style={{ ...thStyle, textAlign: "right" }}>Variance</th>
                        <th style={thStyle}>Flag</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lines.slice(0, 50).map((li, i) => {
                        const fc = flagColor(li.flag);
                        return (
                          <tr key={i} style={{ background: li.flag === "UNDERPAID" || li.flag === "DENIED" ? fc.bg : i % 2 === 0 ? "#fff" : "#F8FAFC" }}>
                            <td style={tdStyle}>{li.cpt_code}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>${(li.billed_amount || 0).toFixed(2)}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>${(li.paid_amount || 0).toFixed(2)}</td>
                            <td style={{ ...tdStyle, textAlign: "right" }}>
                              {li.expected_payment != null ? `$${li.expected_payment.toFixed(2)}` : "\u2014"}
                            </td>
                            <td style={{
                              ...tdStyle, textAlign: "right", fontWeight: 600,
                              color: li.variance < -0.5 ? RED : li.variance > 0.5 ? GREEN : NAVY,
                            }}>
                              {li.variance != null ? `${li.variance >= 0 ? "+" : ""}$${li.variance.toFixed(2)}` : "\u2014"}
                            </td>
                            <td style={tdStyle}>
                              <span style={{
                                padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
                                background: fc.bg, color: fc.text,
                              }}>
                                {li.flag}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                  {lines.length > 50 && (
                    <p style={{ fontSize: 12, color: SLATE, marginTop: 8 }}>
                      Showing 50 of {lines.length} line items. Full details in PDF.
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* === 4. Denial Pattern Analysis === */}
      {analysisResults.some(r => r.denial_intel?.denial_types?.length > 0) && (
        <div style={sectionStyle}>
          <h2 style={headingStyle}>Denial Pattern Analysis</h2>
          {analysisResults.map((ar, pi) => {
            const intel = ar.denial_intel;
            if (!intel?.denial_types?.length) return null;
            return (
              <div key={pi} style={{ marginBottom: 24 }}>
                <h3 style={{ fontSize: 15, fontWeight: 600, color: NAVY, margin: "0 0 10px" }}>{ar.payer_name}</h3>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>Code</th>
                      <th style={thStyle}>Explanation</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>Count</th>
                      <th style={{ ...thStyle, textAlign: "right" }}>Value</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>Appeal Worth</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {intel.denial_types.slice(0, 5).map((dt, di) => {
                      const genKey = `${ar.payer_name}-${dt.adjustment_code}`;
                      return (
                      <tr key={di} style={{ background: di % 2 === 0 ? "#fff" : "#F8FAFC" }}>
                        <td style={{ ...tdStyle, fontWeight: 600 }}>{dt.adjustment_code}</td>
                        <td style={{ ...tdStyle, maxWidth: 300 }}>{dt.plain_language}</td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>{dt.count}</td>
                        <td style={{ ...tdStyle, textAlign: "right" }}>${(dt.total_value || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>
                          <span style={{
                            padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
                            background: dt.appeal_worthiness === "high" ? "#ECFDF5" : dt.appeal_worthiness === "medium" ? "#FFFBEB" : "#F3F4F6",
                            color: dt.appeal_worthiness === "high" ? GREEN : dt.appeal_worthiness === "medium" ? AMBER : SLATE,
                          }}>
                            {dt.appeal_worthiness}
                          </span>
                        </td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>
                          <button
                            onClick={() => handleDraftAppeal(dt, ar.payer_name)}
                            disabled={appealGenerating === genKey}
                            style={{
                              padding: "4px 12px", borderRadius: 6, border: "none",
                              background: TEAL, color: "#fff", fontSize: 11, fontWeight: 600,
                              cursor: appealGenerating === genKey ? "wait" : "pointer",
                              opacity: appealGenerating === genKey ? 0.6 : 1,
                              whiteSpace: "nowrap",
                            }}
                          >
                            {appealGenerating === genKey ? "Drafting..." : "Draft Appeal"}
                          </button>
                        </td>
                      </tr>
                      );
                    })}
                  </tbody>
                </table>
                {intel.pattern_summary && (
                  <p style={{ fontSize: 13, color: SLATE, fontStyle: "italic", marginTop: 8 }}>{intel.pattern_summary}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* === 5. Revenue Gap Estimate === */}
      <div style={sectionStyle}>
        <h2 style={headingStyle}>Revenue Gap Estimate</h2>
        <div style={{
          background: NAVY, borderRadius: 12, padding: 24, color: "#fff", marginBottom: 16,
        }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24, textAlign: "center" }}>
            <div>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>Identified Underpayments</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>
                ${totalUnderpayment.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>Denial Recovery</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>
                ${totalDeniedValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>Total Revenue Gap</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: "#5EEAD4" }}>
                ${(totalUnderpayment + totalDeniedValue).toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.2)", marginTop: 20, paddingTop: 16, textAlign: "center" }}>
            <div style={{ fontSize: 13, opacity: 0.7, marginBottom: 4 }}>Annualized Estimate (&times;12)</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>
              ${((totalUnderpayment + totalDeniedValue) * 12).toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>

        {/* Per-payer breakdown */}
        {analysisResults.length > 1 && (
          <div style={{ marginTop: 12 }}>
            {analysisResults.map((ar, pi) => {
              const s = ar.result?.summary || {};
              return (
                <div key={pi} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "10px 16px", borderBottom: "1px solid #E2E8F0", fontSize: 14,
                }}>
                  <span style={{ fontWeight: 500, color: NAVY }}>{ar.payer_name}</span>
                  <span>
                    <span style={{ color: RED, fontWeight: 600 }}>
                      ${(s.total_underpayment || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </span>
                    <span style={{ color: SLATE, marginLeft: 8 }}>
                      ({s.underpaid_count || 0} underpaid, {s.denied_count || 0} denied)
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* === 6. Billing Contractor Assessment === */}
      {analysisResults.some(r => r.result?.scorecard?.clean_claim_rate != null) && (
        <div style={sectionStyle}>
          <h2 style={headingStyle}>Billing Performance</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
            {analysisResults.map((ar, pi) => {
              const sc = ar.result?.scorecard || {};
              if (sc.clean_claim_rate == null) return null;
              return (
                <div key={pi} style={{ padding: 20, borderRadius: 8, background: "#fff", border: "1px solid #E2E8F0" }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: NAVY, marginBottom: 12 }}>{ar.payer_name}</div>
                  {[
                    { label: "Clean Claim Rate", value: `${sc.clean_claim_rate}%`, bench: "95%", good: sc.clean_claim_rate >= 95 },
                    { label: "Denial Rate", value: `${sc.denial_rate}%`, bench: "<5%", good: sc.denial_rate <= 5 },
                    { label: "Adherence", value: `${sc.payer_adherence_rate}%`, bench: "97%", good: sc.payer_adherence_rate >= 97 },
                    { label: "Preventable Denials", value: `${sc.preventable_denial_rate}%`, bench: "<30%", good: sc.preventable_denial_rate <= 30 },
                  ].map((kpi, ki) => (
                    <div key={ki} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <span style={{ fontSize: 12, color: SLATE }}>{kpi.label}</span>
                      <span style={{
                        fontSize: 14, fontWeight: 600,
                        color: kpi.good ? GREEN : RED,
                      }}>
                        {kpi.value} <span style={{ fontSize: 10, color: SLATE, fontWeight: 400 }}>({kpi.bench})</span>
                      </span>
                    </div>
                  ))}
                  {sc.narrative && (
                    <p style={{ fontSize: 12, color: SLATE, marginTop: 8, lineHeight: 1.5, borderTop: "1px solid #E2E8F0", paddingTop: 8 }}>
                      {sc.narrative}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* === 7-8. Methodology === */}
      <div style={sectionStyle}>
        <h2 style={headingStyle}>Methodology</h2>
        <p style={bodyStyle}>
          This audit analyzed remittance data for {practiceName} across {analysisResults.length} payer{analysisResults.length !== 1 ? "s" : ""}{dateRange ? ` for the period ${dateRange}` : ""}.
          Contract rates were compared against actual paid amounts from 835 Electronic Remittance Advice files.
          Medicare benchmark rates are sourced from the CMS 2026 Physician Fee Schedule,
          geographically adjusted using the CMS carrier/locality crosswalk.
          Denial patterns were analyzed using ANSI X12 adjustment reason codes.
          All dollar amounts are based on the data provided and should be verified against original payer contracts.
        </p>
      </div>

      {/* === 9. Next Steps === */}
      <div style={sectionStyle}>
        <h2 style={headingStyle}>Next Steps</h2>
        <p style={bodyStyle}>
          This report represents a point-in-time audit of your payer contracts.
          For ongoing revenue protection, we recommend quarterly audits as new remittance data becomes available.
          CivicScale Parity Audit can automate this process with monthly monitoring,
          real-time underpayment alerts, and automated appeal letter generation.
        </p>
      </div>

      {/* Footer */}
      <div style={{
        borderTop: `2px solid ${TEAL}`, paddingTop: 16, marginTop: 32,
        fontSize: 12, color: SLATE, lineHeight: 1.6, textAlign: "center",
      }}>
        <p style={{ margin: 0 }}>
          Parity Audit by CivicScale. Benchmark comparisons use publicly available CMS Medicare data.
          This report is not legal or financial advice. Verify all findings with your payer contracts
          and consult a billing specialist before taking action.
        </p>
        <p style={{ margin: "8px 0 0", fontWeight: 600, color: TEAL }}>&copy; CivicScale 2026</p>
      </div>

      {/* Bottom action bar */}
      <div className="no-print" style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 32 }}>
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          style={{
            background: TEAL, border: "none", borderRadius: 8,
            padding: "12px 32px", fontSize: 15, fontWeight: 600,
            color: "#fff", cursor: downloading ? "wait" : "pointer",
            opacity: downloading ? 0.7 : 1,
          }}
        >
          {downloading ? "Generating PDF..." : "Download PDF Report"}
        </button>
        <button
          onClick={() => window.print()}
          style={{
            background: "none", border: `1px solid ${NAVY}`, borderRadius: 8,
            padding: "12px 24px", fontSize: 15, color: NAVY, cursor: "pointer",
          }}
        >
          Print Report
        </button>
      </div>
    </div>
  );
}
