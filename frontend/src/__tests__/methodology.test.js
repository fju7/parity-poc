// The methodology page states the scoring weights and thresholds. They are
// copied from backend/scripts/signal/score_claims.py; this test reads that
// file and fails if the page and the code disagree. On 2026-09-15 the page
// said reproducibility 15% / recency 15% while the code said 20% / 10%.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { WEIGHTS, CATEGORY_THRESHOLDS } from "../components/signal/MethodologyView.jsx";

const src = readFileSync(resolve(__dirname, "../../../backend/scripts/signal/score_claims.py"), "utf8");

describe("methodology page matches score_claims.py", () => {
  it("weights", () => {
    const block = src.match(/DEFAULT_WEIGHTS = \{([\s\S]*?)\}/)[1];
    const codeWeights = Object.fromEntries(
      [...block.matchAll(/"(\w+)":\s*([\d.]+)/g)].map((m) => [m[1], Number(m[2])])
    );
    expect(WEIGHTS).toEqual(codeWeights);
    expect(Object.values(WEIGHTS).reduce((a, b) => a + b, 0)).toBeCloseTo(1.0, 6);
  });
  it("category thresholds", () => {
    const block = src.match(/EVIDENCE_CATEGORIES = \[([\s\S]*?)\]/)[1];
    const code = [...block.matchAll(/\(([\d.]+),\s*"(\w+)"\)/g)].map((m) => [m[2], Number(m[1])]);
    const page = CATEGORY_THRESHOLDS.map(([n, t]) => [n.toLowerCase(), t]);
    expect(page).toEqual(code);
  });
});
