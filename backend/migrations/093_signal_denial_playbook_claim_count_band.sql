-- 093: signal_denial_playbook.appeal_strength -> signal_claim_count_band  (APPEALS-5, ruled 2026-09-19)
--
-- LEFT UNAPPLIED. Apply only on Fred's explicit direction, and BEFORE deploying the code
-- that reads the new name (routers/signal_intelligence.py populate_denial_playbook,
-- routers/provider_audit.py ~1552) -- a migration hits the DB before the code does.
--
-- WHY. The column was a band of how many Signal claims map to the CPT's topic
-- (populate_denial_playbook: >=3 -> 'strong', >=1 -> 'moderate', else 'weak'). Claim count does
-- not bear on whether an appeal is strong; the name asserted a relation the procedure never
-- examined. This is NOT the retired letter grade provider_appeals.appeal_strength (APPEALS-4,
-- e679913); that column stays and is commented in 094.
--
-- WHAT. Rename the column, restate the values as the count bands they are, keep a default.
BEGIN;

ALTER TABLE public.signal_denial_playbook
  RENAME COLUMN appeal_strength TO signal_claim_count_band;

UPDATE public.signal_denial_playbook
   SET signal_claim_count_band = CASE signal_claim_count_band
                                   WHEN 'strong'   THEN '3_plus_claims'
                                   WHEN 'moderate' THEN '1_2_claims'
                                   WHEN 'weak'     THEN '0_claims'
                                   ELSE signal_claim_count_band
                                 END;

ALTER TABLE public.signal_denial_playbook
  ALTER COLUMN signal_claim_count_band SET DEFAULT '0_claims';

ALTER TABLE public.signal_denial_playbook
  ADD CONSTRAINT signal_claim_count_band_values
  CHECK (signal_claim_count_band IN ('0_claims', '1_2_claims', '3_plus_claims'));

COMMENT ON COLUMN public.signal_denial_playbook.signal_claim_count_band IS
  'Band of how many Signal claims map to the CPT''s topic: 0_claims / 1_2_claims / 3_plus_claims. A count, not a prediction about appeal outcome. Renamed from appeal_strength 2026-09-19 (APPEALS-5).';

COMMIT;
