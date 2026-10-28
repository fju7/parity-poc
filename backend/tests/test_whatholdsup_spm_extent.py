"""coverage_check / judgements: where an IPCC SPM statement ends.

Post-study, mid-rerun tool fix (2026-10-28). An SPM statement ran to the next
numbered statement, so a figure caption printed between two statements was read
as part of the first (WHU-S07r): the caption's words, and any confidence term in
it, became the statement's. It now ends at the next numbered statement, a section
heading, or a "Figure SPM." / "Table SPM." caption, whichever comes first. A
caption named inside the statement's own brackets is a reference, not an end.

The page is synthetic; coverage_check.groups_of, units_of and
judgements.candidates_of run unchanged on it.

COUNTERFACTUAL. Make _spm_end return END and t_caption / t_heading go red; drop
the bracket depth (`if not depth:` -> `if True:`) and t_bracketed_reference
goes red.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import coverage_check as C   # noqa: E402
import judgements as J       # noqa: E402

A1 = ("A.1 Urban areas concentrate exposure to heat and flooding, and observed impacts on "
      "infrastructure have increased (high confidence). {6.2, 6.3; Figure SPM.2}")
CAPTION = ("Figure SPM.1 | Projected changes in urban heat. Panel (a) shows observed trends; "
           "panel (b) shows projections with very high confidence under every scenario.")
A2 = "A.2 Compact urban form reduces transport energy use per person (medium confidence)."
HEADING = "B. Options for Adaptation and Mitigation"
B1 = "B.1 Green infrastructure can reduce urban heat in many settings (high confidence)."
B2 = "B.2 Integrated planning lowers emissions and risks together (medium evidence, high agreement)."
B3 = "B.3 Early warning systems reduce deaths from heat waves (high confidence)."

PAGE = " ".join(["Summary for Policymakers", A1, CAPTION, A2, HEADING, B1, B2, B3])


def _groups():
    kind, groups = C.groups_of(PAGE)
    assert kind == "summary"
    return {section: PAGE[s:e] for s, e, section in groups}


def test_a_statement_ends_at_a_figure_caption():
    g = _groups()
    assert g["SPM A.1"].strip() == A1
    assert "Projected changes" not in g["SPM A.1"]


def test_a_statement_ends_at_a_section_heading():
    g = _groups()
    assert g["SPM A.2"].strip() == A2
    assert "Options for Adaptation" not in g["SPM A.2"]


def test_a_caption_named_in_the_statements_own_brackets_is_not_its_end():
    """A.1's reference block names Figure SPM.2; the statement keeps it."""
    assert _groups()["SPM A.1"].rstrip().endswith("Figure SPM.2}")


def test_the_next_numbered_statement_still_ends_one():
    g = _groups()
    assert g["SPM B.1"].strip() == B1 and g["SPM B.2"].strip() == B2


def test_judgement_candidates_take_the_bounded_extent():
    """The caption's 'very high confidence' is not A.1's."""
    cands = {c["section"]: c for c in J.candidates_of("S001", PAGE)}
    s, e = cands["SPM A.1"]["at"]
    assert "very high confidence" not in PAGE[s:e]
    assert PAGE[s:e].strip() == A1


def test_coverage_units_take_the_bounded_extent():
    s = PAGE.index(A1)
    units = C.units_of({"id": "S001"}, PAGE, [[s + 10, s + 40]])
    texts = " ".join(u["text"] for u in units)
    assert "observed impacts on infrastructure" in texts
    assert "Projected changes in urban heat" not in texts
