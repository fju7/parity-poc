-- Migration 043: Add claim_type and consensus_type to signal_claims
-- Foundation for methodology framework — every claim needs a type classification

ALTER TABLE signal_claims
  ADD COLUMN IF NOT EXISTS claim_type text
    CHECK (claim_type IS NULL OR claim_type IN (
      'efficacy', 'safety', 'institutional', 'values_embedded', 'foundational_values'
    ));

ALTER TABLE signal_claims
  ADD COLUMN IF NOT EXISTS consensus_type text
    CHECK (consensus_type IS NULL OR consensus_type IN (
      'strong_consensus', 'active_debate', 'manufactured_controversy', 'genuine_uncertainty'
    ));
