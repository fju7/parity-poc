-- 009_enable_rls_all_tables.sql
-- Enable RLS on all 12 public tables that currently lack it.
-- Run in Supabase SQL Editor.
--
-- Groups:
--   A. User-data tables (4) — user-scoped policies + service_role access
--   B. Analytics/event tables (4) — service_role write, scoped or public read
--   C. Reference data tables (4) — service_role write, public read

-- =========================================================================
-- A. USER-DATA TABLES
-- =========================================================================

-- -------------------------------------------------------------------------
-- A1. signal_subscriptions (user_id, Stripe IDs, tier, billing)
-- Users read own; backend manages via Stripe webhooks (service_role)
-- -------------------------------------------------------------------------
ALTER TABLE signal_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own subscription"
  ON signal_subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on subscriptions"
  ON signal_subscriptions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- A2. signal_topic_subscriptions (user_id, issue_id, status)
-- Users manage own topic subscriptions; backend also accesses
-- -------------------------------------------------------------------------
ALTER TABLE signal_topic_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own topic subscriptions"
  ON signal_topic_subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own topic subscriptions"
  ON signal_topic_subscriptions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own topic subscriptions"
  ON signal_topic_subscriptions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on topic subscriptions"
  ON signal_topic_subscriptions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- A3. signal_notification_preferences (PK = user_id)
-- Users manage own preferences; backend reads for delivery
-- -------------------------------------------------------------------------
ALTER TABLE signal_notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own notification preferences"
  ON signal_notification_preferences FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notification preferences"
  ON signal_notification_preferences FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notification preferences"
  ON signal_notification_preferences FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on notification preferences"
  ON signal_notification_preferences FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- A4. signal_notifications (user_id, delivery, read status)
-- Backend creates; users read own and mark as read
-- -------------------------------------------------------------------------
ALTER TABLE signal_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own notifications"
  ON signal_notifications FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications"
  ON signal_notifications FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access on notifications"
  ON signal_notifications FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);


-- =========================================================================
-- B. ANALYTICS / EVENT TABLES
-- =========================================================================

-- -------------------------------------------------------------------------
-- B1. signal_events (nullable user_id, event tracking)
-- Authenticated users insert own events; service_role full access
-- No public reads — analytics are backend-only
-- -------------------------------------------------------------------------
ALTER TABLE signal_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can insert events"
  ON signal_events FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "Service role full access on events"
  ON signal_events FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- B2. signal_evidence_updates (change log for public signal data)
-- Public read (these describe changes to publicly visible claims);
-- only service_role writes
-- -------------------------------------------------------------------------
ALTER TABLE signal_evidence_updates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read evidence updates"
  ON signal_evidence_updates FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on evidence updates"
  ON signal_evidence_updates FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- B3. signal_platform_metrics (public dashboard stats)
-- Public read; service_role writes
-- -------------------------------------------------------------------------
ALTER TABLE signal_platform_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read platform metrics"
  ON signal_platform_metrics FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on platform metrics"
  ON signal_platform_metrics FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- B4. signal_analytical_profiles (scoring weight profiles)
-- Public read (used by frontend evidence display); service_role writes
-- -------------------------------------------------------------------------
ALTER TABLE signal_analytical_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read analytical profiles"
  ON signal_analytical_profiles FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on analytical profiles"
  ON signal_analytical_profiles FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);


-- =========================================================================
-- C. REFERENCE DATA TABLES (CMS rate history)
-- =========================================================================

-- -------------------------------------------------------------------------
-- C1. rate_schedule_versions (version registry)
-- -------------------------------------------------------------------------
ALTER TABLE rate_schedule_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read rate schedule versions"
  ON rate_schedule_versions FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on rate schedule versions"
  ON rate_schedule_versions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- C2. pfs_rates_historical
-- -------------------------------------------------------------------------
ALTER TABLE pfs_rates_historical ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read pfs rates historical"
  ON pfs_rates_historical FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on pfs rates historical"
  ON pfs_rates_historical FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- C3. opps_rates_historical
-- -------------------------------------------------------------------------
ALTER TABLE opps_rates_historical ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read opps rates historical"
  ON opps_rates_historical FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on opps rates historical"
  ON opps_rates_historical FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- -------------------------------------------------------------------------
-- C4. clfs_rates_historical
-- -------------------------------------------------------------------------
ALTER TABLE clfs_rates_historical ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read clfs rates historical"
  ON clfs_rates_historical FOR SELECT
  USING (true);

CREATE POLICY "Service role full access on clfs rates historical"
  ON clfs_rates_historical FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
