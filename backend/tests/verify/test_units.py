"""Unit tests for the pieces underneath the golden sets: number
normalisation (design doc §4a), citation identification, and the WHU
boundary (design doc §8)."""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
from verify.numbers import canonical_numbers  # noqa: E402
from verify.law import identify as identify_law  # noqa: E402
from verify.literature import identify as identify_lit  # noqa: E402
from verify.types import Provenance  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("paid within thirty days", {"30"}), ("within 30 calendar days", {"30"}), ("thirty (30) days", {"30"}),
    ("forty-five days", {"45"}), ("forty five days", {"45"}), ("eighteen per cent", {"18"}),
    ("18 per cent", {"18"}), ("eighteen percent", {"18"}), ("18%", {"18"}),
    ("an annual percentage rate of eighteen per cent", {"18"}),
    ("HR 0.80, 95% CI 0.72–0.90, P < 0.001", {"0.8", "95", "0.72", "0.9", "0.001"}),
    ("two-sided p=0·053 and HR 0·561", {"0.053", "0.561"}), ("enrolling 1,961 adults", {"1961"}),
    ("one hundred", {"100"}), ("two hundred and ten", {"210"}), ("two and a half", {"2.5"}),
    ("a 30-day deadline", {"30"}), ("−0.5", {"-0.5"}), ('modifier "-25"', {"25", "-25"}),
    ("CPT 99214", {"99214"}), ("30–39 minutes", {"30", "39"}), ("thirty-nine", {"39"}),
    ("one-sided alpha", set()), ("no numbers here at all", set()),
])
def test_number_forms_from_the_design_doc(text, expected):
    assert canonical_numbers(text) == expected


@pytest.mark.parametrize("cite,system,value", [
    ("42 CFR § 424.5(a)(6)", "cfr", "42:424.5(a)(6)"), ("45 C.F.R. 147.130", "cfr", "45:147.130"),
    ("Ohio Revised Code § 3901.38", "orc", "3901.38"), ("R.C. 3901.381", "orc", "3901.381"),
    ("Ohio Administrative Code § 3901-1-54", "oac", "3901-1-54"), ("OAC 3901-1-54", "oac", "3901-1-54"),
    ("CMS Claims Processing Manual, Publication 100-04, Chapter 1, Section 80.3.1", "cms_iom", "100-04:1:80.3.1"),
    ("IOM Publication 100-04, Chapter 12", "cms_iom", "100-04:12"),
    ("NCCI Policy Manual, Chapter 1, Section D", "ncci", "1:D"), ("NCCI Policy Manual, Chapter I", "ncci", "1"),
])
def test_law_identification(cite, system, value):
    ident = identify_law(cite)
    assert ident is not None and (ident.system, ident.value) == (system, value)


def test_law_identification_refuses_an_unnumbered_reference():
    assert identify_law("the Ohio Department of Insurance's claims processing regulations") is None


@pytest.mark.parametrize("raw,system,value", [
    ("https://doi.org/10.1056/NEJMoa2034577", "doi", "10.1056/nejmoa2034577"),
    ("10.1371/journal.pmed.1000097", "doi", "10.1371/journal.pmed.1000097"),
    ("https://clinicaltrials.gov/study/NCT02246621", "nct", "NCT02246621"),
    ("https://pubmed.ncbi.nlm.nih.gov/32109013/", "pmid", "32109013"),
    ("PMC7723445", "pmcid", "PMC7723445"),
])
def test_literature_identification(raw, system, value):
    ident = identify_lit(raw, Provenance.RESOLVED_FROM_HELD)
    assert (ident.system, ident.value, ident.provenance) == (system, value, Provenance.RESOLVED_FROM_HELD)


def test_nothing_under_whatholdsup_imports_the_shared_package():
    """Design doc §8: the boundary is built; WHU's own modules and verdict
    severities stay as they are until the reviewer signs off."""
    offenders = []
    for p in (BACKEND / "scripts" / "whatholdsup").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        if "from verify" in src or "import verify" in src or '"verify"' in src and "spec_from_file_location" in src:
            offenders.append(p.name)
    assert not offenders, offenders
