// Scoring weights and category thresholds, copied from
// backend/scripts/signal/score_claims.py (DEFAULT_WEIGHTS, EVIDENCE_CATEGORIES).
// src/__tests__/methodology.test.js reads the Python file and fails if these drift.
export const WEIGHTS = {
  source_quality: 0.25,
  data_support: 0.2,
  reproducibility: 0.2,
  consensus: 0.15,
  recency: 0.1,
  rigor: 0.1,
};

export const CATEGORY_THRESHOLDS = [
  ["Strong", 4.0],
  ["Moderate", 3.0],
  ["Mixed", 2.0],
  ["Weak", 0.0],
];
