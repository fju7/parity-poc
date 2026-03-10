import { useCallback, useState } from "react";

export default function UploadView({ onFileSelect, onSampleBill, onManualEntry, onHavingTrouble, onDenialAnalysis }) {
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file && file.type === "application/pdf") {
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleFileInput = useCallback(
    (e) => {
      const file = e.target.files[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect]
  );

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="w-full max-w-2xl text-center">
        {/* Logo */}
        <h1 className="text-6xl font-bold text-[#1B3A5C] mb-2 tracking-tight">
          Parity Health
        </h1>
        <p className="text-lg text-gray-500 mb-12">
          Bill Analysis
        </p>

        {/* Drop zone */}
        <label
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`block border-3 border-dashed rounded-2xl p-16 cursor-pointer transition-all duration-200 ${
            dragOver
              ? "border-[#0D7377] bg-teal-50 scale-[1.01]"
              : "border-[#0D7377]/40 hover:border-[#0D7377] hover:bg-gray-50"
          }`}
        >
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileInput}
          />
          <div className="flex flex-col items-center gap-4">
            <svg
              className="w-16 h-16 text-[#0D7377]/60"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
              />
            </svg>
            <div>
              <p className="text-xl font-semibold text-[#1B3A5C]">
                Drop your itemized bill here
              </p>
              <p className="text-sm text-gray-400 mt-1">
                PDF format &middot; or click to browse
              </p>
            </div>
          </div>
        </label>

        {/* Action links */}
        <div className="mt-6 flex flex-col items-center gap-2">
          {onSampleBill && (
            <button
              onClick={onSampleBill}
              className="text-[#0D7377] font-medium hover:underline cursor-pointer text-sm"
            >
              Try a Sample Bill
            </button>
          )}
          <div className="flex items-center gap-4">
            {onManualEntry && (
              <button
                onClick={onManualEntry}
                className="text-gray-500 hover:text-[#1B3A5C] cursor-pointer text-sm"
              >
                Enter Manually
              </button>
            )}
            {onHavingTrouble && (
              <button
                onClick={onHavingTrouble}
                className="text-gray-400 hover:text-gray-600 cursor-pointer text-xs"
              >
                Having trouble?
              </button>
            )}
          </div>
        </div>

        {/* Denial analysis entry point */}
        {onDenialAnalysis && (
          <div className="mt-8 pt-6 border-t border-gray-200">
            <button
              onClick={onDenialAnalysis}
              className="text-[#0D7377] font-medium hover:underline cursor-pointer text-sm flex items-center gap-1.5 mx-auto"
            >
              Received a denial? Analyze it here
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
            </button>
          </div>
        )}

        {/* Privacy points */}
        <div className="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-6 text-left">
          <PrivacyPoint
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 17.25v1.007a3 3 0 0 1-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0 1 15 18.257V17.25m6-12V15a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 15V5.25m18 0A2.25 2.25 0 0 0 18.75 3H5.25A2.25 2.25 0 0 0 3 5.25m18 0V12a9 9 0 0 1-9 9m0 0a9 9 0 0 1-9-9"
              />
            }
            title="Stays on your device"
            text="Your document never leaves your browser."
          />
          <PrivacyPoint
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"
              />
            }
            title="Only codes analyzed"
            text="Only procedure codes are sent to the cloud."
          />
          <PrivacyPoint
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
              />
            }
            title="No personal data"
            text="No names, dates, or diagnoses are transmitted."
          />
        </div>

        {/* Disclaimer */}
        <p className="mt-10 text-xs text-gray-400 max-w-lg mx-auto leading-relaxed">
          Parity Health provides benchmark comparisons only. This is not legal advice.
          Consult a billing specialist or attorney before taking action.
        </p>
      </div>

      <Footer />
    </div>
  );
}

function PrivacyPoint({ icon, title, text }) {
  return (
    <div className="flex items-start gap-3">
      <svg
        className="w-6 h-6 text-[#0D7377] shrink-0 mt-0.5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.5}
      >
        {icon}
      </svg>
      <div>
        <p className="text-sm font-semibold text-[#1B3A5C]">{title}</p>
        <p className="text-xs text-gray-500">{text}</p>
      </div>
    </div>
  );
}

export function Footer() {
  return (
    <footer className="w-full text-center py-6 mt-auto">
      <p className="text-xs text-gray-400">
        Parity Health is powered by CivicScale benchmark infrastructure.
        Benchmark comparisons use publicly available CMS Medicare data.
        Not legal advice. &copy; CivicScale 2026.
      </p>
    </footer>
  );
}
