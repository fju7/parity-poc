"""quotations.norm(): quote-mark KIND and combining diacritics.

Run:  cd backend && python3 -m pytest tests/test_whatholdsup_quotation_norm_folds.py -q

(Moved 2026-10-18 from tests/whatholdsup/, where the pre-commit hook --
which runs backend/tests/test_whatholdsup_*.py -- never collected it.)

WHY THIS EXISTS
Three of issue three's quotations could not be matched to sources we hold:

  Q-01  page 'while'          S043 prints "while"       -- quote-mark kind
  Q-12  page 'Age >60 years'  S045 prints "Age >60..."  -- quote-mark kind
  Q-05  page Budzyn+acute     S043 extracts as Budzyn   -- combining diacritic

_SMART already folded CURLY quotes to straight, so an earlier reading of this
-- "norm() folds neither quote marks nor diacritics" -- was half wrong. The
page uses SINGLE quotes where the sources use DOUBLE, and after the curly fold
those are still two different characters.

WHAT IS DELIBERATELY NOT FOLDED
Hyphens. S029's text layer prints "highquality" where the page quotes
"high-quality" -- pdftotext dropped a line-break hyphen and no pdftotext flag
recovers it (-raw yields "high- quality" and corrupts "automation" into
"auto- mation"). Folding hyphens would also make a source printing "high
quality" match a page quoting "high-quality", and that is a place a real
difference could hide. Q-29 is closed on the record instead.

COUNTERFACTUAL. Each fold is red under exactly one mutation:
    drop  text.replace('"', "'")   -> t_quote_kind, t_q01_needs_both red
    drop  the NFD/Mn comprehension -> t_diacritic,  t_q01_needs_both red
    add   text.replace("-", "")    -> t_hyphen_is_not_folded red
t_q39_still_fails passes under all three: a-for-this is a WORD difference and
no fold here may touch it.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import quotations as Q        # noqa: E402
import spancheck as SC        # noqa: E402
import pytest                 # noqa: E402

# Real strings. Left column as the page prints it, right as the held source
# extracts. Nothing here is invented for the test.
PAGE_01 = ("whereas Budzyń et al. investigated how endoscopists perform "
           "non-CADe-assisted colonoscopy ‘while’ they were exposed to CADe")
SRC_01 = ('whereas Budzyn et al. investigated how endoscopists perform '
          'non-CADe-assisted colonoscopy "while" they were exposed to CADe')
PAGE_05 = "will be stronger in the Budzyń study than in our study"
SRC_05 = "will be stronger in the Budzyn study than in our study"
PAGE_12 = ("the only affected findings are for the variables ‘After AI "
           "introduction (using AI in colonoscopy)’ and ‘Age >60 years’")
SRC_12 = ('the only affected findings are for the variables "After AI '
          'introduction (using AI in colonoscopy)" and "Age >60 years"')


def test_quote_kind_is_folded():
    """Q-12: single on the page, double in S045."""
    assert Q.norm(PAGE_12) == Q.norm(SRC_12)


def test_combining_diacritics_are_folded():
    """Q-05: the acute survives on the page and not through pdftotext."""
    assert Q.norm(PAGE_05) == Q.norm(SRC_05)


def test_q01_needs_both_folds():
    """Q-01 carries both differences in one sentence."""
    assert Q.norm(PAGE_01) == Q.norm(SRC_01)


def test_q39_still_fails():
    """THE GUARD. S042 says 'this retrospective observational study'; the page
    says 'a'. That is a reader-facing misattribution with a recorded
    correction, and no fold here may make it match."""
    assert Q.norm("a retrospective observational study") != \
        Q.norm("this retrospective observational study")


def test_hyphen_is_not_folded():
    """THE OTHER GUARD. Goes red the moment someone folds hyphens. See the
    docstring: Q-29 is a record fix, not a match."""
    assert Q.norm("high-quality empirical studies") != \
        Q.norm("highquality empirical studies")


# --- the accent fold is reported, never silent (2026-10-18) -----------------

def test_accents_are_kept_when_asked():
    assert Q.norm(PAGE_05, fold_accents=False) != Q.norm(SRC_05, fold_accents=False)
    assert Q.norm(PAGE_12, fold_accents=False) == Q.norm(SRC_12, fold_accents=False)


def test_accent_folds_names_the_pair():
    assert Q.accent_folds(PAGE_05) == ["Budzyń / Budzyn"]
    assert Q.accent_folds(SRC_05) == []


@pytest.fixture
def quotation(monkeypatch):
    """preflight_rows over one recorded quotation, its source held as `text`."""
    monkeypatch.setattr(Q, "attestations_on_file", lambda slug, page=None: [])
    monkeypatch.setattr(Q, "_held_ids", lambda slug: {"S043"})
    monkeypatch.setattr(Q, "_sources",
                        lambda slug: {"S043": {"access": {"state": "full_text_held"}}})

    def run(quote, text):
        monkeypatch.setattr(Q, "load", lambda slug: {"quotations": [{
            "id": "Q-05", "quote": quote, "source_id": "S043", "verbatim": text}]})
        monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("docs/3a/3af1.xml", text)])
        page = "<html><body><p>They wrote <q>%s</q>.</p></body></html>" % quote
        return {n: (st, d) for n, st, d in Q.preflight_rows("testissue", page)}
    return run


def test_a_match_that_needs_the_accent_fold_carries_an_info_note(quotation):
    rows = quotation(PAGE_05, SRC_05)
    assert rows["quotations match the source"][0] == Q.OK
    st, d = rows["quotations matched ignoring accents"]
    assert st == Q.OK and d.startswith("INFO")
    assert "matched ignoring accents: Q-05: Budzyń / Budzyn" in d


def test_a_match_that_needs_no_fold_has_no_accent_note(quotation):
    rows = quotation(PAGE_05, PAGE_05)
    assert rows["quotations match the source"][0] == Q.OK
    assert "quotations matched ignoring accents" not in rows


def test_the_quote_kind_fold_has_no_note(quotation):
    rows = quotation(PAGE_12, SRC_12)
    assert rows["quotations match the source"][0] == Q.OK
    assert "quotations matched ignoring accents" not in rows
