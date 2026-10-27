"""Fix 2, step 3: what code decides about an omitted finding (post-study, 2026-10-27).

docs/whu-fix2-omission-rulings-design.md, sections 2 and 2.4. No model here:
these are the decisions no model may make.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import audit_stage as A      # noqa: E402
import omissions as O        # noqa: E402

TEXT = ("Section 1. Changes in layout could reduce emissions in developed countries (high confidence). "
        "Investment in public transport can further support a shift to less intensive modes (high confidence). "
        "Some changes could lead to induced demand (medium confidence).")
HELD = {"S003": TEXT}
OMITTED = "Investment in public transport can further support a shift to less intensive modes"
S03_Q = ("Does involving the wider public, such as community groups, businesses, young people, workers and "
         "Indigenous communities, in making climate policy affect whether the policies win political backing "
         "and get results?")


def test_a_finding_in_the_held_text_gets_verified_offsets():
    f = O.precheck({"source": "S003", "quote": OMITTED, "origin": "S003-13"}, HELD)
    s, e = f["at"]
    assert TEXT[s:e] == OMITTED and f["held_quote"] == OMITTED
    assert f["held_sha256"] == O.sha(TEXT) and f["quote_sha256"] == O.sha(OMITTED)
    # typography folded, as every quotation check folds it
    g = O.precheck({"source": "S003", "quote": "“" + OMITTED.replace("-", "–") + "”"}, HELD)
    assert g.get("at") == [s, e]


def test_not_in_source_is_decided_by_code():
    f = O.precheck({"source": "S003", "quote": "Public transport always halves emissions."}, HELD)
    assert f["outcome"] == O.NOT_IN_SOURCE and "not in the held text of S003" in f["why"]
    assert O.precheck({"source": "S999", "quote": OMITTED}, HELD)["outcome"] == O.NOT_IN_SOURCE
    assert O.precheck({"source": "S003", "quote": ""}, HELD)["outcome"] == O.NOT_IN_SOURCE


def test_not_in_source_rests_on_the_real_locate(monkeypatch):
    monkeypatch.setattr(A, "locate", lambda q, hay: (0, 5))
    assert "outcome" not in O.precheck({"source": "S003", "quote": "Public transport always halves."}, HELD)


def test_overlapping_findings_from_one_source_are_merged():
    a = O.precheck({"source": "S003", "quote": OMITTED, "origin": "S003-13"}, HELD)
    b = O.precheck({"source": "S003", "quote": "public transport can further support a shift", "origin": "S003-14"},
                   HELD)
    c = O.precheck({"source": "S003", "quote": "Some changes could lead to induced demand", "origin": "S003-15"},
                   HELD)
    m = O.fill_quotes(O.merge([a, b, c]), HELD)
    assert [x["origins"] for x in m] == [["S003-13", "S003-14"], ["S003-15"]]
    assert m[0]["held_quote"] == OMITTED


def test_a_scope_element_must_be_words_of_the_question_or_a_scope_out_entry():
    scope = {"question": S03_Q, "covers": "", "out": [{"what": "how assemblies should be designed",
                                                       "why": "a prescription, not an effect"}]}
    assert O.scope_element_ok("affect whether the policies win political backing and get results", scope)[0]
    assert O.scope_element_ok("affect whether … get results", scope)[0]
    assert O.scope_element_ok("how assemblies should be designed", scope)[0]
    ok, why = O.scope_element_ok("the cost-effectiveness of deliberation", scope)
    assert not ok and "neither the question nor a scope.out entry" in why
    assert not O.scope_element_ok("policies", scope)[0]                 # one word names nothing
    assert not O.scope_element_ok("get results … affect whether", scope)[0]   # order matters


def test_the_record_holds_offsets_and_hashes_and_no_source_text(tmp_path):
    f = O.fill_quotes(O.merge([O.precheck({"source": "S003", "quote": OMITTED, "origin": "S003-13"}, HELD)]), HELD)[0]
    e = O.record(tmp_path, f, outcome=O.OUT_OF_SCOPE, reason="a prescription, not an effect",
                 by="ruling model claude-opus-5-5", element="how assemblies should be designed", ruling="r1")
    pub = json.loads((tmp_path / O.RECORD).read_text())["omissions"]
    assert pub == [e] and e["at"] == f["at"] and e["quote_sha256"] == O.sha(OMITTED)
    assert O.leaks_source_text(tmp_path, HELD) == []
    priv = [json.loads(l) for l in (tmp_path / "rulings" / O.PRIVATE).read_text().splitlines()]
    assert priv[0]["quote"] == OMITTED
    # a second decision on the same finding replaces the first
    O.record(tmp_path, f, outcome=O.ADD, reason="r", by="b")
    assert [x["outcome"] for x in json.loads((tmp_path / O.RECORD).read_text())["omissions"]] == [O.ADD]


def test_the_leak_guard_finds_source_text_in_the_committed_record(tmp_path):
    (tmp_path / O.RECORD).write_text(json.dumps({"omissions": [{"reason": OMITTED}]}))
    assert O.leaks_source_text(tmp_path, HELD)


def test_budgets():
    assert O.add_budget(100) == 8 and O.add_budget(40) == 6 and O.add_budget(5) == 0
    assert O.declaration_budget(100) == 10 and O.declaration_budget(30) == 6
