"""Advisor's ruling 4 on P140 (2026-11-26): coverage runs after premise_reading (and judgements), so a source first
named at premise reading -- 02za's S003, 02zc's S004 in the first replay gate -- has its headline units decided.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

from orch import steps as ST  # noqa: E402


def test_coverage_runs_after_every_step_that_can_make_a_source_relied_on_and_before_the_first_draft_commit():
    names = [s.name for s in ST.STEPS]
    cov = names.index("coverage")
    assert cov > names.index("premise_reading") and cov > names.index("judgements") and cov > names.index("draft")
    assert cov < names.index("commit_3b")


def test_a_source_first_named_at_premise_reading_is_relied_on_for_coverage(tmp_path, monkeypatch):
    """coverage_check.relied_on counts a source named in what_the_sources_show (premise_reading writes it) even with
    no bound row, so coverage, now after premise_reading, puts its units to the model."""
    import coverage_check as C
    srcs = [{"id": "S001"}, {"id": "S003"}]
    rows = {"a": {"source_id": "S001", "on_page": True}, "b": {"source_id": "S001", "on_page": True},
            "c": {"source_id": "S001", "on_page": True}}
    assert C.relied_on("x", rows, {}, sources=srcs) == ["S001"]
    assert C.relied_on("x", rows, {"what_the_sources_show": {"sources": ["S003"]}}, sources=srcs) == ["S003", "S001"]
