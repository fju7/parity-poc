"""Check-an-answer pilot v3 (study/whu-reliability/check_pilot/pipeline_v3.py), offline.
Design: docs/whu-check-an-answer-pilot.md §10. Every network step is a recorded reply; no model call."""
import html
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
FIX = Path(__file__).resolve().parent / "fixtures" / "whu_check"
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_v3 as P  # noqa: E402
import test_whu_check_pilot as T  # noqa: E402

SOURCE = (FIX / "source_PMC10771715.txt").read_text(encoding="utf-8")
PAGE = ("<html><head><title>A page</title></head><body>"
        + "".join("<p>%s</p>" % html.escape(p) for p in SOURCE.split("\n\n")) + "</body></html>").encode()
CF = (b"<html><head><title>Just a moment...</title></head><body>Enable JavaScript and cookies to continue"
      b"<script src='/cdn-cgi/challenge-platform/x'></script></body></html>")
JS_SHELL = b"<html><body><div id='root'></div><noscript>You need to enable JavaScript.</noscript></body></html>"
TITLE = "A comparison of the effectiveness of cognitive behavioural interventions"


def reply(body=PAGE, status=200, headers=None, ctype="text/html", final=None):
    return lambda url: {"status": status, "headers": headers or {}, "body": body, "final_url": final or url,
                        "content_type": ctype}


class Net:
    """Recorded network. `pages` maps an address (or a robots.txt / tdmrep.json address) to a reply;
    anything not listed answers 404. Every request is recorded."""

    def __init__(self, pages=None, rendered=None, epmc=None, unpaywall=None, crossref_title=None,
                 crossref_doi=None, crossref_abstract=None):
        self.pages, self.rendered_body = dict(pages or {}), rendered
        self._epmc, self._up, self._ct, self._cd, self._ca = epmc, unpaywall, crossref_title, crossref_doi, crossref_abstract
        self.got, self.rendered, self.lookups = [], [], []
        P._robots.clear()
        P._tdm.clear()

    def get(self, url):
        self.got.append(url)
        f = self.pages.get(url)
        if f is None:
            return {"status": 404, "headers": {}, "body": b"", "final_url": url, "content_type": "text/plain"}
        if isinstance(f, Exception):
            raise f
        return f(url)

    def render(self, url):
        self.rendered.append(url)
        return self.rendered_body

    def table(self):
        return {"get": self.get, "render": self.render,
                "crossref_doi": lambda t: (self._cd, "Crossref title match (recorded)") if self._cd else (None, "no match"),
                "crossref_title": lambda d: (self.lookups.append(("title", d)), self._ct)[1],
                "crossref_abstract": lambda d: self._ca,
                "epmc": lambda ids: (self.lookups.append(("epmc", json.dumps(ids, sort_keys=True))), self._epmc)[1],
                "unpaywall": lambda d: (self.lookups.append(("unpaywall", d)), self._up)[1]}

    def pages_got(self):
        return [u for u in self.got if not u.endswith(("/robots.txt", "/.well-known/tdmrep.json"))]


# ---------------- §10.6 claim selection ----------------

def test_claims_rank_numbers_then_cause_then_conclusions():
    assert P.claim_rank("Deaths fell by 20% in 3 trials [2].") == 0
    assert P.claim_rank("Group therapy reduced symptoms [2].") == 1
    assert P.claim_rank("Overall, the evidence is weak [1].") == 2
    assert P.claim_rank("The review was written in English [1].") == 3


def test_the_first_40_by_rank_and_the_users_ticks(tmp_path):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    md, cited, _ = P.adapt_answer(text)
    rows, refs = P.V1.sentences(md, cited, tmp_path)
    claims, rest, found = P.claims_v3(rows, refs, max_claims=2)
    assert found == 4 and len(claims) == 2 and len(rest) == 2
    assert all(c["rank"] == 0 for c in claims)
    assert [c["idx"] for c in claims] == sorted(c["idx"] for c in claims)       # shown in the answer's order
    pick = rest[0]["idx"]
    claims, _, _ = P.claims_v3(rows, refs, selected=[pick])
    assert [c["idx"] for c in claims] == [pick]


# ---------------- §10.3 (d): walls, robots.txt, TDM ----------------

def test_a_cloudflare_challenge_is_a_bot_wall_and_is_not_rendered_or_retried(tmp_path):
    u = "https://www.researchgate.net/publication/1_x"
    n = Net({u: reply(CF, 403, {"cf-mitigated": "challenge", "Server": "cloudflare"})})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["why_kind"] == P.R_WALL and n.rendered == [] and n.pages_got() == [u]


def test_an_aws_waf_challenge_is_a_bot_wall(tmp_path):
    u = "https://www.example-journal.org/2020/9/e1"
    n = Net({u: reply(b"", 202, {"x-amzn-waf-action": "challenge"})})
    assert P.source_v3(u, None, tmp_path, n.table())["why_kind"] == P.R_WALL


def test_a_challenge_in_place_of_robots_txt_is_a_bot_wall_and_the_page_is_not_asked(tmp_path):
    u = "https://ore.exeter.ac.uk/repository/handle/10871/1"
    n = Net({"https://ore.exeter.ac.uk/robots.txt": reply(b"", 202, {"x-amzn-waf-action": "challenge"})})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["why_kind"] == P.R_WALL and n.pages_got() == []


def test_robots_txt_disallowing_stops_before_the_page(tmp_path):
    u = "https://news.example.org/story"
    n = Net({"https://news.example.org/robots.txt": reply(b"User-agent: *\nDisallow: /", ctype="text/plain")})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["why_kind"] == P.R_ROBOTS and n.pages_got() == []


def test_a_tdmrep_reservation_stops_before_the_page(tmp_path):
    u = "https://agency.example.org/reports/r1.html"
    rules = json.dumps([{"location": "/reports/*", "tdm-reservation": 1}]).encode()
    n = Net({"https://agency.example.org/.well-known/tdmrep.json": reply(rules, ctype="application/json"), u: reply()})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["why_kind"] == P.R_TDM and n.pages_got() == []


def test_a_tdm_reservation_header_or_meta_on_the_page_means_it_is_not_used(tmp_path):
    u = "https://agency.example.org/page"
    n = Net({u: reply(PAGE, headers={"tdm-reservation": "1"})})
    assert P.source_v3(u, None, tmp_path, n.table())["why_kind"] == P.R_TDM
    meta = PAGE.replace(b"<head>", b'<head><meta name="tdm-reservation" content="1">')
    n = Net({u: reply(meta)})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["why_kind"] == P.R_TDM and not (tmp_path / "sources").exists()


# ---------------- §10.3 fetching: render, PDF, errors ----------------

def test_a_page_that_needs_javascript_is_rendered_once(tmp_path):
    u = "https://www.example.org/document/970236841"
    n = Net({u: reply(JS_SHELL)}, rendered=PAGE)
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["extent"] == "full text" and row["rule"] == P.RULE_C and n.rendered == [u]


def test_a_challenge_after_rendering_is_a_bot_wall(tmp_path):
    u = "https://www.example.org/document/1"
    n = Net({u: reply(JS_SHELL)}, rendered=CF)
    assert P.source_v3(u, None, tmp_path, n.table())["why_kind"] == P.R_WALL


def test_a_pdfs_text_is_extracted(tmp_path):
    pytest.importorskip("reportlab")
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for i, para in enumerate(SOURCE.split("\n\n")[:12]):
        y = 800
        for k in range(0, len(para), 90):
            c.drawString(40, y, para[k:k + 90])
            y -= 14
        c.showPage()
    c.save()
    u = "https://www.un.org/files/report.pdf"
    n = Net({u: reply(buf.getvalue(), ctype="application/pdf")})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["extent"] == "full text" and n.rendered == []
    text = (tmp_path / "sources" / (row["source_id"] + ".txt")).read_text()
    assert "\f" in text and P.location(text, text.index(SOURCE.split("\n\n")[2][:30]), True) == "page 3"


def test_http_errors_and_connection_failures_are_named(tmp_path):
    u = "https://lab.example.edu/file_url/471"
    n = Net({u: reply(b"Access denied", 403)})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["why_kind"] == "HTTP error" and "403" in row["extent_why"]
    n = Net({u: P.Refused(P.R_CONN, "connection failed: ConnectionError")})
    assert P.source_v3(u, None, tmp_path, n.table())["why_kind"] == P.R_CONN


# ---------------- §10.3 (a)-(c), barred publishers, identifiers ----------------

def test_barred_publishers_are_never_requested_not_even_for_an_abstract(tmp_path):
    for u in ("https://www.sciencedirect.com/science/article/pii/S0140673623012310",
              "https://doi.org/10.1016/j.eclinm.2024.102953", "https://www.nccn.org/guidelines/x"):
        n = Net(epmc={"abstractText": "x" * 400})
        row = P.source_v3(u, None, tmp_path, n.table())
        assert row["why_kind"] == P.R_BARRED and n.got == [] and ("epmc" not in [k for k, _ in n.lookups])


def test_a_publisher_copy_without_a_licence_is_not_read_but_a_repository_copy_is(tmp_path):
    u = "https://doi.org/10.1038/s41591-020-0001-1"
    repo = "https://eprints.example.ac.uk/1234/1/paper.pdf"
    pub_free = "https://journals.example.org/content/s41591-020-0001-1.pdf"
    up = {"oa_locations": [{"host_type": "publisher", "license": None, "url": pub_free},
                           {"host_type": "repository", "license": None, "url": repo}]}
    n = Net({u: reply(), pub_free: reply(), repo: reply()}, epmc=None, unpaywall=up)
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["extent"] == "full text" and row["rule"] == P.RULE_A and row["retrieved_from"] == repo
    assert u not in n.pages_got() and pub_free not in n.pages_got()


def test_a_publisher_copy_with_a_cc_licence_is_read(tmp_path):
    u = "https://journals.example.org/articles/10.3389/fpsyt.2019.00552/full"
    n = Net({u: reply()}, epmc={"license": "cc by", "doi": "10.3389/fpsyt.2019.00552"})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["rule"] == P.RULE_B and row["ids"] == {"doi": "10.3389/fpsyt.2019.00552"}


def test_without_a_licence_or_a_repository_copy_the_reason_is_publisher_copy_without_licence(tmp_path):
    u = "https://doi.org/10.1038/s41591-020-0001-1"
    n = Net({u: reply()}, unpaywall={"oa_locations": []})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["why_kind"] == P.R_NOLICENCE and n.pages_got() == []


def test_a_meta_doi_whose_crossref_title_disagrees_is_not_used_and_the_page_is_not_read(tmp_path):
    """v2 matched a news page to an unrelated Elsevier DOI and barred it. v3 does not use the DOI, and does
    not read the page either: it carries a citation_doi, so it is a journal page whose licence is unknown."""
    u = "https://alert.psychnews.org/2022/10/aacap-publishes-practice-guidelines.html"
    page = PAGE.replace(b"<head>", b'<head><meta name="citation_doi" content="10.1016/j.jaac.2026.07.1147">')
    n = Net({u: reply(page)}, crossref_title="Clinical practice guideline for the assessment of something else entirely")
    row = P.source_v3(u, "AACAP publishes practice guidelines on depressive disorders news", tmp_path, n.table())
    assert row["why_kind"] == P.R_NOLICENCE and row.get("ids") in ({}, None)
    assert not (tmp_path / "sources").exists()


def test_the_page_title_checks_a_meta_doi_when_the_answer_gives_none(tmp_path):
    u = "https://www.jmir.org/2022/4/e29842"
    page = PAGE.replace(b"<head>", b'<head><meta name="citation_title" content="Digital CBT for adolescents: '
                        b'a randomised trial"><meta name="citation_doi" content="10.2196/29842">')
    n = Net({u: reply(page)}, crossref_title="Digital CBT for adolescents: a randomised trial",
            epmc={"license": "cc by"})
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["ids"] == {"doi": "10.2196/29842"} and row["rule"] == P.RULE_B


# ---------------- §10.4 abstract ----------------

def test_the_abstract_is_used_when_no_full_text_is_held(tmp_path):
    u = "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    n = Net(epmc={"title": "A trial", "abstractText": "<p>" + SOURCE[:900] + "</p>"}, unpaywall=None)
    row = P.source_v3(u, None, tmp_path, n.table())
    assert row["extent"] == "abstract only" and row["abstract_only"] and row["rule"] == P.RULE_ABS


def test_an_abstract_only_verdict_is_labelled_and_absent_on_it_is_couldnt_check():
    doc = {"url": "u", "text": SOURCE[:900], "abstract_only": True}
    span = SOURCE[:900].split(". ")[0][:120]
    r = P.finish({"label": P.BACKED, "span": span, "citations": [{"url": "u"}], "reason": "Supported: ok"}, [doc], {})
    assert r["kind"] == P.ABSTRACT_ONLY and r["passage"]["quote"]
    r = P.finish({"label": P.COULDNT, "reason": "only the abstract could be read, and it does not state this",
                  "citations": [{"url": "u"}]}, [doc], {})
    assert r["reason_kind"] == P.R_ABSTRACT


# ---------------- §10.1 passages ----------------

def test_a_verdict_carries_its_passage_under_60_words_with_location_and_link():
    para = SOURCE.split("\n\n")[3]
    long_span = " ".join(para.split()[:70])
    doc = {"url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10771715/", "text": SOURCE}
    r = P.finish({"label": P.NOT_BACKED, "span": long_span, "citations": [{"url": doc["url"]}], "reason": "x"}, [doc], {})
    p = r["passage"]
    assert p["words"] == 59 and p["quote"].endswith("...") and len(p["quote"].replace(" ...", "").split()) == 59
    assert p["link"].startswith(doc["url"] + "#:~:text=") and p["location"]


def test_no_passage_means_couldnt_check():
    doc = {"url": "u", "text": SOURCE}
    for span in ("", "words that appear nowhere in the source at all"):
        r = P.finish({"label": P.BACKED, "span": span, "citations": [{"url": "u"}], "reason": "x"}, [doc], {})
        assert r["label"] == P.COULDNT and r["reason_kind"] == P.R_NOPASSAGE and r["verdict_withheld"] == P.BACKED


# ---------------- §10.5 a passage the user supplies ----------------

def test_a_supplied_passage_is_judged_alone_and_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    claim = {"idx": 1, "claim": "A network meta-analysis of 62 randomised trials with 6435 participants found that "
                                "most CBT formats, except remote CBT, did better than no intervention after treatment [1].",
             "context": "", "citations": [{"label": "[1]", "url": "https://x.org/a"}]}
    para = next(p for p in SOURCE.split("\n\n") if "except remote CBT" in p)
    c = T.client()
    r = P.check_supplied(claim, " ".join(para.split()[:300]), "https://x.org/a", c, T.count)
    assert r["kind"] == P.SUPPLIED and r["notice"] == P.SUPPLIED_NOTICE and r["label"] == P.BACKED
    assert "attempts" not in r and list(tmp_path.iterdir()) == []
    sent = c.messages.calls[0]
    assert para.split()[0] in sent and SOURCE.split("\n\n")[0][:40] not in sent
    with pytest.raises(ValueError):
        P.check_supplied(claim, "word " * 301, "https://x.org/a", c, T.count)


# ---------------- whole answer ----------------

def test_one_full_v3_check_on_the_recorded_answer(tmp_path):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    pmc = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10771715/"
    uea = "https://uea.ac.uk/about/news/article/technology-assisted-therapy-example"
    n = Net({pmc: reply(), uea: reply()})
    out = P.check(text, tmp_path, T.client(), T.count, net=n.table())
    by = {r["claim"][:40]: r for r in out["results"]}
    assert out["summary"].startswith("4 of 4 claims checked")
    for r in out["results"]:
        if r["label"] in (P.BACKED, P.NOT_BACKED):
            assert r["passage"]["words"] < 60 and r["passage"]["link"]
        if r["label"] == P.COULDNT:
            assert r["reason_kind"] in P.REASONS
    assert sum(r["label"] == P.NO_SOURCE for r in out["results"]) == 1
    man = out["manifest"]
    assert man[pmc]["rule"] == P.RULE_A and man[uea]["rule"] == P.RULE_C
    assert any(r["label"] == P.BACKED for r in by.values())


def test_the_cap_check_stops_the_parallel_judge(tmp_path):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    pmc = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10771715/"
    uea = "https://uea.ac.uk/about/news/article/technology-assisted-therapy-example"
    n = Net({pmc: reply(), uea: reply()})
    c = T.client()

    def stop(_w):
        raise P.Stop("over")
    with pytest.raises(P.Stop):
        P.check(text, tmp_path, c, T.count, net=n.table(), before_call=stop)
    assert c.messages.calls == []


def test_the_v3_samples():
    spec = importlib.util.spec_from_file_location("run_pilot_v3_t", ROOT / "study" / "whu-reliability" / "check_pilot" / "run_pilot_v3.py")
    R3 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R3)
    p = R3.draw_primary()
    assert p == R3.draw_primary() and len(p) == 8
    assert [s for _, s in p].count("Claude") == 3 and [s for _, s in p].count("Perplexity") == 3
    assert [s for _, s in p].count("Gemini") == 2 and ("WHU-Q1-04", "Gemini") not in p
    assert all(q.startswith("WHU-Q1-") for q, _ in p) and "ChatGPT" not in {s for _, s in p}
    assert len(set(R3.draw_secondary())) == 8 and all(q.startswith("WHU-S0") for q, _ in R3.draw_secondary())


def test_a_page_that_was_read_is_not_given_a_doi_by_a_title_lookup(tmp_path):
    u = "https://sdgs.un.org/sites/default/files/Thematic%20Report%20on%20Cities.pdf"
    n = Net({u: reply()}, crossref_doi="10.3402/gha.v2i0.1966")
    row = P.source_v3(u, "Thematic Report on Cities and global health", tmp_path, n.table())
    assert row["rule"] == P.RULE_C and not row.get("ids")


def test_a_title_lookup_finds_an_open_copy_when_the_cited_page_is_walled(tmp_path):
    u = "https://www.researchgate.net/publication/280116267_Xpert_versus_microscopy"
    repo = "https://europepmc.org/articles/PMC1/pdf"
    n = Net({u: reply(CF, 403, {"cf-mitigated": "challenge"}), repo: reply()}, crossref_doi="10.1371/journal.pmed.1",
            unpaywall={"oa_locations": [{"host_type": "repository", "license": None, "url": repo}]})
    row = P.source_v3(u, "Xpert MTB/RIF versus sputum microscopy", tmp_path, n.table())
    assert row["extent"] == "full text" and row["rule"] == P.RULE_A and row["retrieved_from"] == repo
