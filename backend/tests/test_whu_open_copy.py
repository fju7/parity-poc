"""Open copies for a walled source (advisor's ruling on P107, 2026-11-25; backend/scripts/whatholdsup/open_copy.py).

Found on orchestrator trial 1 attempt 24 (WHU-OT1-02za): S002 (Mendoza & Heymann 2022, doi 10.1080/1034912x.2022.2095359)
answered HTTP 403 at tandfonline and the orchestrated acquire tried nothing else; OpenAlex lists a repository copy at
eScholarship under CC BY-NC-ND. The OpenAlex records here are recorded metadata (fixtures/whu_open_copy/, fields only);
every other response is faked. On 2026-11-25 eScholarship answered WHU's honest user agent with HTTP 403 (CloudFront)
at robots.txt and at the item page: a wall, so the copy is found and recorded but never fetched.
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
FIX = Path(__file__).resolve().parent / "fixtures" / "whu_open_copy"

import open_copy as OC   # noqa: E402

S002 = {"id": "S002", "type": "review", "doi": "10.1080/1034912x.2022.2095359",
        "title": "Implementation of Inclusive Education: A Systematic Review of Studies of Inclusive Education "
                 "Interventions in Low- and Lower-Middle-Income Countries",
        "url": "https://www.tandfonline.com/doi/full/10.1080/1034912X.2022.2095359"}
S005 = {"id": "S005", "type": "assessment_summary", "doi": "10.54676/jjnk6989",
        "title": "Global Education Monitoring Report 2020: Inclusion and education: All means all. Paris",
        "url": "https://unesdoc.unesco.org/ark:/48223/pf0000373718"}
ITEM = "https://escholarship.org/uc/item/0bs2s446"


def _err(url, code):
    return urllib.error.HTTPError(url, code, "x", None, io.BytesIO(b""))


class Net:
    """A fake honest client: url -> bytes | (bytes, content type) | an HTTP status to raise. Logs every request."""
    def __init__(self, table):
        self.table, self.log = table, []

    def __call__(self, url):
        self.log.append(url)
        for prefix, got in self.table.items():
            if url.startswith(prefix):
                if isinstance(got, int):
                    raise _err(url, got)
                if isinstance(got, Exception):
                    raise got
                data, ct = got if isinstance(got, tuple) else (got, "application/octet-stream")
                return data, ct, url
        raise _err(url, 404)


def _openalex(name):
    return (FIX / ("openalex_%s.json" % name)).read_bytes(), "application/json"


def _held(ok=True):
    calls = []

    def check(data, ct):
        calls.append(data)
        return (ok, {"state": "full_text_held", "why": "identified (test)"} if ok else {"why": "not it"})
    return check, calls


AS_ON_2026_11_25 = {"https://api.openalex.org/": _openalex("s002"),
                    "https://escholarship.org/robots.txt": 403, "https://escholarship.org/": 403}


def test_s002_eScholarship_copy_is_found_with_its_licence_and_refused_at_the_wall():
    net, (check, calls) = Net(AS_ON_2026_11_25), _held()
    res = OC.find(S002, S002["url"], net, check)
    rec = res["record"]
    assert res.get("data") is None and not res.get("unavailable") and calls == []
    by = {c["where"]: c for c in rec["found"]}
    esc = by["eScholarship (California Digital Library)"]
    assert esc["permitted"] and esc["url"] == ITEM and esc["licence"] == "cc-by-nc-nd"
    assert esc["licence_from"] == "OpenAlex location record" and esc["version"] == "submittedVersion"
    pub = by["International Journal of Disability Development and Education"]
    assert not pub["permitted"] and "already refused" in pub["why"]          # doi.org leads back to tandfonline
    assert rec["tried"] == [{"url": ITEM, "where": esc["where"],
                             "robots": "robots.txt answered HTTP 403: a wall, not passed",
                             "result": "not fetched: robots.txt answered HTTP 403: a wall, not passed"}]
    assert ITEM not in net.log                                                 # never past the wall
    assert rec["outcome"] == "1 permitted open copy listed, none could be held"


def test_a_permitted_copy_is_held_only_after_robots_and_tdm_are_read():
    net = Net({"https://api.openalex.org/": _openalex("s002"),
               "https://escholarship.org/robots.txt": (b"User-agent: *\nAllow: /\n", "text/plain"),
               "https://escholarship.org/.well-known/tdmrep.json": 404,
               ITEM: (b"%PDF-1.7 the document", "application/pdf")})
    check, calls = _held()
    res = OC.find(S002, S002["url"], net, check)
    assert res["data"] == b"%PDF-1.7 the document" and calls == [b"%PDF-1.7 the document"]
    assert net.log == [OC.OPENALEX % S002["doi"], "https://escholarship.org/robots.txt",
                       "https://escholarship.org/.well-known/tdmrep.json", ITEM]
    assert res["copy"]["licence"] == "cc-by-nc-nd" and res["record"]["outcome"].startswith("held from eScholarship")


def test_a_tdm_reservation_refuses_the_copy_before_it_is_fetched():
    net = Net({"https://api.openalex.org/": _openalex("s002"),
               "https://escholarship.org/robots.txt": (b"User-agent: *\nAllow: /\n", "text/plain"),
               "https://escholarship.org/.well-known/tdmrep.json":
                   (json.dumps([{"location": "/uc/*", "tdm-reservation": 1}]).encode(), "application/json")})
    res = OC.find(S002, S002["url"], net, _held()[0])
    assert res.get("data") is None and ITEM not in net.log
    assert res["record"]["tried"][0]["result"] == "not fetched: tdmrep.json reserves /uc/*"


def test_a_page_that_reserves_tdm_is_not_used():
    net = Net({"https://api.openalex.org/": _openalex("s002"),
               "https://escholarship.org/robots.txt": (b"User-agent: *\nAllow: /\n", "text/plain"),
               "https://escholarship.org/.well-known/tdmrep.json": 404,
               ITEM: (b'<html><head><meta name="tdm-reservation" content="1"></head></html>', "text/html")})
    check, calls = _held()
    res = OC.find(S002, S002["url"], net, check)
    assert res.get("data") is None and calls == []


def test_robots_disallowing_the_path_refuses_the_copy():
    net = Net({"https://api.openalex.org/": _openalex("s002"),
               "https://escholarship.org/robots.txt": (b"User-agent: *\nDisallow: /uc/\n", "text/plain")})
    res = OC.find(S002, S002["url"], net, _held()[0])
    assert res.get("data") is None and ITEM not in net.log
    assert res["record"]["tried"][0]["robots"] == "robots.txt disallows it"


def test_a_challenge_page_in_place_of_robots_is_a_wall():
    net = Net({"https://api.openalex.org/": _openalex("s002"),
               "https://escholarship.org/robots.txt": (b"<!DOCTYPE html><html>Checking your browser</html>",
                                                       "text/html")})
    res = OC.find(S002, S002["url"], net, _held()[0])
    assert res.get("data") is None and ITEM not in net.log and "a wall" in res["record"]["tried"][0]["robots"]


def test_a_source_with_no_permitted_copy_is_still_refused():
    """S005: OpenAlex lists one location, closed, on the host already refused; nothing else is fetched."""
    net = Net({"https://api.openalex.org/": _openalex("s005")})
    res = OC.find(S005, S005["url"], net, _held()[0])
    assert res.get("data") is None and not res.get("unavailable")
    assert [c["permitted"] for c in res["record"]["found"]] == [False]
    assert res["record"]["tried"] == [] and net.log == [OC.OPENALEX % S005["doi"]]
    assert res["record"]["outcome"] == "no permitted open copy listed"


def test_a_publisher_copy_without_a_cc_licence_is_not_permitted():
    rec = {"locations": [{"is_oa": True, "landing_page_url": "https://pub.example/x", "license": "publisher-specific",
                          "source": {"type": "journal", "display_name": "J"}},
                         {"is_oa": True, "pdf_url": "https://pub2.example/x.pdf", "license": "cc-by",
                          "source": {"type": "journal", "display_name": "J2"}}]}
    got = OC.candidates(rec, set())
    assert [c["permitted"] for c in got] == [False, True] and "copy rule b" in got[1]["why"]


def test_an_openalex_outage_is_not_evidence_of_absence():
    net = Net({"https://api.openalex.org/": 503})
    res = OC.find(S002, S002["url"], net, _held()[0])
    assert res["unavailable"] and "not evidence of absence" in res["record"]["outcome"]


def test_no_doi_means_nothing_is_looked_up():
    net = Net({})
    res = OC.find(dict(S002, doi=None), S002["url"], net, _held()[0])
    assert net.log == [] and "nothing is ever guessed" in res["record"]["outcome"]


# ---- through acquire_sources.main, as the orchestrated acquire runs it -----------------------------------------

def _acquire(tmp_path, monkeypatch, table, open_copies=True):
    import acquire_sources as AQ
    import source_store as store
    case = tmp_path / "issues" / "WHU-T-x"
    case.mkdir(parents=True)
    (case / "sources.json").write_text(json.dumps({"sources": [dict(S002)]}))
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(store, "library_held", lambda slug: {})
    monkeypatch.setattr(store, "held_check", lambda slug, sid, s, data, ct: (True, {"state": "full_text_held",
                                                                                     "why": "identified (test)"}))
    monkeypatch.setattr(store, "put", lambda slug, sid, data, **kw: {"file": "f", "sha256": "s", "bytes": len(data),
                                                                     "kind": "pdf", "kind_why": "x",
                                                                     "retrieved": "2026-11-25"})
    net = Net(dict(table, **{"https://www.tandfonline.com/": 403}))
    monkeypatch.setattr(AQ, "fetch_retrying", net)
    monkeypatch.setenv("WHU_ORCH_STEP", "acquire")
    out = tmp_path / "acquire.json"
    rc = AQ.main(["x", "--no-summaries", "--out", str(out)] + (["--open-copies"] if open_copies else []))
    return rc, json.loads((case / "sources.json").read_text())["sources"][0]["access"], json.loads(out.read_text()), net


def test_through_acquire_s002_as_on_2026_11_25_is_not_held_and_says_why(tmp_path, monkeypatch):
    rc, acc, out, net = _acquire(tmp_path, monkeypatch, AS_ON_2026_11_25)
    assert rc == 1 and "held" not in acc and ITEM not in net.log
    why = acc["last_fetch"]["why"]
    assert why.startswith("HTTP 403 at https://www.tandfonline.com") and "none could be held" in why
    assert acc["open_copies"]["found"][1]["licence"] == "cc-by-nc-nd" and not acc["last_fetch"].get(
        "registry_unavailable")
    assert out["not_held"][0]["id"] == "S002" and "open copy via OpenAlex" in out["not_held"][0]["reason"]


def test_through_acquire_a_walled_publisher_copy_falls_back_to_a_permitted_open_copy(tmp_path, monkeypatch):
    rc, acc, out, net = _acquire(tmp_path, monkeypatch, {
        "https://api.openalex.org/": _openalex("s002"),
        "https://escholarship.org/robots.txt": (b"User-agent: *\nAllow: /\n", "text/plain"),
        "https://escholarship.org/.well-known/tdmrep.json": 404,
        ITEM: (b"%PDF-1.7 the document", "application/pdf")})
    assert rc == 0 and acc["state"] == "full_text_held"
    assert acc["held"]["route"].startswith("open copy via OpenAlex: eScholarship")
    assert acc["held"]["licence"] == {"name": "cc-by-nc-nd", "from": "OpenAlex location record", "url": ITEM}
    assert acc["held"]["version"] == "submittedVersion" and out["held"] == ["S002"]


def test_through_acquire_an_openalex_outage_stops_the_run_as_registry_unavailable(tmp_path, monkeypatch):
    rc, acc, out, net = _acquire(tmp_path, monkeypatch, {"https://api.openalex.org/": 503})
    assert rc == 1 and acc["last_fetch"]["registry_unavailable"] is True


def test_without_the_flag_nothing_else_is_tried(tmp_path, monkeypatch):
    rc, acc, out, net = _acquire(tmp_path, monkeypatch, AS_ON_2026_11_25, open_copies=False)
    assert rc == 1 and "open_copies" not in acc and net.log == [S002["url"]]


def test_the_orchestrated_acquire_step_runs_the_open_copy_routes():
    from orch import steps as ST
    from orch import code_hash as CHH
    import orchestrator as O
    cmd = ST.BY_NAME["acquire"].cmds[0]
    assert "--open-copies" in cmd
    files = CHH.step_files(ST.BY_NAME["acquire"], O.STEP_CODE) if hasattr(CHH, "step_files") else None
    if files is not None:
        assert any(str(f).endswith("open_copy.py") for f in files)
