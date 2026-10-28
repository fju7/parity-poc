"""acquire_sources.robots_allow: robots.txt read with the fetcher's own client
and headers; a robots.txt that does not come back is UNKNOWN, not "disallow all".

Post-study, mid-rerun tool fix (2026-10-28). RobotFileParser.read() fetched
robots.txt with Python's default client and read a 401/403 as "disallow all",
so a bot wall in front of ipcc.ch's robots.txt (WHU-S01r/S07r) stopped every
added summary as though the site forbade it.

Only the network is faked (fetch, or tls.urlopen beneath it); robots_allow and
main() run whole, so the real robots parsing and the real decision apply. No
real Disallow is bypassed: t_a_real_disallow_is_obeyed.

COUNTERFACTUAL. Put RobotFileParser.read() back and t_same_client goes red; map
an HTTPError to (False, ...) and t_a_403_is_unknown goes red; make the parse
ignore the body (parse([])) and t_a_real_disallow_is_obeyed goes red.
"""
import json
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import acquire_sources as AQ                    # noqa: E402
import tls                                      # noqa: E402
from test_whatholdsup_fix3_sourcing import WG2, case   # noqa: E402,F401

ROBOTS = "https://www.ipcc.ch/robots.txt"


def _net(robots, tried):
    """robots: bytes to serve, or an int HTTP status to raise. The document
    itself answers 503 so main() stops right after deciding to fetch it."""
    def fetch(url, timeout=45):
        tried.append(url)
        if url == ROBOTS:
            if isinstance(robots, int):
                raise urllib.error.HTTPError(url, robots, "x", {}, None)
            return robots, "text/plain", url
        raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)
    return fetch


def _spm(case):
    return [s for s in json.loads((case / "sources.json").read_text())["sources"] if s["id"] == "S002"][0]


def test_a_403_is_unknown_and_recorded_and_the_document_is_tried(case, monkeypatch):
    tried = []
    monkeypatch.setattr(AQ, "fetch", _net(403, tried))
    AQ.main(["x", "--only", "S002"])
    assert tried == [ROBOTS, WG2]
    rob = _spm(case)["access"]["robots"]
    assert rob["result"] == "unknown" and "HTTP 403" in rob["why"]


def test_a_real_disallow_is_obeyed(case, monkeypatch):
    tried = []
    monkeypatch.setattr(AQ, "fetch", _net(b"User-agent: *\nDisallow: /report/\n", tried))
    AQ.main(["x", "--only", "S002"])
    assert tried == [ROBOTS]
    spm = _spm(case)
    assert spm["access"]["robots"]["result"] == "not fetched"
    assert spm["access"]["last_fetch"]["why"] == "robots.txt disallows it"


def test_an_allowing_robots_txt_goes_on_to_the_document(case, monkeypatch):
    tried = []
    monkeypatch.setattr(AQ, "fetch", _net(b"User-agent: *\nDisallow: /private/\n", tried))
    AQ.main(["x", "--only", "S002"])
    assert tried == [ROBOTS, WG2] and _spm(case)["access"]["robots"]["result"] == "allows"


def test_a_network_failure_still_means_not_fetched(monkeypatch):
    def fetch(url, timeout=45):
        raise TimeoutError()
    monkeypatch.setattr(AQ, "fetch", fetch)
    ok, why = AQ.robots_allow(WG2)
    assert not ok and "could not be read" in why


def test_robots_txt_is_fetched_with_the_same_client_and_headers(monkeypatch):
    seen = []

    class Resp:
        headers = {"Content-Type": "text/plain"}
        def read(self): return b"User-agent: *\nAllow: /\n"
        def geturl(self): return ROBOTS
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def urlopen(req, timeout=None):
        seen.append((req.full_url, dict(req.header_items())))
        return Resp()
    monkeypatch.setattr(tls, "urlopen", urlopen)
    assert AQ.robots_allow(WG2)[0]
    [(url, headers)] = seen
    assert url == ROBOTS
    assert headers.get("User-agent") == AQ.UA["User-Agent"]
