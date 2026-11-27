"""The text-assembly sweep (advisor's ruling 1 on P162, 2026-11-26): every label and readers'-list line is exactly one
sentence and bindable. $0, offline.

WHU-OT1-01c stopped at coverage: S005's registry title ends with a full stop, so its label "... appointments. [5]" split
the readers'-list line in two; the line builder cut the quotation to "..." and nothing could bind the line.
coverage_check.safe_label now drops a title's own end punctuation before its number and, if the label still splits the
line, names the source by number ("source [5]").

Runs text_sweep's classes over what the repository holds: every source title recorded in the orchestrated cases
(02z-02zd, 01, 01b, 01c, Q1-04) in every readers'-list state, and the constructed hard cases. The unit class needs each
run's held texts and is run locally (text_sweep.py unit <slug> under orch/run_env.py; reported in deviations.md).
Recorded pages are records: 01c's page keeps the lines the old code wrote, and only those fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "scripts" / "whatholdsup"))

import coverage_check as C  # noqa: E402
import text_sweep as T  # noqa: E402

S005 = "Mobile phone messaging reminders for attendance at healthcare appointments."


@pytest.fixture(autouse=True)
def lean(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")


def test_01cs_s005_line_is_one_sentence_and_bindable():
    srcs = [{"id": "S00%d" % i, "title": "t"} for i in range(1, 5)] + [{"id": "S005", "title": S005}]
    unit = "Overall, the attendance to appointment rates were 67.8% for the no reminders group."
    for st in T.STATES:
        line = T.label_line(st, unit, srcs, "S005")
        assert T.line_problems(line, unit) == [], line
        assert ". [5]" not in line and line.endswith(("[5]).", "removed).", "page).", "reached)."))


@pytest.mark.parametrize("title", T.HARD_TITLES)
def test_a_hard_title_keeps_every_line_one_sentence(title):
    srcs = [{"id": "S001", "title": "first"}, {"id": "S002", "title": title}]
    for span in T.HARD_SPANS:
        for st in T.STATES:
            line = T.label_line(st, span, srcs, "S002")
            assert T.line_problems(line, span) == [], (title, span, line)


def test_a_label_that_cannot_be_mended_is_the_source_number():
    assert C.safe_label("not_material", "Part one. Part two of a title [3]") in (
        "Part one. Part two of a title [3]", "source [3]")
    assert C.safe_label("not_material", "Does it work? [2]") == "Does it work [2]"
    assert C.safe_label("not_material", "A plain title [4]") == "A plain title [4]"


def test_every_recorded_title_in_every_state():
    n, bad = T.check_titles()
    assert n > 300 and bad == [], bad[:3]


def test_the_constructed_cases():
    n, bad = T.check_constructed()
    assert n == len(T.HARD_TITLES) * (len(T.HARD_SPANS) + 1) * len(T.STATES) and bad == [], bad[:3]


def test_recorded_page_lines_fail_only_on_01cs_page_for_its_two_full_stop_titles():
    # 01c's page as the run wrote it: S005 "... appointments." and S007 "... Systematic Reviews." each split a line
    n, bad = T.check_page_lines()
    assert n > 100
    assert {b[0] for b in bad} <= {"WHU-OT1-01c-whu-lean-orch-t1-q1-01c"}
    assert all("Mobile phone messaging reminders" in b[1] or "The Impact of mHealth Interventions" in b[1]
               or b[1] in ("[5]).", "[7]).") for b in bad)


def test_the_checker_itself_finds_a_split_and_an_empty_quotation():
    assert "splits into 2 sentences" in T.line_problems("Outside this question: “a” (Title. [5]).")
    assert "no quotation" in T.line_problems("Outside this question: “…” (Title [5]).")
    assert "quotation not inside its unit" in T.line_problems("Outside this question: “abc” (T [1]).", "xyz")
