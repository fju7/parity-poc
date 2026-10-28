"""The readers' list carries one reader-facing line, not the ruling's working.

Post-study, mid-rerun tool fix (2026-10-28). WHU-S01r's omission reasons were
written as steps -- "Step 1: The finding is in scope. Step 2: ..." -- and the
readers' list took the first sentence, so a reader saw "Step 1: The finding is in
scope". It now takes the record's reason_for_reader if present, else the reason's
final concluding sentence, and never a sentence starting "Step N:".

The reasons below are synthetic, in S01's shape. Declarations are made by the
real omission ruling (fake model) and rendered by the real
coverage_check.declarations.

COUNTERFACTUAL. Put back the first-sentence one_line and t_s01_style goes red;
drop the Step filter (plain = parts) and t_every_sentence_is_a_step goes red; drop
reader_reason (use the reason) and t_reason_for_reader goes red.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import coverage_check as C                   # noqa: E402
import omissions as O                        # noqa: E402
import test_whatholdsup_fix2_ruling as T     # noqa: E402

S01_STYLE = ("Step 1: The finding is in scope. Step 2: It concerns the same population as the question. "
             "Step 3: It does not change what the page tells the reader. "
             "The page already reports that testing finds more cases, so this adds nothing a reader needs.")
ALL_STEPS = ("Step 1: The finding is in scope.\nStep 2: It is about the same tests.\n"
             "Step 3: Not material, because the page already reports the same direction of effect.")
FOR_READER = "the page already reports this direction of effect"


def test_s01_style_reason_gives_its_concluding_sentence():
    assert C.one_line(S01_STYLE) == ("The page already reports that testing finds more cases, "
                                     "so this adds nothing a reader needs")


def test_when_every_sentence_is_a_step_there_is_no_line():
    # Until fix 13 (2026-10-28) the last step was shown without its "Step N:"
    # label; every sentence naming a step is now working, and the readers' list
    # gives the standard outcome phrase (test_whatholdsup_reader_working.py).
    assert C.one_line(ALL_STEPS) == ""


@pytest.mark.parametrize("reason", [S01_STYLE, ALL_STEPS, "Step 1: The finding is in scope.",
                                    "step 2) In scope. Step 3 - not material."])
def test_never_a_line_starting_step_n(reason):
    assert not C._STEP.match(C.one_line(reason))


def test_a_plain_reason_is_unchanged_in_shape():
    assert C.one_line("It is about freight, which the question leaves out.") == \
        "It is about freight, which the question leaves out"


def _ruled(tmp_path, monkeypatch, **extra):
    import source_store
    T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED)])
    reply = dict(T.ADD, outcome="NOT_MATERIAL", reason=S01_STYLE, **extra)
    [d] = T._run(tmp_path, T.Fake(reply))
    assert d["outcome"] == "NOT_MATERIAL"
    monkeypatch.setattr(source_store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(C, "_sources", lambda slug: [{"id": "S003", "title": "WGII Chapter 6"}])
    [line] = C.declarations(T.SLUG, T.HELD, tmp_path)
    return line["sentence"]


def test_end_to_end_the_readers_line_is_the_conclusion(tmp_path, monkeypatch):
    s = _ruled(tmp_path, monkeypatch)
    assert "Step" not in s
    assert s.endswith("; The page already reports that testing finds more cases, so this adds nothing a reader needs.")


def test_reason_for_reader_is_used_when_present(tmp_path, monkeypatch):
    s = _ruled(tmp_path, monkeypatch, reason_for_reader=FOR_READER)
    assert s.endswith("; %s." % FOR_READER)
    [e] = O.load(tmp_path)["omissions"]
    assert e["reason"] == S01_STYLE and e["reason_for_reader"] == FOR_READER


def test_declare_for_reader_and_not_added_cap_keeps_its_cap(tmp_path):
    C.declare("x", "S003@0-90", "not_material", S01_STYLE, "a person", case=tmp_path, for_reader=FOR_READER)
    C.declare("x", "S003@91-195", "not_added_cap", "Step 1: over the declarations budget.", "a person",
              case=tmp_path, for_reader="no room")
    import unittest.mock as m
    with m.patch.object(C, "_sources", lambda slug: []):
        lines = [d["sentence"] for d in C.declarations("x", T.HELD, tmp_path)]
    assert lines[0].endswith("; %s." % FOR_READER)
    assert lines[1].endswith("; the page's limit for declarations was reached.")
