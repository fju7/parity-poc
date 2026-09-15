-- Migration 083: the Cochrane MMR review cited at its current version, fixing forward.
--
-- APPLIED 2026-09-15 by UPDATE through the service client on the operator's
-- instruction; here so the change is on the record and re-runnable. Idempotent.
-- The old citation (CD004407.pub4, 2020) is preserved in the mmr publication
-- records at gates 2b84a4a through 3a3a32c.
--
-- WHY: the publish gate refuses a support link to a source whose status was
-- 'superseded' before the freeze, and superseded stays in the refusal set
-- (ruling of 2026-09-15). Crossref records pub5 (22 November 2021) as the
-- new version of pub4 (found by filter=updates on the source itself, title
-- read back: "Vaccines for measles, mumps, rubella, and varicella in
-- children"). Nine claims rested on pub4; the corpus should cite the current
-- review and each claim re-binds against it -- a claim that fails against
-- pub5 was never supported by the current review, and its refusal stands.
-- curator: Claude Opus 5 on the operator's direction.

UPDATE signal_sources SET url = 'https://doi.org/10.1002/14651858.CD004407.pub5'
 WHERE url ILIKE '%14651858.CD004407.pub4%';
