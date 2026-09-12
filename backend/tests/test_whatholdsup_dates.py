"""Dates a reader sees are editorial-local. Both ends of every comparison agree.

WHAT WENT WRONG
---------------
Two clocks, one subtraction, in three places.

  index_dates.expected()      took .date() on a UTC-aware datetime and compared
                              it to a date typed in New York. cdk46 was published
                              2026-08-28 22:17 ET = 2026-08-29 02:17 UTC. The
                              homepage said 28 August and was right; the checker
                              would have "corrected" it to the 29th.

  corrections_intake          business_days_since() subtracted a local
  .business_days_since()      date.today() from a UTC-stamped `received`. It
                              measures the footer's published promise -- 48
                              hours, 10 business days -- and it errs SHORT,
                              which reports us as more timely than we are.

  watch.days_since_check()    same shape, on the living-issue staleness display.

THE FIXTURES ARE REAL INSTANTS FROM THE RECORD
----------------------------------------------
2026-08-29T02:22:50Z is cdk46's own first publication row. It is the case that
started this, and a test that does not carry it is not a regression test.

BOTH DIRECTIONS
---------------
A zone fix can fail two ways: by not shifting a day that should shift, and by
shifting one that should not. Both are here. So is the DST pair, because
EDITORIAL_TZ is an IANA name and a fixed -04:00 or -05:00 gets one of these two
January/July cases wrong whichever one is chosen.
"""
import importlib.util
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


I = _mod("index_dates")
C = _mod("corrections_intake")


def _utc(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# The constant itself
# ---------------------------------------------------------------------------

def test_editorial_tz_is_an_iana_zone_not_a_fixed_offset():
    assert I.EDITORIAL_TZ.key == "America/New_York"
    jan = _utc("2026-01-15T12:00:00Z").astimezone(I.EDITORIAL_TZ).utcoffset()
    jul = _utc("2026-07-15T12:00:00Z").astimezone(I.EDITORIAL_TZ).utcoffset()
    assert jan == timedelta(hours=-5)
    assert jul == timedelta(hours=-4)
    assert jan != jul, "a fixed offset cannot be right in both January and July"


def test_a_fixed_offset_would_get_one_of_these_two_days_wrong():
    """The argument for the IANA name, executed rather than asserted."""
    winter, summer = _utc("2026-01-15T04:30:00Z"), _utc("2026-07-15T03:30:00Z")
    assert I.editorial_date(winter) == date(2026, 1, 14)
    assert I.editorial_date(summer) == date(2026, 7, 14)
    # -04:00 all year would put the January instant on the 15th.
    assert (winter + timedelta(hours=-4)).date() == date(2026, 1, 15)
    # -05:00 all year would put the July instant on the 14th -- right by luck
    # here, and wrong on any instant between 23:00 and 00:00 EDT.
    assert (summer + timedelta(hours=-5)).date() == date(2026, 7, 14)


# ---------------------------------------------------------------------------
# index_dates — the case that started it
# ---------------------------------------------------------------------------

def test_the_cdk46_instant_is_28_august_in_the_editorial_zone():
    at = _utc("2026-08-29T02:22:50Z")          # cdk46's own first publish row
    assert at.date() == date(2026, 8, 29)      # what the old code compared
    assert I.editorial_date(at) == date(2026, 8, 28)   # what the index says


def test_a_daytime_instant_does_not_shift():
    """The other direction: a fix that moves every date is also broken."""
    assert I.editorial_date(_utc("2026-08-28T16:05:57Z")) == date(2026, 8, 28)
    assert I.editorial_date(_utc("2026-09-09T18:33:15Z")) == date(2026, 9, 9)


def test_the_live_index_agrees_with_the_record():
    assert I.audit() == []


def test_a_reconciliation_is_not_a_reader_facing_update():
    """record-live writes action:"republish" for a change signed as NOT touching
    the argument. deskilling got one on 9 September for a nav link."""
    assert "republish" not in I.PUBLICATION_ACTIONS
    assert I.reconciliations("deskilling"), "fixture gone: expected a record-live row"
    assert "updated" not in I.expected("deskilling")


# ---------------------------------------------------------------------------
# corrections_intake — the published promise
# ---------------------------------------------------------------------------

def _old_business_days_since(iso, today):
    """The code as it stood before 2026-09-09, for comparison only."""
    d, n = datetime.fromisoformat(iso).date(), 0
    while d < today:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def test_the_sla_clock_straddling_midnight_utc():
    received = "2026-09-02T02:00:00+00:00"     # Tue 1 Sep, 22:00 in New York
    today = date(2026, 9, 3)                   # Thu
    assert C._editorial_day(received) == date(2026, 9, 1)
    assert C.business_days_since(received, today) == 2
    # And the bug it replaces, in the direction that flattered us:
    assert _old_business_days_since(received, today) == 1


def test_the_sla_clock_when_nothing_straddles():
    received = "2026-09-01T16:00:00+00:00"     # Tue 1 Sep, 12:00 in New York
    today = date(2026, 9, 3)
    assert C.business_days_since(received, today) == 2
    assert _old_business_days_since(received, today) == 2


def test_a_naive_stamp_is_read_as_utc_because_that_is_what_we_write():
    assert C._editorial_day("2026-09-02T02:00:00") == date(2026, 9, 1)


def test_a_bare_day_typed_by_a_person_is_already_editorial():
    """--on 2026-09-01 means that day here, not midnight in Greenwich. Reading
    it as a UTC instant would silently move it to 31 August."""
    assert C._editorial_day("2026-09-01") == date(2026, 9, 1)


def test_an_unparseable_stamp_returns_none_rather_than_a_guess():
    assert C._editorial_day("not a date") is None
    assert C.business_days_since("not a date", date(2026, 9, 3)) == 0


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("  ok    %s" % name)
            except AssertionError as e:
                fails += 1
                print("  FAIL  %s: %s" % (name, e))
    print("\n%s" % ("all pass" if not fails else "%d failure(s)" % fails))
    raise SystemExit(1 if fails else 0)


# ---------------------------------------------------------------------------
# index_dates — the provenance line, slot by slot (12 September 2026)
# ---------------------------------------------------------------------------
#
# melanoma's card read "14 corrections · sources checked 9 September 2026"
# while the record said 15 and 11 September. The date rows passed it and the
# marker-presence row passed it. The line is generated; the card was typed.

def _index_with(old: str, new: str) -> str:
    html = I.INDEX.read_text(encoding="utf-8")
    assert html.count(old) == 1, "fixture drift: %r not found exactly once" % old
    return html.replace(old, new)


def _melanoma_line() -> str:
    m = [c for c in I.CARD.finditer(I.INDEX.read_text(encoding="utf-8")) if c.group("slug") == "melanoma"][0]
    return I.PROV.search(m.group("meta")).group("line")


def test_the_cards_equal_the_generator_exactly():
    assert I.audit() == []
    html = I.INDEX.read_text(encoding="utf-8")
    for m in I.CARD.finditer(html):
        assert I.PROV.search(m.group("meta")).group("line") == I.meta_html(m.group("slug"), I.CARD_ORDINAL)


def test_a_wrong_correction_count_blocks_and_names_the_field_and_both_values():
    line = _melanoma_line()
    n = int([s for s in I._slots(line) if s.endswith("corrections")][0].split()[0])
    bad = I.audit(_index_with("%d corrections" % n, "%d corrections" % (n + 1)))
    assert len(bad) == 1
    assert bad[0].startswith("melanoma: corrections -- page says '%d corrections', record says '%d corrections'" % (n + 1, n))


def test_a_wrong_sources_checked_date_blocks_and_names_the_field():
    line = _melanoma_line()
    slot = [s for s in I._slots(line) if s.startswith("sources checked")][0]
    bad = I.audit(_index_with(slot, "sources checked 1 January 2026"))
    assert bad == ["melanoma: sources checked -- page says 'sources checked 1 January 2026', record says %r" % slot]


def test_a_missing_marker_is_the_corrections_slot_not_a_second_row():
    line = _melanoma_line()
    slot = [s for s in I._slots(line) if s.endswith("corrections")][0]
    bad = I.audit(_index_with(slot, "no corrections"))
    assert bad == ["melanoma: corrections -- page says 'no corrections', record says %r" % slot]


def test_a_stale_date_is_reported_once_by_the_date_row_with_its_classification():
    line = _melanoma_line()
    slot = [s for s in I._slots(line) if s.startswith("revised")][0]
    bad = I.audit(_index_with(slot, "revised 4 September 2026"))
    assert len(bad) == 1 and "[BEHIND]" in bad[0] and "behind by" in bad[0]


def test_a_wording_mismatch_the_date_rows_accept_is_still_caught():
    line = _melanoma_line()
    slot = [s for s in I._slots(line) if s.startswith("revised")][0]
    bad = I.audit(_index_with(slot, slot.replace("revised", "updated")))
    assert bad == ["melanoma: revised -- page says %r, record says %r" % (slot.replace("revised", "updated"), slot)]


def test_the_preflight_row_blocks_on_a_field_difference():
    line = _melanoma_line()
    slot = [s for s in I._slots(line) if s.startswith("sources checked")][0]
    rows = I.preflight_rows(_index_with(slot, "sources checked 1 January 2026"))
    assert rows[0][0] == "homepage dates match the record" and rows[0][1] == I.BAD
    assert "sources checked -- page says" in rows[0][2]
