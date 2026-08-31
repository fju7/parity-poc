"""A trial's status, start date and enrolment are registry fields, not opinions.

Built 2026-08-31, an hour after test_registry_figures.py, because that checker
sees decimals and nothing else. Three of the eight findings still open on issue
two were a trial's STATUS, its START DATE and its ENROLMENT -- every one a
structured field the API returns in under a second, every one reported NOT_FOUND
by a role that searches the web:

    "HARMONIA opened on 28 March 2022."
      -> "The date 28 March 2022 does not appear in any source I could reach."
    "HARMONIA terminated with 61 patients enrolled."
      -> "No source I could reach confirms that HARMONIA was terminated..."

    NCT05207709: overallStatus TERMINATED, startDate 2022-03-28, enrolment 61.

The lesson is not "add another field". It is that a claim class you believe is
covered can be covered for one data type and silent for every other, and the
silence is indistinguishable from a pass.

These tests are mostly about what this check must REFUSE to say. It confirms
and is otherwise silent, by construction: it must never report a page wrong.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "registry_facts", ROOT / "backend" / "scripts" / "whatholdsup" / "registry_facts.py")
rfa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rfa)

HARMONIA = "NCT05207709"
PALMARES = "NCT06805812"
PALOMA2 = "NCT01740427"


@pytest.fixture
def case(tmp_path, monkeypatch):
    d = tmp_path / "WHU-999-t"
    d.mkdir()
    (d / "design.json").write_text(json.dumps(
        {"trials": {"HARMONIA": HARMONIA, "PALMARES-2": PALMARES, "PALOMA-2": PALOMA2}}))
    monkeypatch.setattr(rfa, "CASES", tmp_path)
    monkeypatch.setattr(rfa, "_CACHE", {})
    monkeypatch.setattr(rfa, "posted_facts", lambda nct: {
        HARMONIA: {"status": "TERMINATED", "start_date": "2022-03-28",
                   "start_date_type": "ACTUAL", "completion_date": "2026-03-26",
                   "completion_date_type": "ACTUAL",
                   "enrolment": 61, "enrolment_type": "ACTUAL"},
        PALMARES: {"status": "RECRUITING", "start_date": "2023-05-01",
                   "enrolment": 3500, "enrolment_type": "ESTIMATED"},
        PALOMA2: {"status": "COMPLETED", "enrolment": 666},
    }.get(nct, {}))
    return d


# --- what it confirms -------------------------------------------------------

def test_confirms_status_date_and_enrolment_from_one_sentence(case):
    page = ("<p>HARMONIA (NCT05207709) is a phase III trial; it opened in March 2022 "
            "and terminated with 61 patients enrolled.</p>")
    got = {(f["field"], str(f["value"])) for f in rfa.findings("t", page)}
    assert got == {("status", "TERMINATED"), ("start_date", "2022-03"),
                   ("enrolment", "61")}, got


def test_reaches_into_a_long_paragraph_via_the_sentence_carrying_the_nct(case):
    """The block rule alone could not see these facts.

    On the live page the PALMARES-2 facts sit in a 1,400-character paragraph,
    which the short-block rule skips. They are in the same sentence as the NCT,
    and that sentence is unambiguous on its own.
    """
    page = ("<p>" + ("Prose about several trials. " * 50)
            + "Its record (NCT06805812, still recruiting toward an estimated 3,500 "
              "patients) has no results posted.</p>")
    got = {(f["field"], str(f["value"])) for f in rfa.findings("t", page)}
    assert got == {("status", "RECRUITING"), ("enrolment", "3500")}, got


def test_a_less_specific_date_agrees_with_a_more_specific_one(case):
    assert rfa.date_agrees("2022-03", "2022-03-28")
    assert rfa.date_agrees("2022-03-28", "2022-03-28")


# --- what it must refuse to say ---------------------------------------------

def test_a_wrong_value_is_silent_and_never_a_contradiction(case):
    """The whole safety argument. This check confirms or says nothing.

    A page reading "58 patients per arm" against a registry enrolment of 116 is
    RIGHT, and a checker that read the per-arm number as a total would report a
    false error on a true sentence. Contradiction needs to understand the
    sentence, and understanding the sentence is what we are not delegating.
    """
    page = ("<p>HARMONIA (NCT05207709) opened in April 2022 and terminated with "
            "90 patients enrolled.</p>")
    fs = rfa.findings("t", page)
    assert [f["field"] for f in fs] == ["status"]      # only the true one
    rows = rfa.preflight_rows("t", page)
    assert all(s != "BLOCKED" for _n, s, _d in rows)


def test_two_registry_numbers_in_one_scope_is_ambiguous(case):
    page = ("<p>NCT05207709 and NCT06805812 both appear, and one of them "
            "terminated with 61 patients enrolled.</p>")
    assert rfa.findings("t", page) == []


def test_a_scope_with_no_nct_says_nothing(case):
    page = ("<p>Shaaban and colleagues randomised 116 patients, 58 to each arm, "
            "at a single centre in Egypt.</p>")
    assert rfa.findings("t", page) == []


def test_a_bare_count_is_not_an_enrolment_claim(case):
    """"followed 1,982 patients" is not "enrolled 1,982 patients".

    Without this the PALMARES-2 paragraph, which reports a DIFFERENT study's
    1,982-patient cohort beside the NCT, would enter an enrolment assertion
    that the registry happens not to post -- harmless here, but the same
    looseness in the other direction is how a figure gets attributed to the
    wrong trial.
    """
    assert rfa.claims_in("followed 1,982 patients across eighteen centres") == []
    assert [c[0] for c in rfa.claims_in("randomised 116 patients")] == ["enrolment"]


def test_a_bare_year_makes_no_date_claim(case):
    assert rfa.claims_in("HARMONIA opened in 2022.") == []


# --- the overturn contract publish.py depends on ----------------------------

def test_overturn_needs_every_checkable_part_confirmed(case):
    page = ("<p>HARMONIA (NCT05207709) opened in March 2022 and terminated with "
            "61 patients enrolled.</p>")
    conf = rfa.confirmed_keys("t", page)
    assert rfa.quote_fully_confirmed("HARMONIA terminated with 61 patients enrolled.", conf)
    assert not rfa.quote_fully_confirmed("HARMONIA terminated with 90 patients enrolled.", conf)


def test_the_confirmed_key_holds_the_registrys_value_not_the_pages(case):
    """The first version stored the page's wording, so a finding quoting
    "opened on 28 March 2022" would not overturn against a page saying only
    "March 2022" -- although 2022-03-28 is the posted date and the quote was
    exactly right. A check that can only confirm the sentence it already read
    is an echo, not a check."""
    page = "<p>HARMONIA (NCT05207709) opened in March 2022.</p>"
    conf = rfa.confirmed_keys("t", page)
    assert conf["start_date"] == {"2022-03-28"}
    assert rfa.quote_fully_confirmed("HARMONIA opened on 28 March 2022.", conf)
    assert not rfa.quote_fully_confirmed("HARMONIA opened on 27 March 2022.", conf)


def test_a_quote_with_no_checkable_assertion_never_overturns(case):
    page = "<p>HARMONIA (NCT05207709) terminated with 61 patients enrolled.</p>"
    conf = rfa.confirmed_keys("t", page)
    assert not rfa.quote_fully_confirmed(
        "The NCCN guideline assigns ribociclib category 1.", conf)
    assert not rfa.quote_fully_confirmed("", conf)


def test_a_registry_that_cannot_be_reached_is_silent_not_confirming(case, monkeypatch):
    monkeypatch.setattr(rfa, "posted_facts", lambda nct: {})
    page = "<p>HARMONIA (NCT05207709) terminated with 61 patients enrolled.</p>"
    assert rfa.findings("t", page) == []
    assert rfa.confirmed_keys("t", page) == {}


# --- the coverage hole that made all three findings invisible ---------------

def test_a_trial_named_without_a_digit_enters_the_trial_map(tmp_path, monkeypatch):
    """HARMONIA was invisible to every registry check on this page.

    The name-to-NCT harvester in registry_figures and study_design required a
    digit in the trial name (PALOMA-2, MONARCH 3), so a trial named by a word
    alone never entered the map -- and a checker that cannot see a thing was
    indistinguishable from a checker that looked and found nothing. Three
    claims about HARMONIA sat unchecked and read as unverifiable while the
    registry posted all three.
    """
    import importlib.util as iu
    for mod in ("registry_figures", "study_design"):
        sp = iu.spec_from_file_location(
            mod, ROOT / "backend" / "scripts" / "whatholdsup" / (mod + ".py"))
        m = iu.module_from_spec(sp)
        sp.loader.exec_module(m)
        d = tmp_path / ("WHU-999-" + mod[:3])
        d.mkdir()
        (d / "sources.json").write_text(json.dumps({"sources": [
            {"id": "S1", "title": "HARMONIA — ribociclib vs palbociclib. NCT05207709",
             "url": "https://clinicaltrials.gov/study/NCT05207709"},
            {"id": "S2", "title": "PALOMA-2 — palbociclib and letrozole. NCT01740427",
             "url": "https://clinicaltrials.gov/study/NCT01740427"},
        ]}))
        monkeypatch.setattr(m, "CASES", tmp_path)
        got = m.trials_for(mod[:3])
        assert got.get("HARMONIA") == HARMONIA, (mod, got)
        assert got.get("PALOMA-2") == PALOMA2, (mod, got)


def test_it_reads_enrolment_phrased_as_a_noun(case):
    """Coverage must not depend on how the page happens to be worded.

    The page said "recruiting toward an estimated 3,500 patients" and this
    check confirmed it. An edit reworded it to "an estimated enrolment of
    3,500" -- and the check stopped confirming, silently, so a finding it had
    settled an hour earlier came back open. A check whose reach depends on the
    page's phrasing loses reach every time the page is edited, in the direction
    of looking cleaner.
    """
    for phrasing in ("recruiting toward an estimated 3,500 patients",
                     "an estimated enrolment of 3,500",
                     "target enrollment of 3500",
                     "3,500 patients were enrolled"):
        got = [(f, v) for f, v, _m in rfa.claims_in(phrasing)]
        assert ("enrolment", 3500) in got, (phrasing, got)


def test_a_noun_phrase_without_an_enrolment_word_is_still_ignored(case):
    assert rfa.claims_in("a cohort of 3,500") == []
    assert rfa.claims_in("followed 3,500 patients") == []
