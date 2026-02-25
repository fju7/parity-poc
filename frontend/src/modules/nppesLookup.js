/**
 * nppesLookup.js — Looks up provider contact information via the public
 * CMS NPPES NPI Registry API. No backend needed.
 *
 * API docs: https://npiregistry.cms.hhs.gov/api-page
 */

const NPPES_BASE = "https://npiregistry.cms.hhs.gov/api/";
const TIMEOUT_MS = 5000;

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
    // Search for NPI-2 (organizations) first, then NPI-1 (individuals) as fallback
    const orgResult = await searchNPPES(providerName, "NPI-2", controller.signal);
    if (orgResult) {
      clearTimeout(timeoutId);
      return orgResult;
    }

    const indResult = await searchNPPES(providerName, "NPI-1", controller.signal);
    clearTimeout(timeoutId);
    return indResult || { found: false, bestMatch: null };
  } catch {
    // Network error, timeout, or abort — graceful failure
    clearTimeout(timeoutId);
    return null;
  }
}

/**
 * @param {string} name
 * @param {"NPI-1"|"NPI-2"} enumerationType
 * @param {AbortSignal} signal
 * @returns {Promise<{found: boolean, bestMatch: object}|null>}
 */
async function searchNPPES(name, enumerationType, signal) {
  const params = new URLSearchParams({
    version: "2.1",
    limit: "5",
    enumeration_type: enumerationType,
  });

  // NPI-2 = organization, NPI-1 = individual
  if (enumerationType === "NPI-2") {
    params.set("organization_name", name.trim());
  } else {
    // For individual providers, try splitting into first/last name
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      params.set("last_name", parts[parts.length - 1]);
      params.set("first_name", parts[0]);
    } else {
      params.set("last_name", name.trim());
    }
  }

  const url = `${NPPES_BASE}?${params.toString()}`;
  const response = await fetch(url, { signal });

  if (!response.ok) return null;

  const data = await response.json();

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
