"""Every sentence gets a row (2026-10-18), except headings by markup and a
source-list role label standing alone. The source-claim / process-claim word
lists are TAGS on rows, and a process-claim tag routes a row to B21's store
check, with the new comparisons. Fixtures only."""
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


B = _load("bindings")
sys.path.insert(0, str(WHU))
import epistemic as E  # noqa: E402


@pytest.mark.parametrize("sent", [
    "It is a retrospective observational study, and that governs everything.",
    "Their December 2024 preprint had said reduced.",
    "The authors list several limitations.",
    "Shaw and colleagues ran three experiments.",
    "The review calls it a randomised trial.",
])
def test_source_claim_is_a_tag_and_the_sentence_gets_a_row(sent):
    must, why = B.is_empirical(sent, set())
    assert must and why.startswith("source claim")
    assert B.claim_trigger(sent)[0] == B.SOURCE_TRIGGER


@pytest.mark.parametrize("sent", [
    "Read at the publisher.",
    "We read both.",
    "This page has not been able to read the 2011 paper itself.",
    "Read at source on 30 August 2026.",
])
def test_process_claim_is_a_tag_and_the_sentence_gets_a_row(sent):
    must, why = B.is_empirical(sent, set())
    assert must and why.startswith("process claim")
    assert B.claim_trigger(sent)[0] == B.PROCESS_TRIGGER


def test_we_found_is_process_not_attribution():
    assert B.claim_trigger("We found the correction through a search.")[0] == B.PROCESS_TRIGGER
    assert B.claim_trigger("The trial found no effect.")[0] == B.SOURCE_TRIGGER


def test_old_triggers_keep_their_reason():
    must, why = B.is_empirical("The rate fell from 28.4% to 22.4% in published work.", set())
    assert must and why == "figure"


@pytest.mark.parametrize("sent", ["So the honest position is this.", "It had not.", "The headline was accurate."])
def test_a_sentence_with_no_marker_word_now_gets_a_row(sent):
    assert B.is_empirical(sent, set()) == (True, "sentence")
    assert B.claim_trigger(sent) == ("", "")


def test_a_heading_by_markup_gets_no_row():
    assert B.is_empirical("Peer review.", set(), heading=True) == (False, "")
    assert B.is_empirical("Peer review.", set())[0]


def test_a_standalone_role_label_gets_no_row():
    assert B.is_empirical("Primary", set(), label="Primary") == (False, "")


def test_a_label_prefix_is_not_the_sentences_own_words():
    sent = "Preprint Kosmyna N, Hauptmann E, Yuan YT."
    assert B.is_empirical(sent, set(), label="Preprint") == (True, "sentence")
    assert B.is_empirical(sent, set())[1].startswith("source claim")


def test_run_in_headings_are_short_bold_leads(monkeypatch):
    html = ("<html><body><p><strong>Peer review.</strong> Three of the studies are preprints.</p>"
            "<p><strong>It is a retrospective observational study, and that governs everything.</strong> "
            "Nobody was randomised.</p><p>One more thing. <strong>Mid-paragraph bold.</strong></p></body></html>")
    monkeypatch.setattr(B, "_page_html", lambda slug: html)
    heads, _labels, _entries = B.page_markup("t")
    assert "Peer review." in heads
    assert not any(h.startswith("It is a retrospective") for h in heads)
    assert "Mid-paragraph bold." not in heads


def test_page_markup_reads_headings_labels_and_entries(monkeypatch):
    html = ("<html><head><title>x</title></head><body><h2 id='a'>What was published</h2><h4>Sub</h4><h5>Not one</h5>"
            '<div class="src"><span class="tag">Preprint</span><span><a href="https://arxiv.org/abs/1">A</a>'
            '<span class="note">Read at source.</span></span></div></body></html>')
    monkeypatch.setattr(B, "_page_html", lambda slug: html)
    heads, labels, entries = B.page_markup("t")
    assert "What was published" in heads and "Sub" in heads and "Not one" not in heads
    assert labels == ["Preprint"]
    assert entries and "Read at source." in entries[0][0] and entries[0][1] == ["https://arxiv.org/abs/1"]
    srcs = [{"id": "S001", "url": "https://arxiv.org/abs/1"}]
    assert B.entry_subject("Read at source.", entries, srcs) == ["S001"]


def test_process_claim_is_routed_to_b21():
    assert not B.is_holdings("Read at the publisher.")
    assert B.is_holdings("Read at the publisher.", B.PROCESS_TRIGGER)


@pytest.fixture
def store(monkeypatch):
    srcs = [{"id": "S046", "document_class": "document", "access": {"state": "full_text_held", "sections": ["the PDF"]}},
            {"id": "S030", "document_class": "document", "access": {"state": "full_text_held", "sections": ["the RSNA publisher page"]}},
            {"id": "S010", "document_class": "document", "access": {"state": "blocked"}},
            {"id": "S027", "document_class": "document", "access": {"state": "abstract_held"}}]
    held = {"S046": {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1/", "also_held": []},
            "S030": {"url": "https://research.vu.nl/repository/x.pdf", "also_held": []}}
    monkeypatch.setattr(E, "_sources", lambda slug: srcs)
    monkeypatch.setattr(E.store, "held", lambda slug: held)
    return srcs


def row(sent, sid):
    return {"sentence": sent, "trigger": B.PROCESS_TRIGGER, "store_subject_markup": [sid]}


def test_read_at_the_publisher_against_a_repository_route(store):
    fl = B.b21_holdings(row("Read at the publisher.", "S046"), "t")
    assert [f["verdict"] for f in fl] == ["store disagrees"]
    assert "pmc.ncbi" in fl[0]["why"]


def test_read_at_the_publisher_passes_when_the_ledger_names_the_publisher(store):
    assert B.b21_holdings(row("Read at the publisher.", "S030"), "t") == []


def test_read_in_full_against_abstract_held(store):
    fl = B.b21_holdings(row("We read it in full.", "S027"), "t")
    assert [f["verdict"] for f in fl] == ["store disagrees"]


def test_could_not_open_against_blocked_passes(store):
    assert B.b21_holdings(row("We could not open it.", "S010"), "t") == []


def test_could_not_open_against_full_text_held_fails(store):
    fl = B.b21_holdings(row("We could not open it.", "S046"), "t")
    assert [f["verdict"] for f in fl] == ["store disagrees"]


def test_a_process_claim_about_no_one_document_is_not_evaluated_never_blocked(store, monkeypatch):
    monkeypatch.setattr(E, "resolve", lambda s, g: [])
    fl = B.b21_holdings({"sentence": "We check the sources on this page against their notices.",
                         "trigger": B.PROCESS_TRIGGER}, "t")
    assert fl and all(B.CALIBRATION_SEVERITY.get(f["verdict"]) != B.BAD for f in fl)


def test_scan_gives_every_sentence_a_row_and_tags_it(monkeypatch, tmp_path):
    html = ("<html><body><h2>The number</h2><p><strong>Peer review.</strong> We read both. "
            "It had not.</p><div class=\"src\"><span class=\"tag\">Primary</span><span>"
            "<a href=\"https://arxiv.org/abs/1\">Doe J. A title.</a>"
            "<span class=\"note\">Read at the publisher.</span></span></div></body></html>")
    monkeypatch.setattr(B, "_page_html", lambda slug: html)
    monkeypatch.setattr(B.store, "sources", lambda slug: [{"id": "S001", "url": "https://arxiv.org/abs/1"}])
    saved = {}
    monkeypatch.setattr(B, "load", lambda slug: {"bindings": {}})
    monkeypatch.setattr(B, "save", lambda slug, doc: saved.update(doc))
    B.scan("t")
    rows = {v["sentence"]: v for v in saved["bindings"].values()}
    assert "The number" not in rows and "Peer review." not in rows and "Primary" not in rows
    assert rows["We read both."]["trigger"] == B.PROCESS_TRIGGER
    assert "trigger" not in rows["It had not."]
    assert rows["Read at the publisher."]["store_subject_markup"] == ["S001"]
