-- Migration 050: provider_appeal_letters table
-- Persists generated appeal letters for reuse

CREATE TABLE IF NOT EXISTS provider_appeal_letters (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID,
  payer TEXT NOT NULL,
  denial_code TEXT NOT NULL,
  cpt_code TEXT,
  letter_text TEXT NOT NULL,
  signal_score FLOAT,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_appeal_letters_lookup
  ON provider_appeal_letters (user_id, payer, denial_code, cpt_code);
