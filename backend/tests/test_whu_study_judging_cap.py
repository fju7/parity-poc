"""The judging day cap (advisor ruling 2026-10-23): judge_m1.py and judge_m2.py
check caps.json "study_judging_per_day" ($50), summed over the judging ledger
issues only, before every call, as well as the per-run cap. Offline."""
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SC = ROOT / "study" / "whu-reliability" / "scripts"
_spec = importlib.util.spec_from_file_location("judge_m1_cap_t", SC / "judge_m1.py")
J1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(J1)
NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


def _ledger(monkeypatch, rows, cap=50):
    monkeypatch.setattr(J1.S, "entries", lambda: rows)
    monkeypatch.setattr(J1.S, "caps", lambda: {} if cap is None else {"study_judging_per_day": cap,
                                                                        "default_per_day": 25})


def test_the_cap_is_fifty_dollars_in_caps_json_apart_from_the_whu_day_cap():
    c = json.loads((ROOT / "backend" / "data" / "spend" / "caps.json").read_text())
    assert c["study_judging_per_day"] == 50 and c["default_per_day"] == 25


def test_only_todays_judging_counts(monkeypatch):
    _ledger(monkeypatch, [
        {"issue": "whu-reliability-judging", "at": "2026-10-24T01:00:00+00:00", "usd": 30.0},
        {"issue": "whu-reliability-judging", "at": "2026-10-23T23:59:00+00:00", "usd": 40.0},   # yesterday
        {"issue": "city-growth-climate-coping", "at": "2026-10-24T02:00:00+00:00", "usd": 20.0},  # WHU, not judging
    ])
    assert J1.judging_today(NOW) == 30.0
    assert J1.day_cap_stop(19.9, NOW) is None
    assert "DAY CAP" in J1.day_cap_stop(20.1, NOW)


def test_it_fails_closed(monkeypatch):
    _ledger(monkeypatch, [], cap=None)
    assert "no 'study_judging_per_day'" in J1.day_cap_stop(0.01, NOW)
    _ledger(monkeypatch, [{"issue": "whu-reliability-judging", "at": "2026-10-24T01:00:00+00:00", "usd": None}])
    assert "no established cost" in J1.day_cap_stop(0.01, NOW)


def test_both_runners_check_it_before_the_per_run_cap():
    for f in ("judge_m1.py", "judge_m2.py"):
        src = (SC / f).read_text()
        assert src.index("day_cap_stop(worst)") < src.index("so_far + worst > a.cap"), f
