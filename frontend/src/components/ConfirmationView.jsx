import { useState, useCallback } from "react";
import { Footer } from "./UploadView.jsx";

export default function ConfirmationView({ billData, onConfirm, onBack }) {
  const [zipCode, setZipCode] = useState(billData.provider?.zip || "");

  const totalBilled = (billData.lineItems || []).reduce(
    (sum, item) => sum + (item.billedAmount || 0),
    0
  );

  const handleConfirm = useCallback(() => {
    // Apply the (possibly edited) zip code before running pipeline
    const confirmed = {
      ...billData,
      provider: {
        ...billData.provider,
        zip: zipCode.trim() || "00000",
      },
    };
    onConfirm(confirmed);
  }, [billData, zipCode, onConfirm]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-[Arial,sans-serif]">
      <main className="max-w-3xl mx-auto px-4 py-8 w-full flex-1">
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
          Review Extracted Data
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          Please review the extracted information before running the benchmark analysis.
        </p>

        {/* Provider & encounter details */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            Provider &amp; Encounter
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Provider Name
              </label>
              <p className="text-sm text-[#1B3A5C] font-medium">
                {billData.provider?.name || "Unknown Provider"}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Service Date
              </label>
              <p className="text-sm text-[#1B3A5C] font-medium">
                {billData.serviceDate || "Not detected"}
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Provider ZIP Code
              </label>
              <input
                type="text"
                value={zipCode}
                onChange={(e) => setZipCode(e.target.value.replace(/\D/g, "").slice(0, 5))}
                placeholder="Enter ZIP code"
                maxLength={5}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
              />
              {(!zipCode || zipCode === "00000") && (
                <p className="text-xs text-amber-600 mt-1">
                  ZIP code is needed for accurate geographic rate lookup.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Line items */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              Extracted Line Items
            </h3>
            <span className="text-sm font-medium text-[#1B3A5C]">
              {billData.lineItems?.length || 0} item{(billData.lineItems?.length || 0) !== 1 ? "s" : ""}
            </span>
          </div>

          {billData.lineItems?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2 pr-4 text-xs font-semibold text-gray-500 uppercase">Code</th>
                    <th className="text-left py-2 pr-4 text-xs font-semibold text-gray-500 uppercase">Type</th>
                    <th className="text-left py-2 pr-4 text-xs font-semibold text-gray-500 uppercase">Description</th>
                    <th className="text-right py-2 text-xs font-semibold text-gray-500 uppercase">Billed</th>
                  </tr>
                </thead>
                <tbody>
                  {billData.lineItems.map((item, index) => (
                    <tr key={index} className="border-b border-gray-50">
                      <td className="py-2.5 pr-4 font-mono text-[#1B3A5C]">{item.code}</td>
                      <td className="py-2.5 pr-4 text-gray-500">{item.codeType}</td>
                      <td className="py-2.5 pr-4 text-gray-700">{item.description}</td>
                      <td className="py-2.5 text-right font-mono text-[#1B3A5C]">
                        {formatCurrency(item.billedAmount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-gray-200">
                    <td colSpan={3} className="py-3 text-sm font-semibold text-[#1B3A5C]">
                      Total Billed
                    </td>
                    <td className="py-3 text-right font-mono font-semibold text-[#1B3A5C]">
                      {formatCurrency(totalBilled)}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-500 italic">No line items extracted.</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleConfirm}
            disabled={!billData.lineItems?.length}
            className="px-6 py-3 text-sm font-semibold text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Run Analysis
          </button>
          <button
            onClick={onBack}
            className="text-sm text-gray-500 hover:text-gray-700 cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}
