import { useState, useCallback } from "react";
import { Footer } from "./UploadView.jsx";

export default function ItemizedBillRequestView({ eobData, onboardingData, onReset }) {
  const [copied, setCopied] = useState(false);

  const fullName = [onboardingData?.firstName, onboardingData?.lastName]
    .filter(Boolean).join(" ");
  const fullAddress = [
    onboardingData?.streetAddress,
    [onboardingData?.city, onboardingData?.state].filter(Boolean).join(", "),
    onboardingData?.zipCode,
  ].filter(Boolean).join(", ");

  const [fields, setFields] = useState({
    patientName: fullName,
    serviceDate: "",
    providerName: "",
    dateOfBirth: onboardingData?.dateOfBirth || "",
    accountId: eobData?.accountNumber || "",
    mailingAddress: fullAddress,
    email: onboardingData?.email || "",
    phone: onboardingData?.phone || "",
  });

  const updateField = useCallback((key, value) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  }, []);

  const providerName = onboardingData?.providerName || "";

  const letterText = buildLetterText(fields, providerName);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(letterText);
    } catch {
      // Fallback for older browsers
      const ta = document.createElement("textarea");
      ta.value = letterText;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [letterText]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-[Arial,sans-serif]">
      {/* Print-only header */}
      <div className="hidden print:block px-4 pt-4 pb-2 border-b border-gray-300 mb-4">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-[#1B3A5C] tracking-tight">
            Parity
          </h1>
          <p className="text-sm text-gray-500">
            {new Date().toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-4 py-8 w-full flex-1">
        {/* Action buttons */}
        <div className="flex items-center gap-3 mb-6 print:hidden">
          {onReset && (
            <button
              onClick={onReset}
              className="px-4 py-2 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
            >
              Upload Another Bill
            </button>
          )}
        </div>

        {/* Explanation section */}
        <div className="mb-8 print:hidden">
          <h2 className="text-2xl font-bold text-[#1B3A5C] mb-2">
            We need your itemized bill
          </h2>
          <p className="text-gray-600 mb-4">
            The document you uploaded is a summary. To analyze your charges, we
            need the itemized bill from your provider — the one that lists each
            procedure separately with its code.
          </p>
          <p className="text-gray-600">
            The good news: you have a legal right to this document. Use the
            letter below to request it. Most providers respond within 2 weeks.
          </p>
        </div>

        {/* Letter template */}
        <div className="bg-white rounded-xl border border-gray-200 p-8 mb-6">
          {/* Subject line */}
          <p className="font-semibold text-[#1B3A5C] mb-6">
            Subject: Request for Itemized Bill —{" "}
            <EditableField
              value={fields.patientName}
              placeholder="Patient Name"
              onChange={(v) => updateField("patientName", v)}
            />
            , Date of Service{" "}
            <EditableField
              value={fields.serviceDate}
              placeholder="Date"
              onChange={(v) => updateField("serviceDate", v)}
            />
          </p>

          {/* Salutation */}
          <p className="text-gray-700 mb-4">Dear Billing Department,</p>

          {/* Body */}
          <p className="text-gray-700 mb-4">
            I am writing to request a complete itemized bill for services I
            received on{" "}
            <EditableField
              value={fields.serviceDate}
              placeholder="date of service"
              onChange={(v) => updateField("serviceDate", v)}
            />.
          </p>

          <p className="text-gray-700 mb-2">
            Specifically, I am requesting a document that includes:
          </p>
          <ul className="list-disc list-inside text-gray-700 mb-4 ml-2 space-y-1">
            <li>Each service or procedure listed separately</li>
            <li>The CPT or procedure code for each service</li>
            <li>The charge amount for each individual service</li>
            <li>The name of the treating provider</li>
          </ul>

          <p className="text-gray-700 mb-6">
            I understand I have the right to receive this information and would
            appreciate receiving it within 30 days. Please send it to the
            address or email below.
          </p>

          <p className="text-gray-700 mb-6">
            Thank you for your assistance.
          </p>

          {/* Signature block */}
          <div className="space-y-2">
            <p className="text-gray-700">Sincerely,</p>
            <p className="text-gray-700">
              <EditableField
                value={fields.patientName}
                placeholder="Patient Name"
                onChange={(v) => updateField("patientName", v)}
              />
            </p>
            <p className="text-gray-700">
              <EditableField
                value={fields.dateOfBirth}
                placeholder="Date of Birth"
                onChange={(v) => updateField("dateOfBirth", v)}
              />
            </p>
            {fields.accountId && (
              <p className="text-gray-700">
                Account or Patient ID:{" "}
                <EditableField
                  value={fields.accountId}
                  placeholder="XXXXXXX"
                  onChange={(v) => updateField("accountId", v)}
                />
              </p>
            )}
            <p className="text-gray-700">
              <EditableField
                value={fields.mailingAddress}
                placeholder="Your Mailing Address"
                onChange={(v) => updateField("mailingAddress", v)}
              />
            </p>
            <p className="text-gray-700">
              <EditableField
                value={fields.email}
                placeholder="Your Email Address"
                onChange={(v) => updateField("email", v)}
              />
            </p>
            <p className="text-gray-700">
              <EditableField
                value={fields.phone}
                placeholder="Your Phone Number"
                onChange={(v) => updateField("phone", v)}
              />
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-3 mb-3 print:hidden">
          <button
            onClick={() => window.print()}
            className="px-5 py-2.5 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer"
          >
            Download Letter
          </button>
          <button
            onClick={handleCopy}
            className="px-5 py-2.5 text-sm font-medium text-[#1B3A5C] border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer"
          >
            {copied ? "Copied!" : "Copy Letter"}
          </button>
        </div>
        <p className="text-xs text-gray-400 mb-8 print:hidden">
          To send: email your provider's billing department and attach or paste this letter.
        </p>

        {/* Come-back note */}
        <div className="bg-[#0D7377]/5 border border-[#0D7377]/20 rounded-xl p-5 text-center print:hidden">
          <p className="text-sm text-[#0D7377] font-medium">
            Once you receive your itemized bill, come back and upload it here.
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editable inline field
// ---------------------------------------------------------------------------

function EditableField({ value, placeholder, onChange }) {
  return (
    <input
      type="text"
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      className="border-b border-gray-300 focus:border-[#0D7377] outline-none px-1 py-0.5 text-[#1B3A5C] font-medium bg-transparent min-w-[80px] placeholder:text-gray-400 placeholder:font-normal print:border-none"
      style={{ width: Math.max(80, (value || placeholder).length * 9) + "px" }}
    />
  );
}

// ---------------------------------------------------------------------------
// Build plain-text letter for clipboard
// ---------------------------------------------------------------------------

function buildLetterText(fields, providerName) {
  const name = fields.patientName || "[Patient Name]";
  const date = fields.serviceDate || "[Date of Service]";
  const dob = fields.dateOfBirth || "[Date of Birth]";
  const addr = fields.mailingAddress || "[Your Mailing Address]";
  const email = fields.email || "[Your Email Address]";
  const phone = fields.phone || "[Your Phone Number]";

  const sigLines = [name, dob];
  if (fields.accountId) sigLines.push(`Account or Patient ID: ${fields.accountId}`);
  sigLines.push(addr, email, phone);

  return `Subject: Request for Itemized Bill — ${name}, Date of Service ${date}

Dear Billing Department,

I am writing to request a complete itemized bill for services I received on ${date}.

Specifically, I am requesting a document that includes:
- Each service or procedure listed separately
- The CPT or procedure code for each service
- The charge amount for each individual service
- The name of the treating provider

I understand I have the right to receive this information and would appreciate receiving it within 30 days. Please send it to the address or email below.

Thank you for your assistance.

Sincerely,
${sigLines.join("\n")}`;
}
