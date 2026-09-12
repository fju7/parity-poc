"""The `evidence 'as of'` row makes the modest promise and no other.

Operator ruling, 12 September 2026
(issues/WHU-003-deskilling/review/2026-09-12-modest-promise-ruling.md):
the as-of date is the date the claims were last checked against the record.
It is a bound. It is never compared to today. Until that day the row was green
only when the date equalled TODAY, so every publish day nudged the evidence
date forward whether or not anyone had re-read anything -- a currency claim
the publication does not make.

The must-not-regress case is the one the ruling turns on: an as-of date well
in the past, on a publish day, is OK.
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

spec = importlib.util.spec_from_file_location("whu_publish_asof", WHU / "publish.py")
P = importlib.util.module_from_spec(spec)
sys.modules["whu_publish_asof"] = P
spec.loader.exec_module(P)

ROW = "evidence 'as of'"


def test_a_date_well_in_the_past_on_a_publish_day_is_ok():
    label, state, detail = P.as_of_row("2 September 2026", date(2026, 9, 1), date(2026, 12, 25))
    assert (label, state) == (ROW, P.OK)
    assert "not compared to today" in detail


def test_the_row_is_not_forced_green_by_today_and_not_forced_amber_by_age():
    """Same page, same record, three different todays: the verdict does not move."""
    verdicts = {P.as_of_row("2 September 2026", date(2026, 9, 1), d)[1]
                for d in (date(2026, 9, 2), date(2026, 9, 12), date(2027, 3, 1))}
    assert verdicts == {P.OK}


def test_no_as_of_date_is_bad():
    assert P.as_of_row("", None, date(2026, 9, 12))[1] == P.BAD


def test_a_future_date_is_bad():
    _, state, detail = P.as_of_row("2 September 2027", None, date(2026, 9, 12))
    assert state == P.BAD and "future" in detail


def test_an_evidence_check_newer_than_the_date_warns_and_says_why():
    _, state, detail = P.as_of_row("2 September 2026", date(2026, 9, 12), date(2026, 9, 12))
    assert state == P.WARN
    assert "looked at since" in detail and "12 September 2026" in detail


def test_a_check_on_the_same_day_or_earlier_is_ok():
    assert P.as_of_row("12 September 2026", date(2026, 9, 12), date(2026, 9, 12))[1] == P.OK
    assert P.as_of_row("12 September 2026", date(2026, 9, 11), date(2026, 9, 12))[1] == P.OK


def test_no_recorded_check_is_ok_not_warn():
    """Class 3 -- nothing has checked this yet -- does not block and does not
    warn here; the date stands as the bound it states."""
    _, state, detail = P.as_of_row("2 September 2026", None, date(2026, 9, 12))
    assert state == P.OK and "no evidence check is recorded" in detail


def test_the_newest_check_is_read_from_the_issue_sweeps(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(P, "case_dir", lambda slug: tmp_path)
    assert P.newest_evidence_check("x") is None
    (tmp_path / "sweeps.json").write_text(json.dumps({"runs": [
        {"on": "2026-09-11", "command": "citations"},
        {"on": "2026-09-12", "command": "registry"},
        {"on": "not a date", "command": "status"}]}), encoding="utf-8")
    assert P.newest_evidence_check("x") == date(2026, 9, 12)
