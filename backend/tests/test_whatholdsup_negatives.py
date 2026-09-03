"""B15 — a universal negative searched against our own library. GAP-001.

Run:  python3 -m pytest backend/tests/test_whatholdsup_negatives.py

No API calls. A stub library of six documents stands in for the real one.

THE TEST THAT MATTERS is the first: the gap's own acceptance criterion, written
into the gap entry before the check existed — plant an outlet reporting a hazard
ratio in the library, claim no outlet reported one, and assert the check
surfaces it. The second is the real sentence from the real failure.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


N = _load("negatives")
SLUG = "testissue"

LIB = {
    # an outlet reporting a hazard ratio for the trial the claim is about
    "S100": "The Phase 3 INTerpath-001 result came with a hazard ratio of 0.62 "
            "(95% CI, 0.41-0.94), the outlet reported.",
    # the same figure, but for a different trial, named in the sentence
    "S200": "In KEYNOTE-942 the combination cut recurrence by 49% (HR=0.51; "
            "95% CI, 0.294-0.887).",
    # a statistics reference explaining what a hazard ratio is
    "S300": "If HR = 1 then the two groups have the same hazard. A 95% CI that "
            "includes 1 cannot exclude no effect.",
    # our own claim, in somebody else's words
    "S400": "No hazard ratios, confidence intervals or p-values for INTerpath-001 "
            "have been released.",
    # the real sentence from the real failure
    "S019": "Primary Analysis: events 22.4% (24/107) vs 40.0% (20/50); HR 0.561 "
            "(95% CI 0.309-1.017), P=0.0266 (formal hypothesis testing of RFS, "
            "overall one-sided alpha=0.10, performed at primary analysis).",
    # a mention with no figure in it at all
    "S500": "The hazard ratio for INTerpath-001 has been the subject of comment.",
}
SRCS = [
    {"id": "S100", "type": "coverage", "about": "INTerpath-001", "also_called": []},
    {"id": "S200", "type": "coverage", "about": "KEYNOTE-942",
     "also_called": ["KEYNOTE-942"]},
    {"id": "S300", "type": "reference", "also_called": []},
    {"id": "S400", "type": "coverage", "about": "INTerpath-001", "also_called": []},
    {"id": "S019", "type": "coverage", "about": "", "also_called": []},
    {"id": "S500", "type": "coverage", "about": "INTerpath-001", "also_called": []},
]
NONE_FOR_TRIAL = {"class": "efficacy_figure", "subject": "INTerpath-001",
                  "claim": "none"}


@pytest.fixture(autouse=True)
def stub(monkeypatch):
    monkeypatch.setattr(N.store, "sources", lambda slug: SRCS)
    monkeypatch.setattr(N.store, "held", lambda slug: {k: {} for k in LIB})
    monkeypatch.setattr(N.SC, "_text", lambda slug, sid: LIB.get(sid))


def quotes(cands):
    return " || ".join(c["quote"] for c in cands)


def test_the_gaps_own_acceptance_criterion():
    """Written into the gap entry before the check existed:

        "A test that plants 'no outlet reported a hazard ratio' on a page whose
        library contains an outlet reporting a hazard ratio, and asserts the
        check surfaces it."
    """
    cands, _ = N.search(SLUG, NONE_FOR_TRIAL)
    assert any(c["source_id"] == "S100" for c in cands), quotes(cands)


def test_it_finds_the_sentence_that_raised_the_gap():
    """S019 said "formal hypothesis testing of RFS, overall one-sided alpha=0.10"
    while the page said the framing was never explained to readers. A document we
    held, had read, and had bound other claims to. Four passes walked past it."""
    cands, _ = N.search(SLUG, NONE_FOR_TRIAL)
    assert any("one-sided alpha=0.10" in c["quote"] for c in cands), quotes(cands)


def test_a_figure_belonging_to_another_trial_is_not_a_counterexample():
    cands, counts = N.search(SLUG, NONE_FOR_TRIAL)
    assert not any(c["source_id"] == "S200" for c in cands)
    assert counts["other_trial"] >= 1


def test_a_statistics_reference_reports_no_trials_result():
    cands, counts = N.search(SLUG, NONE_FOR_TRIAL)
    assert not any(c["source_id"] == "S300" for c in cands)
    assert counts["reference"] >= 1


def test_our_own_claim_in_someone_elses_words_is_not_a_counterexample():
    """Morning Glory's "No hazard ratios ... have been released" matches the
    pattern and agrees with us. Counting it would be the check contradicting a
    sentence with its own support."""
    cands, counts = N.search(SLUG, NONE_FOR_TRIAL)
    assert not any(c["source_id"] == "S400" for c in cands)


def test_the_denial_filter_cannot_swallow_a_positive_report():
    """THE FILTER THAT NEEDED WATCHING, and it failed the first time it was run.

    The first version read a list of negation words and dropped this sentence
    because it contains "did not" — a positive report of a hazard ratio,
    swallowed by a word list, which is how four allow-lists in this repository
    went wrong. The filter is now structural: a report attaches a VALUE to the
    class within a short window, a denial does not.
    """
    LIB["S600"] = ("Although the companies did not comment, the trial reported a "
                   "hazard ratio of 0.55 (95% CI, 0.30-0.99) for INTerpath-001.")
    SRCS.append({"id": "S600", "type": "coverage", "about": "INTerpath-001",
                 "also_called": []})
    try:
        cands, _ = N.search(SLUG, NONE_FOR_TRIAL)
        assert any(c["source_id"] == "S600" for c in cands), (
            "a positive report was dropped because its sentence contained 'not'")
    finally:
        LIB.pop("S600"); SRCS.pop()


def test_a_mention_with_no_figure_is_not_a_report_of_one():
    cands, counts = N.search(SLUG, NONE_FOR_TRIAL)
    assert not any(c["source_id"] == "S500" for c in cands)
    assert counts["no_value"] >= 1


# --- the declaration ---------------------------------------------------------

def test_a_row_with_no_declaration_is_not_usable():
    assert N.declared({"sentence": "no outlet reported it"}) is None


def test_a_class_we_cannot_express_is_refused_rather_than_passed():
    """A claim we cannot search for is a claim we cannot check, and passing it
    would be the exemption this whole layer exists to refuse."""
    assert N.declared({"negative_over": {"class": "vibes", "claim": "none"}}) is None
    assert N.declared({"negative_over": {"class": "efficacy_figure",
                                         "claim": "probably"}}) is None


def test_a_usable_declaration_is_accepted():
    assert N.declared({"negative_over": dict(NONE_FOR_TRIAL)}) == NONE_FOR_TRIAL


# --- reading the candidates --------------------------------------------------

def test_a_candidate_stays_unread_until_somebody_signs_for_it():
    cands, _ = N.search(SLUG, NONE_FOR_TRIAL)
    row = {"negative_over": dict(NONE_FOR_TRIAL, read=[])}
    assert len(N.unread(row, cands)) == len(cands)


def test_a_reading_needs_a_name_and_a_reason():
    """Half a disposition is none. The same rule as b13's exclusions."""
    cands, _ = N.search(SLUG, NONE_FOR_TRIAL)
    c = cands[0]
    for bad in ({"source_id": c["source_id"], "quote": c["quote"], "by": "x"},
                {"source_id": c["source_id"], "quote": c["quote"], "why_not": "y"}):
        row = {"negative_over": dict(NONE_FOR_TRIAL, read=[bad])}
        assert len(N.unread(row, cands)) == len(cands)


def test_a_read_candidate_stops_blocking():
    cands, _ = N.search(SLUG, NONE_FOR_TRIAL)
    c = cands[0]
    row = {"negative_over": dict(NONE_FOR_TRIAL, read=[
        {"source_id": c["source_id"], "quote": c["quote"],
         "why_not": "it is the earlier trial's figure, named two sentences up",
         "by": "claude", "on": "2026-09-03"}])}
    assert len(N.unread(row, cands)) == len(cands) - 1
