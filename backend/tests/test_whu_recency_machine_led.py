"""A recency finding with no body sentence to rule on needs no person (advisor's ruling 3 on P169). $0, offline.

WHU-OT1-01d's preflight STOPped on "recency findings attached" for its WHO guideline study (fa0743110-rec-6) and for
Marcolino 2018 (rec-7): RECENCY_UNMATCHED, "until a person attaches it". Under lean, the findings step's ruling.py
gate settles both by code (lean_editions, rule 3b): the WHO guideline is tied to the held S006 by its URL and its
recency line goes on the page; Marcolino is tied to no held source and is counted and recorded. The run stopped at
omissions, before the findings step, so neither had been settled.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
SLUG = "whu-lean-orch-t1-q1-01d"
CASE = ROOT / "issues" / "WHU-OT1-01d-whu-lean-orch-t1-q1-01d"


@pytest.fixture(autouse=True)
def _lean(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")


def _studies():
    gate = CASE / "draft" / ("%s.html.gate.json" % SLUG)
    if not gate.exists():
        pytest.skip("01d records not present")
    rep = json.loads(gate.read_text(encoding="utf-8"))
    return {s["name"]: s for s in rep["recency"]["studies"]}


def _view():
    import lean_editions as LE
    srcs = json.loads((CASE / "sources.json").read_text(encoding="utf-8"))["sources"]
    run = json.loads((CASE / "orchestrator" / "run_paid.json").read_text(encoding="utf-8"))
    held = {s["id"] for s in run["sources"]["sources"] if s.get("held")}
    return LE.holdings_view(srcs, held)


def _decide(monkeypatch, study):
    import lean_editions as LE
    monkeypatch.setattr(LE, "_append", lambda case, rec: rec)        # never writes the case's records
    monkeypatch.setattr(LE, "decisions", lambda case: [])
    rows = json.loads((CASE / "bindings.json").read_text(encoding="utf-8"))["bindings"]
    view = _view()
    sid, how = LE.match(SLUG, study, view, rows)
    return sid, how, LE.decide(SLUG, CASE, study, sid, view, rows, {}, None, matched_by=how)


def test_who_guideline_is_settled_by_code_with_its_recency_line(monkeypatch):
    import lean_editions as LE
    st = next(s for n, s in _studies().items() if n.startswith("WHO guideline"))
    sid, how, d = _decide(monkeypatch, st)
    assert sid == "S006" and how.startswith("identifier")
    assert d["outcome"] == LE.UNKNOWN_LINE and d["searched"]
    assert d["sentence"].startswith("Our recency check (searched: ")
    f = {"id": "fa0743110-rec-6", "kind": "recency"}
    LE.settle_finding(f, d)
    assert f["decision"] == "judgement" and f["by"] == LE.BY          # code, not a person


def test_unheld_marcolino_is_counted_not_named(monkeypatch):
    import lean_editions as LE
    st = next(s for n, s in _studies().items() if n.startswith("Marcolino"))
    sid, _how, d = _decide(monkeypatch, st)
    assert sid is None and d["outcome"] == LE.UNTIED and d["sentence"] is None
    f = {"id": "fa0743110-rec-7", "kind": "recency"}
    LE.settle_finding(f, d)
    assert f["decision"] == "judgement" and f["by"] == LE.BY


def test_settled_recency_finding_leaves_the_attached_row(monkeypatch):
    import findings as F
    opens = [{"id": "fa0743110-rec-6", "kind": "recency",
              "study": "WHO guideline: Recommendations on Digital Interventions for Health System Strengthening"}]
    assert F._unmatched_recency(SLUG, opens, {}) != []                 # undecided: still on the row
    have = {"fa0743110-rec-6": {"id": "fa0743110-rec-6", "decision": "judgement"}}
    assert F._unmatched_recency(SLUG, opens, have) == []               # settled by code: off it


def test_attached_row_names_code_under_lean():
    import inspect
    import findings as F
    src = inspect.getsource(F.check)
    assert "not yet settled by code (ruling.py gate, lean rule 3b" in src
