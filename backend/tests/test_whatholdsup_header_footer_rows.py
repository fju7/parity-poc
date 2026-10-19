"""The header's prose and the footer's change log get rows (2026-10-19).

The 19 October revision of deskilling read "every sentence on the page" and
none of the standfirst's sentences had a row: FURNITURE dropped the whole
<header>. And a footer sentence about our own process ("we can see a trial
registry move") stood after the same claim was corrected in the body, because
nothing gave footer sentences rows. Fixtures only."""
import importlib.util
import sys
from pathlib import Path

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

PAGE = ("<html><head><title>T — What Holds Up</title></head><body>"
        "<nav><a href='/'>What Holds Up</a> <a href='/issues'>Issues</a></nav>"
        "<header><div class='kicker-row'><span class=\"pill acc\">Issue three</span>"
        "<span class=\"meta\">Published 30 August 2026 &middot; <strong>Evidence read 30 August 2026</strong></span></div>"
        "<h1>What Happens to the Experts First</h1><div class=\"domain\">whatholdsup.org</div>"
        "<p class=\"standfirst\">The evidence usually offered is weak. That study is retrospective.</p></header>"
        "<section><h2>The number</h2><p>It fell from 28.4% to 22.4%.</p></section>"
        "<footer id=\"updates\"><p class=\"note\">As of 30 August 2026, the date the evidence was read.</p>"
        "<p><strong>Updated 12 September 2026.</strong> We can see a trial registry move.</p></footer>"
        "</body></html>")


def _page(monkeypatch, html=PAGE):
    monkeypatch.setattr(B, "_page_html", lambda slug: html)


def test_the_standfirst_and_the_masthead_line_are_page_sentences(monkeypatch):
    _page(monkeypatch)
    s = B.page_sentences("t")
    assert "The evidence usually offered is weak." in s
    assert "That study is retrospective." in s
    assert any(x.startswith("Published 30 August 2026") and "Evidence read 30 August 2026" in x for x in s)


def test_the_title_pills_domain_and_nav_are_still_furniture(monkeypatch):
    _page(monkeypatch)
    flat = " ".join(B.page_sentences("t"))
    assert "What Happens to the Experts First" not in flat
    assert "Issue three" not in flat
    assert "whatholdsup.org" not in flat
    assert "Issues" not in flat


def test_the_footer_is_not_a_body_sentence_but_has_its_own_list(monkeypatch):
    _page(monkeypatch)
    assert not any("registry" in x for x in B.page_sentences("t"))
    f = B.footer_sentences("t")
    assert "We can see a trial registry move." in f
    assert any(x.startswith("As of 30 August 2026") for x in f)


def test_a_section_header_in_a_test_draft_is_unaffected(monkeypatch):
    html = ("<html><body><header><p>Citation test draft, not for publication</p><h1>Title</h1></header>"
            "<header><h2>The short answer</h2></header><p>It works.</p></body></html>")
    _page(monkeypatch, html)
    assert B.page_sentences("t") == ["It works."]


def test_scan_gives_header_rows_and_footer_rows_tagged_as_process_claims(monkeypatch):
    _page(monkeypatch)
    monkeypatch.setattr(B.store, "sources", lambda slug: [])
    saved = {}
    monkeypatch.setattr(B, "load", lambda slug: {"bindings": {}})
    monkeypatch.setattr(B, "save", lambda slug, doc: saved.update(doc))
    B.scan("t")
    rows = {v["sentence"]: v for v in saved["bindings"].values()}
    assert rows["The evidence usually offered is weak."].get("region") is None
    foot = rows["We can see a trial registry move."]
    assert foot["region"] == "footer" and foot["trigger"] == B.PROCESS_TRIGGER
    assert foot["why_empirical"] == B.FOOTER_WHY and foot["on_page"] is True
    assert "What Happens to the Experts First" not in rows


def test_a_footer_row_stays_on_the_page_on_a_second_scan(monkeypatch):
    _page(monkeypatch)
    monkeypatch.setattr(B.store, "sources", lambda slug: [])
    doc = {"bindings": {}}
    monkeypatch.setattr(B, "load", lambda slug: doc)
    monkeypatch.setattr(B, "save", lambda slug, d: None)
    B.scan("t")
    B.scan("t")
    foot = [v for v in doc["bindings"].values() if v.get("region") == "footer"]
    assert foot and all(v["on_page"] and "left_page" not in v for v in foot)
