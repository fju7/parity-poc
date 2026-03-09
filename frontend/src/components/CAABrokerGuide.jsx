import { useState } from "react";
import { Link } from "react-router-dom";

const CARRIERS = [
  {
    name: "UnitedHealthcare",
    color: "#3b82f6",
    share: "~15% national market share",
    contact: "Employer/plan sponsor data team via your UHC account rep or EmployerConnect portal",
    request: "\"Pursuant to the Consolidated Appropriations Act of 2021, Section 201, I am requesting machine-readable claims data for plan year [YEAR] including 837/835 transaction files or equivalent HIPAA-compliant format for all medical and pharmacy claims.\"",
    format: "835 EDI or CSV",
    timeline: "30\u201360 days typical",
    friction: "Often routes through account rep who may be unfamiliar with CAA obligations. Escalate to compliance team if initial request is ignored.",
  },
  {
    name: "Cigna",
    color: "#10b981",
    share: "~10% national market share",
    contact: "Client Services or your Cigna account executive",
    request: "Same CAA Section 201 language as above",
    format: "835 EDI files available",
    timeline: "30\u201345 days typical",
    friction: "May offer aggregate reports first \u2014 insist on transaction-level data.",
  },
  {
    name: "Aetna / CVS Health",
    color: "#8b5cf6",
    share: "~8% national market share",
    contact: "Aetna client portal or account manager",
    request: "Same CAA Section 201 language",
    format: "Claims detail files in CSV or EDI",
    timeline: "45\u201360 days",
    friction: "Aetna has improved compliance but may require a formal written request on company letterhead.",
  },
  {
    name: "Anthem / Elevance Health",
    color: "#f59e0b",
    share: "~9% national market share",
    contact: "Employer portal (Sydney Health for Employers) or account rep",
    request: "Same CAA Section 201 language",
    format: "837/835 EDI or flat file",
    timeline: "30\u201360 days",
    friction: "BCBS affiliates vary by state \u2014 some are more responsive than others. Blue Shield of CA and BCBS of IL tend to be faster.",
  },
  {
    name: "BCBS Affiliates (other)",
    color: "#64748b",
    share: "~30% combined national market share",
    contact: "Your specific BCBS plan\u2019s employer services team",
    request: "Same CAA Section 201 language",
    format: "Varies by affiliate",
    timeline: "30\u201390 days",
    friction: "Most variable of all carriers. Some affiliates are excellent, others are slow. Document all requests in writing.",
  },
];

const TEMPLATE = `Subject: CAA Section 201 Claims Data Request \u2014 [Company Name] Plan Year [YEAR]

Dear [Carrier] Client Services / Account Team,

Pursuant to Section 201 of the Consolidated Appropriations Act of 2021 and its implementing regulations, I am formally requesting machine-readable claims data for the following plan:

Plan Sponsor: [Employer Name]
Group Number: [Group ID]
Plan Year: [YEAR]
Requested Format: 835 EDI transaction files or equivalent HIPAA-compliant machine-readable format
Scope: All medical and pharmacy claims for the requested plan year

Please confirm receipt of this request and provide an expected delivery timeline. If there are any questions or additional authorization requirements, please contact me directly.

[Broker Name]
[Firm]
[Email / Phone]`;

export default function CAABrokerGuide() {
  const [copied, setCopied] = useState(false);

  const copyTemplate = () => {
    navigator.clipboard.writeText(TEMPLATE).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0a1628", color: "#e2e8f0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet" />

      <header className="cs-home-header">
        <Link to="/" style={{ display: "flex", alignItems: "center", gap: "12px", textDecoration: "none", color: "inherit" }}>
          <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "linear-gradient(135deg, #0d9488, #14b8a6)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px", fontWeight: "700", color: "#0a1628" }}>C</div>
          <span style={{ fontSize: "18px", fontWeight: "600", letterSpacing: "-0.02em" }}>CivicScale</span>
        </Link>
        <nav className="cs-home-nav">
          <Link to="/broker/dashboard" style={{ color: "#60a5fa", textDecoration: "none" }}>Broker Dashboard</Link>
        </nav>
      </header>

      <div style={{ maxWidth: "760px", margin: "0 auto", padding: "60px 24px 80px" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <div style={{ display: "inline-block", background: "rgba(59,130,246,0.12)", borderRadius: "8px", padding: "8px 14px", marginBottom: "16px" }}>
            <span style={{ fontSize: "13px", fontWeight: "600", color: "#60a5fa" }}>CAA DATA GUIDE</span>
          </div>
          <h1 style={{ fontFamily: "'DM Serif Display', serif", fontSize: "clamp(26px, 3.5vw, 38px)", fontWeight: "400", color: "#f1f5f9", marginBottom: "12px", lineHeight: "1.2" }}>
            How to Get Your Clients' Claims Data
          </h1>
          <p style={{ fontSize: "15px", color: "#94a3b8", lineHeight: "1.7", maxWidth: "600px", margin: "0 auto" }}>
            The Consolidated Appropriations Act of 2021 gives every employer the legal right to their claims data. Here's how to request it from the major carriers.
          </p>
        </div>

        {/* Why this matters */}
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(59,130,246,0.18)", borderRadius: "14px", padding: "28px", marginBottom: "32px" }}>
          <div style={{ fontSize: "15px", fontWeight: "600", color: "#cbd5e1", marginBottom: "12px" }}>Why this matters</div>
          <p style={{ fontSize: "14px", color: "#94a3b8", lineHeight: "1.8", margin: 0 }}>
            Most employers have never seen their own claims data &mdash; carriers don't volunteer it. But plan sponsors have had a federal right to machine-readable claims data since 2022 under the CAA. A single data request unlocks procedure-level analysis that most brokers have never been able to offer. This guide walks you through the process for the five largest carriers.
          </p>
        </div>

        {/* Carrier Cards */}
        {CARRIERS.map((c) => (
          <div key={c.name} style={{ background: "rgba(255,255,255,0.02)", borderLeft: `4px solid ${c.color}`, borderRadius: "8px", padding: "24px", marginBottom: "16px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "16px", flexWrap: "wrap", gap: "8px" }}>
              <div style={{ fontSize: "18px", fontWeight: "600", color: "#f1f5f9" }}>{c.name}</div>
              <div style={{ fontSize: "12px", color: "#64748b" }}>{c.share}</div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "14px" }}>
              <div>
                <span style={{ fontWeight: "600", color: "#cbd5e1" }}>Who to contact: </span>
                <span style={{ color: "#94a3b8" }}>{c.contact}</span>
              </div>
              <div>
                <span style={{ fontWeight: "600", color: "#cbd5e1" }}>What to request: </span>
                <span style={{ color: "#94a3b8" }}>{c.request}</span>
              </div>
              <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" }}>
                <div>
                  <span style={{ fontWeight: "600", color: "#cbd5e1" }}>Format: </span>
                  <span style={{ color: "#94a3b8" }}>{c.format}</span>
                </div>
                <div>
                  <span style={{ fontWeight: "600", color: "#cbd5e1" }}>Timeline: </span>
                  <span style={{ color: "#94a3b8" }}>{c.timeline}</span>
                </div>
              </div>
              <div style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.15)", borderRadius: "6px", padding: "10px 12px" }}>
                <span style={{ fontWeight: "600", color: "#f59e0b", fontSize: "12px" }}>FRICTION POINT: </span>
                <span style={{ color: "#94a3b8", fontSize: "13px" }}>{c.friction}</span>
              </div>
            </div>
          </div>
        ))}

        {/* Sample Request Letter */}
        <div style={{ marginTop: "40px", marginBottom: "40px" }}>
          <div style={{ fontSize: "20px", fontWeight: "600", color: "#f1f5f9", marginBottom: "8px" }}>Sample Request Letter</div>
          <p style={{ fontSize: "14px", color: "#64748b", marginBottom: "16px" }}>
            Copy and customize this template. Send via email and follow up in writing if no response within 10 business days.
          </p>
          <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "10px", padding: "20px", position: "relative" }}>
            <pre style={{ margin: 0, fontSize: "13px", color: "#cbd5e1", lineHeight: "1.7", whiteSpace: "pre-wrap", wordWrap: "break-word", fontFamily: "'DM Sans', sans-serif" }}>
              {TEMPLATE}
            </pre>
            <button
              onClick={copyTemplate}
              style={{
                position: "absolute", top: "12px", right: "12px",
                background: copied ? "#10b981" : "#3b82f6",
                color: "#fff", border: "none", borderRadius: "6px",
                padding: "8px 16px", fontSize: "13px", fontWeight: "600",
                cursor: "pointer", transition: "background 0.2s",
              }}
            >
              {copied ? "Copied!" : "Copy Template"}
            </button>
          </div>
        </div>

        {/* Once you have the data */}
        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(16,185,129,0.25)", borderRadius: "14px", padding: "28px", marginBottom: "32px" }}>
          <div style={{ fontSize: "18px", fontWeight: "600", color: "#f1f5f9", marginBottom: "16px" }}>Once you have the data</div>
          <ul style={{ margin: 0, padding: "0 0 0 20px", fontSize: "14px", color: "#94a3b8", lineHeight: "2" }}>
            <li>Upload it to Parity Employer's Claims Check tool to see exactly which procedures are driving costs</li>
            <li>Share results with your client as a benchmark report</li>
            <li>Use findings to negotiate better rates at renewal</li>
          </ul>
          <div style={{ marginTop: "20px" }}>
            <Link to="/billing/employer/claims-check" style={{ display: "inline-block", background: "#10b981", color: "#fff", padding: "12px 24px", borderRadius: "8px", fontWeight: "600", fontSize: "14px", textDecoration: "none" }}>
              Go to Claims Check &rarr;
            </Link>
          </div>
        </div>

        <div style={{ textAlign: "center" }}>
          <Link to="/broker/dashboard" style={{ color: "#64748b", fontSize: "14px", textDecoration: "none" }}>
            &larr; Back to Broker Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
