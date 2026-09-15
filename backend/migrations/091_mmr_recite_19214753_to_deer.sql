-- Migration 091: one claim re-cited. mmr-vaccine-autism, claim 19214753
-- ("Andrew Wakefield had been paid by lawyers seeking evidence against vaccine
-- manufacturers at the time of the original 1998 research").
--
-- WHY: the claim cited The Lancet's retraction notice (bmj.c5347's neighbour,
-- 10.1016/S0140-6736(10)60175-4), whose text says nothing about lawyers or
-- payment; it bound FIGURE_BOUND on the year 1998 alone -- the false bind that
-- exposed the date-only levelling defect (fixed in verify/publish.py the same
-- day). Deer's BMJ feature (bmj.c5347, admitted OPERATOR_SUPPLIED) is the
-- document that reports the payment. Approved by the operator 2026-09-15
-- ("Re-cite 19214753 to Deer"). Idempotent. Register row in
-- docs/signal-corpus-freeze.md.
--
-- curator: Claude Opus 5, on the operator's direction.

UPDATE signal_claim_sources
   SET source_id = '6ef0773d-65cb-443b-a92e-c33af266f3f8'::uuid   -- Deer, bmj.c5347
 WHERE claim_id = '19214753-d0ad-45e6-87f3-6bda40817662'::uuid
   AND source_id = '196e03ba-4b2c-43f3-bdca-e28ddecfeb97'::uuid;  -- the retraction notice
