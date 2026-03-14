import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function BrokerConnectCard({ benchmarkData = {}, source = "benchmark" }) {
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState(benchmarkData.email || "");
  const [formCompany, setFormCompany] = useState("");
  const [formMessage, setFormMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const handleSubmit = async () => {
    if (!formEmail) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const res = await fetch(`${API_BASE}/api/employer/broker-connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          employer_email: formEmail,
          requester_name: formName || null,
          company_name: formCompany || null,
          employee_count_range: benchmarkData.company_size || null,
          industry: benchmarkData.industry || null,
          state: benchmarkData.state || null,
          pepm: benchmarkData.pepm || null,
          percentile: benchmarkData.percentile || null,
          annual_gap: benchmarkData.annual_gap || null,
          excess_amount: benchmarkData.excess_amount || null,
          message: formMessage || null,
        }),
      });
      const data = await res.json();
      if (data.submitted) {
        setSubmitted(true);
      } else {
        setSubmitError("Something went wrong. Please try again.");
      }
    } catch {
      setSubmitError("Failed to submit. Please try again.");
    }
    setSubmitting(false);
  };

  return (
    <div className="broker-connect-card" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "14px", padding: "24px" }}>
      <style>{`
        @media print {
          body { background: #fff !important; color: #1e293b !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .broker-connect-card { display: none !important; }
          nav, header, footer, button, .no-print { display: none !important; }
          * { color: #1e293b !important; border-color: #e2e8f0 !important; }
          table { border-collapse: collapse; }
          table th, table td { border: 1px solid #e2e8f0 !important; padding: 6px 10px !important; }
        }
      `}</style>
      <div style={{ fontSize: "11px", fontWeight: "600", color: "#0d9488", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: "16px" }}>WORK WITH A BROKER</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1px 1fr", gap: "20px" }}>
        {/* Option A — Download report as PDF */}
        <div>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>&#128196;</div>
          <h4 style={{ fontSize: "15px", fontWeight: "600", color: "#f1f5f9", margin: "0 0 6px" }}>Download report</h4>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: "0 0 16px", lineHeight: "1.5" }}>
            Save this analysis as a PDF to share with your broker or keep for your records.
          </p>
          <button
            onClick={() => window.print()}
            style={{
              display: "block", width: "100%", textAlign: "center", padding: "10px 16px",
              border: "1px solid #0d9488", borderRadius: "8px", background: "transparent",
              color: "#0d9488", fontSize: "14px", fontWeight: "600",
              cursor: "pointer",
            }}
          >
            Download as PDF
          </button>
        </div>

        {/* Divider */}
        <div style={{ background: "rgba(255,255,255,0.08)", width: "1px" }} />

        {/* Option B — Find a broker */}
        <div>
          <div style={{ fontSize: "20px", marginBottom: "8px" }}>&#128269;</div>
          <h4 style={{ fontSize: "15px", fontWeight: "600", color: "#f1f5f9", margin: "0 0 6px" }}>Connect with a broker</h4>
          <p style={{ fontSize: "13px", color: "#94a3b8", margin: "0 0 16px", lineHeight: "1.5" }}>
            We'll match you with a benefits broker in our network who works with employers your size.
          </p>

          {submitted ? (
            <div style={{ background: "rgba(34,197,94,0.08)", border: "1px solid rgba(34,197,94,0.2)", borderRadius: "8px", padding: "12px 16px" }}>
              <p style={{ margin: 0, fontSize: "13px", color: "#22c55e", fontWeight: "500" }}>
                ✓ Request submitted. We'll follow up within 1 business day.
              </p>
            </div>
          ) : !showForm ? (
            <button
              onClick={() => setShowForm(true)}
              style={{
                display: "block", width: "100%", padding: "10px 16px",
                background: "#0d9488", color: "#fff", border: "none",
                borderRadius: "8px", fontSize: "14px", fontWeight: "600",
                cursor: "pointer",
              }}
            >
              Send Request
            </button>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <input
                value={formName}
                onChange={e => setFormName(e.target.value)}
                placeholder="Your name"
                style={{ padding: "8px 12px", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.04)", color: "#f1f5f9", boxSizing: "border-box" }}
              />
              <input
                value={formEmail}
                onChange={e => setFormEmail(e.target.value)}
                placeholder="Your email"
                type="email"
                style={{ padding: "8px 12px", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.04)", color: "#f1f5f9", boxSizing: "border-box" }}
              />
              <input
                value={formCompany}
                onChange={e => setFormCompany(e.target.value)}
                placeholder="Company name"
                style={{ padding: "8px 12px", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.04)", color: "#f1f5f9", boxSizing: "border-box" }}
              />
              <textarea
                value={formMessage}
                onChange={e => setFormMessage(e.target.value)}
                placeholder="Anything you'd like us to know? e.g. renewal date, current carrier"
                rows={2}
                style={{ padding: "8px 12px", border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", fontSize: "13px", background: "rgba(255,255,255,0.04)", color: "#f1f5f9", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }}
              />
              {submitError && <p style={{ margin: 0, fontSize: "12px", color: "#ef4444" }}>{submitError}</p>}
              <button
                onClick={handleSubmit}
                disabled={submitting || !formEmail}
                style={{
                  padding: "10px 16px", background: "#0d9488", color: "#fff",
                  border: "none", borderRadius: "8px", fontSize: "14px",
                  fontWeight: "600", cursor: submitting ? "wait" : "pointer",
                  opacity: (submitting || !formEmail) ? 0.6 : 1,
                }}
              >
                {submitting ? "Sending..." : "Send Request"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
