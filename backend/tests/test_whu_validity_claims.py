"""The claim definition for future rounds (study/whu-reliability/next_phase/claims.py, validity plan §6). Offline."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_c = importlib.util.spec_from_file_location("validity_claims", ROOT / "study" / "whu-reliability" / "next_phase" / "claims.py")
C = importlib.util.module_from_spec(_c)
_c.loader.exec_module(C)
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))


@pytest.mark.parametrize("text,ctx,prot,want", [
    ("Outside this question: the review also reports costs [3].", "", None, "out_of_scope"),
    ("The question is whether X reduces Y in adults over 65.", "", None, "question"),
    ("We drew on two reviews and one guideline published since 2020 [1][2].", "", None, "process"),
    ("I searched PubMed and Google Scholar for trials since 2015 [4].", "", None, "process"),
    ("We found no trial in children under 5 [2].", "", None, "claim"),
    ("This report relied mainly on the 2023 Cochrane review [1].", "", None, "process"),
    ("Mobile tracking improved adherence by 12% in 3 trials [2].", "", None, "claim"),
    ("Vitamin D had no effect on falls in 8 trials [5].", "## Further reading\n", None, "out_of_scope"),
    ("Anything at all with 3 numbers [1].", "", "reading", "process"),
    ("## Results in 2024", "", None, "furniture"),
])
def test_kinds(text, ctx, prot, want):
    assert C.kind(text, ctx, prot) == want


def test_the_copies_agree_with_whus_patterns_while_meant_to():
    import bindings as B
    assert C.FINDING.pattern == B.STATES_FINDING.pattern
    assert C.DECLARATION.pattern == B.DECLARATION_LEAD.pattern
    # the question pattern adds "your" for the tools; otherwise WHU's
    assert C.QUESTION.pattern.replace("|your", "") == B.QUESTION_RESTATEMENT.pattern
