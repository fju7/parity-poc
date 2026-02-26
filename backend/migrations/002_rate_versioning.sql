-- 002_rate_versioning.sql
-- Historical CMS rate data versioning infrastructure.
-- Run in Supabase SQL Editor.

-- Enable uuid-ossp if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- 1. Rate schedule version registry
-- =========================================================================

CREATE TABLE IF NOT EXISTS rate_schedule_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_type   TEXT NOT NULL CHECK (schedule_type IN ('PFS', 'OPPS', 'CLFS')),
    vintage_year    INTEGER NOT NULL,
    vintage_quarter INTEGER,  -- NULL for annual schedules (PFS, OPPS); 1-4 for quarterly (CLFS)
    effective_date  DATE NOT NULL,
    expiry_date     DATE,     -- NULL means "current / no successor loaded yet"
    is_current      BOOLEAN NOT NULL DEFAULT FALSE,
    source_file     TEXT,
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    row_count       INTEGER,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_rsv_type_effective
    ON rate_schedule_versions (schedule_type, effective_date);

CREATE INDEX IF NOT EXISTS idx_rsv_current
    ON rate_schedule_versions (schedule_type) WHERE is_current = TRUE;

-- =========================================================================
-- 2. PFS historical rates
-- =========================================================================

CREATE TABLE IF NOT EXISTS pfs_rates_historical (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_id          UUID NOT NULL REFERENCES rate_schedule_versions(id) ON DELETE CASCADE,
    hcpcs_code          TEXT NOT NULL,
    carrier             TEXT NOT NULL,
    locality_code       TEXT NOT NULL,
    nonfacility_amount  NUMERIC(10,2),
    facility_amount     NUMERIC(10,2)
);

CREATE INDEX IF NOT EXISTS idx_pfs_hist_version_code
    ON pfs_rates_historical (version_id, hcpcs_code);

CREATE INDEX IF NOT EXISTS idx_pfs_hist_code
    ON pfs_rates_historical (hcpcs_code);

-- =========================================================================
-- 3. OPPS historical rates
-- =========================================================================

CREATE TABLE IF NOT EXISTS opps_rates_historical (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_id      UUID NOT NULL REFERENCES rate_schedule_versions(id) ON DELETE CASCADE,
    hcpcs_code      TEXT NOT NULL,
    payment_rate    NUMERIC(10,2),
    description     TEXT
);

CREATE INDEX IF NOT EXISTS idx_opps_hist_version_code
    ON opps_rates_historical (version_id, hcpcs_code);

-- =========================================================================
-- 4. CLFS historical rates
-- =========================================================================

CREATE TABLE IF NOT EXISTS clfs_rates_historical (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_id      UUID NOT NULL REFERENCES rate_schedule_versions(id) ON DELETE CASCADE,
    hcpcs_code      TEXT NOT NULL,
    payment_rate    NUMERIC(10,2),
    description     TEXT
);

CREATE INDEX IF NOT EXISTS idx_clfs_hist_version_code
    ON clfs_rates_historical (version_id, hcpcs_code);

-- =========================================================================
-- 5. Seed current 2026 versions into registry
-- =========================================================================

INSERT INTO rate_schedule_versions (schedule_type, vintage_year, vintage_quarter, effective_date, expiry_date, is_current, source_file, notes)
VALUES
    ('PFS',  2026, NULL, '2026-01-01', NULL, TRUE, 'cy2026-carrier-files-nonqp-updated-12-29-2025.zip', 'CMS PFS 2026 — loaded from in-memory CSV at startup'),
    ('OPPS', 2026, NULL, '2026-01-01', NULL, TRUE, 'opps_rates.csv',                                    'CMS OPPS 2026 — loaded from in-memory CSV at startup'),
    ('CLFS', 2026, 1,    '2026-01-01', NULL, TRUE, 'clfs_rates.csv',                                    'CMS CLFS 2026 Q1 — loaded from in-memory CSV at startup');
