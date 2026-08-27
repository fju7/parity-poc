-- Migration: tell a tie apart from an instability.
--
-- WHY
-- ---
-- Migration 074 shipped sides_stable as a boolean, and a boolean turned out to
-- be the wrong shape. It tested whether the SIGN of (for - against) was the
-- same in every run. A sign is meaningless inside a difference of one claim,
-- so the guard fired on a category that was being measured perfectly well.
--
-- On 2026-08-27 we ran five independent mappings of each remaining debated
-- category. Two of them reversed direction, for opposite reasons:
--
--   social-media / methodology       10/3, 2/10, 3/8, 11/4, 4/10
--   social-media / platform_design    6/5, 6/6, 6/7,  6/6,  6/6
--
-- The first is an axis inversion. The model partitions 43 claims the same way
-- every time and swaps which half is "for", because the category names a
-- subject rather than a proposition and two near-inverse propositions fit it.
-- Its own summary states the mechanism: both sides agree the research has
-- serious methodological problems and draw opposite conclusions from that.
-- Nothing about that balance can be published.
--
-- The second is a tie. The "for" side is 6 in all five runs and does not move
-- at all; only the "against" side wanders by one, which happens to straddle
-- equality and so flips a sign that was never carrying information. This is a
-- stable measurement of an evenly divided question, and suppressing it hides a
-- real finding — the opposite of the error 074 was written to prevent.
--
-- sides_balance carries the three-way reading the boolean flattens:
--
--   'lean'      a direction that held whenever it was decisive. Sides are
--               stored and may be rendered as a balance.
--   'tie'       measured consistently, and consistently close. Sides are
--               stored and may be rendered, but ONLY as evenly divided. A
--               frontend that prints "6 of 11 claims support" here is
--               reporting noise as a finding.
--   'unstable'  decisive leans in both directions, or one run that put every
--               claim on a single side while others did not. Sides are NULL
--               by intent and must not be displayed.
--
-- A lean is DECISIVE only if the difference is at least 2 claims AND more than
-- a tenth of the claims attributed. Both tests are needed: 6/5 clears neither,
-- 10/3 clears both, and 3/2 clears the share but not the floor and is read as
-- the tie it is. The thresholds live in backend/scripts/signal/map_consensus.py
-- as DECISIVE_MIN_CLAIMS and DECISIVE_MIN_SHARE; this column stores the
-- verdict, not the rule, so changing the rule requires a re-measure and not a
-- backfill.
--
-- sides_stable is KEPT and is now exactly (sides_balance <> 'unstable'). It
-- stays because migration 074's CHECK and the frontend both read it, and
-- because a consumer that only needs "may I show these sides" should not have
-- to learn three values. The constraint below stops the two drifting apart.
--
-- Additive and inert. Nullable, no default, so existing rows keep NULL and
-- nothing changes until a topic is re-mapped with --runs.
--
-- Idempotent.

ALTER TABLE signal_consensus
  ADD COLUMN IF NOT EXISTS sides_balance TEXT;

COMMENT ON COLUMN signal_consensus.sides_balance IS
  '''lean'', ''tie'' or ''unstable'' — how the side attribution behaved across '
  'runs. ''tie'' means measured well and genuinely close: render as evenly '
  'divided, never as a direction. ''unstable'' means the direction reversed '
  'and the side lists are NULL by intent. NULL when runs is 1 or the row '
  'predates migration 075.';

ALTER TABLE signal_consensus
  DROP CONSTRAINT IF EXISTS signal_consensus_sides_balance_values;
ALTER TABLE signal_consensus
  ADD CONSTRAINT signal_consensus_sides_balance_values
  CHECK (sides_balance IS NULL OR sides_balance IN ('lean', 'tie', 'unstable'));

-- The boolean and the three-way reading must never disagree. If they can, a
-- frontend reading one and a report reading the other will tell a reader two
-- different things about the same row.
ALTER TABLE signal_consensus
  DROP CONSTRAINT IF EXISTS signal_consensus_sides_balance_agrees;
ALTER TABLE signal_consensus
  ADD CONSTRAINT signal_consensus_sides_balance_agrees
  CHECK (
    sides_balance IS NULL
    OR sides_stable = (sides_balance <> 'unstable')
  );

-- Ties are the rows a frontend must treat specially, and there is no cheap way
-- to find them from sides_stable alone.
CREATE INDEX IF NOT EXISTS signal_consensus_sides_balance_idx
  ON signal_consensus (sides_balance)
  WHERE sides_balance IS NOT NULL;

-- signal_consensus is already public-read (migration 006) with RLS enabled;
-- adding a column inherits both. No grant changes needed.
