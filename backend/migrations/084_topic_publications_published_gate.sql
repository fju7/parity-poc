-- Migration 084: topic_publications and topic_rechecks admit a row to anon
-- only when the topic is published. Closes a hole one migration wide.
--
-- WHY: 080 created both tables with `FOR SELECT TO anon, authenticated
-- USING (true)`. Probed 2026-09-15 with mmr-vaccine-autism at status 'draft'
-- and one publication record stored: `set local role anon; select count(1)
-- from topic_publications` returned 1. A draft topic's record -- every claim
-- id it supports, every source id that survived, the full gate output -- was
-- public while 078 kept the topic itself, its claims and its sources dark.
--
-- The fix is the join 078 used for the slug-keyed tables (signal_cpt_mappings,
-- signal_denial_playbook): a row is readable only when signal_issues has a
-- row with that slug and status = 'published'. Both anon readers already treat
-- "no row" as not-published (backend/signal_reader.py latest_publication ->
-- None; frontend SignalApp.jsx -> notPublished), so a draft topic now reads
-- exactly as a topic with no record. service_role keeps ALL (bypasses RLS);
-- scripts/publish_topic.py and scripts/recheck_topic.py write with it.
--
-- Not signal_*; alters no row of any table. Idempotent.

DROP POLICY IF EXISTS "Public read topic_publications" ON topic_publications;
DROP POLICY IF EXISTS "Published read topic_publications" ON topic_publications;
CREATE POLICY "Published read topic_publications"
  ON topic_publications FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.slug = topic_publications.slug AND i.status = 'published'));

DROP POLICY IF EXISTS "Public read topic_rechecks" ON topic_rechecks;
DROP POLICY IF EXISTS "Published read topic_rechecks" ON topic_rechecks;
CREATE POLICY "Published read topic_rechecks"
  ON topic_rechecks FOR SELECT TO anon, authenticated
  USING (EXISTS (SELECT 1 FROM signal_issues i
                 WHERE i.slug = topic_rechecks.slug AND i.status = 'published'));
