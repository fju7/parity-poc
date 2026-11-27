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


def test_01d_live_when_its_library_is_here():
    """Run in its own process under the run's recorded environment (orch/run_env.py): inside the suite the library
    root may already be resolved by an earlier import."""
    import subprocess
    if not (ROOT / "backend" / "data" / "whatholdsup" / "library_trial").exists():
        pytest.skip("trial library not present (local only)")
    py = str(ROOT / "backend" / "venv" / "bin" / "python3")
    if not Path(py).exists():
        py = sys.executable
    w = ROOT / "backend" / "scripts" / "whatholdsup"
    out = subprocess.run([py, str(w / "orch" / "run_env.py"), "whu-lean-orch-t1-q1-01d", "--", py,
                          str(w / "figure_sweep.py"), "whu-lean-orch-t1-q1-01d"],
                         capture_output=True, text=True, cwd=str(ROOT), timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    got = json.loads([l for l in out.stdout.splitlines() if l.startswith('{"slug"')][-1])
    assert got["by_class"] == {"in_cited_source": 9}
    assert {r["row"] for r in got["rows"]} == {"1ff00044", "0ed7804d", "21e91962"}


def test_a_cited_source_with_no_held_text_fails(monkeypatch):
    import figure_sweep as FS
    import bindings as B
    import ruling as R
    rows = {"ab12cd34ef567890": {"on_page": True, "source_id": "S001", "sentence": "RR 0.92 [1]."}}
    monkeypatch.setattr(B, "load", lambda slug: {"bindings": rows})
    monkeypatch.setattr(B, "rule_rows", lambda slug: [("rule 1", "BLOCKED",
                                                       "ab12cd34: 0.92 in no span it is bound to (RR)")])
    monkeypatch.setattr(R, "held_texts", lambda slug: {})
    with pytest.raises(FS.CannotSee):
        FS.sweep_case("x")
