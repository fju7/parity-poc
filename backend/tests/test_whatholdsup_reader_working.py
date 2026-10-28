"""Readers'-list reasons never show the ruling model's working.

Post-study, mid-rerun tool fix 13 (2026-10-28). Fix 8 dropped sentences STARTING
"Step N:", but WHU-S01r's reasons also carried working mid-sentence: "Step 2 also
fails: ..." and "Step 2 is therefore not reached." Any sentence that mentions
"Step" followed by a number is now working; when nothing else is left, the line
gives the standard outcome phrase of fix 12.

Records are written by the real omissions.record and coverage_check.declare; the
lines by the real coverage_check.declarations.

COUNTERFACTUAL. Go back to fix 8's filter (not _STEP.match) and t_working goes
red; drop the empty-line fallback in line_reason and t_all_working goes red.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import coverage_check as C    # noqa: E402
import omissions as O         # noqa: E402
import source_ledger as L     # noqa: E402

SPAN = "Investment in public transport can further support a shift to less intensive modes (high confidence)."
TEXT = "Section 1. Preamble text here. " + SPAN + " Closing text."
HELD = {"S003": TEXT}
ALSO_FAILS = "Step 2 also fails: the page already reports the direction of effect."
NOT_REACHED = "Step 2 is therefore not reached."
CONCLUSION = "It concerns transit, not layout."


@pytest.fixture
def case(tmp_path, monkeypatch):
    import source_store
    monkeypatch.setattr(source_store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(C, "_sources", lambda slug: [{"id": "S003", "title": "WGII Chapter 6"}])
    return tmp_path


def _f():
    a = TEXT.index(SPAN)
    return {"source": "S003", "at": [a, a + len(SPAN)], "held_quote": SPAN, "origin": "S003-01"}


def _line(case, outcome, reason, **kw):
    O.record(case, _f(), outcome=outcome, reason=reason, by="p", held_text=TEXT,
             element="layout and pricing", **kw)
    [d] = C.declarations("x", HELD, case)
    s = d["sentence"]
    assert len(L.sentences(s)) == 1
    return s


@pytest.mark.parametrize("working", [ALSO_FAILS, NOT_REACHED, "The step 3 test is not met."])
def test_a_sentence_mentioning_step_n_is_working(working):
    assert C.one_line(working) == ""
    assert C.one_line("%s %s" % (CONCLUSION, working)) == CONCLUSION.rstrip(".")


@pytest.mark.parametrize("reason", [
    ALSO_FAILS, NOT_REACHED,
    "Step 1: The finding is in scope. %s" % ALSO_FAILS,
    "Step 1: The finding is in scope. %s" % NOT_REACHED,
    "%s\n%s" % (ALSO_FAILS, NOT_REACHED)])
@pytest.mark.parametrize("outcome,phrase", [(O.NOT_MATERIAL, "Judged not material"),
                                            (O.OUT_OF_SCOPE, "Judged outside this question")])
def test_all_working_gives_the_standard_phrase(case, reason, outcome, phrase):
    s = _line(case, outcome, reason)
    assert s.endswith("; %s." % phrase) and "Step" not in s


def test_working_after_a_conclusion_is_dropped(case):
    s = _line(case, O.NOT_MATERIAL, "%s %s" % (CONCLUSION, NOT_REACHED))
    assert s.endswith("; %s" % CONCLUSION) and "Step" not in s


def test_a_reason_for_reader_that_is_working_falls_back_too(case):
    s = _line(case, O.NOT_MATERIAL, CONCLUSION, reason_for_reader=ALSO_FAILS)
    assert s.endswith("; Judged not material.")


def test_declare_with_working_only(case):
    C.declare("x", "S003@%d-%d" % tuple(_f()["at"]), "not_material", NOT_REACHED, "p", case=case)
    [d] = C.declarations("x", HELD, case)
    assert d["sentence"].endswith("; Judged not material.")
