/**
 * ManualEntryView — Full manual bill entry form.
 *
 * Accessible from:
 * 1. "Enter Bill Manually" button in AI parsing modal
 * 2. "Enter Manually" option on the upload screen
 *
 * On submit, normalizes data and feeds into the existing pipeline.
 */

import { useState, useCallback } from "react";
import { Footer } from "./UploadView.jsx";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const PROVIDER_TYPES = [
  { value: "", label: "Select type..." },
  { value: "hospital", label: "Hospital" },
  { value: "physician_office", label: "Physician Office" },
  { value: "urgent_care", label: "Urgent Care" },
  { value: "other", label: "Other" },
];

function emptyLineItem() {
  return {
    id: crypto.randomUUID(),
    cptCode: "",
    description: "",
    quantity: 1,
    billedAmount: "",
    modifier: "",
    cptLookupStatus: null, // null | "loading" | "found" | "not_found"
  };
}

export default function ManualEntryView({ onSubmit, onCancel }) {
  const [providerName, setProviderName] = useState("");
  const [serviceDate, setServiceDate] = useState("");
  const [providerType, setProviderType] = useState("");
  const [insuranceName, setInsuranceName] = useState("");
  const [providerZip, setProviderZip] = useState("");
  const [lineItems, setLineItems] = useState([emptyLineItem()]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Compute running total
  const runningTotal = lineItems.reduce((sum, item) => {
    const amt = parseFloat(item.billedAmount) || 0;
    return sum + amt * (item.quantity || 1);
  }, 0);

  // CPT code lookup
  const lookupCPT = useCallback(async (itemId, code) => {
    if (!code || code.length !== 5) return;

    setLineItems((prev) =>
      prev.map((li) =>
        li.id === itemId ? { ...li, cptLookupStatus: "loading" } : li
      )
    );

    try {
      const res = await fetch(
        `${API_BASE}/api/cpt-description?code=${encodeURIComponent(code)}`
      );
      if (!res.ok) throw new Error("Lookup failed");
      const data = await res.json();

      setLineItems((prev) =>
        prev.map((li) => {
          if (li.id !== itemId) return li;
          return {
            ...li,
            description: data.found && data.description ? data.description : li.description,
            cptLookupStatus: data.found ? "found" : "not_found",
          };
        })
      );
    } catch {
      setLineItems((prev) =>
        prev.map((li) =>
          li.id === itemId ? { ...li, cptLookupStatus: "not_found" } : li
        )
      );
    }
  }, []);

  const updateLineItem = useCallback((id, field, value) => {
    setLineItems((prev) =>
      prev.map((li) => (li.id === id ? { ...li, [field]: value } : li))
    );
  }, []);

  const addLineItem = useCallback(() => {
    setLineItems((prev) => [...prev, emptyLineItem()]);
  }, []);

  const removeLineItem = useCallback((id) => {
    setLineItems((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((li) => li.id !== id);
    });
  }, []);

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      setError("");

      // Validate
      if (!providerName.trim()) {
        setError("Provider name is required.");
        return;
      }
      if (!serviceDate) {
        setError("Service date is required.");
        return;
      }

      const validItems = lineItems.filter(
        (li) => li.cptCode.trim().length === 5 && parseFloat(li.billedAmount) > 0
      );
      if (validItems.length === 0) {
        setError("At least one line item with a valid 5-digit CPT code and amount is required.");
        return;
      }

      // Check all CPT codes are 5 chars
      for (const li of lineItems) {
        if (li.cptCode.trim() && li.cptCode.trim().length !== 5) {
          setError(`CPT code "${li.cptCode}" must be exactly 5 characters.`);
          return;
        }
      }

      setSubmitting(true);

      // Build bill data in the format the pipeline expects
      const billData = {
        provider: {
          name: providerName.trim(),
          zip: providerZip.trim() || "00000",
          npi: null,
          type: providerType || null,
        },
        serviceDate: serviceDate,
        parsingMethod: "manual",
        insuranceName: insuranceName.trim() || null,
        lineItems: validItems.map((li) => ({
          code: li.cptCode.trim(),
          codeType: "CPT",
          description: li.description.trim() || "Unknown procedure",
          billedAmount: parseFloat(li.billedAmount) * (li.quantity || 1),
          quantity: li.quantity || 1,
          modifier: li.modifier.trim() || null,
        })),
      };

      onSubmit(billData);
    },
    [providerName, serviceDate, providerType, insuranceName, providerZip, lineItems, onSubmit]
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-[Arial,sans-serif]">
      <main className="max-w-3xl mx-auto px-4 py-8 w-full flex-1">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-[#1B3A5C] mb-1">
            Manual Bill Entry
          </h2>
          <p className="text-sm text-gray-500">
            Enter your bill details below for benchmark analysis.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Section 1: Provider & Encounter */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
              Provider &amp; Encounter
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                  Provider Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={providerName}
                  onChange={(e) => setProviderName(e.target.value)}
                  placeholder="e.g. Clearwater Medical Center"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                  Service Date <span className="text-red-400">*</span>
                </label>
                <input
                  type="date"
                  value={serviceDate}
                  onChange={(e) => setServiceDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                  Provider Type
                </label>
                <select
                  value={providerType}
                  onChange={(e) => setProviderType(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377] bg-white"
                >
                  {PROVIDER_TYPES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                  Provider ZIP Code
                </label>
                <input
                  type="text"
                  value={providerZip}
                  onChange={(e) => setProviderZip(e.target.value.replace(/\D/g, "").slice(0, 5))}
                  placeholder="e.g. 33701"
                  maxLength={5}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-[#1B3A5C] mb-1">
                  Insurance Company
                </label>
                <input
                  type="text"
                  value={insuranceName}
                  onChange={(e) => setInsuranceName(e.target.value)}
                  placeholder="Optional"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
                />
              </div>
            </div>
          </div>

          {/* Section 2: Line Items */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
                Procedure Line Items
              </h3>
              <div className="text-sm font-medium text-[#1B3A5C]">
                Total: {formatCurrency(runningTotal)}
              </div>
            </div>

            <div className="space-y-4">
              {lineItems.map((item, index) => (
                <LineItemRow
                  key={item.id}
                  item={item}
                  index={index}
                  canRemove={lineItems.length > 1}
                  onUpdate={updateLineItem}
                  onRemove={removeLineItem}
                  onLookupCPT={lookupCPT}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={addLineItem}
              className="mt-4 flex items-center gap-1.5 text-sm font-medium text-[#0D7377] hover:text-[#0B6164] cursor-pointer"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add Another Procedure
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Section 3: Submit */}
          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={submitting}
              className="px-6 py-3 text-sm font-semibold text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {submitting ? "Analyzing..." : "Analyze This Bill"}
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="text-sm text-gray-500 hover:text-gray-700 cursor-pointer"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </main>

      <Footer />
    </div>
  );
}

function LineItemRow({ item, index, canRemove, onUpdate, onRemove, onLookupCPT }) {
  const handleCPTBlur = () => {
    if (item.cptCode.trim().length === 5) {
      onLookupCPT(item.id, item.cptCode.trim());
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-gray-400">
          Item {index + 1}
        </span>
        {canRemove && (
          <button
            type="button"
            onClick={() => onRemove(item.id)}
            className="p-1 text-gray-400 hover:text-red-500 rounded hover:bg-red-50 cursor-pointer"
            title="Remove"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </button>
        )}
      </div>

      <div className="grid grid-cols-12 gap-3">
        {/* CPT Code */}
        <div className="col-span-12 sm:col-span-3">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            CPT Code
          </label>
          <input
            type="text"
            value={item.cptCode}
            onChange={(e) =>
              onUpdate(item.id, "cptCode", e.target.value.replace(/\D/g, "").slice(0, 5))
            }
            onBlur={handleCPTBlur}
            placeholder="99213"
            maxLength={5}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
          />
          {item.cptLookupStatus === "loading" && (
            <p className="text-xs text-gray-400 mt-1">Looking up...</p>
          )}
          {item.cptLookupStatus === "found" && item.description && (
            <p className="text-xs text-[#0D7377] mt-1 truncate">
              {item.cptCode} — {item.description}
            </p>
          )}
          {item.cptLookupStatus === "not_found" && item.cptCode.length === 5 && (
            <p className="text-xs text-amber-600 mt-1">Code not in CMS database</p>
          )}
        </div>

        {/* Description */}
        <div className="col-span-12 sm:col-span-4">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Description
          </label>
          <input
            type="text"
            value={item.description}
            onChange={(e) => onUpdate(item.id, "description", e.target.value)}
            placeholder="Procedure description"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
          />
        </div>

        {/* Quantity */}
        <div className="col-span-4 sm:col-span-1">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Qty
          </label>
          <input
            type="number"
            value={item.quantity}
            onChange={(e) =>
              onUpdate(item.id, "quantity", Math.max(1, parseInt(e.target.value) || 1))
            }
            min={1}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-center focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
          />
        </div>

        {/* Amount */}
        <div className="col-span-4 sm:col-span-2">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Amount Billed
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">
              $
            </span>
            <input
              type="number"
              value={item.billedAmount}
              onChange={(e) => onUpdate(item.id, "billedAmount", e.target.value)}
              placeholder="0.00"
              step="0.01"
              min="0"
              className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
            />
          </div>
        </div>

        {/* Modifier */}
        <div className="col-span-4 sm:col-span-2">
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Modifier
          </label>
          <input
            type="text"
            value={item.modifier}
            onChange={(e) =>
              onUpdate(item.id, "modifier", e.target.value.toUpperCase().slice(0, 2))
            }
            placeholder="--"
            maxLength={2}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-center font-mono focus:outline-none focus:ring-2 focus:ring-[#0D7377]/30 focus:border-[#0D7377]"
          />
        </div>
      </div>
    </div>
  );
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}
