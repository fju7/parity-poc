"""watch.py -- the living-issue register and its preflight rows.

Written 12 September 2026 alongside the modest-promise ruling
(issues/WHU-003-deskilling/review/2026-09-12-modest-promise-ruling.md), which
withdrew the `page says when it was last reviewed` row. Until then nothing
tested this module. The tests below pin what the ruling left standing and
what it retired, on fixtures: issues/WHU-003-deskilling/watch.json is never
touched.
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"))
import watch as W  # noqa: E402


def _doc(**over):
    d = {"living": True, "review_interval_days": 30,
         "questions": [{"id": "W1", "question": "did a crossover trial appear", "status": "open"}],
         "checks": [{"on": (W._editorial_today() - timedelta(days=5)).isoformat(), "by": "x",
                     "questions_checked": ["W1"], "searched": ["Europe PMC"], "found": "nothing"}],
         "changelog": []}
    d.update(over)
    return d


@pytest.fixture
def case(tmp_path, monkeypatch):
    """A fake case directory; `write(doc)` puts a watch.json in it."""
    monkeypatch.setattr(W, "case_dir", lambda slug: tmp_path)

    def write(doc):
        (tmp_path / "watch.json").write_text(json.dumps(doc), encoding="utf-8")
        return tmp_path
    return write


def _row(rows, label):
    hits = [r for r in rows if r[0] == label]
    assert len(hits) == 1, "expected exactly one %r row, got %r" % (label, rows)
    return hits[0]


def test_a_non_living_slug_returns_no_rows(case):
    assert W.preflight_rows("nothing-here", "<p>Last reviewed 9 September 2026</p>") == []


def test_zero_open_questions_still_stops(case):
    case(_doc(questions=[{"id": "W1", "question": "q", "status": "closed"}]))
    assert _row(W.preflight_rows("x", ""), "living issue — open questions")[1] == W.BAD


def test_a_stale_watch_warns_and_does_not_stop(case):
    old = (W._editorial_today() - timedelta(days=75)).isoformat()   # > 2 x 30
    case(_doc(checks=[{"on": old, "by": "x"}]))
    row = _row(W.preflight_rows("x", ""), "watch has been run")
    assert row[1] == W.WARN
    assert "75 day(s) ago" in row[2] and "30-day interval" in row[2]


def test_a_never_checked_watch_warns_and_the_row_is_present(case):
    case(_doc(checks=[]))
    row = _row(W.preflight_rows("x", ""), "watch has been run")
    assert row[1] == W.WARN
    assert "no check recorded" in row[2]
    assert "promise" not in row[2], "the currency clause is retired"


def test_a_recent_check_is_ok(case):
    case(_doc())
    assert _row(W.preflight_rows("x", ""), "watch has been run")[1] == W.OK


def test_a_changelog_entry_without_a_sha_still_stops(case):
    case(_doc(changelog=[{"on": "2026-09-01", "what": "a new trial appeared"}]))
    assert _row(W.preflight_rows("x", ""), "changelog entries bound to a sha")[1] == W.BAD


def test_the_retired_rule_stays_retired(case):
    """A page saying 'Last reviewed <date>' produces NO row about a review
    date, whether or not the date matches the register."""
    case(_doc())
    for page in ("<p>Last reviewed 9 September 2026</p>", "<p>Last updated 1 May 2026</p>", ""):
        rows = W.preflight_rows("x", page)
        assert not any("review" in r[0].lower() for r in rows), rows
        assert not any("Last reviewed" in r[2] for r in rows), rows
    assert not hasattr(W, "reviewed_date_on_page") and not hasattr(W, "REVIEWED_RE")


def test_the_three_integrity_rows_are_all_present_for_a_living_issue(case):
    case(_doc(changelog=[{"on": "2026-09-01", "what": "x", "page_sha": "abc"}]))
    labels = [r[0] for r in W.preflight_rows("x", "")]
    assert labels == ["living issue — open questions", "watch has been run",
                      "changelog entries bound to a sha"]
