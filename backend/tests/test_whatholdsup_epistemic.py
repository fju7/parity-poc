"""Claims about what we know, checked against what the store says we hold.

WHY THIS EXISTS
---------------
This publication's most important claims are claims about its own knowledge --
what we hold, what we have read, what we could not reach, what nobody has
opened. Those are the claims the source store can adjudicate, because the store
is where the answer lives. Claims about the world are the hard ones to check by
machine; claims about ourselves are the easy ones, and they are what this
publication trades on.

Nothing checked them until 2026-09-10. Three sentences went wrong in two days.

THE TEST SET COMES FIRST, AND IT HAS BOTH OUTCOMES
---------------------------------------------------
Failure 16: a protective construct nobody has made fire is not a protection, and
one that fires on everything is not either. Three instances must fail and two
must pass, and the two that pass are the harder half -- both of them are
sentences that LOOK like the failing ones.

  FAIL  the corrigendum note: "that requires reading it", while S025 was held in
        full. The passage said "we have now read it" four sentences earlier.
  FAIL  corrections.md, 31 August: "It remains unread", true when written and
        false the next day, unnoticed for nine.
  FAIL  the Morning Glory correction: it announced a clause had been replaced.
        The clause was on the page, and stayed there for five more days.

  PASS  the S029 erratum disclosure: "We have not been able to read it." S030 IS
        held in full -- but S030 is `form: record`, the PubMed record ABOUT the
        notice, not the notice. A check that cannot tell those apart reports our
        most careful sentence as a lie.
  PASS  the S028 note: abstract_held, stating exactly what is held.
"""
import importlib.util
import sys
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


E = _mod("epistemic")

CORRIGENDUM_UNREAD = (
    "What we cannot say is whether the corrigendum touches any of them, because "
    "that requires reading it — and Europe PMC lists exactly one route to it, "
    "marked Subscription required.")
CORRECTIONS_UNREAD = (
    "The MONARCH 3 corrigendum. This page said it was behind a paywall, then "
    "corrected itself to say it was open access. It remains unread and is still "
    "disclosed as unread.")
S029_DISCLOSURE = (
    "A 2018 erratum covering thirteen NEJM articles at once (N Engl J Med "
    "2018;379:2185) applies to this paper. We have not been able to read it: "
    "NEJM returns 403, Europe PMC records the notice as neither open access nor "
    "in its archive, and neither PubMed nor Crossref carries an abstract for it; "
    "so we do not know whether it touches a figure on this page.")
S028_NOTE = (
    "Riaz and colleagues, read from its abstract only — the abstract is held and "
    "the full text is not, and nothing here rests on anything past the abstract.")


# ---------------------------------------------------------------------------
# it fires
# ---------------------------------------------------------------------------

def test_it_fires_on_the_corrigendum_note():
    f = E.check_sentence(CORRIGENDUM_UNREAD, "cdk46")
    assert f, "the corrigendum note must be reported"
    assert f[0]["source"] == "S025"
    assert f[0]["asserted"] == E.UNREAD
    assert "full_text_held" in f[0]["recorded"]


def test_it_fires_on_the_corrections_entry():
    f = E.check_sentence(CORRECTIONS_UNREAD, "cdk46")
    assert f, "the 31 August entry must be reported"
    assert [x["source"] for x in f] == ["S025"], (
        "it must name the corrigendum and NOT the trial paper it corrects: %s"
        % [x["source"] for x in f])
    assert f[0]["asserted"] == E.UNREAD


def test_it_fires_on_a_correction_announcing_a_change_never_made():
    page = ("Morning Glory Sciences — we give its argument on its merits rather "
            "than on its authority — the Phase 2b population was stage IIIB–IV.")
    correction = ("The Morning Glory Sciences clause has been replaced: the "
                  "sentence no longer characterises the outlet.")
    f = E.check_claimed_change(correction, page)
    assert f, "a correction announcing a removal that did not happen must fire"


# ---------------------------------------------------------------------------
# it does NOT fire -- the half that makes it a check rather than an alarm
# ---------------------------------------------------------------------------

def test_it_does_not_fire_on_the_s029_erratum_disclosure():
    """S030 is held in full. What is held is the PubMed RECORD, not the notice.
    The store says so in `form: record`; a check that ignores that field calls
    the most carefully written sentence on the page a contradiction."""
    f = E.check_sentence(S029_DISCLOSURE, "melanoma")
    assert not f, "false positive on a correct disclosure: %r" % (f,)


def test_it_does_not_fire_on_a_note_that_states_what_is_held():
    f = E.check_sentence(S028_NOTE, "melanoma")
    assert not f, "false positive on an accurate abstract-only note: %r" % (f,)


def test_a_correction_whose_change_was_actually_made_does_not_fire():
    page = "The sentence now names the outlet and gives its argument."
    correction = ("The Morning Glory Sciences clause has been replaced: the "
                  "sentence no longer characterises the outlet.")
    assert not E.check_claimed_change(correction, page)


# ---------------------------------------------------------------------------
# the record-vs-document distinction, on its own
# ---------------------------------------------------------------------------

def test_a_record_about_a_document_is_not_the_document():
    assert E.is_record_about("S030", "melanoma") is True
    assert E.is_record_about("S029", "melanoma") is False


if __name__ == "__main__":
    bad = 0
    for n, fn in sorted(globals().items()):
        if n.startswith("test_") and callable(fn):
            try:
                fn(); print("  ok    %s" % n)
            except AssertionError as e:
                bad += 1; print("  FAIL  %s: %s" % (n, e))
    print("\n%s" % ("all pass" if not bad else "%d failure(s)" % bad))
    raise SystemExit(1 if bad else 0)
