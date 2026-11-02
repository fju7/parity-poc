"""eCFR currency and offline replay (CI failure of 2026-11-01/02).

On 2026-11-01 the eCFR versioner was current for titles 42 and 45 only to
2026-10-29. The adapter asked for the first of the month, got 404s, and called
four real CFR sections NONEXISTENT -- in production as much as in CI. And the
"offline" golden tests never noticed they were live: a missing recording
fell through to the network.

These tests fake the registry; none of them may touch the network.

Run: python3 -m pytest backend/tests/verify/test_ecfr_currency.py -q
"""
import datetime as dt
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
from verify import http, law  # noqa: E402
from verify.types import Exists  # noqa: E402

TITLES = "https://www.ecfr.gov/api/versioner/v1/titles.json"
UPTO = "2026-10-29"
XML = (b"<DIV8 N=\"147.200\"><HEAD>\xc2\xa7 147.200 Summary of benefits and coverage and uniform "
       b"glossary.</HEAD><P>(a) A group health plan ... must provide a written summary.</P></DIV8>")


class _Nov1(dt.date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 1)


@pytest.fixture
def ecfr(monkeypatch):
    """A fake eCFR: titles.json says 45 is current to 10-29; the section exists
    at any date up to then and 404s after. Records every URL asked for."""
    asked = []

    def get(url, timeout=45):
        asked.append(url)
        if url == TITLES:
            return 200, json.dumps({"titles": [{"number": 45, "up_to_date_as_of": UPTO},
                                               {"number": 42, "up_to_date_as_of": UPTO}]}).encode(), {}
        date = url.split("/full/")[1].split("/")[0]
        return (200, XML, {}) if date <= UPTO else (404, b'{"error":"not found"}', {})

    monkeypatch.setattr(law.http, "get", get)
    monkeypatch.setattr(law, "dt", types.SimpleNamespace(date=_Nov1, datetime=dt.datetime, timezone=dt.timezone))
    monkeypatch.setattr(law, "_titles_cache", None, raising=False)
    monkeypatch.delenv("VERIFY_ECFR_DATE", raising=False)
    return asked


def test_first_of_month_past_currency_is_checked_at_the_currency_date(ecfr):
    res = law.resolve(law.identify("45 CFR § 147.200"))
    assert res.exists == Exists.EXISTS
    assert res.extra.get("as_of") == UPTO
    assert any(f"/full/{UPTO}/title-45.xml" in u for u in ecfr)
    assert not any("/full/2026-11-01/" in u for u in ecfr)


def test_a_404_past_the_titles_currency_is_unchecked_not_nonexistent(ecfr, monkeypatch):
    monkeypatch.setenv("VERIFY_ECFR_DATE", "2026-11-01")  # forced past the cutoff
    res = law.resolve(law.identify("45 CFR § 147.200"))
    assert res.exists == Exists.UNCHECKED
    assert "eCFR not yet current for 2026-11-01" in res.extra["registry_unavailable"]["ecfr"]


def test_a_404_within_the_titles_currency_is_still_nonexistent(ecfr, monkeypatch):
    monkeypatch.setenv("VERIFY_ECFR_DATE", "2026-10-01")
    monkeypatch.setattr(law.http, "get", lambda url, timeout=45: (
        (200, json.dumps({"titles": [{"number": 45, "up_to_date_as_of": UPTO}]}).encode(), {})
        if url == TITLES else (404, b"", {})))
    res = law.resolve(law.identify("45 CFR § 999.999"))
    assert res.exists == Exists.NONEXISTENT


def test_offline_missing_recording_raises_naming_url_and_hash(tmp_path, monkeypatch):
    def no_network(*a, **k):
        raise AssertionError("offline mode touched the network")
    monkeypatch.setattr(http.urllib.request, "urlopen", no_network)
    monkeypatch.setattr(http, "CACHE_DIR", tmp_path)
    monkeypatch.setenv("VERIFY_OFFLINE", "1")
    url = "https://www.ecfr.gov/api/versioner/v1/full/2026-11-01/title-45.xml?section=147.200"
    with pytest.raises(BaseException) as e:
        http.get(url)
    assert type(e.value).__name__ == "RecordingMissing"
    assert not isinstance(e.value, Exception)  # no adapter's `except Exception` can neutralise it
    assert url in str(e.value) and hashlib.sha1(url.encode()).hexdigest() in str(e.value)
    assert list(tmp_path.iterdir()) == []  # and nothing was written back into the recording
