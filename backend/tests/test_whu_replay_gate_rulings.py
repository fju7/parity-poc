"""Advisor's rulings on the replay gate (2026-11-26).

Ruling 1, the STOP rows the first gate run raised on 02za and 02zc:
  * 02za's "corrections not yet read" was NOT the unread-correction note: it was S007, a held PROTOCOL whose only
    amendment is "Update in 39917627" (its review), a recorded input (the recorded run's errata.json has it). The
    2026-11-07 rule already leaves "Update in" / "Republished in" out of the notices a held source must hold; the row
    blocked it on the empty notice set alone. A defect, fixed in errata.preflight_rows: such a source is accounted
    and named in its own OK row; an expression of concern still blocks.
  * a new STOP row is "unreplayable: new input" only when every source it names was not held by the recorded run
    (so no recorded reply about it exists); any other new STOP row is a FAIL (orch/replay_gate.classify).
Recorded 02za files are read from the repository; nothing is fetched or spent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
ZA = ROOT / "issues" / "WHU-OT1-02za-whu-lean-orch-t1-q1-02za"


def _errata_rows(monkeypatch, srcs, checked):
    import errata as E
    monkeypatch.setattr(E.store, "sources", lambda slug: srcs)
    monkeypatch.setattr(E.store, "held", lambda slug: {s["id"]: {} for s in srcs
                                                        if not (s.get("access") or {}).get("not_held")})
    monkeypatch.setattr(E, "load", lambda slug: {"checked": checked})
    return {r[0]: r for r in E.preflight_rows("x")}


def test_02zas_held_protocol_with_only_an_update_needs_no_correction_read(monkeypatch):
    checked = json.loads((ZA / "errata.json").read_text(encoding="utf-8"))["checked"]
    assert [(a["type"], a["id"]) for a in checked["S007"]["amendments"]] == [("Update in", "39917627")]
    s7 = next(s for s in json.loads((ZA / "sources.json").read_text(encoding="utf-8"))["sources"] if s["id"] == "S007")
    assert s7["title"].startswith("PROTOCOL:") and s7["access"]["state"] == "full_text_held"
    rows = _errata_rows(monkeypatch, [s7], {"S007": checked["S007"]})
    assert "corrections not yet read" not in rows
    r = rows["amendments with no correction to read"]
    assert r[1] == "ok" and "S007: Update in 39917627" in r[2]
    assert "corrections obtained and read" not in rows               # nothing was read; it is not reported as read


@pytest.mark.parametrize("kinds", [["Expression of concern in"], ["Update in", "Expression of concern in"],
                                   ["Update in", "Erratum in"]])
def test_a_concern_or_a_correction_beside_an_update_still_blocks(monkeypatch, kinds):
    src = {"id": "S007", "title": "T", "access": {"state": "full_text_held"}}
    checked = {"S007": {"state": "AMENDED", "amendments": [{"type": k, "id": str(i)} for i, k in enumerate(kinds)]}}
    rows = _errata_rows(monkeypatch, [src], checked)
    assert rows["corrections not yet read"][1] == "BLOCKED"
    assert "amendments with no correction to read" not in rows


def test_a_republication_alone_needs_no_correction_read(monkeypatch):
    src = {"id": "S001", "title": "T", "access": {"state": "full_text_held"}}
    rows = _errata_rows(monkeypatch, [src], {"S001": {"state": "AMENDED",
                                                       "amendments": [{"type": "Republished in", "id": "5"}]}})
    assert rows["amendments with no correction to read"][1] == "ok" and "corrections not yet read" not in rows


# --- the gate's classification of a new STOP row ------------------------------------------------------------------

from orch import replay_gate as RG  # noqa: E402

ROW_02ZA = ("STOP headline conclusions accounted for 7 with no state in S003: use, add or declare each (e.g. "
            "S003@4325-4537, abstract main results). 28 unit(s) in 2 relied-on source(s): 14 used, 7 not_material.")


def _replay_case(tmp_path, held_now):
    """02za's recorded sources.json, with HELD_NOW held as the replay holds them under ruling 5."""
    doc = json.loads((ZA / "sources.json").read_text(encoding="utf-8"))
    for s in doc["sources"]:
        if s["id"] in held_now:
            s["access"] = {"state": "full_text_held"}
    c = tmp_path / "replay_case"
    c.mkdir()
    (c / "sources.json").write_text(json.dumps(doc))
    return c


def test_02zas_held_now_sources_are_the_new_inputs_with_the_reason(tmp_path):
    got = RG.new_inputs(ZA, _replay_case(tmp_path, {"S003", "S004"}))
    assert set(got) == {"S003", "S004"}
    assert "correction_unread" in got["S003"] and "ruling 5" in got["S003"] and "no recorded reply" in got["S003"]
    assert "correction_not_held" in got["S004"]


def test_a_headline_row_naming_only_new_inputs_is_unreplayable(tmp_path):
    inputs = RG.new_inputs(ZA, _replay_case(tmp_path, {"S003", "S004"}))
    r = RG.classify(RG._key(ROW_02ZA), ROW_02ZA, inputs)
    assert r["class"] == RG.UNREPLAYABLE and r["inputs"] == ["S003"] and "correction_unread" in r["why"]


def test_a_headline_row_naming_a_recorded_source_fails(tmp_path):
    inputs = RG.new_inputs(ZA, _replay_case(tmp_path, {"S003"}))
    text = ROW_02ZA.replace("in S003:", "in S001, S003:")
    r = RG.classify(RG._key(text), text, inputs)
    assert r["class"] == "FAIL" and "S001" in r["why"]


def test_a_row_that_does_not_name_all_its_sources_is_never_unreplayable(tmp_path):
    inputs = RG.new_inputs(ZA, _replay_case(tmp_path, {"S003", "S004"}))
    row = ("STOP corrections not yet read 1 source(s) have been formally corrected and we do not hold the correction: "
           "S003: Erratum in 36913230")
    assert RG.classify(RG._key(row), row, inputs)["class"] == "FAIL"


def test_the_gate_passes_a_run_whose_only_new_rows_are_unreplayable_and_lists_them(tmp_path):
    inputs = RG.new_inputs(ZA, _replay_case(tmp_path, {"S003"}))
    rep = {"result": "Not Ready", "steps": [{"step": "archive"}], "_stops": {RG._key(ROW_02ZA)},
           "_stop_text": {RG._key(ROW_02ZA): ROW_02ZA}, "_new_inputs": inputs}
    v, why = RG.judge({"last": "audit", "stops": set()}, rep, 0)
    assert v == "PASS" and RG.UNREPLAYABLE in why and rep["_classified"][0]["class"] == RG.UNREPLAYABLE
    rep["_stops"] = {RG._key(ROW_02ZA), "corrections not yet"}
    v, why = RG.judge({"last": "audit", "stops": set()}, rep, 0)
    assert v == "FAIL" and "corrections not yet" in why


def test_the_headline_row_names_every_source_with_an_open_unit():
    src = (W / "coverage_check.py").read_text(encoding="utf-8")
    assert 'with no state in %s' in src and 'sorted({u["source"] for u in none})' in src
