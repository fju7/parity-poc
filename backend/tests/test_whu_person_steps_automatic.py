"""Lean: the person steps become automatic, fail-safe outcomes (advisor's ruling 4 on P171-P176, 2026-11-27).

No model is called; the fakes answer only from the prompt (test_whatholdsup_fix2_ruling's fixture, reused).
  - unusable omission ruling -> onto the readers' list as declared, counted against the budget
  - refused scope element    -> the declaration counts against the budget
  - declarations over budget -> Not Ready (an honest stop)
  - NOT_MATERIAL on a SERIOUS objection that CHANGES the conclusion -> not accepted; the conclusion sentence is
    withdrawn (tested separately below)
  - licence-barred source    -> refused and recorded
  - failed audit read        -> the sentence is withheld (audit_stage, lean branch)
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

_spec = importlib.util.spec_from_file_location("fix2_fixture", Path(__file__).parent / "test_whatholdsup_fix2_ruling.py")
FX = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FX)

import coverage_check as C    # noqa: E402
import lean_failsafe as LF    # noqa: E402
import omissions as O         # noqa: E402
import ruling as R            # noqa: E402
import source_advocate as SA  # noqa: E402

OTHER = "Some changes could lead to induced demand (medium confidence)."
NOT_MATERIAL = {"in_scope": True, "material": False, "outcome": "NOT_MATERIAL", "reason": "r"}


@pytest.fixture
def lean_on(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")


def _no_person(tmp_path):
    return not (tmp_path / "rulings" / R.FOR_PERSON).exists()


def test_an_unusable_ruling_reply_is_declared_and_counted(tmp_path, monkeypatch, lean_on):
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED)])

    def broken(*a, **k):
        raise R.RulingError("omission reply is not JSON: 'garbled'")
    monkeypatch.setattr(R, "rule", broken)
    [d] = FX._run(tmp_path, FX.never)
    assert d["outcome"] == O.DECLARED_UNRULED and _no_person(tmp_path)
    [e] = O.load(tmp_path)["omissions"]
    assert e["outcome"] == O.DECLARED_UNRULED and e["by"] == R.UNRULED_BY
    [dec] = [x for x in C.declarations(FX.SLUG, FX.HELD, tmp_path) if x["state"] == C.UNRULED]
    line = C.declaration_sentence(dec["state"], dec["text"], "[1]", None)
    assert line.startswith("Not added: “") and line.endswith(C.UNRULED_TAIL + ".")
    counted, _exempt, _twice = C.budget_count([dec])
    assert counted == [dec]                                            # counted against the budget
    assert O.preflight_rows(FX.SLUG, case=tmp_path, held=FX.HELD)[0][1] == "ok"


def test_a_refused_scope_element_is_declared_and_counted(tmp_path, monkeypatch, lean_on):
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED)])
    [d] = FX._run(tmp_path, FX.Fake({"in_scope": False, "material": False, "outcome": "OUT_OF_SCOPE",
                                      "scope_element": "the economics of electric buses", "reason": "r"}))
    assert d["outcome"] == O.OUT_OF_SCOPE and d["element_refused"] == "the economics of electric buses"
    assert _no_person(tmp_path)
    [e] = O.load(tmp_path)["omissions"]
    assert e["element"] == "" and e["by"] == R.SCOPE_REFUSED_BY
    decls = [x for x in C.declarations(FX.SLUG, FX.HELD, tmp_path) if x["from"] == "omissions"]
    counted, exempt, _ = C.budget_count(decls, FX.SCOPE, tmp_path, "2026-01-01T00:00:00+00:00")
    assert len(counted) == 1 and not exempt


def test_declarations_past_the_budget_are_an_honest_stop(tmp_path, monkeypatch, lean_on):
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED), FX._obj(OTHER)])
    ds = FX._run(tmp_path, FX.Fake(NOT_MATERIAL), page_sentences=FX.PAGE[:5])    # budget min(10, 20% of 5) = 1
    assert [d["outcome"] for d in ds] == [O.NOT_MATERIAL, O.OVER_DECLARATIONS] and _no_person(tmp_path)
    row = O.preflight_rows(FX.SLUG, case=tmp_path, held=FX.HELD)[0]
    assert row[1] == "BLOCKED" and "Not Ready" in row[2] and "honest stop" in row[2]


def test_the_orchestrator_stops_at_omissions_on_an_honest_stop():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    body = src[src.index("def code_apply"):src.index("ops = AP.apply_all(ctx.case, page)")]
    assert 'step.name == "omissions"' in body and "O.OVER_DECLARATIONS" in body and "raise RunStop" in body


def test_a_licence_barred_source_is_refused_and_recorded(tmp_path, monkeypatch, lean_on):
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED)])
    assert FX._run(tmp_path, FX.never, licensed={"S003"}) == []
    assert _no_person(tmp_path)
    [e] = O.load(tmp_path)["omissions"]
    assert e["outcome"] == O.REFUSED_LICENCE and e["origins"] == ["S003-01"]
    assert O.preflight_rows(FX.SLUG, case=tmp_path, held=FX.HELD)[0][1] == "ok"


def test_without_lean_every_path_still_goes_to_a_person(tmp_path, monkeypatch):
    monkeypatch.delenv("WHU_LEAN", raising=False)
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED, changes="CHANGES")])
    [d] = FX._run(tmp_path, FX.Fake(NOT_MATERIAL))
    assert d["outcome"] == O.TO_PERSON and not _no_person(tmp_path)


def test_audit_and_acquire_have_lean_branches_with_no_person():
    a = (W / "audit_stage.py").read_text(encoding="utf-8")
    assert 'withhold(u, "bound only to source(s) whose licence forbids machine reading' in a
    assert 'withhold(u, "the audit read failed (FAILED_READ): the sentence is withheld")' in a
    q = (W / "acquire_sources.py").read_text(encoding="utf-8")
    assert 'acc["refused"] = {"why": "licence forbids machine reading"' in q


# ------------------------------------------------- NOT_MATERIAL on a SERIOUS objection that CHANGES the conclusion

def test_not_material_on_a_serious_changing_objection_withdraws_the_conclusion(tmp_path, monkeypatch, lean_on):
    adj = FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED, severity="SERIOUS", changes="CHANGES")])
    [d] = FX._run(tmp_path, FX.Fake(NOT_MATERIAL))
    assert d["outcome"] == O.WITHDRAWN and d["withdrawn"] == FX.PAGE[1] and _no_person(tmp_path)
    [r] = LF.load(tmp_path)
    assert r["sentence"] == FX.PAGE[1] and r["outcome"] == LF.OUTCOME and r["path"] == "omissions"
    # the machine's NOT_MATERIAL is not accepted: nothing declared, the advocate item not closed by it
    [e] = O.load(tmp_path)["omissions"]
    assert e["outcome"] == O.WITHDRAWN and not [x for x in C.declarations(FX.SLUG, FX.HELD, tmp_path)
                                               if x["from"] == "omissions"]
    assert not SA._closed("### " + FX._chunk(adj, "S003-01"), "objections")
    assert O.preflight_rows(FX.SLUG, case=tmp_path, held=FX.HELD)[0][1] == "ok"


def test_the_withdrawn_sentence_leaves_the_page_through_apply(tmp_path, monkeypatch, lean_on):
    from orch import apply as AP
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED, severity="SERIOUS", changes="CHANGES")])
    FX._run(tmp_path, FX.Fake(NOT_MATERIAL))
    ops = [op for _k, _at, op in AP.pending(tmp_path)]
    assert {"op": "delete", "old": FX.PAGE[1], "why": "lean fail-safe (omissions)"} in ops


def test_a_serious_objection_on_a_sentence_that_cannot_be_withdrawn_is_not_ready(tmp_path, monkeypatch, lean_on):
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED, anchor="We did not search the grey literature.",
                                             severity="SERIOUS", changes="CHANGES")])
    [d] = FX._run(tmp_path, FX.Fake(NOT_MATERIAL))
    assert d["outcome"] == O.OVER_DECLARATIONS and d["withdrawn"] is None and _no_person(tmp_path)
    assert LF.load(tmp_path) == []                                     # a protected sentence is never withdrawn
    row = O.preflight_rows(FX.SLUG, case=tmp_path, held=FX.HELD)[0]
    assert row[1] == "BLOCKED" and "Not Ready" in row[2]


def test_a_serious_objection_that_only_narrows_is_still_declared_as_before(tmp_path, monkeypatch, lean_on):
    FX._case(tmp_path, monkeypatch, [FX._obj(FX.OMITTED, severity="SERIOUS", changes="NARROWS")])
    [d] = FX._run(tmp_path, FX.Fake(NOT_MATERIAL))
    assert d["outcome"] == O.NOT_MATERIAL and LF.load(tmp_path) == []
