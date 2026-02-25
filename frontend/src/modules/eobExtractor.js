/**
 * eobExtractor.js — Detects Explanation of Benefits (EOBs).
 *
 * Detection is regex-based (fast, runs client-side).
 * Extraction is handled by the /api/parse-eob AI endpoint.
 */

// ---------------------------------------------------------------------------
// Known insurance company names (for detection)
// ---------------------------------------------------------------------------

const KNOWN_INSURERS = [
  "Cigna",
  "Aetna",
  "UnitedHealthcare",
  "United Healthcare",
  "UHC",
  "Blue Cross",
  "Blue Shield",
  "BlueCross",
  "BlueShield",
  "BCBS",
  "Humana",
  "Anthem",
  "Kaiser",
  "Kaiser Permanente",
  "Molina",
  "Centene",
  "Ambetter",
  "Coventry",
  "HealthFirst",
  "Health First",
  "Oscar Health",
  "Oscar",
  "Bright Health",
  "Medicare",
  "Medicaid",
  "Tricare",
  "Highmark",
  "CareFirst",
  "Premera",
  "Regence",
  "Wellcare",
  "Amerihealth",
  "Carefirst",
  "EmblemHealth",
  "Health Net",
  "Medical Mutual",
  "Priority Health",
];

// Build a single regex from insurer names (case-insensitive)
const INSURER_REGEX = new RegExp(
  KNOWN_INSURERS.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|"),
  "i"
);

// ---------------------------------------------------------------------------
// EOB Detection
// ---------------------------------------------------------------------------

/**
 * Detects whether the extracted text is from an Explanation of Benefits
 * rather than a provider bill.
 *
 * @param {string} rawText - Full text extracted from PDF
 * @returns {boolean}
 */
export function detectEOB(rawText) {
  if (!rawText) return false;

  const upper = rawText.toUpperCase();

  // Strong indicators — immediate true
  if (upper.includes("EXPLANATION OF BENEFITS")) return true;
  if (upper.includes("THIS IS NOT A BILL")) return true;
  if (upper.includes("THIS IS NOT AN INVOICE")) return true;
  if (upper.includes("EOB STATEMENT")) return true;

  // Column pattern — all three required for a match
  const hasAmountBilled =
    upper.includes("AMOUNT BILLED") ||
    upper.includes("BILLED CHARGES") ||
    upper.includes("AMOUNT CHARGED") ||
    upper.includes("PROVIDER CHARGED");
  const hasPlanPaid =
    upper.includes("WHAT PLAN PAID") ||
    upper.includes("PLAN PAID") ||
    upper.includes("INSURANCE PAID") ||
    upper.includes("AMOUNT PAID BY PLAN") ||
    upper.includes("WE PAID");
  const hasPatientOwes =
    upper.includes("WHAT I OWE") ||
    upper.includes("WHAT YOU OWE") ||
    upper.includes("YOUR RESPONSIBILITY") ||
    upper.includes("PATIENT RESPONSIBILITY") ||
    upper.includes("AMOUNT YOU OWE") ||
    upper.includes("YOU MAY OWE");

  if (hasAmountBilled && hasPlanPaid && hasPatientOwes) return true;

  // Known insurer in first 30% of text + "claim" keyword
  const firstThird = rawText.slice(0, Math.floor(rawText.length * 0.3));
  if (INSURER_REGEX.test(firstThird) && /\bclaim\b/i.test(firstThird)) {
    // Additional confirmation: look for EOB-like phrases
    if (
      /\b(?:member|subscriber|group\s*(?:number|#|no)|plan\s*paid|benefit|coverage)\b/i.test(
        rawText
      )
    ) {
      return true;
    }
  }

  return false;
}
