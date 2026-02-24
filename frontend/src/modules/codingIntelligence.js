/**
 * Coding Intelligence — client-side checks + merge with backend alerts.
 *
 * Check 3: E&M complexity pattern — flags high-level E&M codes with
 *          an informational note about documentation requirements.
 * Check 4: Site-of-service mismatch — flags office-setting codes that
 *          appear on a bill from a facility (inferred from provider name).
 */

// Codes that are typically billed in a physician office setting
const OFFICE_SETTING_CODES = new Set([
  "99213", "99214", "99215", // Office visits (established patient)
  "93000",                   // ECG, 12-lead
  "71046",                   // Chest X-ray, 2 views
  "80053",                   // Comprehensive metabolic panel
]);

// Keywords in provider names that suggest a facility setting
const FACILITY_KEYWORDS = [
  "hospital",
  "medical center",
  "health system",
  "regional medical",
  "community health",
  "memorial",
];

// High-level E&M codes that warrant documentation review
const HIGH_LEVEL_EM_CODES = new Set(["99215", "99223", "99233", "99291"]);

/**
 * Run client-side coding intelligence checks and merge with backend alerts.
 *
 * @param {object} billData - Extracted bill data with provider info and line items
 * @param {Array}  backendAlerts - codingAlerts array from the /api/benchmark response
 * @returns {{ codingAlerts: Array, codingSummary: object }}
 */
export default function runCodingIntelligence(billData, backendAlerts = []) {
  const frontendAlerts = [];

  const codes = (billData.lineItems || []).map((item) => item.code);

  // Check 3: E&M complexity pattern
  frontendAlerts.push(...checkEmComplexity(codes));

  // Check 4: Site-of-service mismatch
  frontendAlerts.push(...checkSiteOfService(codes, billData.provider));

  // Merge — backend alerts first (higher confidence), then frontend
  const codingAlerts = [...backendAlerts, ...frontendAlerts];

  // Summary
  const highConfidenceCount = codingAlerts.filter(
    (a) => a.confidence === "high"
  ).length;
  const mediumConfidenceCount = codingAlerts.filter(
    (a) => a.confidence === "medium"
  ).length;

  return {
    codingAlerts,
    codingSummary: {
      totalAlerts: codingAlerts.length,
      highConfidenceCount,
      mediumConfidenceCount,
    },
  };
}

/**
 * Check 3: Flag high-level E&M codes with informational note.
 */
function checkEmComplexity(codes) {
  const alerts = [];
  const seen = new Set();

  for (const code of codes) {
    if (HIGH_LEVEL_EM_CODES.has(code) && !seen.has(code)) {
      seen.add(code);
      alerts.push({
        checkType: "EM_COMPLEXITY",
        codes: [code],
        confidence: "medium",
        severity: "info",
        message:
          `CPT ${code} is a high-level E&M code that requires extensive ` +
          `documentation of medical decision-making complexity. Ensure the ` +
          `clinical documentation supports this level of service.`,
        source: "CMS E&M Guidelines 2026",
      });
    }
  }

  return alerts;
}

/**
 * Check 4: Flag office-setting codes billed by a facility provider.
 */
function checkSiteOfService(codes, provider) {
  if (!provider?.name) return [];

  const nameLower = provider.name.toLowerCase();
  const isFacility = FACILITY_KEYWORDS.some((kw) => nameLower.includes(kw));
  if (!isFacility) return [];

  const alerts = [];
  const seen = new Set();

  for (const code of codes) {
    if (OFFICE_SETTING_CODES.has(code) && !seen.has(code)) {
      seen.add(code);
      alerts.push({
        checkType: "SITE_OF_SERVICE",
        codes: [code],
        confidence: "medium",
        severity: "info",
        message:
          `CPT ${code} is typically billed in an office setting, but this ` +
          `bill is from "${provider.name}" which appears to be a facility. ` +
          `Facility billing for this code may result in higher charges. ` +
          `Verify the place of service is correct.`,
        source: "CMS Place of Service Codes",
      });
    }
  }

  return alerts;
}
