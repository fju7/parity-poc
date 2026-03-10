import { useCallback, useState, useRef } from "react";
import { Footer } from "./UploadView.jsx";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function DenialUploadView({ onAnalysisComplete, onBack }) {
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  const handleFileSelect = useCallback(async (f) => {
    if (!f) return;
    setFile(f);
    setError(null);

    // Read PDF as text via FileReader — for now we just extract text client-side
    // The backend accepts raw text, so users can also paste directly
    if (f.type === "application/pdf") {
      // We can't extract PDF text client-side without a lib, so tell user to paste
      setError("PDF detected — please copy and paste the denial letter text below for best results.");
      setFile(null);
      return;
    }

    // For text files, read directly
    const reader = new FileReader();
    reader.onload = (e) => setText(e.target.result);
    reader.readAsText(f);
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!text.trim() || text.trim().length < 20) {
      setError("Please paste at least a paragraph of the denial letter or EOB.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/health/analyze-denial`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.trim() }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Analysis failed. Please try again.");
      }

      const analysis = await res.json();
      onAnalysisComplete(analysis, text.trim());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [text, onAnalysisComplete]);

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="w-full max-w-2xl">
        {/* Back button */}
        {onBack && (
          <button
            onClick={onBack}
            className="mb-8 text-sm text-[#0D7377] hover:underline cursor-pointer flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Bill Analysis
          </button>
        )}

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-[#1B3A5C] mb-3 tracking-tight">
            Denial Appeal Assistant
          </h1>
          <p className="text-lg text-gray-500 max-w-lg mx-auto leading-relaxed">
            Insurance denied your claim? Let's find out why — and what you can do about it.
          </p>
        </div>

        {/* Text area */}
        <div className="mb-6">
          <label className="block text-sm font-semibold text-[#1B3A5C] mb-2">
            Paste your denial letter or EOB text
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={"Paste the full text of your denial letter, Explanation of Benefits (EOB), or denial notification here...\n\nInclude as much detail as possible — the reason code, the specific language they used, any deadlines mentioned."}
            className="w-full h-64 p-4 border-2 border-gray-200 rounded-xl text-sm text-gray-700 leading-relaxed resize-y focus:outline-none focus:border-[#0D7377] transition-colors"
          />
          <p className="text-xs text-gray-400 mt-1">
            Your text is sent securely for analysis and is not stored.
          </p>
        </div>

        {/* File upload alternative */}
        <div className="mb-6 text-center">
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.text"
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files[0])}
          />
          <button
            onClick={() => fileRef.current?.click()}
            className="text-sm text-gray-500 hover:text-[#0D7377] cursor-pointer"
          >
            Or upload a text file
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={loading || text.trim().length < 20}
          className={`w-full py-4 rounded-xl text-lg font-semibold transition-all ${
            loading || text.trim().length < 20
              ? "bg-gray-200 text-gray-400 cursor-not-allowed"
              : "bg-[#0D7377] text-white hover:bg-[#0B6164] cursor-pointer"
          }`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Analyzing your denial...
            </span>
          ) : (
            "Analyze Denial"
          )}
        </button>

        {/* Privacy note */}
        <div className="mt-8 flex items-start gap-3 bg-gray-50 rounded-xl p-4">
          <svg className="w-5 h-5 text-[#0D7377] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
          </svg>
          <div>
            <p className="text-sm font-semibold text-[#1B3A5C]">Your privacy matters</p>
            <p className="text-xs text-gray-500 mt-0.5">
              The text you provide is sent securely for one-time analysis and is not stored on our servers.
              We recommend removing any Social Security numbers before pasting.
            </p>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
