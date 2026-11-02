"""The judging day cap (advisor ruling 2026-10-23): judge_m1.py and judge_m2.py
check caps.json "study_judging_per_day" ($50; $150 from 2026-10-24, operator), summed over the judging ledger
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


# The WHU day cap's documented schedule (caps.json "_default_per_day_raise",
# Fred 2026-10-30): 60 for the validity phase, back to 25 when the phase ends
# or at 2026-11-30T23:59Z, whichever is first. The phase end is not machine-
# readable, so before the deadline either value is legitimate; after it only
# 25 is. Moving the deadline means editing caps.json AND this constant.
DAY_CAP_RAISED, DAY_CAP_NORMAL = 60, 25
DAY_CAP_RAISE_ENDS = datetime(2026, 11, 30, 23, 59, tzinfo=timezone.utc)


def _caps():
    return json.loads((ROOT / "backend" / "data" / "spend" / "caps.json").read_text())


def test_the_judging_cap_is_150_dollars_in_caps_json_apart_from_the_whu_day_cap():
    assert _caps()["study_judging_per_day"] == 150


def day_cap_problem(c, now):
    """None if caps.json's day cap matches its documented schedule at `now`."""
    v, note = c.get("default_per_day"), c.get("_default_per_day_raise", "")
    if v == DAY_CAP_NORMAL:
        return None
    if v == DAY_CAP_RAISED:
        if now > DAY_CAP_RAISE_ENDS:
            return "default_per_day is still %s after %s; it should be back to %s" % (
                v, DAY_CAP_RAISE_ENDS.isoformat(), DAY_CAP_NORMAL)
        if "2026-11-30T23:59Z" not in note:
            return "default_per_day is %s but the raise note no longer documents the 2026-11-30T23:59Z end" % v
        return None
    return "default_per_day is %r: not %s (normal) or %s (validity-phase raise)" % (v, DAY_CAP_NORMAL, DAY_CAP_RAISED)


def test_the_whu_day_cap_follows_its_documented_schedule():
    assert day_cap_problem(_caps(), datetime.now(timezone.utc)) is None


def test_the_day_cap_schedule_itself():
    note = {"_default_per_day_raise": "... back to 25 when the phase ends or at 2026-11-30T23:59Z ..."}
    before, after = datetime(2026, 11, 2, tzinfo=timezone.utc), datetime(2026, 12, 1, tzinfo=timezone.utc)
    assert day_cap_problem({"default_per_day": 60, **note}, before) is None
    assert day_cap_problem({"default_per_day": 25}, before) is None          # phase ended early
    assert day_cap_problem({"default_per_day": 25}, after) is None
    assert "still 60" in day_cap_problem({"default_per_day": 60, **note}, after)
    assert "no longer documents" in day_cap_problem({"default_per_day": 60}, before)
    for bad in (40, 100, None):
        assert "not 25 (normal) or 60" in day_cap_problem({"default_per_day": bad, **note}, before)


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


class _R:
    def __init__(self, code, body=None, headers=None):
        self.status_code, self._b, self.headers = code, body or {}, headers or {}

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %d" % self.status_code)


def test_a_rate_limit_is_waited_out_but_a_quota_error_is_not(monkeypatch):
    seq = [_R(429, {"error": {"code": "rate_limit_exceeded"}}, {"retry-after": "5"}), _R(200)]
    waits = []
    monkeypatch.setattr(J1.httpx, "post", lambda *a, **k: seq.pop(0))
    assert J1.post_openai({}, "k", sleep=waits.append).status_code == 200 and waits == [30.0]
    import pytest
    for code in ("insufficient_quota", "credit_balance_exhausted"):
        monkeypatch.setattr(J1.httpx, "post", lambda *a, _c=code, **k: _R(429, {"error": {"code": _c}}))
        waits.clear()
        with pytest.raises(J1.OutOfCredit):
            J1.post_openai({}, "k", sleep=waits.append)
        assert waits == []
