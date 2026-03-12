import { useState, useCallback } from "react";
import { Footer } from "./UploadView.jsx";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const DENIAL_TYPE_COLORS = {
  clinical: { bg: "bg-purple-50", border: "border-purple-200", text: "text-purple-700", label: "Clinical Denial" },
  administrative: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", label: "Administrative Denial" },
  coverage: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", label: "Coverage Denial" },
  other: { bg: "bg-gray-50", border: "border-gray-200", text: "text-gray-700", label: "Other Denial" },
};

export default function DenialReportView({ analysis, originalText, onReset, onBack }) {
  const [patientName, setPatientName] = useState("");
  const [providerName, setProviderName] = useState("");
  const [claimNumber, setClaimNumber] = useState("");
  const [letterText, setLetterText] = useState(null);
  const [letterLoading, setLetterLoading] = useState(false);
  const [letterError, setLetterError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [appealOpen, setAppealOpen] = useState(false);

  const typeConfig = DENIAL_TYPE_COLORS[analysis.denial_type] || DENIAL_TYPE_COLORS.other;

  const handleGenerateAppeal = useCallback(async () => {
    setLetterLoading(true);
    setLetterError(null);

    try {
      const res = await fetch(`${API_BASE}/api/health/generate-appeal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          denial_analysis: analysis,
          patient_name: patientName.trim() || null,
          provider_name: providerName.trim() || null,
          claim_number: claimNumber.trim() || null,
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to generate appeal letter. Please try again.");
      }

      const data = await res.json();
      setLetterText(data.letter_text);
    } catch (err) {
      setLetterError(err.message);
    } finally {
      setLetterLoading(false);
    }
  }, [analysis, patientName, providerName, claimNumber]);

  const handleCopy = useCallback(() => {
    if (!letterText) return;
    navigator.clipboard.writeText(letterText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [letterText]);

  const handlePrintLetter = useCallback(() => {
    window.print();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-[Arial,sans-serif]">
      {/* Print-only header */}
      <div className="hidden print:block px-4 pt-4 pb-2 border-b border-gray-300 mb-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-[#1B3A5C] tracking-tight">Parity Health</h1>
          <p className="text-sm text-gray-500">
            Denial Analysis — {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-4 py-8 w-full flex-1">
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
              Analyze Another Denial
            </button>
          )}
          {onBack && (
            <button
              onClick={onBack}
              className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-[#1B3A5C] cursor-pointer"
            >
              Back to Bill Analysis
            </button>
          )}
        </div>

        {/* Denial Type Badge + Confidence */}
        <div className={`${typeConfig.bg} border ${typeConfig.border} rounded-xl p-5 mb-6`}>
          <div className="flex items-center gap-3 mb-2">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${typeConfig.bg} ${typeConfig.text} border ${typeConfig.border}`}>
              {typeConfig.label}
            </span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              analysis.confidence === "high" ? "bg-green-100 text-green-700" :
              analysis.confidence === "medium" ? "bg-amber-100 text-amber-700" :
              "bg-gray-100 text-gray-600"
            }`}>
              {analysis.confidence} confidence
            </span>
          </div>
          <h2 className="text-xl font-bold text-[#1B3A5C] mb-2">Why Your Claim Was Denied</h2>
          <p className="text-gray-700 leading-relaxed">{analysis.denial_reason_plain}</p>
          {analysis.denial_reason_code && (
            <p className="text-sm text-gray-500 mt-2">
              Reason code: <span className="font-mono font-semibold">{analysis.denial_reason_code}</span>
            </p>
          )}
        </div>

        {/* What They Cited */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-bold text-[#1B3A5C] mb-3">What They Cited</h3>
          <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 rounded-lg p-4 border border-gray-100">
            {analysis.specific_criterion}
          </p>
        </div>

        {/* Weakness — only if present, prominently displayed */}
        {analysis.weakness && (
          <div className="bg-amber-50 border-2 border-amber-300 rounded-xl p-6 mb-6">
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
              </svg>
              <h3 className="text-lg font-bold text-amber-800">Weakness in Their Reasoning</h3>
            </div>
            <p className="text-sm text-amber-900 leading-relaxed font-medium">
              {analysis.weakness}
            </p>
            <p className="text-xs text-amber-700 mt-3">
              This may be your strongest argument in an appeal.
            </p>
          </div>
        )}

        {/* Supporting Documentation Checklist */}
        {analysis.supporting_documentation && analysis.supporting_documentation.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <h3 className="text-lg font-bold text-[#1B3A5C] mb-3">What to Include in Your Appeal</h3>
            <p className="text-sm text-gray-500 mb-4">Gather these documents before filing your appeal:</p>
            <ul className="space-y-2">
              {analysis.supporting_documentation.map((doc, i) => (
                <li key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                  <input type="checkbox" className="mt-0.5 accent-[#0D7377]" />
                  <span className="text-sm text-gray-700">{doc}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Appeal Deadline */}
        {analysis.appeal_deadline_hint && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-6 flex items-start gap-3">
            <svg className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <div>
              <h4 className="font-semibold text-amber-800 text-sm">Appeal Deadline</h4>
              <p className="text-sm text-amber-700 mt-0.5">{analysis.appeal_deadline_hint}</p>
            </div>
          </div>
        )}

        {/* Fight This Denial — Collapsible Section */}
        <div className="rounded-xl border-2 border-[#0D7377] overflow-hidden mb-6 print:hidden">
          <button
            onClick={() => setAppealOpen(!appealOpen)}
            className="w-full flex items-center justify-between px-6 py-4 bg-[#0D7377]/5 hover:bg-[#0D7377]/10 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <svg className="w-6 h-6 text-[#0D7377]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
              </svg>
              <h3 className="text-lg font-bold text-[#0D7377]">Fight This Denial</h3>
            </div>
            <svg
              className={`w-5 h-5 text-[#0D7377] transition-transform duration-200 ${appealOpen ? "rotate-180" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          </button>

          {appealOpen && (
            <div className="px-6 py-6 bg-white border-t border-[#0D7377]/20">
              <p className="text-sm text-gray-500 mb-5">
                We'll draft a professional appeal letter based on the denial analysis above.
                Fill in the optional fields to personalize it.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Patient Name <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    value={patientName}
                    onChange={(e) => setPatientName(e.target.value)}
                    placeholder="e.g. Jane Smith"
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]/30"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Provider Name <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    value={providerName}
                    onChange={(e) => setProviderName(e.target.value)}
                    placeholder="e.g. Dr. Johnson or Memorial Hospital"
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]/30"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    Claim Number <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    value={claimNumber}
                    onChange={(e) => setClaimNumber(e.target.value)}
                    placeholder="e.g. CLM-2024-12345"
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]/30"
                  />
                </div>
              </div>

              <button
                onClick={handleGenerateAppeal}
                disabled={letterLoading}
                className={`px-6 py-3 rounded-xl font-semibold transition-all ${
                  letterLoading
                    ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                    : "bg-[#0D7377] text-white hover:bg-[#0B6164] cursor-pointer"
                }`}
              >
                {letterLoading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Drafting your appeal letter...
                  </span>
                ) : (
                  "Generate Appeal Letter"
                )}
              </button>

              {letterError && (
                <p className="text-sm text-red-600 mt-3">{letterError}</p>
              )}
            </div>
          )}
        </div>

        {/* Appeal Letter Display */}
        {letterText && (
          <div className="rounded-xl border border-gray-200 overflow-hidden mb-6 appeal-letter-print">
            <div className="flex items-center justify-between px-6 py-4 bg-gray-50 border-b border-gray-200 print:hidden">
              <h3 className="text-lg font-bold text-[#1B3A5C]">Your Appeal Letter</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className={`px-4 py-2 text-sm font-medium rounded-lg cursor-pointer transition-all ${
                    copied
                      ? "bg-green-100 text-green-700 border border-green-300"
                      : "text-[#0D7377] border border-[#0D7377] hover:bg-teal-50"
                  }`}
                >
                  {copied ? "Copied!" : "Copy Letter"}
                </button>
                <button
                  onClick={handlePrintLetter}
                  className="px-4 py-2 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
                >
                  Download as PDF
                </button>
              </div>
            </div>
            <div className="bg-white p-8">
              <pre className="whitespace-pre-wrap text-[15px] text-gray-800 leading-[1.7] font-[Arial,sans-serif]">
                {letterText}
              </pre>
            </div>
            <div className="px-6 py-3 bg-amber-50 border-t border-amber-200 print:hidden">
              <p className="text-xs text-amber-700">
                This letter is a starting point. Review it carefully and add any additional medical
                documentation before sending.
              </p>
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <div className="text-xs text-gray-400 text-center mb-4 space-y-2">
          <p>
            This analysis and appeal letter are generated by AI and are for informational purposes only.
            This is not legal advice. Review all content carefully before submitting. Consult a medical
            billing advocate or attorney for complex cases.
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
}
