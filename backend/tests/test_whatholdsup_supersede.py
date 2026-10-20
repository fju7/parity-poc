"""supersede.py stamps a study issue's records and moves them aside (2026-10-20).

What WHU-P02's clean re-run did by hand: every record stamped
"superseded": {reason, on, by}, the files moved to rulings/superseded/ and
advocate/superseded/ under a UTC-stamp prefix, nothing deleted.
"""
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("supersede_t", WHU / "supersede.py")
SU = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SU)

BY = "Claude Code (session test)"
NOW = datetime(2026, 10, 21, 1, 2, tzinfo=timezone.utc)


@pytest.fixture
def case(tmp_path):
    (tmp_path / "rulings").mkdir()
    (tmp_path / "advocate").mkdir()
    (tmp_path / "rulings" / "rulings.jsonl").write_text('{"ruling": "accept"}\n{"ruling": "reject"}\n')
    (tmp_path / "rulings" / "applied_check.jsonl").write_text('{"checked": 3}\n')
    (tmp_path / "gate-findings.json").write_text(json.dumps({"findings": [{"id": "c1"}]}))
    (tmp_path / "change-reviews.json").write_text(json.dumps({"reviews": []}))
    (tmp_path / "advocate" / "2026-10-20-briefs.json").write_text(json.dumps([{"source": "S1"}]))
    (tmp_path / "advocate" / "2026-10-20-adjudication.md").write_text("# demo\n")
    (tmp_path / "audit").mkdir()
    (tmp_path / "audit" / "keep.txt").write_text("x")
    return tmp_path


def test_every_record_is_stamped_and_moved_and_nothing_is_lost(case):
    moved = SU.supersede(case, "made before ruling payloads carried context", BY, now=NOW)
    mark = {"reason": "made before ruling payloads carried context", "on": "2026-10-21", "by": BY}
    assert dict(moved) == {
        "rulings/rulings.jsonl": "rulings/superseded/20261021T0102Z-rulings.jsonl",
        "rulings/applied_check.jsonl": "rulings/superseded/20261021T0102Z-applied_check.jsonl",
        "change-reviews.json": "rulings/superseded/20261021T0102Z-change-reviews.json",
        "gate-findings.json": "rulings/superseded/20261021T0102Z-gate-findings.json",
        "advocate/2026-10-20-briefs.json": "advocate/superseded/20261021T0102Z-2026-10-20-briefs.json",
        "advocate/2026-10-20-adjudication.md": "advocate/superseded/20261021T0102Z-2026-10-20-adjudication.md"}
    for frm, _to in moved:
        assert not (case / frm).exists()                       # no current tool can read it
    rs = [json.loads(l) for l in (case / "rulings/superseded/20261021T0102Z-rulings.jsonl").read_text().splitlines()]
    assert [r["ruling"] for r in rs] == ["accept", "reject"] and all(r["superseded"] == mark for r in rs)
    g = json.loads((case / "rulings/superseded/20261021T0102Z-gate-findings.json").read_text())
    assert g["superseded"] == mark and g["findings"] == [{"id": "c1"}]
    b = json.loads((case / "advocate/superseded/20261021T0102Z-2026-10-20-briefs.json").read_text())
    assert b == [{"source": "S1", "superseded": mark}]
    md = (case / "advocate/superseded/20261021T0102Z-2026-10-20-adjudication.md").read_text()
    assert md.startswith("SUPERSEDED on 2026-10-21 by %s: made before" % BY) and md.endswith("# demo\n")
    assert "20261021T0102Z" in (case / "rulings/superseded/README.txt").read_text()
    assert (case / "audit" / "keep.txt").exists()              # audit runs are withdrawn, not superseded


def test_only_limits_the_records(case):
    moved = SU.supersede(case, "r", BY, only=["gate-findings"], now=NOW)
    assert [m[0] for m in moved] == ["gate-findings.json"]
    assert (case / "rulings" / "rulings.jsonl").exists()
    with pytest.raises(ValueError):
        SU.supersede(case, "r", BY, only=["nonsense"], now=NOW)


def test_a_reason_is_required_and_nothing_is_overwritten(case):
    with pytest.raises(ValueError):
        SU.supersede(case, "  ", BY, now=NOW)
    SU.supersede(case, "r", BY, only=["gate-findings"], now=NOW)
    (case / "gate-findings.json").write_text("{}")
    with pytest.raises(SystemExit):
        SU.supersede(case, "r", BY, only=["gate-findings"], now=NOW)
    assert (case / "gate-findings.json").exists()             # left in place, not lost


def test_a_persons_name_needs_a_signature():
    SU.check_by(BY, None)
    with pytest.raises(SystemExit) as e:
        SU.check_by("Fred Ugast", None)
    assert "--signature" in str(e.value)


def test_a_published_issue_is_refused(monkeypatch):
    import publish
    monkeypatch.setattr(publish, "is_study", lambda slug: False)
    with pytest.raises(SystemExit) as e:
        SU.main(["melanoma", "--reason", "r", "--by", BY])
    assert "not a study issue" in str(e.value)
