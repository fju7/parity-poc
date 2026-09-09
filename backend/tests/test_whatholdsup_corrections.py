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


_OVERLAP_FILE = (Path(__file__).resolve().parents[2] / "issues"
                 / "WHU-001-melanoma" / "log-quotations.json")


def _declared_overlaps(slug):
    """Investigated body/log overlaps, declared with commit-level provenance.

    Same shape and same discipline as figure-exclusions.json: the file carries
    the evidence, and a declaration that no longer matches is reported as stale
    rather than ignored, so it cannot become the mechanism by which this test is
    silenced.
    """
    if not _OVERLAP_FILE.exists():
        return {}
    import json as _json
    doc = _json.loads(_OVERLAP_FILE.read_text(encoding="utf-8"))
    return {" ".join((r.get("sentence") or "").split()): r
            for r in doc.get("overlaps") or []}


def test_the_change_log_is_outside_the_binder_which_is_why_this_exists():
    """A sentence present in BOTH the body and the change log.

    WHAT THIS DETECTS, stated exactly, because the previous message did not.
    It said an overlap meant `page_sentences` had started reading the footer.
    That was one possible cause asserted as the only one, and on 2026-09-09 it
    was the wrong one: FURNITURE still strips <footer id="updates"> correctly,
    and the overlap was two DISTINCT sentences with identical text, one in each
    region. The message sent the next reader after a bug that was not there.

    What an overlap actually means is that the same string exists twice, and the
    set intersection cannot say which region either copy came from. Three
    readings, only one of them benign:

      * the log QUOTES a body sentence — normal, and what happened here;
      * a body sentence MIGRATED out of the log, or a log entry LEAKED into the
        body — a real defect;
      * FURNITURE has stopped stripping — also a real defect, and the one the
        old message named.

    The test cannot tell them apart. `git log -S` on the sentence can, and the
    message says so rather than guessing.

    THE HAZARD EITHER WAY. Bindings are keyed by fingerprint(sentence), which is
    a hash of the text. Two identical sentences have one key, so a binding
    recorded for the body copy is indistinguishable from one for the log copy —
    the log sentence is bound by construction whenever it quotes the body
    verbatim. corrections_check line 197 has the figure-level form of this: a
    figure in a log sentence is exempted from b13 if the same figure appears in
    the body.
    """
    B = _load("bindings")
    body = {" ".join(s.split()) for s in B.page_sentences("melanoma")}
    log = CC.sentences("melanoma")
    assert log, "no change log found"
    overlap = [" ".join(s.split()) for s in log if s in body]

    declared = _declared_overlaps("melanoma")
    undeclared = [s for s in overlap if s not in declared]
    stale = [s for s in declared if s not in overlap]

    assert not stale, (
        "%d declared overlap(s) in %s no longer appear in both regions. THIS IS "
        "THE CASE THAT MATTERS: a body sentence removed or reworded while the "
        "change log keeps quoting it leaves the log entry carrying the body "
        "sentence's binding — bindings key on fingerprint(sentence) — so it "
        "reads as verified while supporting nothing on the page. Re-investigate "
        "and retire or amend the declaration: %s"
        % (len(stale), _OVERLAP_FILE.name, stale[:2]))

    assert not undeclared, (
        "%d sentence(s) appear in both the body and the change log and are not "
        "declared. This test cannot tell you which copy came first, and the "
        "cause changes what to do: a log entry quoting a body sentence is "
        "correct; a body sentence that migrated out of the log, or a log entry "
        "that leaked into the body, is not; and FURNITURE having stopped "
        "stripping <footer> is a third cause again. Run `git log -S` on each "
        "before ruling. Note that bindings key on fingerprint(sentence), so the "
        "two copies share one binding whichever way it happened. %d overlap(s) "
        "ARE already declared as investigated in %s — read those first, and add "
        "to that file only with commit-level provenance. Undeclared: %s"
        % (len(undeclared), len(declared), _OVERLAP_FILE, undeclared[:2]))
