"""Money spent by a run that dies partway must still be recorded.

On 2026-08-31 the email gate died mid-run:

    [ERROR] source:P-VERIFY poster: Your credit balance is too low to access
    the Anthropic API.

Eleven source calls had already succeeded and been billed. The ledger wrote
once, at the end, inside the report-writing branch -- which that run never
reached. The money was spent and the ledger recorded NONE of it.

A ledger that only records runs that finish is a ledger of what was spent
successfully. That is the figure least likely to matter when someone is asking
why the bill is high: a run that fails partway is exactly the run whose cost is
invisible and exactly the run that gets retried.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "fc_ledger_timing", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
fc = importlib.util.module_from_spec(spec)
sys.modules["fc_ledger_timing"] = fc
spec.loader.exec_module(fc)


def _response(model="claude-sonnet-4-6", inp=100_000, out=5_000, searches=3):
    usage = types.SimpleNamespace(
        input_tokens=inp, output_tokens=out,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
        server_tool_use=types.SimpleNamespace(web_search_requests=searches))
    return types.SimpleNamespace(model=model, usage=usage)


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(fc._spend, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(fc, "USAGE", [])
    monkeypatch.setattr(fc, "_LEDGER_ISSUE", "testissue")
    return tmp_path / "ledger.jsonl"


def rows(ledger):
    if not ledger.exists():
        return []
    return [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]


def test_a_call_is_recorded_at_the_moment_it_returns(ledger):
    fc._record_usage("source:HARMONIA", _response())
    assert len(rows(ledger)) == 1
    assert rows(ledger)[0]["role"] == "source:HARMONIA"
    assert rows(ledger)[0]["issue"] == "testissue"


def test_calls_before_a_failure_survive_the_failure(ledger):
    """The 31 August email gate, reproduced: some calls land, then the API
    refuses, then the run exits without writing a report."""
    for i in range(11):
        fc._record_usage("source:%d" % i, _response())
    # ... and now the credit balance runs out and nothing further happens.
    assert len(rows(ledger)) == 11
    assert sum(r["usd"] for r in rows(ledger)) > 0


def test_it_is_priced_the_same_way_the_report_prices_it(ledger):
    """One place knows how to turn tokens into dollars.

    The first draft of _ledger_now multiplied per-MILLION rates by raw token
    counts and would have recorded a $0.30 call as $300,000 -- tripping the
    spend cap on the first API response of every run.
    """
    fc._record_usage("inference", _response())
    assert rows(ledger)[0]["usd"] == pytest.approx(
        fc.usage_summary()["total"]["usd"])


def test_nothing_is_recorded_twice(ledger):
    """The other way this went wrong: save() ran twice and turned $5.20 into
    $10.39. A ledger that overcounts is not the safe direction -- it would trip
    a $40 cap at real spend of $20 and stop work for a reason that is not true.
    """
    fc._record_usage("extract", _response())
    fc._record_usage("advocate", _response())
    assert len(rows(ledger)) == 2
    assert [r["role"] for r in rows(ledger)] == ["extract", "advocate"]


def test_an_unpriced_model_records_the_call_and_says_so(ledger):
    fc._record_usage("extract", _response(model="claude-something-unreleased"))
    r = rows(ledger)[0]
    assert r["usd"] == 0.0
    assert "not in the price table" in r["note"]
    assert r["input"] == 100_000            # the tokens are still on the record


def test_bookkeeping_never_breaks_a_run(ledger, monkeypatch):
    """record() is best-effort by contract. A broken ledger must not stop a
    gate: the check is what protects the reader, the accounting is not."""
    def boom(**_kw):
        raise RuntimeError("disk full")
    monkeypatch.setattr(fc._spend, "record", boom)
    fc._record_usage("extract", _response())      # must not raise
    assert fc.USAGE and fc.USAGE[0]["label"] == "extract"
