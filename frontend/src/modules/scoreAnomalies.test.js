import { describe, it, expect } from "vitest";
import scoreAnomalies from "./scoreAnomalies.js";

describe("scoreAnomalies", () => {
  it("correctly flags high-ratio and duplicate items", () => {
    // 3 synthetic items:
    // 1) 1.5x benchmark — should NOT be flagged (below default 2.0 threshold)
    // 2) 3.0x benchmark — should be flagged
    // 3) duplicate CPT code — should be flagged
    const extracted = [
      { code: "99213", codeType: "CPT", description: "Office visit L3", billedAmount: 150.0 },
      { code: "99214", codeType: "CPT", description: "Office visit L4", billedAmount: 300.0 },
      { code: "99213", codeType: "CPT", description: "Office visit L3", billedAmount: 150.0 },
    ];

    const benchmarked = [
      { code: "99213", codeType: "CPT", billedAmount: 150.0, benchmarkRate: 100.0, benchmarkSource: "CMS_PFS_2026", localityCode: "99" },
      { code: "99214", codeType: "CPT", billedAmount: 300.0, benchmarkRate: 100.0, benchmarkSource: "CMS_PFS_2026", localityCode: "99" },
    ];

    const result = scoreAnomalies(extracted, benchmarked);

    // Item 1: 1.5x, but also duplicate → flagged for duplicate only
    const item1 = result.lineItems[0];
    expect(item1.anomalyScore).toBe(1.5);
    expect(item1.flagged).toBe(true);
    expect(item1.flagReason).toContain("Duplicate");

    // Item 2: 3.0x → flagged for high ratio
    const item2 = result.lineItems[1];
    expect(item2.anomalyScore).toBe(3.0);
    expect(item2.flagged).toBe(true);
    expect(item2.flagReason).toContain("3.0x");

    // Item 3: duplicate of item 1 → flagged
    const item3 = result.lineItems[2];
    expect(item3.flagged).toBe(true);
    expect(item3.flagReason).toContain("Duplicate");

    // Summary
    expect(result.summary.totalBilled).toBe(600.0);
    expect(result.summary.totalBenchmark).toBe(300.0); // 100 + 100 + 100
    expect(result.summary.flaggedItemCount).toBe(3);
    expect(result.summary.totalItemCount).toBe(3);
    expect(result.summary.totalPotentialDiscrepancy).toBeGreaterThan(0);
  });

  it("does not flag items below the threshold with no duplicates", () => {
    const extracted = [
      { code: "99213", codeType: "CPT", description: "Office visit", billedAmount: 180.0 },
    ];
    const benchmarked = [
      { code: "99213", codeType: "CPT", billedAmount: 180.0, benchmarkRate: 100.0, benchmarkSource: "CMS_PFS_2026", localityCode: "01" },
    ];

    const result = scoreAnomalies(extracted, benchmarked);

    expect(result.lineItems[0].anomalyScore).toBe(1.8);
    expect(result.lineItems[0].flagged).toBe(false);
    expect(result.lineItems[0].flagReason).toBe("");
  });

  it("handles items with null benchmark gracefully", () => {
    const extracted = [
      { code: "XXXXX", codeType: "UNKNOWN", description: "Unknown", billedAmount: 500.0 },
    ];
    const benchmarked = [
      { code: "XXXXX", codeType: "UNKNOWN", billedAmount: 500.0, benchmarkRate: null, benchmarkSource: "NOT_FOUND", localityCode: null },
    ];

    const result = scoreAnomalies(extracted, benchmarked);

    expect(result.lineItems[0].anomalyScore).toBeNull();
    expect(result.lineItems[0].flagged).toBe(false);
    expect(result.lineItems[0].estimatedDiscrepancy).toBe(0);
  });

  it("respects a custom anomaly threshold", () => {
    const extracted = [
      { code: "99214", codeType: "CPT", description: "Office visit", billedAmount: 250.0 },
    ];
    const benchmarked = [
      { code: "99214", codeType: "CPT", billedAmount: 250.0, benchmarkRate: 100.0, benchmarkSource: "CMS_PFS_2026", localityCode: "01" },
    ];

    // 2.5x — not flagged at threshold 3.0
    const result = scoreAnomalies(extracted, benchmarked, { anomalyThreshold: 3.0 });
    expect(result.lineItems[0].anomalyScore).toBe(2.5);
    expect(result.lineItems[0].flagged).toBe(false);
  });
});
