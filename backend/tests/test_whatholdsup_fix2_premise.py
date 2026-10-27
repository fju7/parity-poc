"""Fix 2, step 2: the premise's declared scope (post-study, 2026-10-27).

docs/whu-fix2-omission-rulings-design.md, section 2.4.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import premise as PM    # noqa: E402

QUESTION = "Does involving the wider public in making climate policy affect whether the policies win backing?"


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(PM, "case_dir", lambda slug: tmp_path)
    (tmp_path / "issue.json").write_text(json.dumps({"question": QUESTION}))
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "access": {"state": "full_text_held", "on": "2026-10-22"}},
        {"id": "S002", "access": {"state": "full_text_held", "on": "2026-10-23"}}]}))
    return tmp_path


def _premise(case, scope):
    (case / "premise.json").write_text(json.dumps({"scope": scope}))


def test_the_template_carries_an_empty_scope():
    s = PM.TEMPLATE["scope"]
    assert s["covers"] == "" and s["out"] == [] and "BEFORE any source" in s["_note"]


def test_no_scope_warns_and_never_stops(case):
    _premise(case, PM.TEMPLATE["scope"])
    [row] = PM.scope_rows("x")
    assert row[1] == PM.WARN and "only the question's own words" in row[2]


def test_scope_written_before_the_first_source_is_ok(case):
    _premise(case, {"covers": "backing and results", "out": [{"what": "how assemblies should be designed",
                                                                "why": "a prescription, not an effect"}],
                    "by": "Claude Code", "written_at": "2026-10-22T00:01:00Z"})
    [row] = PM.scope_rows("x")
    assert row[1] == PM.OK and "1 out-of-scope entry" in row[2]


def test_scope_written_after_a_source_was_held_warns(case):
    _premise(case, {"covers": "backing", "out": [], "by": "Claude Code", "written_at": "2026-10-24T09:00:00Z"})
    [row] = PM.scope_rows("x")
    assert row[1] == PM.WARN and "after the first source was held (2026-10-22)" in row[2]


def test_scope_of_returns_the_question_and_declared_entries(case):
    _premise(case, {"covers": "backing", "out": [{"what": "design of assemblies", "why": "w"}, {"what": ""}],
                    "written_at": "2026-10-21"})
    s = PM.scope_of("x")
    assert s["question"] == QUESTION and s["covers"] == "backing"
    assert [o["what"] for o in s["out"]] == ["design of assemblies"]


def test_the_scope_row_is_on_the_premise_board(case):
    _premise(case, {"covers": "", "out": []})
    labels = [r[0] for r in PM.preflight_rows("x")]
    assert labels[-1] == "scope declared"
