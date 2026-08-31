"""The ledger has to count, and the cap has to stop.

Both were built on 2026-08-31 after "what has this issue cost" turned out to
have no answer: fifteen scripts made priced calls, one recorded anything, and
that one wrote into a file the next run overwrote. The cap then spent an hour
as a number printed on a board with nothing enforcing it, which is what the
previous cap ("two gate runs") had been.
"""
import importlib.util
import json
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "spend_ledger", ROOT / "backend" / "scripts" / "spend_ledger.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(sl, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(sl, "CAPS", tmp_path / "caps.json")
    return tmp_path


def set_caps(ledger, **kw):
    (ledger / "caps.json").write_text(json.dumps(kw), encoding="utf-8")


class FakeUsage:
    input_tokens, output_tokens = 10_000, 2_000
    cache_creation_input_tokens = cache_read_input_tokens = 0
    server_tool_use = types.SimpleNamespace(web_search_requests=3)


class FakeClient:
    class messages:
        @staticmethod
        def create(**kw):
            return types.SimpleNamespace(model="claude-sonnet-4-6", usage=FakeUsage())


def test_price_matches_the_published_table(ledger):
    usd, counts = sl.price("claude-sonnet-4-6", FakeUsage())
    # 10000 in @ $3/M + 2000 out @ $15/M + 3 searches @ $10/1000
    assert usd == pytest.approx(0.03 + 0.03 + 0.03)
    assert counts["web_searches"] == 3


def test_unknown_model_costs_none_rather_than_a_guess(ledger):
    usd, counts = sl.price("some-model-we-do-not-price", FakeUsage())
    assert usd is None
    assert counts["input"] == 10_000


def test_wrapping_the_client_meters_every_call(ledger):
    """Wrapping the CLIENT, not the call site: a call added later is metered
    without anyone remembering to meter it."""
    c = sl.metered(FakeClient(), script="t.py", issue="iss")
    c.messages.create(model="claude-sonnet-4-6")
    c.messages.create(model="claude-sonnet-4-6")
    assert sl.spent(issue="iss") == pytest.approx(0.18)


def test_per_issue_cap_stops_the_run(ledger):
    set_caps(ledger, default_per_issue=0.10)
    sl.record(script="t.py", issue="iss", usd=0.09)
    sl.check_cap("iss", about_to_spend=0.005)          # still under
    with pytest.raises(sl.OverCap) as e:
        sl.check_cap("iss", about_to_spend=0.50)
    assert "0.10" in str(e.value)


def test_day_cap_catches_what_the_issue_cap_cannot(ledger):
    """Signal work carries no issue, so a per-issue cap is blind to it."""
    set_caps(ledger, default_per_issue=100, default_per_day=0.10)
    sl.record(script="golden_set.py", issue="", usd=0.09)
    with pytest.raises(sl.OverCap) as e:
        sl.check_cap("anything", about_to_spend=0.50)
    assert "daily cap" in str(e.value)


def test_override_is_allowed_and_recorded(ledger, monkeypatch):
    set_caps(ledger, default_per_issue=0.01)
    sl.record(script="t.py", issue="iss", usd=1.00)
    monkeypatch.setenv("WHU_SPEND_OVERRIDE", "because I said so")
    sl.check_cap("iss", about_to_spend=5.0)            # allowed
    overrides = [e for e in sl.entries() if e.get("role") == "override"]
    assert overrides and "because I said so" in overrides[-1]["note"]


def test_recording_never_raises(ledger, monkeypatch):
    """Accounting must not be able to break a run it is only observing."""
    monkeypatch.setattr(sl, "LEDGER", Path("/nonexistent/dir/x.jsonl"))
    sl.record(script="t.py", usd=1.0)                  # must not raise


def test_the_two_price_tables_agree():
    """factcheck_draft keeps its own copy. Copies drift; this notices.

    Not merged into one, because the gate's table carries a comment about when
    the prices were read and why a missing model is left unpriced. Two tables
    with a test between them is honest; two tables with nothing between them is
    how they diverge.
    """
    src = (ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py").read_text()
    ns: dict = {}
    import ast
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in (
                "PRICES", "WEB_SEARCH_PER_1000"):
            ns[node.targets[0].id] = ast.literal_eval(node.value)
    assert ns.get("PRICES") == sl.PRICES, "the gate's price table has drifted from the ledger's"
    assert ns.get("WEB_SEARCH_PER_1000") == sl.WEB_SEARCH_PER_1000
