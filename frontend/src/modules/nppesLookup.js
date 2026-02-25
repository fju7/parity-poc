/**
 * nppesLookup.js — Looks up provider contact information via the public
 * CMS NPPES NPI Registry API, proxied through our backend (NPPES has no CORS).
 *
 * API docs: https://npiregistry.cms.hhs.gov/api-page
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TIMEOUT_MS = 15000;

/**
 * Look up an organization provider by name via NPPES.
 *
 * @param {string} providerName - The provider/organization name to search
 * @returns {Promise<{found: boolean, bestMatch: {npi: string, name: string, address: {line1: string, city: string, state: string, zip: string}, phone: string}}|null>}
 *   Returns null on network/timeout errors (graceful failure).
 */
export async function lookupNPPES(providerName) {
  if (!providerName || providerName.trim().length < 3) {
    return null;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    // Try exact name first, then wildcard variations for abbreviated names
    const searchNames = buildSearchVariations(providerName);
    console.log("[NPPES] Searching for:", searchNames);

    for (const name of searchNames) {
      const orgResult = await searchNPPES(name, "NPI-2", controller.signal);
      if (orgResult) {
        console.log("[NPPES] Found org match:", orgResult.bestMatch?.name);
        clearTimeout(timeoutId);
        return orgResult;
      }
    }

    // Fallback: try individual provider (NPI-1) with original name
    const indResult = await searchNPPES(providerName.trim(), "NPI-1", controller.signal);
    if (indResult) {
      console.log("[NPPES] Found individual match:", indResult.bestMatch?.name);
    } else {
      console.log("[NPPES] No results found for:", providerName);
    }
    clearTimeout(timeoutId);
    return indResult || { found: false, bestMatch: null };
  } catch (err) {
    // Network error, timeout, or abort — graceful failure
    console.warn("[NPPES] Lookup failed:", err.message);
    clearTimeout(timeoutId);
    return null;
  }
}

/**
 * Build search name variations for NPPES.
 * NPPES organization_name supports wildcard (*) for partial matching.
 * Abbreviated names like "H LEE MOFFITT CANCER CTR" need shorter search terms.
 */
function buildSearchVariations(name) {
  const cleaned = name.trim();
  const variations = [cleaned];

  // Add wildcard version: "MOFFITT*" from "H LEE MOFFITT CANCER CTR"
  // Strategy: find the longest meaningful word (4+ chars, not a common prefix)
  const SKIP_WORDS = new Set([
    "THE", "OF", "AND", "AT", "FOR", "IN", "CTR", "CENTER", "CENTRE",
    "HOSPITAL", "MEDICAL", "HEALTH", "CLINIC", "GROUP", "INC", "LLC",
    "DEPT", "DEPARTMENT", "SYSTEM", "SYSTEMS", "SERVICES", "CARE",
  ]);

  const words = cleaned.split(/\s+/).filter((w) => w.length >= 4);
  const keyWords = words.filter((w) => !SKIP_WORDS.has(w.toUpperCase()));

  // Try the most distinctive word with wildcard
  if (keyWords.length > 0) {
    // Sort by length descending — longest word is usually most distinctive
    keyWords.sort((a, b) => b.length - a.length);
    const bestWord = keyWords[0];

    // "MOFFITT*" — wildcard search
    if (!variations.includes(bestWord + "*")) {
      variations.push(bestWord + "*");
    }

    // Also try two-word combination if available: "MOFFITT CANCER*"
    if (keyWords.length >= 2) {
      const twoWord = keyWords[0] + " " + keyWords[1] + "*";
      if (!variations.includes(twoWord)) {
        variations.push(twoWord);
      }
    }
  }

  return variations;
}

/**
 * Search NPPES via our backend proxy (CMS NPPES API has no CORS support).
 *
 * @param {string} name
 * @param {"NPI-1"|"NPI-2"} enumerationType
 * @param {AbortSignal} signal
 * @returns {Promise<{found: boolean, bestMatch: object}|null>}
 */
async function searchNPPES(name, enumerationType, signal) {
  const params = new URLSearchParams({
    name: name.trim(),
    enumeration_type: enumerationType,
    limit: "5",
  });

  const url = `${API_BASE}/api/nppes-lookup?${params.toString()}`;
  console.log("[NPPES] Proxy request:", url);
  const response = await fetch(url, { signal });

  if (!response.ok) {
    console.warn("[NPPES] Proxy returned:", response.status);
    return null;
  }

  const data = await response.json();
  console.log("[NPPES] API response:", data.result_count, "results");

  if (!data.results || data.results.length === 0) return null;

  // Pick the best match (first result from NPPES is typically most relevant)
  const best = data.results[0];
  const parsed = parseNPPESResult(best);

  if (parsed) {
    return { found: true, bestMatch: parsed };
  }

  return null;
}

/**
 * Parse an NPPES result object into our simplified format.
 */
function parseNPPESResult(result) {
  if (!result) return null;

  const npi = result.number ? String(result.number) : "";

  // Get name
  let name = "";
  if (result.basic) {
    if (result.basic.organization_name) {
      name = result.basic.organization_name;
    } else {
      const parts = [
        result.basic.first_name,
        result.basic.middle_name,
        result.basic.last_name,
      ].filter(Boolean);
      name = parts.join(" ");
      if (result.basic.credential) {
        name += `, ${result.basic.credential}`;
      }
    }
  }

  // Get practice location address (prefer practice over mailing)
  let address = { line1: "", city: "", state: "", zip: "" };
  let phone = "";

  if (result.addresses && result.addresses.length > 0) {
    // Prefer "LOCATION" (practice) address over "MAILING"
    const practiceAddr =
      result.addresses.find((a) => a.address_purpose === "LOCATION") ||
      result.addresses[0];

    address = {
      line1: [practiceAddr.address_1, practiceAddr.address_2]
        .filter(Boolean)
        .join(", "),
      city: practiceAddr.city || "",
      state: practiceAddr.state || "",
      zip: (practiceAddr.postal_code || "").slice(0, 5),
    };

    phone = formatPhone(practiceAddr.telephone_number || "");
  }

  return { npi, name, address, phone };
}

/**
 * Format a phone number string to (XXX) XXX-XXXX.
 */
function formatPhone(raw) {
  const digits = raw.replace(/\D/g, "");
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  if (digits.length === 11 && digits[0] === "1") {
    return `(${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  return raw; // Return as-is if format is unexpected
}
