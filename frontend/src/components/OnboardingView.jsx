import { useState, useCallback } from "react";
import { Footer } from "./UploadView.jsx";

const STORAGE_KEY = "parity_patient_info";
const SAVED_FIELDS = ["patientName", "dateOfBirth", "mailingAddress", "email", "phone"];

function loadSavedInfo() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

function saveSavedInfo(fields) {
  try {
    const data = {};
    for (const key of SAVED_FIELDS) data[key] = fields[key] || "";
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch { /* ignore */ }
}

export default function OnboardingView({ onSubmit }) {
  const saved = loadSavedInfo();

  const [fields, setFields] = useState({
    patientName: saved?.patientName || "",
    dateOfBirth: saved?.dateOfBirth || "",
    providerName: "",
    serviceDate: "",
    mailingAddress: saved?.mailingAddress || "",
    email: saved?.email || "",
    phone: saved?.phone || "",
  });

  const updateField = useCallback((key, value) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleContinue = useCallback(
    (e) => {
      e.preventDefault();
      saveSavedInfo(fields);
      onSubmit(fields);
    },
    [fields, onSubmit]
  );

  const handleClearSaved = useCallback(() => {
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
    setFields({
      patientName: "",
      dateOfBirth: "",
      providerName: fields.providerName,
      serviceDate: fields.serviceDate,
      mailingAddress: "",
      email: "",
      phone: "",
    });
  }, [fields.providerName, fields.serviceDate]);

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
            Enter your details below to pre-fill your request.
          </p>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Patient full name
            </label>
            <input
              type="text"
              required
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
              required
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
              required
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
              required
              value={fields.serviceDate}
              onChange={(e) => updateField("serviceDate", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="MM/DD/YYYY"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Mailing address
            </label>
            <input
              type="text"
              required
              value={fields.mailingAddress}
              onChange={(e) => updateField("mailingAddress", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="123 Main St, City, ST 12345"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Email address
            </label>
            <input
              type="email"
              required
              value={fields.email}
              onChange={(e) => updateField("email", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="jane@example.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Phone number
              <span className="text-gray-400 font-normal"> (optional)</span>
            </label>
            <input
              type="tel"
              value={fields.phone}
              onChange={(e) => updateField("phone", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="(555) 123-4567"
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
          >
            Continue
          </button>

          {saved && (
            <p className="text-center">
              <button
                type="button"
                onClick={handleClearSaved}
                className="text-sm text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                Update my information
              </button>
            </p>
          )}
        </form>
      </div>

      <Footer />
    </div>
  );
}
