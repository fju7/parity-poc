"""APPEALS-8 (2026-09-21): the auto-generated topic request satisfies signal_topic_requests.

OI-PARITY-1: aggregate_denial_patterns inserted {parsed_title, parsed_description, raw_request,
status} and omitted topic_name, which has been NOT NULL with no default since migration 005.
Every threshold-crossing pattern since af25379 (2026-03-24, "use correct column names") raised
23502; the function-level handler logged the traceback and the flag update never ran.

Offline. The fake client enforces the one database rule that matters here (topic_name NOT NULL)
and records every write in order, so the test can assert the request row is complete and that
the pattern's flag is set only after the request exists.
"""
import asyncio
import os
import sys

import pytest

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers import signal_intelligence as SI  # noqa: E402

# One pattern already past the threshold (count >= 5), not yet requested.
THRESHOLD_ROW = {"id": "pat-1", "denial_code": "CO-50", "cpt_code": "90707", "payer": "Cigna",
                 "occurrence_count": 5, "total_value_at_risk": "600.00"}

# Columns of signal_topic_requests that are NOT NULL with no default (information_schema, 2026-09-21).
TOPIC_REQUEST_REQUIRED = ("topic_name",)
TOPIC_REQUEST_STATUSES = {"submitted", "pending", "clarification_needed", "approved", "processing",
                          "completed", "rejected"}


class _NotNullViolation(Exception):
    pass


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, sb, table):
        self.sb, self.table_name = sb, table
        self.op, self.payload, self.eqs = "select", None, []

    def select(self, *a, **k):
        self.op = "select"; return self
    def eq(self, col, val):
        self.eqs.append((col, val)); return self
    def limit(self, *a, **k):
        return self
    def insert(self, payload):
        self.op, self.payload = "insert", payload; return self
    def update(self, payload):
        self.op, self.payload = "update", payload; return self

    def execute(self):
        if self.op == "select":
            if self.table_name == "provider_denial_patterns" and ("topic_request_created", False) in self.eqs:
                return _Resp([dict(THRESHOLD_ROW)])
            return _Resp([])
        self.sb.writes.append((self.table_name, self.op, dict(self.payload), list(self.eqs)))
        if self.table_name == "signal_topic_requests" and self.op == "insert":
            for col in TOPIC_REQUEST_REQUIRED:
                if self.payload.get(col) is None:
                    raise _NotNullViolation(
                        f"null value in column \"{col}\" of relation \"signal_topic_requests\" violates not-null constraint")
            assert self.payload.get("status", "submitted") in TOPIC_REQUEST_STATUSES
        return _Resp([{"id": "req-1", **self.payload}])


class _FakeSB:
    def __init__(self):
        self.writes = []
    def table(self, name):
        return _Query(self, name)


@pytest.fixture
def sb(monkeypatch):
    fake = _FakeSB()
    monkeypatch.setattr(SI, "_get_sb", lambda: fake)
    return fake


def _run(sb):
    # No denied lines: skips the upsert loop and goes straight to the threshold check.
    asyncio.run(SI.aggregate_denial_patterns([], "Cigna"))
    return sb.writes


def test_threshold_pattern_creates_a_complete_topic_request(sb):
    writes = _run(sb)
    inserts = [w for w in writes if w[0] == "signal_topic_requests" and w[1] == "insert"]
    assert inserts, "no topic request was inserted"
    payload = inserts[0][2]
    assert payload["topic_name"], "topic_name is NOT NULL on signal_topic_requests"
    # Same convention as the human path (signal_topic_request.py): topic_name mirrors parsed_title.
    assert payload["topic_name"] == payload["parsed_title"] == "Denial pattern: CO-50 on CPT 90707"
    assert payload["status"] == "pending"
    assert payload["raw_request"].startswith("Auto-generated:")


def test_pattern_is_flagged_only_after_the_request_row_exists(sb):
    writes = _run(sb)
    kinds = [(t, op) for t, op, _, _ in writes]
    assert ("signal_topic_requests", "insert") in kinds
    assert ("provider_denial_patterns", "update") in kinds
    assert kinds.index(("signal_topic_requests", "insert")) < kinds.index(("provider_denial_patterns", "update"))
    flag = [w for w in writes if w[0] == "provider_denial_patterns" and w[1] == "update"][0]
    assert flag[2] == {"topic_request_created": True} and ("id", "pat-1") in flag[3]
