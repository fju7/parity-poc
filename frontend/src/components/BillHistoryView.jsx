import { useState, useEffect } from "react";
import { getAllBills, deleteBill, exportAllBills } from "../lib/localBillStore.js";
import { Footer } from "./UploadView.jsx";

export default function BillHistoryView({ onViewBill, onNavigate }) {
  const [bills, setBills] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function fetchBills() {
      try {
        const data = await getAllBills();
        if (!cancelled) setBills(data);
      } catch (err) {
        console.error("Failed to load bill history:", err);
      }
      if (!cancelled) setLoading(false);
    }

    fetchBills();
    return () => { cancelled = true; };
  }, []);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await deleteBill(id);
      setBills((prev) => prev.filter((b) => b.id !== id));
    } catch (err) {
      console.error("Failed to delete bill:", err);
    }
  };

  const handleExport = async () => {
    try {
      const json = await exportAllBills();
      const blob = new Blob([json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "parity-bill-history.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export bills:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-[Arial,sans-serif]">
      <main className="max-w-5xl mx-auto px-4 py-8 w-full flex-1">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-[#1B3A5C]">Bill History</h2>
          {bills.length > 0 && (
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 text-sm font-medium text-[#0D7377] hover:text-[#0B6164] cursor-pointer"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              Export My History
            </button>
          )}
        </div>

        {loading ? (
          <div className="text-center py-16">
            <p className="text-gray-400 text-sm">Loading...</p>
          </div>
        ) : bills.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-500 mb-4">No analyses yet. Upload a bill to get started.</p>
            <button
              onClick={() => onNavigate("upload")}
              className="text-sm font-medium text-[#0D7377] hover:underline cursor-pointer"
            >
              Upload a bill
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-gray-500 text-xs uppercase tracking-wider">
                  <th className="px-6 py-3 font-medium">Provider</th>
                  <th className="px-6 py-3 font-medium">Service Date</th>
                  <th className="px-6 py-3 font-medium text-right">Total Billed</th>
                  <th className="px-6 py-3 font-medium text-center">Flagged</th>
                  <th className="px-6 py-3 font-medium text-right">Analyzed</th>
                  <th className="px-6 py-3 font-medium w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {bills.map((bill) => (
                  <tr
                    key={bill.id}
                    onClick={() => onViewBill(bill.id)}
                    className="hover:bg-gray-50 cursor-pointer"
                  >
                    <td className="px-6 py-4 text-[#1B3A5C] font-medium">
                      {bill.provider?.name || "Unknown Provider"}
                    </td>
                    <td className="px-6 py-4 text-gray-600">
                      {bill.serviceDate || "\u2014"}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-[#1B3A5C]">
                      {formatCurrency(bill.summary?.totalBilled)}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {bill.summary?.flaggedItemCount > 0 ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                          {bill.summary.flaggedItemCount} of {bill.summary.totalItemCount}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">None</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right text-gray-500 text-xs">
                      {formatDate(bill.createdAt)}
                    </td>
                    <td className="px-2 py-4 text-center">
                      <button
                        onClick={(e) => handleDelete(e, bill.id)}
                        className="p-1.5 text-gray-400 hover:text-red-500 rounded-lg hover:bg-red-50 cursor-pointer"
                        title="Delete"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}

function formatCurrency(amount) {
  if (amount == null) return "\u2014";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

function formatDate(iso) {
  if (!iso) return "\u2014";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
