"""The recombination shape: a DOI whose suffix repeats a page, volume or issue
number of the citation it sits in.

Jain 2015 was stored as 10.1001/jama.2015.1534 -- registrant, journal code and
year all correct, and the real first page (JAMA 2015;313(15):1534-1540) in the
suffix. It survived every check short of the registry round-trip because
every part was plausible. The extractor now carries a note on such a DOI and
the policy layer surfaces it in the refusal or flag reason. It is a FLAG, not
a refusal: 10.1093/ije/31.2.285 (volume 31, issue 2, page 285) is real.
"""
from __future__ import annotations

import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify.extract import AssertionClass as A, citation_numbers, doi_recombination, extract  # noqa: E402
from verify.policy import Held, check  # noqa: E402

JAIN = "Jain A, Marshall J, Buikema A. Autism Occurrence by MMR Vaccine Status Among US Children With Older Siblings. JAMA. 2015;313(15):1534-1540."


def test_citation_numbers_reads_volume_issue_pages_and_year():
    n = citation_numbers(JAIN)
    assert n["volume"] == {"313"} and n["issue"] == {"15"} and n["page"] == {"1534", "1540"} and n["year"] == {"2015"}


def test_the_fabricated_jain_doi_is_noted_and_the_real_one_is_not():
    assert doi_recombination("10.1001/jama.2015.1534", JAIN) == "DOI suffix repeats the citation's page 1534"
    assert doi_recombination("10.1001/jama.2015.3077", JAIN) is None      # the year alone is not a note


def test_a_real_doi_built_from_volume_issue_page_is_noted_not_refused():
    note = doi_recombination("10.1093/ije/31.2.285", "Ben-Shlomo Y, Kuh D. Int J Epidemiol. 2002;31(2):285-293.")
    assert note and "page 285" in note and "volume 31" in note


def test_digit_runs_are_compared_whole():
    # 15 (the issue) sits inside 2015 in the suffix; that is not a repeat
    assert doi_recombination("10.1001/jama.2015.3077", "JAMA. 2015;313(15):3077-3080.") == "DOI suffix repeats the citation's page 3077"
    assert doi_recombination("10.1001/jama.2015.9999", "JAMA. 2015;313(15):3077-3080.") is None


def test_the_window_is_the_citation_line_not_the_sentence():
    text = ("Jain A. JAMA. 2015;313(15):1534-1540. doi:10.1001/jama.2015.1534\n"
            "Hviid A. Ann Intern Med. 2019;170(8):513-520. doi:10.7326/M18-2101")
    notes = {c.value: c.extra for c in extract(A.IDENTIFIER, text) if c.kind == "doi"}
    assert notes["10.1001/jama.2015.1534"] == "DOI suffix repeats the citation's page 1534"
    assert notes["10.7326/m18-2101"] == ""


def test_the_note_reaches_the_verdict_on_a_gated_surface():
    text = "Jain A. JAMA. 2015;313(15):1534-1540. doi:10.1001/jama.2015.1534"
    v = check("routers.health_analyze::analyze_denial", {"t": text}, Held())
    f = next(f for f in v.refusals + v.flags if f.kind == "doi")
    assert "page 1534" in f.reason
    # handed over, it binds and carries no note: the registry vouched for it, not the shape
    v2 = check("routers.health_analyze::analyze_denial", {"t": text}, Held(identifiers=["10.1001/jama.2015.1534"]))
    doi_findings = [f for f in v2.findings if f.kind == "doi"]
    assert doi_findings and all(f.ok for f in doi_findings) and all("page" not in f.reason for f in doi_findings)
