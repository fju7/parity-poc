-- Migration 036: Provider benchmark observations table
-- Captures anonymized denial rate and underpayment observations from 835 analyses
-- No PHI, no user_id — used to build proprietary benchmarks over time

CREATE TABLE IF NOT EXISTS provider_benchmark_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    observed_at TIMESTAMPTZ DEFAULT NOW(),

    -- What was analyzed (no PHI, no practice name, no user ID)
    cpt_code TEXT NOT NULL,
    payer_category TEXT,     -- "Medicare", "BCBS", "Aetna", "Commercial", etc.
    specialty TEXT,          -- from provider_profiles if available

    -- Observation data
    was_denied BOOLEAN NOT NULL,
    was_underpaid BOOLEAN NOT NULL,
    paid_as_pct_of_contracted FLOAT,  -- e.g. 0.92 = paid at 92% of contract
    denial_code TEXT,                 -- CO-16, CO-45, etc.

    -- Geographic context (coarse — no ZIP, just region)
    region TEXT,   -- "Northeast", "South", "Midwest", "West", "Unknown"

    -- Metadata
    line_count_in_analysis INT  -- how many lines were in the full 835
                                -- (context for statistical weight)
);

CREATE INDEX IF NOT EXISTS idx_pbo_cpt_code
    ON provider_benchmark_observations(cpt_code);
CREATE INDEX IF NOT EXISTS idx_pbo_observed_at
    ON provider_benchmark_observations(observed_at);

-- No RLS needed — this table has no PHI and no user_id.
-- Service role key writes; no user reads directly.
