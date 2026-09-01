-- Migration: record how often the engine agreed with itself.
--
-- WHY
-- ---
-- A consensus label is currently the product of one model call. That call is
-- treated as a measurement, and the row records what it said. On 2026-08-27 we
-- measured how repeatable that is, and the answer is: the verdict repeats, the
-- reasoning underneath it does not.
--
-- Three full sweeps of all 53 categories in a single day returned identical
-- statuses every time. Zero flips. The holistic judgment is stable.
--
-- Side attribution is not. social-media-teen-mental-health / methodology, 43
-- claims, identical prompt hash 7722652f9266, six measurements in one day:
--
--     10 for /  3 against     leans FOR
--      2 for / 10 against     leans AGAINST
--      3 for /  8 against     leans AGAINST
--     11 for /  4 against     leans FOR
--      4 for / 10 against     leans AGAINST
--     ~10 for / ~3 against    leans FOR
--
-- Three each way. The published topic page renders those counts, so a reader
-- arriving on one day is told most of the evidence supports the methodological
-- critique, and a reader arriving the next is told most of it opposes. Both
-- from the same claims. The status reads "debated" throughout, so nothing in
-- the pipeline noticed.
--
-- These columns exist so a row can say how many times it was measured, how
-- often those measurements agreed, and whether the side attribution held its
-- direction — which is the difference between "the evidence is genuinely
-- balanced" and "we cannot measure this consistently". Presenting the second
-- as the first would attribute our own instability to the evidence, which is
-- the exact error this publication exists to name.
--
-- runs            how many independent mappings produced this row. 1 for every
--                 row written before repeated measurement existed.
-- agreement       fraction of those runs that returned the stored status.
--                 1.0 when every run agreed. NULL when runs is 1, because a
--                 single measurement has no agreement to report — that is
--                 different from perfect agreement and must not read as it.
-- sides_stable    TRUE  side attribution kept its direction across runs.
--                 FALSE it reversed; for_claim_ids/against_claim_ids are
--                       deliberately NULL and must not be displayed.
--                 NULL  not assessed (single run, or row predates this).
-- sides_observed  every [for, against] pair seen, so the instability is
--                 auditable rather than asserted.
--
-- NOTE ON READING sides_stable = FALSE: migration 071 made the side columns
-- nullable so NULL could mean "this row predates side attribution". A row with
-- NULL sides AND sides_stable = FALSE means something different and stronger:
-- the sides were measured, they contradicted each other, and we withheld them.
-- A consumer must check sides_stable before treating NULL as "unknown".
--
-- Additive and inert. All four are nullable with no default, so existing rows
-- keep NULL and nothing changes until a topic is re-mapped with --runs.
--
-- Idempotent.

ALTER TABLE signal_consensus
  ADD COLUMN IF NOT EXISTS runs           SMALLINT,
  ADD COLUMN IF NOT EXISTS agreement      NUMERIC(4,3),
  ADD COLUMN IF NOT EXISTS sides_stable   BOOLEAN,
  ADD COLUMN IF NOT EXISTS sides_observed JSONB;

COMMENT ON COLUMN signal_consensus.runs IS
  'Number of independent mappings behind this row. NULL or 1 means a single '
  'call, which is what every row written before migration 074 was.';

COMMENT ON COLUMN signal_consensus.agreement IS
  'Fraction of runs returning the stored consensus_status, 0-1. NULL when runs '
  'is 1: a single measurement has no agreement to report, which is not the '
  'same as perfect agreement and must not be rendered as 100%.';

COMMENT ON COLUMN signal_consensus.sides_stable IS
  'TRUE if side attribution kept its direction across runs. FALSE if it '
  'reversed, in which case for_claim_ids and against_claim_ids are NULL by '
  'intent and must not be shown. NULL if not assessed.';

COMMENT ON COLUMN signal_consensus.sides_observed IS
  'Array of [for_count, against_count] pairs, one per run, so an instability '
  'claim can be checked rather than taken on trust.';

-- Rows whose sides were measured and withheld are the ones a reader must never
-- be shown counts for. Make that cheap to select.
CREATE INDEX IF NOT EXISTS signal_consensus_sides_stable_idx
  ON signal_consensus (sides_stable)
  WHERE sides_stable IS FALSE;

-- Guard the invariant the frontend depends on: sides are withheld precisely
-- when they were found unstable. Written as a trigger-free CHECK so it cannot
-- drift out of sync with whatever writes the row.
ALTER TABLE signal_consensus
  DROP CONSTRAINT IF EXISTS signal_consensus_unstable_sides_withheld;
ALTER TABLE signal_consensus
  ADD CONSTRAINT signal_consensus_unstable_sides_withheld
  CHECK (
    sides_stable IS DISTINCT FROM FALSE
    OR (for_claim_ids IS NULL AND against_claim_ids IS NULL)
  );

-- signal_consensus is already public-read (migration 006) with RLS enabled;
-- adding columns inherits both. No grant changes needed.
