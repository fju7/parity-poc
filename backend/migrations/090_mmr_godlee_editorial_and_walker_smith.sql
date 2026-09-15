-- Migration 090: two sources added to mmr-vaccine-autism; one claim re-cited.
--
-- AUTHORED 2026-09-15, NOT APPLIED. Tier-1 review required (Fred). Post-freeze
-- change; rows go in docs/signal-corpus-freeze.md when applied. Idempotent.
--
-- (a) Godlee F, Smith J, Marcovitch H. "Wakefield's article linking MMR
--     vaccine and autism was fraudulent." BMJ 2011;342:c7452, 6 January 2011,
--     doi 10.1136/bmj.c7452. NOT in the corpus. Claim 0eda21d2 -- "The BMJ
--     formally characterized the 1998 Lancet paper ... as 'an elaborate fraud'
--     in an editorial by editor Fiona Godlee" -- is linked to Deer's feature
--     (bmj.c5347), which does not contain the phrase; the editorial the claim
--     itself names does, once: "the paper was in fact an elaborate fraud".
--     Re-citing the claim to the document it names is a citation correction,
--     not a judgment about support: SPAN decides that at publish. The text was
--     hand-fetched and admitted under Provenance.OPERATOR_SUPPLIED
--     (sha256 f58bdbdd4b9b0cbd4e38976fbd9ee813a96b19bcd92e251fcd3c91371afb6084,
--     Fred Ugast, https://www.bmj.com/content/342/bmj.c7452); the BMJ serves a
--     403 to the machine.
-- (b) Walker-Smith v General Medical Council [2012] EWHC 503 (Admin), Case No
--     CO/7039/2010, Mitting J, 7 March 2012. The High Court quashed the GMC
--     panel's findings and sanction against Professor Walker-Smith. Added as
--     its own source, LINKED TO NO CLAIM: which claims it qualifies is the
--     operator's page-wording decision (report of 2026-09-15). Machine-
--     fetchable from The National Archives' Find Case Law (HTTP 200, 223k
--     chars); Fred's hand-fetched copy (76 pp, sha256
--     072ea8a12594eeb9...) confirmed the identity. content_text is NULL on
--     both rows: the gate fetches the document itself; nothing model-written
--     enters.
--
-- curator: Claude Opus 5, on the operator's direction.

BEGIN;

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT i.id,
       'Wakefield''s article linking MMR vaccine and autism was fraudulent',
       'https://doi.org/10.1136/bmj.c7452',
       'journal', DATE '2011-01-06', NULL,
       jsonb_build_object('slug', 'godlee-2011-bmj-editorial-fraudulent',
                          'citation', 'Godlee F, Smith J, Marcovitch H. Wakefield''s article linking MMR vaccine and autism was fraudulent. BMJ. 2011;342:c7452.',
                          'added_by_migration', '090', 'fetch_strategy', 'doi_metadata')
FROM signal_issues i
WHERE i.slug = 'mmr-vaccine-autism'
  AND NOT EXISTS (SELECT 1 FROM signal_sources s WHERE s.issue_id = i.id AND s.url = 'https://doi.org/10.1136/bmj.c7452');

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT i.id,
       'Walker-Smith v General Medical Council [2012] EWHC 503 (Admin)',
       'https://caselaw.nationalarchives.gov.uk/ewhc/admin/2012/503',
       'regulatory', DATE '2012-03-07', NULL,
       jsonb_build_object('slug', 'walker-smith-v-gmc-2012-ewhc-503',
                          'citation', 'Walker-Smith v General Medical Council [2012] EWHC 503 (Admin), 7 March 2012, Mitting J, Case No CO/7039/2010.',
                          'added_by_migration', '090', 'fetch_strategy', 'metadata_only',
                          'status_registry', 'none: a judgment subject to appeal has no machine-readable status; human re-check interval required (Phase 5)')
FROM signal_issues i
WHERE i.slug = 'mmr-vaccine-autism'
  AND NOT EXISTS (SELECT 1 FROM signal_sources s WHERE s.issue_id = i.id AND s.url = 'https://caselaw.nationalarchives.gov.uk/ewhc/admin/2012/503');

-- claim 0eda21d2: cite the editorial it names, in place of Deer's feature
UPDATE signal_claim_sources cs
   SET source_id = (SELECT s.id FROM signal_sources s JOIN signal_issues i ON i.id = s.issue_id
                     WHERE i.slug = 'mmr-vaccine-autism' AND s.url = 'https://doi.org/10.1136/bmj.c7452')
 WHERE cs.claim_id = '0eda21d2-b057-45ba-84c1-6ec9c7c384d5'::uuid
   AND cs.source_id = '6ef0773d-65cb-443b-a92e-c33af266f3f8'::uuid;   -- Deer, bmj.c5347

COMMIT;
