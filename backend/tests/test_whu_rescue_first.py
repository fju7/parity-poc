"""Rescue first for a refusal about one retrieval, refusal first for one about the work (advisor's ruling 4 on the
design review of 2026-11-26; acquire_sources.py, open_copy.py).

  * a page that identifies the work but fails the form rule (02zd's S004, "undetermined") or is a landing, shell or
    stub page is offered to the landing route; a wall falls through to the open copies;
  * bytes that do not identify the work (identity fails) are refused first: no rescue is tried, and that is recorded;
  * a held abstract no longer ends the full-text search; with no full text by any route the abstract is kept;
  * the open-copy route excludes only the refused URL, never its whole host;
  * every rescue not tried is recorded in the source's access.rescue.
Pages, documents and OpenAlex records here are CONSTRUCTED; nothing is fetched.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import landing_route as LR   # noqa: E402
import open_copy as OC       # noqa: E402

TITLE = ("Rapid Evidence Assessment (REA) of What Works to Improve Educational Outcomes for People with Disabilities "
         "in Low- and Middle-Income Countries")
PAGE_URL = "https://www.example.gov.uk/research-for-development-outputs/rea"
FULL = "https://www.example.gov.uk/government/uploads/rea_full_report.pdf"
DOC = b"%PDF-1.4 the full report"
OGL = ('<footer><a rel="license" href="https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/">'
       'Open Government Licence v3.0</a></footer>')
PAGE = ("<html><body><h1>%s</h1><a href=\"%s\">%s (full report)</a>%s</body></html>" % (TITLE, FULL, TITLE, OGL)).encode()


def _err(url, code):
    return urllib.error.HTTPError(url, code, "x", None, io.BytesIO(b""))


class Hops:
    def __init__(self, table):
        self.table = table

    def __call__(self, url):
        got = self.table[url]
        if got[0] == "doc":
            return 200, None, got[1], "application/pdf"
        return got[0], got[1], b"", "text/html"


def _run(tmp_path, monkeypatch, *, src, fetch, held_check, open_copy=None):
    import acquire_sources as AQ
    import source_store as store
    case = tmp_path / "issues" / "WHU-T-x"
    case.mkdir(parents=True)
    (case / "sources.json").write_text(json.dumps({"sources": [dict(src)]}))
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(store, "library_held", lambda slug: {})
    monkeypatch.setattr(store, "held_check", held_check)
    monkeypatch.setattr(store, "text_of", lambda d, c, pages=8: ("Methods. Results.", "text"))
    monkeypatch.setattr(store, "put", lambda slug, sid, data, **kw: {"file": "f", "sha256": "s", "bytes": len(data),
                                                                     "kind": "full_text", "kind_why": "x",
                                                                     "retrieved": "2026-11-26"})
    monkeypatch.setattr(AQ, "fetch_retrying", fetch)
    monkeypatch.setattr(LR, "step", Hops({FULL: ("doc", DOC)}))
    monkeypatch.setattr(LR.OC, "robots", lambda u, f: (True, "robots.txt allows it"), raising=False)
    monkeypatch.setattr(LR.OC, "tdm_site", lambda u, f: (False, "no tdmrep.json"), raising=False)
    calls = []
    if open_copy is not None:
        def fake_find(s, refused, fetch, held):
            calls.append(set(refused) if not isinstance(refused, str) else {refused})
            return open_copy
        monkeypatch.setattr(OC, "find", fake_find)
    monkeypatch.setenv("WHU_ORCH_STEP", "acquire")
    out = tmp_path / "acquire.json"
    rc = AQ.main(["x", "--no-summaries", "--landing-pdfs", "--open-copies", "--out", str(out)])
    return rc, json.loads((case / "sources.json").read_text())["sources"][0]["access"], calls


def _form_rule_check(slug, sid, s, data, ct):
    # 02zd's S004: the page identifies the work (12 of 12 title words) but fails the assessment-summary form rule
    if data.startswith(b"<html"):
        return False, {"state": "fragment_only", "kind": "undetermined",
                       "why": "identified (12 of 12), but not the document: undetermined -- form 'assessment summary'"}
    return True, {"state": "full_text_held", "kind": "full_text", "why": "identified (test)"}


def test_a_form_rule_refusal_is_offered_to_the_landing_route_first(tmp_path, monkeypatch):
    src = {"id": "S004", "type": "review", "title": TITLE, "url": PAGE_URL}
    rc, acc, _calls = _run(tmp_path, monkeypatch, src=src, held_check=_form_rule_check,
                           fetch=lambda u: (PAGE, "text/html", u) if u == PAGE_URL else (_ for _ in ()).throw(_err(u, 404)))
    assert rc == 0 and acc["state"] == "full_text_held"
    assert acc["held"]["route"].startswith("landing page PDF link: %s" % FULL)
    assert acc["rescue"]["landing"] == "tried"


def test_bytes_that_are_not_the_work_are_refused_first_and_no_rescue_is_tried(tmp_path, monkeypatch):
    src = {"id": "S007", "type": "review", "title": TITLE, "url": PAGE_URL, "doi": "10.1/x"}

    def identity_fails(slug, sid, s, data, ct):
        return False, {"state": None, "kind": None, "why": "nothing in these bytes identifies them as this document"}
    rc, acc, calls = _run(tmp_path, monkeypatch, src=src, held_check=identity_fails,
                          fetch=lambda u: (PAGE, "text/html", u), open_copy={"record": {"outcome": "x"}})
    assert rc == 1 and "held" not in acc and calls == []                # the open-copy route was never asked
    assert acc["rescue"]["landing"].startswith("not tried: the bytes fetched are not this work")
    assert acc["rescue"]["open_copy"] == acc["rescue"]["landing"]


def test_a_wall_falls_through_to_the_open_copies_and_only_the_refused_url_is_excluded(tmp_path, monkeypatch):
    src = {"id": "S002", "type": "review", "title": TITLE, "url": "https://www.tandfonline.com/doi/full/10.1/x",
           "doi": "10.1/x"}
    rc, acc, calls = _run(tmp_path, monkeypatch, src=src, held_check=_form_rule_check,
                          fetch=lambda u: (_ for _ in ()).throw(_err(u, 403)),
                          open_copy={"record": {"outcome": "no permitted open copy listed"}})
    assert rc == 1 and calls and src["url"] in calls[0]
    assert acc["rescue"]["open_copy"] == "tried"
    assert acc["rescue"]["landing"] == "not tried: no page about the document was fetched"


def test_a_held_abstract_does_not_end_the_full_text_search(tmp_path, monkeypatch):
    src = {"id": "S001", "type": "review", "title": TITLE, "url": PAGE_URL, "doi": "10.1/x"}

    def abstract_page(slug, sid, s, data, ct):
        if data.startswith(b"<html"):
            return True, {"state": "abstract_held", "kind": "abstract", "why": "an abstract (test)"}
        return True, {"state": "full_text_held", "kind": "full_text", "why": "identified (test)"}
    rc, acc, calls = _run(tmp_path, monkeypatch, src=src, held_check=abstract_page,
                          fetch=lambda u: (PAGE, "text/html", u))
    assert rc == 0 and acc["state"] == "full_text_held"              # the abstract page's own PDF link
    assert acc["held"]["route"].startswith("landing page PDF link")


def test_with_no_full_text_by_any_route_the_abstract_is_kept_and_the_search_recorded(tmp_path, monkeypatch):
    src = {"id": "S001", "type": "review", "title": TITLE, "url": PAGE_URL, "doi": "10.1/x"}
    bare = b"<html><body><h1>%s</h1><p>Abstract only.</p></body></html>" % TITLE.encode()

    def abstract_page(slug, sid, s, data, ct):
        return True, {"state": "abstract_held", "kind": "abstract", "why": "an abstract (test)"}
    rc, acc, calls = _run(tmp_path, monkeypatch, src=src, held_check=abstract_page,
                          fetch=lambda u: (bare, "text/html", u),
                          open_copy={"record": {"outcome": "no permitted open copy listed"}})
    assert acc["state"] == "abstract_held" and calls                      # the open copies were tried first
    assert acc["rescue"] == dict(acc["rescue"], landing="tried", open_copy="tried")


def test_open_copy_excludes_the_refused_url_not_its_host():
    work = {"locations": [
        {"source": {"display_name": "Same host, another copy", "type": "repository"}, "is_oa": True,
         "pdf_url": "https://www.example.gov.uk/government/uploads/rea_full_report.pdf", "version": "publishedVersion"},
        {"source": {"display_name": "The refused copy", "type": "repository"}, "is_oa": True,
         "pdf_url": PAGE_URL, "version": "publishedVersion"}]}
    rows = OC.candidates(work, {PAGE_URL})
    assert rows[0]["permitted"] is True
    assert rows[1]["permitted"] is False and "already refused" in rows[1]["why"]
