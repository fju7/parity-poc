-- Migration: our own record of every unsubscribe request.
--
-- WHY THIS EXISTS SEPARATELY FROM RESEND
-- --------------------------------------
-- The one-click endpoint marks the contact unsubscribed in Resend, which is
-- what actually stops mail, because Resend is the send path. That call can
-- fail: a bad key, an API change, a contact that was never in an audience, a
-- transient 5xx. RFC 8058 requires the endpoint to answer 200 regardless — a
-- non-200 makes some clients retry and shows the reader a failure for a request
-- we did in fact receive.
--
-- So the request must be recorded somewhere we control, independently of
-- whether the propagation worked. This table is that record. It is:
--
--   the evidence that a request was made and when — which is the thing a
--   regulator, a complaint, or an angry reader asks about;
--   the work queue for anything Resend rejected (propagated_to_resend = false);
--   the suppression list of last resort if Resend is ever replaced.
--
-- Nothing is deleted here. An unsubscribe that disappears from the record is
-- an unsubscribe that can be silently undone by a later import.
--
-- Idempotent.

CREATE TABLE IF NOT EXISTS whatholdsup_unsubscribes (
  email                 TEXT PRIMARY KEY,
  unsubscribed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  propagated_to_resend  BOOLEAN NOT NULL DEFAULT false,
  source                TEXT,
  note                  TEXT
);

COMMENT ON TABLE whatholdsup_unsubscribes IS
  'Every unsubscribe request received, independent of whether Resend accepted '
  'it. Never delete a row: a request that vanishes from this record can be '
  'silently undone by a later contact import.';

COMMENT ON COLUMN whatholdsup_unsubscribes.propagated_to_resend IS
  'FALSE means the request was received and honoured in our records but the '
  'Resend API call failed. These rows are a work queue, not history.';

COMMENT ON COLUMN whatholdsup_unsubscribes.source IS
  '''one-click'' for an RFC 8058 POST from a mail client, ''manual'' for one '
  'handled by hand from the mailto, ''import'' for a suppression list brought '
  'in from elsewhere.';

-- The rows that need a human.
CREATE INDEX IF NOT EXISTS whatholdsup_unsubscribes_unpropagated_idx
  ON whatholdsup_unsubscribes (unsubscribed_at)
  WHERE propagated_to_resend IS FALSE;

-- RLS on, and NO public policy. The endpoint writes with the service key.
-- An unsubscribe list is a list of email addresses of people who read us;
-- it must not be readable by anyone holding the anon key, which is published
-- in the frontend bundle.
ALTER TABLE whatholdsup_unsubscribes ENABLE ROW LEVEL SECURITY;
