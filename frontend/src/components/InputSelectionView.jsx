import { useCallback, useState, useRef } from "react";
import { Footer } from "./UploadView.jsx";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function InputSelectionView({
  onFileSelect,
  onPasteText,
  onImageUpload,
  onSampleBill,
  onManualEntry,
  onDenialClassified,
  onDenialAnalysis,
  onSbcClassified,
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
      if (!fname.endsWith(".pdf")) {
        const ext = fname.split(".").pop().toUpperCase();
        if (["TXT", "EDI", "837", "835"].includes(ext)) {
          setClassifyError(
            `${ext} files are clinical data formats used by providers and insurers. Please upload a PDF of your bill, EOB, denial letter, or plan summary.`
          );
        } else {
          setClassifyError("Please upload a PDF file.");
        }
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
          if (sbcData) {
            pendingSbcFileRef.current = file;
            setShowSbcReplace(true);
            setClassifying(false);
            return;
          }
          await uploadSbc(file);
          setClassifying(false);
          return;
        }

        if (docType === "denial_letter") {
          setClassifying(false);
          if (onDenialClassified) {
            onDenialClassified(file);
          } else if (onDenialAnalysis) {
            onDenialAnalysis();
          }
          return;
        }

        // medical_bill, eob, unknown → bill pipeline
        setClassifying(false);
        onFileSelect(file);
      } catch (err) {
        console.error("Classification error:", err);
        setClassifying(false);
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

        {/* SBC plan summary — shown ABOVE input options when loaded */}
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

        {/* Classification spinner overlay OR input option cards */}
        {classifying ? (
          <div className="flex flex-col items-center gap-4 py-16">
            <svg
              className="animate-spin h-12 w-12 text-[#0D7377]"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-lg font-semibold text-[#0D7377]">Identifying document...</p>
            <p className="text-sm text-gray-400">We're figuring out what you uploaded so we can route it correctly.</p>
          </div>
        ) : (
          <>
            {/* Input option cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              {/* Upload PDF — now with auto-classification */}
              <label
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`group flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-dashed cursor-pointer transition-all duration-200 ${
                  dragOver
                    ? "border-[#0D7377] bg-teal-50 scale-[1.02]"
                    : "border-gray-200 hover:border-[#0D7377] hover:bg-gray-50"
                }`}
              >
                <input
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={handleFileInput}
                />
                <div className="w-12 h-12 rounded-full bg-[#0D7377]/10 flex items-center justify-center group-hover:bg-[#0D7377]/20 transition-colors">
                  <svg className="w-6 h-6 text-[#0D7377]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12-3-3m0 0-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-[#1B3A5C]">Upload PDF</p>
                  <p className="text-xs text-gray-400 mt-0.5">Any medical document</p>
                </div>
              </label>

              {/* Paste Text */}
              <button
                onClick={onPasteText}
                className="group flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-dashed border-gray-200 hover:border-[#0D7377] hover:bg-gray-50 cursor-pointer transition-all duration-200"
              >
                <div className="w-12 h-12 rounded-full bg-[#0D7377]/10 flex items-center justify-center group-hover:bg-[#0D7377]/20 transition-colors">
                  <svg className="w-6 h-6 text-[#0D7377]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-[#1B3A5C]">Paste Text</p>
                  <p className="text-xs text-gray-400 mt-0.5">From portal or email</p>
                </div>
              </button>

              {/* Take Photo / Upload Image */}
              <button
                onClick={onImageUpload}
                className="group flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-dashed border-gray-200 hover:border-[#0D7377] hover:bg-gray-50 cursor-pointer transition-all duration-200"
              >
                <div className="w-12 h-12 rounded-full bg-[#0D7377]/10 flex items-center justify-center group-hover:bg-[#0D7377]/20 transition-colors">
                  <svg className="w-6 h-6 text-[#0D7377]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-semibold text-[#1B3A5C]">Photo / Image</p>
                  <p className="text-xs text-gray-400 mt-0.5">Screenshot or camera</p>
                </div>
              </button>
            </div>
          </>
        )}

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
        {!classifying && (
          <div className="flex flex-col items-center gap-2">
            {onSampleBill && (
              <button
                onClick={onSampleBill}
                className="text-[#0D7377] font-medium hover:underline cursor-pointer text-sm"
              >
                Try a Sample Bill
              </button>
            )}
            {onManualEntry && (
              <button
                onClick={onManualEntry}
                className="text-gray-500 hover:text-[#1B3A5C] cursor-pointer text-sm"
              >
                Enter Manually
              </button>
            )}
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
