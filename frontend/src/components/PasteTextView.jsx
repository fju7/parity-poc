import { useState, useCallback } from "react";
import { Footer } from "./UploadView.jsx";

export default function PasteTextView({ onSubmit, onBack }) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed) return;

    if (trimmed.length < 20) {
      setError("Please paste more of your bill text for accurate analysis.");
      return;
    }

    setError("");
    setSubmitting(true);
    try {
      await onSubmit(trimmed);
    } catch {
      setSubmitting(false);
      setError("Something went wrong. Please try again.");
    }
  }, [text, onSubmit]);

  return (
    <div className="min-h-screen bg-white flex flex-col items-center px-4 pt-12 font-[Arial,sans-serif]">
      <div className="w-full max-w-2xl">
        {/* Back link */}
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#1B3A5C] cursor-pointer mb-6"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          Back
        </button>

        <h2 className="text-2xl font-bold text-[#1B3A5C] mb-1">
          Paste Your Bill Text
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          Copy and paste the text from your itemized bill, patient portal, or email.
        </p>

        {/* Textarea */}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste your itemized bill text here..."
          rows={14}
          className="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377] placeholder-gray-400 font-mono"
        />

        {/* Character count */}
        <div className="flex items-center justify-between mt-2 mb-4">
          <p className="text-xs text-gray-400">
            {text.length > 0 ? `${text.length.toLocaleString()} characters` : ""}
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Privacy note */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-6">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            <p className="text-xs text-amber-800">
              Your bill text will be sent to our AI service for extraction. Only procedure codes and amounts are used for benchmark analysis. No personal health information is stored.
            </p>
          </div>
        </div>

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={!text.trim() || submitting}
          className="w-full py-3 text-sm font-semibold text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? "Analyzing..." : "Analyze Bill"}
        </button>
      </div>

      <Footer />
    </div>
  );
}
