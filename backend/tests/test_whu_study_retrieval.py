"""Scoring prep round 2 (2026-10-23): snapshot.py's certificate-chain fallback
and the marks on sources still unreachable. Offline, synthetic."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SC = ROOT / "study" / "whu-reliability" / "scripts"
sys.path.insert(0, str(SC))
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
requests = pytest.importorskip("requests")
import snapshot as SN  # noqa: E402


class _Resp:
    status, headers = 200, {"Content-Type": "text/html"}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return b"<html>the document</html>"

    def geturl(self):
        return "https://example.org/final"


def test_a_certificate_failure_is_retried_through_tls(monkeypatch):
    def bad(*a, **k):
        raise requests.exceptions.SSLError("unable to get local issuer certificate")
    seen = []
    monkeypatch.setattr(SN.requests, "get", bad)
    monkeypatch.setattr(SN.tls, "urlopen", lambda req, timeout=60: seen.append(req.full_url) or _Resp())
    data, row = SN.fetch("https://example.org/a")
    assert data == b"<html>the document</html>" and seen == ["https://example.org/a"]
    assert row["status"] == 200 and row["tls"] == "chain completed by tls.py"


def test_any_other_failure_is_not_retried(monkeypatch):
    def down(*a, **k):
        raise requests.exceptions.ConnectionError("refused")
    monkeypatch.setattr(SN.requests, "get", down)
    monkeypatch.setattr(SN.tls, "urlopen", lambda *a, **k: pytest.fail("tls.urlopen called"))
    with pytest.raises(requests.exceptions.ConnectionError):
        SN.fetch("https://example.org/a")


def _ps():
    spec = importlib.util.spec_from_file_location("prepare_scoring_rt", SC / "prepare_scoring.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_still_unreachable_marks():
    P = _ps()
    blocked_free = {"source_id": "S1", "url": "https://www.who.int/page", "extent_why": "HTTP 403",
                    "retrieval": {"tried": [{"route": "a", "url": "u", "result": "HTTP 403"},
                                            {"route": "b", "url": "u", "result": "HTTP 403"}], "oa_evidence": {"ids": {}}}}
    r = P.still_unreachable(blocked_free)
    assert r["blocks_automation"] and r["free_to_read"].startswith("likely") and r["free_to_read_but_blocks_automation"]
    paywalled = {"source_id": "S2", "url": "https://www.sciencedirect.com/science/article/pii/X", "extent_why": "HTTP 403",
                 "retrieval": {"tried": [{"route": "a", "result": "HTTP 403"}],
                               "oa_evidence": {"ids": {"pii": "X"}, "is_oa": False}}}
    r = P.still_unreachable(paywalled)
    assert r["blocks_automation"] and r["free_to_read"] == "unknown" and not r["free_to_read_but_blocks_automation"]
    oa = dict(paywalled, retrieval={"tried": [{"route": "b", "result": "HTTP 403"}],
                                    "oa_evidence": {"ids": {"doi": "10.1/x"}, "is_oa": True}})
    assert P.still_unreachable(oa)["free_to_read_but_blocks_automation"]
    gone = {"source_id": "S3", "url": "https://example.org/x", "extent_why": "HTTP 404",
            "retrieval": {"tried": [{"route": "a", "result": "HTTP 404"}, {"route": "b", "result": "HTTP 404"}]}}
    assert not P.still_unreachable(gone)["blocks_automation"]


def test_the_retrieval_never_reads_whus_store():
    src = (SC / "retrieve_sources.py").read_text()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    body = code.split('"""', 2)[2]                                  # past the docstring
    for name in ("source_store", "store.held", "load_issue_index", "data/whatholdsup/library"):
        assert name not in body, name


@pytest.mark.skipif(sys.platform != "darwin", reason="the macOS proxy lookup")
def test_on_macos_proxy_settings_come_from_the_environment():
    # A system proxy lookup (urllib, on a plain-http address) leaves every child
    # the process forks afterwards dying on signal 11: curl, and pdftotext.
    import os
    assert os.environ.get("no_proxy")
    src = (SC / "retrieve_sources.py").read_text()
    assert "close_fds=False" in src and '"/usr/bin/curl"' in src


# --- Round 3 (2026-10-23): the advisor's fetches (route d) and reachability ---

def _io():
    spec = importlib.util.spec_from_file_location("ingest_operator_t", SC / "ingest_operator.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _incoming(tmp_path, data=b"<html><body>" + b"An ordinary agency page about the topic. " * 80 + b"</body></html>"):
    import hashlib
    d = tmp_path / "incoming"
    d.mkdir()
    (d / "S1.html").write_bytes(data)
    return d, {"id": "S1", "outcome": "held", "version_held": "web page as rendered (agency page)",
               "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "method": "browser"}


def test_an_advisor_file_that_differs_from_its_log_stops(tmp_path):
    IO = _io()
    d, e = _incoming(tmp_path)
    assert IO.check([e], d) == []
    assert IO.check([dict(e, sha256="0" * 64)], d)                    # hash
    assert IO.check([dict(e, bytes=e["bytes"] + 1)], d)               # size
    assert IO.check([dict(e, id="S2")], d)                            # no file
    assert IO.check([{"id": "S9", "outcome": "challenge"}], d) == []  # nothing held, nothing to check


def test_an_advisor_file_is_held_by_the_same_extent_rule_with_route_d(tmp_path, monkeypatch):
    IO = _io()
    d, e = _incoming(tmp_path)
    monkeypatch.setattr(IO, "RUN", tmp_path)
    (tmp_path / "sources").mkdir()
    row = {"source_id": "S1", "url": "https://www.agency.gov/page", "extent": "unreachable", "extent_why": "HTTP 403",
           "retrieval": {"tried": [{"route": "a", "result": "HTTP 403"}], "route": None}}
    r = IO.ingest(row, e, d)
    assert r["extent"] == "full text" and r["retrieval"]["route"] == "d"
    assert r["retrieval"]["version"] == "web page as rendered" and r["raw_sha256"] == e["sha256"]
    assert r["retrieval"]["earlier_passes"][0]["tried"][0]["route"] == "a"   # the earlier pass is kept
    assert (tmp_path / "sources" / "S1.txt").read_text().startswith("An ordinary")
    # A challenge stays unreachable, with the advisor's outcome recorded.
    row2 = {"source_id": "S2", "url": "https://x.org/a", "extent": "unreachable", "extent_why": "HTTP 403"}
    r2 = IO.ingest(row2, {"id": "S2", "outcome": "challenge", "method": "browser"}, d)
    assert r2["extent"] == "unreachable" and r2["retrieval"]["route"] is None
    assert _ps().still_unreachable(r2)["advisor_tried"] == "challenge"


def test_reachability_counts_script_operator_and_unreachable_items():
    P = _ps()
    man = {"u1": {"extent": "full text", "retrieval": None}, "u2": {"extent": "full text", "retrieval": {"route": "d"}},
           "u3": {"extent": "unreachable"}}
    items = [{"item": "i1", "citations": [{"url": "u1"}]}, {"item": "i2", "citations": [{"url": "u1"}, {"url": "u2"}]},
             {"item": "i3", "citations": [{"url": "u2"}, {"url": "u3"}]}, {"item": "i4", "citations": [{"url": None}]}]
    km = {i: {"system": "Claude"} for i in ("i1", "i2", "i3", "i4")}
    r = P.reachability(items, km, man)["Claude"]
    assert (r["items_all_sources_by_script"], r["items_needing_operator_fetch"], r["items_unreachable"]) == (1, 1, 2)
    assert r["share_unreachable"] == 0.5 and r["flag_unreachable_over_20pct"]
    assert r["sources"] == {"distinct": 3, "by_script": 1, "by_operator_fetch": 1, "unreachable": 1}


def test_a_rendered_page_is_recorded_as_such_and_a_failure_keeps_its_reason(tmp_path, monkeypatch):
    IO = _io()
    d, e = _incoming(tmp_path)
    monkeypatch.setattr(IO, "RUN", tmp_path)
    (tmp_path / "sources").mkdir()
    row = {"source_id": "S1", "url": "https://www.agency.gov/page", "extent": "unreachable", "extent_why": "HTTP 403"}
    r = IO.ingest(row, dict(e, method="built-in browser; document.documentElement.outerHTML"), d)
    assert r["retrieval"]["tried"][0]["form"].startswith("browser-rendered HTML")
    row2 = {"source_id": "S2", "url": "https://x.org/a", "extent": "unreachable", "extent_why": "HTTP 403"}
    r2 = IO.ingest(row2, {"id": "S2", "outcome": "failed", "reason": "repository server error (HTTP 502)"}, d)
    assert r2["extent"] == "unreachable" and "repository server error" in r2["extent_why"]
