-- 048_provider_appeal_outcomes.sql
-- Track appeal outcomes to build the data flywheel.

CREATE TABLE IF NOT EXISTS provider_appeal_outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  appeal_id UUID REFERENCES provider_appeals(id),
  claim_id TEXT,
  cpt_code TEXT,
  denial_code TEXT,
  payer TEXT,
  signal_topic_slug TEXT,
  appeal_submitted_at TIMESTAMPTZ,
  outcome TEXT CHECK (outcome IN ('pending', 'won', 'lost', 'partial')),
  outcome_recorded_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_appeal_outcomes_appeal
  ON provider_appeal_outcomes(appeal_id);

CREATE INDEX IF NOT EXISTS idx_appeal_outcomes_outcome
  ON provider_appeal_outcomes(outcome);
