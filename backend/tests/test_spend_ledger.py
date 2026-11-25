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


# Ruling 3 (2026-11-23): a budget line in caps.json "lines" is summed over every ledger issue with its prefix.

def _rows(ledger, rows):
    with (ledger / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        for issue, usd in rows:
            fh.write(json.dumps({"at": "2026-11-23T00:00:00+00:00", "script": "t", "role": "", "issue": issue,
                                 "usd": usd}) + "\n")


def test_a_line_is_summed_across_its_issues(ledger, monkeypatch):
    monkeypatch.delenv("WHU_SPEND_OVERRIDE", raising=False)
    set_caps(ledger, default_per_issue=40, default_per_day=1000,
             lines={"seeded-defect test": {"cap_usd": 89, "ledger_issue_prefix": "whu-validity-sd-"}})
    _rows(ledger, [("whu-validity-sd-full", 50.0), ("whu-validity-sd-sonnet", 30.0), ("other", 500.0)])
    assert sl.line_spent("whu-validity-sd-")[0] == pytest.approx(80.0)
    sl.check_cap("whu-validity-sd-haiku", 9.0)                 # 89.00: at the cap, allowed
    with pytest.raises(sl.OverLineCap, match="seeded-defect test"):
        sl.check_cap("whu-validity-sd-haiku", 9.5)             # each issue is under $40; the line is not
    sl.check_cap("other-issue", 9.5)                           # an issue outside the line is untouched


def test_a_line_cap_is_not_lifted_by_the_override(ledger, monkeypatch):
    set_caps(ledger, default_per_issue=40, default_per_day=1000,
             lines={"t1": {"cap_usd": 20, "ledger_issue_prefix": "whu-lean-orch-t1-"}})
    _rows(ledger, [("whu-lean-orch-t1-q1-02", 19.0)])
    monkeypatch.setenv("WHU_SPEND_OVERRIDE", "a reason")
    with pytest.raises(sl.OverLineCap):
        sl.check_cap("whu-lean-orch-t1-q1-02j", 2.0)


def test_an_unpriced_row_makes_the_line_unsummable(ledger):
    set_caps(ledger, default_per_day=1000, lines={"x": {"cap_usd": 10, "ledger_issue_prefix": "whu-cf-"}})
    _rows(ledger, [("whu-cf-01", None)])
    with pytest.raises(sl.UnpricedModel):
        sl.check_cap("whu-cf-02", 0.1)


def test_the_committed_lines_hold_todays_spend():
    real = json.loads((ROOT / "backend/data/spend/caps.json").read_text())["lines"]
    assert real["seeded-defect test"] == {"cap_usd": 89, "ledger_issue_prefix": "whu-validity-sd-"}
    # moves between these two lines are by ruling (8 Nov, 23 Nov x3); together they were $160 ($10 lean runs + $150 Fred),
    # $170 since Fred approved +$10 on the trial line (2026-11-25, relayed by the advisor; deviations.md P108)
    assert real["orchestrator trial 1"]["cap_usd"] == 50 and real["new-questions test"]["cap_usd"] == 120
    assert real["orchestrator trial 1"]["cap_usd"] + real["new-questions test"]["cap_usd"] == 170
