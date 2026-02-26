/**
 * scoreAnomalies.js — Client-side anomaly scoring engine.
 *
 * Takes line items from PDF extraction + benchmark rates from the API
 * and computes anomaly scores, flags, and summary statistics.
 *
 * @param {Array<{code, codeType, description, billedAmount}>} extractedItems
 *   Line items from extractBillData()
 * @param {Array<{code, codeType, billedAmount, benchmarkRate, benchmarkSource, localityCode}>} benchmarkedItems
 *   Line items from the /api/benchmark response
 * @param {Object} [options]
 * @param {number} [options.anomalyThreshold=2.0] - Score above which an item is flagged
 * @returns {{
 *   lineItems: Array<{
 *     code: string,
 *     codeType: string,
 *     description: string,
 *     billedAmount: number,
 *     benchmarkRate: number|null,
 *     benchmarkSource: string,
 *     localityCode: string|null,
 *     anomalyScore: number|null,
 *     flagged: boolean,
 *     flagReason: string,
 *     estimatedDiscrepancy: number
 *   }>,
 *   summary: {
 *     totalBilled: number,
 *     totalBenchmark: number,
 *     totalPotentialDiscrepancy: number,
 *     flaggedItemCount: number,
 *     totalItemCount: number
 *   }
 * }}
 */

// Known CMS bundled code sets — if these codes appear as separate charges
// on the same bill, it may indicate unbundling.
const BUNDLED_SETS = [
  {
    codes: ["99213", "36415", "85025"],
    label: "Office visit + venipuncture + CBC",
  },
  {
    codes: ["99214", "36415", "85025"],
    label: "Office visit + venipuncture + CBC",
  },
  {
    codes: ["27447", "20680", "20930"],
    label: "Knee replacement + hardware removal + bone graft",
  },
  {
    codes: ["43239", "43235"],
    label: "Upper GI endoscopy with biopsy + diagnostic",
  },
  {
    codes: ["70553", "70551"],
    label: "MRI brain with and without contrast + without contrast",
  },
];

export default function scoreAnomalies(
  extractedItems,
  benchmarkedItems,
  options = {}
) {
  const { anomalyThreshold = 2.0 } = options;

  // Build a map from code to benchmark data for quick lookup
  const benchmarkMap = new Map();
  for (const item of benchmarkedItems) {
    benchmarkMap.set(item.code, item);
  }

  // Count code occurrences for duplicate detection
  const codeCounts = new Map();
  for (const item of extractedItems) {
    codeCounts.set(item.code, (codeCounts.get(item.code) || 0) + 1);
  }

  // Detect unbundling: check if all codes in any bundled set appear
  const allCodes = new Set(extractedItems.map((i) => i.code));
  const unbundledCodes = new Set();
  for (const bundle of BUNDLED_SETS) {
    if (bundle.codes.every((c) => allCodes.has(c))) {
      for (const c of bundle.codes) {
        unbundledCodes.set
          ? unbundledCodes.add(c)
          : unbundledCodes.add(c);
      }
    }
  }

  // Find which bundle label applies to each code
  const unbundleLabels = new Map();
  for (const bundle of BUNDLED_SETS) {
    if (bundle.codes.every((c) => allCodes.has(c))) {
      for (const c of bundle.codes) {
        unbundleLabels.set(c, bundle.label);
      }
    }
  }

  // Score each item
  let totalBilled = 0;
  let totalBenchmark = 0;
  let totalPotentialDiscrepancy = 0;
  let flaggedItemCount = 0;

  const scoredItems = extractedItems.map((extracted) => {
    const bench = benchmarkMap.get(extracted.code) || {};
    const benchmarkRate = bench.benchmarkRate ?? null;
    const benchmarkSource = bench.benchmarkSource ?? "NOT_FOUND";
    const dataVintage = bench.dataVintage ?? null;
    const localityCode = bench.localityCode ?? null;

    // Anomaly score
    let anomalyScore = null;
    if (benchmarkRate && benchmarkRate > 0) {
      anomalyScore = Math.round((extracted.billedAmount / benchmarkRate) * 100) / 100;
    }

    // Flag reasons (can accumulate multiple)
    const reasons = [];

    // 1. High anomaly score
    if (anomalyScore !== null && anomalyScore > anomalyThreshold) {
      reasons.push(
        `Billed at ${anomalyScore.toFixed(1)}x the Medicare benchmark rate`
      );
    }

    // 2. Duplicate billing
    if (codeCounts.get(extracted.code) > 1) {
      reasons.push("Duplicate: same procedure code appears multiple times");
    }

    // 3. Unbundling
    if (unbundledCodes.has(extracted.code)) {
      reasons.push(
        `Possible unbundling: ${unbundleLabels.get(extracted.code)}`
      );
    }

    const flagged = reasons.length > 0;
    const flagReason = reasons.join("; ");

    // Discrepancy
    const estimatedDiscrepancy =
      benchmarkRate !== null
        ? Math.round((extracted.billedAmount - benchmarkRate) * 100) / 100
        : 0;

    // Accumulate totals
    totalBilled += extracted.billedAmount;
    if (benchmarkRate !== null) {
      totalBenchmark += benchmarkRate;
    }
    if (flagged && estimatedDiscrepancy > 0) {
      totalPotentialDiscrepancy += estimatedDiscrepancy;
    }
    if (flagged) flaggedItemCount++;

    return {
      code: extracted.code,
      codeType: extracted.codeType,
      description: extracted.description,
      billedAmount: extracted.billedAmount,
      benchmarkRate,
      benchmarkSource,
      dataVintage,
      localityCode,
      anomalyScore,
      flagged,
      flagReason,
      estimatedDiscrepancy,
      isHistorical: bench.isHistorical ?? false,
      historicalDataAvailable: bench.historicalDataAvailable ?? true,
      warning: bench.warning ?? null,
    };
  });

  return {
    lineItems: scoredItems,
    summary: {
      totalBilled: Math.round(totalBilled * 100) / 100,
      totalBenchmark: Math.round(totalBenchmark * 100) / 100,
      totalPotentialDiscrepancy:
        Math.round(totalPotentialDiscrepancy * 100) / 100,
      flaggedItemCount,
      totalItemCount: scoredItems.length,
    },
  };
}
