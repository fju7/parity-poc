"""Two things pdftotext does to a held paper, read for what they are.

Adopted 2026-10-18, from the deskilling survey (WHU-003):

  2a  "1, 222"     S001's PDF prints 1,222 and its extracted text reads
                   "1, 222". In HELD TEXT ONLY, a comma, one space and exactly
                   three digits between groups is a thousands separator when
                   that reading is exactly the sentence's figure. Rule 1, B12
                   and B13 share it (figure_text.split_grouped) and each says
                   so in an INFO note. Never applied to a page sentence: on a
                   page "1, 222 and 3" is a list.
  2b  dropped "-"  S029's PDF breaks "high-quality" across a line and the
                   extracted text reads "highquality". The quotation matcher
                   and the span matcher (b2_present, b5_complete) accept a
                   page hyphen between two letters that the PDF text dropped,
                   with an INFO note, and only for a PDF-derived layer.

Fixtures only. Nothing here reads an issue directory or loads publish.py.
"""
import importlib.util
import re
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


FT = _load("figure_text")
SC = _load("spancheck")
SLUG = "testissue"

S001_PDF = ("Across three randomized controlled trials on human-AI interactions "
            "(N = 1, 222), we provide causal evidence. The pretest solve rate did "
            "not differ (F (3, 581) = 1.21, P = 0.306).")
S029_PDF = ("Overall, the number of highquality empirical studies remains limited, "
            "but consistent themes emerge across domains.")
Q29 = "the number of high-quality empirical studies remains limited"


# --- 2a: a comma and one space between groups, in held text -----------------

@pytest.mark.parametrize("figure, text, printed", [
    ("1222", "(N = 1, 222)", "1, 222"),
    ("1,222", "across 1, 222 participants", "1, 222"),
    ("1222.5", "a total of 1, 222.5 hours", "1, 222.5"),
    ("1222333", "spending of 1, 222, 333 dollars", "1, 222, 333"),
])
def test_a_comma_and_one_space_is_read_as_a_separator_in_held_text(figure, text, printed):
    assert FT.split_grouped(figure, text) == printed


@pytest.mark.parametrize("figure, text", [
    ("222", "1, 222 and 3"),          # the list: 222 is not 1,222, and gets nothing
    ("1222", "5, 1, 222"),            # a list carrying on before it
    ("1222", "1, 222, 333"),          # runs on into another group: not 1,222
    ("1222", "11, 222"),              # a different lead group
    ("1222", "1,  222"),              # two spaces is not one
    ("1222", "1, 2223"),              # four digits is not a group
    ("1222", "1, 222.5"),             # a decimal that is not this figure
    ("3581", "F (3, 581) = 1.21"),    # degrees of freedom
    ("1222", "1,222"),                # the plain comma is the ordinary reader's
    ("222", "222"),                   # three digits have no groups to split
])
def test_a_comma_and_one_space_never_makes_a_different_number(figure, text):
    assert FT.split_grouped(figure, text) is None


def test_the_page_sentence_is_never_read_this_way():
    # comma_grouped is what the page side goes through; a list stays a list.
    assert FT.comma_grouped("1, 222 and 3") == "1, 222 and 3"


def test_b13_finds_1222_in_held_text_and_says_how(monkeypatch):
    b13 = _load("b13")
    monkeypatch.setattr(b13.store, "held", lambda slug: {"S001": {}})
    monkeypatch.setattr(b13.SC, "_text", lambda slug, sid: S001_PDF)
    hits, notes = b13.where_noted("1222", SLUG)
    assert hits == ["S001"]
    assert notes == ["1222 is printed '1, 222' in S001's extracted text, read as one figure"]
    assert b13.where("1222", SLUG) == ["S001"]


def test_b13_gives_a_list_figure_no_grouping_note(monkeypatch):
    b13 = _load("b13")
    monkeypatch.setattr(b13.store, "held", lambda slug: {"S001": {}})
    monkeypatch.setattr(b13.SC, "_text", lambda slug, sid: "the scores were 1, 222 and 3")
    _hits, notes = b13.where_noted("222", SLUG)
    assert notes == []
    assert b13.where_noted("1223", SLUG) == ([], [])


def test_b13_preflight_carries_the_note_as_info(monkeypatch):
    b13 = _load("b13")
    monkeypatch.setattr(b13.store, "held", lambda slug: {"S001": {}})
    monkeypatch.setattr(b13.store, "sources", lambda slug: [{"id": "S001"}])
    monkeypatch.setattr(b13.SC, "_text", lambda slug, sid: S001_PDF)
    monkeypatch.setattr(b13.B, "page_sentences",
                        lambda slug: ["Three experiments randomised 1,222 people."])
    monkeypatch.setattr(b13.B, "_page_html",
                        lambda slug: "<p>Three experiments randomised 1,222 people.</p>")
    monkeypatch.setattr(b13, "load_exclusions", lambda slug: [])
    rows = {n: (st, d) for n, st, d in b13.preflight_rows(SLUG)}
    assert rows["figures in held documents"][0] == b13.OK
    st, d = rows["figures read across a comma-and-space grouping"]
    assert st == b13.OK and d.startswith("INFO") and "'1, 222'" in d


def test_b12_reads_1222_as_printed_with_an_info_note(monkeypatch):
    monkeypatch.setattr(SC, "_text", lambda slug, sid: S001_PDF)
    ok, why = SC.b12_precision("1,222", SLUG, "S001")
    assert ok and "as printed" in why and "INFO" in why and "'1, 222'" in why


def test_b12_gives_a_different_number_nothing(monkeypatch):
    monkeypatch.setattr(SC, "_text", lambda slug, sid: "the scores were 1, 222 and 3")
    ok, why = SC.b12_precision("1,223", SLUG, "S001")
    assert "INFO" not in why


class _Stub:
    """spancheck over one fixture span, as test_whatholdsup_figure_checks does."""
    UNDETERMINED = "undetermined"
    DROPPED_HYPHEN_NOTE = SC.DROPPED_HYPHEN_NOTE
    _norm = staticmethod(SC._norm)
    HELD = {}

    @staticmethod
    def _text(slug, sid):
        return _Stub.HELD.get(sid)

    @staticmethod
    def _texts(slug, sid):
        return [("f", _Stub.HELD[sid])] if sid in _Stub.HELD else []

    @staticmethod
    def defective_renditions(slug, sid):
        return False, ""

    @staticmethod
    def b2_present(span, slug, sid, **kw):
        doc = _Stub.HELD.get(sid)
        return (SC._norm(span).lower() in SC._norm(doc or "").lower()), "searched"


@pytest.fixture
def rule1(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "spancheck", _Stub())
    B = _load("bindings")
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    monkeypatch.setattr(B.store, "sources", lambda slug: [])

    def _no_page(slug):
        raise RuntimeError("no page in a fixture")
    monkeypatch.setattr(B, "_page_html", _no_page)

    def run(sentence, span):
        _Stub.HELD.clear()
        _Stub.HELD["S001"] = span
        B.save(SLUG, {"bindings": {"R00": {
            "sentence": sentence, "sentence_sha": "R00", "on_page": True,
            "bucket": "context", "source_id": "S001", "span": span,
            "premises": [], "step": ""}}})
        return {n: (st, d) for n, st, d in B.rule_rows(SLUG)}, B
    return run


def test_rule_1_reads_a_comma_and_space_span_figure_with_a_note(rule1):
    rows, B = rule1("Three experiments randomised 1,222 people.",
                    "Across three randomized controlled trials (N = 1, 222)")
    assert rows["rule 1 — written from a document we hold"][0] == B.OK
    st, d = rows["rule 1 — figures read across a comma-and-space grouping"]
    assert st == B.OK and d.startswith("INFO") and "'1, 222'" in d


def test_rule_1_still_fails_a_figure_the_grouping_does_not_make(rule1):
    rows, B = rule1("Three experiments randomised 1,223 people.",
                    "Across three randomized controlled trials (N = 1, 222)")
    st, d = rows["rule 1 — written from a document we hold"]
    assert st == B.BAD and "1223" in d
    assert "rule 1 — figures read across a comma-and-space grouping" not in rows


# --- 2b: a hyphen the PDF text dropped --------------------------------------

def test_a_dropped_hyphen_between_letters_is_found():
    body = SC._norm(S029_PDF).lower()
    hit = SC.find_dropping_hyphens(Q29, body)
    assert hit and body[hit[0]:hit[1]] == "the number of highquality empirical studies remains limited"


@pytest.mark.parametrize("needle, body", [
    ("high-quality studies", "high-quality studies"),   # a plain match is not this
    ("high-quality studies", "high quality studies"),   # a space is something, not nothing
    ("high-quality studies", "low-quality studies"),
    ("a 2-3 year gap", "a 23 year gap"),                 # digits, not letters
    ("high-quality studies", "highqualitystudies"),     # only the hyphen may go
])
def test_a_dropped_hyphen_is_nothing_else(needle, body):
    assert SC.find_dropping_hyphens(needle, body) is None


@pytest.fixture
def held(monkeypatch):
    """b2_present / b5_complete over one held rendition of S029."""
    files = {}
    monkeypatch.setattr(SC, "_text", lambda slug, sid: files[sid][1] if sid in files else None)
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [files[sid]] if sid in files else [])
    monkeypatch.setattr(SC.store, "held", lambda slug: {sid: {"file": f} for sid, (f, _t) in files.items()})

    def put(file, text):
        files["S029"] = (file, text)
    return put


def test_b2_accepts_a_dropped_hyphen_in_a_pdf_layer_and_says_so(held):
    held("docs/ca/caec.pdf", S029_PDF)
    ok, why = SC.b2_present(Q29, SLUG, "S029", trust_canary=False)
    assert ok is True and "INFO" in why and SC.DROPPED_HYPHEN_NOTE in why


@pytest.mark.parametrize("file", ["docs/24/2402.xml", "docs/73/73ec.html"])
def test_b2_does_not_accept_a_dropped_hyphen_outside_a_pdf_layer(held, file):
    held(file, S029_PDF)
    ok, _why = SC.b2_present(Q29, SLUG, "S029", trust_canary=False)
    assert ok is False


def test_b5_reads_the_tail_after_a_dehyphenated_span(held):
    held("docs/ca/caec.pdf", S029_PDF)
    ok, why = SC.b5_complete("the number of high-quality empirical studies remains limited, but", SLUG, "S029")
    assert ok is True, why
    held("docs/ca/caec.pdf", "the number of highquality empirical studies and then more")
    ok, why = SC.b5_complete("the number of high-quality empirical studies", SLUG, "S029")
    assert ok is False and "continues" in why


@pytest.fixture
def quotation(monkeypatch):
    """quotations.preflight_rows over one recorded quotation of S029."""
    Q = _load("quotations")
    monkeypatch.setitem(sys.modules, "spancheck", SC)
    monkeypatch.setattr(Q, "attestations_on_file", lambda slug, page=None: [])
    monkeypatch.setattr(Q, "_held_ids", lambda slug: {"S029"})
    monkeypatch.setattr(Q, "_sources", lambda slug: {"S029": {"access": {"state": "full_text_held"}}})
    monkeypatch.setattr(Q, "load", lambda slug: {"quotations": [{
        "id": "Q-29", "quote": Q29, "source_id": "S029",
        "verbatim": "Overall, the number of high-quality empirical studies remains "
                    "limited, but consistent themes emerge across domains."}]})
    page = "<html><body><p>The review says <q>%s</q>.</p></body></html>" % Q29

    def run(file, text):
        monkeypatch.setattr(SC, "_texts", lambda slug, sid: [(file, text)])
        return {n: (st, d) for n, st, d in Q.preflight_rows(SLUG, page)}, Q
    return run


def test_a_quotation_matches_across_a_hyphen_its_pdf_text_dropped(quotation):
    rows, Q = quotation("docs/ca/caec.pdf", S029_PDF)
    assert rows["quotations match the source"][0] == Q.OK
    st, d = rows["quotations matched ignoring a dropped hyphen"]
    assert st == Q.OK and d.startswith("INFO") and "Q-29" in d
    assert "recorded verbatim context matches the bytes" not in rows


def test_a_quotation_missing_a_hyphen_in_xml_still_differs(quotation):
    rows, Q = quotation("docs/24/2402.xml", S029_PDF)
    assert rows["quotations match the source"][0] == Q.BAD
    assert "quotations matched ignoring a dropped hyphen" not in rows


def test_a_quotation_with_a_different_word_still_differs_in_a_pdf(quotation):
    rows, Q = quotation("docs/ca/caec.pdf", S029_PDF.replace("highquality", "lowquality"))
    assert rows["quotations match the source"][0] == Q.BAD
    assert "quotations matched ignoring a dropped hyphen" not in rows
