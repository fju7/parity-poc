"""Check-an-answer pilot v7 (study/whu-reliability/check_pilot/pipeline_v7.py), offline.

v7 = v6 with the window reads on claude-sonnet-5-5 and every first call over a window in flight together. A scripted
judge stands in for the model (v6's test judge); token counts are len // 4. No model call."""
import json
import sys
import threading
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_v6 as P6  # noqa: E402
import pipeline_v7 as P7  # noqa: E402
import run_pilot_v7 as R7  # noqa: E402
from test_whu_check_pilot_v6 import BatchJudge, count, long_text, small, target  # noqa: E402,F401

SUPPORT = "the aquifer recharge doubled after the levee works"


def run(targets, judge, **kw):
    return P7.windowed_read(targets, {}, Path("/nonexistent"), judge, count, **kw)


def models_of(judge_cls):
    seen = []

    class Recording(judge_cls):
        def create(self, **kw):
            seen.append(kw["model"])
            return super().create(**kw)
    return Recording, seen


def test_window_calls_name_sonnet_and_the_study_judge_stays_opus(small):
    Recording, seen = models_of(BatchJudge)
    rows, log, _layout, _secs = run([target(1, "claim one", long_text())], Recording(lambda w, c, n: {
        "label": "Absent", "span": "", "reason": "not there"}))
    assert seen and set(seen) == {"claude-sonnet-5-5"}
    assert {j["model"] for j in log if j["kind"] == "window"} == {"claude-sonnet-5-5"}
    assert P7.J.CLAUDE_MODEL == "claude-opus-5-5"            # stage 1 and v5's re-reads are untouched


def test_window_worst_case_is_priced_at_sonnet(small):
    jobs, _ = P7.plan_windows([target(1, "c", long_text())], {}, Path("/nonexistent"), count)
    w = [j for j in jobs if j["kind"] == "window"]
    assert w and all(abs(j["worst"] - P7.worst_cost(j["n_in"])) < 1e-12 for j in w)
    assert all(P7.worst_cost(j["n_in"]) < P6.worst_cost(j["n_in"]) for j in w)


def test_every_first_window_call_is_in_flight_together_even_past_eight(small):
    """Nine windows' first calls must all be inside create() at once (v6's 8 workers could not pass this)."""
    targets = [target(i, "claim %d" % i, ("Report %d.\n\n" % i) + long_text(140), sid="S%d" % i,
                      url="https://example.org/r%d" % i) for i in range(1, 6)]
    jobs, _ = P7.plan_windows(targets, {}, Path("/nonexistent"), count)
    n = len({j["prefix"] for j in jobs})
    assert n > 8, "the fixture must make more windows than v6's 8 workers (made %d)" % n
    barrier, seen, lock = threading.Barrier(n, timeout=5), [], threading.Lock()

    class Together(BatchJudge):
        def create(self, **kw):
            with lock:
                seen.append(1)
                first_wave = len(seen) <= n                    # the first n calls are the n windows' first calls
            if first_wave:
                barrier.wait()                                 # BrokenBarrierError unless all n are in flight
            return super().create(**kw)
    rows, log, _l, _s = run(targets, Together(lambda w, c, k: {"label": "Absent", "span": "", "reason": "x"}))
    assert not any(j["failures"] for j in log)


def test_a_failed_window_gives_couldnt_check_never_not_backed(small):
    judge = BatchJudge(lambda w, c, n: {"label": "Absent", "span": "", "reason": "no"},
                       fail_on=lambda extent: "part 2 of" in extent)
    rows, log, _l, _s = run([target(1, "claim one", long_text())], judge)
    assert rows[0]["label"] == P7.COULDNT and rows[0]["reason_kind"] == P6.R_WINDOW
    assert any(j["failures"] for j in log)


def test_each_window_call_records_its_start_and_end(small):
    rows, log, _l, secs = run([target(1, "claim one", long_text())],
                              BatchJudge(lambda w, c, n: {"label": "Absent", "span": "", "reason": "no"}))
    assert log and all(0 <= j["start"] <= j["end"] <= secs + 0.1 for j in log)


def test_likely_over_the_cap_calls_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(R7, "OUT", tmp_path)
    (tmp_path / "estimate.json").write_text(json.dumps({"at": "t", "likely_usd": 7.0, "worst_usd": 30.0}))
    monkeypatch.setattr(R7, "spent", lambda entries=None: 2.0)
    monkeypatch.setattr(R7, "clients", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a client was made")))
    a = types.SimpleNamespace(cap=8.0, vp_planned=0.0, no_call_after=None)
    assert R7.do_run(a) == 5
    assert "nothing was called" in capsys.readouterr().out


def test_worst_over_the_cap_alone_does_not_stop_the_gate():
    assert R7.gate(likely=6.0, spent_usd=0.0, cap=8.0)[0] is True        # worst ($30) is not the gate's figure
    assert R7.gate(likely=6.0, spent_usd=2.5, cap=8.0)[0] is False


def test_targets_must_match_v6s_windowed_rows(monkeypatch):
    monkeypatch.setattr(R7.R6, "recorded", lambda q, s: ({"results": [], "found": 1}, {"results": []}))
    monkeypatch.setattr(R7.R6, "held", lambda q, s: {})
    monkeypatch.setattr(R7.V6, "plan_v6", lambda s1, man, work, count: [{"idx": 3, "windowed": True}])
    monkeypatch.setattr(R7, "v6_result", lambda q, s: {"results": [{"idx": 4, "decided_by": P6.WINDOWED}],
                                                       "jobs": []})
    with pytest.raises(P7.Stop, match="not v6's windowed rows"):
        R7.plan_answer("WHU-Q1-01", "Claude", count)


def test_a_blind_spend_counter_fails_the_run():
    lines = [{"role": R7.ROLE, "issue": "whu-check-pilot-v6", "usd": 0.4}]
    assert R7.counter_blind(0.0, lines)
    assert R7.counter_blind(0.4, lines) is None


def test_the_runner_meters_on_its_own_issue_and_role(monkeypatch):
    got = {}
    monkeypatch.setattr(R7.S, "metered", lambda raw, **kw: got.update(kw) or raw)
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=lambda **k: object()))
    monkeypatch.setattr(R7.J, "env_keys", lambda: {"ANTHROPIC_API_KEY": "x"})
    R7.clients()
    assert got["issue"] == "whu-check-pilot-v7" and got["role"] == "check-pilot-v7"


def test_likely_is_v6s_window_cost_at_sonnets_prices():
    assert R7.PRICE_RATIO == pytest.approx(0.5)


def test_the_preview_stays_on_v2():
    text = (ROOT / "backend" / "routers" / "whu_check.py").read_text()
    assert "pipeline_v7" not in text and "pipeline_v6" not in text
