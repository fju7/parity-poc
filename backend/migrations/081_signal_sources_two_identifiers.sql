-- Migration 081: two identifiers in signal_sources corrected, fixing forward.
--
-- APPLIED 2026-09-14 by UPDATE through the service client on the operator's
-- instruction, before this file was committed; here so the change is on the
-- record and re-runnable. Idempotent. The frozen snapshot
-- (scripts/signal/output/verify_sources_2026-09-14.json), the mmr publication
-- record at gate 2b84a4a and the survival read all preserve the WRONG values
-- permanently -- that is what the freeze is for.
--
-- WHY: these are a NONEXISTENT identifier and a WRONG_DOCUMENT identifier in
-- the two most consequential places in the mmr-vaccine-autism corpus. The
-- Jain 2015 JAMA cohort (95,727 US children, the largest sibling-risk
-- analysis) was stored as 10.1001/jama.2015.1534, which resolves to nothing.
-- The Honda 2005 Japan MMR-withdrawal study -- the one natural experiment on
-- the question -- was stored twice, as 10.1111/j.1469-8749.2005.tb01095.x
-- (a gastrostomy-tube paper) and 10.1111/j.1469-8749.2005.tb01215.x (a
-- botulinum-toxin paper); it is not even in that journal. Seventeen claims
-- rested on the four rows and every one was withheld at the first freeze.
--
-- HOW FOUND: exact-title search on Europe PMC, the returned title read back
-- (the golden-set rule), 2026-09-14:
--   "Autism occurrence by MMR vaccine status among US children with older
--    siblings with and without autism" -> PMID 25898051, JAMA 2015,
--    doi 10.1001/jama.2015.3077
--   "No effect of MMR withdrawal on the incidence of autism: a total
--    population study" -> PMID 15877763, J Child Psychol Psychiatry 2005,
--    doi 10.1111/j.1469-7610.2005.01425.x
-- curator: Claude Opus 5, on the operator's direction; recorded in
-- docs/signal-corpus-freeze.md.

UPDATE signal_sources SET url = 'https://doi.org/10.1001/jama.2015.3077'
 WHERE url = 'https://doi.org/10.1001/jama.2015.1534';
UPDATE signal_sources SET url = 'https://doi.org/10.1111/j.1469-7610.2005.01425.x'
 WHERE url IN ('https://doi.org/10.1111/j.1469-8749.2005.tb01095.x',
               'https://doi.org/10.1111/j.1469-8749.2005.tb01215.x');
