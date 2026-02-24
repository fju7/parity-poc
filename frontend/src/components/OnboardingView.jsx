import { useState, useCallback } from "react";
import { supabase } from "../lib/supabase.js";
import { Footer } from "./UploadView.jsx";

function formatDateMask(raw) {
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return digits.slice(0, 2) + "/" + digits.slice(2);
  return digits.slice(0, 2) + "/" + digits.slice(2, 4) + "/" + digits.slice(4);
}

function formatPhoneMask(raw) {
  const digits = raw.replace(/\D/g, "").slice(0, 10);
  if (digits.length === 0) return "";
  if (digits.length <= 3) return "(" + digits;
  if (digits.length <= 6) return "(" + digits.slice(0, 3) + ") " + digits.slice(3);
  return "(" + digits.slice(0, 3) + ") " + digits.slice(3, 6) + "-" + digits.slice(6);
}

export default function OnboardingView({
  onSubmit,
  initialData,
  isAccountView = false,
  consentData,
  onDeleteAccount,
  session,
}) {
  const [fields, setFields] = useState({
    firstName: initialData?.firstName || "",
    lastName: initialData?.lastName || "",
    dateOfBirth: initialData?.dateOfBirth || "",
    streetAddress: initialData?.streetAddress || "",
    city: initialData?.city || "",
    state: initialData?.state || "",
    zipCode: initialData?.zipCode || "",
    email: initialData?.email || "",
    phone: initialData?.phone || "",
  });

  const [analyticsEnabled, setAnalyticsEnabled] = useState(consentData?.consentAnalytics ?? true);
  const [employerEnabled, setEmployerEnabled] = useState(consentData?.consentEmployer ?? false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

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

  const handleConsentToggle = async (key, value) => {
    if (key === "analytics") setAnalyticsEnabled(value);
    if (key === "employer") setEmployerEnabled(value);

    if (session?.user) {
      try {
        const update = key === "analytics"
          ? { consent_analytics: value }
          : { consent_employer: value };
        await supabase.from("profiles").update(update).eq("id", session.user.id);
      } catch {
        // Non-blocking
      }
    }
  };

  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center px-4 font-[Arial,sans-serif]">
      <div className="w-full max-w-md">
        {/* Header — different for account vs first-time */}
        {isAccountView ? (
          <h2 className="text-2xl font-bold text-[#1B3A5C] mb-8 text-center">
            My Account
          </h2>
        ) : (
          <>
            <h1 className="text-5xl font-bold text-[#1B3A5C] mb-2 tracking-tight text-center">
              Parity Health
            </h1>
            <p className="text-lg text-gray-500 mb-10 text-center">
              Bill Analysis
            </p>
          </>
        )}

        {/* Form */}
        <form onSubmit={handleContinue} className="space-y-5">
          <p className="text-sm text-gray-600 mb-2">
            {isAccountView
              ? "Update your personal information."
              : "Enter your details below to pre-fill your request."}
          </p>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                First name
              </label>
              <input
                type="text"
                required
                value={fields.firstName}
                onChange={(e) => updateField("firstName", e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
                placeholder="Jane"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                Last name
              </label>
              <input
                type="text"
                required
                value={fields.lastName}
                onChange={(e) => updateField("lastName", e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
                placeholder="Smith"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Date of birth
            </label>
            <input
              type="text"
              required
              value={fields.dateOfBirth}
              onChange={(e) => updateField("dateOfBirth", formatDateMask(e.target.value))}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="MM/DD/YYYY"
              inputMode="numeric"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
              Street address
            </label>
            <input
              type="text"
              required
              value={fields.streetAddress}
              onChange={(e) => updateField("streetAddress", e.target.value)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="123 Main St"
            />
          </div>

          <div className="grid grid-cols-6 gap-3">
            <div className="col-span-3">
              <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                City
              </label>
              <input
                type="text"
                required
                value={fields.city}
                onChange={(e) => updateField("city", e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
                placeholder="Tampa"
              />
            </div>
            <div className="col-span-1">
              <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                State
              </label>
              <input
                type="text"
                required
                maxLength={2}
                value={fields.state}
                onChange={(e) => updateField("state", e.target.value.toUpperCase())}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
                placeholder="FL"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                Zip code
              </label>
              <input
                type="text"
                required
                value={fields.zipCode}
                onChange={(e) => updateField("zipCode", e.target.value)}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
                placeholder="33701"
              />
            </div>
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
              onChange={(e) => updateField("phone", formatPhoneMask(e.target.value))}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]"
              placeholder="(555) 123-4567"
            />
          </div>

          <button
            type="submit"
            className="w-full py-3 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
          >
            {isAccountView ? "Save Changes" : "Continue"}
          </button>
        </form>

        {/* Privacy & Data section — only shown on My Account view */}
        {isAccountView && (
          <div className="mt-10 pt-8 border-t border-gray-200">
            <h3 className="text-lg font-bold text-[#1B3A5C] mb-4">Privacy & Data</h3>

            <div className="space-y-4">
              {/* Analytics toggle */}
              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-xl">
                <div>
                  <p className="font-medium text-[#1B3A5C] text-sm">Help improve Parity Health</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Share anonymized usage data to improve accuracy
                  </p>
                </div>
                <Toggle
                  checked={analyticsEnabled}
                  onChange={(val) => handleConsentToggle("analytics", val)}
                />
              </div>

              {/* Employer toggle */}
              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-xl">
                <div>
                  <p className="font-medium text-[#1B3A5C] text-sm">Contribute to employer dashboard</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Allow de-identified trends on your employer's dashboard
                  </p>
                </div>
                <Toggle
                  checked={employerEnabled}
                  onChange={(val) => handleConsentToggle("employer", val)}
                />
              </div>
            </div>

            {/* Delete account */}
            {onDeleteAccount && (
              <div className="mt-8">
                {showDeleteConfirm ? (
                  <div className="p-4 border border-red-200 rounded-xl bg-red-50">
                    <p className="text-sm text-red-800 font-medium mb-3">
                      Are you sure? This will permanently delete your account and all local bill data.
                    </p>
                    <div className="flex gap-3">
                      <button
                        onClick={onDeleteAccount}
                        className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 cursor-pointer"
                      >
                        Yes, delete my account
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(false)}
                        className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="text-sm font-medium text-red-600 hover:text-red-700 cursor-pointer"
                  >
                    Delete My Account
                  </button>
                )}
              </div>
            )}
          </div>
        )}
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
