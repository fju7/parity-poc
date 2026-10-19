"""When does the Signal golden-set job fail?

Rule (2026-10-19): the job fails only on things nobody has looked at --
a drift with no entry in signal_golden_decisions.json, a category with no
baseline, a category the run could not measure, or a live label that differs
from the baseline without a recorded exception. Drifts that already have a
decision, and warnings, are printed in the report but do not fail the job.

Two levels, because a unit test of the rule cannot catch main() wiring around
it wrongly:
  1. run_outcome / split_decided -- the rule itself, one test per case.
  2. main() end to end with the model, Supabase and the live page stubbed,
     replaying the shape of scheduled run 39258219331 (2026-10-19) against the
     REAL decisions file.
No network, no model call.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SIGNAL = Path(__file__).resolve().parents[2] / "scripts" / "signal"
# scripts/signal itself (not scripts/) -- see test_no_stdlib_shadowing.py.
sys.path.insert(0, str(SIGNAL))
_spec = importlib.util.spec_from_file_location("golden_set", SIGNAL / "golden_set.py")
gs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gs)


def drift(slug, category, why):
    return {"slug": slug, "category": category, "why": why}


DECISIONS = {
    ("car-t-cell-therapy", "long_term_outcomes", "consensus -> debated"):
        {"decision": "fixture_is_right"},
    ("social-media-teen-mental-health", "methodology", "side BALANCE REVERSED"):
        {"decision": "instrument_not_fit_to_publish"},
}
KNOWN_STATUS = drift("car-t-cell-therapy", "long_term_outcomes", "consensus -> debated")
KNOWN_SIDES = drift("social-media-teen-mental-health", "methodology",
                    "side BALANCE REVERSED [10, 3] -> [4, 9]")
NEW = drift("glp1-drugs", "cardiovascular", "consensus -> debated")
WARN = drift("mrna-vaccine-myocarditis", "biological_mechanism",
             "side balance crossed the tie line [5, 1] -> [3, 2]")


def outcome(**kw):
    base = dict(unbaselined=[], unmeasured=[], undecided=[], stale_new=[],
                decided=[], warnings=[])
    base.update(kw)
    return gs.run_outcome(**base)


# --- 1. the rule, one case each ------------------------------------------------

def test_nothing_moved_passes():
    assert outcome() == (0, "clean")


def test_warnings_alone_pass():
    assert outcome(warnings=[WARN]) == (0, "known_only")


def test_known_decided_drift_passes():
    decided, undecided = gs.split_decided([KNOWN_STATUS], DECISIONS)
    assert undecided == []
    assert outcome(decided=decided) == (0, "known_only")


def test_known_side_reversal_passes_whatever_the_counts():
    # The counts differ every run; the decision keys on the kind of move.
    for counts in ("[10, 3] -> [4, 9]", "[10, 3] -> [3, 8]", "[10, 3] -> [2, 10]"):
        f = drift("social-media-teen-mental-health", "methodology",
                  f"side BALANCE REVERSED {counts}")
        decided, undecided = gs.split_decided([f], DECISIONS)
        assert undecided == [] and len(decided) == 1


def test_new_drift_fails():
    decided, undecided = gs.split_decided([NEW], DECISIONS)
    assert decided == []
    assert outcome(undecided=undecided) == (1, "new_drift")


def test_known_drift_in_a_new_direction_fails():
    # A decision covers one direction. The reverse move is news.
    reverse = drift("car-t-cell-therapy", "long_term_outcomes", "debated -> consensus")
    _, undecided = gs.split_decided([reverse], DECISIONS)
    assert outcome(undecided=undecided) == (1, "new_drift")


def test_a_decision_does_not_cover_another_category():
    other = drift("car-t-cell-therapy", "efficacy", "consensus -> debated")
    _, undecided = gs.split_decided([other], DECISIONS)
    assert outcome(undecided=undecided) == (1, "new_drift")


def test_new_drift_fails_even_alongside_known_ones_and_warnings():
    decided, undecided = gs.split_decided([KNOWN_STATUS, KNOWN_SIDES, NEW], DECISIONS)
    assert len(decided) == 2 and len(undecided) == 1
    assert outcome(decided=decided, undecided=undecided, warnings=[WARN]) == (1, "new_drift")


def test_entry_without_a_decision_word_does_not_count():
    # load_decisions() drops rows whose `decision` is empty; an empty
    # decisions map must leave the drift undecided.
    _, undecided = gs.split_decided([KNOWN_STATUS], {})
    assert outcome(undecided=undecided) == (1, "new_drift")


def test_unbaselined_fails():
    assert outcome(unbaselined=[{"slug": "x", "category": "y"}]) == (1, "unbaselined")


def test_unmeasured_fails_even_if_everything_else_is_decided():
    decided, _ = gs.split_decided([KNOWN_STATUS], DECISIONS)
    assert outcome(unmeasured=[{"slug": "x", "category": "y"}],
                   decided=decided) == (1, "unmeasured")


def test_unrecorded_site_mismatch_fails():
    assert outcome(stale_new=[{"slug": "x", "category": "y"}]) == (1, "site_mismatch")


def test_site_mismatch_fails_even_when_every_drift_is_decided():
    decided, _ = gs.split_decided([KNOWN_STATUS], DECISIONS)
    assert outcome(stale_new=[{"slug": "x", "category": "y"}],
                   decided=decided) == (1, "site_mismatch")


# --- 2. main() end to end --------------------------------------------------------

def _fixture_entries():
    return [
        {"slug": "car-t-cell-therapy", "category": "long_term_outcomes",
         "claims": 23, "expected_status": "consensus", "expected_debated_sides": None},
        {"slug": "social-media-teen-mental-health", "category": "methodology",
         "claims": 43, "expected_status": "debated", "expected_debated_sides": [10, 3]},
        {"slug": "glp1-drugs", "category": "cardiovascular",
         "claims": 14, "expected_status": "consensus", "expected_debated_sides": None},
        {"slug": "glp1-drugs", "category": "efficacy",
         "claims": 41, "expected_status": "consensus", "expected_debated_sides": None},
    ]


def _run_main(monkeypatch, capsys, readings, decisions, stale=()):
    entries = _fixture_entries()

    def fake_measure(es, adopt_new=False):
        out = []
        for e in es:
            status, sides = readings[(e["slug"], e["category"])]
            out.append({**e, "actual": {"status": status, "sides": sides},
                        "claims_now": e["claims"]})
        return out, []

    monkeypatch.setattr(gs, "load_fixture", lambda: {
        "recorded_at": "2026-08-25", "model": "stub", "categories": entries})
    monkeypatch.setattr(gs, "measure", fake_measure)
    monkeypatch.setattr(gs, "warn_if_unpinned", lambda *_: None)
    monkeypatch.setattr(gs, "published_mismatches", lambda _e: list(stale))
    monkeypatch.setattr(gs, "load_published_exceptions", lambda: {})
    monkeypatch.setattr(gs, "load_decisions", lambda: decisions)
    monkeypatch.setattr(sys, "argv", ["golden_set.py"])
    code = gs.main()
    return code, capsys.readouterr().out


RUN_2026_10_19 = {
    ("car-t-cell-therapy", "long_term_outcomes"): ("debated", [6, 2]),
    ("social-media-teen-mental-health", "methodology"): ("debated", [4, 9]),
    ("glp1-drugs", "cardiovascular"): ("debated", [2, 2]),
    ("glp1-drugs", "efficacy"): ("consensus", None),
}


GLP1_CV = ("glp1-drugs", "cardiovascular", "consensus -> debated")


def _real_decisions_without_glp1():
    # glp1 cardiovascular was decided on 2026-10-19 (after this run). Remove it
    # so the test keeps exercising the undecided path whatever the file holds.
    return {k: v for k, v in gs.load_decisions().items() if k != GLP1_CV}


def test_main_fails_on_the_one_undecided_drift_and_still_reports_the_known_ones(monkeypatch, capsys):
    code, out = _run_main(monkeypatch, capsys, RUN_2026_10_19, _real_decisions_without_glp1())
    assert code == 1
    assert "GOLDEN_OUTCOME=new_drift" in out
    assert "ALREADY DECIDED" in out and "car-t-cell-therapy" in out
    tail = out.split("nobody has decided about it yet.", 1)[1]
    assert "glp1-drugs" in tail and "car-t-cell-therapy" not in tail


def test_main_passes_once_that_drift_is_decided(monkeypatch, capsys):
    decisions = _real_decisions_without_glp1()
    decisions[GLP1_CV] = {"decision": "fixture_is_right", "reason": "test stub"}
    code, out = _run_main(monkeypatch, capsys, RUN_2026_10_19, decisions)
    assert code == 0
    assert "GOLDEN_OUTCOME=known_only" in out
    # Passing does not hide anything: the known drifts are still listed.
    assert "DRIFTED" in out and "ALREADY DECIDED" in out


def test_main_fails_on_an_unrecorded_site_mismatch_with_nothing_else_wrong(monkeypatch, capsys):
    clean = {k: (("debated", [10, 3]) if k[1] == "methodology" else ("consensus", None))
             for k in RUN_2026_10_19}
    stale = [{"slug": "glp1-drugs", "category": "efficacy", "live": "debated",
              "why": "debated -> consensus"}]
    code, out = _run_main(monkeypatch, capsys, clean, gs.load_decisions(), stale=stale)
    assert code == 1 and "GOLDEN_OUTCOME=site_mismatch" in out


def test_main_unmeasured_fails(monkeypatch, capsys):
    entries = _fixture_entries()

    def blind(es, adopt_new=False):
        return [{**e, "actual": None, "note": "api failed"} for e in es], []

    monkeypatch.setattr(gs, "load_fixture", lambda: {
        "recorded_at": "x", "model": "stub", "categories": entries})
    monkeypatch.setattr(gs, "measure", blind)
    monkeypatch.setattr(gs, "warn_if_unpinned", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["golden_set.py"])
    assert gs.main() == 1
    assert "GOLDEN_OUTCOME=unmeasured" in capsys.readouterr().out


def test_main_unbaselined_fails(monkeypatch, capsys):
    entries = _fixture_entries()

    def with_gap(es, adopt_new=False):
        measured = [{**e, "actual": {"status": e["expected_status"],
                                     "sides": e["expected_debated_sides"]},
                     "claims_now": e["claims"]} for e in es]
        return measured, [{"slug": "glp1-drugs", "category": "new_cat",
                           "claims": 5, "why": "5 claims, no fixture entry"}]

    monkeypatch.setattr(gs, "load_fixture", lambda: {
        "recorded_at": "x", "model": "stub", "categories": entries})
    monkeypatch.setattr(gs, "measure", with_gap)
    monkeypatch.setattr(gs, "warn_if_unpinned", lambda *_: None)
    monkeypatch.setattr(sys, "argv", ["golden_set.py"])
    assert gs.main() == 1
    assert "GOLDEN_OUTCOME=unbaselined" in capsys.readouterr().out


def test_the_real_decisions_file_now_passes_the_2026_10_19_run(monkeypatch, capsys):
    code, out = _run_main(monkeypatch, capsys, RUN_2026_10_19, gs.load_decisions())
    assert code == 0 and "GOLDEN_OUTCOME=known_only" in out


def test_the_real_decisions_file_loads_and_keys_both_drift_kinds():
    d = gs.load_decisions()
    assert GLP1_CV in d
    assert ("car-t-cell-therapy", "long_term_outcomes", "consensus -> debated") in d
    assert ("social-media-teen-mental-health", "methodology", "side BALANCE REVERSED") in d
