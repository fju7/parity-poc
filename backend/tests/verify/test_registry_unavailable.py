"""Registry unavailability is a first-class failure mode.

The 49-of-59 template finding (docs/fabricated-doi-recombination-2026-09-15.md)
means shape cannot tell a fabricated DOI from a real one; the registry
round-trip is the only test in the literature path, so the registries'
failure behaviour is the system's. Required, per injected failure:

    REFUSE      never Found / never EXISTS
    BOUNDED     http.get's four attempts and no more
    DISTINCT    "the registry did not answer" (REGISTRY_UNAVAILABLE / UNCHECKED
                with a registry_unavailable note) is recorded apart from "the
                registry answered and found nothing" (NOT_FOUND / NONEXISTENT).
                Only the second is a fact about the source.

Measured before the fix on 2026-09-15: verify.search reported every one of
these as "no registry title matched"; literature.resolve reported a Handle
429, 503 or HTML 200 as EXISTS.
"""
from __future__ import annotations

import os
import sys
import urllib.error

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

import verify.search as vs  # noqa: E402
from verify import http, literature  # noqa: E402
from verify.literature import identify  # noqa: E402
from verify.types import Exists  # noqa: E402

TITLE = "Autism Occurrence by MMR Vaccine Status Among US Children With Older Siblings With and Without Autism"
EMPTY = (200, b'{"resultList":{"result":[]},"message":{"items":[]},"studies":[]}', {})


def _inject(monkeypatch, module, mapping):
    """http.get that answers by URL substring; anything unmapped answers 200 with no hits."""
    def fake(url, timeout=45):
        for k, v in mapping.items():
            if k in url:
                return v
        return EMPTY
    monkeypatch.setattr(module.http, "get", fake)


# --- verify.search --------------------------------------------------------

SEARCH_FAILURES = {
    "429 Europe PMC after retries":  ({"ebi.ac.uk": (429, b"Too Many Requests", {"retries": "3"})}, "europepmc", "HTTP 429 after 4 attempts"),
    "503 Crossref":                  ({"crossref": (503, b"<html>upstream</html>", {"retries": "3"})}, "crossref", "HTTP 503"),
    "connection timeout":            ({"ebi.ac.uk": (0, b"", {"error": "TimeoutError: timed out", "retries": "3"})}, "europepmc", "no response: TimeoutError"),
    "HTML body on a 200":            ({"ebi.ac.uk": (200, b"<html>maintenance</html>", {})}, "europepmc", "HTTP 200 with no parseable JSON"),
    "empty body on a 200":           ({"crossref": (200, b"", {})}, "crossref", "HTTP 200 with no parseable JSON"),
    "JSON but not an object":        ({"crossref": (200, b"[]", {})}, "crossref", "HTTP 200 with no parseable JSON"),
}


@pytest.mark.parametrize("case", list(SEARCH_FAILURES), ids=list(SEARCH_FAILURES))
def test_search_refuses_with_registry_unavailable_when_a_registry_does_not_answer(monkeypatch, case):
    mapping, registry, note = SEARCH_FAILURES[case]
    _inject(monkeypatch, vs, mapping)
    r = vs.search(TITLE, "Jain", 2015)
    assert isinstance(r, vs.Unresolved)                                   # refused
    assert r.status == vs.REGISTRY_UNAVAILABLE                            # distinct from NOT_FOUND
    assert r.registries[registry]["answered"] is False and note in r.registries[registry]["note"]
    assert r.reason.startswith("registry did not answer") and "not evidence about the source" in r.reason
    other = [n for n in r.registries if n != registry]
    assert other and all(r.registries[n]["answered"] for n in other)      # the registry that did answer is recorded as such


def test_search_records_not_found_only_when_every_registry_answered(monkeypatch):
    _inject(monkeypatch, vs, {})
    r = vs.search(TITLE, "Jain", 2015)
    assert isinstance(r, vs.Unresolved) and r.status == vs.NOT_FOUND
    assert r.registries == {"europepmc": {"answered": True, "http": 200}, "crossref": {"answered": True, "http": 200}}
    assert r.reason.startswith("no registry title matched")


def test_search_trial_path_reports_ctgov_unavailable(monkeypatch):
    _inject(monkeypatch, vs, {"clinicaltrials.gov": (502, b"", {"retries": "3"})})
    r = vs.search("Immunogenicity and Safety Study of PriorixTetra in Healthy Children", None, 2012, kind="trial")
    assert isinstance(r, vs.Unresolved) and r.status == vs.REGISTRY_UNAVAILABLE
    assert r.registries["clinicaltrials.gov"] == {"answered": False, "http": 502, "note": "HTTP 502 after 4 attempts"}


def test_search_an_exception_inside_a_registry_call_is_unavailable_not_not_found(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("socket closed")
    monkeypatch.setattr(vs, "_epmc", boom)
    _inject(monkeypatch, vs, {})
    r = vs.search(TITLE, "Jain", 2015)
    assert r.status == vs.REGISTRY_UNAVAILABLE and "RuntimeError" in r.registries["europepmc"]["note"]


def test_unresolved_record_carries_the_status():
    d = vs.Unresolved("t", "r", [], "now", vs.REGISTRY_UNAVAILABLE, {"crossref": {"answered": False, "http": 429, "note": "HTTP 429"}}).to_dict()
    assert d["status"] == "REGISTRY_UNAVAILABLE" and d["registries"]["crossref"]["http"] == 429


def test_discovery_writes_the_status_into_the_proposal(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("discover", os.path.join(BACKEND, "scripts", "signal", "00_discover_sources.py"))
    d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
    monkeypatch.setattr(vs, "search", lambda *a, **k: vs.Unresolved(TITLE, "registry did not answer: crossref (HTTP 429)", [], "t",
                                                                    vs.REGISTRY_UNAVAILABLE, {"crossref": {"answered": False, "http": 429, "note": "HTTP 429"}}))
    out = d._resolve_proposal({"slug": "x", "title": TITLE, "first_author": "Jain", "year": 2015, "source_type": "journal"})
    assert "identifier" not in out and out["url"] is None and out["fetch_strategy"] == "unresolved"
    assert out["unresolved"]["status"] == "REGISTRY_UNAVAILABLE" and out["unresolved"]["registries"]["crossref"]["http"] == 429


# --- literature.resolve (the publish path) --------------------------------

RESOLVE_FAILURES = {
    "handle 429":            ({"doi.org/api": (429, b"Too Many Requests", {"retries": "3"})}, "handle", "HTTP 429 after 4 attempts"),
    "handle 503 html":       ({"doi.org/api": (503, b"<html>", {"retries": "3"})}, "handle", "HTTP 503"),
    "handle timeout":        ({"doi.org/api": (0, b"", {"error": "TimeoutError", "retries": "3"})}, "handle", "no response: TimeoutError"),
    "handle html 200":       ({"doi.org/api": (200, b"<html>", {})}, "handle", "HTTP 200 with no parseable JSON"),
    "handle json 200 without responseCode": ({"doi.org/api": (200, b'{"unexpected": true}', {})}, "handle", "HTTP 200 with no parseable JSON"),
}


@pytest.mark.parametrize("case", list(RESOLVE_FAILURES), ids=list(RESOLVE_FAILURES))
def test_resolve_stays_unchecked_when_the_handle_registry_does_not_answer(monkeypatch, case):
    mapping, registry, note = RESOLVE_FAILURES[case]
    _inject(monkeypatch, literature, mapping)
    res = literature.resolve(identify("10.1001/jama.2015.1534"))
    assert res.exists == Exists.UNCHECKED                                  # never EXISTS
    assert note in res.extra["registry_unavailable"][registry]


def test_resolve_nonexistent_only_on_a_parsed_handle_answer(monkeypatch):
    _inject(monkeypatch, literature, {"doi.org/api": (404, b'{"responseCode":100,"handle":"10.1001/jama.2015.1534"}', {})})
    res = literature.resolve(identify("10.1001/jama.2015.1534"))
    assert res.exists == Exists.NONEXISTENT and res.registry == "handle" and "registry_unavailable" not in res.extra


def test_resolve_handle_exists_but_crossref_silent_is_recorded_and_has_no_heading(monkeypatch):
    _inject(monkeypatch, literature, {"doi.org/api": (200, b'{"responseCode":1}', {}), "crossref": (429, b"", {"retries": "3"})})
    res = literature.resolve(identify("10.1001/jama.2015.3077"))
    assert res.exists == Exists.EXISTS and res.heading is None
    assert res.extra["registry_unavailable"]["crossref"] == "HTTP 429 after 4 attempts"
    from verify.bind import bind_heading
    assert bind_heading("Autism occurrence by MMR vaccine status", res).ok is False   # no heading -> HEADING refuses


@pytest.mark.parametrize("system,mapping", [
    ("pmid", {"ebi.ac.uk": (503, b"", {"retries": "3"})}),
    ("pmid", {"ebi.ac.uk": (200, b"<html>", {})}),
    ("nct", {"clinicaltrials.gov": (429, b"", {"retries": "3"})}),
])
def test_resolve_pmid_and_nct_paths_stay_unchecked(monkeypatch, system, mapping):
    _inject(monkeypatch, literature, mapping)
    res = literature.resolve(identify("25898051" if system == "pmid" else "NCT01506193"))
    assert res.exists == Exists.UNCHECKED and res.extra.get("registry_unavailable")


def test_publish_record_names_registry_unavailable_apart_from_nonexistent(monkeypatch):
    from verify import publish
    publish._run_cache.clear()
    _inject(monkeypatch, literature, {"doi.org/api": (429, b"", {"retries": "3"})})
    row = publish.gate_source({"id": "s1", "title": "Jain 2015", "url": "https://doi.org/10.1001/jama.2015.3077", "source_type": "journal"})
    assert row["survives"] is False
    assert row["withheld_reason"] == "resolve: REGISTRY_UNAVAILABLE handle: HTTP 429 after 4 attempts"
    assert row["resolution"]["exists"] == "UNCHECKED" and row["resolution"]["registry_unavailable"] == {"handle": "HTTP 429 after 4 attempts"}
    publish._run_cache.clear()
    _inject(monkeypatch, literature, {"doi.org/api": (404, b'{"responseCode":100}', {})})
    row = publish.gate_source({"id": "s2", "title": "Jain 2015", "url": "https://doi.org/10.1001/jama.2015.1534", "source_type": "journal"})
    assert row["survives"] is False and row["withheld_reason"] == "resolve: NONEXISTENT" and "registry_unavailable" not in row["resolution"]
    publish._run_cache.clear()


# --- http.get is bounded ----------------------------------------------------

def test_http_get_retries_are_bounded_and_report_the_count(monkeypatch):
    calls = []
    def urlopen(req, timeout=45):
        calls.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
    monkeypatch.setattr(http.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    monkeypatch.setattr(http, "CACHE_DIR", None)
    st, body, headers = http.get("https://api.crossref.org/works?query.bibliographic=x")
    assert st == 429 and len(calls) == 4 and headers["retries"] == "3"


def test_http_get_never_raises_on_a_dead_connection(monkeypatch):
    def urlopen(req, timeout=45):
        raise TimeoutError("timed out")
    monkeypatch.setattr(http.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    monkeypatch.setattr(http, "CACHE_DIR", None)
    st, body, headers = http.get("https://www.ebi.ac.uk/europepmc/x")
    assert st == 0 and headers["error"].startswith("TimeoutError") and headers["retries"] == "3"


# --- law: the eCFR resolver ---------------------------------------------------

@pytest.mark.parametrize("case,mapping,note", [
    ("ecfr 429", {"ecfr.gov": (429, b"", {"retries": "3"})}, "HTTP 429 after 4 attempts"),
    ("ecfr timeout", {"ecfr.gov": (0, b"", {"error": "TimeoutError", "retries": "3"})}, "no response: TimeoutError"),
    ("ecfr html 200 (maintenance page)", {"ecfr.gov": (200, b"<html><body>Down for maintenance</body></html>", {})}, "HTTP 200 without the section"),
])
def test_law_ecfr_stays_unchecked_when_the_registry_does_not_answer(monkeypatch, case, mapping, note):
    from verify import law
    _inject(monkeypatch, law, mapping)
    res, _ = law._cfr(law.identify("42 CFR § 410.32"))
    assert res.exists == Exists.UNCHECKED and note in res.extra["registry_unavailable"]["ecfr"]


def test_law_ecfr_nonexistent_only_on_a_404(monkeypatch):
    from verify import law
    _inject(monkeypatch, law, {"ecfr.gov": (404, b"", {})})
    res, _ = law._cfr(law.identify("42 CFR § 410.32"))
    assert res.exists == Exists.NONEXISTENT


# --- UNCHECKED at the publish gate is a withholding, never a pass ---------------

def test_unchecked_at_gate_source_withholds_and_is_never_a_pass(monkeypatch):
    """Asserted, not implied: whatever produced UNCHECKED -- a registry that
    did not answer, or nothing at all -- the source does not survive and the
    record says resolve: UNCHECKED."""
    from verify import publish
    from verify.types import Resolution
    publish._run_cache.clear()
    monkeypatch.setattr(literature, "resolve", lambda ident: Resolution(ident, Exists.UNCHECKED, checked_at="t"))
    fetched = []
    monkeypatch.setattr(literature, "fetch", lambda res: fetched.append(res) or None)
    row = publish.gate_source({"id": "s3", "title": "Any paper", "url": "https://doi.org/10.1056/nejmoa021134", "source_type": "journal"})
    assert row["survives"] is False and row["withheld_reason"] == "resolve: UNCHECKED"
    assert row["resolution"]["exists"] == "UNCHECKED" and row["document"] is None and fetched == []   # nothing downstream ran
    publish._run_cache.clear()


# --- the fetch path: an abstract Europe PMC did not serve is unfetched, not absent --

def test_fetch_records_europepmc_unavailable_and_publish_says_so(monkeypatch):
    """2026-09-15 re-freeze b902246: Europe PMC stopped answering mid-run and
    three abstracts that had bound at 0b7359b were withheld as "nothing
    retrieved (publisher: a shell ...)". The record must say the registry did
    not answer."""
    from verify import publish
    from verify.types import Resolution
    publish._run_cache.clear()
    res = Resolution(identify("10.1056/nejmoa021134"), Exists.EXISTS, heading="A population-based study", canonical="https://doi.org/10.1056/nejmoa021134", registry="crossref", checked_at="t", extra={})
    monkeypatch.setattr(literature, "resolve", lambda ident: res)
    _inject(monkeypatch, literature, {"ebi.ac.uk": (429, b"", {"retries": "3"})})
    from verify import generic
    monkeypatch.setattr(generic, "fetch", lambda g: None)
    monkeypatch.setattr(generic, "resolve", lambda i: Resolution(i, Exists.UNCHECKED, extra={"http": 403}))
    row = publish.gate_source({"id": "s4", "title": "Madsen 2002", "url": "https://doi.org/10.1056/nejmoa021134", "source_type": "journal"})
    assert row["survives"] is False
    assert row["withheld_reason"].startswith("fetch: REGISTRY_UNAVAILABLE europepmc: HTTP 429 after 4 attempts")
    assert row["resolution"]["fetch_unavailable"] == {"europepmc": "HTTP 429 after 4 attempts"}
    publish._run_cache.clear()
