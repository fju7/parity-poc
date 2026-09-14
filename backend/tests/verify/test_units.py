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


# ---------------------------------------------------------------------------
# HEADING abstention (added 2026-09-14): a third outcome that makes FIGURE or
# SPAN mandatory instead of letting a weakened HEADING pass on its own.
# ---------------------------------------------------------------------------
from verify.bind import bind_all, bind_heading, HEADING_MIN_DISTINCTIVE  # noqa: E402
from verify.types import Document, Exists, Identifier, Resolution, Context  # noqa: E402


def _law(heading, text):
    ident = Identifier("orc", "0000.00")
    return Resolution(ident, Exists.EXISTS, heading=heading), Document(ident, "x", text)


def test_n_is_two_and_recorded():
    assert HEADING_MIN_DISTINCTIVE == 2


def test_heading_abstains_when_too_little_remains():
    res, _ = _law("Rules", "the superintendent may adopt rules")
    b = bind_heading("Ohio prompt pay statutes", res)
    assert b.abstained and not b.ok and "cannot_discriminate" in b.reason


def test_abstention_with_a_passing_figure_binds():
    res, doc = _law("Rules", "a claim shall be paid within thirty days of receipt")
    ok, bs = bind_all("clean claims paid within 30 days", res, doc, Context(state="OH"), characterisation="prompt pay")
    assert bs[0].abstained and ok


def test_abstention_with_a_failing_figure_refuses():
    res, doc = _law("Rules", "the superintendent may adopt rules")
    ok, bs = bind_all("clean claims paid within 30 days", res, doc, Context(state="OH"), characterisation="prompt pay")
    assert bs[0].abstained and not ok


def test_abstention_with_nothing_mandatory_refuses():
    res, doc = _law("Rules", "the superintendent may adopt rules")
    ok, bs = bind_all("applicable state prompt pay statutes", res, doc, Context(state="OH"), characterisation="prompt pay")
    assert bs[0].abstained and not ok and "cannot be bound" in bs[0].reason


def test_containment_is_decisive_whatever_the_count():
    ident = Identifier("nct", "NCT00000000")
    res = Resolution(ident, Exists.EXISTS, heading="A Phase 3 Study of X || MONARCH 3")
    b = bind_heading("MONARCH 3", res)
    assert b.ok and not b.abstained


def test_digit_scale_and_registry_year_from_the_mmr_run():
    """Two false refusals the first end-to-end run produced, 2026-09-14."""
    assert canonical_numbers("over 23 million children") == {"23000000"}
    assert "1200000000" in canonical_numbers("1.2 billion")
    from verify.bind import bind_figure
    from verify.types import Document, Identifier
    doc = Document(Identifier("doi", "10.1/x"), "s", "no year appears in this abstract; 12 children")
    assert not bind_figure("Smeeth 2004 studied 12 children", doc).ok
    assert bind_figure("Smeeth 2004 studied 12 children", doc, registry_text="Some title 2004").ok


# ---------------------------------------------------------------------------
# FIGURE at stated precision (ruling of 2026-09-14): the four cases, verbatim.
# ---------------------------------------------------------------------------
from verify.bind import bind_figure as _bf  # noqa: E402
from verify.types import Document as _D, Identifier as _I  # noqa: E402


def _docn(text):
    return _D(_I("doi", "10.1/x"), "s", text)


def test_figure_binds_at_stated_precision_and_refuses_otherwise():
    cochrane = _docn("138 studies (23,480,668 participants) were included")
    assert _bf("over 23 million children", cochrane).ok
    assert _bf("23 million children", cochrane).ok
    assert not _bf("24 million children", cochrane).ok
    assert _bf("over 20 million children", cochrane).ok
    hviid = _docn("657,461 children born in Denmark")
    assert not _bf("650,000 children", hviid).ok            # rounds to 660,000, not 650,000
    assert _bf("660,000 children", hviid).ok
    assert _bf("about 650,000 children", hviid).ok is False  # 'about' rounds at the stated unit too: 660,000
    assert _bf("HR 0.93", _docn("hazard ratio 0.926 (95% CI 0.85 to 1.02)")).ok
    assert not _bf("12 children", _docn("13 children were enrolled")).ok
    assert _bf("thirty days", _docn("not later than 30 days")).ok      # word-form still exact


def test_apostrophes_are_not_quotation_marks():
    from verify.bind import _QUOTE
    assert not _QUOTE.search("Wakefield's hypothesis and the children's records were reviewed")
    assert _QUOTE.search('the paper said "no causal association was found" in its abstract')


def test_space_separated_thousands_as_annals_writes_them():
    assert canonical_numbers("Participants 657 461 children born in Denmark") == {"657461"}
    assert canonical_numbers("During 5 025 754 person-years, 6517 children; 129.7 per 100 000") >= {"5025754", "6517", "129.7", "100000"}
    assert canonical_numbers("657\u2009461") == {"657461"}
    assert canonical_numbers("in 2010 and 12 children") == {"2010", "12"}
