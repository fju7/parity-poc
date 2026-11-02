"""NCCI Policy Manual: which year's chapter, and what "not found" means.

Before 2026-11-02 the chapter PDF's URL was built from today's year and the
chapter number. Chapter 11's file is "11-chapter11a-...", so a real chapter read
NONEXISTENT; a year CMS had not published (with last year's moved) read
NONEXISTENT; and in January the golden replay would ask for next year's URL.
The chapter now comes from CMS's own index page, capped at the current year.

Run: python3 -m pytest backend/tests/verify/test_ncci_currency.py -q
"""
import datetime as dt
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
from verify import http, law  # noqa: E402
from verify.types import Exists  # noqa: E402

INDEX = ("https://www.cms.gov/medicare/coding-billing/"
         "national-correct-coding-initiative-ncci-edits/medicare-ncci-policy-manual")
FIXTURES = Path(__file__).parent / "fixtures" / "http"


def _today(y, m, d):
    class _D(dt.date):
        @classmethod
        def today(cls):
            return cls(y, m, d)
    return types.SimpleNamespace(date=_D, datetime=dt.datetime, timezone=dt.timezone)


def _index(*files):
    return "".join(f'<a href="/files/document/{f}">x</a>' for f in files).encode()


@pytest.fixture
def cms(monkeypatch):
    """A fake cms.gov: `pages` maps URL -> (status, body); anything else 404s."""
    pages = {}
    monkeypatch.setattr(law.http, "get", lambda url, timeout=45: (*pages.get(url, (404, b"")), {}))
    monkeypatch.setattr(law, "_ncci_cache", None, raising=False)
    monkeypatch.setattr(law, "dt", _today(2026, 11, 2))
    return pages


def test_a_chapter_whose_file_name_breaks_the_pattern_is_found_from_the_index(cms):
    cms[INDEX] = (200, _index("01-chapter1-ncci-medicare-policy-manual-2026-final.pdf",
                              "11-chapter11a-ncci-medicare-policy-manual-2026-final.pdf"))
    cms["https://www.cms.gov/files/document/11-chapter11a-ncci-medicare-policy-manual-2026-final.pdf"] = (200, b"%PDF-1.7 x")
    res = law.resolve(law.identify("NCCI Policy Manual, Chapter 11"))
    assert res.exists == Exists.EXISTS and res.extra.get("year") == 2026


def test_index_unavailable_and_no_pdf_at_the_usual_url_is_unchecked_not_nonexistent(cms):
    cms[INDEX] = (503, b"<html>upstream</html>")
    res = law.resolve(law.identify("NCCI Policy Manual, Chapter 1"))
    assert res.exists == Exists.UNCHECKED
    assert "not yet published, or renamed" in res.extra["registry_unavailable"]["cms.gov NCCI"]


def test_a_chapter_listed_only_for_a_future_year_is_unchecked(cms):
    cms[INDEX] = (200, _index("01-chapter1-ncci-medicare-policy-manual-2027-final.pdf"))
    cms["https://www.cms.gov/files/document/01-chapter1-ncci-medicare-policy-manual-2027-final.pdf"] = (200, b"%PDF-1.7 x")
    res = law.resolve(law.identify("NCCI Policy Manual, Chapter 1"))
    assert res.exists == Exists.UNCHECKED
    assert "not yet in effect in 2026" in res.extra["registry_unavailable"]["cms.gov NCCI"]


def test_a_chapter_the_index_does_not_list_is_still_nonexistent(cms):
    cms[INDEX] = (200, _index("01-chapter1-ncci-medicare-policy-manual-2026-final.pdf"))
    res = law.resolve(law.identify("NCCI Policy Manual, Chapter 14"))
    assert res.exists == Exists.NONEXISTENT


def test_in_january_the_recorded_replay_still_uses_the_published_2026_manual(monkeypatch):
    # The real recordings, offline, on 2027-01-05: the old code asked for the
    # 2027 URL (no recording -> RecordingMissing); the index says 2026.
    monkeypatch.setattr(http, "CACHE_DIR", FIXTURES)
    monkeypatch.setenv("VERIFY_OFFLINE", "1")
    monkeypatch.setattr(law, "_ncci_cache", None, raising=False)
    monkeypatch.setattr(law, "dt", _today(2027, 1, 5))
    res = law.resolve(law.identify("NCCI Policy Manual, Chapter I"))
    assert res.exists == Exists.EXISTS and res.extra.get("year") == 2026
