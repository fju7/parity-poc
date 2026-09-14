"""Reader state comes from the site, never from published.json.

Run:  cd backend && python3 -m pytest tests/whatholdsup/test_reader_state.py -q

WHY THIS EXISTS
On 2026-09-14 the board and `next` both said "readers are on <sha>" and took
the sha from the newest "publish" row of published.json. That row records what
somebody signed off from the working tree; it says nothing about the deploy,
and on that day it was wrong for every issue: melanoma 76703fe9 vs live
58c28929, deskilling 2e644545 (30 August) vs live d72bb438, cdk46 4e4bb50b vs
live fec7a9a2. The two paths now fetch the page and report what it serves, or
say "readers: not checked (fetch failed: ...)" -- and never fall back to the
record. Each case here stubs the fetch; nothing touches the network.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import publish as P            # noqa: E402

REAL = ROOT / "backend" / "data" / "whatholdsup" / "published.json"
LIVE = "feedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedfacefeedface"


def _rows():
    return json.loads(REAL.read_text(encoding="utf-8"))["published"]


def _newest_publish(slug):
    return [r for r in _rows() if r["issue"] == slug and r["action"] == "publish"][-1]


@pytest.fixture
def stale_record(tmp_path, monkeypatch):
    """The real record, whose newest publish row for every issue differs from
    the page on disk AND from whatever the stubbed site serves."""
    rec = tmp_path / "published.json"
    rec.write_text(json.dumps({"what_this_is": "test", "published": _rows()}))
    monkeypatch.setattr(P, "RECORD", rec)
    for slug in P.ISSUES:
        assert _newest_publish(slug)["sha"] != P.sha(ROOT / P.ISSUES[slug]["page"]), \
            "fixture premise: the newest publish row is stale against the repo"
    return rec


@pytest.fixture
def upstream_clear(monkeypatch):
    """Everything next_action() checks before the record passes, so the
    REPUBLISH branch is reached without a gate run or a preflight."""
    monkeypatch.setattr(P, "gate_state", lambda f, slug=None: {"state": P.OK, "outstanding": [], "detail": "", "exists": True})
    monkeypatch.setattr(P, "outside_review", lambda page, slug: (P.OK, ""))
    monkeypatch.setattr(P, "preflight", lambda slug, **kw: [])


def _publish_step(slug):
    steps = P._step_states(slug)
    step = [s for s in steps if s["name"] == P.STEPS[5][0]][0]
    return step["detail"]


# --- T3: the board must not claim readers are on the recorded sha ------------

@pytest.mark.parametrize("slug", sorted(P.ISSUES))
def test_board_reports_the_live_sha_not_the_recorded_one(stale_record, monkeypatch, slug):
    monkeypatch.setattr(P, "live_sha", lambda url, timeout=20: (LIVE, None))
    detail = _publish_step(slug)
    recorded = _newest_publish(slug)["sha"][:8]
    assert "readers are on %s" % LIVE[:8] in detail
    assert "readers are on %s" % recorded not in detail
    assert "recorded %s" % recorded in detail          # the row is still named, as a row


@pytest.mark.parametrize("slug", sorted(P.ISSUES))
def test_next_reports_the_live_sha_not_the_recorded_one(stale_record, upstream_clear, monkeypatch, slug):
    monkeypatch.setattr(P, "live_sha", lambda url, timeout=20: (LIVE, None))
    what, how = P.next_action(slug)
    recorded = _newest_publish(slug)["sha"][:8]
    assert what.startswith("REPUBLISH")
    assert "readers are on %s" % LIVE[:8] in what
    assert "Readers are on %s" % recorded not in what and "readers are on %s" % recorded not in what


def test_the_fetch_is_of_the_issue_url(stale_record, monkeypatch):
    seen = []
    monkeypatch.setattr(P, "live_sha", lambda url, timeout=20: seen.append(url) or (LIVE, None))
    _publish_step("melanoma")
    assert seen == [P.ISSUES["melanoma"]["url"]]


# --- T4: fetch failure -> "not checked", never a recorded sha ------------------

@pytest.mark.parametrize("slug", sorted(P.ISSUES))
def test_board_fetch_failure_says_not_checked(stale_record, monkeypatch, slug):
    monkeypatch.setattr(P, "live_sha", lambda url, timeout=20: (None, "HTTP 500"))
    detail = _publish_step(slug)
    recorded = _newest_publish(slug)["sha"][:8]
    assert "readers: not checked (fetch failed: HTTP 500)" in detail
    assert "readers are on" not in detail
    assert "readers are on %s" % recorded not in detail


def test_next_fetch_failure_says_not_checked(stale_record, upstream_clear, monkeypatch):
    monkeypatch.setattr(P, "live_sha", lambda url, timeout=20: (None, "URLError: timed out"))
    what, _ = P.next_action("deskilling")
    assert "readers: not checked (fetch failed: URLError: timed out)" in what
    assert "readers are on" not in what and "Readers are on" not in what


def test_live_sha_never_raises_and_never_reads_the_record(monkeypatch):
    import urllib.request

    def boom(*a, **k):
        raise TimeoutError("timed out")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    called = []
    monkeypatch.setattr(P, "load_record", lambda: called.append(1) or [])
    h, why = P.live_sha("https://whatholdsup.org/melanoma")
    assert h is None and why.startswith("TimeoutError")
    assert called == []


def test_readers_line_has_exactly_two_shapes(monkeypatch):
    monkeypatch.setattr(P, "live_sha", lambda url, timeout=20: (LIVE, None))
    assert P.readers_line("u") == (LIVE, "readers are on %s (fetched just now)" % LIVE[:8])
    monkeypatch.setattr(P, "live_sha", lambda url, timeout=20: (None, "HTTP 502"))
    assert P.readers_line("u") == (None, "readers: not checked (fetch failed: HTTP 502)")
