-- Migration 092: the BMJ's competing-interests correction to Godlee's editorial
-- enters the corpus as a source, and the editorial's row records it.
--
-- AUTHORED 2026-09-15, NOT APPLIED. Tier-1 review required (Fred). Idempotent.
-- (The operator asked for this as "091"; 091 became the approved re-cite of
-- claim 19214753 so that the re-freeze could follow it -- numbering is order
-- of application.)
--
-- WHAT: BMJ 2011;342:d1678, 15 March 2011, "Corrections": "The BMJ should
-- have declared competing interests in relation to this editorial by Fiona
-- Godlee and colleagues (BMJ 2011;342:c7452 ...). The BMJ Group receives
-- advertising and sponsorship revenue from vaccine manufacturers, and
-- specifically from Merck and GSK, which both manufacture MMR vaccines."
-- Fred's hand-fetched copy is tests/verify/fixtures/supplied/bmj-d1678-...pdf
-- (sha256 953b3c5010ca76c5...); its own head names bmj.d1678 first, so the
-- OPERATOR_SUPPLIED path admits it for its own DOI and refuses it for c7452.
--
-- WHY: Crossref reports c7452 "unchanged" -- no update-to, relation, or
-- updating work -- so the machine would never have surfaced the correction.
-- A reader who finds it independently will ask why the page did not. Same
-- reasoning as Walker-Smith v GMC (090): a page that presents the editorial's
-- characterisation must carry the journal's own correction to it.
--
-- HOW THE PAGE SAYS IT (not in this migration -- a code path, for review):
-- the row's title is prefixed "Correction —" so the Sources panel cannot show
-- two identical titles; metadata.corrects / corrected_by tie the two rows
-- together; and the publish gate should read a hand-curated correction on
-- the editorial's row as a status event, so the editorial carries the
-- "corrected" marker with the correction's text, exactly as a Crossref
-- update-to would -- the Phase 5 curated-events table, applied to a paper.
-- Claim 0eda21d2's link to c7452 is a SUBJECT link (the claim is about the
-- editorial), so a "corrected" status marks it and does not refuse it.
-- No claim is linked to d1678 by this migration.
--
-- curator: Claude Opus 5, on the operator's direction.

BEGIN;

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT i.id,
       'Correction — Wakefield''s article linking MMR vaccine and autism was fraudulent (competing interests)',
       'https://doi.org/10.1136/bmj.d1678',
       'journal', DATE '2011-03-15', NULL,
       jsonb_build_object('slug', 'bmj-2011-d1678-correction-competing-interests',
                          'citation', 'Corrections. Wakefield''s article linking MMR vaccine and autism was fraudulent. BMJ. 2011;342:d1678.',
                          'corrects', 'doi:10.1136/bmj.c7452',
                          'correction_kind', 'competing_interests',
                          'correction_text', 'The BMJ should have declared competing interests in relation to this editorial by Fiona Godlee and colleagues. The BMJ Group receives advertising and sponsorship revenue from vaccine manufacturers, and specifically from Merck and GSK, which both manufacture MMR vaccines.',
                          'not_surfaced_by', 'crossref: c7452 reports no update-to, relation, or updating work (checked 2026-09-15)',
                          'added_by_migration', '092', 'fetch_strategy', 'doi_metadata')
FROM signal_issues i
WHERE i.slug = 'mmr-vaccine-autism'
  AND NOT EXISTS (SELECT 1 FROM signal_sources s WHERE s.issue_id = i.id AND s.url = 'https://doi.org/10.1136/bmj.d1678');

UPDATE signal_sources s
   SET metadata = coalesce(s.metadata, '{}'::jsonb) || jsonb_build_object(
         'corrected_by', jsonb_build_object('doi', '10.1136/bmj.d1678', 'date', '2011-03-15',
                                            'kind', 'competing_interests',
                                            'summary', 'undeclared Merck and GSK advertising and sponsorship revenue',
                                            'source', 'hand-curated 2026-09-15; not in Crossref'))
  FROM signal_issues i
 WHERE i.id = s.issue_id AND i.slug = 'mmr-vaccine-autism'
   AND s.url = 'https://doi.org/10.1136/bmj.c7452'
   AND NOT (coalesce(s.metadata, '{}'::jsonb) ? 'corrected_by');

COMMIT;
