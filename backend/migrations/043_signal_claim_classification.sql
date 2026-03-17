-- 043_signal_claim_classification.sql
-- Add claim_type and consensus_type columns to signal_claims.
-- These classify each claim before scoring (Session S — methodology framework).

ALTER TABLE signal_claims
  ADD COLUMN IF NOT EXISTS claim_type TEXT,
  ADD COLUMN IF NOT EXISTS consensus_type TEXT;

-- Valid claim_type values
ALTER TABLE signal_claims
  ADD CONSTRAINT chk_claim_type CHECK (
    claim_type IS NULL OR claim_type IN (
      'efficacy',
      'safety',
      'institutional',
      'values_embedded',
      'foundational_values'
    )
  );

-- Valid consensus_type values
ALTER TABLE signal_claims
  ADD CONSTRAINT chk_consensus_type CHECK (
    consensus_type IS NULL OR consensus_type IN (
      'strong_consensus',
      'active_debate',
      'manufactured_controversy',
      'genuine_uncertainty'
    )
  );
