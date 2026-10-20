"""The card's "published" date follows a page that predates its record.

published.json begins on 28 August 2026 because it was created then; melanoma
was live from 26 August (issues/WHU-001-melanoma/provenance.md). The record is
not backfilled, so the masthead said 26 August and every card said 28. A
case's provenance.md may now carry "**First live:** YYYY-MM-DD"; when that is
earlier than the record's first day the card uses it, and otherwise the
record stands.
"""
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("index_dates", WHU / "index_dates.py")
I = importlib.util.module_from_spec(spec)
spec.loader.exec_module(I)

RECORD = [date(2026, 8, 28), date(2026, 9, 10)]


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "ROOT", tmp_path)
    d = tmp_path / "issues" / "WHU-099-x"
    d.mkdir(parents=True)

    def write(text):
        (d / "provenance.md").write_text(text, encoding="utf-8")
    return write


def test_a_provenance_first_live_date_earlier_than_the_record_is_shown(case):
    case("# x\n\n**First live:** 2026-08-26 — \"live from 26 August.\"\n")
    assert I.first_live("x") == date(2026, 8, 26)
    assert I.published_date("x", RECORD) == date(2026, 8, 26)


def test_an_issue_without_one_shows_the_records_date(case, tmp_path):
    assert I.published_date("x", RECORD) == date(2026, 8, 28)       # no provenance.md
    case("# x\n\nThe page was live from 26 August.\n")               # prose, no field
    assert I.first_live("x") is None
    assert I.published_date("x", RECORD) == date(2026, 8, 28)


def test_a_provenance_date_later_than_the_record_is_ignored(case):
    case("**First live:** 2026-08-30\n")
    assert I.published_date("x", RECORD) == date(2026, 8, 28)


def test_revised_still_comes_from_the_record_alone(case, monkeypatch):
    case("**First live:** 2026-08-26\n")
    monkeypatch.setattr(I, "publication_dates", lambda slug: RECORD)
    monkeypatch.setattr(I, "corrections_count", lambda slug: 0)
    assert I.expected("x") == {"published": date(2026, 8, 26), "updated": date(2026, 9, 10)}


def test_melanoma_carries_its_first_live_date():
    assert I.first_live("melanoma") == date(2026, 8, 26)
    assert I.first_live("cdk46") is None and I.first_live("deskilling") is None
