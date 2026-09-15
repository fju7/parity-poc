-- Migration 088: five mmr-vaccine-autism plain summaries refused by the prose gate.
--
-- Operator-directed post-freeze change (docs/signal-corpus-freeze.md), 2026-09-15.
--
-- WHY
-- ---
-- A plain summary is a paraphrase surface. A definitional gloss, a currency
-- conversion, a gestational threshold or an FDA-label characterisation is an
-- assertion nothing examined, sitting under a bound claim and looking exactly
-- like it. That includes "1.0 would mean identical risk" -- true, helpful, and
-- it still goes, because keeping it gives the methodology page an exception to
-- explain. If that gloss is wanted it belongs in the gated glossary or in
-- hand-written copy. The five below were refused by
-- scripts/signal/prose_gate.py run read-only over the frozen record
-- (verify/policy.check, surface scripts.signal.score_claims::generate_summaries):
--
--   8b84dcfd  renders   "1.0" (odds ratio 0.86 in the claim; 1.0 added as a gloss)
--   6bbf8769  renders   "37 weeks" (the model's own definition of preterm)
--   43dc8f6d  withheld  "1.0" (same gloss under RR 0.92)
--   58b05989  withheld  "over half a million US dollars" (a conversion of £435,643)
--   77ad8922  withheld  "FDA-approved label" (the claim says "FDA product labeling")
--
-- The three on withheld claims are removed too, so nothing is waiting to
-- render if a claim is ever un-withheld. Not rewritten: rewriting under the
-- freeze would generate new unverified prose to patch unverified prose. The
-- refusal path is "no summary stored; the claim renders without one", which
-- for an existing row is NULL.
--
-- READ-ONLY EVERYWHERE ELSE: nothing in signal_sources, signal_claim_sources,
-- signal_claim_scores/composites, signal_consensus, signal_summaries or the
-- publication record changes. The 381-source research snapshot
-- (scripts/signal/output/verify_sources_2026-09-14.json) is a file and is not
-- touched. Each UPDATE names one id and requires the summary to be present,
-- so a re-run changes nothing.

UPDATE signal_claims SET plain_summary = NULL WHERE id = '8b84dcfd-00ac-4205-b926-6fab4ded379b' AND plain_summary IS NOT NULL;
UPDATE signal_claims SET plain_summary = NULL WHERE id = '6bbf8769-8079-411f-995e-63314469fc7e' AND plain_summary IS NOT NULL;
UPDATE signal_claims SET plain_summary = NULL WHERE id = '43dc8f6d-84bb-472d-97a0-4c0dd0f8cd2d' AND plain_summary IS NOT NULL;
UPDATE signal_claims SET plain_summary = NULL WHERE id = '58b05989-bab4-4f86-8a18-92278eec623c' AND plain_summary IS NOT NULL;
UPDATE signal_claims SET plain_summary = NULL WHERE id = '77ad8922-0a16-4bde-b105-a127fc8e783c' AND plain_summary IS NOT NULL;
