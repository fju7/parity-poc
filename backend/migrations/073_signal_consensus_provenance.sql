-- Migration: record what produced each consensus label.
--
-- WHY
-- ---
-- signal_consensus stores a judgment (consensus / debated / uncertain) and the
-- prose behind it, but nothing about its origin beyond mapped_at. That gap has
-- a measured cost.
--
-- GLP-1 'pricing' was published as "debated" in March 2026. In August the
-- identical prompt over the identical 44 claims returned "consensus" — and
-- reading those claims confirmed "consensus" was the correct answer. The site
-- served a wrong label for five months, and diagnosing it took hours of
-- reconstructing the prompt from git history and inferring which model had run,
-- because neither was recorded anywhere.
--
-- A stability sweep then measured every category: 47 of 52 published labels
-- still match what the current model produces, 5 do not. That is a healthy
-- number, but it is only knowable because the sweep was run by hand. These two
-- columns make it answerable from the row itself.
--
-- model_id       the model string the API ACTUALLY used, read back off the
--                response — correct even when the configured value is an
--                unpinned alias like "claude-sonnet-4-6".
-- prompt_version a short sha256 of the system prompt that produced the row.
--                Changes automatically whenever the prompt text changes, so
--                "was this produced by the prompt we have now?" is a string
--                comparison rather than an archaeology exercise.
--
-- Additive and inert: both columns are nullable with no default. Existing rows
-- keep NULL, which correctly means "provenance unknown" — that is the honest
-- record for every row written before today. They populate as topics are
-- re-mapped.
--
-- Idempotent.

ALTER TABLE signal_consensus
  ADD COLUMN IF NOT EXISTS model_id TEXT,
  ADD COLUMN IF NOT EXISTS prompt_version TEXT;

COMMENT ON COLUMN signal_consensus.model_id IS
  'Model string the API actually used to produce this row, read from the '
  'response rather than the configured value. NULL for rows written before '
  'migration 073, which genuinely have unknown provenance.';

COMMENT ON COLUMN signal_consensus.prompt_version IS
  'First 12 hex chars of the sha256 of the system prompt that produced this '
  'row (see scripts/signal/signal_model.py:prompt_version). NULL for rows '
  'written before migration 073.';

-- Answering "which published labels predate provenance tracking?" should not
-- require a sequential scan once most rows carry it.
CREATE INDEX IF NOT EXISTS signal_consensus_provenance_idx
  ON signal_consensus (model_id, prompt_version);

-- signal_consensus is already public-read (migration 006) with RLS enabled;
-- adding columns inherits both. No grant changes needed.
