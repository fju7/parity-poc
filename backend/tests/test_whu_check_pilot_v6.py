"""Check-an-answer pilot v6 (study/whu-reliability/check_pilot/pipeline_v6.py), offline.

v6 = v5, with a windowed whole-source read (overlapping windows, claims batched per window) for the claims v5 sent
to its passages-checked path. A scripted judge stands in for the model; token counts are len // 4. No model call."""
import json
import re
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_v5 as P5  # noqa: E402
import pipeline_v6 as P6  # noqa: E402
import run_pilot_v6 as R6  # noqa: E402

URL = "https://example.org/long-report"
WORDS = ("basin", "rainfall", "aquifer", "levee", "estuary", "upland", "delta", "tributary", "wetland", "runoff")


def count(text):
    return len(text) // 4


def long_text(n=70):
    return "\n\n".join("Paragraph %d: the %s and %s survey in district %d logged %d readings and no change of note."
                       % (i, WORDS[i % 10], WORDS[(i * 3) % 10], i, 100 + i) for i in range(n))


@pytest.fixture
def small(monkeypatch):
    """Windows of 1,200 tokens with 400 overlap; a source over 1,200 tokens is 'long'."""
    monkeypatch.setattr(P6, "WINDOW_TOKENS", 1200)
    monkeypatch.setattr(P6, "OVERLAP_TOKENS", 400)
    monkeypatch.setattr(P6.J, "MAX_SOURCE_TOKENS", 1200)


def target(idx, claim, text, url=URL, sid="Slong", extra_docs=()):
    docs = [{"source_id": sid, "url": url, "extent": "full text", "abstract_only": False, "tokens": count(text),
             "chunked": False, "text": text}] + list(extra_docs)
    return {"idx": idx, "claim": claim, "context": "", "citations": [{"label": str(i + 1), "url": d["url"]}
                                                                      for i, d in enumerate(docs)],
            "full_docs": docs, "stage1": {"label": P6.NOT_BACKED, "study_label": "Absent", "usd": 0.01},
            "path": P5.EXPANDED, "windowed": True}


class BatchJudge:
    """Reads the window and the numbered claims out of each prompt; decide(window_text, claim, n) -> entry."""

    def __init__(self, decide, fail_on=None):
        self.decide, self.fail_on, self.calls, self.lock = decide, fail_on, [], threading.Lock()
        self.messages = self

    def create(self, **kw):
        prompt = "".join(b["text"] for b in kw["messages"][0]["content"])
        doc = re.search(r"<<<DOCUMENT 1 \((.*?)\)\n(.*)\nDOCUMENT 1>>>", prompt, re.S)
        extent, window = doc.group(1), doc.group(2)
        claims = re.findall(r"<<<CLAIM (\d+)\n(.*?)\nCLAIM \1>>>", prompt, re.S)
        with self.lock:
            self.calls.append({"extent": extent, "claims": [c for _n, c in claims], "prefix": kw["messages"][0][
                "content"][0]["text"]})
        if self.fail_on and self.fail_on(extent):
            raise RuntimeError("HTTP 529 overloaded")
        reply = {n: self.decide(window, c, int(n)) for n, c in claims}
        reply = {n: e for n, e in reply.items() if e is not None}
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(reply))], model=kw["model"],
                               stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=3000, output_tokens=200,
                                                     cache_creation_input_tokens=0, cache_read_input_tokens=0))


def run(targets, judge, man=None):
    return P6.windowed_read(targets, man or {}, Path("/nonexistent"), judge, count)


# -- the batched prompt ------------------------------------------------------------------------------------------

def test_the_batched_prompt_is_m1_with_the_listed_edits_only():
    m1 = P6.J.PROMPT.read_text(encoding="utf-8")
    t = P6.batched_prompt()
    assert "{documents}" in t and "{claims}" in t and "{claim}" not in t and "{context}" not in t
    edited = [old for old, _new in P6.M1_EDITS]
    kept = [ln for ln in m1.splitlines() if ln.strip() and not any(ln in old or old.split("\n")[0] in ln
                                                                       for old in edited)]
    assert kept and all(ln in t for ln in kept)                 # every other M1 line, verbatim (labels included)
    assert len(P6.batched_prompt_sha()) == 64


def test_an_edit_that_does_not_match_m1_exactly_once_stops(monkeypatch):
    monkeypatch.setattr(P6, "M1_EDITS", P6.M1_EDITS + (("no such sentence in M1", "x"),))
    with pytest.raises(P6.Stop):
        P6.batched_prompt()


def test_no_m1_instruction_is_copied_into_v6_beyond_the_edited_fragments():
    src = (ROOT / "study" / "whu-reliability" / "check_pilot" / "pipeline_v6.py").read_text(encoding="utf-8")
    edited = [old for old, _new in P6.M1_EDITS]
    lines = [ln.strip() for ln in P6.J.PROMPT.read_text(encoding="utf-8").splitlines() if len(ln.strip()) > 40]
    assert not [ln for ln in lines if ln in src and not any(ln in old for old in edited)]


# -- windows -------------------------------------------------------------------------------------------------------

def test_windows_cover_the_source_fit_one_call_and_overlap_enough():
    text = long_text()
    ws = P6.windows(text, count, size=1200, overlap=400)
    assert len(ws) >= 3 and ws[0][0] == 0 and ws[-1][1] == len(text)
    for a, b in ws:
        assert count(text[a:b]) <= 1200
    for (a1, b1), (a2, b2) in zip(ws, ws[1:]):
        assert a1 < a2 < b1 < b2 and count(text[a2:b1]) >= 400


def test_a_backing_passage_straddling_a_window_boundary_is_read_whole_in_the_next_window(small):
    text = long_text()
    ws = P6.windows(text, count)
    b1 = ws[0][1]
    span = text[b1 - 140:b1 + 140]                               # crosses the end of window 1
    assert span not in text[ws[0][0]:ws[0][1]] and span in text[ws[1][0]:ws[1][1]]
    judge = BatchJudge(lambda window, claim, n: {"label": "Supported", "span": span, "reason": "it says so"}
                       if span in window else {"label": "Absent", "span": window[:60], "reason": "not here"})
    rows, log, layout = run([target(5, "District readings were logged with no change of note.", text)], judge)
    r = rows[0]
    assert r["label"] == P6.BACKED and r["decided_by"] == P6.WINDOWED and r["passage"]["quote"]
    assert len(judge.calls) == len(ws) == len(layout["Slong"]["windows"])          # every window read
    assert "part 1 of %d of a long document" % len(ws) in judge.calls[0]["extent"]


def test_one_window_erroring_gives_couldnt_check_never_not_backed(small):
    text = long_text()
    judge = BatchJudge(lambda w, c, n: {"label": "Absent", "span": w[:60], "reason": "not here"},
                       fail_on=lambda extent: extent.split("part ")[1].startswith("2 of"))
    rows, log, _ = run([target(1, "A claim the source never makes.", text)], judge)
    assert rows[0]["label"] == P6.COULDNT and rows[0]["label"] != P6.NOT_BACKED
    assert rows[0]["reason_kind"] == P6.R_WINDOW and "HTTP 529" in rows[0]["reason"]
    assert sum(j["failures"] for j in log) == 1


def test_a_backing_window_still_backs_when_another_window_errors(small):
    text = long_text()
    good = text[:120]
    judge = BatchJudge(lambda w, c, n: {"label": "Supported", "span": good, "reason": "yes"} if good in w
                       else {"label": "Absent", "span": w[:60], "reason": "no"},
                       fail_on=lambda extent: extent.split("part ")[1].startswith("2 of"))
    rows, _log, _ = run([target(1, "Paragraph 0 claim.", text)], judge)
    assert rows[0]["label"] == P6.BACKED


def test_a_claim_missing_from_the_reply_is_a_failed_window(small):
    text = long_text()
    judge = BatchJudge(lambda w, c, n: None if "missing" in c else {"label": "Absent", "span": w[:60], "reason": "no"})
    rows, _log, _ = run([target(1, "This one is missing from the reply.", text),
                         target(2, "This one is answered.", text)], judge)
    by = {r["idx"]: r for r in rows}
    assert by[1]["label"] == P6.COULDNT and by[1]["reason_kind"] == P6.R_WINDOW
    assert by[2]["label"] == P6.NOT_BACKED


def test_not_backed_only_when_every_window_was_read_and_shows_m1s_first_label(small):
    text = long_text()
    ws = P6.windows(text, count)
    over = text[ws[-1][0]:ws[-1][0] + 80]
    judge = BatchJudge(lambda w, c, n: {"label": "Overstates", "span": over, "reason": "weaker"} if w.startswith(over)
                       else {"label": "Absent", "span": w[:60], "reason": "not here"})
    rows, log, _ = run([target(1, "A stronger claim.", text)], judge)
    assert rows[0]["label"] == P6.NOT_BACKED and rows[0]["study_label"] == "Overstates"
    assert rows[0]["passage"]["quote"] and len(rows[0]["windows"]) == len(ws) and not any(j["failures"] for j in log)


def test_claims_are_batched_at_most_twenty_per_call_and_the_first_call_per_window_goes_alone(small):
    text = long_text()
    ts = [target(i, "Claim number %d about district readings." % i, text) for i in range(25)]
    judge = BatchJudge(lambda w, c, n: {"label": "Absent", "span": w[:60], "reason": "no"})
    rows, log, layout = run(ts, judge)
    nw = len(layout["Slong"]["windows"])
    assert len(judge.calls) == 2 * nw and max(len(c["claims"]) for c in judge.calls) == P6.BATCH
    first_seen = {}
    for i, c in enumerate(judge.calls):
        first_seen.setdefault(c["prefix"], i)
    # every window's first call precedes every second call over the same window
    assert all(first_seen[c["prefix"]] < i for i, c in enumerate(judge.calls) if first_seen[c["prefix"]] != i)
    assert max(first_seen.values()) < min(i for i, c in enumerate(judge.calls) if first_seen[c["prefix"]] != i)
    assert all(r["label"] == P6.NOT_BACKED for r in rows)


def test_a_claim_with_a_short_source_too_gets_a_whole_read_of_it_as_well(small, tmp_path, monkeypatch):
    text = long_text()
    short = {"source_id": "Sshort", "url": "https://example.org/short", "extent": "full text", "abstract_only": False,
             "tokens": 50, "chunked": False, "text": "The short note says district 3 logged 103 readings."}
    t = target(1, "District 3 logged 103 readings.", text, extra_docs=[short])
    seen = {}

    def fake_plan(r, man, work, cnt):
        seen["citations"] = [c["url"] for c in r["citations"]]
        return {"prefix": "P", "worst": 0.01, "idx": r["idx"]}
    monkeypatch.setattr(P6.V5, "plan_reread", fake_plan)
    monkeypatch.setattr(P6.V5, "_one", lambda p, man, client, bc: {"study_label": "Supported", "usd_reread": 0.02,
                                                                    "span": "district 3 logged 103 readings",
                                                                    "reason": "the note says it"})
    judge = BatchJudge(lambda w, c, n: {"label": "Absent", "span": w[:60], "reason": "no"})
    rows, log, _ = run([t], judge)
    assert seen["citations"] == ["https://example.org/short"]                   # only the short source, whole
    assert rows[0]["label"] == P6.BACKED and any(j["kind"] == "whole" for j in log)


# -- the runner's spending rules (§13.8) ---------------------------------------------------------------------------

def test_a_blind_spend_counter_fails_the_run():
    lines = [{"role": R6.ROLE, "issue": "whu-check-pilot-v5", "usd": 0.42}]
    assert R6.counter_blind(0.0, lines)                          # $0 on the run's issue, priced lines for its role
    assert R6.counter_blind(0.42, lines) is None
    assert R6.counter_blind(0.0, []) is None
    spent = [0.0]
    b = R6.Budget(8.0, lambda: spent[0], lambda: lines)
    b.before_call(0.1)
    b.returned()
    with pytest.raises(P6.Stop, match="reads \\$0"):
        b.before_call(0.1)


def test_the_runner_meters_on_its_own_issue_and_role(monkeypatch):
    got = {}
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=lambda api_key: "raw"))
    monkeypatch.setattr(R6.J, "env_keys", lambda: {"ANTHROPIC_API_KEY": "k"})
    monkeypatch.setattr(R6.S, "metered", lambda raw, **kw: got.update(kw) or "metered")
    assert R6.clients() == ("raw", "metered")
    assert got["issue"] == R6.ISSUE == "whu-check-pilot-v6" and got["role"] == R6.ROLE
    assert R6.spent([{"issue": R6.ISSUE, "usd": 1.5}, {"issue": "whu-check-pilot-v5", "usd": 9}]) == 1.5


def test_no_paid_call_on_the_days_reserved_for_vp():
    assert R6.reserved(datetime(2026, 10, 31, 0, 1, tzinfo=timezone.utc))
    assert R6.reserved(datetime(2026, 11, 1, 23, 59, tzinfo=timezone.utc))
    assert not R6.reserved(datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc))


def test_the_preview_stays_on_v2():
    src = (ROOT / "backend" / "routers" / "whu_check.py").read_text(encoding="utf-8")
    assert "PIPELINE_VERSION = 2" in src
