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


def test_a_europe_pmc_outage_falls_back_to_pubmed_then_crossref():
    ns, cov = _fake(down(RG.EUROPE_PMC), RG.Answer(RG.PUBMED, True, why="no record"),
                    RG.Answer(RG.CROSSREF_NAME, True, records=[dict(rec(), registry="crossref")]))
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert isinstance(got, RV.Found) and got.registry == "crossref" and got.identifier.value == "10.1002/cl2.70016"
    assert got.extra["record"]["registry"] == "crossref"
    assert [r["registry"] for r in got.extra["answered"]] == ["Europe PMC", "PubMed", "Crossref"]
    assert [r["answered"] for r in got.extra["answered"]] == [False, True, True]
    assert cov and cov[0][1] == ["PubMed", "Crossref"]                # the Europe PMC outage is covered


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


def test_a_later_fallback_is_asked_only_if_an_earlier_one_did_not_give_the_source():
    ns, cov = _fake(down(RG.EUROPE_PMC), RG.Answer(RG.PUBMED, True, records=[dict(rec(), registry="pubmed")]))
    ns.crossref_title = lambda t, a=None: pytest.fail("PubMed gave the source; Crossref is not asked")
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert got.registry == "pubmed" and [r["registry"] for r in got.extra["answered"]] == ["Europe PMC", "PubMed"]


def test_a_fallback_outage_is_covered_too_when_another_registry_answered():
    ns, cov = _fake(down(RG.EUROPE_PMC), down(RG.PUBMED, "https://eutils.ncbi.nlm.nih.gov/x"),
                    RG.Answer(RG.CROSSREF_NAME, True, records=[dict(rec(), registry="crossref")]))
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert got.registry == "crossref"
    assert sorted(u for u, _ in cov) == sorted(["https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x",
                                                 "https://eutils.ncbi.nlm.nih.gov/x"])


def test_a_steps_subprocess_can_mark_an_outage_covered(tmp_path):
    """Found in rehearsal: sitecustomize loaded the wrapper without registering it, so a subprocess's covers
    (errata.py at acquire) were lost and covered outages still stopped the run."""
    import os
    import subprocess
    log = tmp_path / "u.jsonl"
    code = ("import json, sys; sys.path.insert(0, %r); import registries as RG; "
            "m = sys.modules.get('whu_registry_http'); assert m is not None and m.installed(), 'not registered'; "
            "RG.covered(RG.Answer('Europe PMC', False, url='https://www.ebi.ac.uk/a'), ['PubMed', 'Crossref'])"
            % str(W))
    log.write_text(json.dumps({"url": "https://www.ebi.ac.uk/a", "error": "HTTPError: 503", "attempts": 4}) + "\n")
    env = dict(os.environ, WHU_ORCH_UNAVAILABLE_LOG=str(log), PYTHONPATH=str(W / "orch" / "site"))
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert RH.outages(log) == [] and RH.covered_outages(log)[0]["covered_by"] == ["PubMed", "Crossref"]


def test_europe_pmc_answering_uses_no_fallback():
    called = []
    ns, cov = _fake(RG.Answer(RG.EUROPE_PMC, True, rec(), [rec()]))
    ns.pubmed_title = lambda t: called.append(t)
    got = RV.search(TITLE, "Hunt", 2025, registries=ns)
    assert isinstance(got, RV.Found) and got.registry == "europepmc" and called == [] and cov == []


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
    st = CR.status(SRC, lambda k, v: down(RG.EUROPE_PMC), lambda d: RG.Answer(RG.CROSSREF_NAME, True, {"relation": {}}),
                   lambda k, v: RG.Answer(RG.PUBMED, True, pm))
    assert st["retracted"] is False and st["corrections"] == [{"id": "999", "registry": "MED", "type": "ErratumIn"}]
    assert [(r["registry"], r["answered"]) for r in st["registries"]] == [
        ("Europe PMC", False), ("PubMed", True), ("Crossref", True)]
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


@pytest.mark.rehearsal
def test_rehearsal_europe_pmc_down_confirms_through_the_fallbacks_and_stops_where_only_it_serves(tmp_path):
    r, _ = _rehearse(tmp_path, "europepmc_down.json")
    assert _outcome(r, "confirm") and r["steps"][-1]["step"] == "acquire" and r["steps"][-1].get("failed")
    assert "acquire: registry unavailable; run again later" in r["result"]
    assert r["registry_outages_covered"]                              # identity and status were answered for
    assert all("europepmc" in o["url"] for o in r["registry_outages"])   # only Europe PMC's own texts stopped it


@pytest.mark.rehearsal
def test_rehearsal_a_status_from_crossref_alone_stops_the_run(tmp_path):
    r, state = _rehearse(tmp_path, "only_crossref_answers.json")
    assert _outcome(r, "confirm")                                     # identity through Crossref
    assert "acquire: registry unavailable; run again later" in r["result"]
    assert "1 of 3 registries answered (Crossref)" in r["steps"][-1]["failed"]      # the status check stopped it
    # the status needed a second registry: PubMed's outage stays uncovered, and no status was recorded at all
    assert any("eutils.ncbi.nlm.nih.gov" in o["url"] for o in r["registry_outages"])
    srcs = json.loads((state / "case" / "sources.json").read_text())["sources"]
    assert srcs and not any(s.get("retraction_check") for s in srcs)


@pytest.mark.rehearsal
def test_rehearsal_a_confirm_outage_resumes_at_confirm_with_no_new_proposals(tmp_path):
    r, state = _rehearse(tmp_path, "registries_down_at_confirm.json", "none.json")
    assert "confirm: registry unavailable" in r["resumed"]["prior_result"]
    assert r["resumed"]["at"] == "confirm" and r["steps"][-1]["step"] == "archive"
    ev = [json.loads(l) for l in (state / "events.jsonl").read_text().splitlines() if l.strip()]
    assert len([e for e in ev if e.get("step") == "discover" and e.get("event") == "anthropic"]) == 1
    d = next(s for s in r["steps"] if s["step"] == "discover")
    assert d["code"]["proposals_sha256"] == json.loads((state / "case" / "proposals.json").read_text())["sha256"]
