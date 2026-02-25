import { Footer } from "./UploadView.jsx";

function fmt$(amount) {
  if (amount == null) return null;
  return `$${Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
}

export default function EOBDetectedView({ eobExtracted, eobParseError, onRequestItemized, onUploadItemized }) {
  const e = eobExtracted || {};

  // Collect non-empty extracted fields for display (AI response uses snake_case)
  const summaryFields = [
    { label: "Insurance Company", value: e.insurance_company },
    { label: "Provider", value: e.provider_name },
    { label: "Claim Number", value: e.claim_number },
    { label: "Member ID", value: e.member_id },
    { label: "Group Number", value: e.group_number },
    { label: "Service Date", value: e.service_date },
    { label: "Patient Name", value: e.patient_name },
    { label: "Total Billed", value: fmt$(e.amount_billed) },
    { label: "Plan Paid", value: fmt$(e.plan_paid) },
    { label: "Patient Responsibility", value: fmt$(e.patient_responsibility) },
    { label: "Cost Reduction", value: fmt$(e.cost_reduction) },
    { label: "Account", value: e.account_name },
  ].filter((f) => f.value);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-[Arial,sans-serif]">
      <main className="max-w-2xl mx-auto px-4 py-12 w-full flex-1">
        {/* Icon + Heading */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-50 mb-4">
            <svg className="w-8 h-8 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-[#1B3A5C] mb-2">
            Explanation of Benefits Detected
          </h2>
          <p className="text-gray-600 max-w-lg mx-auto">
            This document is an <strong>EOB from your insurance company</strong>, not an itemized bill from your provider. EOBs summarize what your plan covered but don't include the procedure codes we need to benchmark your charges.
          </p>
        </div>

        {/* Parse error fallback message */}
        {eobParseError && (
          <div className="flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-100 rounded-lg mb-6">
            <svg className="w-4 h-4 text-amber-600 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
            </svg>
            <span className="text-sm text-amber-700">
              We couldn't read all the details from your EOB. Please fill in the form below manually.
            </span>
          </div>
        )}

        {/* What we found */}
        {summaryFields.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
              What we found in your EOB
            </h3>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
              {summaryFields.map((f) => (
                <div key={f.label}>
                  <dt className="text-xs text-gray-400">{f.label}</dt>
                  <dd className="text-sm font-medium text-[#1B3A5C]">{f.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {/* What's the difference */}
        <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-5 mb-8">
          <h3 className="text-sm font-semibold text-[#1B3A5C] mb-2">
            What's the difference?
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-gray-700 mb-1">EOB (what you uploaded)</p>
              <ul className="text-gray-500 space-y-1">
                <li>Sent by your insurance</li>
                <li>Shows plan payments & your share</li>
                <li>Usually lacks CPT procedure codes</li>
              </ul>
            </div>
            <div>
              <p className="font-medium text-gray-700 mb-1">Itemized Bill (what we need)</p>
              <ul className="text-gray-500 space-y-1">
                <li>Sent by your provider/hospital</li>
                <li>Lists each procedure with codes</li>
                <li>Often a UB-04 or CMS-1500 form</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <button
            onClick={onRequestItemized}
            className="flex-1 px-5 py-3 text-sm font-medium text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer text-center"
          >
            Request Itemized Bill from Provider
          </button>
          <button
            onClick={onUploadItemized}
            className="flex-1 px-5 py-3 text-sm font-medium text-[#1B3A5C] border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer text-center"
          >
            I have the itemized bill — upload it
          </button>
        </div>

        {/* Tip */}
        <p className="text-xs text-gray-400 text-center mb-4">
          Tip: Ask your provider for a "UB-04" (hospital) or "CMS-1500" (physician) form — these always include procedure codes.
        </p>
      </main>

      <Footer />
    </div>
  );
}
