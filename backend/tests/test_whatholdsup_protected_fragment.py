"""Fix 10, tightened: which fragments count as targeting a protected sentence.

Post-study, mid-rerun tool fix 14 (2026-10-28). A fragment counts as targeting a
protected sentence only if (a) it has at least 6 words after normalisation and
(b) it occurs in NO unprotected sentence on the page. A fragment in both is
ambiguous: it is not protected (not_ruled_protected does not close it), and its
item goes to a person, never to the ruling model.

The adjudication file is written by the real source_advocate.write_template; the
real protected_check, _closed, open_items, ruling.rule_advocate (split_protected,
route_to_person) and ruling.rule_omissions decide. The model is a stub that fails
the test if it is called.

COUNTERFACTUAL. Drop the word floor and t_short goes red; drop the unprotected-
sentence test (never AMBIGUOUS) and t_both_not_protected and t_both_to_a_person go
red; drop the "ambiguous" item marker in _advocate_items and t_both_to_a_person
goes red.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import bindings as B                              # noqa: E402
import ruling as R                                # noqa: E402
import source_advocate as SA                      # noqa: E402
import test_whatholdsup_fix2_ruling as T          # noqa: E402
import test_whatholdsup_not_ruled_protected as N  # noqa: E402

QUESTION = "The question is whether the trials of testing cut deaths among adults."
FINDING = "The trials of testing cut deaths among adults in two countries."
PAGE = [QUESTION, FINDING, "Measured effects come mostly from pricing."] + \
       ["Filler sentence number %d about pricing." % i for i in range(16)]
SHORT = "the trials"                                                   # 2 words
ONLY_PROTECTED = "whether the trials of testing cut deaths"               # 7 words, only in QUESTION
BOTH = "the trials of testing cut deaths among adults"                     # 8 words, in both


@pytest.fixture
def page(monkeypatch):
    monkeypatch.setattr(B, "page_sentences", lambda slug: list(PAGE))


def _closes(tmp_path, monkeypatch, target):
    N._adj(tmp_path, monkeypatch, [N._misstates(target)])
    return SA.open_items(T.SLUG)[0] == []


def _for_person(tmp_path):
    p = tmp_path / "rulings" / R.FOR_PERSON
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def test_sanity_the_page():
    assert B.protected_kind(QUESTION) == "question" and B.protected_kind(FINDING) is None
    for frag in (SHORT, ONLY_PROTECTED, BOTH):
        assert frag in QUESTION
    assert SHORT in FINDING.lower() and BOTH in FINDING.lower() and ONLY_PROTECTED not in FINDING.lower()


def test_short_fragment_is_not_protected(tmp_path, monkeypatch, page):
    assert SA.protected_check(T.SLUG).status(SHORT) is None
    assert not _closes(tmp_path, monkeypatch, SHORT)


def test_six_plus_words_only_in_a_protected_sentence_is_protected(tmp_path, monkeypatch, page):
    assert SA.protected_check(T.SLUG).status(ONLY_PROTECTED) == "protected"
    assert _closes(tmp_path, monkeypatch, ONLY_PROTECTED)


def test_both_is_ambiguous_and_not_protected(tmp_path, monkeypatch, page):
    assert SA.protected_check(T.SLUG).status(BOTH) == SA.AMBIGUOUS
    assert not _closes(tmp_path, monkeypatch, BOTH)


def test_both_goes_to_a_person_never_the_model(tmp_path, monkeypatch, page):
    T._case(tmp_path, monkeypatch, [N._misstates(BOTH)])
    assert R.rule_advocate(T.SLUG, T.never, P=T.P, rows={}, held=T.HELD, case=tmp_path) == []
    [rec] = _for_person(tmp_path)
    assert rec["mode"] == "advocate" and rec["protected"] == SA.AMBIGUOUS and rec["sentence"] == BOTH
    assert "a person decides which" in rec["why"]
    assert len(SA.open_items(T.SLUG)[0]) == 1                  # still open, for the person


def test_an_omission_anchored_on_both_goes_to_a_person(tmp_path, monkeypatch, page):
    T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED, anchor=BOTH)])
    assert T._run(tmp_path, T.never, page_sentences=PAGE) == []
    [rec] = _for_person(tmp_path)
    assert rec["mode"] == "omissions" and rec["protected"] == SA.AMBIGUOUS


def test_an_unprotected_six_word_fragment_is_still_ruled(tmp_path, monkeypatch, page):
    T._case(tmp_path, monkeypatch, [N._misstates("testing cut deaths among adults in two countries")])
    items = R._advocate_items(T.SLUG, {}, T.HELD, tmp_path)
    keep, person = R.split_protected(items, {})
    assert len(keep) == 1 and person == []
