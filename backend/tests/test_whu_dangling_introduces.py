"""A later sentence that introduces a term itself does not point at nothing (P203, after WHU-OT1-04e: the audit
stopped on CDR and CO2 in sentences reading 'carbon dioxide removal (CDR)' and 'carbon dioxide (CO2)'). $0."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import applied_check as AC  # noqa: E402


@pytest.mark.parametrize("term,sentence,want", [
    ("CDR", "but carbon dioxide removal (CDR) will also have an important role", True),
    ("CO2", "unavoidable for reaching net zero carbon dioxide (CO2) or net zero GHG emissions", True),
    ("IPCC", "the Intergovernmental Panel on Climate Change (IPCC) says", True),
    ("IPCC", "The IPCC also states that CDR will be necessary", False),
    ("CDR", "CDR (carbon dioxide removal) is", False),               # only the standard form; the safe direction
    ("CDR", "the role of CDR (see [2])", False),
    ("GHG", "net zero CO2 (or GHG) emissions", False),
    ("CDR", "results [3] (CDR)", False),
])
def test_introduces(term, sentence, want):
    assert AC.introduces(term, sentence) is want


def test_04e_only_the_unintroduced_term_is_still_a_finding(monkeypatch):
    import publish as P
    import source_store as store
    case = ROOT / "issues" / "WHU-OT1-04e-whu-lean-orch-t1-q1-04e"
    if not (case / "draft" / "whu-lean-orch-t1-q1-04e.html").exists():
        pytest.skip("04e records not present")
    monkeypatch.setenv("WHU_LEAN", "1")
    found = AC.dangling(case, (case / "draft" / "whu-lean-orch-t1-q1-04e.html").read_text(encoding="utf-8"))
    assert [f["term"] for f in found] == ["IPCC"]
