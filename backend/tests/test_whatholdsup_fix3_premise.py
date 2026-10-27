"""Fix 3, step 1: the premise states its evidence standard (post-study, 2026-10-27)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import premise as PM    # noqa: E402


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(PM, "case_dir", lambda slug: tmp_path)
    (tmp_path / "issue.json").write_text(json.dumps({"question": "Does planning help places cope?"}))
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "access": {"state": "full_text_held", "on": "2026-10-22"}}]}))
    return tmp_path


def _premise(case, es, scope=None):
    (case / "premise.json").write_text(json.dumps({"evidence_standard": es, "scope": scope or {}}))


def test_the_template_carries_the_field():
    es = PM.TEMPLATE["evidence_standard"]
    assert es["weighs"] == [] and es["when_they_differ"] == "state both" and "BEFORE any source" in es["_note"]


def test_missing_warns(case):
    _premise(case, PM.TEMPLATE["evidence_standard"])
    [row] = PM.evidence_standard_rows("x", held_assessments=[])
    assert row[1] == PM.WARN


def test_measured_only_with_a_held_assessment_stops_unless_scoped_out(case):
    _premise(case, {"weighs": ["measured"], "written_at": "2026-10-21"})
    [row] = PM.evidence_standard_rows("x", held_assessments=["S003"])
    assert row[1] == PM.BAD and "S003" in row[2]
    _premise(case, {"weighs": ["measured"], "written_at": "2026-10-21"},
             scope={"out": [{"what": "expert assessments", "why": "the question is about measured effects only"}]})
    assert PM.evidence_standard_rows("x", held_assessments=["S003"])[0][1] == PM.OK
    assert PM.evidence_standard_rows("x", held_assessments=[])[0][1] == PM.OK


def test_both_written_before_the_first_source_is_ok_and_after_warns(case):
    _premise(case, {"weighs": ["measured", "assessed"], "written_at": "2026-10-21T09:00:00Z"})
    assert PM.evidence_standard_rows("x", held_assessments=["S003"])[0][1] == PM.OK
    _premise(case, {"weighs": ["measured", "assessed"], "written_at": "2026-10-23"})
    row = PM.evidence_standard_rows("x", held_assessments=["S003"])[0]
    assert row[1] == PM.WARN and "after the first source was held" in row[2]


def test_the_row_is_on_the_premise_board(case):
    _premise(case, {"weighs": []})
    assert [r[0] for r in PM.preflight_rows("x")][-1] == "evidence standard declared"


def test_replay_s08_held_chapter_is_an_assessment():
    if not list((ROOT / "issues").glob("WHU-S08-*/bindings.json")):
        pytest.skip("the study's records are private and not here")
    held = PM._holds_assessment("settlement-planning-climate-resilience")
    if not held:
        pytest.skip("the held texts are not here")
    assert "S003" in held
