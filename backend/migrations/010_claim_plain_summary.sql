-- Add plain-language summary column to signal_claims
ALTER TABLE signal_claims ADD COLUMN IF NOT EXISTS plain_summary TEXT;
