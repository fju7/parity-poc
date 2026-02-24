/**
 * extractBillData.js — Browser-side PDF extraction for medical bills.
 *
 * Uses PDF.js to parse a PDF File object entirely in the browser.
 * No data is sent to any server during this step.
 *
 * @param {File} file - A PDF File object from a file input or drag-and-drop
 * @returns {Promise<{
 *   provider: { name: string, zip: string, npi: string|null },
 *   serviceDate: string,
 *   lineItems: Array<{ code: string, codeType: "CPT"|"REVENUE"|"UNKNOWN", description: string, billedAmount: number }>
 * }>}
 */

import * as pdfjsLib from "pdfjs-dist";

// Configure the PDF.js web worker for browser environments.
// In Node/test environments, workerSrc is set to "" by the test setup
// which causes PDF.js to use its inline fake worker instead.
const isNode =
  typeof process !== "undefined" && process.versions && process.versions.node;
if (!isNode) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.mjs",
    import.meta.url
  ).toString();
}

// ---------------------------------------------------------------------------
// Regex patterns
// ---------------------------------------------------------------------------

// CPT codes: 5-digit numbers (00100–99499 range typical, but we accept any 5-digit)
const CPT_PATTERN = /\b(\d{5})\b/;

// Revenue codes: 4-digit numbers on facility/hospital bills (0100-0999 range typical)
const REVENUE_PATTERN = /\b(0\d{3})\b/;

// Dollar amounts: $1,234.56 or 1234.56 or 1,234.56
const DOLLAR_PATTERN = /\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2}))/g;

// ZIP code: 5-digit, optionally followed by -4 extension
const ZIP_PATTERN = /\b(\d{5})(?:-\d{4})?\b/;

// NPI: 10-digit number, often preceded by "NPI"
const NPI_PATTERN = /\bNPI[:#\s]*(\d{10})\b/i;

// Date patterns: MM/DD/YYYY, MM-DD-YYYY, Month DD YYYY, etc.
const DATE_PATTERNS = [
  /\b(\d{1,2}\/\d{1,2}\/\d{4})\b/,
  /\b(\d{1,2}-\d{1,2}-\d{4})\b/,
  /\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b/i,
];

// Keywords that often precede the provider/facility name
const PROVIDER_KEYWORDS =
  /(?:hospital|medical center|health|clinic|physician|healthcare|surgery center)/i;

// Service-related keywords that help identify line-item rows
const SERVICE_KEYWORDS =
  /(?:CPT|HCPCS|procedure|service|charge|code|revenue)/i;

// Date-of-service keywords
const DATE_KEYWORDS =
  /(?:date of service|service date|dos|date\(s\) of service|stmt date|statement date)/i;

// ---------------------------------------------------------------------------
// Main extraction function
// ---------------------------------------------------------------------------

export default async function extractBillData(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  const pages = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    pages.push(content);
  }

  // Build structured lines from text items, preserving spatial layout
  const allLines = [];
  for (const content of pages) {
    const lines = buildLines(content.items);
    allLines.push(...lines);
  }

  const fullText = allLines.map((l) => l.text).join("\n");

  const provider = extractProvider(allLines, fullText);
  const serviceDate = extractServiceDate(fullText);
  const lineItems = extractLineItems(allLines);
  const patientName = extractPatientName(allLines, fullText);
  const accountNumber = extractAccountNumber(fullText);

  return { provider, serviceDate, lineItems, patientName, accountNumber };
}

// ---------------------------------------------------------------------------
// Spatial line grouping
// ---------------------------------------------------------------------------

/**
 * Groups text items into lines based on their Y-coordinate.
 * Items within a small vertical tolerance are considered the same line.
 * Items are sorted left-to-right within each line.
 */
function buildLines(items) {
  if (!items.length) return [];

  // Group by approximate Y position (transform[5] is the Y coordinate)
  const yTolerance = 3;
  const buckets = [];

  for (const item of items) {
    if (!item.str || !item.str.trim()) continue;
    const y = item.transform[5];
    const x = item.transform[4];

    let placed = false;
    for (const bucket of buckets) {
      if (Math.abs(bucket.y - y) < yTolerance) {
        bucket.items.push({ text: item.str, x });
        placed = true;
        break;
      }
    }
    if (!placed) {
      buckets.push({ y, items: [{ text: item.str, x }] });
    }
  }

  // Sort buckets top-to-bottom (higher Y = higher on page in PDF coords)
  buckets.sort((a, b) => b.y - a.y);

  return buckets.map((bucket) => {
    bucket.items.sort((a, b) => a.x - b.x);
    const text = bucket.items.map((i) => i.text).join("  ");
    return { text, y: bucket.y };
  });
}

// ---------------------------------------------------------------------------
// Provider extraction
// ---------------------------------------------------------------------------

function extractProvider(lines, fullText) {
  let name = "";
  let zip = "";
  let npi = null;

  // NPI: search entire text
  const npiMatch = fullText.match(NPI_PATTERN);
  if (npiMatch) npi = npiMatch[1];

  // Provider name: look in the first ~15 lines for hospital/medical-sounding names
  const headerLines = lines.slice(0, 20);

  for (const line of headerLines) {
    if (PROVIDER_KEYWORDS.test(line.text) && !name) {
      // Clean up: take the part that looks like a name
      name = line.text
        .replace(/\s{2,}/g, " ")
        .trim()
        .split(/\s{2,}|[|]/)[0]
        .trim();
      break;
    }
  }

  // If no keyword match, use the first substantial non-numeric line as provider name
  if (!name) {
    for (const line of headerLines) {
      const cleaned = line.text.replace(/\s{2,}/g, " ").trim();
      if (
        cleaned.length > 5 &&
        !/^\d+$/.test(cleaned) &&
        !/^(page|date|account|patient|statement|total|balance)/i.test(cleaned)
      ) {
        name = cleaned.split(/\s{2,}|[|]/)[0].trim();
        break;
      }
    }
  }

  // ZIP: look for a 5-digit ZIP near the provider name area (first 15 lines)
  // Prefer one that appears after a state abbreviation pattern
  const stateZipPattern = /\b[A-Z]{2}\s+(\d{5})(?:-\d{4})?\b/;
  for (const line of headerLines) {
    const stateMatch = line.text.match(stateZipPattern);
    if (stateMatch) {
      zip = stateMatch[1];
      break;
    }
  }

  // Fallback: any 5-digit ZIP in header
  if (!zip) {
    for (const line of headerLines) {
      const m = line.text.match(ZIP_PATTERN);
      if (m && !isCPTLikeCode(m[1])) {
        zip = m[1];
        break;
      }
    }
  }

  return { name, zip, npi };
}

// ---------------------------------------------------------------------------
// Service date extraction
// ---------------------------------------------------------------------------

function extractServiceDate(fullText) {
  // First look for a date near a date-of-service keyword
  const dosSection = fullText.match(
    /(?:date of service|service date|dos|date\(s\) of service)[:\s]*([\s\S]{0,60})/i
  );

  if (dosSection) {
    for (const pattern of DATE_PATTERNS) {
      const m = dosSection[1].match(pattern);
      if (m) return m[1];
    }
  }

  // Look for "Statement Date" or similar
  const stmtSection = fullText.match(
    /(?:stmt\.?\s*date|statement\s*date|billing\s*date)[:\s]*([\s\S]{0,60})/i
  );
  if (stmtSection) {
    for (const pattern of DATE_PATTERNS) {
      const m = stmtSection[1].match(pattern);
      if (m) return m[1];
    }
  }

  // Fallback: find any date in the document
  for (const pattern of DATE_PATTERNS) {
    const m = fullText.match(pattern);
    if (m) return m[1];
  }

  return "";
}

// ---------------------------------------------------------------------------
// Line item extraction
// ---------------------------------------------------------------------------

function extractLineItems(lines) {
  const items = [];
  const seen = new Set();

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const text = line.text;

    // Skip header/label rows
    if (SERVICE_KEYWORDS.test(text) && !CPT_PATTERN.test(text)) continue;
    if (/^\s*(sub)?total|balance|amount due|payment|adjustment/i.test(text))
      continue;

    // Try to extract a line item from this row
    const item = parseLineItem(text);
    if (item) {
      // Deduplicate: same code + same amount on the same line
      const key = `${item.code}-${item.billedAmount}`;
      if (!seen.has(key)) {
        seen.add(key);
        items.push(item);
      }
    }
  }

  return items;
}

/**
 * Attempt to parse a single text line into a line item.
 * Returns null if the line doesn't look like a billable item.
 */
function parseLineItem(text) {
  // Must contain at least one dollar amount
  const amounts = extractDollarAmounts(text);
  if (amounts.length === 0) return null;

  // Try to find a CPT code (5-digit)
  let code = null;
  let codeType = "UNKNOWN";

  // Look for explicit CPT label
  const cptLabeled = text.match(/(?:CPT|HCPCS|Proc(?:edure)?)[:\s#]*(\d{5})\b/i);
  if (cptLabeled) {
    code = cptLabeled[1];
    codeType = "CPT";
  }

  // Look for a standalone 5-digit code if no labeled match
  if (!code) {
    const fiveDigit = text.match(/\b(\d{5})\b/);
    if (fiveDigit && isCPTLikeCode(fiveDigit[1])) {
      code = fiveDigit[1];
      codeType = "CPT";
    }
  }

  // Look for a revenue code (4-digit starting with 0)
  if (!code) {
    const revMatch = text.match(REVENUE_PATTERN);
    if (revMatch) {
      code = revMatch[1];
      codeType = "REVENUE";
    }
  }

  // If we still have no code, skip this line
  if (!code) return null;

  // The billed amount is typically the largest dollar amount on the line,
  // or the last one (rightmost column in a table)
  const billedAmount = amounts[amounts.length - 1];

  // Description: text between the code and the dollar amount, cleaned up
  const description = extractDescription(text, code);

  return { code, codeType, description, billedAmount };
}

// ---------------------------------------------------------------------------
// Patient name extraction
// ---------------------------------------------------------------------------

function extractPatientName(lines, fullText) {
  // Look for labels like "Patient:", "Member:", "Insured:", "Subscriber:"
  const labelPattern =
    /(?:Patient|Member|Insured|Subscriber)\s*(?:Name)?\s*[:\s]\s*([A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+){1,3})/i;

  // First check structured lines for better context
  for (const line of lines) {
    const m = line.text.match(labelPattern);
    if (m) return m[1].trim();
  }

  // Fallback: search full text
  const m = fullText.match(labelPattern);
  if (m) return m[1].trim();

  return "";
}

// ---------------------------------------------------------------------------
// Account number extraction
// ---------------------------------------------------------------------------

function extractAccountNumber(fullText) {
  // Look for account/claim/reference number labels followed by an alphanumeric ID
  const patterns = [
    /(?:Account|Acct)[\s.#:]*(?:Number|No|#)?[\s.#:]*([A-Z0-9][\w-]{3,20})/i,
    /(?:Claim|Reference|Ref)[\s.#:]*(?:Number|No|#)?[\s.#:]*([A-Z0-9][\w-]{3,20})/i,
    /(?:Patient\s*ID|Member\s*ID)[\s.#:]*([A-Z0-9][\w-]{3,20})/i,
  ];

  for (const pattern of patterns) {
    const m = fullText.match(pattern);
    if (m) return m[1].trim();
  }

  return "";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extract all dollar amounts from a text string.
 * Returns sorted array of numbers.
 */
function extractDollarAmounts(text) {
  const amounts = [];
  let match;
  const pattern = new RegExp(DOLLAR_PATTERN.source, "g");
  while ((match = pattern.exec(text)) !== null) {
    const num = parseFloat(match[1].replace(/,/g, ""));
    if (num > 0) amounts.push(num);
  }
  return amounts;
}

/**
 * Heuristic: is this 5-digit number likely a CPT code?
 * Filter out things like ZIP codes or years embedded in text.
 */
function isCPTLikeCode(num) {
  const n = parseInt(num, 10);
  // CPT ranges: 00100-01999 (anesthesia), 10004-69990 (surgery/medicine),
  // 70010-79999 (radiology), 80047-89398 (path/lab), 90281-99607 (medicine/E&M)
  // Revenue codes (0100-0999) are handled separately.
  // Exclude obvious non-CPT: years (2020-2030), very round numbers
  if (n >= 2020 && n <= 2030) return false;
  if (n >= 10000 && n <= 99999) return true;
  if (n >= 100 && n <= 1999) return true; // anesthesia codes
  return false;
}

/**
 * Extract a description from the line text, stripping out the code and amounts.
 */
function extractDescription(text, code) {
  let desc = text;

  // Remove the code itself
  desc = desc.replace(code, "");

  // Remove dollar amounts
  desc = desc.replace(/\$?\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})/g, "");

  // Remove common column headers/labels
  desc = desc.replace(
    /\b(CPT|HCPCS|Proc|Rev|Code|Qty|Units?|Charges?|Amount)\b/gi,
    ""
  );

  // Remove dates (they might be inline)
  desc = desc.replace(/\d{1,2}[/-]\d{1,2}[/-]\d{2,4}/g, "");

  // Clean up whitespace and separators
  desc = desc.replace(/[|]/g, " ").replace(/\s{2,}/g, " ").trim();

  // Remove leading/trailing punctuation
  desc = desc.replace(/^[\s\-:,.*]+|[\s\-:,.*]+$/g, "").trim();

  return desc || "Unknown procedure";
}
