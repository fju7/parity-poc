import { useState, useEffect } from "react";
import { Footer } from "./UploadView.jsx";

const STEPS = [
  "Reading your document...",
  "Looking up benchmark rates...",
  "Analyzing charges...",
  "Checking coding patterns...",
];

export default function ProcessingView({ currentStep = 0, slowServer = false }) {
  const [dots, setDots] = useState("");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "" : d + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-[#1B3A5C] mb-12 tracking-tight">
          Parity Health
        </h1>

        {/* Spinner */}
        <div className="flex justify-center mb-10">
          <div className="relative w-20 h-20">
            <div className="absolute inset-0 rounded-full border-4 border-gray-200" />
            <div className="absolute inset-0 rounded-full border-4 border-[#0D7377] border-t-transparent animate-spin" />
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {STEPS.map((step, i) => (
            <div key={i} className="flex items-center justify-center gap-2">
              {i < currentStep ? (
                <svg
                  className="w-5 h-5 text-[#0D7377]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="m4.5 12.75 6 6 9-13.5"
                  />
                </svg>
              ) : i === currentStep ? (
                <div className="w-5 h-5 flex items-center justify-center">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#0D7377] animate-pulse" />
                </div>
              ) : (
                <div className="w-5 h-5 flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-gray-300" />
                </div>
              )}
              <span
                className={`text-base ${
                  i === currentStep
                    ? "text-[#1B3A5C] font-medium"
                    : i < currentStep
                      ? "text-gray-400"
                      : "text-gray-300"
                }`}
              >
                {i === currentStep ? step.replace("...", dots) : step}
              </span>
            </div>
          ))}
        </div>

        {/* Cold-start "waking up" notice */}
        {slowServer && (
          <div className="mt-10 flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl px-5 py-4 max-w-md">
            <div className="w-4 h-4 rounded-full bg-[#0D7377]/60 animate-pulse shrink-0" />
            <p className="text-sm text-gray-500">
              Waking up the server&hellip; this takes up to 30 seconds on first use. Subsequent analyses will be faster.
            </p>
          </div>
        )}
      </div>

      <Footer />
    </div>
  );
}
