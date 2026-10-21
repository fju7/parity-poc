"""A study issue's gate limit is ruling 2's three runs, and nothing else (2026-10-21).

Ruling 2 (advisor, 2026-10-20; study/whu-reliability/RUN.md step 4): at most
three gate runs per study issue. The per-cycle cap of two belongs to published
issues; WHU-P02's third run was refused by it. A fourth run is refused, with no
override on a study issue. Published issues are unchanged. No API calls; the
runs file is a scratch one.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "fc_study_runs_t", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)


class _Ledger:
    def __init__(self, study):
        self.study, self.lines = study, []

    def record(self, **kw):
        self.lines.append(kw)

    def is_study_issue(self, issue):
        return self.study


@pytest.fixture()
def report(tmp_path):
    return str(tmp_path / "ultra-processed-foods.html.gate.json")


def _set(monkeypatch, study):
    led = _Ledger(study)
    monkeypatch.setattr(fc, "_spend", led)
    return led


def _runs(report, n, **kw):
    done = 0
    for i in range(n):
        if not fc.cycle_check(report, kw.get("past"), False, past_issue_cap=kw.get("issue")):
            break
        fc.cycle_record(report, "sha%d" % i, kw.get("past"))
        done += 1
    return done


def test_a_study_issue_gets_three_runs_in_one_cycle(report, monkeypatch):
    _set(monkeypatch, True)
    assert fc.report_is_study(report) is True
    assert _runs(report, 5) == 3                             # no per-cycle cap of two
    assert fc.cycle_state(report)["cycle"] == 1


def test_a_fourth_run_is_refused_and_nothing_lifts_it(report, monkeypatch, capsys):
    led = _set(monkeypatch, True)
    _runs(report, 3)
    assert fc.cycle_check(report, None, False) is False
    assert fc.cycle_check(report, "the review found X and a run settles it", False) is False
    assert fc.cycle_check(report, None, False, past_issue_cap="a reason long enough") is False
    assert fc.cycle_check(report, None, True) is False       # a new cycle buys nothing either
    assert "ruling 2 allows 3" in capsys.readouterr().out
    assert led.lines == []                                   # no override recorded: none taken
    assert len(fc.all_runs(fc.cycle_state(report))) == 3


def test_a_new_cycle_on_a_study_issue_keeps_the_runs_and_the_count(report, monkeypatch):
    _set(monkeypatch, True)
    _runs(report, 2)
    assert fc.cycle_check(report, None, True) is True
    fc.cycle_record(report, "sha2", None)
    assert len(fc.all_runs(fc.cycle_state(report))) == 3
    assert fc.cycle_check(report, None, False) is False


def test_a_published_issue_is_unchanged(report, monkeypatch):
    _set(monkeypatch, False)
    assert _runs(report, 3) == 2                             # the per-cycle cap still applies
    assert fc.cycle_check(report, "the review found X and a run settles it", False) is True
    fc.cycle_record(report, "sha2", "the review found X and a run settles it")
    assert fc.cycle_check(report, None, False) is False      # the issue budget of three
    assert fc.cycle_check(report, "another reason given here", False) is True   # still liftable


def test_the_study_flag_is_read_from_the_issue(report, monkeypatch):
    asked = []
    led = _set(monkeypatch, True)
    led.is_study_issue = lambda issue: asked.append(issue) or True
    fc.cycle_check(report, None, False)
    assert asked and asked[0] == fc.issue_slug_for(report[:-len(".gate.json")])
