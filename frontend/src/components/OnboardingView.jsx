import { useState, useCallback } from "react";
import { Footer } from "./UploadView.jsx";

export default function OnboardingView({ onSubmit }) {
  const [fields, setFields] = useState({
    patientName: "",
    dateOfBirth: "",
    providerName: "",
    serviceDate: "",
  });

  const updateField = useCallback((key, value) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleContinue = useCallback(
    (e) => {
      e.preventDefault();
      onSubmit(fields);
    },
    [fields, onSubmit]
  );

  const handleSkip = useCallback(() => {
    onSubmit({ patientName: "", dateOfBirth: "", providerName: "", serviceDate: "" });
  }, [onSubmit]);

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="w-full max-w-md">
        {/* Logo */}
        <h1 className="text-5xl font-bold text-[#1B3A5C] mb-2 tracking-tight text-center">
          Parity
        </h1>
        <p className="text-lg text-gray-500 mb-10 text-center">
          Medical Bill Analysis
        </p>

        {/* Form */}
        <form onSubmit={handleContinue} className="space-y-5">
          <p className="text-sm text-gray-600 mb-2">
            Enter your details below to pre-fill your request. All fields are
            optional.
          </p>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Patient full name
            </label>
            <input
              type="text"
              value={fields.patientName}
              onChange={(e) => updateField("patientName", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="Jane Smith"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Date of birth
            </label>
            <input
              type="text"
              value={fields.dateOfBirth}
              onChange={(e) => updateField("dateOfBirth", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="MM/DD/YYYY"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Provider or hospital name
            </label>
            <input
              type="text"
              value={fields.providerName}
              onChange={(e) => updateField("providerName", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="City Medical Center"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Date of service
            </label>
            <input
              type="text"
              value={fields.serviceDate}
              onChange={(e) => updateField("serviceDate", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="MM/DD/YYYY"
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
          >
            Continue
          </button>

          <p className="text-center">
            <button
              type="button"
              onClick={handleSkip}
              className="text-sm text-gray-400 hover:text-gray-600 cursor-pointer"
            >
              Skip
            </button>
          </p>
        </form>
      </div>

      <Footer />
    </div>
  );
}
