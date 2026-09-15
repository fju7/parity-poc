"""Offline tests for the billing contract SUCCESS path and the provider wrapper's
error path (shared assertion policy, Phase A.5 d/e).

WHY THIS EXISTS
---------------
From 2026-03-26 to 2026-09-15 billing_contracts.analyze_contract called
_call_claude(file_b64, "application/pdf", PROMPT) positionally into a
(system_prompt, user_content, max_tokens) signature. The wrapper swallowed the
resulting API error and returned None; the endpoint stored
{"extraction": None, "rates_extracted": 0} and returned 200. The existing
test file covered only the 401 paths, so nothing noticed for 173 days.

These tests run with no network: the Supabase client and the model wrapper
are stubbed, and the assertions are on WHAT THE ENDPOINT HANDS THE MODEL and
WHAT IT STORES, which is where the bug lived.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import routers.billing_contracts as bc  # noqa: E402
import routers.provider_shared as ps  # noqa: E402


# ---------------------------------------------------------------------------
# stubs
# ---------------------------------------------------------------------------

class _Q:
    """Minimal PostgREST chain: .select/.eq/.limit/.update/.is_ return self; .execute returns rows."""
    def __init__(self, rows, log):
        self._rows, self._log = rows, log
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def is_(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def order(self, *a, **k): return self
    def update(self, payload):
        self._log.append(payload); return self
    def execute(self):
        class R: data = self._rows
        return R()


class _SB:
    def __init__(self, rows):
        self.rows, self.updates = rows, []
    def table(self, name): return _Q(self.rows, self.updates)


CONTRACT = {
    "id": "c1", "billing_company_id": "bc1", "practice_id": "p1", "payer_name": "Aetna",
    "effective_date": "2025-01-01", "expiry_date": "2025-12-31",
    "storage_path": None, "file_content": "JVBERi0xLjQK",   # any base64
}


@pytest.fixture
def stubbed(monkeypatch):
    sb = _SB([CONTRACT])
    monkeypatch.setattr(bc, "_require_billing_contracts",
                        lambda auth: ({"email": "t@x"}, "bc1", "admin", "u1", sb))
    return sb


# ---------------------------------------------------------------------------
# (e) success path
# ---------------------------------------------------------------------------

def test_analyze_contract_hands_the_model_the_pdf_and_stores_the_rates(stubbed, monkeypatch):
    seen = {}
    def fake_call(**kwargs):
        seen.update(kwargs)
        return {"payer_name": "Aetna", "effective_date": "2025-01-01",
                "rates": [{"cpt": "99213", "rate": 95.5, "description": "Office visit"}]}
    monkeypatch.setattr(ps, "_call_claude", fake_call)

    out = asyncio.run(bc.analyze_contract("c1", authorization="Bearer x"))

    # The call is by keyword, in the wrapper's own vocabulary.
    assert seen["system_prompt"] == ps.FEE_SCHEDULE_EXTRACTION_PROMPT
    assert isinstance(seen["max_tokens"], int)
    blocks = seen["user_content"]
    assert blocks[0]["type"] == "document" and blocks[0]["source"]["media_type"] == "application/pdf"
    assert blocks[0]["source"]["data"] == CONTRACT["file_content"]
    # What is stored is the extraction, and the count is real.
    stored = stubbed.updates[-1]["analysis_result"]
    assert stored["extraction"]["rates"][0]["cpt"] == "99213"
    assert stored["rates_extracted"] == 1
    assert out["analysis"]["rates_extracted"] == 1 if "analysis" in out else True


def test_the_old_positional_call_can_no_longer_succeed_silently(monkeypatch):
    """The exact call shape that ran in production for 173 days now raises
    before any network call, naming the argument order."""
    monkeypatch.setattr(ps, "_get_claude", lambda: (_ for _ in ()).throw(AssertionError("must not reach the client")))
    with pytest.raises(ps.ClaudeCallError) as exc:
        ps._call_claude("JVBERi0xLjQK", "application/pdf", ps.FEE_SCHEDULE_EXTRACTION_PROMPT)
    assert "argument order" in str(exc.value)


def test_analyze_contract_model_failure_stores_nothing_and_is_a_502(stubbed, monkeypatch):
    def failing(**kwargs):
        raise ps.ClaudeCallError("API error: simulated 500")
    monkeypatch.setattr(ps, "_call_claude", failing)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        asyncio.run(bc.analyze_contract("c1", authorization="Bearer x"))
    assert exc.value.status_code == 502
    assert stubbed.updates == []          # nothing written


# ---------------------------------------------------------------------------
# (d) the wrapper raises; it never returns None and never wraps HTML as a letter
# ---------------------------------------------------------------------------

class _Client:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.messages = self
    def create(self, **kwargs):
        b = self.behaviour
        if isinstance(b, Exception):
            raise b
        class Block: text = b
        class Resp: content = [Block()]
        return Resp()


def test_wrapper_raises_on_api_error(monkeypatch):
    monkeypatch.setattr(ps, "_get_claude", lambda: _Client(RuntimeError("HTTP 500 from API")))
    with pytest.raises(ps.ClaudeCallError) as exc:
        ps._call_claude(system_prompt="s", user_content="u", max_tokens=10)
    assert "HTTP 500" in str(exc.value)


def test_wrapper_raises_on_non_json_and_does_not_wrap_html(monkeypatch):
    monkeypatch.setattr(ps, "_get_claude", lambda: _Client("<html><body>Dear Payer</body></html>"))
    with pytest.raises(ps.ClaudeCallError) as exc:
        ps._call_claude(system_prompt="s", user_content="u", max_tokens=10)
    assert "not JSON" in str(exc.value)


def test_wrapper_returns_parsed_json_on_success(monkeypatch):
    monkeypatch.setattr(ps, "_get_claude", lambda: _Client('```json\n{"rates": []}\n```'))
    assert ps._call_claude(system_prompt="s", user_content="u", max_tokens=10) == {"rates": []}
