"""A ruling's sentence that a later lean fail-safe record removed is superseded, not missing (P208, after WHU-OT1-04f:
the overstatement check removed an advocate amend's sentence and applied_check reported the amend as a mismatch). $0."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import applied_check as AC  # noqa: E402
import lean_failsafe as FS  # noqa: E402

AMENDED = "Its role grows over time, from a modest contribution today to several gigatons by mid-century [1]."
OTHER = "The firmest point is that deep reductions come first [1]."


def _case(tmp_path, failsafe_sentence):
    (tmp_path / "rulings").mkdir()
    (tmp_path / "rulings" / "rulings.jsonl").write_text(json.dumps({
        "id": "r1", "ruling": "amend", "ruling_kind": "advocate", "text": AMENDED,
        "inputs": {"sentence": "Its role grows over time [1, 4]."}, "at": "2026-11-27T18:00:00+00:00"}) + "\n")
    if failsafe_sentence:
        FS.record("overstatement", {"protected": None, "sentence": failsafe_sentence, "kind": "overstatement",
                                    "ref": {"finding_key": "k1"}}, tmp_path)
    return tmp_path


def test_a_failsafe_removal_supersedes_the_rulings_sentence(tmp_path):
    case = _case(tmp_path, AMENDED)
    r = AC.check(case, "<p>%s</p>" % OTHER)
    assert r["mismatches"] == [] and any("lean fail-safe (overstatement)" in s["by"] for s in r["superseded"])


def test_without_the_failsafe_record_it_is_still_a_mismatch(tmp_path):
    case = _case(tmp_path, None)
    assert len(AC.check(case, "<p>%s</p>" % OTHER)["mismatches"]) == 1


def test_a_failsafe_removal_of_another_sentence_does_not_excuse_it(tmp_path):
    case = _case(tmp_path, OTHER)
    assert len(AC.check(case, "<p>Something else entirely.</p>")["mismatches"]) == 1


def test_04f_recorded_run_has_no_mismatch(monkeypatch):
    case = ROOT / "issues" / "WHU-OT1-04f-whu-lean-orch-t1-q1-04f"
    page = case / "draft" / "whu-lean-orch-t1-q1-04f.html"
    if not page.exists():
        pytest.skip("04f records not present")
    monkeypatch.setenv("WHU_LEAN", "1")
    assert AC.check(case, page.read_text(encoding="utf-8"))["mismatches"] == []
