"""The coverage step counts as a stage that received text, for "sentences rest on received text" (advisor's ruling C
on P117, 2026-11-25; lean_received.coverage_ranges, lean_reading.preflight_rows).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): the preflight row "sentences rest on received text" stopped on
the readers'-list line bound to S001@5808-5858 ("Judged not material to this question: ..."), 0% received. The code
path: orchestrator.code_coverage sends the model each open headline unit's text (model_steps.coverage_decision) and
coverage_check.declare records the decision in coverage.json under the unit's offsets, by the model; since P103
orchestrator.bind_readers_lines binds each readers'-list line to its declaration's span; lean_reading.rests_row measures
"received" with lean_received.masks, which counted the audit, the ruling calls and the advocate only. All seven
declaration lines were settled by the audit as holds_by_record_check, with no passage delivered; six passed only
because other stages happened to receive their spans.

Records: the committed folder issues/WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc/ (read only); S001's held text is read from
the local trial library (gitignored), so those tests skip elsewhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
CASE = ROOT / "issues" / "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"
SLUG = "whu-lean-orch-t1-q1-02zc"
SEVEN = ["S001@5808-5858", "S001@5859-5918", "S001@5919-6023", "S001@6024-6153", "S001@6154-6556",
         "S001@7900-8058", "S001@8059-8153"]

import lean_reading as LRD    # noqa: E402
import lean_received as LR    # noqa: E402


def test_02zc_coverage_step_sent_the_model_the_seven_declared_spans():
    decl = json.loads((CASE / "coverage.json").read_text())["declarations"]
    assert sorted(decl) == SEVEN and {d["by"] for d in decl.values()} == {"claude-sonnet-5-5"}
    assert LR.coverage_ranges(CASE, "S001") == [(5808, 5858), (5859, 5918), (5919, 6023), (6024, 6153),
                                                 (6154, 6556), (7900, 8058), (8059, 8153)]
    assert LR.coverage_ranges(CASE, "S002") == []
    assert "coverage" not in LR.STAGES                    # never counted toward a section read in full


def test_a_declaration_by_code_or_a_person_counts_as_nothing_received(tmp_path):
    (tmp_path / "coverage.json").write_text(json.dumps({"declarations": {
        "S001@0-10": {"by": "claude-sonnet-5-5"}, "S001@10-20": {"by": "code (lean: furniture)"},
        "S001@20-30": {"by": "A Person"}, "S0011@30-40": {"by": "claude-opus-5-5"}, "S001@bad": {"by": "claude-x"}}}))
    (tmp_path / "rulings").mkdir()
    (tmp_path / "rulings" / "coverage_in_scope.jsonl").write_text(json.dumps({"unit": "S001@50-60"}) + "\n")
    assert LR.coverage_ranges(tmp_path, "S001") == [(0, 10), (50, 60)]


def _row(sent, span, sid="S001"):
    return {"sentence": sent, "on_page": True, "source_id": sid, "span": span}


def test_an_ordinary_sentence_on_unreceived_text_still_stops():
    held = {"S001": "Alpha beta gamma delta. Twenty-eight studies were included. Epsilon zeta eta theta."}
    a = held["S001"].index("Twenty")
    b = a + len("Twenty-eight studies were included.")
    rows = {"k1": _row("Judged not material to this question: x.", held["S001"][a:b]),
            "k2": _row("Epsilon zeta eta theta [1].", "Epsilon zeta eta theta.")}
    cov = LR._mask(len(held["S001"]), [(a, b)])
    name, state, why = LRD.rests_row(rows, held, {"S001": cov})
    assert state == LRD.BAD and "k2 on S001@" in why and "k1" not in why
    full = LR.union({"coverage": cov, "audit": LR._mask(len(held["S001"]), [(b, len(held["S001"]))])})
    assert LRD.rests_row(rows, held, {"S001": full})[1] == LRD.OK


def test_the_preflight_union_includes_the_coverage_step():
    src = (W / "lean_reading.py").read_text(encoding="utf-8")
    assert "coverage=LR._mask(len(held[sid]), LR.coverage_ranges(case, sid))" in src


def test_02zc_rests_row_stopped_without_coverage_and_passes_with_it():
    import source_store as store
    from orch import run_env as RE
    if not store.LIB_TRIAL.exists():
        pytest.skip("the trial library is local only (gitignored)")
    snap = RE.snapshot()
    try:
        RE.use(CASE)
        import bindings as B
        import ruling as R
        held = R.held_texts(SLUG)
        if "S001" not in held:
            pytest.skip("S001's held text is not in this library")
        srcs = json.loads((CASE / "sources.json").read_text())["sources"]
        m = LR.measure(SLUG, held=held, sources=srcs, case=CASE)
        rows = B.load(SLUG).get("bindings") or {}
        entries = B.page_markup(SLUG)[2]
        before = LRD.rests_row(rows, held, {sid: LR.union(v["masks"]) for sid, v in m.items()}, entries)
        assert before[1] == LRD.BAD and "4ae79588d827c918 on S001@5808-5858: 0% received" in before[2]
        got = {r[0]: r for r in LRD.preflight_rows(SLUG)}
        assert got[LRD.ROW_RESTS][1] == LRD.OK, got[LRD.ROW_RESTS]
    finally:
        RE.restore(snap)
