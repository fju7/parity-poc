"""APPEALS-7 (2026-09-21): the Signal playbook enrichment is reachable through the endpoint.

The unit tests in test_appeals5.py call _attach_signal_evidence directly and passed for six
months while the caller was dead: analyze_denials extended its denial-code list with the
adjustment_codes STRING, so the playbook filter received ['C','O','-','5','0'] and matched
nothing (f9dc071, 2026-03-23). These tests go through POST /api/provider/analyze-denials with
the payload the frontend actually sends (ProviderApp.jsx:626 joins parse_835 codes with ", ";
:665 and :743 send that string as adjustment_codes) and a fake reader that HONOURS the .in_()
filter values -- so a character-split code list returns no row, exactly as PostgREST would.

Offline: auth, the model call, the anon reader and the background aggregation are stubbed at
the names provider_audit binds. The playbook row is the live (CO-50, 90707) row's shape.
"""
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers import provider_audit as PA  # noqa: E402
from routers.provider_shared import _AuthUser  # noqa: E402

# One published playbook row, keyed as the endpoint keys its lookup.
PLAYBOOK_ROWS = [{
    "id": "row-1",
    "denial_code": "CO-50",
    "cpt_code": "90707",
    "signal_topic_slug": "mmr-vaccine-autism",
    "signal_issue_id": "issue-1",
    "signal_claim_count_band": "3_plus_claims",
    "payer_analytical_path": "Payer likely weighted recency and rigor heavily.",
    "challenging_evidence_summary": "A 2019 Danish study tracked approximately 650,000 children.",
    "recommended_claims": "[]",
    "last_updated": "2026-09-21T00:00:00+00:00",
}]


class _Resp:
    def __init__(self, data):
        self.data = data


class _PlaybookQuery:
    """Applies .in_() filters to PLAYBOOK_ROWS the way PostgREST applies them: a value is
    matched only if it equals a member of the list. This is the property the old unit tests
    lacked -- they were handed already-matched rows."""

    def __init__(self, rows):
        self._rows = list(rows)
        self.filters = []          # recorded so a test can assert what the endpoint sent

    def select(self, *a, **k):
        return self

    def in_(self, column, values):
        self.filters.append((column, list(values)))
        self._rows = [r for r in self._rows if r.get(column) in values]
        return self

    def execute(self):
        return _Resp(self._rows)


class _FakeReader:
    def __init__(self):
        self.queries = []

    def table(self, name):
        assert name == "signal_denial_playbook", name
        q = _PlaybookQuery(PLAYBOOK_ROWS)
        self.queries.append(q)
        return q


def _model_result_for(codes):
    """What the model returns for these codes: one denial_type per code, no affected_cpts --
    attach_denial_totals fills those from the lines, in code."""
    return {"denial_types": [{"adjustment_code": c, "description": f"{c} denial"} for c in codes],
            "pattern_summary": "stub"}


@pytest.fixture
def harness(monkeypatch):
    reader = _FakeReader()
    monkeypatch.setattr(PA, "_get_authenticated_user",
                        lambda request: _AuthUser({"company_id": "c-1", "email": "t@example.com", "role": "admin"}))
    monkeypatch.setattr(PA, "signal_reader", lambda: reader)

    async def _no_aggregation(*a, **k):
        return None
    monkeypatch.setattr(PA, "aggregate_denial_patterns", _no_aggregation)

    app = FastAPI()
    app.include_router(PA.router, prefix="/api/provider")   # as routers/provider.py mounts it
    return TestClient(app), reader


def _post(client, adjustment_codes, cpt="90707"):
    # Shaped exactly as ProviderApp.jsx:743 builds it.
    return client.post("/api/provider/analyze-denials",
                       headers={"Authorization": "Bearer test"},
                       json={"payer_name": "Cigna",
                             "denied_lines": [{"cpt_code": cpt, "billed_amount": 120.0,
                                               "adjustment_codes": adjustment_codes,
                                               "claim_id": "CLM-1"}]})


def test_single_code_line_reaches_the_playbook_and_is_enriched(harness, monkeypatch):
    client, reader = harness
    monkeypatch.setattr(PA, "_call_claude", lambda **kw: _model_result_for(["CO-50"]))

    r = _post(client, "CO-50")
    assert r.status_code == 200, r.text
    dts = r.json()["denial_types"]
    assert dts and dts[0]["adjustment_code"] == "CO-50"
    assert dts[0]["affected_cpts"] == ["90707"]

    # The filter the endpoint sent must be whole codes, not characters.
    sent = dict(reader.queries[0].filters)
    assert sent["denial_code"] == ["CO-50"], sent["denial_code"]

    se = dts[0].get("signal_evidence")
    assert se is not None, "playbook row matched nothing: signal_evidence absent"
    assert se["signal_claim_count_band"] == "3_plus_claims"
    assert se["topic_slug"] == "mmr-vaccine-autism"


def test_multi_code_line_is_split_on_comma_and_stripped(harness, monkeypatch):
    """Production lines carry 'CO-45, CO-50' (59 of 224 provider_analyses line_items on
    2026-09-21): comma-joined with a space, the same format denial_totals parses."""
    client, reader = harness
    monkeypatch.setattr(PA, "_call_claude", lambda **kw: _model_result_for(["CO-45", "CO-50"]))

    r = _post(client, "CO-45, CO-50")
    assert r.status_code == 200, r.text
    sent = dict(reader.queries[0].filters)
    assert sorted(sent["denial_code"]) == ["CO-45", "CO-50"], sent["denial_code"]

    by_code = {dt["adjustment_code"]: dt for dt in r.json()["denial_types"]}
    assert "signal_evidence" in by_code["CO-50"]
    assert "signal_evidence" not in by_code["CO-45"]     # no playbook row for it


def test_unmatched_pair_is_not_enriched_and_does_not_error(harness, monkeypatch):
    client, reader = harness
    monkeypatch.setattr(PA, "_call_claude", lambda **kw: _model_result_for(["CO-97"]))
    r = _post(client, "CO-97", cpt="99213")
    assert r.status_code == 200
    assert "signal_evidence" not in r.json()["denial_types"][0]
