-- Migration 093: WHU clean-core execution identity and append-only receipts.
--
-- This creates no public API and changes no current WHU publication behavior.
-- It is the first shadow-only foundation: exact consequential inputs, attempts,
-- provider identity, coverage state, and price knowledge are stored separately.
-- A completed execution is not a semantic verdict and this schema grants it no
-- publication authority.

CREATE TABLE IF NOT EXISTS public.whu_core_executions (
    execution_id uuid PRIMARY KEY,
    operation text NOT NULL CHECK (btrim(operation) <> ''),
    operation_version text NOT NULL CHECK (btrim(operation_version) <> ''),
    caller text NOT NULL CHECK (btrim(caller) <> ''),
    created_at timestamptz NOT NULL,
    subject_versions jsonb NOT NULL CHECK (
        jsonb_typeof(subject_versions) = 'array' AND jsonb_array_length(subject_versions) > 0
    ),
    request_payload_hash text NOT NULL CHECK (request_payload_hash ~ '^[0-9a-f]{64}$'),
    request_payload_ref text,
    code_identity jsonb NOT NULL CHECK (jsonb_typeof(code_identity) = 'object'),
    config_identity jsonb NOT NULL CHECK (jsonb_typeof(config_identity) = 'object'),
    requested_provider text,
    requested_model text,
    resolved_model text,
    prompt_hashes jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(prompt_hashes) = 'array'),
    policy_hashes jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(policy_hashes) = 'array'),
    fixture_hashes jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(fixture_hashes) = 'array'),
    input_population_id text,
    coverage_state text NOT NULL CHECK (coverage_state IN (
        'NOT_EVALUATED', 'PARTIALLY_EVALUATED', 'EVALUATED', 'INVALIDATED'
    )),
    pricing_state text NOT NULL CHECK (pricing_state IN (
        'KNOWN', 'ESTIMATED', 'UNKNOWN', 'NOT_APPLICABLE'
    )),
    cost_usd numeric(14, 6),
    input_tokens bigint CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens bigint CHECK (output_tokens IS NULL OR output_tokens >= 0),
    downstream_object_versions jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(downstream_object_versions) = 'array'),
    idempotency_key text NOT NULL UNIQUE CHECK (idempotency_key ~ '^[0-9a-f]{64}$'),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    CHECK (cost_usd IS NULL OR cost_usd >= 0),
    CHECK ((pricing_state = 'UNKNOWN' AND cost_usd IS NULL)
        OR (pricing_state IN ('KNOWN', 'ESTIMATED') AND cost_usd IS NOT NULL)
        OR pricing_state = 'NOT_APPLICABLE')
);

CREATE TABLE IF NOT EXISTS public.whu_core_execution_attempt_events (
    event_id uuid PRIMARY KEY,
    attempt_id uuid NOT NULL,
    execution_id uuid NOT NULL REFERENCES public.whu_core_executions(execution_id) ON DELETE RESTRICT,
    ordinal integer NOT NULL CHECK (ordinal > 0),
    event_sequence integer NOT NULL CHECK (event_sequence > 0),
    state text NOT NULL CHECK (state IN ('PENDING', 'RUNNING', 'COMPLETED', 'ERROR', 'CANCELLED')),
    occurred_at timestamptz NOT NULL,
    provider_request_id text,
    response_hash text CHECK (response_hash IS NULL OR response_hash ~ '^[0-9a-f]{64}$'),
    response_ref text,
    error_code text,
    error_detail text,
    UNIQUE (attempt_id, event_sequence),
    UNIQUE (execution_id, ordinal, event_sequence),
    CHECK (state <> 'COMPLETED' OR response_hash IS NOT NULL),
    CHECK (state <> 'ERROR' OR error_code IS NOT NULL),
    CHECK (state = 'ERROR' OR (error_code IS NULL AND error_detail IS NULL))
);

CREATE INDEX IF NOT EXISTS whu_core_attempt_events_execution_idx
    ON public.whu_core_execution_attempt_events (execution_id, ordinal, event_sequence);
CREATE INDEX IF NOT EXISTS whu_core_executions_subjects_idx
    ON public.whu_core_executions USING gin (subject_versions);
CREATE INDEX IF NOT EXISTS whu_core_executions_created_idx
    ON public.whu_core_executions (created_at);

ALTER TABLE public.whu_core_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whu_core_executions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.whu_core_execution_attempt_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.whu_core_execution_attempt_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role full access" ON public.whu_core_executions;
CREATE POLICY "Service role full access" ON public.whu_core_executions
    FOR ALL TO service_role USING (true) WITH CHECK (true);
DROP POLICY IF EXISTS "Service role full access" ON public.whu_core_execution_attempt_events;
CREATE POLICY "Service role full access" ON public.whu_core_execution_attempt_events
    FOR ALL TO service_role USING (true) WITH CHECK (true);

REVOKE ALL ON public.whu_core_executions FROM PUBLIC, anon, authenticated;
REVOKE ALL ON public.whu_core_execution_attempt_events FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON public.whu_core_executions TO service_role;
GRANT SELECT, INSERT ON public.whu_core_execution_attempt_events TO service_role;

COMMENT ON TABLE public.whu_core_executions IS
    'Append-only WHU clean-core execution identity. A row proves recorded execution inputs, not semantic truth.';
COMMENT ON COLUMN public.whu_core_executions.request_payload_ref IS
    'Access-controlled reference to request_payload_submitted_to_sdk; never described as provider wire bytes.';
COMMENT ON TABLE public.whu_core_execution_attempt_events IS
    'Append-only attempt events. Start, completion, error, and cancellation are new events; retries use a new attempt ID.';

-- Serialize events for one attempt and reject state laundering at the storage
-- boundary. An attempt starts once and may end once; ERROR can never acquire a
-- later COMPLETED event. A retry is a different attempt_id/ordinal.
CREATE OR REPLACE FUNCTION public.whu_core_validate_attempt_event()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $fn$
DECLARE
    previous public.whu_core_execution_attempt_events%ROWTYPE;
    latest_ordinal integer;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.attempt_id::text, 0));
    SELECT * INTO previous
      FROM public.whu_core_execution_attempt_events
     WHERE attempt_id = NEW.attempt_id
     ORDER BY event_sequence DESC
     LIMIT 1;

    IF NOT FOUND THEN
        IF NEW.event_sequence <> 1 OR NEW.state <> 'RUNNING' THEN
            RAISE EXCEPTION 'first attempt event must be sequence 1 RUNNING';
        END IF;
        PERFORM pg_advisory_xact_lock(hashtextextended(NEW.execution_id::text, 1));
        SELECT coalesce(max(ordinal), 0) INTO latest_ordinal
          FROM public.whu_core_execution_attempt_events
         WHERE execution_id = NEW.execution_id;
        IF NEW.ordinal <> latest_ordinal + 1 THEN
            RAISE EXCEPTION 'attempt ordinal must be contiguous: expected %, got %',
                latest_ordinal + 1, NEW.ordinal;
        END IF;
    ELSE
        IF NEW.execution_id <> previous.execution_id OR NEW.ordinal <> previous.ordinal THEN
            RAISE EXCEPTION 'attempt identity cannot change between events';
        END IF;
        IF NEW.event_sequence <> previous.event_sequence + 1 THEN
            RAISE EXCEPTION 'attempt event sequence must be contiguous';
        END IF;
        IF previous.state <> 'RUNNING'
           OR NEW.state NOT IN ('COMPLETED', 'ERROR', 'CANCELLED') THEN
            RAISE EXCEPTION 'illegal attempt transition: % -> %', previous.state, NEW.state;
        END IF;
    END IF;
    RETURN NEW;
END
$fn$;

DROP TRIGGER IF EXISTS whu_core_validate_attempt_event
    ON public.whu_core_execution_attempt_events;
CREATE TRIGGER whu_core_validate_attempt_event
    BEFORE INSERT ON public.whu_core_execution_attempt_events
    FOR EACH ROW EXECUTE FUNCTION public.whu_core_validate_attempt_event();

-- Append-only is enforced for service_role too. Corrections create a new
-- execution and optional supersession metadata; history is never rewritten.
CREATE OR REPLACE FUNCTION public.whu_core_refuse_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $fn$
BEGIN
    RAISE EXCEPTION 'WHU core execution receipts are append-only';
END
$fn$;

DROP TRIGGER IF EXISTS whu_core_executions_append_only ON public.whu_core_executions;
CREATE TRIGGER whu_core_executions_append_only
    BEFORE UPDATE OR DELETE ON public.whu_core_executions
    FOR EACH ROW EXECUTE FUNCTION public.whu_core_refuse_mutation();
DROP TRIGGER IF EXISTS whu_core_attempt_events_append_only ON public.whu_core_execution_attempt_events;
CREATE TRIGGER whu_core_attempt_events_append_only
    BEFORE UPDATE OR DELETE ON public.whu_core_execution_attempt_events
    FOR EACH ROW EXECUTE FUNCTION public.whu_core_refuse_mutation();
