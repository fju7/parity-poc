/**
 * eobExtractor.js — Detects Explanation of Benefits (EOBs) and extracts
 * structured data from them. Pure functions, no server calls.
 */

// ---------------------------------------------------------------------------
// Known insurance company names (for detection + extraction)
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

// ---------------------------------------------------------------------------
// EOB Data Extraction
// ---------------------------------------------------------------------------

/**
 * Extracts structured data from an EOB document.
 *
 * @param {string} rawText - Full text extracted from PDF
 * @param {Array<{text: string, y: number}>} rawLines - Structured lines from PDF
 * @returns {{
 *   insuranceCompany: string,
 *   providerName: string,
 *   claimNumber: string,
 *   memberID: string,
 *   serviceDate: string,
 *   totalBilled: number|null,
 *   planPaid: number|null,
 *   patientResponsibility: number|null,
 *   groupNumber: string,
 *   patientName: string
 * }}
 */
export function extractEOBData(rawText, rawLines) {
  const lineTexts = rawLines.map((l) => (typeof l === "string" ? l : l.text));

  return {
    insuranceCompany: extractInsuranceCompany(lineTexts),
    providerName: extractProviderFromEOB(rawText, lineTexts),
    claimNumber: extractClaimNumber(rawText),
    memberID: extractMemberID(rawText),
    serviceDate: extractServiceDate(rawText),
    totalBilled: extractEOBAmount(rawText, "billed"),
    planPaid: extractEOBAmount(rawText, "planPaid"),
    patientResponsibility: extractEOBAmount(rawText, "patientOwes"),
    groupNumber: extractGroupNumber(rawText),
    patientName: extractPatientName(rawText),
  };
}

// ---------------------------------------------------------------------------
// Individual extraction functions
// ---------------------------------------------------------------------------

function extractInsuranceCompany(lineTexts) {
  // Check first 10 lines for a known insurer name
  const headerLines = lineTexts.slice(0, 10);
  for (const line of headerLines) {
    const match = line.match(INSURER_REGEX);
    if (match) return match[0];
  }

  // Fallback: scan all lines
  for (const line of lineTexts) {
    const match = line.match(INSURER_REGEX);
    if (match) return match[0];
  }

  return "";
}

function extractClaimNumber(text) {
  const patterns = [
    /(?:Claim|Claim\s*#|Claim\s*Number|Claim\s*No\.?)[:\s#]*([A-Z0-9][\w-]{4,30})/i,
    /(?:Claim\s*ID)[:\s#]*([A-Z0-9][\w-]{4,30})/i,
    /(?:Reference\s*#|Reference\s*Number|Ref\s*#)[:\s]*([A-Z0-9][\w-]{4,30})/i,
  ];

  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) return m[1].trim();
  }
  return "";
}

function extractMemberID(text) {
  const patterns = [
    /(?:Member\s*(?:ID|#|Number|No\.?))[:\s#]*([A-Z0-9][\w-]{4,30})/i,
    /(?:Subscriber\s*(?:ID|#|Number|No\.?))[:\s#]*([A-Z0-9][\w-]{4,30})/i,
    /(?:ID\s*Number|Identification\s*(?:#|Number))[:\s#]*([A-Z0-9][\w-]{4,30})/i,
    /(?:Insured\s*(?:ID|#))[:\s#]*([A-Z0-9][\w-]{4,30})/i,
  ];

  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) return m[1].trim();
  }
  return "";
}

function extractGroupNumber(text) {
  const patterns = [
    /(?:Group\s*(?:#|Number|No\.?|ID))[:\s#]*([A-Z0-9][\w-]{2,20})/i,
    /(?:Policy\s*(?:#|Number|No\.?))[:\s#]*([A-Z0-9][\w-]{2,20})/i,
  ];

  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) return m[1].trim();
  }
  return "";
}

function extractProviderFromEOB(text, lineTexts) {
  // Look for "Provider:" or "Provider Name:" labels
  const patterns = [
    /(?:Provider|Rendering\s*Provider|Servicing\s*Provider|Doctor|Physician)[:\s]+([A-Z][A-Za-z\s.,'-]{3,60})/i,
    /(?:Services?\s*(?:provided|rendered)\s*by)[:\s]+([A-Z][A-Za-z\s.,'-]{3,60})/i,
  ];

  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) {
      // Clean up: stop at common trailing text
      return m[1]
        .replace(/\s*(Date|Claim|Service|Amount|Total|NPI|Tax).*$/i, "")
        .trim();
    }
  }

  // Try line-by-line for "Provider" label
  for (const line of lineTexts) {
    const m = line.match(
      /(?:Provider|Doctor|Physician)[:\s]+([A-Z][A-Za-z\s.,'-]{3,50})/i
    );
    if (m) {
      return m[1]
        .replace(/\s*(Date|Claim|Service|Amount).*$/i, "")
        .trim();
    }
  }

  return "";
}

function extractServiceDate(text) {
  const patterns = [
    /(?:Date(?:s)?\s*of\s*Service|Service\s*Date|DOS|Service\s*From)[:\s]*([\d]{1,2}[/-][\d]{1,2}[/-][\d]{2,4})/i,
    /(?:Date(?:s)?\s*of\s*Service|Service\s*Date|DOS)[:\s]*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})/i,
  ];

  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) return m[1].trim();
  }
  return "";
}

function extractPatientName(text) {
  const patterns = [
    /(?:Patient|Member|Subscriber|Insured)\s*(?:Name)?[:\s]+([A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+){1,3})/i,
  ];

  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) return m[1].trim();
  }
  return "";
}

/**
 * Extract dollar amounts near specific EOB labels.
 * @param {string} text
 * @param {"billed"|"planPaid"|"patientOwes"} type
 * @returns {number|null}
 */
function extractEOBAmount(text, type) {
  const labelMap = {
    billed: [
      /(?:Amount\s*Billed|Billed\s*Charges?|Total\s*Charges?|Amount\s*Charged|Provider\s*Charged)[:\s]*\$?\s?([\d,]+\.\d{2})/i,
      /(?:Total\s*Billed)[:\s]*\$?\s?([\d,]+\.\d{2})/i,
    ],
    planPaid: [
      /(?:(?:What\s*)?Plan\s*Paid|Insurance\s*Paid|We\s*Paid|Amount\s*Paid\s*(?:by\s*Plan)?|Paid\s*Amount)[:\s]*\$?\s?([\d,]+\.\d{2})/i,
      /(?:Total\s*(?:Plan|Insurance)\s*(?:Payment|Paid))[:\s]*\$?\s?([\d,]+\.\d{2})/i,
    ],
    patientOwes: [
      /(?:What\s*(?:I|You)\s*Owe|(?:Your|Patient)\s*Responsibility|Amount\s*You\s*Owe|You\s*May\s*Owe|Patient\s*(?:Owes|Balance))[:\s]*\$?\s?([\d,]+\.\d{2})/i,
      /(?:Total\s*(?:Patient|Your)\s*(?:Responsibility|Amount))[:\s]*\$?\s?([\d,]+\.\d{2})/i,
    ],
  };

  const patterns = labelMap[type] || [];
  for (const pattern of patterns) {
    const m = text.match(pattern);
    if (m) {
      return parseFloat(m[1].replace(/,/g, ""));
    }
  }
  return null;
}
