/**
 * AIParseModal — Privacy disclosure modal for AI-assisted bill reading.
 *
 * Shows when standard parsing finds <2 line items or user clicks "Having trouble?".
 * Offers three choices: use AI reading, enter manually, or skip.
 */

export default function AIParseModal({ onUseAI, onManualEntry, onSkip, itemCount }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full p-8 font-[Arial,sans-serif]">
        <h2 className="text-xl font-bold text-[#1B3A5C] mb-2">
          Try AI-Assisted Reading?
        </h2>
        <p className="text-sm text-gray-600 mb-4 leading-relaxed">
          Our automatic reader {itemCount === 0 ? "couldn't find any procedure codes in" : `only found ${itemCount} item${itemCount === 1 ? "" : "s"} in`} this
          bill. Claude AI can read almost any bill layout with higher accuracy.
        </p>

        {/* Privacy disclosure */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 text-amber-600 shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
              />
            </svg>
            <div>
              <p className="text-sm font-semibold text-amber-800 mb-1">
                Privacy note
              </p>
              <p className="text-xs text-amber-700 leading-relaxed">
                AI-assisted reading sends your bill content to Anthropic&apos;s Claude
                API for processing. Your bill is not stored or used for training.
                This is the only feature in Parity Health that sends health data
                outside your device.
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={onUseAI}
            className="w-full px-4 py-3 text-sm font-semibold text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer transition-colors"
          >
            Use AI Reading
          </button>
          <button
            onClick={onManualEntry}
            className="w-full px-4 py-3 text-sm font-semibold text-[#1B3A5C] border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
          >
            Enter Bill Manually
          </button>
          {itemCount > 0 && (
            <button
              onClick={onSkip}
              className="w-full text-center text-xs text-gray-400 hover:text-gray-600 cursor-pointer py-2"
            >
              Skip — Use What Was Found
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
