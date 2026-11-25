"""Advisor's rulings after orchestrator trial 1 attempt 24 (2026-11-24): attempt 24 stopped twice at discover on
Europe PMC (a read timeout, then HTTP 503), and each resume paid for a new model call.

  1. discovery is split: `discover` makes and saves the proposals (sha256), `confirm` looks them up; a resume after
     a registry outage repeats `confirm` alone and reuses the saved proposals;
  2. identity lookups fall back from Europe PMC to PubMed and Crossref; a retraction / correction status needs
     answers from two of Europe PMC, PubMed and Crossref, else the run stops "registry unavailable"; every status
     records which registries answered; an outage a fallback answered for is marked covered and does not stop the run.

All offline: registries are fakes or recorded replies.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import orchestrator as O  # noqa: E402
import registries as RG  # noqa: E402
from orch import checkpoint as CP  # noqa: E402
from orch import corrections as CR  # noqa: E402
from orch import registry_http as RH  # noqa: E402
from orch import resolve as RV  # noqa: E402
from orch import steps as ST  # noqa: E402

FX = ROOT / "backend/tests/fixtures/whu_orch_corrections"
TITLE = "Effectiveness of interventions for improving educational outcomes for people with disabilities"


def down(reg, url="https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x"):
    return RG.Answer(reg, False, why="%s did not answer (HTTP 503)" % reg, url=url)


def rec(title=TITLE, authors="Hunt X, Saran A", year="2025", doi="10.1002/cl2.70016", **kw):
    return dict({"title": title, "authorString": authors, "pubYear": year, "doi": doi}, **kw)


# ---------------------------------------------------------------- the outage log: covered outages do not stop a run

def test_a_covered_outage_does_not_stop_the_run_and_an_uncovered_one_does(tmp_path):
    log = tmp_path / "u.jsonl"
    RH.install(log)
    try:
        log.write_text("\n".join(json.dumps(r) for r in [
            {"url": "https://www.ebi.ac.uk/a", "error": "HTTPError: 503", "attempts": 4},
            {"url": "https://www.ebi.ac.uk/b", "error": "HTTPError: 503", "attempts": 4}]) + "\n")
        RH.covered("https://www.ebi.ac.uk/a", ["PubMed", "Crossref"])
        assert [o["url"] for o in RH.outages(log)] == ["https://www.ebi.ac.uk/b"]
        cov = RH.covered_outages(log)
        assert [o["url"] for o in cov] == ["https://www.ebi.ac.uk/a"] and cov[0]["covered_by"] == ["PubMed", "Crossref"]
        RH.covered("https://www.ebi.ac.uk/a", ["PubMed"])           # a cover with no outage left covers nothing
        assert [o["url"] for o in RH.outages(log)] == ["https://www.ebi.ac.uk/b"]
    finally:
        RH.uninstall()


def test_the_step_stop_reads_only_uncovered_outages(tmp_path):
    log = tmp_path / "u.jsonl"
    log.write_text(json.dumps({"url": "https://www.ebi.ac.uk/a", "error": "HTTPError: 503", "attempts": 4}) + "\n" +
                   json.dumps({"covered": "https://www.ebi.ac.uk/a", "by": ["PubMed", "Crossref"]}) + "\n")
    ctx = SimpleNamespace(unavailable_log=log, model_log=tmp_path / "m.jsonl")
    O._stop_if_unavailable(ctx, ST.BY_NAME["confirm"])               # no stop
    with open(log, "a") as fh:
        fh.write(json.dumps({"url": "https://www.ebi.ac.uk/b", "error": "HTTPError: 503", "attempts": 4}) + "\n")
    with pytest.raises(O.RunStop, match="confirm: registry unavailable; run again later"):
        O._stop_if_unavailable(ctx, ST.BY_NAME["confirm"])


# ---------------------------------------------------------------- the registry clients: answered or not

def test_an_outage_is_not_an_answer_and_a_404_is(monkeypatch):
    def raising(code):
        def f(req, timeout=None, **kw):
            raise urllib.error.HTTPError(req.full_url, code, "x", None, io.BytesIO(b""))
        return f
    monkeypatch.setattr(RG.urllib.request, "urlopen", raising(503))
    a = RG.crossref_work("10.1/x")
    assert not a.answered and a.url.startswith("https://api.crossref.org/works/")
    monkeypatch.setattr(RG.urllib.request, "urlopen", raising(429))
    assert not RG.epmc_title("x").answered
    monkeypatch.setattr(RG.urllib.request, "urlopen", raising(404))
    a = RG.crossref_work("10.1/x")
    assert a.answered and a.record is None                           # "no such DOI" is an answer
    monkeypatch.setattr(RG, "PAUSE", {})


def test_the_client_is_named_honestly_and_no_key_is_sent(monkeypatch):
    seen = []

    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"esearchresult": {"idlist": []}}'

    def f(req, timeout=None, **kw):
        seen.append((req.full_url, req.get_header("User-agent")))
        return R()
    monkeypatch.setattr(RG.urllib.request, "urlopen", f)
    monkeypatch.setattr(RG, "PAUSE", {})
    RG.pubmed_title(TITLE)
    url, ua = seen[0]
    assert ua == "WHU-fetch/1.0 (automated research client)" and "tool=whu-fetch" in url
    assert "api_key" not in url and "email" not in url and "@" not in ua


def test_pubmed_title_terms_drop_stopwords_and_punctuation():
    t = RG.title_term("Barriers to, and facilitators of, education: a review")
    assert t == "Barriers[ti] AND facilitators[ti] AND education[ti] AND review[ti]"


def test_a_pubmed_record_gives_its_status_fields():
    got = RG.parse_efetch((FX / "pubmed_efetch_9500320_no_abstract.xml").read_text())
    assert got["pmid"] == "9500320" and "Retracted Publication" in got["pubtypes"]
    assert got["doi"] == "10.1016/s0140-6736(97)11096-0"            # the record's own, not a cited work's
    assert any(l["type"] == "RetractionIn" for l in got["links"]) or "Retracted Publication" in got["pubtypes"]


def test_crossref_and_pubmed_records_take_europe_pmcs_field_names():
    cr = RG.epmc_shaped_from_crossref({"DOI": "10.1002/cl2.70016", "title": [TITLE], "type": "journal-article",
                                       "author": [{"family": "Hunt", "given": "Xanthe"}, {"family": "Saran"}],
                                       "issued": {"date-parts": [[2025, 2, 6]]},
                                       "container-title": ["Campbell Systematic Reviews"]})
    assert cr["authorString"] == "Hunt X, Saran" and cr["pubYear"] == "2025" and cr["registry"] == "crossref"
    pm = RG.epmc_shaped_from_summary({"uid": "38292375", "title": TITLE + ".", "pubdate": "2024 Jan",
                                      "authors": [{"name": "Smith J"}],
                                      "articleids": [{"idtype": "doi", "value": "10.1/x"},
                                                     {"idtype": "pmc", "value": "PMC1234567"}]})
    assert pm["pmid"] == "38292375" and pm["pmcid"] == "PMC1234567" and pm["doi"] == "10.1/x"


# ---------------------------------------------------------------- identity: Europe PMC, then PubMed and Crossref

def _fake(epmc=None, pubmed=None, crossref=None, pmcid=None):
    covered = []
    ns = SimpleNamespace(
        epmc_title=lambda t: epmc, epmc_id=lambda k, v: epmc,
        pubmed_title=lambda t: pubmed, pubmed_pmcid=lambda p: pmcid or pubmed,
        crossref_title=lambda t, a=None: crossref,
        covered=lambda a, by: covered.append((a.url, list(by))))
    return ns, covered


def test_a_europe_pmc_outage_leaves_pubmed_and_crossref_to_confirm():
    ns, cov = _fake(down(RG.EUROPE_PMC), RG.Answer(RG.PUBMED, True, why="no record"),
                    RG.Answer(RG.CROSSREF_NAME, True, records=[dict(rec(), registry="crossref")]))
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert isinstance(got, RV.Found) and got.registry == "crossref" and got.identifier.value == "10.1002/cl2.70016"
    assert got.extra["record"]["registry"] == "crossref"
    rows = got.extra["answered"]
    assert [(r["registry"], r["answered"], r.get("matched")) for r in rows] == [
        ("Europe PMC", False, None), ("PubMed", True, False), ("Crossref", True, True)]
    assert cov and cov[0][1] == ["PubMed", "Crossref"]                # the Europe PMC outage is covered


def test_all_three_registries_are_asked_every_time_and_the_first_match_in_order_is_the_source():
    """Ruling 3 after the fallback build: not only as a fallback."""
    asked = []
    ns, cov = _fake()
    ns.epmc_title = lambda t: asked.append("epmc") or RG.Answer(RG.EUROPE_PMC, True, rec(), [rec()])
    ns.pubmed_title = lambda t: asked.append("pubmed") or RG.Answer(RG.PUBMED, True, records=[
        dict(rec(pmid="1"), registry="pubmed")])
    ns.crossref_title = lambda t, a=None: asked.append("crossref") or RG.Answer(RG.CROSSREF_NAME, True, records=[])
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert asked == ["epmc", "pubmed", "crossref"] and got.registry == "europepmc" and cov == []
    assert got.extra["matched_by"] == ["europepmc", "pubmed"]
    assert [r.get("matched") for r in got.extra["answered"]] == [True, True, False]


def test_another_matching_registrys_identifiers_are_merged_with_their_provenance():
    """Found in rehearsal: Europe PMC's record of S004 had no PMCID and PubMed's had one."""
    ns, cov = _fake()
    ns.epmc_title = lambda t: RG.Answer(RG.EUROPE_PMC, True, rec(), [rec()])
    ns.pubmed_title = lambda t: RG.Answer(RG.PUBMED, True, records=[dict(rec(pmid="41", pmcid="PMC13662523"),
                                                                        registry="pubmed")])
    ns.crossref_title = lambda t, a=None: RG.Answer(RG.CROSSREF_NAME, True, records=[])
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert got.registry == "europepmc" and got.extra["pmcid"] == "PMC13662523" and got.extra["pmid"] == "41"
    assert got.extra["identifiers_from"] == {"pmcid": "pubmed", "pmid": "pubmed"}   # the registry ids src uses
    ns.pubmed_title = lambda t: RG.Answer(RG.PUBMED, True, records=[dict(rec(doi="10.9/other", pmcid="PMC9"),
                                                                        registry="pubmed")])
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert "pmcid" not in got.extra                                   # a different DOI is a different work


def test_a_protocol_is_never_taken_for_the_work_and_an_exact_title_comes_first():
    """Found in rehearsal: Crossref's first agreeing candidate for an evidence and gap map was its PROTOCOL."""
    t = "Teacher professional development for disability inclusion: an evidence and gap map"
    ns, cov = _fake(down(RG.EUROPE_PMC), down(RG.PUBMED), RG.Answer(RG.CROSSREF_NAME, True, records=[
        dict(rec(title="PROTOCOL: " + t, doi="10.1002/cl2.1201"), registry="crossref"),
        dict(rec(title=t + " and more", doi="10.1002/cl2.9"), registry="crossref"),
        dict(rec(title=t, doi="10.1002/cl2.1287"), registry="crossref")]))
    got = RV.search(t, "Hunt", 2025, registries=ns)
    assert got.identifier.value == "10.1002/cl2.1287"
    got = RV.search("PROTOCOL: " + t, "Hunt", 2025, registries=ns)   # a proposal that names a protocol keeps it
    assert got.identifier.value == "10.1002/cl2.1201"

def test_a_fallback_record_is_held_to_the_same_checks():
    ns, cov = _fake(down(RG.EUROPE_PMC), RG.Answer(RG.PUBMED, True, records=[dict(rec(authors="Jones K"),
                                                                                  registry="pubmed")]),
                    RG.Answer(RG.CROSSREF_NAME, True, records=[]))
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert isinstance(got, RV.Unresolved) and got.status == "NOT_FOUND" and "first author" in got.reason
    assert cov                                                        # answered (no agreeing record): covered


def test_no_registry_answering_leaves_the_outage_to_stop_the_run():
    ns, cov = _fake(down(RG.EUROPE_PMC), down(RG.PUBMED), down(RG.CROSSREF_NAME))
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert isinstance(got, RV.Unresolved) and got.status == "REGISTRY_UNAVAILABLE" and cov == []


def test_an_outage_is_covered_when_any_other_registry_answered():
    ns, cov = _fake(down(RG.EUROPE_PMC), down(RG.PUBMED, "https://eutils.ncbi.nlm.nih.gov/x"),
                    RG.Answer(RG.CROSSREF_NAME, True, records=[dict(rec(), registry="crossref")]))
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert got.registry == "crossref"
    assert sorted(u for u, _ in cov) == sorted(["https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x",
                                                 "https://eutils.ncbi.nlm.nih.gov/x"])


def test_a_pmc_article_falls_back_to_pubmed_by_its_pmcid():
    ns, cov = _fake(down(RG.EUROPE_PMC), pmcid=RG.Answer(RG.PUBMED, True, records=[dict(
        rec(pmid="1", pmcid="PMC10844053"), registry="pubmed")]))
    got = RV.search_pmcid("PMC10844053", TITLE, "Hunt", 2025, registries=ns)
    assert isinstance(got, RV.Found) and got.registry == "pubmed" and got.extra["pmcid"] == "PMC10844053"


def test_confirm_records_which_registries_answered():
    found = RV.Found(RV.Ident("doi", "10.1002/cl2.70016"), TITLE, "crossref",
                     {"answered": [{"registry": "Europe PMC", "answered": False},
                                   {"registry": "PubMed", "answered": True},
                                   {"registry": "Crossref", "answered": True}]})
    srcs, _ = O.resolve_proposals([{"title": TITLE, "first_author": "Hunt", "year": 2025, "type": "review",
                                    "url": ""}], lambda t, a, y, k: found)
    assert srcs[0]["registry"] == "crossref" and len(srcs[0]["identity_lookup"]) == 3
    assert O.registries_answered(srcs, []) == ["PubMed", "Crossref"]   # the page says what was searched
    assert O.registries_answered([{"title": "x"}], []) == ["Europe PMC"]


# ---------------------------------------------------------------- status: two of three registries

SRC = {"id": "S001", "type": "review", "title": TITLE, "doi": "10.1002/cl2.70016"}


def test_a_status_with_europe_pmc_down_comes_from_pubmed_and_crossref(monkeypatch):
    cov = []
    monkeypatch.setattr(RG, "covered", lambda a, by: cov.append((a.registry, list(by))))
    pm = {"title": TITLE, "pubtypes": ["Journal Article"], "doi": "10.1002/cl2.70016",
          "links": [{"type": "ErratumIn", "pmid": "999"}]}
    st = CR.status(SRC, lambda k, v: down(RG.EUROPE_PMC),
                   lambda d: RG.Answer(RG.CROSSREF_NAME, True, {"title": [TITLE], "relation": {}}),
                   lambda k, v: RG.Answer(RG.PUBMED, True, pm))
    assert st["retracted"] is False and st["checkable"] is True and st["state"] == "checked"
    assert st["corrections"] == [{"id": "999", "registry": "MED", "type": "ErratumIn", "found_by": ["PubMed"]}]
    assert [(r["registry"], r["answered"], r["record"]) for r in st["registries"]] == [
        ("Europe PMC", False, None), ("PubMed", True, "found"), ("Crossref", True, "found")]
    assert st["status_from"] == ["PubMed", "Crossref"]                 # every registry that returned the record
    assert st["registries"][1]["findings"] == [] and "ErratumIn" in str(st["corrections"])
    assert cov == [("Europe PMC", ["PubMed", "Crossref"])]


def test_a_status_from_one_registry_stops_the_run(monkeypatch):
    monkeypatch.setattr(RG, "covered", lambda a, by: pytest.fail("nothing may be covered"))
    with pytest.raises(CR.RegistryUnavailable, match="1 of 3 registries answered \\(Crossref\\)"):
        CR.status(SRC, lambda k, v: down(RG.EUROPE_PMC), lambda d: RG.Answer(RG.CROSSREF_NAME, True, {}),
                  lambda k, v: down(RG.PUBMED))


def test_a_pubmed_retraction_link_retracts():
    pm = {"title": TITLE, "pubtypes": ["Journal Article"], "links": [{"type": "RetractionIn", "pmid": "5"}]}
    st = CR.status(SRC, lambda k, v: RG.Answer(RG.EUROPE_PMC, True, None, why="no record"),
                   lambda d: RG.Answer(RG.CROSSREF_NAME, True, None, why="no record"),
                   lambda k, v: RG.Answer(RG.PUBMED, True, pm))
    assert st["retracted"] is True and "PubMed: RetractionIn 5" in st["why"]


def test_acquire_stops_when_only_one_registry_answers_a_status(tmp_path):
    c = tmp_path / "issues" / "WHU-T-x"
    (c / "orchestrator").mkdir(parents=True)
    s = dict(SRC, access={"state": "full_text_held", "held": {"file": "f"}})
    (c / "sources.json").write_text(json.dumps({"sources": [s]}))
    ctx = SimpleNamespace(case=c, lookup=lambda k, v: down(RG.EUROPE_PMC),
                          crossref=lambda d: RG.Answer(RG.CROSSREF_NAME, True, {}),
                          pubmed=lambda k, v: down(RG.PUBMED), fulltext=None)
    with pytest.raises(O.RunStop, match="acquire: registry unavailable; run again later"):
        O.code_acquire(ctx, ST.BY_NAME["acquire"])


def test_the_errata_sweep_in_an_orchestrated_run_needs_two_registries(monkeypatch):
    import errata as E
    monkeypatch.setattr(RG, "covered", lambda a, by: None)
    pm = {"title": TITLE, "pubtypes": [], "links": [{"type": "UpdateIn", "pmid": "77"}], "doi": "10.1002/cl2.70016"}
    row = E.orchestrated_row(SRC, "DOI", "10.1002/cl2.70016",
                             (lambda k, v: down(RG.EUROPE_PMC), lambda k, v: RG.Answer(RG.PUBMED, True, pm),
                              lambda d: RG.Answer(RG.CROSSREF_NAME, True, {"title": [TITLE]})))
    assert row["state"] == "AMENDED" and row["amendments"][0]["type"] == "Update in"   # errata's own names
    assert row["index"] == "PubMed + Crossref"
    row = E.orchestrated_row(SRC, "DOI", "10.1002/cl2.70016",
                             (lambda k, v: down(RG.EUROPE_PMC), lambda k, v: down(RG.PUBMED),
                              lambda d: RG.Answer(RG.CROSSREF_NAME, True, {"title": [TITLE]})))
    assert row["state"] == "UNCHECKED" and "1 of 3 registries answered" in row["why"]



# ---------------------------------------------------------------- ruling 4 after the fallback build: status needs a record

def test_two_answering_with_no_record_is_not_checkable_and_never_clean():
    st = CR.status(SRC, lambda k, v: RG.Answer(RG.EUROPE_PMC, True, None, why="no record"),
                   lambda d: RG.Answer(RG.CROSSREF_NAME, True, None, why="HTTP 404"),
                   lambda k, v: RG.Answer(RG.PUBMED, True, None, why="no record"))
    assert st["checkable"] is False and st["retracted"] is None and st["state"] == CR.NOT_CHECKABLE
    assert st["state"] == "no registry record; retraction status not checkable" and st["status_from"] == []


def test_a_source_with_no_identifier_is_not_checkable():
    st = CR.status({"id": "S9", "title": "An agency page", "url": "https://www.who.int/x"})
    assert st["checkable"] is False and st["retracted"] is None and st["state"] == CR.NOT_CHECKABLE


def test_a_crossref_record_of_another_work_is_not_used():
    st = CR.status(SRC, lambda k, v: RG.Answer(RG.EUROPE_PMC, True, rec()),
                   lambda d: RG.Answer(RG.CROSSREF_NAME, True, {"title": ["Fish oils and the heart"],
                                                                 "updated-by": [{"type": "retraction",
                                                                                 "DOI": "10.9/r"}]}),
                   lambda k, v: RG.Answer(RG.PUBMED, True, None, why="no record"))
    assert st["retracted"] is False and st["status_from"] == ["Europe PMC"]
    assert st["registries"][2]["record"] == "none" and "not used" in st["registries"][2]["why"]


def test_a_correction_two_registries_report_is_one_correction_with_both_as_provenance():
    epmc = dict(rec(), pmid="12", commentCorrectionList={"commentCorrection": [
        {"type": "Erratum in", "id": "999", "source": "MED"}]})
    pm = {"title": TITLE, "pubtypes": [], "links": [{"type": "ErratumIn", "pmid": "999"}]}
    st = CR.status(SRC, lambda k, v: RG.Answer(RG.EUROPE_PMC, True, epmc),
                   lambda d: RG.Answer(RG.CROSSREF_NAME, True, None, why="HTTP 404"),
                   lambda k, v: RG.Answer(RG.PUBMED, True, pm))
    assert st["corrections"] == [{"id": "999", "registry": "MED", "type": "Erratum in",
                                  "found_by": ["Europe PMC", "PubMed"]}]
    assert st["status_from"] == ["Europe PMC", "PubMed"]


def test_the_errata_row_with_no_record_anywhere_says_not_checkable(monkeypatch):
    import errata as E
    monkeypatch.setattr(RG, "covered", lambda a, by: None)
    row = E.orchestrated_row(SRC, "DOI", "10.1002/cl2.70016",
                             (lambda k, v: RG.Answer(RG.EUROPE_PMC, True, None), lambda k, v: RG.Answer(RG.PUBMED, True),
                              lambda d: RG.Answer(RG.CROSSREF_NAME, True, None)))
    assert row["state"] == "UNCHECKED" and row["why"].startswith("no registry record; retraction status not checkable")


# ---------------------------------------------------------------- PubMed paced in every mode, across processes

def test_ncbi_requests_are_paced_across_processes(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_NCBI_PACE_FILE", str(tmp_path / "pace"))
    clock, slept = [100.0], []

    def sleep(s):
        slept.append(s)
        clock[0] += s
    assert RG.ncbi_pace(lambda: clock[0], sleep) == 0
    clock[0] += 0.1
    w = RG.ncbi_pace(lambda: clock[0], sleep)
    assert abs(w - (RG.NCBI_INTERVAL - 0.1)) < 1e-6                   # waits out the interval
    assert 1 / RG.NCBI_INTERVAL < 3                                   # under NCBI's 3 a second with no API key
    clock[0] += 5
    assert RG.ncbi_pace(lambda: clock[0], sleep) == 0
    assert float((tmp_path / "pace").read_text()) == clock[0]          # one file, read by every process


def test_every_ncbi_request_goes_through_the_pacer_and_no_other_does(monkeypatch):
    paced = []
    monkeypatch.setattr(RG, "ncbi_pace", lambda: paced.append(1) or 0.0)

    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"{}"
    monkeypatch.setattr(RG.urllib.request, "urlopen", lambda req, timeout=None, **kw: R())
    monkeypatch.setattr(RG, "PAUSE", {})
    RG.pubmed_title(TITLE)
    RG.pmc_fulltext("PMC1")
    n = len(paced)
    RG.crossref_work("10.1/x")
    RG.epmc_title(TITLE)
    assert n == 2 and len(paced) == 2


# ---------------------------------------------------------------- ruling 2 after the fallback build: NCBI PMC full text

def _urlopen_returning(body: bytes, code: int = 200):
    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return body

    def f(req, timeout=None, **kw):
        if code != 200:
            raise urllib.error.HTTPError(req.full_url, code, "x", None, io.BytesIO(b""))
        return R()
    return f


JATS = (b'<pmc-articleset><article><front><article-meta><title-group><article-title>T</article-title></title-group>'
        b'<permissions><license><ali:license_ref>https://creativecommons.org/licenses/by/4.0/</ali:license_ref>'
        b'<license-p>This is an open access article.</license-p></license></permissions></article-meta></front>'
        b'<body><p>Results.</p></body></article></pmc-articleset>')


def test_pmc_full_text_is_used_only_with_a_body_and_a_licence(monkeypatch):
    monkeypatch.setattr(RG, "ncbi_pace", lambda: 0.0)
    monkeypatch.setattr(RG.urllib.request, "urlopen", _urlopen_returning(JATS))
    a = RG.pmc_fulltext("PMC11799928")
    assert a.answered and a.record["licence"]["url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert "db=pmc" in a.url and "id=11799928" in a.url and "tool=whu-fetch" in a.url
    monkeypatch.setattr(RG.urllib.request, "urlopen", _urlopen_returning(
        b"<pmc-articleset><article><front/><!--The publisher of this article does not allow downloading of the "
        b"full text in XML form.--></article></pmc-articleset>"))
    a = RG.pmc_fulltext("PMC8356339")
    assert a.answered and a.record is None and "does not allow downloading" in a.why
    monkeypatch.setattr(RG.urllib.request, "urlopen", _urlopen_returning(JATS.replace(b"<license>", b"<x>")
                                                                         .replace(b"</license>", b"</x>")))
    a = RG.pmc_fulltext("PMC1")
    assert a.answered and a.record is None and "no licence statement" in a.why
    monkeypatch.setattr(RG.urllib.request, "urlopen", _urlopen_returning(b"", 503))
    assert not RG.pmc_fulltext("PMC1").answered


def test_the_acquire_fallback_covers_europe_pmc_only_when_pmc_answers(monkeypatch):
    import acquire_sources as AQ
    cov = []
    monkeypatch.setattr(RG, "covered", lambda a, by: cov.append((a.url, list(by))))
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1/fullTextXML"
    miss = [down(RG.EUROPE_PMC, url)]
    data, ct, final, rec_ = AQ.pmc_fallback(url, miss, lambda p: RG.Answer("PMC", True, {
        "xml": JATS.decode(), "licence": {"url": "https://creativecommons.org/licenses/by/4.0/"}}, url="u"))
    assert data == JATS and ct == "application/xml" and rec_["licence"]["url"].endswith("by/4.0/")
    assert cov == [(url, ["PMC"])]
    cov.clear()
    data, *_ = AQ.pmc_fallback(url, miss, lambda p: RG.Answer("PMC", False, why="HTTP 503", url="u"))
    assert data is None and cov == []                                 # nothing answered: the outage stops the run
    data, _ct, _f, rec_ = AQ.pmc_fallback(url, miss, lambda p: RG.Answer("PMC", True, why="not served: x", url="u"))
    assert data is None and cov == [(url, ["PMC"])] and rec_["why"] == "not served: x"


def test_a_correction_notice_falls_back_to_pubmed_and_pmc(monkeypatch):
    calls = []
    monkeypatch.setattr(RG, "covered", lambda a, by: calls.append(list(by)))
    monkeypatch.setattr(RG, "epmc_id", lambda k, v: down(RG.EUROPE_PMC))
    pm = RG.Answer(RG.PUBMED, True, {"title": "Erratum", "abstract": "The second table's totals are corrected; "
                                                                    "the conclusions are unchanged.", "pmcid": None})
    text, how = CR.notice_text({"id": "999", "registry": "MED"}, pubmed=lambda k, v: pm)
    assert "corrected" in text and how.startswith("PubMed abstract") and calls == [["PubMed"]]
    with pytest.raises(CR.RegistryUnavailable, match="Europe PMC and PubMed"):
        CR.notice_text({"id": "999", "registry": "MED"}, pubmed=lambda k, v: down(RG.PUBMED))



# ---------------------------------------------------------------- ruling 3 after P091: PMC when Europe PMC lacks the copy

def _acquire_case(tmp_path, monkeypatch, epmc_fulltext_error, epmc_meta, pmc):
    """acquire_sources.main on one PMC-hosted source, with Europe PMC's metadata and full text and NCBI PMC faked."""
    import acquire_sources as AQ
    import source_store as store
    case = tmp_path / "issues" / "WHU-T-x"
    case.mkdir(parents=True)
    (case / "sources.json").write_text(json.dumps({"sources": [{
        "id": "S001", "type": "review", "title": "T", "url": "https://europepmc.org/article/PMC/PMC1234567"}]}))   # 6-9 digits (acquisition_url)
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(store, "library_held", lambda slug: {})
    monkeypatch.setattr(store, "held_check", lambda slug, sid, s, data, ct: (True, {"state": "full_text_held",
                                                                                     "why": "ok"}))
    monkeypatch.setattr(store, "put", lambda slug, sid, data, **kw: {"file": "f", "sha256": "s", "bytes": len(data),
                                                                     "kind": "xml", "kind_why": "x",
                                                                     "retrieved": "2026-11-24"})
    monkeypatch.setattr(RG, "epmc_id", lambda k, v: epmc_meta)
    monkeypatch.setattr(RG, "pmc_fulltext", pmc)
    monkeypatch.setattr(RG, "covered", lambda a, by: None)

    def fetch(url):
        raise epmc_fulltext_error
    monkeypatch.setattr(AQ, "fetch_retrying", fetch)
    monkeypatch.setenv("WHU_ORCH_STEP", "acquire")
    AQ.main(["x", "--no-summaries"])
    return json.loads((case / "sources.json").read_text())["sources"][0]["access"]


SERVED = RG.Answer("PMC", True, {"xml": JATS.decode() if "JATS" in globals() else "<body/>",
                                 "licence": {"url": "https://creativecommons.org/licenses/by/4.0/",
                                             "statement": "open access"}}, url="u")


def test_a_europe_pmc_404_falls_back_to_pmc(tmp_path, monkeypatch):
    e404 = urllib.error.HTTPError("https://www.ebi.ac.uk/x", 404, "x", None, io.BytesIO(b""))
    acc = _acquire_case(tmp_path, monkeypatch, e404, RG.Answer(RG.EUROPE_PMC, True, {"isOpenAccess": "Y"}),
                        lambda p: SERVED)
    assert acc["state"] == "full_text_held" and acc["held"]["route"].startswith("NCBI PMC")
    assert acc["held"]["licence"]["url"].endswith("by/4.0/")


def test_europe_pmc_metadata_not_served_falls_back_to_pmc(tmp_path, monkeypatch):
    acc = _acquire_case(tmp_path, monkeypatch, AssertionError("Europe PMC's full text is never requested"),
                        RG.Answer(RG.EUROPE_PMC, True, {"isOpenAccess": "N"}), lambda p: SERVED)
    assert acc["state"] == "full_text_held" and acc["held"]["route"].startswith("NCBI PMC")


def test_neither_serving_the_copy_is_not_held_and_not_an_outage(tmp_path, monkeypatch):
    acc = _acquire_case(tmp_path, monkeypatch, AssertionError("not requested"),
                        RG.Answer(RG.EUROPE_PMC, True, {"isOpenAccess": "N"}),
                        lambda p: RG.Answer("PMC", True, why="not served: NCBI PMC The publisher of this article "
                                                              "does not allow downloading", url="u"))
    lf = acc["last_fetch"]
    assert lf["result"] == "not fetched" and "Europe PMC: not served" in lf["why"] and "NCBI PMC: not served" in lf["why"]
    assert not lf.get("registry_unavailable")


def test_pmc_down_after_a_europe_pmc_404_is_an_outage_not_an_absence(tmp_path, monkeypatch):
    e404 = urllib.error.HTTPError("https://www.ebi.ac.uk/x", 404, "x", None, io.BytesIO(b""))
    acc = _acquire_case(tmp_path, monkeypatch, e404, RG.Answer(RG.EUROPE_PMC, True, {"isOpenAccess": "Y"}),
                        lambda p: RG.Answer("PMC", False, why="HTTP 503", url="u"))
    assert acc["last_fetch"]["registry_unavailable"] is True


def test_a_notice_europe_pmc_does_not_serve_is_read_from_pmc(monkeypatch):
    monkeypatch.setattr(RG, "epmc_id", lambda k, v: RG.Answer(RG.EUROPE_PMC, True, {
        "abstractText": "short", "pmcid": "PMC5", "isOpenAccess": "N"}))
    xml = "<article><body><p>" + "The second table is corrected in full; the conclusions stand. " * 3 + \
          "</p></body></article>"
    text, how = CR.notice_text({"id": "999", "registry": "MED"},
                               pmc=lambda p: RG.Answer("PMC", True, {"xml": xml, "licence": {}}))
    assert "corrected" in text and how.startswith("NCBI PMC full text PMC5")


# ---------------------------------------------------------------- the discovery checkpoint

def _ctx(tmp_path, reply):
    c = tmp_path / "issues" / "WHU-T-orch-x"
    (c / "orchestrator").mkdir(parents=True)
    (c / "issue.json").write_text(json.dumps({"question": "Does X help?"}))
    found = SimpleNamespace(identifier=SimpleNamespace(kind="doi", value="10.1/x"), heading="Found title",
                            registry="europepmc", extra={})
    return SimpleNamespace(case=c, slug="orch-x", ask=lambda p, n, r: reply, search=lambda t, a, y, k: found,
                           replies=[], log=[])


REPLY = json.dumps({"sources": [{"title": "A review", "first_author": "S", "year": 2024, "type": "review",
                                 "url": "https://x.org/r"}]})


def test_discover_saves_the_proposals_with_their_hash_and_confirm_reuses_them(tmp_path):
    ctx = _ctx(tmp_path, REPLY)
    out = O.code_discover(ctx, ST.BY_NAME["discover"])
    doc = json.loads((ctx.case / "proposals.json").read_text())
    assert out["proposals_sha256"] == doc["sha256"] == O.proposals_sha(doc)
    ctx.log = [{"step": "discover", "code": out}]
    ctx.ask = lambda *a: pytest.fail("confirm makes no model call")
    O.code_confirm(ctx, ST.BY_NAME["confirm"])
    assert json.loads((ctx.case / "sources.json").read_text())["sources"][0]["title"] == "Found title"


def test_confirm_refuses_proposals_that_changed(tmp_path):
    ctx = _ctx(tmp_path, REPLY)
    out = O.code_discover(ctx, ST.BY_NAME["discover"])
    ctx.log = [{"step": "discover", "code": out}]
    p = ctx.case / "proposals.json"
    doc = json.loads(p.read_text())
    doc["proposals"][0]["title"] = "Another review"
    p.write_text(json.dumps(doc))
    with pytest.raises(O.RunStop, match="do not match their recorded sha256"):
        O.code_confirm(ctx, ST.BY_NAME["confirm"])
    doc["sha256"] = O.proposals_sha(doc)                              # rehashed: still not the discover step's
    p.write_text(json.dumps(doc))
    with pytest.raises(O.RunStop, match="not the ones the discover step recorded"):
        O.code_confirm(ctx, ST.BY_NAME["confirm"])
    p.unlink()
    with pytest.raises(O.RunStop, match="no saved proposals"):
        O.code_confirm(ctx, ST.BY_NAME["confirm"])


def test_confirm_follows_discover_and_owns_the_source_list():
    assert ST.NAMES.index("discover") + 1 == ST.NAMES.index("confirm") < ST.NAMES.index("acquire")
    c = ST.BY_NAME["confirm"]
    assert c.kind == "code" and not c.models                          # no model call
    from orch import chain as CH
    assert CH.owned("sources.json", ST.owns_for(c, "x")) and not CH.owned("sources.json",
                                                                          ST.owns_for(ST.BY_NAME["discover"], "x"))
    assert CH.owned("proposals.json", ST.owns_for(ST.BY_NAME["discover"], "x"))
    assert CH.FROZEN["source_list"][1] == "confirm" and CH.FROZEN["identifiers"][1] == "confirm"


@pytest.fixture
def private(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_PRIVATE_ROOT", str(tmp_path / "private"))
    monkeypatch.setenv("WHU_LIBRARY_ROOT", str(tmp_path / "library"))


def test_a_resume_after_a_confirm_outage_restarts_at_confirm_with_the_saved_proposals(tmp_path, private):
    from orch import chain as CH
    case = tmp_path / "issues" / "WHU-OT1-99-whu-x"
    (case / "orchestrator").mkdir(parents=True)
    names = ["provenance", "premise", "discover", "confirm", "acquire"]
    for k, s in enumerate(names[:3]):
        if s == "discover":
            (case / "proposals.json").write_text('{"proposals": [], "sha256": "abc"}')
        CH.append(case, s, CH.snapshot(case, "whu-x"), {})
        CP.save(case, "whu-x", k, s, CH.rows(case)[-1]["hashes"], ROOT)
    (case / "sources.json").write_text("half-written by the failed confirm")
    rec_ = {"result": "Not Ready: confirm: registry unavailable; run again later",
            "steps": [{"step": s, "code": {"changed": False}} for s in names[:3]] +
                     [{"step": "confirm", "failed": "RunStop: confirm: registry unavailable"}]}
    pl = CP.plan(case, "whu-x", rec_, names, set(), 2)
    assert pl["resume_at"] == "confirm"
    CP.restore(case, "whu-x", pl["checkpoint"], chain=pl["chain"])
    assert not (case / "sources.json").exists()                       # what the failed step wrote is gone
    assert json.loads((case / "proposals.json").read_text())["sha256"] == "abc"   # the proposals are kept


# ---------------------------------------------------------------- the rehearsal plans

def test_a_rehearsal_plan_can_make_a_registry_answer_503(tmp_path, monkeypatch):
    from orch import rehearsal as R
    plan = tmp_path / "p.json"
    plan.write_text(json.dumps({"registry": [{"step": "*", "what": "https://www.ebi.ac.uk/*", "error": "503",
                                              "times": 5}]}))
    monkeypatch.setenv("WHU_REHEARSE_PLAN", str(plan))
    monkeypatch.setenv("WHU_REHEARSE_STATE", str(tmp_path / "state"))
    with pytest.raises(urllib.error.HTTPError) as e:
        R.cached_urlopen(lambda *a, **k: pytest.fail("never reached"), "https://www.ebi.ac.uk/europepmc/x")
    assert e.value.code == 503
    for name in ("europepmc_down", "europepmc_search_down", "only_crossref_answers"):
        d = json.loads((W / "orch" / "rehearsal_plans" / ("%s.json" % name)).read_text())
        assert d["registry"] and all(r["error"] == "503" for r in d["registry"])


# ---------------------------------------------------------------- the full rehearsals (offline; minutes each; -m rehearsal)

PLANS = W / "orch" / "rehearsal_plans"


def _rehearse(tmp_path, plan, resume_plan=None):
    import os
    import subprocess
    state = tmp_path / "state"
    argv = [str(ROOT / "backend/venv/bin/python3"), str(W / "orchestrator.py"), "rehearse", "whu-lean-orch-t1-q1-02w",
            "--state", str(state), "--offline", "--plan", str(PLANS / plan)]
    if resume_plan:
        argv += ["--then-resume-plan", str(PLANS / resume_plan)]
    subprocess.run(argv, cwd=str(ROOT), env=dict(os.environ, WHU_LEAN="1"), capture_output=True, timeout=2400)
    return json.loads((state / "case" / "orchestrator" / "run_rehearse.json").read_text()), state


def _outcome(r, step):
    return next(((s.get("code") or {}).get("outcome") for s in r["steps"] if s["step"] == step), None)


def _sources(state):
    d = json.loads((state / "case" / "sources.json").read_text())["sources"]
    confirmed = sorted((s.get("doi") or s["title"]).lower() for s in d if not s.get("added_by"))
    held = sorted(s["id"] for s in d if (s.get("access") or {}).get("state") == "full_text_held")
    return confirmed, held, d


@pytest.mark.rehearsal
def test_rehearsal_the_confirmed_and_held_sources_are_the_same_whether_or_not_europe_pmc_is_down(tmp_path):
    """Rulings 2 and 3 after the fallback build: identity asks all three registries every time, and Europe PMC's
    full texts fall back to NCBI PMC."""
    up, s_up = _rehearse(tmp_path / "up", "none.json")
    down_, s_down = _rehearse(tmp_path / "down", "europepmc_down.json")
    assert up["result"] == down_["result"] == "Ready."
    c_up, h_up, _ = _sources(s_up)
    c_down, h_down, d = _sources(s_down)
    assert c_up == c_down and h_up == h_down and h_up
    assert down_["registry_outages"] == [] and down_["registry_outages_covered"]
    for s in d:
        if s["id"] in h_down and (s["access"]["held"].get("route") or "").startswith("NCBI PMC"):
            assert s["access"]["held"]["licence"]["statement"]               # the licence is recorded
        assert s["retraction_check"]["state"] == "checked"
        assert "Europe PMC" not in s["retraction_check"]["status_from"]       # it never answered


@pytest.mark.rehearsal
def test_rehearsal_with_only_crossref_answering_no_status_and_no_pmcid_lookup_can_be_made(tmp_path):
    r, state = _rehearse(tmp_path, "only_crossref_answers.json")
    assert "registry unavailable; run again later" in r["result"]
    assert r["steps"][-1]["step"] in ("confirm", "acquire") and r["steps"][-1].get("failed")
    assert r["registry_outages"]                                      # what no registry could answer stopped it
    p = state / "case" / "sources.json"
    if p.exists():
        assert not any(s.get("retraction_check") for s in json.loads(p.read_text()).get("sources") or [])


@pytest.mark.rehearsal
def test_rehearsal_a_confirm_outage_resumes_at_confirm_with_no_new_proposals(tmp_path):
    r, state = _rehearse(tmp_path, "registries_down_at_confirm.json", "none.json")
    assert "confirm: registry unavailable" in r["resumed"]["prior_result"]
    assert r["resumed"]["at"] == "confirm" and r["steps"][-1]["step"] == "archive"
    ev = [json.loads(l) for l in (state / "events.jsonl").read_text().splitlines() if l.strip()]
    assert len([e for e in ev if e.get("step") == "discover" and e.get("event") == "anthropic"]) == 1
    d = next(s for s in r["steps"] if s["step"] == "discover")
    assert d["code"]["proposals_sha256"] == json.loads((state / "case" / "proposals.json").read_text())["sha256"]
