"""A headline unit whose page statement a later step removed (advisor's ruling 3 on P152, 2026-11-26).

The fresh Q1-01 (WHU-OT1-01b) stopped its $0 preflight on "headline conclusions accounted for": 2 S003 units with no
state (S003@5592-5764, antenatal care; S003@6825-7045, vaccination attendance). Cause: coverage had decided both as
USED -- each was bound to a page sentence -- and the overstatement step's lean fail-safe later removed both
sentences (bindings off_page_by failsafe:overstatement:...). Coverage runs once, after premise reading (P143); nothing
re-decided a unit after a later removal. Now such a unit is code's own readers'-list line (coverage_check.REMOVED:
found in our sources, not stated on this page), computed from bindings.json by load(), never written to
coverage.json, and not counted against the declarations budget.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import coverage_check as C  # noqa: E402

ABSTRACT = ("Background: x. Objectives: y. Main results: For health service use, TCC mobile telephone reminders may "
            "increase use of antenatal care slightly (low-certainty evidence). TCCMD may increase attendance for "
            "vaccinations (low-certainty evidence). Authors' conclusions: TCCMD may improve some outcomes.")
UNIT_A = "For health service use, TCC mobile telephone reminders may increase use of antenatal care slightly"


@pytest.fixture
def case(tmp_path, monkeypatch):
    import ruling as R
    import premise as PM
    import lean
    c = tmp_path / "WHU-OT1-99-whu-x"
    c.mkdir()
    (c / "issue.json").write_text(json.dumps({"slug": "whu-x"}))
    monkeypatch.setattr(R, "held_texts", lambda slug: {"S003": ABSTRACT})
    monkeypatch.setattr(PM, "load", lambda slug: {"what_the_sources_show": {"sources": ["S003"]}})
    monkeypatch.setattr(C, "_sources", lambda slug: [{"id": "S003", "type": "review"}])
    monkeypatch.setattr(lean, "enabled", lambda: False)
    return c


def _bindings(c, on_page):
    row = {"sentence": "Reminders sent by mobile phone may slightly increase antenatal care.", "source_id": "S003",
           "span": UNIT_A, "on_page": on_page}
    if not on_page:
        row["off_page_by"] = "failsafe:overstatement:c5f61ad2:4785e15f83fe50ce"
    (c / "bindings.json").write_text(json.dumps({"bindings": {"a": row}}))


def test_a_unit_whose_statement_was_removed_is_declared_by_code(case):
    _bindings(case, on_page=False)
    got = C.removed_units(case)
    assert len(got) >= 1
    k, d = next((k, d) for k, d in got.items() if UNIT_A[:40] in ABSTRACT[int(k.split("@")[1].split("-")[0]):])
    assert d["state"] == C.REMOVED and d["removed_by"] == ["failsafe:overstatement:c5f61ad2:4785e15f83fe50ce"]
    assert C.load(case)["declarations"][k]["state"] == C.REMOVED
    assert "declarations" not in json.loads((case / "bindings.json").read_text())   # nothing written
    assert not (case / C.RECORD).exists()                                            # never written to coverage.json
    assert C.REMOVED not in C.COUNTED                                                # not against the budget


def test_a_unit_still_stated_on_the_page_is_not_declared(case):
    _bindings(case, on_page=True)
    assert C.removed_units(case) == {}


def test_an_existing_decision_is_kept_and_writers_read_raw(case):
    _bindings(case, on_page=False)
    k = next(iter(C.removed_units(case)))
    (case / C.RECORD).write_text(json.dumps({"units": [], "declarations": {k: {"state": "not_material"}}}))
    assert C.load(case)["declarations"][k]["state"] == "not_material"
    assert C.load(case, raw=True)["declarations"] == {k: {"state": "not_material"}}


def test_the_line_reads_as_the_ruling_says():
    line = C.declaration_sentence(C.REMOVED, "may increase use of antenatal care slightly", "Source 3", None)
    assert line.startswith("Not added: “may increase") and "found in our sources, not stated on this page" in line
