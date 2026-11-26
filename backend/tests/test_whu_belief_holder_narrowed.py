"""P142's belief-holder pattern, narrowed (advisor's ruling 2 on P152, 2026-11-26).

On the fresh Q1-01 (WHU-OT1-01b) the preflight row "belief claims rest on a verified outlet" stopped on a findings
sentence: "commonly reported" matched. The pattern now catches only sentences asserting that people, groups or the
public hold the belief.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "scripts" / "whatholdsup"))

import belief_claims as B  # noqa: E402

FINDING_01B = ("Blood pressure was the most commonly reported clinical endpoint, and intervention patients had a median "
               "systolic reduction of only 1.0 mmHg, with an IQR running from a 2.3 mmHg reduction to a 2.0 mmHg "
               "increase [7].")


def test_01bs_findings_sentence_no_longer_trips_the_row():
    assert B.holder_sentences([FINDING_01B]) == []
    ok, _ = B.check([FINDING_01B], {"belief": {"carried_by": [{"outlet": "PATH"}]}})
    assert ok


@pytest.mark.parametrize("s", ["Many parents believe X.", "X is widely believed.", "It is often said that X.",
                               "The conventional wisdom is that X.", "Campaigners argue that X.",
                               "X is commonly held to be true."])
def test_sentences_saying_who_holds_the_belief_still_do(s):
    assert B.holder_sentences([s]) == [s]


@pytest.mark.parametrize("s", ["The most widely cited trial enrolled 2,086 people.",
                               "Adherence was the most frequently reported outcome.",
                               "The finding was often repeated across the included studies."])
def test_evidence_reporting_verbs_are_not_holder_claims(s):
    assert B.holder_sentences([s]) == []
