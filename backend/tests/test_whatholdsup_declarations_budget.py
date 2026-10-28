"""The declarations budget counts agent declarations, not not_added_cap lines.

Post-study, mid-rerun tool fix (2026-10-28). WHU-S01r's readers' list carried
"Not added: ... the page's limit for declarations was reached" lines, and the
preflight counted them against the very budget whose being full put them there.
A not_added_cap line follows from the additions or declarations cap, not from an
agent's choice; out_of_scope and not_material (and relevance not established,
declared as one of those) still count.

The declarations are made by the real coverage_check.declare and checked by the
real coverage_check.preflight_rows, on the synthetic abstract of the fix 2
coverage tests (10-11 page sentences with the list: budget min(10, 20%) = 2).

COUNTERFACTUAL. Count every declaration again (decls[budget:] in place of
counted[budget:]) and t_cap_lines_are_not_counted goes red; count nothing
(COUNTED = ()) and t_agent_declarations_still_count goes red.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import coverage_check as C                    # noqa: E402
from test_whatholdsup_fix2_coverage import (  # noqa: E402,F401  (case is a fixture)
    ABSTRACT, HELD, _rows, case)

SMALL = ["The test makes little to no difference to all-cause mortality at six months, the review found."] + \
        ["Filler %d." % i for i in range(5)]   # with the heading and 3-4 lines, 10-11 sentences: budget 2


def _units():
    return [u for u in C.units_of({"id": "S001"}, ABSTRACT, []) if "makes little" not in u["text"]]


def _declare(case, states, by="Claude Code"):
    for u, state in zip(_units(), states):
        if state == "out_of_scope":
            C.declare("x", C.unit_key(u), state, "about speed, not deaths", by,
                      element="reduce deaths among adults", case=case)
        else:
            C.declare("x", C.unit_key(u), state, "over the declarations budget (2)", by, case=case)


def _list_row(case):
    page = SMALL + [C.HEADING] + [d["sentence"] for d in C.declarations("x", HELD, case)]
    return _rows(case, page)[C.ROW_LIST]


def test_cap_lines_are_not_counted_against_the_budget(case):
    assert len(_units()) >= 4
    _declare(case, ["out_of_scope", "out_of_scope", "not_added_cap", "not_added_cap"])
    r = _list_row(case)
    assert r[1] == C.OK, r
    assert "4 declared finding(s)" in r[2] and "2 counted against the budget of 2" in r[2]


def test_agent_declarations_still_count(case):
    _declare(case, ["out_of_scope", "out_of_scope", "out_of_scope", "not_added_cap"])
    r = _list_row(case)
    assert r[1] == C.BAD and "1 declaration(s) past the budget of 2" in r[2]


def test_not_material_counts_too(case):
    _declare(case, ["out_of_scope", "not_material", "not_material"])
    assert _list_row(case)[1] == C.BAD
