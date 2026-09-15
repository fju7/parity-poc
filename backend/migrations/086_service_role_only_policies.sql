-- Migration 086: fourteen "Service role full access" policies that granted
-- full access to everyone.
--
-- WHY THIS EXISTS -- FOUND 2026-09-15 BY THE POST-MIGRATION GRANT CHECK ON 085
-- ----------------------------------------------------------------------------
-- The migration policy in CLAUDE.md requires, after every migration, a check
-- that anon and authenticated do not appear in the grants of the touched
-- table. Running it on provider_appeals after 085 found: RLS enabled, one
-- policy named "Service role full access", written
--
--     CREATE POLICY "Service role full access" ON provider_appeals
--         FOR ALL USING (true) WITH CHECK (true);
--
-- with no TO clause -- so it applies to PUBLIC -- while anon and
-- authenticated hold the default full DML grants CREATE TABLE gives them.
-- Probed with the anon key: GET /rest/v1/provider_appeals returned
-- HTTP 206, content-range 0-0/6. Every appeal letter (patient name in
-- letter_text) is readable, writable and deletable by anyone holding the
-- public anon key, which the frontend ships to every browser.
--
-- The same shape is on thirteen more tables. The name says what was
-- intended; the SQL says what happened. This is the same defect migration
-- 084 closed on topic_publications/topic_rechecks after 080.
--
-- WHEN IT STARTED (the exposure window has a start)
-- -----------------------------------------------
-- provider_appeals: migration 018 (2026-03-06) wrote it correctly, as
--   USING (auth.role() = 'service_role'). Migration 032 (committed 2026-03-12,
--   "provider_tables_company_id") DROPPED that policy and recreated it as
--   USING (true) WITH CHECK (true) -- on provider_appeals, provider_analyses,
--   provider_audits, provider_contracts and provider_subscriptions.
--   provider_profiles got the same text from 031 (2026-03-12).
--   pharmacy_asp from 039 (2026-03-14).
-- employer_accounts, employer_contributions, employer_users, health_users,
--   health_subscriptions, mue_limits, ncci_edits: NO migration file in the
--   repo creates them or their policy; they were created outside the
--   numbered series, and the Supabase migration history only begins at 069.
--   Earliest-existence bound from their own rows: employer_* 2026-02-25,
--   health_* 2026-03-12. The policy's creation date on these six is unknown.
-- So the window is 2026-03-12 (provider/health) or as early as 2026-02-25
-- (employer) to the application of this migration.
--
-- WHAT WAS FOUND IN THE LOGS
-- --------------------------
-- Supabase edge logs retain 90 days (earliest 2026-06-17 15:44Z). Every day
-- from then to 2026-09-15 15:00Z was queried for a request to any of the
-- fourteen tables whose JWT role was not service_role. Result: exactly one,
-- the operator's own anon-key GET probe on provider_appeals at
-- 2026-09-15 14:14:47Z. Before 2026-06-17 the logs do not exist; whether the
-- anon key was ever used against these tables between 2026-03-12 and
-- 2026-06-17 is unknowable.
--
-- WHAT THIS DOES
-- --------------
-- Account / PHI / billing tables (eleven): ENABLE RLS explicitly (it was
-- verified on provider_appeals only; the rest were assumed until the
-- pre-check below confirmed all fourteen), drop the public policy, recreate
-- it for service_role only, and REVOKE every privilege from PUBLIC, anon and
-- authenticated. The backend reads these with the service key (RLS bypass;
-- unaffected). The frontend reads none of them directly: frontend/src calls
-- .from() on profiles (x7), signal_* and topic_* only, and `profiles` is a
-- separate object from provider_profiles (verified independently by the
-- operator 2026-09-15). REVOKING `authenticated` COMMITS THESE ELEVEN TABLES
-- TO BACKEND-MEDIATED ACCESS PERMANENTLY: a future feature that wants a
-- browser to read one of them must go through the API, not through
-- supabase-js with a user JWT. That is the intent, not an oversight.
--
-- Reference-data tables (mue_limits, ncci_edits, pharmacy_asp): keep anon /
-- authenticated SELECT -- public reference data is fine to read -- but revoke
-- INSERT/UPDATE/DELETE/TRUNCATE, which nobody outside the loaders should hold.
-- "Public read" is dropped before it is created (42710 otherwise).
--
-- Sequences: all eleven account tables have uuid primary keys and own no
-- sequence and no identity column (checked in pg_attribute/pg_depend on
-- 2026-09-15). ncci_edits alone has a bigint IDENTITY id (deptype 'i'). The
-- sequence block therefore covers deptype 'a' AND 'i' and runs over all
-- fourteen tables; today it touches exactly one sequence, ncci_edits's.
--
-- LEFT ALONE, AS A DECISION
-- -------------------------
-- The SELECT-only public policies on clfs_rates_historical,
-- opps_rates_historical, pfs_rates_historical and rate_schedule_versions are
-- CMS rate tables: public reference data.
-- signal_analytical_profiles (4 rows: name, description, weights,
-- trade_off_summary for Balanced / Regulatory / Clinical / Patient) is the
-- scoring-profile configuration the public Signal UI renders in
-- ProfileSelector; it contains no user or corpus data, and the page must
-- read it anonymously.
-- signal_platform_metrics (0 rows; metric_key, metric_value, display_label,
-- visible) is the landing-page counter table; it is published by design and
-- the frontend reads it anonymously.
-- Both are read-only to anon after this migration as before; neither holds
-- anything a person wrote.
--
-- NOT COVERED HERE -- SURFACED BY THE WIDENED PRE-CHECK, FOR REVIEW (087)
-- -----------------------------------------------------------------------
-- The widened check (every policy whose roles include public/anon/
-- authenticated, any cmd) also shows: broker_client_benchmarks
-- "public read by share token" FOR SELECT TO anon USING (true) -- the token
-- is not in the qual, so anon reads every broker's client benchmarks, not
-- just the shared one; and "Allow anonymous inserts" WITH CHECK (true) on
-- employer_benchmark_sessions, employer_claims_uploads and
-- employer_scorecard_sessions, which the backend does not need (it writes
-- with the service key). These are outside what was reviewed for 086 and are
-- staged separately.
--
-- APPLIED FROM THIS FILE in a single transaction. After applying:
--   1. the widened policy query must show no qual='true' policy for
--      public/anon/authenticated on any of the fourteen except the SELECT
--      "Public read" on the three reference tables;
--   2. an anon-key GET on provider_appeals must return 401/permission denied
--      or zero rows; an anon-key INSERT and DELETE must be refused;
--   3. a provider appeal generated end to end with the service key must still
--      store, including its verification record.

DO $$
DECLARE
    t text;
    account_tables text[] := ARRAY[
        'employer_accounts', 'employer_contributions', 'employer_users',
        'health_subscriptions', 'health_users',
        'provider_analyses', 'provider_appeals', 'provider_audits',
        'provider_contracts', 'provider_profiles', 'provider_subscriptions'
    ];
    reference_tables text[] := ARRAY['mue_limits', 'ncci_edits', 'pharmacy_asp'];
BEGIN
    FOREACH t IN ARRAY account_tables LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access" ON public.%I', t);
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access on %s" ON public.%I', t, t);
        EXECUTE format('CREATE POLICY "Service role full access" ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', t);
        EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC, anon, authenticated', t);
        EXECUTE format('GRANT ALL ON public.%I TO service_role', t);
    END LOOP;

    FOREACH t IN ARRAY reference_tables LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access" ON public.%I', t);
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access on %s" ON public.%I', t, t);
        EXECUTE format('DROP POLICY IF EXISTS "Public read" ON public.%I', t);
        EXECUTE format('CREATE POLICY "Service role full access" ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', t);
        EXECUTE format('CREATE POLICY "Public read" ON public.%I FOR SELECT TO anon, authenticated USING (true)', t);
        EXECUTE format('REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.%I FROM PUBLIC, anon, authenticated', t);
        EXECUTE format('GRANT SELECT ON public.%I TO anon, authenticated', t);
        EXECUTE format('GRANT ALL ON public.%I TO service_role', t);
    END LOOP;
END $$;

-- Sequences owned by any of the fourteen (serial: deptype 'a'; identity:
-- deptype 'i'). Today: ncci_edits.id only.
DO $$
DECLARE s record;
BEGIN
    FOR s IN
        SELECT seq.relname AS seqname
        FROM pg_class seq
        JOIN pg_depend d ON d.objid = seq.oid AND d.deptype IN ('a', 'i')
        JOIN pg_class tbl ON tbl.oid = d.refobjid
        JOIN pg_namespace n ON n.oid = tbl.relnamespace
        WHERE seq.relkind = 'S' AND n.nspname = 'public'
          AND tbl.relname = ANY (ARRAY['employer_accounts','employer_contributions','employer_users',
                                       'health_subscriptions','health_users','provider_analyses','provider_appeals',
                                       'provider_audits','provider_contracts','provider_profiles','provider_subscriptions',
                                       'mue_limits','ncci_edits','pharmacy_asp'])
    LOOP
        EXECUTE format('REVOKE ALL ON SEQUENCE public.%I FROM PUBLIC, anon, authenticated', s.seqname);
        EXECUTE format('GRANT ALL ON SEQUENCE public.%I TO service_role', s.seqname);
    END LOOP;
END $$;
