"""The budget for gating one issue, and the flag that used to get round it.

Run:  python3 -m pytest backend/tests/test_gate_budget.py

No API calls. Every case drives cycle_check against a scratch runs file.

WHY THIS EXISTS
The control that decides whether a gate run happens — the only thing standing
between a draft and unbounded spend — had no test of any kind. It had a cap of
two runs per cycle, an override that required a written reason (--past-cap),
and a second override that required nothing and DELETED the run history
(--new-cycle).

Issue one is what that produced: its runs file read "cycle 5, runs: []" while
the spend ledger showed seven gate runs in thirty hours for $30.53. Both extra
cycles were opened by the assistant. One followed a real outside review; the
other was a one-sentence re-read that the cap would have stopped.

Given a priced override and a free one, the free one gets used. So the history
now survives a new cycle, and the budget is counted over the life of the issue:
two runs, the outside review, one run to close it.
"""
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "fc", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)


@pytest.fixture()
def report(tmp_path):
    return str(tmp_path / "draft.gate.json")


def run(report, n=1, past=None, new=False):
    """Attempt n runs; return how many were allowed."""
    done = 0
    for i in range(n):
        if not fc.cycle_check(report, past, new):
            break
        fc.cycle_record(report, "sha%d" % i, past)
        done += 1
        new = False          # a cycle opens once
    return done


def test_two_runs_are_allowed_in_a_cycle(report):
    assert run(report, 3) == 2


def test_a_new_cycle_keeps_the_runs_it_used_to_delete(report):
    """The whole defect, as one assertion.

    --new-cycle wrote {"runs": []} over the record, so nothing anywhere knew
    how many times a draft had been gated. The counter it reset was the only
    counter there was.
    """
    run(report, 2)
    assert fc.cycle_check(report, None, True) is True
    st = fc.cycle_state(report)
    assert st["runs"] == []
    assert len(st["closed"]) == 2
    assert len(fc.all_runs(st)) == 2


def test_the_budget_is_three_over_the_life_of_the_issue(report):
    """Two runs, the outside review, one run to close it."""
    assert run(report, 2) == 2
    assert run(report, 1, new=True) == 1
    assert fc.cycle_check(report, None, False) is False


def test_a_new_cycle_cannot_buy_a_fourth_run(report):
    """The point. Opening a cycle is not how you get more runs."""
    run(report, 2)
    run(report, 1, new=True)
    assert fc.cycle_check(report, None, True) is False
    assert len(fc.all_runs(fc.cycle_state(report))) == 3


def test_a_written_reason_still_gets_past_it(report):
    """A rule with no override gets worked around. This one costs a sentence.

    The override that survives is the one that puts a reason on the record,
    not the one that quietly resets a counter.
    """
    run(report, 2)
    run(report, 1, new=True)
    assert fc.cycle_check(report, "the review found X and a run settles it",
                          False) is True


def test_the_override_is_recorded_against_the_run(report):
    run(report, 2)
    run(report, 1, past="because I said so")
    st = fc.cycle_state(report)
    assert any(r.get("past_cap") for r in fc.all_runs(st))


def test_a_draft_with_no_report_path_is_not_counted(report):
    """--report is what identifies a draft across runs. Without it there is
    nothing to count against, and the caller is told nothing is being counted
    rather than being silently allowed forever."""
    assert fc.cycle_check("", None, False) is True


# ---------------------------------------------------------------------------
# --past-issue-cap (2026-10-19): the issue budget's own override, on the ledger
# ---------------------------------------------------------------------------

class _Ledger:
    def __init__(self):
        self.lines = []

    def record(self, **kw):
        self.lines.append(kw)


def _spent(report, monkeypatch):
    led = _Ledger()
    monkeypatch.setattr(fc, "_spend", led)
    run(report, 2)
    run(report, 1, new=True)          # three runs: the whole budget
    return led


def test_the_issue_budget_stops_a_fourth_run(report, monkeypatch):
    _spent(report, monkeypatch)
    assert fc.cycle_check(report, None, False) is False


def test_past_issue_cap_lifts_the_issue_budget_and_writes_the_ledger(report, monkeypatch):
    led = _spent(report, monkeypatch)
    assert fc.cycle_check(report, None, False,
                          past_issue_cap="page changed after gate run 3") is True
    over = [l for l in led.lines if l.get("role") == "override"]
    assert len(over) == 1
    assert over[0]["usd"] == 0.0 and over[0]["script"] == "factcheck_draft.py"
    assert "RUNS_PER_ISSUE=%d" % fc.RUNS_PER_ISSUE in over[0]["note"]
    assert "page changed after gate run 3" in over[0]["note"]
    assert over[0]["issue"] == "draft"


def test_past_issue_cap_with_a_blank_reason_is_refused(report, monkeypatch):
    _spent(report, monkeypatch)
    assert fc.cycle_check(report, None, False, past_issue_cap="   ") is False
    with pytest.raises(Exception):
        fc._reason("  ")
    with pytest.raises(Exception):
        fc._reason("ok")
    assert fc._reason(" page changed after gate run 3 ") == "page changed after gate run 3"


def test_the_cli_refuses_the_flag_without_a_reason(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["factcheck_draft.py", "x.html", "--past-issue-cap", ""])
    with pytest.raises(SystemExit) as e:
        fc.main()
    assert e.value.code == 2


def test_past_issue_cap_does_not_lift_the_per_cycle_cap(report, monkeypatch):
    monkeypatch.setattr(fc, "_spend", _Ledger())
    run(report, 2)
    assert fc.cycle_check(report, None, False, past_issue_cap="a reason for it") is False


def test_the_older_past_cap_route_past_the_issue_budget_is_now_on_the_ledger(report, monkeypatch):
    led = _spent(report, monkeypatch)
    assert fc.cycle_check(report, "the review found X and a run settles it", False) is True
    assert [l for l in led.lines if l.get("role") == "override"]


def test_the_run_records_the_issue_override(report, monkeypatch):
    _spent(report, monkeypatch)
    fc.cycle_record(report, "sha9", None, "page changed after gate run 3")
    st = fc.cycle_state(report)
    assert fc.all_runs(st)[-1]["past_issue_cap"] == "page changed after gate run 3"
