"""Check-an-answer pilot v8 (study/whu-reliability/check_pilot/pipeline_v8.py), offline.

v8 = v6's Opus window reads + v7's concurrent window reads + planning without API token counts (a local estimate,
windows <= 140k estimated tokens, counts cached by hash). A scripted judge stands in for the model (v6's test judge);
no model call and no count_tokens call."""
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_v6 as P6  # noqa: E402
import pipeline_v8 as P8  # noqa: E402
from test_whu_check_pilot_v6 import BatchJudge, long_text, target  # noqa: E402

ABSENT = {"label": "Absent", "span": "", "reason": "not here"}


class NoCountJudge(BatchJudge):
    """v6's scripted judge; count_tokens must never be called; usage reports TRUE(prompt) input tokens."""

    def __init__(self, decide, fail_on=None, true=None):
        super().__init__(decide, fail_on)
        self.true, self.models = true, []

    def count_tokens(self, **_kw):
        raise AssertionError("count_tokens was called")

    def create(self, **kw):
        r = super().create(**kw)
        self.models.append(kw["model"])
        if self.true:
            prompt = "".join(b["text"] for b in kw["messages"][0]["content"])
            r.usage.input_tokens = self.true(prompt)
        return r


@pytest.fixture
def small(monkeypatch):
    """Windows of 1,200 estimated tokens with 400 overlap; a source over 1,200 estimated tokens is long."""
    monkeypatch.setattr(P8, "WINDOW_EST", 1200)
    monkeypatch.setattr(P6, "OVERLAP_TOKENS", 400)
    monkeypatch.setattr(P8.J, "MAX_SOURCE_TOKENS", 1200)


def big_text(chars):
    paras, i = [], 0
    while sum(len(p) + 2 for p in paras) < chars:
        paras.append("Paragraph %d: the %s survey in district %d logged %d readings and no change of note."
                     % (i, ("basin", "levee", "delta", "runoff")[i % 4], i, 100 + i))
        i += 1
    return "\n\n".join(paras)


def run(targets, judge, count=None, **kw):
    count = count or P8.LocalCount()
    return P8.windowed_read(targets, {}, Path("/nonexistent"), judge, count, **kw)


# -- the local count and its cache ---------------------------------------------------------------------------------

def test_the_local_count_overestimates_every_ratio_measured_on_the_pilot():
    for chars_per_token in (1.99, 2.33, 2.72, 2.80):                   # §15.3: the pilot's measured range
        text = "x" * 190_000
        assert P8.LocalCount.estimate(text) >= len(text) / chars_per_token


def test_a_cached_count_is_reused_in_process_and_from_the_file(tmp_path):
    path = tmp_path / "token_counts.json"
    c = P8.LocalCount(path)
    text = big_text(50_000)
    n = c(text)
    assert c(text) == n and c.computed == 1                            # reused, not recomputed
    c.save()
    c2 = P8.LocalCount(path)
    assert c2(text) == n and c2.computed == 0                          # a fresh process reads it from the file
    assert c2(text + " one more sentence.") != n and c2.computed == 1  # a changed text is not served a stale count
    assert all(k.startswith(P8.ESTIMATOR + ":") for k in json.loads(path.read_text()))


def test_a_cached_figure_is_the_one_used_even_if_the_estimator_would_say_otherwise(tmp_path):
    path = tmp_path / "token_counts.json"
    c = P8.LocalCount(path)
    text = "Paragraph 0: the basin survey."
    c(text)
    key = next(iter(c.cache))
    path.write_text(json.dumps({key: 12345}))
    assert P8.LocalCount(path)(text) == 12345


# -- planning and windows ------------------------------------------------------------------------------------------

def test_windows_are_at_most_140k_estimated_tokens_and_overlap_at_least_2k():
    text = big_text(700_000)                                           # ~368k estimated tokens
    count = P8.LocalCount()
    t = target(1, "a claim", text)
    t["full_docs"][0]["tokens"] = count(text)
    jobs, layout = P8.plan_windows([t], {}, Path("/nonexistent"), count)
    ws = layout["Slong"]["windows"]
    assert len(ws) >= 3 and ws[0][0] == 0 and ws[-1][1] == len(text)
    assert all(count(text[a:b]) <= P8.WINDOW_EST for a, b in ws)
    assert all(count(text[a2:b1]) >= P6.OVERLAP_TOKENS for (a1, b1), (a2, b2) in zip(ws, ws[1:]))


def test_no_count_tokens_call_in_planning_or_the_window_stage():
    text = big_text(700_000)
    judge = NoCountJudge(lambda w, c, n: ABSENT)
    rows, log, _l, _s = run([target(1, "a claim", text)], judge)       # count_tokens would raise
    assert log and not any(j["failures"] for j in log)
    src = (ROOT / "study" / "whu-reliability" / "check_pilot" / "pipeline_v8.py").read_text()
    assert "count_tokens_fn" not in src and ".count_tokens(" not in src


def test_window_calls_are_on_opus():
    judge = NoCountJudge(lambda w, c, n: ABSENT)
    t = target(1, "a claim", big_text(400_000))
    t["full_docs"][0]["tokens"] = P8.LocalCount()(t["full_docs"][0]["text"])
    _rows, log, _l, _s = run([t], judge)
    assert set(judge.models) == {P8.J.CLAUDE_MODEL} == {"claude-opus-5-5"}
    assert {j["model"] for j in log} == {"claude-opus-5-5"}


def test_an_underestimated_window_is_read_whole_gives_the_right_verdict_and_is_flagged():
    """Local estimate under 140k for the window; the true count (a text denser than 1.9 chars/token) over 150k."""
    text = big_text(560_000)
    count = P8.LocalCount()
    t = target(7, "District 3 logged 103 readings.", text)
    t["full_docs"][0]["tokens"] = count(text)
    jobs, layout = P8.plan_windows([t], {}, Path("/nonexistent"), count)
    a, b = layout["Slong"]["windows"][0]
    assert count(text[a:b]) <= 140_000 and len(text[a:b]) / 1.5 > 150_000     # under by estimate, over in truth
    support = "Paragraph 3: the runoff survey in district 3 logged 103 readings and no change of note."
    assert support in text[a:b]
    judge = NoCountJudge(lambda w, c, n: {"label": "Supported", "span": support, "reason": "says so"}
                         if support in w else ABSENT, true=lambda prompt: int(len(prompt) / 1.5))
    rows, log, _l, _s = run([t], judge, count=count, planned=(jobs, layout))
    assert rows[0]["label"] == P6.BACKED and rows[0]["passage"]["quote"]
    first = [j for j in log if j["range"] == [a, b]][0]
    assert first["over_limit"] and first["n_in_true"] > 150_000 and first["n_in_est"] <= 150_000
    assert any(c["prefix"].count(text[a:b]) == 1 and "part 1 of" in c["extent"] for c in judge.calls)  # uncut


def test_a_source_estimated_under_the_line_is_read_whole_not_windowed_and_a_large_call_is_flagged(monkeypatch):
    text = big_text(270_000)                                           # ~142k estimated: under 150k, not long
    count = P8.LocalCount()
    assert count(text) < P8.J.MAX_SOURCE_TOKENS
    short = {"source_id": "Smid", "url": "https://example.org/mid", "extent": "full text", "abstract_only": False,
             "tokens": count(text), "chunked": False, "text": text}
    t = target(1, "a claim", big_text(400_000), extra_docs=[short])
    t["full_docs"][0]["tokens"] = count(t["full_docs"][0]["text"])
    seen = {}

    def fake_plan(r, man, work, cnt):
        seen["citations"] = [c["url"] for c in r["citations"]]
        return {"prefix": "P", "worst": 0.01, "idx": r["idx"]}
    monkeypatch.setattr(P6.V5, "plan_reread", fake_plan)
    jobs, layout = P8.plan_windows([t], {}, Path("/nonexistent"), count)
    assert seen["citations"] == ["https://example.org/mid"] and "Smid" not in layout   # read whole, by v5's path
    inner = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(
        usage=SimpleNamespace(input_tokens=180_000, cache_creation_input_tokens=0, cache_read_input_tokens=0))))
    sized = P8.SizeLog(inner, count)
    sized.messages.create(model="claude-opus-5-5", messages=[{"role": "user", "content": [{"type": "text",
                                                                                           "text": text}]}])
    assert sized.calls[0]["over_limit"] and sized.calls[0]["est_input"] < 150_000


# -- concurrency and failures --------------------------------------------------------------------------------------

def test_every_first_window_call_is_in_flight_together(small):
    targets = [target(i, "claim %d" % i, ("Report %d.\n\n" % i) + long_text(140), sid="S%d" % i,
                      url="https://example.org/r%d" % i) for i in range(1, 6)]
    count = P8.LocalCount()
    jobs, layout = P8.plan_windows(targets, {}, Path("/nonexistent"), count)
    n = len({j["prefix"] for j in jobs})
    assert n > 8, "the fixture must make more windows than v6's 8 workers (made %d)" % n
    barrier, seen, lock = threading.Barrier(n, timeout=5), [], threading.Lock()

    class Together(NoCountJudge):
        def create(self, **kw):
            with lock:
                seen.append(1)
                first_wave = len(seen) <= n
            if first_wave:
                barrier.wait()
            return super().create(**kw)
    _rows, log, _l, _s = run(targets, Together(lambda w, c, k: ABSENT), count=count, planned=(jobs, layout))
    assert not any(j["failures"] for j in log)
    assert all(0 <= j["start"] <= j["end"] for j in log)


def test_a_failed_window_gives_couldnt_check_never_not_backed():
    judge = NoCountJudge(lambda w, c, n: ABSENT, fail_on=lambda extent: "part 2 of" in extent)
    rows, log, _l, _s = run([target(1, "a claim", big_text(700_000))], judge)
    assert rows[0]["label"] == P8.COULDNT and rows[0]["reason_kind"] == P6.R_WINDOW
    assert sum(j["failures"] for j in log) == 1


def test_the_preview_stays_on_v2():
    text = (ROOT / "backend" / "routers" / "whu_check.py").read_text()
    assert "pipeline_v8" not in text
