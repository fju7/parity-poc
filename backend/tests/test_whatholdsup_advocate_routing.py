"""The source advocate routes each sentence by its binding row (GAP-020).

The advocate handed a source every page sentence containing a word from the
source's title as sources.json spells it. On WHU-P04 a name mismatch misrouted
sentences silently. Now a sentence reaches the sources its binding row rests on
(the span's source, also_rests_on, premises) and no other; a sentence with no
binding to a source reaches no source, and the run reports it. No model is
called.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("source_advocate_routing_t", WHU / "source_advocate.py")
SA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SA)
import audit_stage as A  # noqa: E402

UNNAMED = "Emissions grew by 2.2% a year in the most recent decade."
IPCC_ELSEWHERE = "The IPCC's figure is lower than the one the inventory reports."
PREMISE = "So growth was faster than in the decade before."
LOOSE = "This page was drafted for a study."

SOURCES = [{"id": "S1", "title": "IPCC AR5 Synthesis Report: Summary for Policymakers", "type": "review"},
           {"id": "S2", "title": "National greenhouse gas inventory 2014", "type": "primary"},
           {"id": "S3", "title": "Global Carbon Budget", "type": "primary"}]


def rows():
    return {
        A.fingerprint(UNNAMED): {"sentence": UNNAMED, "source_id": "S1", "span": "2.2% per year"},
        A.fingerprint(IPCC_ELSEWHERE): {"sentence": IPCC_ELSEWHERE, "source_id": "S2", "span": "x"},
        A.fingerprint(PREMISE): {"sentence": PREMISE, "bucket": "judgement", "source_id": "",
                                 "premises": [{"source_id": "S3", "span": "y"}]},
    }


TEXT = " ".join([UNNAMED, IPCC_ELSEWHERE, PREMISE, LOOSE])


def test_a_sentence_reaches_the_source_it_is_bound_to_without_naming_it():
    assert "ipcc" not in UNNAMED.lower()
    routed, _ = SA.route(TEXT, rows())
    assert UNNAMED in routed["S1"]


def test_a_sentence_naming_ipcc_but_bound_elsewhere_does_not_reach_the_ipcc_source():
    routed, _ = SA.route(TEXT, rows())
    assert IPCC_ELSEWHERE not in routed.get("S1", [])
    assert routed["S2"] == [IPCC_ELSEWHERE]


def test_a_premise_source_receives_the_sentence():
    routed, _ = SA.route(TEXT, rows())
    assert routed["S3"] == [PREMISE]


def test_a_sentence_with_no_binding_reaches_no_source_and_is_reported():
    r = rows()
    r["norow"] = {"sentence": "Nothing here.", "rests_on_record": [{"path": "x"}]}
    routed, unrouted = SA.route(TEXT + " Nothing here.", r)
    assert all(LOOSE not in v and "Nothing here." not in v for v in routed.values())
    assert {u["sentence"]: u["why"] for u in unrouted} == {LOOSE: SA.NO_ROW, "Nothing here.": SA.NO_SOURCE}


def test_a_run_sends_each_source_only_its_bound_sentences_and_saves_the_unrouted(tmp_path, monkeypatch):
    d = tmp_path / "issues" / "WHU-X-demo"
    d.mkdir(parents=True)
    (tmp_path / "page.html").write_text("<html><body><p>%s</p></body></html>" % TEXT)
    monkeypatch.setattr(SA, "ROOT", tmp_path)
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: d)
    monkeypatch.setattr(SA.sl, "load", lambda slug: {"sources": SOURCES})
    monkeypatch.setattr(SA.sl, "access_of", lambda s: {"state": "machine-readable"})
    monkeypatch.setattr(SA, "binding_rows", lambda slug: rows())
    monkeypatch.setattr(A, "held_for_audit", lambda slug: {})
    import stage_cap
    monkeypatch.setattr(stage_cap, "guard", lambda stage, slug, units: None)
    sent = {}

    def call(system, user, search=False, label="", **kw):
        sent[label.split(":")[-1]] = json.loads(user)["sentences_about_you"]
        return []
    monkeypatch.setattr(SA.fc, "call", call)
    args = types.SimpleNamespace(slug="demo", page="page.html", only=None, day="2026-10-21", resume=None)
    assert SA.cmd_run(args) == 0
    assert sent == {"S1": [UNNAMED], "S2": [IPCC_ELSEWHERE], "S3": [PREMISE]}
    rd = sorted((d / "advocate" / "runs").iterdir())[-1]
    routing = json.loads((rd / "routing.json").read_text())
    assert routing["unrouted"] == [{"sentence": LOOSE, "why": SA.NO_ROW}]
