-- Migration 089: one more mmr-vaccine-autism plain summary refused by the prose gate.
--
-- Operator-directed post-freeze change (docs/signal-corpus-freeze.md), 2026-09-15,
-- following 088. Claim 5b3bff25 ("Ten of the thirteen co-authors ... withdrew
-- their names ... in 2004", withheld by CHRONOLOGY) carried the summary "In 2004
-- -- six years before the paper was formally retracted -- ...". The 2004 is in
-- the claim; the 2010 is in neither the claim nor the fetched document (the
-- 1998 paper's abstract), only in the model's memory. "Six years" is arithmetic
-- over a date the model supplied: a fabricated figure, not a paraphrase count.
-- The gate's exemption for counting words now excludes a word followed by a
-- unit ("six years"), and refuses this summary. Same treatment as 088: the
-- summary is removed, not rewritten; the claim renders without one if it is
-- ever un-withheld.

UPDATE signal_claims SET plain_summary = NULL WHERE id = '5b3bff25-5a8c-4689-967d-04273804dc3f' AND plain_summary IS NOT NULL;
