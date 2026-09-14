"""An unpriced model is an ERROR, not a zero.

Run:  cd backend && python3 -m pytest tests/test_unpriced_model.py -q

WHY THIS EXISTS
PRICES (factcheck_draft.py and spend_ledger.py, held equal by a test) lists
two models. Until 2026-09-14, a call under any other model was recorded at
usd 0.0 with a note, spent() summed zero, and every cap in the system silently
stopped working the moment signal_model.MODEL resolved elsewhere. Unknown cost
is NOT ESTABLISHED -- the opposite of nothing. Three guards, three tests each
way: the call refuses before spending; a response under an unpriced model is
written as usd null and the run stops; check_cap refuses while any null line
exists in its scope. Nothing here touches the network or the real ledger.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

_sp = importlib.util.spec_from_file_location("sl_unpriced", ROOT / "backend" / "scripts" / "spend_ledger.py")
sl = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(sl)
_fp = importlib.util.spec_from_file_location("fc_unpriced", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
fc = importlib.util.module_from_spec(_fp); _fp.loader.exec_module(fc)

PRICED = next(iter(sl.PRICES))
UNPRICED = "claude-not-in-the-table-9"


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    p = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(sl, "LEDGER", p)
    if fc._spend is not None:
        monkeypatch.setattr(fc._spend, "LEDGER", p)
    monkeypatch.setattr(sl, "caps", lambda: {"default_per_issue": 40, "default_per_day": 25})
    if fc._spend is not None:
        monkeypatch.setattr(fc._spend, "caps", lambda: {"default_per_issue": 40, "default_per_day": 25})
    return p


def _lines(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _usage(inp=1000, out=10):
    return types.SimpleNamespace(input_tokens=inp, output_tokens=out,
                                 cache_creation_input_tokens=0, cache_read_input_tokens=0,
                                 server_tool_use=None)


def _response(model, text='{"ok": true}'):
    return types.SimpleNamespace(model=model, usage=_usage(), stop_reason="end_turn",
                                 content=[types.SimpleNamespace(type="text", text=text)])


# --- the ledger never writes 0.0 for an unknown price -------------------------------

def test_record_writes_null_not_zero_when_cost_is_not_established(ledger):
    sl.record(script="t", role="r", issue="melanoma", usd=None, input_tokens=5, note="x")
    assert _lines(ledger)[-1]["usd"] is None
    sl.record(script="t", role="r", issue="melanoma", usd=0.0)
    assert _lines(ledger)[-1]["usd"] == 0.0


def test_check_cap_refuses_while_an_unpriced_line_exists(ledger):
    sl.record(script="t", role="r", issue="melanoma", usd=0.01)
    sl.check_cap("melanoma", 0.5)                                   # fine
    sl.record(script="t", role="r", issue="melanoma", usd=None, note="UNPRICED")
    with pytest.raises(sl.UnpricedModel):
        sl.check_cap("melanoma", 0.5)
    with pytest.raises(sl.UnpricedModel):
        sl.check_cap("cdk46", 0.5)                                  # the DAY cap sees it too
    assert sl.unpriced(issue="melanoma") and not sl.unpriced(issue="deskilling")


# --- the metered client (every Signal pipeline script) ------------------------------

def test_metered_refuses_an_unpriced_model_before_spending(ledger):
    calls = []
    inner = types.SimpleNamespace(create=lambda **kw: calls.append(kw) or _response(PRICED))
    m = sl._MeteredMessages(inner, "score_claims.py", "glp1", "score")
    with pytest.raises(sl.UnpricedModel):
        m.create(model=UNPRICED, messages=[])
    assert calls == [] and _lines(ledger) == []


def test_metered_records_null_and_raises_when_the_response_is_unpriced(ledger):
    inner = types.SimpleNamespace(create=lambda **kw: _response(UNPRICED))
    m = sl._MeteredMessages(inner, "score_claims.py", "glp1", "score")
    with pytest.raises(sl.UnpricedModel):
        m.create(model=PRICED, messages=[])                         # alias resolved elsewhere
    line = _lines(ledger)[-1]
    assert line["usd"] is None and "UNPRICED" in line["note"] and line["input"] == 1000


def test_metered_prices_a_known_model(ledger):
    inner = types.SimpleNamespace(create=lambda **kw: _response(PRICED))
    m = sl._MeteredMessages(inner, "score_claims.py", "glp1", "score")
    m.create(model=PRICED, messages=[])
    assert _lines(ledger)[-1]["usd"] > 0


# --- the gate wrapper (every WHU call) ---------------------------------------------

def test_call_refuses_before_spending_when_the_configured_model_is_unpriced(ledger, monkeypatch):
    monkeypatch.setattr(fc, "SIGNAL_MODEL", UNPRICED)
    monkeypatch.setattr(fc, "_get_client", lambda: (_ for _ in ()).throw(AssertionError("client must not be built")))
    fc.enter_issue("melanoma")
    with pytest.raises(SystemExit) as e:
        fc.call("s", "u", search=False)
    assert "not in the price table" in str(e.value)
    assert _lines(ledger) == []


def test_call_records_null_and_stops_when_the_response_model_is_unpriced(ledger, monkeypatch):
    monkeypatch.setattr(fc, "SIGNAL_MODEL", PRICED)
    client = types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **kw: _response(UNPRICED)))
    monkeypatch.setattr(fc, "_get_client", lambda: client)
    fc.enter_issue("melanoma")
    with pytest.raises(SystemExit) as e:
        fc.call("s", "u", search=False, max_tokens=100)
    assert "not in the price table" in str(e.value)
    line = _lines(ledger)[-1]
    assert line["usd"] is None and "UNPRICED" in line["note"]
    assert line["input"] == 1000                                    # the spend itself is on the record


def test_call_prices_a_known_model_and_proceeds(ledger, monkeypatch):
    monkeypatch.setattr(fc, "SIGNAL_MODEL", PRICED)
    client = types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **kw: _response(PRICED)))
    monkeypatch.setattr(fc, "_get_client", lambda: client)
    fc.enter_issue("melanoma")
    assert fc.call("s", "u", search=False, max_tokens=100) == {"ok": True}
    assert _lines(ledger)[-1]["usd"] > 0


def test_the_cap_is_never_computed_from_a_zero_standing_in_for_unknown(ledger):
    """spent() must not be the thing that decides: with a null line present the
    cap refuses even though the arithmetic sum would pass. The line is dated
    YESTERDAY so the daily cap cannot see it -- only the per-issue guard can."""
    sl.record(script="t", role="r", issue="melanoma", usd=None, at="2026-01-01T00:00:00+00:00")
    assert sl.spent(issue="melanoma") == 0.0                        # the sum is meaningless...
    with pytest.raises(sl.UnpricedModel):
        sl.check_cap("melanoma", 0.01)                              # ...so it is not consulted
    sl.check_cap("cdk46", 0.01)                                     # another issue is unaffected


def test_an_old_unpriced_line_blocks_its_issue_only(ledger):
    sl.record(script="t", role="r", issue="melanoma", usd=None, at="2026-01-01T00:00:00+00:00")
    with pytest.raises(sl.UnpricedModel):
        sl.check_cap("melanoma", 0.01)
    sl.check_cap("deskilling", 0.01)
