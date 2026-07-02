-- Migration 069 — Parity Health evidence cache (PH-3)
-- Two-table evidence cache for the appeal-letter evidence retrieval pipeline.
-- PHI FIREWALL: neither table has any PHI column, by construction. Keys are
--   non-PHI clinical concepts only (CPT code, denial_category, procedure terms).
-- COPYRIGHT (D5): content_tier encodes redistribution rights.
--   'full'    = PubMed abstracts, CMS/government policy — may store body text.
--   'bounded' = NCCN/ASCO & other copyrighted guidance — citation + link + short
--               factual summary ONLY; storing full body text is blocked by CHECK.
-- Grants name every role explicitly, per the Oct-30-2026 Supabase Data API policy.
-- UUID primary keys => no sequences => no sequence grants required.

BEGIN;

-- ========================================================================
-- Table 1: evidence_item — one row per real, verified real-world artifact
-- ========================================================================
CREATE TABLE public.evidence_item (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source              text NOT NULL
                          CHECK (source IN ('pubmed','cms_moldx','cms_ncd_lcd','fda','nccn','asco','other')),
    source_uid          text NOT NULL,          -- PMID, LCD/article ID, FDA ID, etc.
    title               text,
    citation            text,                   -- formatted citation string
    url                 text,
    pub_year            integer,
    study_type          text,                   -- RCT | meta_analysis | guideline | coverage_policy | designation | other
    content_tier        text NOT NULL DEFAULT 'full'
                          CHECK (content_tier IN ('full','bounded')),
    summary             text,                   -- short factual summary (safe for ALL tiers)
    abstract            text,                   -- full body text; ONLY allowed when content_tier='full'
    metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,  -- authors, journal, MeSH, designation detail
    verified            boolean NOT NULL DEFAULT false,
    verified_at         timestamptz,
    verification_method text,                   -- e.g. 'esummary 200 + uid match'
    retracted           boolean NOT NULL DEFAULT false,
    content_hash        text,                   -- detect upstream changes on refresh
    fetched_at          timestamptz NOT NULL DEFAULT now(),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT evidence_item_source_uid_uniq UNIQUE (source, source_uid),
    -- Copyright guard: bounded (copyrighted) sources may not store full body text.
    CONSTRAINT evidence_item_bounded_no_fulltext
        CHECK (content_tier = 'full' OR abstract IS NULL)
);

COMMENT ON TABLE public.evidence_item IS
  'Verified evidence artifacts (PubMed/CMS/FDA/NCCN/ASCO). No PHI. content_tier=bounded blocks storing copyrighted full text. For bounded sources, metadata must also not contain full body text (app-enforced).';

-- ========================================================================
-- Table 2: evidence_query — one row per PHI-free concept query (dedupe/cache)
-- ========================================================================
CREATE TABLE public.evidence_query (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source          text NOT NULL
                      CHECK (source IN ('pubmed','cms_moldx','cms_ncd_lcd','fda','nccn','asco','other')),
    query_key       text NOT NULL,              -- normalized PHI-free query string, or a stable hash of it
    cpt_code        text,                       -- denormalized for lookup + eval reproducibility
    denial_category text,
    result_uids     text[] NOT NULL DEFAULT '{}',  -- evidence_item.source_uid values this query returned
    result_count    integer NOT NULL DEFAULT 0,
    fetched_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz,                -- TTL / staleness horizon (short for CMS, long for PubMed)
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT evidence_query_key_uniq UNIQUE (source, query_key)
);

COMMENT ON TABLE public.evidence_query IS
  'Cache of PHI-free concept queries -> result UIDs. No PHI. Keyed on CPT/denial_category/source. If a raw query can exceed the btree index limit, store a hash in query_key.';

-- ========================================================================
-- Indexes
-- ========================================================================
CREATE INDEX evidence_item_source_idx   ON public.evidence_item  (source);
CREATE INDEX evidence_query_concept_idx ON public.evidence_query (cpt_code, denial_category, source);
CREATE INDEX evidence_query_expires_idx ON public.evidence_query (expires_at);

-- ========================================================================
-- Row Level Security: enable on both. No policies are created intentionally
-- (default-deny for anon/authenticated; service_role bypasses RLS).
-- ========================================================================
ALTER TABLE public.evidence_item  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_query ENABLE ROW LEVEL SECURITY;

-- ========================================================================
-- Grants — explicit per role. CREATE TABLE auto-grants DML to anon+authenticated;
-- revoke it, then grant only service_role.
-- ========================================================================
REVOKE ALL ON public.evidence_item  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.evidence_query FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.evidence_item  TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.evidence_query TO service_role;

COMMIT;
