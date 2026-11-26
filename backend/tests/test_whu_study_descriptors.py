"""Study descriptors are not headline units (advisor's ruling 2 on P157, 2026-11-26).

A sentence that reports only the number, design, population or location of included studies is excluded when lean
derives headline units (lean_coverage.study_descriptor, furniture kind "study descriptor"). Any sentence that also
states an effect, a direction or a certainty grade stays a unit. EXCLUDED are the 11 units the rule excludes in
WHU-OT1-01b's relied-on sources, verbatim.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend" / "scripts" / "whatholdsup"))

import lean_coverage as LC  # noqa: E402

EXCLUDED = [
    "We identiﬁed 18 eligible studies (11 randomised, seven non‐randomised) conducted in Bangladesh, China, Ethiopia, India, Kenya, Palestine, Uganda, and the USA.",
    "Eight randomized trials across varying healthcare contexts in the USA,.",
    "India, China, Guatemala, Ghana, and Kenya, met our inclusion criteria.",
    "We included 27 trials (17,463 participants).",
    "Trial populations were: pregnant and postpartum women (11 trials conducted in low‐, middle‐ or high‐income countries (LMHIC); pregnant and postpartum women living with HIV (three trials carried out in one lower middle‐income country); and parents of children under the age of five years (13 trials conducted in LMHIC).",
    "We included 35 studies, from a wide range of countries on six continents.",
    "Nineteen studies were conducted in low‐ and middle‐income settings and sixteen in high‐income settings.",
    "We identified 35 studies (30 randomized trials and five non‐randomized trials) and analyzed 34 studies (40 comparisons).",
    "Twenty‐nine studies took place in the USA and six studies took place in Canada, France, Israel, and Kenya.",
    "All studies except two took place in outpatient care.",
    "Twenty‐eight studies (reporting a total of thirty‐two comparisons) were included."
]

KEPT = [
    "No trials in any population reported data on unintended consequences.",
    "Nineteen studies were conducted in low- and middle-income settings and the intervention reduced deaths.",
    "Computer\u2010generated reminders delivered on paper to healthcare professionals alone (single\u2010component "
    "intervention) probably improves quality of care compared with usual care (median improvement 11.0% (IQR 5.4% to "
    "20.0%); 27 studies (27 comparisons); moderate\u2010certainty evidence).",
    "We included 27 trials (17,463 participants), which found that reminders may increase attendance.",
    "Eight randomized trials in the USA reported an RR of 1.13.",
    "The intervention may slightly improve patient or client acceptability and satisfaction (1 study, 187 participants).",
]


@pytest.mark.parametrize("s", EXCLUDED)
def test_01bs_descriptors_are_not_headline_units(s):
    assert LC.study_descriptor(s) and LC.furniture(s) == "study descriptor"
    keep, out = LC.split_units([{"text": s}])
    assert keep == [] and out[0]["furniture"] == "study descriptor"


@pytest.mark.parametrize("s", KEPT)
def test_a_sentence_with_an_effect_a_direction_or_a_certainty_grade_stays_a_unit(s):
    assert not LC.study_descriptor(s)


def test_the_count_matches_the_report():
    assert len(EXCLUDED) == 11
