"""Lean WHU's coverage rules (lean_coverage.py, coverage_check under lean.enabled()).

(a) is tested on the real texts round 1 took as headline units or declared
findings, copied from the held sources at the offsets their coverage.json and
omissions.json record (WHU-Q1-01..04), and on real SPM / abstract findings
from the same sources that must stay units. No model is called."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import coverage_check as C                    # noqa: E402
import lean                                   # noqa: E402
import lean_coverage as LC                    # noqa: E402
import signers                                # noqa: E402
from test_whatholdsup_declarations_budget import SMALL, _declare, _units  # noqa: E402
from test_whatholdsup_fix2_coverage import ABSTRACT, HELD, _rows, case     # noqa: E402,F401


@pytest.fixture
def lean_on():
    lean.enable(True)
    yield
    lean.enable(False)
    lean._forced = None


# ----------------------------------------------------------------- (a) the real round-1 cases

NOT_FINDINGS = {
    # WHU-Q1-01, S002 (WHO guideline): the recommendation-category legend
    "legend text": "ȺȺ recommended only in specific contexts or conditions – the intervention or option is "
                   "applicable only to the condition, setting or population specified",
    # WHU-Q1-02, S003 and the omission reason that quoted it
    "author list": "Kuper H, Saran A, White H",
    "author list ": "Authors: Hannah Kuper1, Ashrita Saran2, and Howard White2 With support from: Jill Adona, "
                    "Nina Ashley de la Cruz, Yashika Kanojia Suresh Kumar",
    # WHU-Q1-02, S002@6169-6638
    "abbreviation list": "Abbreviations 3ie International Initiative for Impact Evaluation CBR community‐based "
                         "rehabilitation CEDIL Centre for Excellence for Development Impact and Learning DFID "
                         "Department for International Development",
    # WHU-Q1-03, S001 (SPM figure text: Figure SPM.5's colour bar)
    "figure or table text": "Simulated change at 2°C global warming Simulated change at 4°C global warming 0 0.5 1 1.5 "
                            "2 2.5 3 3.5 4 4.5 5 5.5 6 6.5 7 Change (°C) 31 16 Warmer",
    # WHU-Q1-04, S004@57929-58632 (WGIII SPM axis ticks)
    "figure or table text ": "Global GHG emissions b. 2030 80 80 70 70 60 60 50 50 40 40 30 30 20 20 10 10 0 0 -10 "
                             "2010 2015 2020 2025 2030 2035 2040 2045 2050 Modelled pathways: c",
    # WHU-Q1-04, S004@57895-57928 and @112184-112216 (axis labels)
    "figure axis or legend text": "GHG emissions (GtCO2-eq yr –1) a.",
    "figure axis or legend text ": "Net global GHG emissions +50% b.",
    # WHU-Q1-03, S001@58509-58538 and @56229-56345; WHU-Q1-04 S004 footer
    "page header or footer": "Summary for Policymakers l a.",
    "page header or footer ": "See footnote 15 for definition and relation to precipitation and evapotranspiration. "
                              "15 SPM Summary for Policymakers",
    "page header or footer  ": "This pre-final-publication version of the AR6 WGIII SPM approved text is subject "
                               "to error correction.",
    # bare numbers / section references only
    "section references or bare numbers": "(high confidence) {7.4, 7.6, 7.7, 12.5, 12.6}",
}

FINDINGS = [
    # real units round 1's pages used: they must stay headline units
    "A.1.7 Global mean sea level increased by 0.20 [0.15 to 0.25] m between 1901 and 2018.",
    "The average rate of sea level rise was 1.3 [0.6 to 2.1] mm yr–1 between 1901 and 1971, increasing to 1.9 "
    "[0.8 to 2.9] mm yr–1 between 1971 and 2006, and further increasing to 3.7 [3.2 to 4.2] mm yr–1 between "
    "2006 and 2018 (high confidence).",
    "In adults with hypertension or diabetes (1 study, 3324 participants), tracking + CDSS + TCC may make little "
    "or no difference to HbA1c (MD 0.08 [‐0.27, 0.43]), total cholesterol (MD ‐2.50 [‐7.10, 2.10]).",
    "B.3 Continued global warming is projected to further intensify the global water cycle, including its "
    "variability, global monsoon precipitation and the severity of wet and dry events. {4.3, 4.4, 4.5, 8.2}",
    "Abrupt responses and tipping points of the climate system, such as strongly increased Antarctic ice-sheet "
    "melt and forest dieback, cannot be ruled out (high confidence). {1.4, 4.3, 4.4, 4.8, 5.4, 8.6}",
    "When CO2 is captured directly from the atmosphere (DACCS), or from biomass (BECCS), CCS provides the storage "
    "component of these CDR methods.",
    "EW has the potential to remove 2–4 (full range: <1 to about 100) GtCO2 yr –1, at costs ranging from USD50 "
    "to 200 (full range: USD24–578) tCO2–1.",
]


@pytest.mark.parametrize("kind", sorted(NOT_FINDINGS))
def test_round_one_furniture_is_never_a_headline_unit(kind):
    assert LC.furniture(NOT_FINDINGS[kind]) == kind.strip()


@pytest.mark.parametrize("text", FINDINGS)
def test_round_one_findings_stay_headline_units(text):
    assert LC.furniture(text) is None


def test_split_units_keeps_findings_and_names_the_furniture():
    us = [{"text": FINDINGS[0]}, {"text": NOT_FINDINGS["author list"]}]
    keep, cut = LC.split_units(us)
    assert keep == [us[0]] and cut[0]["furniture"] == "author list"


# ----------------------------------------------------------------- (b) already stated

def test_a_finding_the_page_states_is_already_stated_and_a_different_one_is_not():
    page = ["Sea level rose by 0.20 m (0.15 to 0.25 m) between 1901 and 2018, the global mean, the IPCC says.",
            "Something else entirely."]
    assert LC.already_stated(FINDINGS[0], page) == page[0]
    other = ["Global mean sea level increased by 0.30 m between 1901 and 2018."]      # a different figure
    assert LC.already_stated(FINDINGS[0], other) is None


def test_an_already_stated_declaration_is_not_on_the_readers_list(case, lean_on):
    u = _units()[0]
    C.declare("x", C.unit_key(u), "out_of_scope", "about speed, not deaths", "Claude Code",
              element="reduce deaths among adults", case=case)
    assert C.declarations("x", HELD, case)
    cov = C.load(case)
    cov["declarations"][C.unit_key(u)]["state"] = LC.ALREADY
    (case / C.RECORD).write_text(__import__("json").dumps(cov))
    assert C.declarations("x", HELD, case) == []


# ----------------------------------------------------------------- (c) the budget is a STOP

def test_past_the_budget_is_a_stop_under_lean_even_with_a_persons_sign_off(case, monkeypatch):
    monkeypatch.setattr(signers, "is_agent", lambda by: False)
    monkeypatch.setattr(signers, "check_value", lambda *a, **k: (True, "signed"))
    _declare(case, ["out_of_scope", "out_of_scope", "out_of_scope"], by="A Person")

    def row():
        page = SMALL + [C.HEADING] + [d["sentence"] for d in C.declarations("x", HELD, case)]
        return _rows(case, page)[C.ROW_LIST]
    assert row()[1] == C.OK                                  # off: a person's sign-off passes it
    lean.enable(True)
    try:
        r = row()
        assert r[1] == C.BAD and "past the budget of 2" in r[2] and "a STOP" in r[2]
    finally:
        lean.enable(False)
        lean._forced = None


# ----------------------------------------------------------------- (d) numbered citations

def test_readers_list_lines_carry_a_numbered_citation_under_lean(case, monkeypatch):
    srcs = [{"id": "S000", "title": "Another"}, {"id": "S001", "title": "The review", "also_called": ["The review"]}]
    monkeypatch.setattr(C, "_sources", lambda slug: srcs)
    _declare(case, ["out_of_scope"])
    off = C.declarations("x", HELD, case)[0]["sentence"]
    lean.enable(True)
    try:
        on = C.declarations("x", HELD, case)[0]["sentence"]
    finally:
        lean.enable(False)
        lean._forced = None
    assert "(The review)" in off and "[2]" not in off
    assert "(The review [2])" in on
