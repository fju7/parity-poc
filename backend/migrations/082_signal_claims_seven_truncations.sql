-- Migration 082: seven claim sentences corrected, fixing forward -- the figure
-- each stated was a truncation of the figure its source states.
--
-- APPLIED 2026-09-14 by UPDATE through the service client on the operator's
-- instruction; here so the change is on the record and re-runnable. Idempotent.
-- The old text is preserved beside this file in 082_signal_claims_seven_
-- truncations.json and in the mmr publication record at gate b8d47ee.
--
-- WHY: FIGURE binds a figure at the precision it was stated (verify/numbers.py);
-- '650,000' for Hviid's 657 461 rounds to 660,000, '530,000' for Madsen's
-- 537,303 rounds to 540,000, '1.2 million' for Taylor's 1,256,407 rounds to 1.3
-- million. The ruling of 2026-09-14: do not loosen FIGURE; these are the claims'
-- fault and the fix is the sentence. The seven remaining 'figure not in source'
-- refusals that are the abstract's silence, and the four mis-linked accountability
-- claims, are left alone. curator: Claude Opus 5 on the operator's direction.

UPDATE signal_claims SET claim_text = 'A Danish cohort study examined 657,461 children born between 1999 and 2010 for an association between MMR vaccination and autism.' WHERE id = 'ca508e86-9c7c-4b70-8bfe-a39ab77d7caf';
UPDATE signal_claims SET claim_text = 'MMR-vaccinated children showed no increased risk of autism compared to unvaccinated children in a cohort of 657,461 Danish children.' WHERE id = '295dd47e-4878-4603-80ec-991836ff85f1';
UPDATE signal_claims SET claim_text = 'A Danish cohort study followed 657,461 children born between 1999 and 2010 to examine the relationship between MMR vaccination and autism.' WHERE id = '36c5e766-4651-49d4-a8c7-d26733de3dbe';
UPDATE signal_claims SET claim_text = 'A Danish registry study followed 657,461 children born in Denmark between 1999 and 2010 to examine the relationship between MMR vaccination and autism.' WHERE id = 'a586782f-1dbd-4ee2-8851-a2454b6aef5e';
UPDATE signal_claims SET claim_text = 'A Danish cohort study followed 537,303 children born between 1991 and 1998, comparing autism rates between 440,655 MMR-vaccinated and 96,648 unvaccinated children using national registry data.' WHERE id = '65012622-9f24-4c21-a32b-eec0bf5da472';
UPDATE signal_claims SET claim_text = 'The Danish cohort study followed 537,303 children born between 1991 and 1998, comparing autism rates between MMR-vaccinated and unvaccinated children.' WHERE id = '74060ece-eab1-426a-9db6-9fb9c81a550c';
UPDATE signal_claims SET claim_text = 'A meta-analysis by Taylor et al. pooled data from 1,256,407 children across five cohort studies and five case-control studies.' WHERE id = 'f24515e1-65ec-442b-bb5e-53adc4efe6dd';
