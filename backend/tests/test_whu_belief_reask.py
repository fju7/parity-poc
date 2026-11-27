"""The belief step asks once more for different outlets when none is confirmed (advisor's ruling D on P117, 2026-11-25;
orch/premise_reading.belief_outlets).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): the step proposed three outlets and code confirmed none; none
was a wall. Save the Children's article URL redirected to its Zimbabwe section page (14 of 36 key words); Leonard
Cheshire's and UKFIET's pages were fetched but carried 17 and 16 of 36 (needs 22). (02za: 2 of 3 short of key words,
1 confirmed; 02z: 2 walls, 1 confirmed.) A different proposal could avoid each 02zc failure, so: one re-ask naming the
refused outlets, code excluding any repeat, verify_outlet unchanged, both rounds recorded.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
CASE_02ZC = ROOT / "issues" / "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"

from orch import premise_reading as P   # noqa: E402
from orch import steps as ST            # noqa: E402

BELIEF = "Inclusive education helps children with disabilities learn in ordinary schools."
GOOD = (b"<html><body><p>Inclusive education means all children learn together in the same schools, including "
        b"children with disabilities.</p></body></html>")
SHORT = b"<html><body><p>Our programme in Tanzania supports families.</p></body></html>"


def _get(pages, log):
    def get(url):
        log.append(url)
        if url.endswith("/robots.txt"):
            return pages.get(url, {"status": 404, "headers": {}, "body": b"", "final_url": url})
        return pages[url]
    return get


def _ok(url, body=GOOD, status=200, final=None):
    return {"status": status, "headers": {}, "body": body, "final_url": final or url}


@pytest.fixture
def case(tmp_path, monkeypatch):
    # Round 2 is off since ruling 2 on P162 (P.ROUNDS = 1); its code stays and is tested with it switched on.
    monkeypatch.setattr(P, "ROUNDS", 2)
    c = tmp_path / "issues" / "WHU-OT1-99-whu-x"
    c.mkdir(parents=True)
    (c / "premise.json").write_text(json.dumps({"belief": {"statement": BELIEF},
                                                "public_record_check": {"carried_in_general_coverage": ""}}))
    return c


def _asker(replies):
    asked = []

    def ask(prompt, max_tokens, role):
        asked.append((role, prompt))
        return replies[len(asked) - 1]
    return ask, asked


def _log(case):
    return [json.loads(l) for l in (case / P.LOG).read_text().splitlines() if l.strip()]


R1 = json.dumps({"outlets": [
    {"outlet": "Leonard Cheshire", "url": "https://www.leonardcheshire.org/a", "sentence": "s"},
    {"outlet": "Save the Children", "url": "https://zimbabwe.savethechildren.net/news/x", "sentence": "s"}]})


def test_02zc_none_confirmed_and_none_a_wall():
    rows = [json.loads(l) for l in (CASE_02ZC / P.LOG).read_text().splitlines() if l.strip()]
    belief = [r for r in rows if r["check"] == "belief-outlet"]
    assert len(belief) == 3 and not any(r["code"]["ok"] for r in belief)
    assert not any("wall" in r["code"]["why"] for r in belief)
    assert all(r["code"]["robots"] == "robots.txt allows it" for r in belief)


def test_round_two_asks_for_different_outlets_and_can_confirm_one(case):
    r2 = json.dumps({"outlets": [{"outlet": "BBC News", "url": "https://www.bbc.co.uk/news/education-1",
                                  "sentence": "s"}]})
    ask, asked = _asker([R1, r2])
    log = []
    pages = {"https://www.leonardcheshire.org/a": _ok("https://www.leonardcheshire.org/a", SHORT),
             "https://zimbabwe.savethechildren.net/news/x": _ok("https://zimbabwe.savethechildren.net/news/x", SHORT,
                                                                 final="https://www.savethechildren.net/zimbabwe"),
             "https://www.bbc.co.uk/news/education-1": _ok("https://www.bbc.co.uk/news/education-1")}
    got = P.belief_outlets(case, ask, "claude-sonnet-4-6", get=_get(pages, log))
    assert [r for r, _p in asked] == ["belief-outlet", "belief-outlet-reask"]
    second = asked[1][1]
    assert second.startswith(P.BELIEF_PROMPT.format(n=3, belief=BELIEF))
    assert "Leonard Cheshire (https://www.leonardcheshire.org/a)" in second and "DIFFERENT" in second
    assert got["verified"] == 1 and got["rounds"] == [{"round": 1, "proposed": 2, "verified": 0},
                                                      {"round": 2, "proposed": 1, "verified": 0 + 1, "excluded": 0}]
    d = json.loads((case / "premise.json").read_text())
    assert [c["outlet"] for c in d["belief"]["carried_by"]] == ["BBC News"]
    assert [(r["round"], r["proposed"]["outlet"], r["code"]["ok"]) for r in _log(case)] == [
        (1, "Leonard Cheshire", False), (1, "Save the Children", False), (2, "BBC News", True)]


def test_a_repeated_outlet_or_url_is_excluded_by_code_and_never_fetched_again(case):
    r2 = json.dumps({"outlets": [
        {"outlet": "Leonard Cheshire", "url": "https://www.leonardcheshire.org/b", "sentence": "s"},     # same outlet
        {"outlet": "Other", "url": "http://zimbabwe.savethechildren.net/news/x/", "sentence": "s"}]})  # same URL
    ask, asked = _asker([R1, r2])
    log = []
    pages = {"https://www.leonardcheshire.org/a": _ok("https://www.leonardcheshire.org/a", SHORT),
             "https://zimbabwe.savethechildren.net/news/x": _ok("https://zimbabwe.savethechildren.net/news/x", SHORT)}
    got = P.belief_outlets(case, ask, "m", get=_get(pages, log))
    assert got["verified"] == 0 and got["rounds"][1] == {"round": 2, "proposed": 0, "verified": 0, "excluded": 2}
    assert "https://www.leonardcheshire.org/b" not in log and log.count("https://zimbabwe.savethechildren.net/news/x") == 1
    assert [r["code"]["why"] for r in _log(case) if r["round"] == 2] == [
        "excluded by code: refused in round 1, not checked again"] * 2
    d = json.loads((case / "premise.json").read_text())
    assert "carried_by" not in d["belief"] and not d["public_record_check"]["carried_in_general_coverage"]


def test_no_round_two_when_round_one_confirms_one(case):
    ask, asked = _asker([json.dumps({"outlets": [{"outlet": "U", "url": "https://www.unicef.org/x"}]})])
    got = P.belief_outlets(case, ask, "m", get=_get({"https://www.unicef.org/x": _ok("https://www.unicef.org/x")}, []))
    assert len(asked) == 1 and got["verified"] == 1 and got["rounds"] == [{"round": 1, "proposed": 1, "verified": 1}]


def test_an_unusable_round_two_reply_is_recorded_not_a_crash(case):
    ask, asked = _asker([R1, "no json here", "still none"])
    pages = {"https://www.leonardcheshire.org/a": _ok("https://www.leonardcheshire.org/a", SHORT),
             "https://zimbabwe.savethechildren.net/news/x": _ok("https://zimbabwe.savethechildren.net/news/x", SHORT)}
    got = P.belief_outlets(case, ask, "m", get=_get(pages, []))
    assert got["verified"] == 0 and "unusable" in got["rounds"][1]
    assert len(asked) == 3                                        # round 2 and its one re-ask, then stop


def test_the_step_is_one_call_whose_limit_is_its_derived_bound():
    # the advisor's ruling on the belief limit: (calls in one round = 1) x max(dry run $0.75, highest same-config
    # measured belief call) x 2; the $0.50 of ruling 2 on P162 was below the call's own $0.75 reservation
    import stage_cap as SC
    b = ST.BY_NAME["belief"]
    assert P.ROUNDS == 1 and b.max_calls == 1 and ST.BELIEF_CALLS_PER_ROUND == 1
    rows = [{"role": "belief-outlet", "usd": 0.7127, "model": ST.GATE_MODEL, "step": "belief"},
            {"role": "belief-outlet", "usd": 2.00, "model": "other-model", "step": "belief"},      # not same config
            {"role": "belief-outlet", "usd": 3.00, "model": ST.GATE_MODEL}]                        # not orchestrated
    assert SC.belief_call_bound(ST.GATE_MODEL, rows)[0] == pytest.approx(1.50)                    # max(.75,.7127)x2
    assert SC.belief_call_bound(ST.GATE_MODEL, [])[0] == pytest.approx(1.50)                      # the dry run
    hi = rows[:1] + [{"role": "belief-outlet", "usd": 0.90, "model": ST.GATE_MODEL, "step": "belief"}]
    assert SC.belief_call_bound(ST.GATE_MODEL, hi)[0] == pytest.approx(1.80)


def test_the_guard_admits_the_rounds_call_and_refuses_a_second_round(monkeypatch):
    import stage_cap as SC
    SL = SC.S                     # spend_ledger as stage_cap loads it (backend/scripts never goes on sys.path)
    b = ST.BY_NAME["belief"]
    made = []
    monkeypatch.setattr(SL, "entries", lambda: list(made))
    monkeypatch.setattr(SL, "orch_lock", lambda: {"token": "t", "step": "belief"})
    for k, v in {"WHU_ORCH_STEP": "belief", "WHU_ORCH_TOKEN": "t", "WHU_ORCH_ISSUE": "x", "WHU_ORCH_STEP_START": "",
                 "WHU_ORCH_ALLOW": json.dumps(ST.allow_for(b)), "WHU_ORCH_STEP_CAP": "1.5",
                 "WHU_ORCH_STEP_CALLS": str(b.max_calls)}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv(SL.NEXT_BOUND_ENV, raising=False)
    SL.orch_guard(ST.GATE_MODEL, "factcheck_draft.py", "belief-outlet", "x", 0.75)          # the round's one call
    made.append({"issue": "x", "at": "2026-11-27T01:00:00+00:00", "step": "belief", "role": "belief-outlet",
                 "usd": 0.7127})
    with pytest.raises(SL.OrchestratorRefused, match="made its 1 calls"):
        SL.orch_guard(ST.GATE_MODEL, "factcheck_draft.py", "belief-outlet", "x", 0.75)      # a second round
    monkeypatch.setenv("WHU_ORCH_STEP_CAP", "0.5")                                         # the $0.50 error
    made.clear()
    with pytest.raises(SL.OrchestratorRefused, match="\\$0.50 cap"):
        SL.orch_guard(ST.GATE_MODEL, "factcheck_draft.py", "belief-outlet", "x", 0.75)


def test_a_malformed_reply_is_never_asked_again_and_the_fail_safe_stays(tmp_path):
    import belief_claims as BC
    c = tmp_path / "issues" / "WHU-OT1-99-whu-z"
    c.mkdir(parents=True)
    (c / "premise.json").write_text(json.dumps({"belief": {"statement": BELIEF},
                                                "public_record_check": {"carried_in_general_coverage": ""}}))
    asked = []
    got = P.belief_outlets(c, lambda p, m, r: asked.append(r) or "not json at all", "m",
                           get=lambda url: {"status": 404, "headers": {}, "body": b"", "final_url": url})
    assert asked == ["belief-outlet"] and got["verified"] == 0 and got["rounds"][0].get("malformed") is True
    assert json.loads((c / "premise.json").read_text())["belief"]["outlet_unverified"]["sentence"] == BC.UNVERIFIED


def test_with_one_round_nothing_confirmed_asks_once_and_keeps_the_fail_safe(tmp_path):
    import belief_claims as BC
    c = tmp_path / "issues" / "WHU-OT1-99-whu-y"
    c.mkdir(parents=True)
    (c / "premise.json").write_text(json.dumps({"belief": {"statement": BELIEF},
                                                "public_record_check": {"carried_in_general_coverage": ""}}))
    asked = []

    def ask(prompt, max_tokens, role):
        asked.append(role)
        return json.dumps({"outlets": [{"outlet": "Nowhere", "url": "https://example.org/x", "sentence": "x"}]})
    got = P.belief_outlets(c, ask, "m", get=lambda url: {"status": 404, "headers": {}, "body": b"", "final_url": url})
    assert asked == ["belief-outlet"] and got["verified"] == 0 and len(got["rounds"]) == 1
    rec = json.loads((c / "premise.json").read_text())["belief"]["outlet_unverified"]
    assert rec["sentence"] == BC.UNVERIFIED
