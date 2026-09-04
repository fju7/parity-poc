"""B18 — the correction history is claims, and it must be able to fail.

WHAT WENT WRONG
---------------
`bindings.page_sentences` strips <nav>, <header>, <footer>, <aside>. The change
log lives in <footer id="updates">. On issue one that is 154 sentences, 26 of
them carrying figures, invisible to rule 1, rule 2, the span checks, the scope
checks and the binder. The one region where we tell readers what we got wrong
was the only region with no control at all.

Both corrections that themselves needed correcting were written there:

  2 September — a notice said three figures "came from no document" and one
  "exists nowhere". The check behind it had reported only that they were in
  nothing WE HOLD, and said so in its own output.

  3 September — "The printed figure was out by 0.05 against its own working,
  for eight days." 3.35 rounds to 3.4. There was no discrepancy. We accused
  ourselves of an arithmetic error we had not made, in the place a reader goes
  to decide whether we can be trusted about our own mistakes. Our own gate
  reported it the same day (o1, o2) and it stood for another day.

THE THREE HISTORICAL SENTENCES ARE THE FIXTURES
-----------------------------------------------
A check written after an incident must fail on that incident. All three
published forms of the 3.4/3.35 claim are here as data, and so are the forms
that must NOT fire: the sentence retracting it, and an ordinary description of a
figure changing.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
BAD, WARN, OK = "BLOCKED", "warn", "ok"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


CC = _load("corrections_check")


def fires(sentence, paragraph=None):
    """The C2 decision for one sentence in its paragraph."""
    para = paragraph or sentence
    if not CC.MISMATCH.search(sentence):
        return False
    if CC.SHOWS_ROUNDING.search(para):
        return False
    nums = list(dict.fromkeys([m.group(1) for m in CC.NUM.finditer(sentence)]
                              + [m.group(1) for m in CC.NUM.finditer(para)]))
    return any(CC._rounds_to(a, b)
               for i, a in enumerate(nums) for b in nums[i + 1:] if a != b)


PUBLISHED_AND_WRONG = [
    ("Readers saw 3.4 ; the working underneath it comes to 3.35 , and that "
     "discrepancy is recorded below.", None),
    ("The composite readers saw did not match its own working: the scorecard "
     "showed 3.4 where the dimensions underneath it come to 3.35.", None),
    ("The printed figure was out by 0.05 against its own working, for eight days.",
     "The composite readers saw did not match its own working. The published page "
     "scored this assessment 3.4. It did not: the six scores and the published "
     "weights come to 3.35. The printed figure was out by 0.05 against its own "
     "working, for eight days."),
]


@pytest.mark.parametrize("sentence,para", PUBLISHED_AND_WRONG)
def test_it_fails_on_every_published_form_of_the_error(sentence, para):
    assert fires(sentence, para), (
        "this exact sentence was published and was false; the check must catch it")


MUST_NOT_FIRE = [
    # the retraction: it shows the arithmetic, so a reader can judge it
    ("The separate claim that its printed 3.4 disagreed with its own working of "
     "3.35 was itself wrong.",
     "The scorecard was split into two numbers. The separate claim that its "
     "printed 3.4 disagreed with its own working of 3.35 was itself wrong — "
     "3.35 rounds to 3.4 — and that is corrected above."),
    # an ordinary description of a figure changing asserts no mismatch
    ("Distant metastasis-free survival eased from 62% to 59% over that period.",
     None),
    # a REAL mismatch between two numbers neither of which rounds to the other
    ("The page said the interval was 0.288 to 0.906 and the paper says 0.294 to "
     "0.887, which do not match.", None),
]


@pytest.mark.parametrize("sentence,para", MUST_NOT_FIRE)
def test_it_does_not_fire_on_these(sentence, para):
    assert not fires(sentence, para)


def test_the_retraction_carve_out_is_the_working_not_a_word_list():
    """A sentence that shows its arithmetic is not an unchecked claim. That is
    the repository's existing standard, applied here — NOT a list of retraction
    words, which is the thing that has been wrong every time it was tried."""
    src = (WHU / "corrections_check.py").read_text(encoding="utf-8")
    assert "SHOWS_ROUNDING" in src
    # one pattern, about showing the working; no vocabulary of denials
    for word in ("itself wrong", "was right", "no discrepancy", "not a discrepancy",
                 "corrected above", "retract"):
        assert word not in src.split("SHOWS_ROUNDING = ")[1].split("\n")[0], word


def test_rounds_to_is_symmetric_and_precision_aware():
    assert CC._rounds_to("3.4", "3.35")
    assert CC._rounds_to("3.35", "3.4")
    assert CC._rounds_to("60", "59.8")
    assert not CC._rounds_to("3.4", "3.2")
    assert not CC._rounds_to("0.510", "0.501")


def test_a_page_with_no_change_log_blocks_rather_than_passing_vacuously():
    rows = CC.preflight_rows.__wrapped__ if hasattr(CC.preflight_rows, "__wrapped__") \
        else CC.preflight_rows
    real = CC.changelog_html
    CC.changelog_html = lambda slug: ""
    try:
        got = rows("melanoma")
    finally:
        CC.changelog_html = real
    assert got[0][1] == BAD
    assert "nothing to read" in got[0][2]


def test_the_live_change_log_passes_both_rules():
    rows = CC.preflight_rows("melanoma")
    assert [st for _n, st, _d in rows] == [OK, OK], rows


def test_the_change_log_is_outside_the_binder_which_is_why_this_exists():
    """If page_sentences ever starts covering the footer, this check becomes
    redundant rather than wrong — but somebody should notice, not discover it."""
    B = _load("bindings")
    body = {" ".join(s.split()) for s in B.page_sentences("melanoma")}
    log = CC.sentences("melanoma")
    assert log, "no change log found"
    overlap = [s for s in log if s in body]
    assert not overlap, (
        "the binder now reads the change log; B18's premise has changed and its "
        "docstring should be revisited: %s" % overlap[:2])
