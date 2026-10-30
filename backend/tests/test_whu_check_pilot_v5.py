"""Check-an-answer pilot v5 (study/whu-reliability/check_pilot/pipeline_v5.py), offline.

v5 = v4, then a fuller read of every NOT BACKED: the whole held source where it fits one call, else the top 20
passages plus neighbours (unsupported there -> NOT FOUND IN THE PASSAGES CHECKED). Every network step is v3's
recorded reply; the judge is a scripted client. No model call."""
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_v4 as P4  # noqa: E402
import pipeline_v5 as P5  # noqa: E402
import test_whu_check_pilot as T  # noqa: E402
import test_whu_check_pilot_v4 as T4  # noqa: E402

REPLIES = json.loads((T.FIX / "replies.json").read_text())
SPAN = REPLIES["clearly better than every other format"]["span"]      # verbatim in the held source


class Judge:
    """A scripted judge: reply(prompt, claim) -> {label, span, reason}; records every prompt in order."""

    def __init__(self, reply):
        self.reply, self.calls, self.lock = reply, [], threading.Lock()
        self.messages = self

    def create(self, **kw):
        prompt = "".join(b["text"] for b in kw["messages"][0]["content"])
        claim = prompt.split("<<<CLAIM", 1)[1].split("CLAIM>>>", 1)[0]
        with self.lock:
            self.calls.append(prompt)
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(self.reply(prompt, claim)))],
                               model=kw["model"], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=2000, output_tokens=120,
                                                     cache_creation_input_tokens=0, cache_read_input_tokens=0))


def recorded(_prompt, claim):
    return REPLIES[next(k for k in REPLIES if not k.startswith("_") and k in claim)]


def supported(_prompt, _claim):
    return {"label": "Supported", "span": SPAN, "reason": "the whole source states it"}


def absent(_prompt, _claim):
    return {"label": "Absent", "span": "", "reason": "not in what was shown"}


def stage1(tmp_path):
    """v4's check on the recorded answer: 1 BACKED, 2 NOT BACKED (Overstates, Absent), 1 NO SOURCE."""
    out = P4.check(T4._answer(), tmp_path, T.client(), T.count, net=T4._net())
    return out["results"], out["manifest"]


def test_only_a_stage1_not_backed_label_triggers_a_fuller_read():
    for m1 in ("Overstates", "Understates", "Absent", "Wrong source", "Contradicted"):
        assert P5.needs_fuller_read({"label": P5.NOT_BACKED, "study_label": m1})
        assert P5.needs_fuller_read({"label": P5.COULDNT, "study_label": m1, "verdict_withheld": P5.NOT_BACKED})
    for m1 in ("Supported", "REFUSED", "NOT_VERIFIABLE_ABSTRACT", "UNCITED", None):
        assert not P5.needs_fuller_read({"label": P5.BACKED, "study_label": m1})


def test_a_not_backed_is_rejudged_against_the_whole_source_and_the_second_reading_decides(tmp_path):
    rows, man = stage1(tmp_path)
    planned = P5.plan_v5(rows, man, tmp_path, T.count)
    rereads = [p for p in planned if p.get("path")]
    assert [p["idx"] for p in rereads] == [1, 2] and {p["path"] for p in rereads} == {P5.WHOLE}
    j = Judge(supported)
    out = {r["idx"]: r for r in P5.fuller_read(planned, man, j, None)}
    held = (tmp_path / "sources" / (rereads[0]["docs"][0]["source_id"] + ".txt")).read_text(encoding="utf-8")
    assert len(j.calls) == 2 and all(held in c and P4.PI.DOC_SEP not in c for c in j.calls)   # the whole text
    assert out[0]["label"] == P5.BACKED and out[0]["decided_by"] == P5.PASSAGES and "stage1" not in out[0]
    assert out[3]["label"] == P5.NO_SOURCE and out[3]["decided_by"] == P5.NOT_JUDGED
    for i in (1, 2):
        assert out[i]["label"] == P5.BACKED and out[i]["decided_by"] == P5.WHOLE
        assert out[i]["stage1"]["label"] == P5.NOT_BACKED and out[i]["passage"]["quote"]
        assert out[i]["usd"] >= out[i]["usd_reread"] > 0


def test_a_whole_source_not_backed_stays_not_backed_with_its_own_passage(tmp_path):
    rows, man = stage1(tmp_path)
    out = {r["idx"]: r for r in P5.fuller_read(P5.plan_v5(rows, man, tmp_path, T.count), man, Judge(recorded))}
    assert out[1]["label"] == P5.NOT_BACKED and out[1]["decided_by"] == P5.WHOLE
    assert out[1]["passage"]["quote"] and out[1]["reason"].startswith("Overstates")


def test_over_the_one_call_limit_is_top_20_plus_neighbours_and_unsupported_is_not_found(tmp_path, monkeypatch):
    rows, man = stage1(tmp_path)
    monkeypatch.setattr(P5.J, "MAX_SOURCE_TOKENS", 200)          # the 5,134-character source is now "too long"
    planned = P5.plan_v5(rows, man, tmp_path, T.count)
    rereads = [p for p in planned if p.get("path")]
    assert {p["path"] for p in rereads} == {P5.EXPANDED} and all(p["expanded"] for p in rereads)
    assert all(not d["chunked"] and d["passages"] for p in rereads for d in p["docs"])
    out = {r["idx"]: r for r in P5.fuller_read(planned, man, Judge(absent))}
    for i in (1, 2):
        r = out[i]
        assert r["label"] == P5.NOT_FOUND and r["label"] != P5.NOT_BACKED and r["reason_kind"] == P5.NOT_FOUND
        assert r["decided_by"] == P5.EXPANDED and r.get("passage") is None and P5.NOT_FOUND_NOTE in r["reason"]
    t = P5.totals(list(out.values()))
    assert t[P5.NOT_FOUND] == 2 and t[P5.NOT_BACKED] == 0
    assert "2 NOT FOUND IN THE PASSAGES CHECKED" in P5.summary(list(out.values()), 4)
    sup = {r["idx"]: r for r in P5.fuller_read(P5.plan_v5(rows, man, tmp_path, T.count), man, Judge(supported))}
    assert sup[1]["label"] == P5.BACKED and sup[1]["decided_by"] == P5.EXPANDED and sup[1]["passage"]["quote"]


def test_expanded_text_is_the_top_passages_with_their_neighbours_never_the_whole_source():
    paras = ["Paragraph %d is about rainfall in the lowland basin and nothing else of note here." % i
             for i in range(200)]
    paras[100] = "The Lindqvist cohort reported remission of 41.7% after cognitive behavioural therapy."
    text = "\n\n".join(paras)
    sent, rec = P5.expanded_text(text, "Cognitive behavioural therapy gave 41.7% remission in the Lindqvist cohort.")
    assert paras[100] in sent and paras[99] in sent and paras[101] in sent
    assert len(rec["top"]) <= P5.EXPAND_K and len(sent) < len(text) / 4


def test_rereads_sharing_a_prefix_go_first_alone_then_the_rest(tmp_path):
    rows, man = stage1(tmp_path)
    planned = P5.plan_v5(rows, man, tmp_path, T.count)
    twin = dict(next(p for p in planned if p.get("path")), idx=99)
    first, rest = P5.waves([p for p in planned if p.get("path")] + [twin])
    assert twin in rest and all(p["prefix"] != twin["prefix"] or p is not twin for p in first)
    assert len({p["prefix"] for p in first}) == len(first)


def test_a_full_v5_check_runs_both_stages_and_records_the_path(tmp_path):
    j = Judge(lambda p, c: recorded(p, c) if P4.PI.DOC_SEP in p else supported(p, c))
    out = P5.check(T4._answer(), tmp_path, j, T.count, net=T4._net())
    assert out["version"] == 5 and out["summary"].startswith("4 of 4 claims checked")
    assert len(j.calls) == 5                                        # 3 on passages, 2 on the whole source
    assert [r["decided_by"] for r in out["results"]] == [P5.PASSAGES, P5.WHOLE, P5.WHOLE, P5.NOT_JUDGED]
    assert not any(k in r for r in out["results"] for k in P5._HIDDEN)
    pub = P5.public(out["results"], out["manifest"])
    assert [p["decided_by"] for p in pub] == [r["decided_by"] for r in out["results"]]


def test_no_prompt_is_copied_into_v5():
    src = (ROOT / "study" / "whu-reliability" / "check_pilot" / "pipeline_v5.py").read_text(encoding="utf-8")
    prompt = P5.J.PROMPT.read_text(encoding="utf-8")
    long_lines = [ln.strip() for ln in prompt.splitlines() if len(ln.strip()) > 40]
    assert long_lines and not any(ln in src for ln in long_lines)
    assert "J.build(" in src and "V1.judge(" in src


# -- the runner's spending rules (§12.4) ---------------------------------------------------------------

import run_pilot_v5 as R5  # noqa: E402


def test_room_needs_ten_dollars_left_under_the_day_cap_after_the_worst_case():
    assert R5.room(9.62, 40.38, 60.0)[0]
    assert not R5.room(9.63, 40.38, 60.0)[0]
    assert not R5.room(45.0, 6.0, 60.0)[0] and R5.room(45.0, 5.0, 60.0)[0]


def test_the_budget_holds_spent_plus_in_flight_under_the_cap_and_releases_on_return():
    spent = [0.0]
    b = R5.Budget(8.0, lambda: spent[0])
    b.before_call(3.0)
    b.before_call(4.0)                                   # same thread: 7 in flight
    with pytest.raises(P5.Stop):
        b.before_call(1.5)                               # 0 + 7 + 1.5 > 8
    b.returned()
    spent[0] = 1.0                                       # the calls' actual cost is now in the ledger
    b.before_call(6.5)                                   # 1 + 0 + 6.5 <= 8
    assert b.in_flight == pytest.approx(6.5)
    calls = []
    client = b.wrap(SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: calls.append(kw) or "ok")))
    assert client.messages.create(model="m") == "ok" and b.in_flight == 0 and calls


def test_the_preview_stays_on_v2():
    src = (ROOT / "backend" / "routers" / "whu_check.py").read_text(encoding="utf-8")
    assert "PIPELINE_VERSION = 2" in src
