"""The assessment-summary rule runs at confirm, the step that owns the source list (P193, after WHU-OT1-04b: acquire
added the WGIII SPM after the list was frozen and the chain check stopped the run). $0, offline."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import acquire_sources as AQ  # noqa: E402

CH12 = "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_Chapter12.pdf"


def test_confirm_applies_the_rule_and_acquire_then_adds_nothing(tmp_path):
    from orch import chain as CH
    srcs = [{"id": "S001", "type": "review", "title": "Chapter 12", "url": CH12}]
    added = AQ.summaries_to_add(srcs, "2026-11-27")
    assert [e["url"] for e in added] == [AQ.AR6_SPM["wg3"][0]] and added[0]["added_by"] == AQ.ADDED_BY
    listed = srcs + added
    (tmp_path / "sources.json").write_text(json.dumps({"sources": listed}))
    fp = CH.source_list_fp(tmp_path)
    assert AQ.summaries_to_add(listed, "2026-11-27") == []                  # acquire: nothing new
    assert CH.source_list_fp(tmp_path) == fp


def test_code_confirm_calls_the_rule_before_writing_the_list():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    body = src[src.index("def code_confirm"):src.index("def registries_answered")]
    assert body.index("AQ.summaries_to_add(sources") < body.index('(ctx.case / "sources.json").write_text')


def test_04b_recorded_list_would_have_had_its_summary_at_confirm():
    case = ROOT / "issues" / "WHU-OT1-04b-whu-lean-orch-t1-q1-04b"
    if not (case / "sources.json").exists():
        return
    srcs = json.loads((case / "sources.json").read_text())["sources"]
    confirmed = [s for s in srcs if s.get("added_by") != AQ.ADDED_BY]
    got = AQ.summaries_to_add(confirmed)
    assert [e["url"] for e in got] == [s["url"] for s in srcs if s.get("added_by") == AQ.ADDED_BY]
