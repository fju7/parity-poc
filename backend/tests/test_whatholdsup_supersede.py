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


# --- a superseded adjudication file is replaced by a blank template (2026-10-21) --

BRIEFS = [{"source": "S1", "title": "T", "principal": "p", "state": "machine-readable", "mode": "objections",
           "objections": [{"severity": "SERIOUS", "claim_quoted": "a", "objection": "o1", "why": "w"},
                          {"severity": "MINOR", "claim_quoted": "b", "objection": "o2", "why": "w"}]}]


@pytest.fixture
def adv_case(case, monkeypatch):
    import source_advocate as SA
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: case)
    (case / "advocate" / "2026-10-20-briefs.json").write_text(json.dumps(BRIEFS))
    SA.write_template("demo", "2026-10-20", BRIEFS)
    adj = case / "advocate" / "2026-10-20-adjudication.md"
    adj.write_text(adj.read_text().replace("MERIT:  \n", "MERIT:  no — ruled\n", 1)
                   .replace("EFFECT: \n", "EFFECT: none\n", 1))            # one item closed
    return case, SA


def test_superseding_the_adjudication_leaves_a_blank_template_the_ruling_model_finds(adv_case):
    case, SA = adv_case
    import ruling as R
    assert [i["head"] for i in R.advocate_items("demo", case)] == ["S1-02"]
    written = []
    moved = SU.supersede(case, "re-ruled grouped by sentence (GAP-019)", BY, only=["advocate-adjudication"],
                         now=NOW, slug="demo", templates=written)
    assert moved == [("advocate/2026-10-20-adjudication.md",
                      "advocate/superseded/20261021T0102Z-2026-10-20-adjudication.md")]
    assert written == ["advocate/2026-10-20-adjudication.md"]
    fresh = (case / "advocate" / "2026-10-20-adjudication.md").read_text()
    assert fresh.startswith("# demo — source advocate, 2026-10-20\n")    # the old heading's day
    assert "MERIT:  no" not in fresh and "SUPERSEDED" not in fresh
    assert [i["head"] for i in R.advocate_items("demo", case)] == ["S1-01", "S1-02"]   # every item open again
    old = (case / "advocate/superseded/20261021T0102Z-2026-10-20-adjudication.md").read_text()
    assert old.startswith("SUPERSEDED on 2026-10-21") and "MERIT:  no — ruled" in old   # nothing lost
    assert (case / "advocate" / "2026-10-20-briefs.json").exists()


def test_no_template_when_the_briefs_are_superseded_too(adv_case):
    case, SA = adv_case
    written = []
    SU.supersede(case, "r", BY, only=["advocate-briefs", "advocate-adjudication"], now=NOW, slug="demo",
                 templates=written)
    assert written == [] and not list((case / "advocate").glob("*-adjudication.md"))


def test_without_a_slug_no_template_is_written(adv_case):
    case, SA = adv_case
    SU.supersede(case, "r", BY, only=["advocate-adjudication"], now=NOW)
    assert not (case / "advocate" / "2026-10-20-adjudication.md").exists()


def test_a_template_is_never_written_into_another_issues_folder(adv_case, monkeypatch, tmp_path):
    case, SA = adv_case
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: tmp_path / "elsewhere")
    with pytest.raises(SystemExit):
        SU.supersede(case, "r", BY, only=["advocate-adjudication"], now=NOW, slug="demo")


def test_main_passes_the_slug(monkeypatch, case):
    import publish, source_store
    seen = {}
    monkeypatch.setattr(publish, "is_study", lambda slug: True)
    monkeypatch.setattr(source_store, "case_dir", lambda slug: case)
    monkeypatch.setattr(SU, "supersede", lambda *a, **k: seen.update(k) or [])
    SU.main(["demo", "--reason", "r", "--by", BY])
    assert seen["slug"] == "demo"
