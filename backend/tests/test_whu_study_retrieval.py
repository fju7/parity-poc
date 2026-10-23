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
