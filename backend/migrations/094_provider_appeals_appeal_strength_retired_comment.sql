-- 094: register provider_appeals.appeal_strength as RETIRED  (APPEALS-5 ITEM 4, 2026-09-19)
--
-- LEFT UNAPPLIED. Apply only on Fred's explicit direction. Comment only: no data change, no drop.
--
-- The column (migration 018) held the model-authored letter grade high|medium|low. APPEALS-4
-- (e679913, 2026-09-19) removed every writer, reader and renderer; the rows that exist are
-- historical and must not be read. It is deliberately NOT dropped: the rows are the record of
-- what was once asserted to users. backend/tests/test_appeals4_retired_and_dated.py fails if a
-- reader of this column returns.
BEGIN;

COMMENT ON COLUMN public.provider_appeals.appeal_strength IS
  'RETIRED as of e679913 (2026-09-19, APPEALS-4): model-authored letter grade high|medium|low; no writer, no reader, must not be read. Rows are historical. Not dropped: they record what was once asserted.';

COMMIT;
