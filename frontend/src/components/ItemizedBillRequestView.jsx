import { useState, useCallback, useEffect } from "react";
import { Footer } from "./UploadView.jsx";

/**
 * Format a date string like "2025-11-07" to "November 7, 2025".
 * Returns the original string if parsing fails.
 */
function formatDateLong(dateStr) {
  if (!dateStr) return "";
  const match = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return dateStr;
  const d = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}

export default function ItemizedBillRequestView({
  eobData,
  eobExtracted,
  nppesResult,
  nppesLoading,
  onboardingData,
  onReset,
  reason,
}) {
  const [copied, setCopied] = useState(false);
  const isEOB = reason === "eob_detected";

  const fullName = [onboardingData?.firstName, onboardingData?.lastName]
    .filter(Boolean).join(" ");
  const fullAddress = [
    onboardingData?.streetAddress,
    [onboardingData?.city, onboardingData?.state].filter(Boolean).join(", "),
    onboardingData?.zipCode,
  ].filter(Boolean).join(", ");

  // AI endpoint returns snake_case field names
  const [fields, setFields] = useState({
    patientName: eobExtracted?.patient_name || fullName,
    serviceDate: eobExtracted?.service_date || "",
    providerName: eobExtracted?.provider_name || "",
    providerAddress: eobExtracted?.provider_address || "",
    providerCityStateZip: "",
    providerPhone: "",
    dateOfBirth: onboardingData?.dateOfBirth || "",
    accountId: eobData?.accountNumber || "",
    mailingAddress: fullAddress,
    email: onboardingData?.email || "",
    phone: onboardingData?.phone || "",
    insuranceCompany: eobExtracted?.insurance_company || "",
    claimNumber: eobExtracted?.claim_number || "",
    memberID: eobExtracted?.member_id || "",
    groupNumber: eobExtracted?.group_number || "",
  });

  // Sync eobExtracted fields into form state (handles late-arriving data)
  useEffect(() => {
    if (!eobExtracted) return;
    setFields((prev) => ({
      ...prev,
      patientName: prev.patientName || eobExtracted.patient_name || "",
      serviceDate: prev.serviceDate || eobExtracted.service_date || "",
      providerName: prev.providerName || eobExtracted.provider_name || "",
      providerAddress: prev.providerAddress || eobExtracted.provider_address || "",
      insuranceCompany: prev.insuranceCompany || eobExtracted.insurance_company || "",
      claimNumber: prev.claimNumber || eobExtracted.claim_number || "",
      memberID: prev.memberID || eobExtracted.member_id || "",
      groupNumber: prev.groupNumber || eobExtracted.group_number || "",
    }));
  }, [eobExtracted]);

  // Pre-fill provider fields when NPPES result arrives
  useEffect(() => {
    if (nppesResult?.found && nppesResult.bestMatch) {
      const m = nppesResult.bestMatch;
      setFields((prev) => ({
        ...prev,
        providerName: prev.providerName || m.name || "",
        providerAddress: prev.providerAddress || m.address?.line1 || "",
        providerCityStateZip:
          prev.providerCityStateZip ||
          [m.address?.city, m.address?.state, m.address?.zip].filter(Boolean).join(", ") ||
          "",
        providerPhone: prev.providerPhone || m.phone || "",
      }));
    }
  }, [nppesResult]);

  const updateField = useCallback((key, value) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  }, []);

  const formattedDate = formatDateLong(fields.serviceDate) || fields.serviceDate;
  const letterText = buildLetterText(fields, isEOB);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(letterText);
    } catch {
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
            Parity Health
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
            {isEOB
              ? "Request your itemized bill"
              : reason === "no_codes"
                ? "We couldn\u2019t find procedure codes on this bill"
                : "We need your itemized bill"}
          </h2>
          <p className="text-gray-600 mb-4">
            {isEOB
              ? "We detected an Explanation of Benefits (EOB) from your insurance. To benchmark your charges, we need the itemized bill from your provider \u2014 the one that lists each procedure with its CPT code."
              : reason === "no_codes"
                ? "This is common for bills that don\u2019t itemize services. To analyze your charges, we need an itemized bill from your provider \u2014 the one that lists each procedure separately with its code."
                : "The document you uploaded is a summary. To analyze your charges, we need the itemized bill from your provider \u2014 the one that lists each procedure separately with its code."}
          </p>
          <p className="text-gray-600">
            The good news: you have a legal right to this document. Use the
            letter below to request it. Most providers respond within 2 weeks.
          </p>
        </div>

        {/* NPPES status banner */}
        {isEOB && (
          <div className="mb-4 print:hidden">
            {nppesLoading && (
              <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-50 border border-blue-100 rounded-lg">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500" />
                </span>
                <span className="text-sm text-blue-700">Looking up provider contact information...</span>
              </div>
            )}
            {!nppesLoading && nppesResult?.found && (
              <div className="flex items-center gap-2 px-4 py-2.5 bg-green-50 border border-green-100 rounded-lg">
                <svg className="w-4 h-4 text-green-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
                <span className="text-sm text-green-700">
                  Contact information found for <strong>{nppesResult.bestMatch?.name}</strong> — please verify before sending.
                </span>
              </div>
            )}
            {!nppesLoading && nppesResult && !nppesResult.found && (
              <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-100 rounded-lg">
                <svg className="w-4 h-4 text-amber-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                </svg>
                <span className="text-sm text-amber-700">
                  Provider contact information not found — please add the provider address manually.
                </span>
              </div>
            )}
          </div>
        )}

        {/* Provider + claim details form (EOB mode) */}
        {isEOB && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6 print:hidden">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              Provider & Claim Details
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField label="Provider Name" value={fields.providerName} onChange={(v) => updateField("providerName", v)} />
              <FormField label="Provider Phone" value={fields.providerPhone} onChange={(v) => updateField("providerPhone", v)} placeholder="(XXX) XXX-XXXX" />
              <FormField label="Provider Address" value={fields.providerAddress} onChange={(v) => updateField("providerAddress", v)} className="sm:col-span-2" />
              <FormField label="City, State, ZIP" value={fields.providerCityStateZip} onChange={(v) => updateField("providerCityStateZip", v)} className="sm:col-span-2" />
              <FormField label="Insurance Company" value={fields.insuranceCompany} onChange={(v) => updateField("insuranceCompany", v)} />
              <FormField label="Claim Number" value={fields.claimNumber} onChange={(v) => updateField("claimNumber", v)} />
              <FormField label="Member ID" value={fields.memberID} onChange={(v) => updateField("memberID", v)} />
              <FormField label="Group Number" value={fields.groupNumber} onChange={(v) => updateField("groupNumber", v)} />
            </div>
          </div>
        )}

        {/* Letter template */}
        <div className="bg-white rounded-xl border border-gray-200 p-8 mb-6">
          {/* Provider address block (EOB enhanced) */}
          {isEOB && (fields.providerName || fields.providerAddress) && (
            <div className="text-gray-700 mb-6 print:mb-4">
              <p className="text-sm text-gray-400 mb-1 print:hidden">To:</p>
              {fields.providerName && <p className="font-medium">{fields.providerName}</p>}
              {fields.providerAddress && <p>{fields.providerAddress}</p>}
              {fields.providerCityStateZip && <p>{fields.providerCityStateZip}</p>}
            </div>
          )}

          {/* Date */}
          <p className="text-gray-700 mb-6">
            {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
          </p>

          {/* Subject line */}
          <p className="font-semibold text-[#1B3A5C] mb-2">
            Subject: Request for Itemized Bill —{" "}
            <EditableField
              value={fields.patientName}
              placeholder="Patient Name"
              onChange={(v) => updateField("patientName", v)}
            />
            , Date of Service{" "}
            <EditableField
              value={formattedDate}
              placeholder="Date"
              onChange={(v) => updateField("serviceDate", v)}
            />
          </p>

          {/* Re: line with claim details (EOB enhanced) */}
          {isEOB && (fields.insuranceCompany || fields.claimNumber || fields.memberID) && (
            <p className="text-sm text-gray-500 mb-6">
              Re:{" "}
              {[
                fields.insuranceCompany && `Insurance: ${fields.insuranceCompany}`,
                fields.claimNumber && `Claim #${fields.claimNumber}`,
                fields.memberID && `Member ID: ${fields.memberID}`,
              ]
                .filter(Boolean)
                .join(" | ")}
            </p>
          )}

          {/* Salutation */}
          <p className="text-gray-700 mb-4">Dear Billing Department,</p>

          {/* Body */}
          <p className="text-gray-700 mb-4">
            I am writing to request a complete itemized bill for services I
            received on{" "}
            <EditableField
              value={formattedDate}
              placeholder="date of service"
              onChange={(v) => updateField("serviceDate", v)}
            />.
          </p>

          {isEOB && (
            <p className="text-gray-700 mb-4">
              I have received an Explanation of Benefits from my insurance company
              {fields.insuranceCompany ? ` (${fields.insuranceCompany})` : ""}
              {fields.claimNumber ? `, claim #${fields.claimNumber}` : ""}
              , but this document does not include the individual procedure codes needed to verify my charges.
            </p>
          )}

          <p className="text-gray-700 mb-2">
            Specifically, I am requesting a document that includes:
          </p>
          <ul className="list-disc list-inside text-gray-700 mb-4 ml-2 space-y-1">
            <li>Each service or procedure listed separately</li>
            <li>The CPT or HCPCS procedure code for each service</li>
            <li>The charge amount for each individual service</li>
            <li>The name of the treating provider</li>
            {isEOB && <li>Revenue codes and service descriptions</li>}
          </ul>

          {isEOB ? (
            <p className="text-gray-700 mb-4">
              Under the No Surprises Act (P.L. 116-260) and applicable state consumer protection laws, patients have the right to receive a detailed, itemized statement of charges. I understand this right and respectfully request that this information be provided within 30 days. Please send the itemized bill to my mailing address below. You may also contact me at the phone number below to arrange delivery.
            </p>
          ) : (
            <p className="text-gray-700 mb-4">
              I understand I have the right to receive this information and would
              appreciate receiving it within 30 days. Please send the itemized bill to my mailing address below. You may also contact me at the phone number below to arrange delivery.
            </p>
          )}

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
            {isEOB && fields.memberID && (
              <p className="text-gray-700">
                Member ID:{" "}
                <EditableField
                  value={fields.memberID}
                  placeholder="Member ID"
                  onChange={(v) => updateField("memberID", v)}
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
                value={fields.phone}
                placeholder="Your Phone Number"
                onChange={(v) => updateField("phone", v)}
              />
            </p>
          </div>

          {/* Generated-by footer (print only) */}
          <div className="hidden print:block mt-8 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-400">Generated by Parity Health (parityhealth.com)</p>
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
        <div className="space-y-2.5 mb-8 print:hidden">
          <p className="text-sm font-medium text-[#1B3A5C]">How to send this letter:</p>
          <div className="flex items-start gap-2 text-sm text-gray-600">
            <span className="shrink-0">📞</span>
            <p><strong>Call first:</strong> Contact the billing department{fields.providerPhone ? ` at ${fields.providerPhone}` : ""} to confirm the correct mailing address and fax number for records requests.</p>
          </div>
          <div className="flex items-start gap-2 text-sm text-gray-600">
            <span className="shrink-0">📬</span>
            <p><strong>Mail or fax:</strong> Send the letter by certified mail or fax to the billing department. Keep a copy for your records.</p>
          </div>
          <div className="flex items-start gap-2 text-sm text-gray-600">
            <span className="shrink-0">⏱</span>
            <p><strong>Response time:</strong> Providers are typically required to respond within 30 days. Follow up if you haven't heard back.</p>
          </div>
        </div>

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
// Form field (for the provider/claim details form)
// ---------------------------------------------------------------------------

function FormField({ label, value, onChange, placeholder, className = "" }) {
  return (
    <div className={className}>
      <label className="block text-xs text-gray-500 mb-1">{label}</label>
      <input
        type="text"
        value={value}
        placeholder={placeholder || label}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 text-sm text-[#1B3A5C] border border-gray-200 rounded-lg focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377]/20 outline-none placeholder:text-gray-300"
      />
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

function buildLetterText(fields, isEOB) {
  const name = fields.patientName || "[Patient Name]";
  const rawDate = fields.serviceDate || "[Date of Service]";
  const date = formatDateLong(rawDate) || rawDate;
  const dob = fields.dateOfBirth || "[Date of Birth]";
  const addr = fields.mailingAddress || "[Your Mailing Address]";
  const phone = fields.phone || "[Your Phone Number]";
  const todayStr = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });

  // Provider address block
  const providerBlock = [];
  if (isEOB) {
    if (fields.providerName) providerBlock.push(fields.providerName);
    if (fields.providerAddress) providerBlock.push(fields.providerAddress);
    if (fields.providerCityStateZip) providerBlock.push(fields.providerCityStateZip);
  }

  // Re: line
  const reItems = [];
  if (isEOB) {
    if (fields.insuranceCompany) reItems.push(`Insurance: ${fields.insuranceCompany}`);
    if (fields.claimNumber) reItems.push(`Claim #${fields.claimNumber}`);
    if (fields.memberID) reItems.push(`Member ID: ${fields.memberID}`);
  }

  // EOB paragraph
  const eobParagraph = isEOB
    ? `\nI have received an Explanation of Benefits from my insurance company${fields.insuranceCompany ? ` (${fields.insuranceCompany})` : ""}${fields.claimNumber ? `, claim #${fields.claimNumber}` : ""}, but this document does not include the individual procedure codes needed to verify my charges.\n`
    : "";

  // Request items
  const requestItems = [
    "Each service or procedure listed separately",
    "The CPT or HCPCS procedure code for each service",
    "The charge amount for each individual service",
    "The name of the treating provider",
  ];
  if (isEOB) requestItems.push("Revenue codes and service descriptions");

  // Rights paragraph
  const rightsParagraph = isEOB
    ? "Under the No Surprises Act (P.L. 116-260) and applicable state consumer protection laws, patients have the right to receive a detailed, itemized statement of charges. I understand this right and respectfully request that this information be provided within 30 days. Please send the itemized bill to my mailing address below. You may also contact me at the phone number below to arrange delivery."
    : "I understand I have the right to receive this information and would appreciate receiving it within 30 days. Please send the itemized bill to my mailing address below. You may also contact me at the phone number below to arrange delivery.";

  // Signature lines
  const sigLines = [name, dob];
  if (fields.accountId) sigLines.push(`Account or Patient ID: ${fields.accountId}`);
  if (isEOB && fields.memberID) sigLines.push(`Member ID: ${fields.memberID}`);
  sigLines.push(addr, phone);

  const parts = [];
  if (providerBlock.length > 0) parts.push(providerBlock.join("\n"));
  parts.push(todayStr);
  parts.push(`Subject: Request for Itemized Bill — ${name}, Date of Service ${date}`);
  if (reItems.length > 0) parts.push(`Re: ${reItems.join(" | ")}`);
  parts.push(`Dear Billing Department,`);
  parts.push(`I am writing to request a complete itemized bill for services I received on ${date}.`);
  if (eobParagraph) parts.push(eobParagraph.trim());
  parts.push(`Specifically, I am requesting a document that includes:\n${requestItems.map((i) => `- ${i}`).join("\n")}`);
  parts.push(rightsParagraph);
  parts.push("Thank you for your assistance.");
  parts.push(`Sincerely,\n${sigLines.join("\n")}`);
  parts.push("Generated by Parity Health (parityhealth.com)");

  return parts.join("\n\n");
}
