-- 029: Seed analytical profiles for Parity Signal
-- Populates signal_analytical_profiles with 3 named profiles,
-- each with different scoring weights and trade-off summaries.

INSERT INTO signal_analytical_profiles (name, description, weights, trade_off_summary, source_type_association, is_default)
VALUES
  (
    'Balanced',
    'Default scoring — equal consideration across all evidence dimensions.',
    '{"source_quality": 0.25, "data_support": 0.20, "reproducibility": 0.20, "consensus": 0.15, "recency": 0.10, "rigor": 0.10}',
    'The default view weights all evidence dimensions proportionally. No single factor dominates — you see the full picture as-is.',
    NULL,
    true
  ),
  (
    'Regulatory',
    'Heavily weights source quality and consensus — FDA/CMS/official sources dominate conclusions.',
    '{"source_quality": 0.40, "data_support": 0.10, "reproducibility": 0.10, "consensus": 0.30, "recency": 0.05, "rigor": 0.05}',
    'This view prioritizes official regulatory sources (FDA, CMS, EMA) and established scientific consensus. Claims backed by authoritative sources rank higher, even if newer studies suggest different conclusions. Use this lens when regulatory positioning or compliance matters most.',
    'fda,cms,regulatory',
    false
  ),
  (
    'Clinical',
    'Heavily weights reproducibility and rigor — peer-reviewed trials and methodological quality dominate.',
    '{"source_quality": 0.10, "data_support": 0.15, "reproducibility": 0.30, "consensus": 0.05, "recency": 0.05, "rigor": 0.35}',
    'This view prioritizes claims supported by reproducible, methodologically rigorous studies — primarily RCTs and systematic reviews. A single well-designed trial can outweigh multiple lower-quality sources. Use this lens when clinical decision-making or formulary evaluation is the goal.',
    'clinical_trial,systematic_review',
    false
  ),
  (
    'Patient',
    'Heavily weights recency and data support — what is known now, practically, for real-world decisions.',
    '{"source_quality": 0.10, "data_support": 0.35, "reproducibility": 0.10, "consensus": 0.10, "recency": 0.30, "rigor": 0.05}',
    'This view prioritizes the most recent evidence and breadth of real-world data support. Newer findings and practical outcomes rank higher than historical consensus. Use this lens when making time-sensitive decisions or evaluating emerging treatments where the latest data matters most.',
    'real_world,observational',
    false
  )
ON CONFLICT DO NOTHING;
