import { useCallback, useState, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function UploadView({
  onFileSelect,
  onSampleBill,
  onManualEntry,
  onHavingTrouble,
  onDenialAnalysis,
  onSbcClassified,
  onDenialClassified,
  sbcData,
  onSbcLoaded,
  onSbcClear,
}) {
  const [dragOver, setDragOver] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [classifyError, setClassifyError] = useState(null);
  const [showSbcReplace, setShowSbcReplace] = useState(false);
  const pendingSbcFileRef = useRef(null);

  const classifyAndRoute = useCallback(
    async (file) => {
      setClassifyError(null);

      const fname = file.name.toLowerCase();

      // Reject EDI/claims files
      const ext = fname.split(".").pop().toUpperCase();
      if (["EDI", "837", "835"].includes(ext)) {
        setClassifyError(
          "This looks like an EDI claims file. Parity Health works with medical bills, EOBs, denial letters, and insurance plan summaries. Please upload one of those instead."
        );
        return;
      }

      // TXT files — read as text and send to bill analysis
      if (fname.endsWith(".txt")) {
        const text = await file.text();
        onFileSelect(file);
        return;
      }

      // All other non-PDF files
      if (!fname.endsWith(".pdf") && !["jpg","jpeg","png","webp"].includes(ext.toLowerCase())) {
        setClassifyError("Please upload a PDF, JPG, or PNG file.");
        return;
      }

      setClassifying(true);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(`${API_BASE}/api/health/classify-document`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Classification failed.");
        }

        const result = await res.json();
        const docType = result.document_type;

        if (docType === "unsupported_format") {
          setClassifyError(result.reason);
          setClassifying(false);
          return;
        }

        if (docType === "sbc") {
          // If SBC already loaded, ask to replace
          if (sbcData) {
            pendingSbcFileRef.current = file;
            setShowSbcReplace(true);
            setClassifying(false);
            return;
          }
          // Upload as SBC
          await uploadSbc(file);
          setClassifying(false);
          return;
        }

        if (docType === "denial_letter") {
          // Route to denial flow — pass the file to App.jsx
          setClassifying(false);
          if (onDenialClassified) {
            onDenialClassified(file);
          } else if (onDenialAnalysis) {
            onDenialAnalysis();
          }
          return;
        }

        // medical_bill, eob, or unknown with decent confidence → bill pipeline
        setClassifying(false);
        onFileSelect(file);
      } catch (err) {
        console.error("Classification error:", err);
        setClassifying(false);
        // On classification failure, fall back to bill analysis
        onFileSelect(file);
      }
    },
    [sbcData, onFileSelect, onDenialAnalysis, onDenialClassified, onSbcLoaded]
  );

  const uploadSbc = useCallback(
    async (file) => {
      setClassifying(true);
      setClassifyError(null);
      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch(`${API_BASE}/api/health/analyze-sbc`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || "Failed to analyze SBC.");
        }

        const data = await res.json();
        onSbcLoaded(data);
      } catch (err) {
        setClassifyError(err.message || "Failed to read plan document.");
      } finally {
        setClassifying(false);
      }
    },
    [onSbcLoaded]
  );

  const handleSbcReplaceConfirm = useCallback(async () => {
    setShowSbcReplace(false);
    const file = pendingSbcFileRef.current;
    if (file) {
      await uploadSbc(file);
      pendingSbcFileRef.current = null;
    }
  }, [uploadSbc]);

  const handleSbcReplaceCancel = useCallback(() => {
    setShowSbcReplace(false);
    pendingSbcFileRef.current = null;
  }, []);

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
      if (file) classifyAndRoute(file);
    },
    [classifyAndRoute]
  );

  const handleFileInput = useCallback(
    (e) => {
      const file = e.target.files[0];
      if (file) classifyAndRoute(file);
      // Reset so the same file can be re-selected
      e.target.value = "";
    },
    [classifyAndRoute]
  );

  const formatCurrency = (val) => {
    if (val == null) return "—";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="w-full max-w-2xl text-center">
        {/* Logo */}
        <h1 className="text-6xl font-bold text-[#1B3A5C] mb-2 tracking-tight">
          Parity Health
        </h1>
        <p className="text-lg text-gray-500 mb-10">
          Bill Analysis
        </p>

        {/* SBC plan summary card — shown ABOVE the drop zone when loaded */}
        {sbcData && (
          <div className="mb-6 bg-white border-2 border-green-200 rounded-xl p-5 text-left relative">
            <button
              onClick={onSbcClear}
              className="absolute top-3 right-3 w-6 h-6 flex items-center justify-center rounded-full text-gray-400 hover:text-gray-600 hover:bg-gray-100 cursor-pointer"
              title="Clear plan"
            >
              &times;
            </button>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
                &#10003; Plan Loaded
              </span>
              <span className="text-sm font-semibold text-[#1B3A5C]">
                {sbcData.plan_name || "Your Plan"}
              </span>
              {sbcData.plan_year && (
                <span className="text-xs text-gray-400">{sbcData.plan_year}</span>
              )}
            </div>
            <p className="text-xs text-gray-500 mb-3">
              Your plan details are loaded. When you analyze a bill, we'll estimate what you actually owe based on your deductible, copays, and coinsurance.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div>
                <p className="text-gray-400">Deductible</p>
                <p className="font-semibold text-[#1B3A5C]">{formatCurrency(sbcData.deductible_individual)}</p>
              </div>
              <div>
                <p className="text-gray-400">OOP Max</p>
                <p className="font-semibold text-[#1B3A5C]">{formatCurrency(sbcData.oop_max_individual)}</p>
              </div>
              <div>
                <p className="text-gray-400">PCP Copay</p>
                <p className="font-semibold text-[#1B3A5C]">{formatCurrency(sbcData.primary_care_copay)}</p>
              </div>
              <div>
                <p className="text-gray-400">Coinsurance</p>
                <p className="font-semibold text-[#1B3A5C]">
                  {sbcData.coinsurance_in_network != null ? `${sbcData.coinsurance_in_network}%` : "—"}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Unified drop zone */}
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
            accept="application/pdf,image/*,text/plain,.txt"
            className="hidden"
            onChange={handleFileInput}
          />

          {classifying ? (
            <div className="flex flex-col items-center gap-4">
              <svg
                className="animate-spin h-12 w-12 text-[#0D7377]"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <p className="text-lg font-semibold text-[#0D7377]">
                Identifying document...
              </p>
              <p className="text-sm text-gray-400">
                We're figuring out what you uploaded so we can route it correctly.
              </p>
            </div>
          ) : (
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
                  Drop any medical document here
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  Bills, EOBs, denial letters, or plan summaries &middot; PDF, JPG, PNG, or TXT
                </p>
              </div>
            </div>
          )}
        </label>

        {/* Classification error */}
        {classifyError && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 text-left">
            <p className="text-sm text-red-700">{classifyError}</p>
          </div>
        )}

        {/* SBC replacement dialog */}
        {showSbcReplace && (
          <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg p-4 text-left">
            <p className="text-sm font-semibold text-amber-800 mb-2">
              Replace your current plan summary?
            </p>
            <p className="text-xs text-amber-700 mb-3">
              You already have <strong>{sbcData?.plan_name || "a plan"}</strong> loaded.
              Uploading a new SBC will replace it.
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleSbcReplaceConfirm}
                className="px-4 py-1.5 bg-amber-600 text-white text-sm rounded-lg hover:bg-amber-700 cursor-pointer"
              >
                Replace
              </button>
              <button
                onClick={handleSbcReplaceCancel}
                className="px-4 py-1.5 bg-white border border-gray-300 text-sm text-gray-700 rounded-lg hover:bg-gray-50 cursor-pointer"
              >
                Keep Current
              </button>
            </div>
          </div>
        )}

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
