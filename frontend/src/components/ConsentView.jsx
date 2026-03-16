import { useState } from "react";
import { Footer } from "./UploadView.jsx";

import { API_BASE } from "../lib/apiBase";
export default function ConsentView({ onSubmit }) {
  const [consentAnalytics, setConsentAnalytics] = useState(true);
  const [consentEmployer, setConsentEmployer] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  // Employer code state
  const [employerCode, setEmployerCode] = useState("");
  const [employerCompany, setEmployerCompany] = useState("");
  const [codeStatus, setCodeStatus] = useState("idle"); // idle | verifying | valid | invalid

  const verifyCode = async (code) => {
    if (!code.trim()) return;
    setCodeStatus("verifying");
    try {
      const res = await fetch(`${API_BASE}/api/employer/verify-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code.trim() }),
      });
      const data = await res.json();
      if (data.valid) {
        setEmployerCompany(data.company_name);
        setCodeStatus("valid");
      } else {
        setCodeStatus("invalid");
      }
    } catch {
      setCodeStatus("invalid");
    }
  };

  const handleContinue = () => {
    if (!agreedToTerms) return;
    onSubmit({
      consentAnalytics,
      consentEmployer,
      employerCode: consentEmployer && codeStatus === "valid" ? employerCode.trim() : null,
    });
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="w-full max-w-lg">
        {/* Header */}
        <h1 className="text-2xl font-bold text-[#1B3A5C] mb-2 text-center">
          Before we get started
        </h1>
        <p className="text-gray-500 mb-8 text-center">
          Please review how Parity Health handles your data
        </p>

        {/* Cards */}
        <div className="space-y-4 mb-8">
          {/* 1. Health data stays on device — always on */}
          <div className="flex items-start gap-4 p-4 border border-gray-200 rounded-xl bg-gray-50">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#0D7377]/10 flex items-center justify-center mt-0.5">
              <svg className="w-5 h-5 text-[#0D7377]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <p className="font-medium text-[#1B3A5C]">Your health data stays on this device</p>
                <span className="text-xs font-medium text-[#0D7377] bg-[#0D7377]/10 px-2 py-0.5 rounded-full">
                  Always on
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Bill details, line items, and analysis results are stored locally in your browser. They are never uploaded to our servers.
              </p>
            </div>
          </div>

          {/* 2. Analytics — toggle, default on */}
          <div className="flex items-start gap-4 p-4 border border-gray-200 rounded-xl">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#1B3A5C]/10 flex items-center justify-center mt-0.5">
              <svg className="w-5 h-5 text-[#1B3A5C]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <p className="font-medium text-[#1B3A5C]">Help improve Parity Health</p>
                <Toggle checked={consentAnalytics} onChange={setConsentAnalytics} />
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Share anonymized, aggregate usage data so we can improve accuracy and detect new billing patterns. No personal health information is included.
              </p>
            </div>
          </div>

          {/* 3. Employer dashboard — toggle, default off */}
          <div className="flex items-start gap-4 p-4 border border-gray-200 rounded-xl">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#1B3A5C]/10 flex items-center justify-center mt-0.5">
              <svg className="w-5 h-5 text-[#1B3A5C]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <p className="font-medium text-[#1B3A5C]">Contribute to employer dashboard</p>
                <Toggle checked={consentEmployer} onChange={setConsentEmployer} />
              </div>
              <p className="text-sm text-gray-500 mt-1">
                If your employer partners with Parity Health, allow de-identified billing trends to appear on their benefits dashboard. You can change this anytime.
              </p>

              {/* Employer code input — shown when toggle is on */}
              {consentEmployer && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <label className="block text-xs font-medium text-[#1B3A5C] mb-1.5">
                    Employer Code <span className="text-gray-400 font-normal">(optional)</span>
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={employerCode}
                      onChange={(e) => {
                        setEmployerCode(e.target.value.toUpperCase());
                        if (codeStatus === "invalid") setCodeStatus("idle");
                      }}
                      onBlur={() => { if (employerCode.trim()) verifyCode(employerCode); }}
                      placeholder="e.g. ACME-2847"
                      className="flex-1 px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
                    />
                  </div>
                  {codeStatus === "verifying" && (
                    <p className="text-xs text-gray-400 mt-1">Checking...</p>
                  )}
                  {codeStatus === "valid" && (
                    <p className="text-xs text-[#0D7377] mt-1 flex items-center gap-1">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                      </svg>
                      {employerCompany}
                    </p>
                  )}
                  {codeStatus === "invalid" && (
                    <p className="text-xs text-red-500 mt-1">Code not recognized</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    Ask your benefits team for this code. You can also add it later in Settings.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Terms checkbox */}
        <label className="flex items-start gap-3 mb-6 cursor-pointer">
          <input
            type="checkbox"
            checked={agreedToTerms}
            onChange={(e) => setAgreedToTerms(e.target.checked)}
            className="mt-1 h-4 w-4 rounded border-gray-300 text-[#0D7377] focus:ring-[#0D7377] cursor-pointer accent-[#0D7377]"
          />
          <span className="text-sm text-gray-600">
            I have read and agree to the{" "}
            <a href="/terms" target="_blank" rel="noopener noreferrer" className="text-[#0D7377] underline">Terms of Service</a>{" "}
            and{" "}
            <a href="/privacy" target="_blank" rel="noopener noreferrer" className="text-[#0D7377] underline">Privacy Policy</a>
          </span>
        </label>

        {/* Continue button */}
        <button
          onClick={handleContinue}
          disabled={!agreedToTerms}
          className={`w-full py-3 text-sm font-medium text-white rounded-lg cursor-pointer ${
            agreedToTerms
              ? "bg-[#0D7377] hover:bg-[#0B6164]"
              : "bg-gray-300 cursor-not-allowed"
          }`}
        >
          Continue
        </button>
      </div>

      <Footer />
    </div>
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out cursor-pointer focus:outline-none ${
        checked ? "bg-[#0D7377]" : "bg-gray-200"
      }`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}
