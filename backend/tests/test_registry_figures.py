"""Figures must be checked against the registry, and against the RIGHT trial.

Built 2026-08-31 after a $5.20 gate run reported four findings that were all
wrong the same way. The SOURCE role searches the web; ClinicalTrials.gov's
structured results are not reliably reachable that way, and it said so in its
own notes -- "only a stub page was returned". It then reported NOT_FOUND and
twice escalated to WRONG_VALUE, which reads as "this figure is wrong" rather
than "I could not look". Acting on it would have replaced a correct HR 0.921
with 0.956.

The registry is stubbed here; these tests are about scope and attribution.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "registry_figures", ROOT / "backend" / "scripts" / "whatholdsup" / "registry_figures.py")
rf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rf)

PALOMA2 = "NCT01740427"
ML7 = "NCT02278120"


@pytest.fixture
def case(tmp_path, monkeypatch):
    d = tmp_path / "WHU-999-t"
    d.mkdir()
    (d / "design.json").write_text(json.dumps({"trials": {"PALOMA-2": PALOMA2}}))
    monkeypatch.setattr(rf, "CASES", tmp_path)
    monkeypatch.setattr(rf, "_CACHE", {})
    monkeypatch.setattr(rf, "registry_text", lambda nct: {
        PALOMA2: 'HR 0.921 ci 0.755 to 1.124 p 0.208706',
        ML7: 'HR 0.711 p 0.00973',
    }.get(nct))
    return d


def test_confirms_a_figure_the_registry_posts(case):
    page = ("<p>Registry PALOMA-2 &mdash; ClinicalTrials.gov results posting. NCT01740427. "
            "Gives the final overall-survival analysis as HR 0.921 (0.755&ndash;1.124).</p>")
    fs = rf.findings("t", page)
    assert fs and all(f["in_registry"] for f in fs), fs
    assert {f["norm"] for f in fs} == {"0.921", "0.755", "1.124"}


def test_a_figure_the_registry_does_not_post_is_not_called_wrong(case):
    """Absence of evidence. The registry posts a subset of what a paper prints,
    and calling that a contradiction is the mistake being corrected."""
    page = ("<p>Registry PALOMA-2. NCT01740427. The paper rounds this to HR 0.96.</p>")
    rows = rf.preflight_rows("t", page)
    states = {n: s for n, s, _d in rows}
    assert "BLOCKED" not in states.values()
    assert states.get("figures the registry does not post") == "warn"


def test_a_long_prose_block_is_not_attributed(case):
    """THE FAULT THIS FILE EXISTS TO PREVENT.

    Whole-block scope credited MONALEESA-2's '63.9 versus 51.4 months, HR 0.76'
    to MONALEESA-7's registry, because one long section contained a single NCT
    and several trials' figures. A checker that misattributes a figure is worse
    than none — it is the fault that made the gate's own report wrong.
    """
    long_block = ("<p>NCT01740427. " + ("Prose about several trials. " * 40)
                  + "Ribociclib improved survival: HR 0.76. Abemaciclib was HR 0.804.</p>")
    assert len(rf.plain(long_block)) > rf.MAX_BLOCK
    assert rf.findings("t", long_block) == []


def test_two_registry_numbers_in_one_block_is_ambiguous(case):
    page = "<p>NCT01740427 and NCT02278120 both appear here with HR 0.921.</p>"
    assert rf.findings("t", page) == []


def test_repeated_figure_counts_once(case):
    page = ("<p>Registry PALOMA-2. NCT01740427. HR 0.921 in the table.</p>"
            "<p>Registry PALOMA-2. NCT01740427. HR 0.921 again in prose.</p>")
    assert len([f for f in rf.findings("t", page) if f["norm"] == "0.921"]) == 1


def test_an_unreachable_registry_says_nothing(case, monkeypatch):
    """Not reachable is not a finding — the exact error being corrected."""
    monkeypatch.setattr(rf, "registry_text", lambda nct: None)
    page = "<p>Registry PALOMA-2. NCT01740427. HR 0.921 (0.755-1.124).</p>"
    assert rf.findings("t", page) == []
