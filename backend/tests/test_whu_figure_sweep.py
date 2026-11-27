"""The $0 sweep of figures in no bound span (advisor's ruling 4 on P169). Rule 1 itself is not touched."""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))


def test_a_figure_is_matched_as_a_whole_number():
    import figure_sweep as FS
    assert FS._has("0.92", "RR 0.92, 95% CI")
    assert not FS._has("0.92", "RR 10.92")
    assert not FS._has("0.92", "RR 0.925")


def test_recorded_result_has_no_unsupported_figure():
    rec = json.loads((ROOT / "study/whu-reliability/next_phase/results/figure_sweep_p169.json").read_text())
    assert rec["errors"] == 0 and rec["cases_swept"] == 55
    assert rec["by_class"] == {"in_cited_source": 11, "in_other_source_only": 0, "in_no_held_source": 0}
    assert sorted({r["slug"] for r in rec["rows"]}) == ["whu-lean-orch-t1-q1-01d", "whu-lean-orch-t1-q1-02z"]


def test_01d_live_when_its_library_is_here(monkeypatch):
    lib = ROOT / "backend" / "data" / "whatholdsup" / "library_trial"
    if not lib.exists():
        pytest.skip("trial library not present (local only)")
    monkeypatch.setenv("WHU_LEAN", "1")
    monkeypatch.setenv("WHU_LIBRARY_ROOT", str(lib))
    import figure_sweep as FS
    got = FS.sweep_case("whu-lean-orch-t1-q1-01d")
    assert got["by_class"] == {"in_cited_source": 9}
    assert {r["row"] for r in got["rows"]} == {"1ff00044", "0ed7804d", "21e91962"}
