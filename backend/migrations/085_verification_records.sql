-- Migration 085: a verification record beside every model-written letter.
--
-- WHY THIS EXISTS
-- ---------------
-- Shared assertion policy, Phase B (docs/shared-assertion-policy-phase-a-inventory.md
-- §D, amendment 3: "UNCHECKED must have a consumer"). verify.policy.check()
-- runs at the response boundary of each gated surface and produces a
-- Verdict -- what was refused, what bound, and what could NOT be checked
-- (a figure read from an image with no text layer). A verdict that is
-- returned but not stored is lost the moment the response is consumed; a
-- letter in provider_appeals would then carry no record of what was checked
-- when it was written. This column stores Verdict.to_dict() beside the
-- letter it describes. Nullable: rows written before the gate have no record,
-- and NULL is the honest value for "never checked".
--
-- billing_contracts and provider_analyses already carry a jsonb result column
-- and store the record inside it; only provider_appeals lacked one.

ALTER TABLE provider_appeals
    ADD COLUMN IF NOT EXISTS verification jsonb;

COMMENT ON COLUMN provider_appeals.verification IS
    'verify.policy Verdict.to_dict() for the letter at generation time: refused / unchecked / flags / checked. NULL = generated before the gate (2026-09-15) or never checked.';

-- No grant changes: provider_appeals grants are unchanged by adding a column
-- (service_role only, per the table''s existing policy).
