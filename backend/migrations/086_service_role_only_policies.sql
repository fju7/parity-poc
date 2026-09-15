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
-- The same shape is on thirteen more tables (query below). The name says
-- what was intended; the SQL says what happened. This is the same defect
-- migration 084 closed on topic_publications/topic_rechecks after 080.
--
-- WHAT THIS DOES
-- --------------
-- Account / PHI / billing tables: drop the public policy, recreate it for
-- service_role only, and REVOKE every privilege from PUBLIC, anon and
-- authenticated. The backend reads these with the service key (RLS bypass;
-- unaffected). The frontend reads none of them directly (grep of
-- frontend/src .from(...) on 2026-09-15: profiles, signal_*, topic_*).
--
-- Reference-data tables (mue_limits, ncci_edits, pharmacy_asp): keep anon /
-- authenticated SELECT -- public reference data is fine to read -- but revoke
-- INSERT/UPDATE/DELETE/TRUNCATE, which nobody outside the loaders should hold.
--
-- The SELECT-only public policies on clfs/opps/pfs_rates_historical,
-- rate_schedule_versions, signal_analytical_profiles and
-- signal_platform_metrics are left as they are: read-only reference data.
--
-- AUTHORED, NOT APPLIED. Tier-1 review required. After applying, re-run:
--   select tablename from pg_policies where schemaname='public'
--     and roles='{public}' and qual='true' and cmd='ALL';    -- expect 0 rows
-- and the anon-key probe on provider_appeals must return 0 rows / 401.

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
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access" ON public.%I', t);
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access on %s" ON public.%I', t, t);
        EXECUTE format('CREATE POLICY "Service role full access" ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', t);
        EXECUTE format('REVOKE ALL ON public.%I FROM PUBLIC, anon, authenticated', t);
        EXECUTE format('GRANT ALL ON public.%I TO service_role', t);
    END LOOP;

    FOREACH t IN ARRAY reference_tables LOOP
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access" ON public.%I', t);
        EXECUTE format('DROP POLICY IF EXISTS "Service role full access on %s" ON public.%I', t, t);
        EXECUTE format('CREATE POLICY "Service role full access" ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true)', t);
        EXECUTE format('CREATE POLICY "Public read" ON public.%I FOR SELECT TO anon, authenticated USING (true)', t);
        EXECUTE format('REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.%I FROM PUBLIC, anon, authenticated', t);
        EXECUTE format('GRANT SELECT ON public.%I TO anon, authenticated', t);
        EXECUTE format('GRANT ALL ON public.%I TO service_role', t);
    END LOOP;
END $$;

-- Sequences owned by these tables (id defaults) follow the same rule.
DO $$
DECLARE s record;
BEGIN
    FOR s IN
        SELECT seq.relname AS seqname
        FROM pg_class seq
        JOIN pg_depend d ON d.objid = seq.oid AND d.deptype = 'a'
        JOIN pg_class tbl ON tbl.oid = d.refobjid
        JOIN pg_namespace n ON n.oid = tbl.relnamespace
        WHERE seq.relkind = 'S' AND n.nspname = 'public'
          AND tbl.relname = ANY (ARRAY['employer_accounts','employer_contributions','employer_users',
                                       'health_subscriptions','health_users','provider_analyses','provider_appeals',
                                       'provider_audits','provider_contracts','provider_profiles','provider_subscriptions'])
    LOOP
        EXECUTE format('REVOKE ALL ON SEQUENCE public.%I FROM PUBLIC, anon, authenticated', s.seqname);
        EXECUTE format('GRANT ALL ON SEQUENCE public.%I TO service_role', s.seqname);
    END LOOP;
END $$;
