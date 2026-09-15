"""Every table in public lands in a named bucket, or the build fails.

Two halves:
  offline  the 2026-09-15 pre-087 snapshot is the known-bad: the classifier
           must FAIL the tables migration 087 fixes, for the stated reasons,
           and must pass the same snapshot once 087's changes are simulated.
           Seen to fail before it was allowed to pass.
  live     with SUPABASE_URL + SUPABASE_SERVICE_KEY present (CI has them),
           call public.db_posture() and assert zero FAIL on the real project.
           Skipped -- loudly -- without credentials; never green while blind.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify import db_posture as dp  # noqa: E402

FIXTURE = os.path.join(BACKEND, "tests", "verify", "fixtures", "db_posture_2026-09-15_pre087.json")
DROPS_087 = {
    "broker_client_benchmarks": ["public read by share token"],
    "employer_benchmark_sessions": ["Allow anonymous inserts on employer_benchmark_sessions"],
    "employer_claims_uploads": ["Allow anonymous inserts on employer_claims_uploads"],
    "employer_scorecard_sessions": ["Allow anonymous inserts on employer_scorecard_sessions"],
    "signal_events": ["Authenticated users can insert events"],
}


@pytest.fixture(scope="module")
def snapshot():
    return json.load(open(FIXTURE, encoding="utf-8"))["tables"]


def _by_table(verdicts):
    return {v.table: v for v in verdicts}


def test_known_bad_snapshot_fails_for_the_named_reasons(snapshot):
    v = _by_table(dp.classify(snapshot))
    # a table with NO policy and default grants -- invisible to a policy query
    assert v["provider_appeal_letters"].bucket == "FAIL"
    assert any(r.startswith("dormant_client_grants") for r in v["provider_appeal_letters"].reasons)
    # the name-versus-qual lint
    assert any(r.startswith("name_claims_condition_qual_is_true") for r in v["broker_client_benchmarks"].reasons)
    assert any(r.startswith("name_claims_condition_qual_is_true") for r in v["signal_events"].reasons)
    # unconditional client inserts
    for t in ("employer_benchmark_sessions", "employer_claims_uploads", "employer_scorecard_sessions"):
        assert any(r.startswith("unconditional_insert_for_clients") for r in v[t].reasons), t
    # TRUNCATE is not subject to RLS
    assert any(r.startswith("clients_hold_") and "TRUNCATE" in r for r in v["profiles"].reasons)
    # and the tables 086 fixed are clean already
    for t in ("provider_appeals", "health_users", "employer_users"):
        assert v[t].bucket == "service_role_only", (t, v[t].reasons)
    for t in ("mue_limits", "ncci_edits", "pharmacy_asp"):
        assert v[t].bucket == "public_read", (t, v[t].reasons)


def test_simulated_087_posture_is_clean(snapshot):
    stmts = dp.hygiene_statements(snapshot, drop_policies=DROPS_087)
    sim = []
    for r in snapshot:
        rr = json.loads(json.dumps(r)); n = rr["table_name"]
        rr["policies"] = [p for p in rr["policies"] if p["name"] not in DROPS_087.get(n, [])]
        for s in stmts:
            if f" ON public.{n} FROM " in s:
                privs = s.split("REVOKE ")[1].split(" ON ")[0].split(", "); role = s.split(" FROM ")[1].rstrip(";")
                rr["grants"][role] = [g for g in rr["grants"].get(role, []) if g not in privs]
        sim.append(rr)
    vs = dp.classify(sim)
    fails = [v for v in vs if v.bucket == "FAIL"]
    assert not fails, dp.report(vs)
    # nothing left to revoke once the floor is reached
    assert dp.hygiene_statements(sim) == []
    # every bucket is populated by name, not by accident
    buckets = {v.bucket for v in vs}
    assert {"service_role_only", "public_read", "gated_read", "user_scoped"} <= buckets


def test_every_allow_list_entry_is_a_public_read_table(snapshot):
    allow = dp._allow()
    names = {r["table_name"] for r in snapshot}
    for t in allow:
        assert t in names, f"allow-list names a table that does not exist: {t}"


def test_the_087_file_carries_the_generated_floor(snapshot):
    """The migration's REVOKE block must be exactly what the classifier
    generates from the snapshot; a hand edit to one side without the other
    is how a floor drifts."""
    path = os.path.join(BACKEND, "migrations", "087_db_posture_and_grant_floor.sql")
    body = open(path, encoding="utf-8").read()
    expected = dp.hygiene_statements(snapshot, drop_policies=DROPS_087)
    in_file = [l.strip() for l in body.splitlines() if l.startswith("REVOKE ") and " ON public." in l]
    assert in_file == expected


# ---------------------------------------------------------------------------
# live
# ---------------------------------------------------------------------------
_HAS_CREDS = bool(os.environ.get("SUPABASE_URL")) and bool(os.environ.get("SUPABASE_SERVICE_KEY"))


@pytest.mark.skipif(not _HAS_CREDS, reason="SUPABASE_URL / SUPABASE_SERVICE_KEY absent: the live posture check did not run")
def test_live_project_has_no_table_outside_a_bucket():
    rows = dp.fetch_live()
    assert rows, "db_posture() returned nothing -- is migration 087 applied, and is this the Parity project?"
    vs = dp.classify(rows)
    fails = [v for v in vs if v.bucket == "FAIL"]
    assert not fails, dp.report(vs)
