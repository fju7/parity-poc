-- Add cached AI trend narrative to provider_subscriptions
ALTER TABLE provider_subscriptions
  ADD COLUMN IF NOT EXISTS trend_narrative TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS trend_narrative_updated_at TIMESTAMPTZ DEFAULT NULL;
