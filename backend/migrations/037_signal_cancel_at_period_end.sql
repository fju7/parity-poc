-- Migration 037: Add cancel_at_period_end to signal_subscriptions
ALTER TABLE signal_subscriptions
  ADD COLUMN IF NOT EXISTS cancel_at_period_end BOOLEAN DEFAULT FALSE;
