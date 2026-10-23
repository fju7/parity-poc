"""supersede.py --ruling-for: one ruling row, by the finding it rules (2026-10-22).

WHU-S02's recency finding was ruled on the source-list line before the recency
routing fix. Superseding all of rulings.jsonl would throw away every other
ruling on the issue; `--ruling-for <finding id>` stamps and moves only the
row(s) that rule that finding, to rulings/superseded/, and the consistency
report then counts a pair that re-asked that row as superseded.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import consistency as C  # noqa: E402
import supersede as S  # noqa: E402

NOW = datetime(2026, 10, 22, 18, 5, tzinfo=timezone.utc)
FID = "f459ab0c1-rec-4"
ROWS = [
    {"id": "aaaa000000000001", "ruling_kind": "gate", "finding_id": "f459ab0c1-obj-1", "row": "r1",
     "covers": [{"finding_id": "f459ab0c1-obj-1", "row": "r1"}], "ruling": "reject", "text": None},
    {"id": "bbbb000000000002", "ruling_kind": "gate", "finding_id": FID, "row": "r2",
     "covers": [{"finding_id": FID, "row": "r2"}], "ruling": "reject", "text": None},
    {"id": "cccc000000000003", "ruling_kind": "advocate", "advocate_item": "S003-1", "ruling": "amend",
     "text": "t"},
]


def _case(tmp_path, rows=ROWS):
    case = tmp_path / "WHU-S99-xq"
    (case / "rulings").mkdir(parents=True)
    (case / "rulings" / "rulings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    pairs = [{"type": "pair", "step": "gate", "kind": "gate", "ruling_id": rid, "usable": True,
              "agree": True, "agree_decision": True} for rid in ("aaaa000000000001", "bbbb000000000002")]
    (case / "consistency.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pairs))
    return case


def _lines(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def test_only_the_row_for_the_finding_is_stamped_and_moved(tmp_path):
    case = _case(tmp_path)
    before = (case / "rulings" / "rulings.jsonl").read_text().splitlines()
    to, ids = S.supersede_ruling_for(case, FID, "ruled on the source-list line", "Claude Code", now=NOW)
    assert ids == ["bbbb000000000002"]
    assert to == "rulings/superseded/20261022T1805Z-ruling-for-f459ab0c1-rec-4-rulings.jsonl"
    moved = _lines(case / to)
    assert len(moved) == 1 and moved[0]["id"] == "bbbb000000000002"
    assert moved[0]["superseded"] == {"reason": "ruled on the source-list line", "on": "2026-10-22",
                                      "by": "Claude Code", "only": "the ruling row(s) for %s" % FID}
    after = (case / "rulings" / "rulings.jsonl").read_text().splitlines()
    assert after == [before[0], before[2]]                     # the others untouched, byte for byte
    assert "superseded" not in json.dumps(_lines(case / "rulings" / "rulings.jsonl"))
    assert FID in (case / "rulings" / "superseded" / "README.txt").read_text()


def test_the_consistency_report_counts_it_as_superseded(tmp_path):
    case = _case(tmp_path)
    log = case / "consistency.jsonl"
    assert C.report(log, case)["issue"]["pairs"] == 2
    S.supersede_ruling_for(case, FID, "r", "Claude Code", now=NOW)
    rep = C.report(log, case)
    assert rep["issue"]["pairs"] == 1                          # the current pair
    assert rep["superseded"]["rates"]["pairs"] == 1
    assert rep["not found"]["rates"]["pairs"] == 0


def test_a_row_that_also_rules_another_finding_is_refused(tmp_path):
    rows = [dict(ROWS[1], covers=[{"finding_id": FID}, {"finding_id": "f459ab0c1-obj-2"}])]
    case = _case(tmp_path, rows)
    with pytest.raises(ValueError, match="also rules f459ab0c1-obj-2"):
        S.supersede_ruling_for(case, FID, "r", "Claude Code", now=NOW)
    assert _lines(case / "rulings" / "rulings.jsonl") == rows   # nothing moved
    assert not (case / "rulings" / "superseded").exists()


def test_no_row_for_the_finding_is_refused(tmp_path):
    case = _case(tmp_path)
    with pytest.raises(ValueError, match="no ruling row"):
        S.supersede_ruling_for(case, "f459ab0c1-rec-9", "r", "Claude Code", now=NOW)
    with pytest.raises(ValueError, match="reason"):
        S.supersede_ruling_for(case, FID, " ", "Claude Code", now=NOW)
