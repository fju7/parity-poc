"""The design characteriser must catch a mischaracterised trial — and only that.

The failure this is built for is recorded in source_ledger.py: the page called
MONALEESA-2's final overall-survival p-value "two-sided" in five places, and
three gate runs agreed, because a model checker drawn from the same
distribution as the writer re-derives the writer's guess and it reads like
corroboration. Design facts are registered, so this check asks the registry.

The registry is stubbed here. These tests are about the comparison logic and
the scoping, not about ClinicalTrials.gov being up.
"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "backend" / "scripts" / "whatholdsup" / "study_design.py"
spec = importlib.util.spec_from_file_location("study_design", MOD)
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)

BLOCKED = "BLOCKED"

# KEYNOTE-942 as ClinicalTrials.gov actually records it: masking NONE.
OPEN_LABEL = {"phases": ["PHASE2"], "studyType": "INTERVENTIONAL",
              "designInfo": {"allocation": "RANDOMIZED", "interventionModel": "PARALLEL",
                             "maskingInfo": {"masking": "NONE"}}}
# PALOMA-3 as recorded: TRIPLE masked, randomised, Phase 3.
MASKED = {"phases": ["PHASE3"], "studyType": "INTERVENTIONAL",
          "designInfo": {"allocation": "RANDOMIZED", "interventionModel": "PARALLEL",
                         "maskingInfo": {"masking": "TRIPLE"}}}


@pytest.fixture
def case(tmp_path, monkeypatch):
    d = tmp_path / "WHU-999-testissue"
    d.mkdir()
    (d / "design.json").write_text(json.dumps(
        {"trials": {"KEYNOTE-942": "NCT03897881", "PALOMA-3": "NCT01942135"}}))
    monkeypatch.setattr(sd, "CASES", tmp_path)
    return d


def stub(monkeypatch, mapping):
    monkeypatch.setattr(sd, "registry", lambda nct: mapping.get(nct))


def states(rows):
    return {n: s for n, s, _d in rows}


def test_blinded_claim_about_an_open_label_trial_blocks(case, monkeypatch):
    """THE CASE THIS FILE EXISTS FOR."""
    stub(monkeypatch, {"NCT03897881": OPEN_LABEL})
    page = "<p>In the double-blind Phase 2b trial, KEYNOTE-942, recurrences were fewer.</p>"
    rows = sd.preflight_rows("testissue", page)
    assert states(rows)["design claims match the registry"] == BLOCKED
    detail = [d for n, _s, d in rows if n == "design claims match the registry"][0]
    assert "masking NONE" in detail and "KEYNOTE-942" in detail


def test_accurate_description_passes(case, monkeypatch):
    """A check that fires on correct work gets switched off."""
    stub(monkeypatch, {"NCT01942135": MASKED})
    page = "<p>PALOMA-3 was a randomised, double-blind Phase 3 trial of palbociclib.</p>"
    rows = sd.preflight_rows("testissue", page)
    assert BLOCKED not in states(rows).values(), rows


def test_wrong_phase_blocks(case, monkeypatch):
    stub(monkeypatch, {"NCT01942135": MASKED})
    page = "<p>PALOMA-3 was a Phase 2 trial.</p>"
    rows = sd.preflight_rows("testissue", page)
    assert states(rows)["design claims match the registry"] == BLOCKED


def test_design_words_do_not_leak_across_sentences(case, monkeypatch):
    """The first version reached 260 characters either side of a trial name and
    reported PALOMA-3 as 'double-blind' and 'Phase 2b' by collecting the
    KEYNOTE-942 sentence next to it. It caught the real error and invented a
    second one, which is the failure mode that gets a check switched off.
    """
    stub(monkeypatch, {"NCT03897881": OPEN_LABEL, "NCT01942135": MASKED})
    page = ("<p>In the double-blind Phase 2b trial, KEYNOTE-942, recurrences were fewer.</p>"
            "<p>PALOMA-3 was a randomised Phase 3 study of palbociclib plus fulvestrant.</p>")
    found = {(f["trial"], f["label"]) for f in sd.findings("testissue", page)}
    assert ("PALOMA-3", "blinded") not in found
    assert ("PALOMA-3", "phase") in found
    assert ("KEYNOTE-942", "blinded") in found
    detail = [d for n, _s, d in sd.preflight_rows("testissue", page)
              if n == "design claims match the registry"][0]
    assert "PALOMA-3" not in detail


def test_repeated_characterisation_is_one_finding(case, monkeypatch):
    """MONALEESA-2's p-value was wrong in five places and that was one error."""
    stub(monkeypatch, {"NCT03897881": OPEN_LABEL})
    page = ("<p>KEYNOTE-942 was double-blind.</p><p>The double-blind KEYNOTE-942 trial ran on.</p>"
            "<p>Again, KEYNOTE-942 was double-blind.</p>")
    fs = [f for f in sd.findings("testissue", page) if f["label"] == "blinded"]
    assert len(fs) == 1


def test_unresolvable_trial_with_no_attestation_blocks(case, monkeypatch):
    """An unverified design claim is not a verified one."""
    stub(monkeypatch, {})          # registry returns nothing for anything
    page = "<p>PALOMA-3 was a double-blind trial.</p>"
    rows = sd.preflight_rows("testissue", page)
    assert states(rows)["design claims nobody could check"] == BLOCKED


def test_loose_characterisation_is_surfaced_not_blocked(case, monkeypatch):
    """Coverage stated rather than hidden: a design word naming no trial we can
    identify was verified by nothing, and the check says so without blocking."""
    stub(monkeypatch, {})
    page = "<p>It was an open-label study with no control arm.</p>"
    rows = sd.preflight_rows("testissue", page)
    assert states(rows).get("design claims tied to no trial") == "warn"
    assert BLOCKED not in states(rows).values()
