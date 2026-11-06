"""The patch ledger (study/whu-reliability/next_phase/patch_ledger.py) and its non-impact check. Offline."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NP = ROOT / "study" / "whu-reliability" / "next_phase"


def _mod(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


PL = _mod("patch_ledger", NP / "patch_ledger.py")
NI = _mod("scored_pages_preflight", NP / "nonimpact" / "scored_pages_preflight.py")

DEV = """| Date | What | Why | When |
|---|---|---|---|
| 2026-11-05 | **An old row.** text | x | y |
| 2026-11-06 | **Advisor: the lean four-question test is CLOSED as reported; the report is FINAL.** t | x | y |
| 2026-11-07 | **A new patch.** t | x | y |
"""


def _entry(**kw):
    e = {"id": "P001", "deviation": "Advisor: the lean four-question test is CLOSED", "date": "2026-11-06",
         "kind": "patch", "trigger": "ruling", "timing": "after data seen", "components": ["deviations.md"],
         "data_exposure": "all results", "decision_rule_change": False, "non_impact_check": {"none": "records only"}}
    e.update(kw)
    return e


def test_every_phase_row_needs_an_entry_and_legacy_rows_do_not():
    res = PL.validate(DEV, [_entry()])
    assert res["legacy_rows"] == 1 and res["phase_rows"] == 2
    assert res["problems"] == ["deviations row 2026-11-07 'A new patch.' has no patch entry"]
    res = PL.validate(DEV, [_entry(), _entry(id="P002", deviation="A new patch.", date="2026-11-07")])
    assert res["problems"] == []


def test_fields_are_fixed():
    bad = _entry(timing="soon", decision_rule_change="no", components=[], non_impact_check={"script": "x.py"})
    probs = PL.problems_of(bad)
    assert any("timing" in p for p in probs) and any("decision_rule_change" in p for p in probs)
    assert any("components" in p for p in probs) and any("non_impact_check" in p for p in probs)
    assert PL.problems_of({"id": "P001"})[0].startswith("missing field")


def test_a_check_is_rerun_and_compared_by_hash(tmp_path, monkeypatch):
    script = tmp_path / "chk.py"
    script.write_text("print('stable output')\n")
    monkeypatch.setattr(PL, "HERE", tmp_path)
    want = hashlib.sha256(b"stable output\n").hexdigest()
    e = _entry(non_impact_check={"script": "chk.py", "args": [], "expected_sha256": want})
    assert PL.run_check(e)["matches"] is True
    e["non_impact_check"]["expected_sha256"] = "0" * 64
    assert PL.run_check(e)["matches"] is False


def test_the_committed_ledger_is_valid():
    res = PL.validate(PL.DEVIATIONS.read_text(encoding="utf-8"), PL.load())
    assert res["problems"] == [], res["problems"]


def test_scored_pages_check_reports_identity_by_hash():
    slug = "whu-lean-q1-01c"
    assert NI.line(slug, "anything") == "%s DIFFERS" % slug
    stored = NI.STORED[slug]
    assert len(stored) == 64 and all(c in "0123456789abcdef" for c in stored)
    expected = hashlib.sha256("".join("%s identical\n" % s for s in NI.STORED).encode()).hexdigest()
    ledger = {e["id"]: e for e in PL.load()}
    checks = [e for e in ledger.values() if e["non_impact_check"].get("script") == "nonimpact/scored_pages_preflight.py"]
    assert checks and all(e["non_impact_check"]["expected_sha256"] == expected for e in checks)
