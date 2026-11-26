"""Raw replies kept privately, and the replay gate (advisor's ruling 2 on the design review of 2026-11-26;
reply_store.py, orch/replay_rehearsal.py, orch/replay_gate.py).

  * a paid orchestrated call's reply is recorded raw, outside the repository, never a key; nothing is recorded in a
    rehearsal or outside an orchestrated paid run;
  * the replay rebuilds the recorded run's replies where a record holds the whole answer (premise, discovery,
    belief outlets) and labels every other reply synthetic; a recorded cut-off reply is censored (synthetic);
    the recorded output count comes back with each reply and a count at or over today's limit is a cut-off;
  * the gate's verdicts, and a paid run refuses without a passing gate record for the current code.
The 02zd records read here are committed (issues/WHU-OT1-02zd-...); the private checkpoint is read only when
present. Nothing is fetched or spent.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
ZD = ROOT / "issues" / "WHU-OT1-02zd-whu-lean-orch-t1-q1-02zd"
ZD_SLUG = "whu-lean-orch-t1-q1-02zd"

import reply_store as RS  # noqa: E402
from orch import replay_gate as RG  # noqa: E402
from orch import replay_rehearsal as RR  # noqa: E402


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_REPLY_STORE", str(tmp_path / "replies"))
    return tmp_path / "replies"


def test_a_paid_reply_is_recorded_raw_and_never_a_key(store, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_MODE", "paid")
    monkeypatch.setenv("WHU_ORCH_STEP", "premise")
    RS.record(issue="x", site="premise", role="premise", model="m", max_tokens=4000, stop_reason="end_turn",
              usage={"output": 12}, prompt="the prompt", text='{"belief": "b"} sk-ant-abcdefghijklmnop')
    [row] = RS.load("x")
    assert row["text"].startswith('{"belief": "b"}') and "sk-ant-" not in row["text"]
    assert row["step"] == "premise" and row["max_tokens"] == 4000 and row["raw"] is True
    assert len(row["prompt_sha256"]) == 64 and "prompt" not in row


@pytest.mark.parametrize("mode", ["rehearse", "trial", "replay", ""])
def test_nothing_is_recorded_outside_a_paid_run(store, monkeypatch, mode):
    monkeypatch.setenv("WHU_ORCH_MODE", mode)
    RS.record(issue="x", site="s", role="r", model="m", max_tokens=1, stop_reason=None, usage={}, prompt="p",
              text="t")
    assert RS.load("x") == []


def test_the_store_is_outside_the_repository_by_default(monkeypatch):
    monkeypatch.delenv("WHU_REPLY_STORE", raising=False)
    assert ROOT not in RS.root().parents and "whu-study-private" in str(RS.root())


def test_factcheck_call_records_its_raw_reply_in_a_paid_run(store, monkeypatch):
    import contextlib
    sys.path.insert(0, str(ROOT / "backend" / "scripts" / "signal"))
    import factcheck_draft as F
    monkeypatch.setattr(F, "_spend", types.SimpleNamespace(orch_guard=lambda *a, **k: None,
                                                           check_cap=lambda *a, **k: None,
                                                           call_site=lambda s: contextlib.nullcontext()))
    monkeypatch.setattr(F, "_ledger_now", lambda e: None, raising=False)
    monkeypatch.setattr(F, "_LEDGER_ISSUE", "rs-test")
    monkeypatch.setattr(F, "_RS", RS)

    class C:
        messages = None

        def __init__(self):
            self.messages = self

        def create(self, **kw):
            return types.SimpleNamespace(model=F.SIGNAL_MODEL, stop_reason="end_turn",
                                         usage=types.SimpleNamespace(input_tokens=3, output_tokens=4,
                                                                     cache_creation_input_tokens=0,
                                                                     cache_read_input_tokens=0, server_tool_use=None),
                                         content=[types.SimpleNamespace(type="text", text='{"sources": []}')])
    monkeypatch.setattr(F, "_get_client", lambda: C())
    monkeypatch.setenv("WHU_ORCH_MODE", "paid")
    monkeypatch.setenv("WHU_ORCH_STEP", "discover")
    assert F.call("s", "u", search=False, label="discover", raw=True) == '{"sources": []}'
    [row] = RS.load("rs-test")
    assert row["call_site"] == "fc:discover" and row["text"] == '{"sources": []}' and row["usage"]["output"] == 4


# --- the replay ----------------------------------------------------------------------------------------------------

@pytest.fixture
def replay(tmp_path, monkeypatch, store):
    monkeypatch.setenv("WHU_REHEARSE_REPLAY", "1")
    monkeypatch.setenv("WHU_REHEARSE_BASE_SLUG", ZD_SLUG)
    monkeypatch.setenv("WHU_REHEARSE_BASE", str(ZD))
    monkeypatch.setenv("WHU_REPLAY_ROOT", str(ROOT))
    return tmp_path


def test_the_premise_and_discovery_are_rebuilt_from_02zds_own_records(replay):
    p = RR.reply(replay, "premise", "premise", 4000)
    assert p["source"] == "parsed" and json.loads(p["text"])["belief"].startswith(
        json.loads((ZD / "premise.json").read_text())["belief"]["statement"][:40])
    assert p["output"] == 1051                                        # 02zd's own premise call, from the ledger
    d = RR.reply(replay, "discover", "discover", 4600)
    props = json.loads((ZD / "proposals.json").read_text())["proposals"]
    assert d["source"] == "parsed" and json.loads(d["text"])["sources"] == props and len(props) == 8


def test_the_belief_rounds_are_rebuilt_round_by_round(replay):
    r1 = json.loads(RR.reply(replay, "belief", "belief-outlet", 4200)["text"])["outlets"]
    r2 = RR.reply(replay, "belief", "belief-outlet", 4200)
    assert [o["outlet"] for o in r1][0] == "Devex" and r2["output"] == 2051
    assert "House of Commons" in r2["text"]


def test_02zds_cut_off_premise_reading_is_censored_and_replayed_synthetic(replay):
    got = RR.reply(replay, "premise_reading", "premise-reading", 3000)
    assert got["source"] == "synthetic" and got["text"] is None and "cut off" in got["why"]


def test_a_recorded_count_at_or_over_todays_limit_is_a_cut_off():
    assert RR.stop_for(1500, 1500) == "max_tokens" and RR.stop_for(1499, 1500) == "end_turn"
    assert RR.stop_for(None, 1500) == "end_turn"


def test_a_reply_no_record_holds_is_labelled_synthetic(replay):
    got = RR.reply(replay, "coverage", "coverage", 1200)
    assert got["source"] == "synthetic" and got["text"] is None and got["why"] == "no record holds this answer"


def test_02zds_held_documents_are_seeded_at_their_own_urls(tmp_path):
    if not (RR.CHECKPOINTS / ZD_SLUG).exists():
        pytest.skip("the private checkpoints are local only")
    seeded = RR.seed_http(ZD_SLUG, tmp_path / "http", lambda u: "k%d" % abs(hash(u)))
    ok = [s for s in seeded if s["seeded"]]
    assert ok and all((tmp_path / "http" / ("k%d.body" % abs(hash(s["url"])))).exists() for s in ok)


# --- the gate ------------------------------------------------------------------------------------------------------

REC = {"last": "premise_reading", "stops": set()}


@pytest.mark.parametrize("result,steps,unknown,verdict", [
    ("Ready.", ["provenance", "archive"], 0, "PASS"),
    ("Insufficient sources: 1 of 4 confirmed sources held (minimum 2); not drafted", ["acquire"], 0, "PASS"),
    ("Not Ready: acquire: registry unavailable; run again later (x)", ["acquire"], 0, "INCONCLUSIVE"),
    ("Not Ready: AttributeError: 'dict' object has no attribute 'strip'", ["draft"], 0, "FAIL"),
    ("Not Ready: draft: record changed outside the step that owns it", ["draft"], 0, "FAIL"),
    ("Not Ready", ["provenance", "preflight", "archive"], 0, "PASS"),
    ("Ready.", ["archive"], 2, "FAIL")])
def test_gate_verdicts(result, steps, unknown, verdict):
    rep = {"result": result, "steps": [{"step": s} for s in steps], "_stops": set()}
    assert RG.judge(REC, rep, unknown)[0] == verdict


def test_a_new_stop_row_fails_the_gate():
    rec = {"last": "archive", "stops": {"page gate never"}}
    rep = {"result": "Not Ready", "steps": [{"step": "archive"}], "_stops": {"page gate never", "quotation matcher 11"}}
    v, why = RG.judge(rec, rep, 0)
    assert v == "FAIL" and "quotation matcher 11" in why


def test_check_needs_a_passing_record_for_this_code(tmp_path, monkeypatch):
    monkeypatch.setattr(RG, "GATE_DIR", tmp_path)
    assert RG.check()[0] is False
    sha = RR.code_sha()
    (tmp_path / ("%s.json" % sha)).write_text(json.dumps({"code_sha": sha, "passed": False, "runs": [
        {"slug": "s", "verdict": "FAIL"}]}))
    assert RG.check()[0] is False
    (tmp_path / ("%s.json" % sha)).write_text(json.dumps({"code_sha": sha, "passed": True, "at": "now", "runs": []}))
    assert RG.check()[0] is True


def test_a_paid_run_refuses_without_the_gate():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    i = src.index('if a.mode == "paid":\n            # Ruling 2 on the design review')
    assert "RG.check()" in src[i:i + 400] and "return 2" in src[i:i + 400]
