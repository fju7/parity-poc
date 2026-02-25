const DB_NAME = "parity-bills";
const DB_VERSION = 1;
const STORE_NAME = "bills";

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("createdAt", "createdAt", { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Returns an empty bill schema structure — useful for manual entry.
 */
export function getBillSchema() {
  return {
    bill_id: "",
    created_at: "",
    parsing_method: "standard",
    parsing_confidence: null,

    provider: {
      name: "",
      npi: null,
      type: null,
      place_of_service_code: null,
    },

    encounter: {
      service_date: null,
      admission_date: null,
      discharge_date: null,
      primary_diagnosis_icd10: null,
    },

    payer: {
      insurance_name: null,
      plan_type: null,
    },

    line_items: [],

    totals: {
      total_billed: 0.0,
      total_patient_responsibility: null,
    },

    analysis: {
      benchmark_source: null,
      anomaly_count: 0,
      total_potential_discrepancy: 0.0,
      coding_flags_count: 0,
      anomaly_score_max: 0.0,
      referred_to_attorney: false,
    },

    consent: {
      analytics_consent: true,
      employer_consent: false,
    },
  };
}

/**
 * Normalize incoming bill data (from any parsing method) into the
 * standard schema before saving. Maps from the current parser output
 * format and from AI/manual entry formats.
 */
export function normalizeBill(data) {
  const billId = crypto.randomUUID();
  const now = new Date().toISOString();

  // Detect parsing method from data
  const parsingMethod = data.parsing_method || data.parsingMethod || "standard";
  const parsingConfidence = data.parsing_confidence || data.parsingConfidence || null;

  // Provider: handle both old format {name, zip, npi} and new format
  const rawProvider = data.provider || {};
  const provider = {
    name: rawProvider.name || "",
    npi: rawProvider.npi || null,
    type: rawProvider.type || rawProvider.providerType || null,
    place_of_service_code: rawProvider.place_of_service_code || null,
  };

  // Encounter
  const rawEncounter = data.encounter || {};
  const encounter = {
    service_date: rawEncounter.service_date || data.serviceDate || null,
    admission_date: rawEncounter.admission_date || null,
    discharge_date: rawEncounter.discharge_date || null,
    primary_diagnosis_icd10: rawEncounter.primary_diagnosis_icd10 || null,
  };

  // Payer
  const rawPayer = data.payer || {};
  const payer = {
    insurance_name: rawPayer.insurance_name || data.insuranceName || null,
    plan_type: rawPayer.plan_type || null,
  };

  // Line items: map from old format [{code, codeType, description, billedAmount}]
  // to new format [{line_id, cpt_code, revenue_code, description, quantity, billed_amount, modifier, place_of_service}]
  const rawLineItems = data.line_items || data.lineItems || [];
  const lineItems = rawLineItems.map((item) => ({
    line_id: item.line_id || crypto.randomUUID(),
    cpt_code: item.cpt_code || item.code || "",
    revenue_code: item.revenue_code || (item.codeType === "REVENUE" ? item.code : null),
    description: item.description || "",
    quantity: item.quantity ?? 1,
    billed_amount: item.billed_amount ?? item.billedAmount ?? 0,
    modifier: item.modifier || null,
    place_of_service: item.place_of_service || null,
  }));

  // Totals
  const rawTotals = data.totals || {};
  const totalBilled =
    rawTotals.total_billed ??
    data.summary?.totalBilled ??
    lineItems.reduce((sum, li) => sum + (li.billed_amount || 0), 0);
  const totals = {
    total_billed: totalBilled,
    total_patient_responsibility: rawTotals.total_patient_responsibility ?? null,
  };

  // Analysis (populated after pipeline runs)
  const rawAnalysis = data.analysis || {};
  const rawSummary = data.summary || {};
  const analysis = {
    benchmark_source: rawAnalysis.benchmark_source || null,
    anomaly_count: rawAnalysis.anomaly_count ?? rawSummary.flaggedItemCount ?? 0,
    total_potential_discrepancy:
      rawAnalysis.total_potential_discrepancy ??
      rawSummary.totalPotentialDiscrepancy ??
      0,
    coding_flags_count:
      rawAnalysis.coding_flags_count ??
      (data.codingAlerts?.length || data.codingSummary?.totalAlerts || 0),
    anomaly_score_max: rawAnalysis.anomaly_score_max ?? 0,
    referred_to_attorney: rawAnalysis.referred_to_attorney ?? false,
  };

  // Consent
  const rawConsent = data.consent || {};
  const consent = {
    analytics_consent: rawConsent.analytics_consent ?? true,
    employer_consent: rawConsent.employer_consent ?? false,
  };

  return {
    bill_id: billId,
    created_at: now,
    parsing_method: parsingMethod,
    parsing_confidence: parsingConfidence,
    provider,
    encounter,
    payer,
    line_items: lineItems,
    totals,
    analysis,
    consent,
  };
}

/**
 * Save a bill to IndexedDB. Normalizes the data into the standard schema
 * and also preserves the original analysis data for report rendering.
 */
export async function saveBill(billData) {
  const db = await openDB();
  const id = crypto.randomUUID();

  // Normalize the bill into the standard schema
  const normalized = normalizeBill(billData);

  // Store both the normalized schema and the original report data
  // so that ReportView can render without changes
  const record = {
    id,
    createdAt: normalized.created_at,
    // Normalized schema fields
    ...normalized,
    // Original report data (for backward-compatible rendering)
    provider: billData.provider || normalized.provider,
    serviceDate: billData.serviceDate || normalized.encounter.service_date,
    summary: billData.summary || null,
    lineItems: billData.lineItems || [],
    partialWarning: billData.partialWarning || null,
    codingAlerts: billData.codingAlerts || [],
    codingSummary: billData.codingSummary || null,
    parsingMethod: billData.parsingMethod || billData.parsing_method || "standard",
  };

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).put(record);
    tx.oncomplete = () => resolve(id);
    tx.onerror = () => reject(tx.error);
  });
}

export async function getAllBills() {
  const db = await openDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.index("createdAt").getAll();

    request.onsuccess = () => {
      // Index returns ascending; reverse for newest-first
      resolve(request.result.reverse());
    };
    request.onerror = () => reject(request.error);
  });
}

export async function getBillById(id) {
  const db = await openDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const request = tx.objectStore(STORE_NAME).get(id);
    request.onsuccess = () => resolve(request.result || null);
    request.onerror = () => reject(request.error);
  });
}

export async function deleteBill(id) {
  const db = await openDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function exportAllBills() {
  const bills = await getAllBills();
  return JSON.stringify(bills, null, 2);
}

export async function clearAll() {
  const db = await openDB();

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
