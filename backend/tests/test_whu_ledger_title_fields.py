"""A source's own title in the source list is not a claim about what it says (advisor's ruling 3 on P118-P121,
2026-11-25; source_ledger.title_fields, is_title_field, audit).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): the preflight row "new claims about unread sources" stopped on
"S005: Global Education Monitoring Report 2020: Inclusion and education: All means all." -- the source list's entry
[5] for unheld S005, whose title matches CHARACTERISING on "Report". The word list is unchanged.

Records: the committed folder issues/WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc/ (read only).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
CASE = ROOT / "issues" / "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"
SLUG = "whu-lean-orch-t1-q1-02zc"
ROW = "new claims about unread sources"

import source_ledger as L   # noqa: E402

WORDS = L.CHARACTERISING.pattern


def _page():
    return L.plain((CASE / "draft" / ("%s.html" % SLUG)).read_text(encoding="utf-8"))


def _row(text):
    return next(r for r in L.audit(SLUG, text) if r[0] == ROW)


def test_02zc_s005_title_no_longer_trips_the_row():
    text = _page()
    assert "Global Education Monitoring Report 2020: Inclusion and education: All means all." in text
    assert L.CHARACTERISING.search("Global Education Monitoring Report 2020")           # 'Report' still matches
    assert _row(text)[1] == L.OK


def test_a_page_sentence_saying_what_unread_s005_says_still_trips_it():
    # S005's identifier ends in its title's own full stop, so a sentence about it ends on the title
    sent = ("Most countries exclude children with disabilities, as reported in the Global Education Monitoring "
            "Report 2020: Inclusion and education: All means all.")
    got = _row(_page() + " " + sent)
    assert got[1] == L.BAD and got[2].count("S005: ") == 1 and "S005: Most countries exclude" in got[2]


def test_only_whole_title_fields_are_skipped():
    titles = L.title_fields([{"id": "S1", "title": "The Trial Report: Results.", "also_called": ["TR-1 report"],
                              "proposed": {"title": "A trial report"},
                              "registry_record": {"title": "Final report of the trial"}}])
    assert L.is_title_field("The Trial Report: Results.", titles)
    assert L.is_title_field("tr-1 report.", titles) and L.is_title_field("Final report of the trial", titles)
    assert not L.is_title_field("The Trial Report: Results. reports a benefit", titles)
    assert not L.is_title_field("", titles)


def test_the_word_list_is_unchanged():
    assert WORDS.startswith(r"\b(") and "reports?" in WORDS and "states?" in WORDS and "characterizes?" in WORDS
