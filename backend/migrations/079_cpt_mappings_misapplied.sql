-- Migration 079: three CPT-to-topic mappings that were errors, removed.
--
-- APPLIED 2026-09-14 by DELETE through the service client, on the operator's
-- instruction, before this file was committed; it is here so the change is
-- on the record and re-runnable. Idempotent.
--
-- crispr-gene-therapy was mapped to 0537T and 0538T, which are the CAR-T
-- harvesting and preparation codes (the car-t-cell-therapy mapping keeps
-- them, correctly). Casgevy and Lyfgenia bill under the HSCT codes, not
-- these. 81479 is "unlisted molecular pathology procedure": an unlisted code
-- implies nothing about the subject.
--
-- THE FREEZE: this deletes three rows from a signal_* table. The table is
-- signal_cpt_mappings, seeded by migration 046 -- product configuration, not
-- evidence: no source, claim, score, consensus or summary is touched. It is
-- recorded as the one post-freeze row change in docs/signal-corpus-freeze.md.
-- The 21 mappings judged generic (an office visit is not a GLP-1 prescription)
-- are left for the relevance design.

DELETE FROM signal_cpt_mappings
 WHERE topic_slug = 'crispr-gene-therapy'
   AND cpt_code IN ('0537T', '0538T', '81479');
