-- Migration: our own record of who subscribed, and when.
--
-- WHY THIS EXISTS
-- ---------------
-- Until now the answer to "who subscribes to What Holds Up" lived in exactly
-- one place: a Resend audience. Resend is a delivery tool. It is very good at
-- delivery and it is not a system of record — it holds the addresses it needs
-- to send to, not the history of how they arrived, and it is somebody else's
-- database.
--
-- That is survivable while the list is free and undifferentiated. It stops
-- being survivable the moment any of these is wanted:
--
--   tiers, entitlements, or anything a person pays for;
--   "which questions is this reader watching" — the changelog product;
--   a signup date, a source, or a receipt trail;
--   moving off Resend without losing everything except the addresses.
--
-- None of those are being built now. This table exists so that when one of
-- them is, it is a column on a table that already has the history, rather than
-- an attempt to reconstruct a year of signups from an email provider.
--
-- WHY UNSUBSCRIBE STATE IS NOT A COLUMN HERE
-- ------------------------------------------
-- whatholdsup_unsubscribes already records every unsubscribe request, keyed on
-- email, independent of whether Resend accepted it. Putting an unsubscribed_at
-- column here as well would give the same fact two homes and guarantee they
-- disagree. Active subscribers are this table LEFT JOIN that one, where the
-- unsubscribe row is null.
--
-- Idempotent.

CREATE TABLE IF NOT EXISTS whatholdsup_subscribers (
  email               TEXT PRIMARY KEY,
  subscribed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  source              TEXT,
  resend_contact_id   TEXT
);

COMMENT ON TABLE whatholdsup_subscribers IS
  'Every subscription request received, with when and from where. The system '
  'of record; Resend is the delivery mechanism. Unsubscribe state lives in '
  'whatholdsup_unsubscribes, not here, so that fact has one home.';

COMMENT ON COLUMN whatholdsup_subscribers.source IS
  '''site'' for the form on whatholdsup.org, ''manual'' for one added by hand '
  'from the mailto, ''import'' for a list brought in from elsewhere.';

COMMENT ON COLUMN whatholdsup_subscribers.resend_contact_id IS
  'NULL means the row was recorded but the Resend contact was not created, so '
  'this person is on our list and will receive nothing. These rows are a work '
  'queue, not history. The same reasoning as propagated_to_resend on '
  'whatholdsup_unsubscribes, in the other direction.';

-- The rows that need a human: recorded here, never reached Resend.
CREATE INDEX IF NOT EXISTS whatholdsup_subscribers_unsynced_idx
  ON whatholdsup_subscribers (subscribed_at)
  WHERE resend_contact_id IS NULL;

-- RLS on, and NO public policy. The endpoint writes with the service key.
-- This is a list of the email addresses of people who read us. The anon key is
-- published in the frontend bundle; anything readable with it is public.
ALTER TABLE whatholdsup_subscribers ENABLE ROW LEVEL SECURITY;
