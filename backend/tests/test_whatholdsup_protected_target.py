"""not_ruled_protected: a target is protected when it is CONTAINED in a protected sentence.

Post-study, mid-rerun tool fix (2026-10-28). Fix 7 accepted "MERIT:
not_ruled_protected" only when the item's "We say" text was itself a protected
sentence. On WHU-S01r the advocate quoted the part of the sentence it objected
to, so an objection on the question restatement could not close. The target now
counts as protected when it is contained, after normalisation (quotations.norm,
quoted_in), in a protected sentence on the page or in a protected binding row.

The adjudication file is written by the real source_advocate.write_template; the
real _closed, open_items, ruling.advocate_items and bindings.protected_kind decide.

COUNTERFACTUAL. Drop the containment test in protected_check (return False after
the protected_kind check) and t_fragment and t_row_marked_fragment go red; compare
without quotations.norm (raw `in`) and t_normalised goes red; drop the
page-sentence list (sents = []) and t_fragment goes red.
"""
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

PART_OF_QUESTION = "whether layout and pricing cut transport emissions"      # in T.PAGE[0], protected
PART_OF_FINDING = "layout changes could reduce emissions"                   # in T.PAGE[1], not protected


@pytest.fixture
def page(monkeypatch):
    monkeypatch.setattr(B, "page_sentences", lambda slug: list(T.PAGE))


def _closes(tmp_path, monkeypatch, target):
    N._adj(tmp_path, monkeypatch, [N._misstates(target)])
    objs, _qs = SA.open_items(T.SLUG)
    return objs == [] and R.advocate_items(T.SLUG, tmp_path) == []


def test_sanity_the_fragment_is_not_protected_on_its_own():
    assert B.protected_kind(PART_OF_QUESTION) is None
    assert PART_OF_QUESTION in T.PAGE[0] and PART_OF_FINDING in T.PAGE[1]


def test_fragment_of_a_protected_sentence_closes(tmp_path, monkeypatch, page):
    assert _closes(tmp_path, monkeypatch, PART_OF_QUESTION)


def test_normalised_fragment_closes(tmp_path, monkeypatch, page):
    assert _closes(tmp_path, monkeypatch, "“Whether  layout and pricing cut Transport emissions”")


def test_fragment_with_an_ellipsis_closes(tmp_path, monkeypatch, page):
    assert _closes(tmp_path, monkeypatch, "whether layout … transport emissions")


def test_fragment_of_an_unprotected_sentence_stays_open(tmp_path, monkeypatch, page):
    assert not _closes(tmp_path, monkeypatch, PART_OF_FINDING)


def test_text_on_no_protected_sentence_stays_open(tmp_path, monkeypatch, page):
    assert not _closes(tmp_path, monkeypatch, "pricing cut freight emissions in rural areas")


def test_fragment_of_a_row_marked_sentence_closes(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "page_sentences", lambda slug: [])
    monkeypatch.setattr(B, "load", lambda slug: {"bindings": {
        B.fingerprint(T.PAGE[1]): {"sentence": T.PAGE[1], "on_page": True, "protected": "reading"}}})
    assert _closes(tmp_path, monkeypatch, PART_OF_FINDING)
