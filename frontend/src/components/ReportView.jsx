import { useState } from "react";
import { Footer } from "./UploadView.jsx";

export default function ReportView({ report, provider, serviceDate, onReset }) {
  const { lineItems, summary } = report;
  const billState = getBillState(summary, lineItems);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-[Arial,sans-serif]">
      {/* Print-only header */}
      <div className="hidden print:block px-4 pt-4 pb-2 border-b border-gray-300 mb-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-[#1B3A5C] tracking-tight">
            Parity Health
          </h1>
          <p className="text-sm text-gray-500">
            Report generated {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Medical Bill Benchmark Analysis — CMS PFS 2026 | OPPS 2026 | CLFS 2026 Q1
        </p>
      </div>

      <main className="max-w-5xl mx-auto px-4 py-8 w-full flex-1">
        {/* Action buttons */}
        <div className="flex items-center gap-3 mb-6 print:hidden">
          <button
            onClick={() => window.print()}
            className="px-4 py-2 text-sm font-medium text-[#1B3A5C] border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"
          >
            Download Report
          </button>
          {onReset && (
            <button
              onClick={onReset}
              className="px-4 py-2 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
            >
              Analyze Another Bill
            </button>
          )}
        </div>

        {/* Summary Card — top-level verdict */}
        <SummaryCard billState={billState} summary={summary} />

        {/* Historical rate data warning */}
        <HistoricalDataBanner lineItems={lineItems} serviceDate={serviceDate} />

        {/* Partial benchmark warning */}
        {report.partialWarning && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 flex items-start gap-3">
            <svg className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
            </svg>
            <p className="text-sm text-amber-800">{report.partialWarning}</p>
          </div>
        )}

        {/* Bill Summary */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-[#1B3A5C]">
                  {provider?.name || "Medical Provider"}
                </h2>
                {report.parsingMethod === "ai" && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-100 text-purple-700">
                    AI-assisted reading
                  </span>
                )}
                {report.parsingMethod === "manual" && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-600">
                    Manual entry
                  </span>
                )}
              </div>
              {serviceDate && (
                <p className="text-sm text-gray-500 mt-1">
                  Service date: {serviceDate}
                </p>
              )}
            </div>
            <div className="text-right text-sm text-gray-500">
              <p>{summary.totalItemCount} line items analyzed</p>
              <p>{summary.flaggedItemCount} flagged for review</p>
            </div>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard label="Total Billed" value={formatCurrency(summary.totalBilled)} />
            <StatCard
              label="Total Benchmark"
              value={formatCurrency(summary.totalBenchmark)}
            />
            <StatCard
              label="Potential Discrepancy"
              value={formatCurrency(summary.totalPotentialDiscrepancy)}
              highlight
            />
          </div>
        </div>

        {/* Anomaly Meter */}
        <AnomalyMeter
          flagged={summary.flaggedItemCount}
          total={summary.totalItemCount}
        />

        {/* Discrepancy Callout */}
        {summary.totalPotentialDiscrepancy > 0 && (
          <div className="bg-[#1B3A5C] rounded-xl p-6 mb-6 text-center">
            <p className="text-white/70 text-sm mb-1">
              Total Potential Discrepancy
            </p>
            <p className="text-white text-4xl font-bold">
              {formatCurrency(summary.totalPotentialDiscrepancy)}
            </p>
            <p className="text-white/50 text-xs mt-2">
              Based on CMS Medicare benchmark rates for your area
            </p>
          </div>
        )}

        {/* Line Items Table */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-bold text-[#1B3A5C]">
              Line Item Analysis
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-gray-500 text-xs uppercase tracking-wider">
                  <th className="px-6 py-3 font-medium">Code</th>
                  <th className="px-6 py-3 font-medium">Description</th>
                  <th className="px-6 py-3 font-medium text-right">Billed</th>
                  <th className="px-6 py-3 font-medium text-right">
                    Benchmark
                  </th>
                  <th className="px-6 py-3 font-medium text-right">Score</th>
                  <th className="px-6 py-3 font-medium">Flag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lineItems.map((item, i) => (
                  <LineItemRow key={i} item={item} />
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Coding Intelligence Section */}
        <CodingIntelligenceSection
          codingAlerts={report.codingAlerts}
          codingSummary={report.codingSummary}
        />

        {/* What to do next */}
        <WhatToDoNext billState={billState} summary={summary} />

        {/* Disclaimer */}
        <div className="text-xs text-gray-400 text-center mb-4 space-y-2">
          <p>
            Benchmark rates sourced from CMS Medicare Physician Fee Schedule (2026),
            CMS Outpatient Prospective Payment System (2026), and CMS Clinical Laboratory
            Fee Schedule (2026 Q1). Rates reflect the CMS schedule in effect at time of
            report generation. For bills with service dates in prior years, rates may
            differ from those in effect at time of service.
          </p>
          <p>
            Parity Health provides benchmark comparisons only. This is not legal advice.
            Consult a billing specialist or attorney before taking action.
            Benchmark rates are based on publicly available CMS Medicare data and
            may not reflect negotiated commercial insurance rates.
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Show a blue info banner when historical rate data isn't available for old bills */
function HistoricalDataBanner({ lineItems, serviceDate }) {
  // Only show if any item lacks historical data
  const hasUnavailable = lineItems.some((li) => li.historicalDataAvailable === false);
  if (!hasUnavailable) return null;

  // Only show if service date is >12 months ago
  if (!serviceDate) return null;
  let parsed;
  // Try MM/DD/YYYY
  const mdyMatch = serviceDate.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (mdyMatch) {
    parsed = new Date(+mdyMatch[3], +mdyMatch[1] - 1, +mdyMatch[2]);
  } else {
    parsed = new Date(serviceDate);
  }
  if (isNaN(parsed.getTime())) return null;

  const twelveMonthsAgo = new Date();
  twelveMonthsAgo.setFullYear(twelveMonthsAgo.getFullYear() - 1);
  if (parsed >= twelveMonthsAgo) return null;

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex items-start gap-3">
      <svg className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
      </svg>
      <div>
        <p className="text-sm font-medium text-blue-800">
          Benchmark rates may differ from time of service
        </p>
        <p className="text-sm text-blue-700 mt-1">
          This bill's service date is more than 12 months ago. We're comparing against
          current CMS rates because historical rate data for that period hasn't been loaded
          yet. Actual Medicare rates at the time of service may have been different.
        </p>
      </div>
    </div>
  );
}

/** Determine the overall bill state for the summary card */
function getBillState(summary, lineItems) {
  const benchmarkedCount = lineItems.filter((li) => li.benchmarkRate !== null).length;
  if (benchmarkedCount === 0) return "no_benchmarks";
  if (summary.flaggedItemCount === 0) return "clean";
  // "minor" if all flagged items have score <= 3x AND total discrepancy < $500
  const hasHighScore = lineItems.some((li) => li.flagged && li.anomalyScore > 3);
  if (!hasHighScore && summary.totalPotentialDiscrepancy < 500) return "minor";
  return "significant";
}

const BILL_STATE_CONFIG = {
  significant: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    icon: "text-amber-500",
    titleColor: "text-amber-800",
    title: "This bill has charges that look unusually high",
    getBody: (summary) =>
      `We found ${summary.flaggedItemCount} charge${summary.flaggedItemCount === 1 ? "" : "s"} that ${summary.flaggedItemCount === 1 ? "is" : "are"} significantly above the Medicare benchmark for your area. The total potential overcharge is ${formatCurrency(summary.totalPotentialDiscrepancy)}. See the details below and consider contacting the billing department.`,
    iconPath: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
  },
  minor: {
    bg: "bg-blue-50",
    border: "border-blue-200",
    icon: "text-blue-500",
    titleColor: "text-blue-800",
    title: "A few charges are slightly above benchmark",
    getBody: (summary) =>
      `We found ${summary.flaggedItemCount} charge${summary.flaggedItemCount === 1 ? "" : "s"} modestly above the Medicare benchmark (${formatCurrency(summary.totalPotentialDiscrepancy)} total). This is relatively common and may not require action, but review the details below if you'd like to follow up.`,
    iconPath: "m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z",
  },
  clean: {
    bg: "bg-green-50",
    border: "border-green-200",
    icon: "text-green-500",
    titleColor: "text-green-800",
    title: "This bill looks good",
    getBody: () =>
      "All charges are within normal range compared to Medicare benchmarks for your area. No action is needed — this bill appears to be fairly priced.",
    iconPath: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  },
  no_benchmarks: {
    bg: "bg-gray-50",
    border: "border-gray-200",
    icon: "text-gray-400",
    titleColor: "text-gray-700",
    title: "We couldn't benchmark this bill",
    getBody: () =>
      "None of the procedure codes on this bill matched our current Medicare rate database. This can happen with certain facility codes or newer procedures. The raw charges are shown below for your reference.",
    iconPath: "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z",
  },
};

function SummaryCard({ billState, summary }) {
  const cfg = BILL_STATE_CONFIG[billState];

  return (
    <div className={`${cfg.bg} border ${cfg.border} rounded-xl p-5 mb-6 flex items-start gap-4`}>
      <svg className={`w-6 h-6 ${cfg.icon} shrink-0 mt-0.5`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d={cfg.iconPath} />
      </svg>
      <div>
        <h2 className={`text-lg font-bold ${cfg.titleColor} mb-1`}>{cfg.title}</h2>
        <p className="text-sm text-gray-600 leading-relaxed">{cfg.getBody(summary)}</p>
      </div>
    </div>
  );
}

function StatCard({ label, value, highlight = false }) {
  return (
    <div
      className={`rounded-lg p-4 ${
        highlight ? "bg-amber-50 border border-amber-200" : "bg-gray-50"
      }`}
    >
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p
        className={`text-2xl font-bold ${
          highlight ? "text-amber-600" : "text-[#1B3A5C]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function AnomalyMeter({ flagged, total }) {
  const pct = total > 0 ? (flagged / total) * 100 : 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-[#1B3A5C]">
          Anomaly Overview
        </h3>
        <span className="text-sm text-gray-500">
          {flagged} of {total} items flagged
        </span>
      </div>
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            pct > 50 ? "bg-red-500" : pct > 25 ? "bg-amber-500" : "bg-[#0D7377]"
          }`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
    </div>
  );
}

function LineItemRow({ item }) {
  const [expanded, setExpanded] = useState(false);
  const scoreColor = getScoreColor(item.anomalyScore);
  const plainLabel = getScorePlainLabel(item.anomalyScore);

  return (
    <>
      <tr
        className={`${
          item.flagged ? "bg-amber-50/50" : ""
        } hover:bg-gray-50 cursor-pointer`}
        onClick={() => item.flagged && setExpanded(!expanded)}
      >
        <td className="px-6 py-3 font-mono text-[#1B3A5C] whitespace-nowrap">
          {item.code}
          <span className="ml-1.5 text-[10px] text-gray-400 font-sans">
            {item.codeType}
          </span>
        </td>
        <td className="px-6 py-3 text-gray-600 max-w-xs truncate">
          {item.description}
        </td>
        <td className="px-6 py-3 text-right font-mono text-[#1B3A5C]">
          {formatCurrency(item.billedAmount)}
        </td>
        <td className="px-6 py-3 text-right">
          {item.benchmarkRate !== null ? (
            <div className="flex flex-col items-end">
              <span className="font-mono text-gray-500">{formatCurrency(item.benchmarkRate)}</span>
              {item.dataVintage && (
                <span className="text-[10px] leading-tight text-[#4A5568]">{item.dataVintage}</span>
              )}
            </div>
          ) : (
            <span className="font-mono text-gray-500">N/A</span>
          )}
        </td>
        <td className="px-6 py-3 text-right">
          {item.anomalyScore !== null ? (
            <div className="flex flex-col items-end">
              <span className={`font-mono font-semibold ${scoreColor}`}>
                {item.anomalyScore.toFixed(1)}x
              </span>
              <span className={`text-[10px] leading-tight ${plainLabel.color}`}>
                {plainLabel.text}
              </span>
            </div>
          ) : (
            <span className="text-gray-300">&mdash;</span>
          )}
        </td>
        <td className="px-6 py-3">
          {item.flagged && (
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                item.anomalyScore && item.anomalyScore > 3
                  ? "bg-red-100 text-red-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              <svg
                className="w-3 h-3"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.345 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 6a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 6Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
                  clipRule="evenodd"
                />
              </svg>
              Review
            </span>
          )}
        </td>
      </tr>
      {expanded && item.flagged && (
        <tr className="bg-amber-50/30">
          <td colSpan={6} className="px-6 py-4">
            <div className="text-sm space-y-1">
              <p className="text-gray-700">
                <span className="font-semibold">Flag reason:</span>{" "}
                {item.flagReason}
              </p>
              {item.benchmarkRate !== null && (
                <p className="text-gray-500">
                  <span className="font-semibold">Discrepancy:</span>{" "}
                  {formatCurrency(item.estimatedDiscrepancy)} over benchmark
                </p>
              )}
              <p className="text-[#4A5568] text-xs">
                Source: {item.benchmarkSource}
                {item.localityCode && ` (Locality ${item.localityCode})`}
              </p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Coding Intelligence Section
// ---------------------------------------------------------------------------

const CODING_EXPLANATIONS = {
  NCCI_EDIT:
    "These two procedures are normally included together as one charge under Medicare rules. Billing them separately may result in a higher total.",
  MUE_LIMIT:
    "This procedure was billed more times than Medicare considers typical for a single visit. Extra units may not be justified.",
  SITE_OF_SERVICE:
    "This procedure was billed at the higher hospital/facility rate, but it's commonly performed in an office setting at a lower cost.",
  EM_COMPLEXITY:
    "The office visit complexity level billed here is higher than what's typical for the services described. A lower-level visit code may be more appropriate.",
};

function CodingIntelligenceSection({ codingAlerts, codingSummary }) {
  if (!codingAlerts || codingAlerts.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          {/* Shield icon */}
          <svg
            className="w-5 h-5 text-[#1B3A5C]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
            />
          </svg>
          <div>
            <h3 className="text-lg font-bold text-[#1B3A5C]">
              Coding Pattern Analysis
            </h3>
            <p className="text-xs text-gray-500">
              Common billing patterns we check for
            </p>
          </div>
          {codingSummary && (
            <div className="ml-auto flex items-center gap-2">
              {codingSummary.highConfidenceCount > 0 && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                  {codingSummary.highConfidenceCount} Review
                </span>
              )}
              {codingSummary.mediumConfidenceCount > 0 && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  {codingSummary.mediumConfidenceCount} Info
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {codingAlerts.map((alert, i) => (
          <CodingAlertRow key={i} alert={alert} />
        ))}
      </div>

      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <p className="text-xs text-gray-400">
          Coding checks are based on CMS National Correct Coding Initiative and
          Medically Unlikely Edit rules. These are informational flags — consult
          with a certified coder for definitive guidance.
        </p>
      </div>
    </div>
  );
}

function CodingAlertRow({ alert }) {
  const [expanded, setExpanded] = useState(false);
  const isHigh = alert.confidence === "high";
  const explanation = CODING_EXPLANATIONS[alert.checkType];

  return (
    <div
      className="px-6 py-4 hover:bg-gray-50 cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-3">
        {/* Confidence badge */}
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium shrink-0 mt-0.5 ${
            isHigh
              ? "bg-amber-100 text-amber-700"
              : "bg-blue-100 text-blue-700"
          }`}
        >
          {isHigh ? "Review" : "Info"}
        </span>

        <div className="flex-1 min-w-0">
          {/* Check type + codes */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-[#1B3A5C]">
              {formatCheckType(alert.checkType)}
            </span>
            {alert.codes.map((code) => (
              <span
                key={code}
                className="font-mono text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600"
              >
                {code}
              </span>
            ))}
          </div>

          {/* Plain English explanation (always visible) */}
          {explanation && (
            <p className="text-sm text-gray-500 mt-1 leading-relaxed">{explanation}</p>
          )}

          {/* Expandable technical details */}
          {expanded && (
            <div className="mt-2 text-sm text-gray-600 leading-relaxed bg-gray-50 rounded-lg p-3">
              <p className="font-medium text-gray-700 mb-1">Technical detail</p>
              <p>{alert.message}</p>
              <p className="text-xs text-gray-400 mt-1">
                Source: {alert.source}
              </p>
            </div>
          )}
        </div>

        {/* Expand chevron */}
        <svg
          className={`w-4 h-4 text-gray-400 shrink-0 mt-1 transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m19.5 8.25-7.5 7.5-7.5-7.5"
          />
        </svg>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// What to do next
// ---------------------------------------------------------------------------

function WhatToDoNext({ billState, summary }) {
  if (billState === "clean") {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-bold text-[#1B3A5C] mb-3">
          What to do next
        </h3>
        <div className="flex items-start gap-3 p-4 bg-green-50 rounded-lg border border-green-200">
          <svg className="w-5 h-5 text-green-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <p className="text-sm text-gray-600 leading-relaxed">
            Your bill looks fairly priced. No action is needed — you can file this away with confidence. If you have questions about any specific charge, you can always call the provider's billing department and ask for an itemized explanation.
          </p>
        </div>
      </div>
    );
  }

  if (billState === "no_benchmarks") {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-lg font-bold text-[#1B3A5C] mb-3">
          What to do next
        </h3>
        <p className="text-sm text-gray-600 leading-relaxed">
          Since we couldn't benchmark the codes on this bill, we recommend requesting an itemized bill from the provider if you haven't already, and comparing charges with your insurance Explanation of Benefits (EOB). A medical billing advocate can also help review charges that seem unusually high.
        </p>
      </div>
    );
  }

  // significant or minor
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <h3 className="text-lg font-bold text-[#1B3A5C] mb-4">
        What to do next
      </h3>
      <div className="space-y-4">
        {/* Step 1 */}
        <div className="flex items-start gap-4">
          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-[#0D7377] text-white text-sm font-bold shrink-0">1</span>
          <div>
            <h4 className="font-semibold text-[#1B3A5C] text-sm">Download this report</h4>
            <p className="text-sm text-gray-500 leading-relaxed mt-0.5">
              Use the "Download Report" button at the top of this page. You'll want a copy of the benchmark comparisons when you contact the provider.
            </p>
          </div>
        </div>

        {/* Step 2 */}
        <div className="flex items-start gap-4">
          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-[#0D7377] text-white text-sm font-bold shrink-0">2</span>
          <div>
            <h4 className="font-semibold text-[#1B3A5C] text-sm">Call the billing department</h4>
            <p className="text-sm text-gray-500 leading-relaxed mt-0.5">
              Ask for an itemized explanation of the flagged charges. Mention that Medicare benchmarks for your area show lower rates for these procedures. Many billing departments will review and adjust charges when presented with specific data.
            </p>
          </div>
        </div>

        {/* Step 3 */}
        <div className="flex items-start gap-4">
          <span className="flex items-center justify-center w-7 h-7 rounded-full bg-[#0D7377] text-white text-sm font-bold shrink-0">3</span>
          <div>
            <h4 className="font-semibold text-[#1B3A5C] text-sm">Consider a billing advocate</h4>
            <p className="text-sm text-gray-500 leading-relaxed mt-0.5">
              If the provider won't adjust the charges, a medical billing advocate can negotiate on your behalf. They often work on contingency (they only get paid if they save you money).
            </p>
            <button className="mt-2 px-4 py-2 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer print:hidden">
              Find a Specialist
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCheckType(checkType) {
  const labels = {
    NCCI_EDIT: "Bundled Procedure",
    MUE_LIMIT: "Unusual Quantity",
    EM_COMPLEXITY: "Visit Level Question",
    SITE_OF_SERVICE: "Facility vs. Office Rate",
  };
  return labels[checkType] || checkType;
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

function getScoreColor(score) {
  if (score === null) return "text-gray-400";
  if (score > 3) return "text-red-600";
  if (score > 2) return "text-amber-600";
  if (score > 1.5) return "text-yellow-600";
  return "text-[#0D7377]";
}

function getScorePlainLabel(score) {
  if (score === null) return { text: "No benchmark", color: "text-gray-400" };
  if (score > 3) return { text: "Very high", color: "text-red-500" };
  if (score > 2) return { text: "High", color: "text-amber-500" };
  if (score > 1.5) return { text: "Above average", color: "text-yellow-500" };
  if (score >= 0.8) return { text: "Normal range", color: "text-green-500" };
  return { text: "Below benchmark", color: "text-gray-400" };
}
