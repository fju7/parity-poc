"""A landing page's own PDF link (advisor's rulings on the S006 landing-page route, 2026-11-25/26;
backend/scripts/whatholdsup/landing_route.py, acquire_sources.py --landing-pdfs).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): S006 (Kuper et al. 2018) was recorded at its gov.uk Research
for Development Outputs page, which source_store classed a landing page; nothing else was tried. The page links three
PDFs: the full report on www.gov.uk (its link text contains the whole title), and a summary and an easy-read version on
assets.publishing.service.gov.uk -- another registrable domain under the strict Public Suffix List reading (gov.uk and
service.gov.uk are suffixes). The full-report link answers 301 to assets.publishing.service.gov.uk, then 301 again on
that host, then 200 with the PDF. The site states the Open Government Licence v3.0; the PDF states no licence.

The 02zc page, redirect chain, robots.txt and PDF were recorded on 2026-11-25/26 into the private study folder
(~/Projects/whu-study-private/landing_route/02zc_S006/; publisher text never enters the repo), so the first test skips
elsewhere. Every other page, chain and document here is CONSTRUCTED.
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
PRIV = Path.home() / "Projects" / "whu-study-private" / "landing_route" / "02zc_S006"
CASE = ROOT / "issues" / "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"
SLUG = "whu-lean-orch-t1-q1-02zc"

import landing_route as LR   # noqa: E402

TITLE = ("Rapid Evidence Assessment (REA) of What Works to Improve Educational Outcomes for People with Disabilities "
         "in Low- and Middle-Income Countries")
SRC = {"id": "S006", "type": "review", "title": TITLE, "url": "https://www.example.gov.uk/outputs/rea"}
PAGE_URL = SRC["url"]
OGL_FOOTER = ('<footer><a rel="license" href="https://www.nationalarchives.gov.uk/doc/open-government-licence/'
              'version/3/">Open Government Licence v3.0</a></footer>')


def _err(url, code):
    return urllib.error.HTTPError(url, code, "x", None, io.BytesIO(b""))


def _page(links, footer=OGL_FOOTER, head=""):
    a = "".join('<a href="%s">%s</a>' % (u, t) for u, t in links)
    return ("<html><head>%s</head><body><h1>%s</h1>%s%s</body></html>" % (head, TITLE, a, footer)).encode()


class Net:
    """robots.txt / tdmrep.json: url -> bytes | status; anything else 404. Logs every request."""
    def __init__(self, table=None):
        self.table, self.log = table or {}, []

    def __call__(self, url):
        self.log.append(url)
        got = self.table.get(url, 404)
        if isinstance(got, int):
            raise _err(url, got)
        return got, "text/plain", url


class Hops:
    """One hop at a time: url -> (status, location) | ("doc", bytes) | an HTTP status to raise."""
    def __init__(self, table):
        self.table, self.log = table, []

    def __call__(self, url):
        self.log.append(url)
        got = self.table[url]
        if isinstance(got, int):
            raise _err(url, got)
        if got[0] == "doc":
            return 200, None, got[1], "application/pdf"
        return got[0], got[1], b"", "text/html"


def _held(ok=True):
    return lambda d, c: (ok, {"state": "full_text_held", "why": "identified (test)"} if ok else
                         {"why": "contains 2 of 12 distinctive title words"})


def _run(page, hops, held=True, text="Methods. Results. Discussion.", net=None):
    net = net or Net()
    return LR.find(page, PAGE_URL, SRC, _held(held), net, Hops(hops), text_of=lambda d, c: text), net


FULL = "https://www.example.gov.uk/uploads/full_report.pdf"
DOC = ("doc", b"%PDF-1.7 the report")


# ---- the 02zc page, as recorded ---------------------------------------------------------------------------------

def test_02zc_s006_is_held_via_the_full_report_link_with_its_licence_recorded():
    if not (PRIV / "full_report.pdf").exists():
        pytest.skip("the recorded 02zc page and PDF are in the private study folder only")
    import source_store as store
    src = next(s for s in json.loads((CASE / "sources.json").read_text())["sources"] if s["id"] == "S006")
    chain = json.loads((PRIV / "chain.json").read_text())
    pdf = (PRIV / "full_report.pdf").read_bytes()
    robots = {"https://www.gov.uk/robots.txt": (PRIV / "robots_www.gov.uk.txt").read_bytes()}
    hops = {c["url"]: (("doc", pdf) if c["status"] == 200 else (c["status"], c["location"])) for c in chain}
    res = LR.find((PRIV / "landing.html").read_bytes(), src["url"], src,
                  lambda d, c: store.held_check(SLUG, "S006", src, d, c), Net(robots), Hops(hops))
    rec = res["record"]
    assert rec["chosen"].endswith("/file/727787/Education_Rapid_Review_full_report.pdf")
    assert rec["chosen"].startswith("https://www.gov.uk/") and rec["chosen_by"] == "the only candidate"
    others = [c for c in rec["candidates"] if c["url"] != rec["chosen"]]
    assert len(others) == 2 and all(c["host"] == "assets.publishing.service.gov.uk" and not c["same_domain"]
                                    for c in others)
    assert [h["status"] for h in rec["chain"]] == [301, 301, 200]
    assert rec["final_url"] == ("https://assets.publishing.service.gov.uk/government/uploads/system/uploads/"
                                "attachment_data/file/738206/Education_Rapid_Review_full_report.pdf")
    assert all(h["robots"] in ("robots.txt allows it", "no robots.txt (HTTP 404)") for h in rec["chain"])
    assert all(h["tdm"] == "no tdmrep.json (HTTP 404)" for h in rec["chain"])
    assert res["check"]["state"] == "full_text_held"
    assert res["licence"]["line"] == "site licence Open Government Licence v3.0, document silent"


def test_the_strict_public_suffix_reading():
    assert LR.registrable("www.gov.uk") == "www.gov.uk"
    assert LR.registrable("assets.publishing.service.gov.uk") == "publishing.service.gov.uk"
    assert LR.registrable("gov.uk") is None and LR.registrable("service.gov.uk") is None
    assert LR.registrable("a.b.example.co.uk") == "example.co.uk" and LR.registrable("ebi.ac.uk") == "ebi.ac.uk"
    assert LR.registrable("x.y.ck") == "x.y.ck" and LR.registrable("www.ck") == "www.ck"    # wildcard, exception
    assert LR.psl_version()


# ---- the link ---------------------------------------------------------------------------------------------------

def test_two_links_both_containing_the_whole_title_are_refused():
    page = _page([(FULL, TITLE + " (full report)"), ("/uploads/full_report_v2.pdf", "Download: " + TITLE)])
    res, net = _run(page, {})
    assert "data" not in res and "2 candidates pass the title rule and 2 have link text containing the whole " \
        "title" in res["record"]["outcome"] and net.log == []


def test_of_two_candidates_the_only_one_containing_the_whole_title_is_taken():
    page = _page([("/uploads/summary.pdf", "Summary: what works to improve educational outcomes for people with "
                                           "disabilities in low and middle income countries"), (FULL, TITLE)])
    res, _net = _run(page, {FULL: DOC})
    assert res["record"]["chosen"] == FULL and res["record"]["chosen_by"].startswith("tie-break")


def test_no_title_matching_pdf_link_is_refused():
    res, _net = _run(_page([("/uploads/annual_accounts.pdf", "Annual accounts 2018")]), {})
    assert "data" not in res and res["record"]["outcome"].startswith("refused: no PDF link passing the title rule")


def test_a_link_on_another_registrable_domain_is_not_a_candidate():
    res, _net = _run(_page([("https://assets.publishing.service.gov.uk/x/full_report.pdf", TITLE)]), {})
    assert "data" not in res and not res["record"]["candidates"][0]["same_domain"]


def test_a_citation_pdf_url_meta_is_taken_first():
    meta = '<meta name="citation_pdf_url" content="/uploads/rea.pdf">'
    page = _page([(FULL, TITLE)], head=meta)
    res, _net = _run(page, {"https://www.example.gov.uk/uploads/rea.pdf": DOC})
    assert res["record"]["from"] == "citation_pdf_url meta" and res["final"].endswith("/uploads/rea.pdf")


# ---- redirects --------------------------------------------------------------------------------------------------

def test_a_redirect_to_a_host_the_page_links_pdfs_on_is_followed_and_recorded():
    other = "https://assets.publishing.service.gov.uk/f/full_report.pdf"
    page = _page([(FULL, TITLE), ("https://assets.publishing.service.gov.uk/f/summary.pdf", "Summary")])
    net = Net({"https://www.example.gov.uk/robots.txt": b"User-agent: *\nAllow: /\n"})
    res, net = _run(page, {FULL: (301, other), other: DOC}, net=net)
    assert res["final"] == other and [h["url"] for h in res["record"]["chain"]] == [FULL, other]
    assert "https://assets.publishing.service.gov.uk/robots.txt" in net.log           # the final host, before it
    assert "https://assets.publishing.service.gov.uk/.well-known/tdmrep.json" in net.log


def test_a_redirect_to_a_host_the_page_does_not_link_pdfs_on_is_refused():
    other = "https://cdn.elsewhere.example.com/full_report.pdf"
    hops = Hops({FULL: (302, other), other: DOC})
    res = LR.find(_page([(FULL, TITLE)]), PAGE_URL, SRC, _held(), Net(), hops, text_of=lambda d, c: "")
    assert "data" not in res and "another registrable domain on which the landing page links no PDF" in \
        res["record"]["outcome"]
    assert hops.log == [FULL] and res["record"]["chain"][-1]["url"] == other


def test_robots_disallowing_the_final_host_refuses_before_the_document_is_fetched():
    other = "https://assets.publishing.service.gov.uk/f/full_report.pdf"
    page = _page([(FULL, TITLE), ("https://assets.publishing.service.gov.uk/f/s.pdf", "Summary")])
    net = Net({"https://assets.publishing.service.gov.uk/robots.txt": b"User-agent: *\nDisallow: /\n"})
    hops = Hops({FULL: (301, other), other: DOC})
    res = LR.find(page, PAGE_URL, SRC, _held(), net, hops, text_of=lambda d, c: "")
    assert "data" not in res and "disallows" in res["record"]["outcome"] and hops.log == [FULL]


def test_a_wall_is_not_passed():
    res, _net = _run(_page([(FULL, TITLE)]), {FULL: 403})
    assert res["record"]["outcome"] == "refused: HTTP 403: a wall, not passed"


# ---- identity and licence ---------------------------------------------------------------------------------------

def test_a_pdf_failing_the_identity_check_is_refused():
    res, _net = _run(_page([(FULL, TITLE)]), {FULL: DOC}, held=False)
    assert "data" not in res and res["record"]["outcome"].startswith("refused: not the document")


def test_a_pdf_stating_all_rights_reserved_is_refused():
    res, _net = _run(_page([(FULL, TITLE)]), {FULL: DOC}, text="© 2018 The Authors. All rights reserved. Methods.")
    assert "data" not in res and res["record"]["outcome"].startswith("refused: the document says all rights reserved")


def test_a_pdf_stating_another_licence_is_refused():
    res, _net = _run(_page([(FULL, TITLE)]), {FULL: DOC}, text="This report is licensed under the Acme Licence 2.")
    assert "data" not in res and "not OGL or CC" in res["record"]["outcome"]


def test_a_pdf_stating_a_cc_licence_is_held_and_says_so():
    res, _net = _run(_page([(FULL, TITLE)]), {FULL: DOC}, text="Published under a CC BY 4.0 licence. Methods.")
    assert res["licence"]["line"] == "site licence Open Government Licence v3.0, document states CC BY 4.0"


def test_neither_the_site_nor_the_document_stating_a_licence_is_refused():
    res, _net = _run(_page([(FULL, TITLE)], footer=""), {FULL: DOC})
    assert "data" not in res and "neither the site nor the document states a licence" in res["record"]["outcome"]


# ---- through acquire_sources.main ------------------------------------------------------------------------------

def _acquire(tmp_path, monkeypatch, flag=True):
    import acquire_sources as AQ
    import source_store as store
    case = tmp_path / "issues" / "WHU-T-x"
    case.mkdir(parents=True)
    (case / "sources.json").write_text(json.dumps({"sources": [dict(SRC)]}))
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(store, "library_held", lambda slug: {})

    def held_check(slug, sid, s, data, ct):
        if data.startswith(b"<html"):
            return False, {"state": "blocked", "kind": "landing", "why": "landing — a page ABOUT the document"}
        return True, {"state": "full_text_held", "kind": "full_text", "why": "identified (test)"}
    monkeypatch.setattr(store, "held_check", held_check)
    monkeypatch.setattr(store, "text_of", lambda d, c, pages=8: ("Methods.", "text"))
    monkeypatch.setattr(store, "put", lambda slug, sid, data, **kw: {"file": "f", "sha256": "s", "bytes": len(data),
                                                                     "kind": "full_text", "kind_why": "x",
                                                                     "retrieved": "2026-11-26"})
    page = _page([(FULL, TITLE)])

    def fetch(url):
        if url == PAGE_URL:
            return page, "text/html", url
        raise _err(url, 404)
    monkeypatch.setattr(AQ, "fetch_retrying", fetch)
    monkeypatch.setattr(LR, "step", Hops({FULL: DOC}))
    monkeypatch.setenv("WHU_ORCH_STEP", "acquire")
    out = tmp_path / "acquire.json"
    rc = AQ.main(["x", "--no-summaries", "--out", str(out)] + (["--landing-pdfs"] if flag else []))
    return rc, json.loads((case / "sources.json").read_text())["sources"][0]["access"], json.loads(out.read_text())


def test_through_acquire_a_landing_page_is_held_through_its_pdf_link(tmp_path, monkeypatch):
    rc, acc, out = _acquire(tmp_path, monkeypatch)
    assert rc == 0 and out["held"] == ["S006"] and acc["state"] == "full_text_held"
    assert acc["held"]["route"] == "landing page PDF link: %s (the only candidate)" % FULL
    assert acc["held"]["licence"]["line"] == "site licence Open Government Licence v3.0, document silent"
    assert acc["held"]["redirects"] == [FULL] and acc["held"]["final_url"] == FULL
    assert acc["landing_pdf"]["outcome"].startswith("held from the landing page's PDF link")


def test_without_the_flag_the_landing_page_is_not_held(tmp_path, monkeypatch):
    rc, acc, out = _acquire(tmp_path, monkeypatch, flag=False)
    assert rc == 1 and "held" not in acc and "landing_pdf" not in acc


def test_the_orchestrated_acquire_step_runs_the_landing_route():
    from orch import steps as ST
    assert "--landing-pdfs" in ST.BY_NAME["acquire"].cmds[0]
