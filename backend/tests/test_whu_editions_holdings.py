"""Recency lines are written for held sources only (advisor's ruling A on P117, 2026-11-25; lean_editions.holdings_view).

Found on orchestrator trial 1 attempt 25 (WHU-OT1-02zc): the gate's recency check judged the UNESCO GEM Report 2020
SUPERSEDED, lean rule 3b tied it to S005 and wrote 'A newer edition exists of source [5]; this page uses the edition
listed as source [5].' -- about a source the page also says it could not hold. Changecheck found the contradiction,
its ruling removed the line, and preflight then stopped on the missing line. Ruled: this breaks the holdings rule
(unheld sources are invisible to every stage); the generator reads only the holdings view.

Records: the committed folder issues/WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc/ (read only): sources.json, the gate
report's recency studies, rulings/lean_editions.jsonl.
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

import holdings as HO        # noqa: E402
import lean_editions as LE   # noqa: E402


def _sources():
    return json.loads((CASE / "sources.json").read_text())["sources"]


def _study(name_starts):
    rep = json.loads((CASE / "draft" / ("%s.html.gate.json" % SLUG)).read_text())
    return next(s for s in rep["recency"]["studies"] if (s.get("name") or "").startswith(name_starts))


def _held():
    # 02zc's holdings: the library stored S001, S003 and S004; S003 and S004 are blocked by their corrections
    return {k for k, v in HO.classify(_sources(), {"S001", "S003", "S004"}).items() if v["holding"] == HO.HELD}


def test_02zc_records_carry_the_line_about_unheld_s005():
    assert _held() == {"S001"}
    logged = [json.loads(l) for l in (CASE / "rulings" / "lean_editions.jsonl").read_text().splitlines() if l.strip()]
    assert {d["old_source"] for d in logged} == {"S003", "S004", "S005", "S006"}        # none of them held
    s5 = next(d for d in logged if d["old_source"] == "S005")
    assert s5["outcome"] == LE.DISCLOSED and s5["sentence"].startswith("A newer edition exists of source [5]")


def test_an_unheld_sources_study_is_tied_to_nothing_and_writes_no_line(tmp_path):
    study = _study("UNESCO Global Education Monitoring Report 2020")
    assert study["status"] == LE.SUPERSEDED
    srcs = _sources()
    assert LE.match(SLUG, study, srcs, {})[0] == "S005"                # the whole list: tied to unheld S005
    view = LE.holdings_view(srcs, _held())
    assert [s["id"] for s in view] == ["S001"]
    sid, how = LE.match(SLUG, study, view, {})
    assert sid is None
    d = LE.decide(SLUG, tmp_path, study, sid, view, {}, {}, matched_by=how)
    assert d["outcome"] == LE.UNTIED and d["sentence"] is None
    assert [ln["sentence"] for ln in LE.lines(tmp_path)] == [LE.count_line(1)]   # counted, never named


def test_every_02zc_recency_study_about_an_unheld_source_writes_no_line(tmp_path):
    rep = json.loads((CASE / "draft" / ("%s.html.gate.json" % SLUG)).read_text())
    view = LE.holdings_view(_sources(), _held())
    for st in rep["recency"]["studies"]:
        if st.get("status") in LE.HANDLED:
            sid, how = LE.match(SLUG, st, view, {})
            LE.decide(SLUG, tmp_path, st, sid, view, {}, {}, matched_by=how)
    assert not [ln for ln in LE.lines(tmp_path) if LE.is_code_line(ln["sentence"]) and
                not LE.COUNT_RE.match(ln["sentence"])]


def test_a_held_source_with_a_newer_edition_still_gets_its_line(tmp_path):
    study = _study("UNESCO Global Education Monitoring Report 2020")
    view = LE.holdings_view(_sources(), _held() | {"S005"})            # as if S005 were held
    sid, how = LE.match(SLUG, study, view, {})
    assert sid == "S005"
    d = LE.decide(SLUG, tmp_path, study, sid, view, {}, {}, matched_by=how)
    assert d["outcome"] == LE.DISCLOSED and d["sentence"] == LE.line_for(view, "S005")
    assert d["sentence"].startswith("A newer edition exists of ")


def test_the_gate_reads_only_the_holdings_view():
    src = (W / "ruling.py").read_text(encoding="utf-8")
    body = src[src.index("def lean_editions_gate"):src.index("def _settle_recency")]
    assert "srcs = LE.holdings_view(srcs, HO.held_ids(slug))" in body
    assert body.index("LE.holdings_view") < body.index("LE.match(")


@pytest.mark.parametrize("bad", [None, [], [{"id": "S001"}]])
def test_holdings_view_never_widens(bad):
    assert LE.holdings_view([{"id": "S002"}, "x", {"id": "S001"}], {"S001"}) == [{"id": "S001"}]
    assert LE.holdings_view(bad, set()) == []
