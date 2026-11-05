"""The fresh set's stage 2 (study/whu-reliability/check_pilot/fresh_judge.py), offline: no model, no network."""
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
import fresh_judge as G  # noqa: E402

KM = {"I1": ("A", "Claude", 0), "I2": ("A", "Claude", 1), "I3": ("A", "Claude", 2), "I4": ("A", "Claude", 3),
      "I5": ("B", "Gemini", 0), "I6": ("B", "Gemini", 1)}
V8 = {("A", "Claude"): {0: ("x0", "BACKED"), 1: ("x1", "NOT BACKED"), 2: ("x2", "COULDN'T CHECK")},
      ("B", "Gemini"): {0: ("y0", "BACKED"), 1: ("changed", "BACKED")}}
TEXTS = {("A", "Claude"): {0: "x0", 1: "x1", 2: "x2", 3: "x3"}, ("B", "Gemini"): {0: "y0", 1: "y1"}}


@pytest.fixture
def stage2(tmp_path, monkeypatch):
    fresh = tmp_path / "fresh_m1"
    fresh.mkdir()
    (fresh / "key_map.json").write_text(json.dumps(
        {i: {"question": q, "system": s, "sentence": "%s/%s/%d" % (q, s, n)} for i, (q, s, n) in KM.items()}))
    (fresh / "uncited.json").write_text(json.dumps([{"item": "I4"}]))
    (fresh / "items.json").write_text(json.dumps([{"item": i, "claim": "c", "citations": [{"url": "https://s"}],
                                                   "reference": "r"} for i in KM]))
    frozen = tmp_path / "sampling_log.json"
    frozen.write_text("{}")
    monkeypatch.setattr(G, "FRESH_M1", fresh)
    monkeypatch.setattr(G.FS, "FROZEN", frozen)
    monkeypatch.setattr(G, "ROOT2", tmp_path / "stage2")
    monkeypatch.setattr(G, "RUN", tmp_path / "stage2" / "m1")
    monkeypatch.setattr(G, "LOG2", tmp_path / "log2")
    monkeypatch.setattr(G, "SCOPE", tmp_path / "log2" / "scope.json")
    monkeypatch.setattr(G, "COUNTS", tmp_path / "counts.json")
    monkeypatch.setattr(G, "sentence_texts", lambda q, s: TEXTS[q, s])
    monkeypatch.setattr(G, "v8_rows", lambda q, s: {i: {"idx": i, "claim": c, "label": l}
                                                    for i, (c, l) in V8[q, s].items()})
    return tmp_path


def test_the_scope_is_the_v8_judged_sentences_with_the_same_text_and_is_written_once(stage2):
    assert G.do_scope(None) == 0
    sc = json.loads(G.SCOPE.read_text())
    assert sc["items"] == 3 and sorted(json.loads((G.RUN / "key_map.json").read_text())) == ["I1", "I2", "I5"]
    assert sc["classified"] == {"in scope: v8 BACKED": 2, "in scope: v8 NOT BACKED": 1, "uncited (not an M1 item)": 1,
                                "v8 COULDN'T CHECK": 1, "v8's claim text differs from the sampled sentence": 1}
    assert [i["item"] for i in json.loads((G.RUN / "items.json").read_text())] == ["I1", "I2", "I5"]
    with pytest.raises(SystemExit, match="decided once"):
        G.do_scope(None)


def test_no_scope_after_a_judge_reply(stage2):
    (G.RUN / "replies" / "claude").mkdir(parents=True)
    (G.RUN / "replies" / "claude" / "I1.json").write_text("{}")
    with pytest.raises(SystemExit, match="before any judging"):
        G.do_scope(None)


def _est(likely, items=3):
    G.ROOT2.mkdir(parents=True, exist_ok=True)
    (G.ROOT2 / "estimate.json").write_text(json.dumps({"at": "t", "items": items, "likely_usd": likely,
                                                       "worst_usd": 3 * likely}))


def test_the_run_stops_before_any_call_when_likely_passes_the_line(stage2, monkeypatch, capsys):
    _est(81.0)
    monkeypatch.setattr(G, "spent", lambda entries=None: 0.0)
    monkeypatch.setattr(G.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("judged")))
    assert G.do_run(types.SimpleNamespace(today=40, vp_planned=0)) == 5
    assert "nothing was called" in capsys.readouterr().out


def test_the_run_stops_with_no_room_under_the_day_cap(stage2, monkeypatch):
    _est(30.0)
    monkeypatch.setattr(G, "spent", lambda entries=None: 0.0)
    monkeypatch.setattr(G.R5, "today_total", lambda: 35.0)                       # 35 + 20 leaves 5 < 10
    monkeypatch.setattr(G.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("judged")))
    assert G.do_run(types.SimpleNamespace(today=20, vp_planned=0)) == 3


def test_the_run_calls_both_judges_once_each_on_its_own_issue_capped_at_todays_amount(stage2, monkeypatch):
    _est(30.0)
    monkeypatch.setattr(G, "spent", lambda entries=None: 12.0)
    monkeypatch.setattr(G.R5, "today_total", lambda: 0.0)
    got = {}
    monkeypatch.setattr(G.subprocess, "run", lambda cmd, **k: got.setdefault("cmd", cmd) and
                        types.SimpleNamespace(returncode=0))
    assert G.do_run(types.SimpleNamespace(today=40, vp_planned=0)) == 0
    cmd = got["cmd"]
    val = lambda f: cmd[cmd.index(f) + 1]
    assert val("--judges") == "claude,openai" and val("--consistency-share") == "0"
    assert val("--ledger-issue") == "whu-check-fresh-judge" and float(val("--cap")) == pytest.approx(52.0)
    assert G.ISSUE == "whu-check-fresh-judge" and G.LINE_CAP == 80.0
    caps = json.loads((ROOT / "backend" / "data" / "spend" / "caps.json").read_text())
    assert caps["per_issue"]["whu-check-fresh-judge"] == 80


def _reply(item, judge, label, **extra):
    d = G.RUN / "replies" / judge
    d.mkdir(parents=True, exist_ok=True)
    (d / (item + ".json")).write_text(json.dumps({"label": label, **extra}))


def _manifest():
    (G.RUN / "sources").mkdir(parents=True, exist_ok=True)
    (G.RUN / "sources" / "manifest.json").write_text(json.dumps([{"source_id": "S1", "url": "https://s",
                                                                  "text_chars": 900000}]))


def test_agreement_counts_three_ways_lists_disagreements_by_direction_and_is_never_ready(stage2, monkeypatch):
    G.do_scope(None)
    monkeypatch.setattr(G.F, "COUNTS", stage2 / "v8_counts.json")
    (stage2 / "v8_counts.json").write_text(json.dumps({"pass_bar": {"couldnt_check_at_most_20": False}}))
    monkeypatch.setattr(G, "spent", lambda entries=None: 1.0)
    monkeypatch.setattr(G.V1, "study_label_to_check", lambda l: {"Supported": "BACKED", "Absent": "NOT BACKED"}.get(
        l, "COULDN'T CHECK"))
    _manifest()
    for item, c, o in (("I1", "Supported", "Supported"), ("I2", "Supported", "Absent"), ("I5", "Absent", "Unreachable")):
        _reply(item, "claude", c)
        _reply(item, "openai", o, unreachable_sources=[{"url": "https://s", "source_id": "S1"}]
               if o == "Unreachable" else [])
    out, pairs = G.agree()
    a = out["agreement"]
    assert (a["vs_claude_judge"]["n"], a["vs_claude_judge"]["agree"]) == (3, 1)
    assert (a["vs_openai_judge"]["n"], a["vs_openai_judge"]["agree"]) == (2, 2)
    assert (a["two_judge_agreed"]["n"], a["two_judge_agreed"]["agree"]) == (1, 1)
    d = a["vs_claude_judge"]["disagreement_counts"]
    assert d == {"v8 BACKED, judge NOT BACKED": 1, "v8 NOT BACKED, judge BACKED": 1}
    assert out["ready"] is False and len(pairs) == 3
    assert "no human has checked" in out["label"] and "Blinding was partial" in out["label"]
    nj = out["not_judged"]                       # I5: OpenAI did not judge it; listed, excluded, counted
    assert nj["items"] == 1 and nj["ids"] == ["I5"] and nj["by_judge_label"] == {"openai": {"Unreachable": 1}}
    assert nj["detail"][0]["judges"] == ["openai"] and nj["detail"][0]["sources"][0]["text_chars"] == 900000
    ct = out["contested"]                        # I2: Claude judge BACKED, OpenAI NOT BACKED
    assert ct["items"] == 1 and ct["detail"][0]["item"] == "I2" and ct["status"] == G.CONTESTED
    assert G.committed(out)["contested"]["detail"][0].get("item") is None


def test_the_not_judged_list_names_the_judge_and_the_source_length(stage2):
    G.do_scope(None)
    _manifest()
    for item in ("I1", "I2", "I5"):
        why = [{"url": "https://s", "source_id": "S1", "why": "key word 'x' is in the source but not in what the "
                                                              "judge receives"}] if item == "I2" else []
        for j in G.JUDGES:
            _reply(item, j, "INCOMPLETE_SOURCES" if item == "I2" else "Supported", undelivered_sources=why,
                   sources=[{"source_id": "S1", "tokens": 406098}] if why else [])
    pairs = [{"item": i, "answer": "A/Claude", "idx": 0, "v8": "BACKED",
              **{j: ("COULDN'T CHECK" if i == "I2" else "BACKED") for j in G.JUDGES},
              **{j + "_raw": ("INCOMPLETE_SOURCES" if i == "I2" else "Supported") for j in G.JUDGES}}
             for i in ("I1", "I2", "I5")]
    nj = G.not_judged(pairs)
    assert nj["ids"] == ["I2"] and nj["detail"][0]["judges"] == ["claude", "openai"]
    src = nj["detail"][0]["sources"][0]
    assert (src["text_chars"], src["tokens"], src["judges"]) == (900000, 406098, ["claude", "openai"])
    assert "judge receives" in src["why"]
    assert nj["not_validated"] == ("Agreement is not measured on claims whose source exceeds the judges' single-read "
                                   "limit (1 items skipped, sources of 406k-406k tokens); v8's windowed reading of "
                                   "very long sources is therefore not validated by this test.")


def test_the_estimate_log_marks_an_estimate_written_after_the_run_as_in_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(G.F, "EST_LOG", tmp_path / "log.jsonl")
    led = [{"at": "2026-11-04T15:00:00+00:00", "issue": "i", "usd": 1.0}]
    before = G.F.log_estimate("r", "i", {"at": "2026-11-04T14:00:00+00:00", "likely_usd": 50.0}, 40.0, entries=led)
    assert before["out_of_sample"] is True and before["ratio"] == 1.25
    after = G.F.log_estimate("r", "i", {"at": "2026-11-04T16:00:00+00:00", "likely_usd": 40.4}, 40.0, entries=led)
    assert after["out_of_sample"] is False
    assert len((tmp_path / "log.jsonl").read_text().splitlines()) == 1     # a rerun replaces its row


def test_a_partial_set_is_not_analysed(stage2):
    G.do_scope(None)
    _reply("I1", "claude", "Supported")
    with pytest.raises(G.F.P.Stop, match="partial set"):
        G.agree()


def test_the_interval_resamples_answers_not_sentences():
    pairs = [{"answer": "A", "v8": "BACKED", "k": "BACKED"}] * 9 + [{"answer": "B", "v8": "BACKED", "k": "NOT BACKED"}]
    lo, hi = G.interval(pairs, "k")
    assert lo == 0.0 and hi == 1.0            # two answers: a resample is all A, all B, or both
    assert G.interval([p for p in pairs if p["answer"] == "A"], "k") is None


def test_the_committed_counts_never_pair_an_item_id_with_its_answer():
    out = {"agreement": {"k": {"disagreements": {"d": [{"answer": "A/Claude", "item": "I1", "sentence": 0}]}}},
           "not_judged": {"detail": [{"item": "I2", "answer": "B/Gemini", "sentence": 1, "judges": ["claude"]}]}}
    c = G.committed(out)
    assert c["agreement"]["k"]["disagreements"]["d"] == [{"answer": "A/Claude", "sentence": 0}]
    assert c["not_judged"]["detail"] == [{"item": "I2", "judges": ["claude"]}]
    assert out["agreement"]["k"]["disagreements"]["d"][0]["item"] == "I1"          # the private copy is untouched
