"""A source-list tag is not part of the sentence on a study issue (GAP-017).

The source list's <span class="tag">Methods</span> was folded into the entry's
sentence, so the audit read "Methods" as the sentence's own word and a ruling
removed it (WHU-P02 u70). On a study issue the tag is dropped before splitting,
by bindings.page_sentences, changecheck and applied_check alike. A published
issue is unchanged: its bound rows' fingerprints include the tag.
"""
import sys
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import bindings as B          # noqa: E402
import changecheck as C       # noqa: E402
import applied_check as AC    # noqa: E402

PAGE = ("<html><body><article><p>The trial enrolled 20 adults.</p>"
        '<div class="src"><span class="tag">Methods</span> Hall KD, et al. '
        'An inpatient trial. <a href="https://doi.org/10.1/x">Read</a></div>'
        "</article></body></html>")


def _page(monkeypatch, study):
    monkeypatch.setattr(B.ledger, "page_text", lambda slug: PAGE, raising=False)
    monkeypatch.setattr(B, "_is_study", lambda slug: study)
    return B.page_sentences("demo")


def test_a_study_page_sentence_does_not_carry_its_tag(monkeypatch):
    got = _page(monkeypatch, True)
    assert any(s.startswith("Hall KD") for s in got)
    assert not any("Methods" in s for s in got)


def test_a_published_page_is_unchanged(monkeypatch):
    got = _page(monkeypatch, False)
    assert any(s.startswith("Methods Hall KD") for s in got)


def test_changecheck_and_applied_check_split_a_study_page_the_same_way(monkeypatch):
    study = _page(monkeypatch, True)
    assert not any("Methods" in s for s in C.sentences_of(PAGE, drop_tags=True))
    assert any(s.startswith("Methods") for s in C.sentences_of(PAGE))           # published default
    assert AC.page_sentences(PAGE) == C.sentences_of(PAGE, drop_tags=True)
    assert [s for s in study if s.startswith("Hall")] == \
        [s for s in AC.page_sentences(PAGE) if s.startswith("Hall")]


def test_a_tag_change_alone_is_not_a_changed_sentence_on_a_study_page():
    before = PAGE
    after = PAGE.replace(">Methods<", ">Primary<")
    assert C.changed(before, after, drop_tags=True)[0] == []
    assert C.changed(before, after)[0]                                         # published: it is


def test_the_real_published_pages_keep_their_tagged_fingerprints():
    for slug in ("melanoma", "cdk46", "deskilling"):
        assert B._is_study(slug) is False
