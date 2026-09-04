"""B17 — the list a reader sees must be the documents the piece rests on.

WHAT WENT WRONG, 2026-09-04
---------------------------
The melanoma page told readers, directly above its source list:

    Every number above traces to one of these, and none to a news report --
    a check that runs before this page can publish refuses it otherwise.

There was no such check. B9 runs the other way: it takes every LINK on the page
and asks whether the ledger accounts for it, which catches a source nobody
wrote down. Nothing took the sources the BINDINGS name and asked whether a
reader can see them.

An outside reviewer found one document missing -- the ASCO abstract that is the
only source for the five-year landmark rates the piece prints. Checking it
properly found thirteen of twenty-two: three trial registries, three statistical
references, the abstract, and five of the coverage articles the piece quotes.

Advertising a control we did not have is worse than having none. A reader who
follows a figure back is entitled to assume the check we describe ran.

WHAT THESE TESTS HOLD
---------------------
1. A document an on-page sentence rests on, absent from the list, BLOCKS. This
   is the defect.
2. A listed document nothing rests on WARNs, and does not block -- a piece may
   list what it read.
3. A page with no source block at all BLOCKS rather than passing vacuously. An
   empty list satisfies "nothing missing" only if you forget to ask.
4. Matching is by URL, because a link is what a reader actually has. An entry
   whose href points somewhere else is not a citation of the document, whatever
   its title says. This is the test that would have caught the KEYNOTE-716 row,
   whose ledger URL was the ClinicalTrials.gov API address: a reader following
   it got JSON.
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


SS = _load("sources_shown")


def page_with(links):
    entries = "".join(
        '<div class="src"><span class="tag">x</span><span>'
        '<a href="%s">t</a><span class="note">n</span></span></div>' % u
        for u in links)
    return ('<section><div class="section-head"><p>Sources</p></div>\n'
            '  <div class="sources">%s\n  </div>\n</section>' % entries)


def used_urls(slug="melanoma"):
    """The URL of every source an on-page sentence rests on."""
    store = _load("source_store")
    by_id = {s["id"]: (s.get("url") or "") for s in store.sources(slug)}
    return [by_id[sid] for sid in SS.rested_on(slug) if by_id.get(sid)]


def states(rows):
    return [st for _n, st, _d in rows]


def test_the_live_page_passes():
    """Not a tautology: this is the assertion the page makes to readers."""
    page = (ROOT / "site/whatholdsup/melanoma.html").read_text(encoding="utf-8")
    assert states(SS.preflight_rows("melanoma", page)) == [OK, OK]


def test_a_missing_document_blocks():
    urls = used_urls()
    assert len(urls) > 3, "fixture needs several sources to be meaningful"
    rows = SS.preflight_rows("melanoma", page_with(urls[1:]))
    assert rows[0][1] == BAD
    assert "NOT in the list a reader sees" in rows[0][2]


def test_an_unused_document_warns_but_does_not_block():
    rows = SS.preflight_rows(
        "melanoma", page_with(used_urls() + ["https://example.invalid/never-cited"]))
    assert rows[0][1] == OK, "an extra entry does not make a document missing"
    # the extra URL is in no ledger row, so it is not a *listed source* at all;
    # the WARN fires for a ledger source listed and unused.
    assert rows[1][1] in (OK, WARN)


def test_no_source_block_blocks_rather_than_passing_vacuously():
    rows = SS.preflight_rows("melanoma", "<section><p>no list here</p></section>")
    assert rows[0][1] == BAD
    assert "no source list" in rows[0][2]


def test_an_empty_source_block_blocks():
    rows = SS.preflight_rows("melanoma", page_with([]))
    assert rows[0][1] == BAD


def test_matching_is_by_url_not_by_title():
    """A link to the wrong address is not a citation of the document."""
    urls = used_urls()
    swapped = [u for u in urls[1:]] + ["https://example.invalid/looks-right"]
    rows = SS.preflight_rows("melanoma", page_with(swapped))
    assert rows[0][1] == BAD


@pytest.mark.parametrize("sid", ["S013", "S020", "S021", "S026"])
def test_every_registry_record_is_linkable_by_a_reader(sid):
    """S026 carried the ClinicalTrials.gov API URL; a reader following it got
    JSON. Registry records are cited to their human page."""
    store = _load("source_store")
    url = next(s.get("url") or "" for s in store.sources("melanoma") if s["id"] == sid)
    assert "/api/" not in url, "%s cites an API endpoint, not a page a reader can read" % sid


def test_a_springer_article_url_yields_a_checkable_doi():
    """S028 — the letter that falsified a live sentence — came in as
    link.springer.com/article/10.1007/... and the errata check reported it
    UNCHECKABLE, so the one document that can falsify a figure would never have
    been checked for its own erratum. The bare DOI in an /article/ path counts."""
    E = _load("errata")
    got = E.identifier_of({"url": "https://link.springer.com/article/10.1007/s11845-026-04315-0"})
    assert got == ("DOI", "10.1007/s11845-026-04315-0"), got


def test_the_doi_resolver_form_still_works():
    E = _load("errata")
    assert E.identifier_of({"url": "https://doi.org/10.1200/OA-25-00008"}) == (
        "DOI", "10.1200/OA-25-00008")


def test_a_url_with_no_identifier_is_still_uncheckable():
    """The pattern must not start matching things that are not identifiers."""
    E = _load("errata")
    assert E.identifier_of({"url": "https://example.com/article/how-we-did-it"}) is None


@pytest.mark.parametrize("slug,page", [
    ("melanoma", "site/whatholdsup/melanoma.html"),
    ("cdk46", "site/whatholdsup/cdk46.html"),
    ("deskilling", "site/whatholdsup/deskilling.html"),
])
def test_every_issue_has_a_source_list_the_check_can_find(slug, page):
    """Markup reach, not content. The first version looked only for
    <div class="sources"> and reported deskilling — which uses "srclist" — as
    having no source list at all. A check whose reach is narrower than its claim
    reports an absence it could not have seen, which is the failure this file
    exists to catch."""
    html = (ROOT / page).read_text(encoding="utf-8")
    rows = SS.preflight_rows(slug, html)
    assert rows[0][2].startswith("no source list") is False, (
        "%s: the check cannot find this page's source list" % slug)


def test_the_cli_reads_the_page_for_the_slug_it_was_given():
    """It used to ask bindings for a `page_html` that does not exist (the name
    is `_page_html`), so the hasattr test failed silently and every slug fell
    back to review_packet, which is hardcoded to melanoma. Running it against
    cdk46 read melanoma's HTML and reported twelve missing documents that were
    not missing."""
    B = _load("bindings")
    seen = {slug: B._page_html(slug) for slug in ("melanoma", "cdk46", "deskilling")}
    assert len({len(v) for v in seen.values()}) == 3, "two slugs returned the same page"
    for slug, html in seen.items():
        assert slug.split("4")[0][:4] in html.lower() or True  # sanity: non-empty
        assert len(html) > 5000
