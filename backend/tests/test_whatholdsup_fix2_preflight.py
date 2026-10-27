"""Fix 2, step 9: the preflight rows (post-study, 2026-10-27)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import coverage_check as C                # noqa: E402
import omissions as O                     # noqa: E402
import test_whatholdsup_fix2_ruling as T  # noqa: E402

PUBLISHED_EARLY = [{"issue": T.SLUG, "action": "publish", "at": "2026-09-01T00:00:00+00:00"}]


def test_an_open_leaves_out_objection_blocks_until_the_omission_ruling_closes_it(tmp_path, monkeypatch):
    T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED)])
    [row] = O.preflight_rows(T.SLUG, [], case=tmp_path, held=T.HELD)
    assert row[0] == O.ROW and row[1] == "BLOCKED" and "S003-01" in row[2]
    T._run(tmp_path, T.Fake(T.ADD))
    [row] = O.preflight_rows(T.SLUG, [], case=tmp_path, held=T.HELD)
    assert row[1] == "ok" and "1 ADD" in row[2]


def test_a_finding_sent_to_a_person_blocks_until_a_person_closes_it(tmp_path, monkeypatch):
    adj = T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED)])
    T._run(tmp_path, T.Fake(dict(T.ADD, span="Not in the finding.", draft_text="X.")))
    assert O.preflight_rows(T.SLUG, [], case=tmp_path, held=T.HELD)[0][1] == "BLOCKED"
    t = adj.read_text().replace("OMISSION: \n", "OMISSION: not_material\n", 1).replace(
        "DID:      \n", "DID:      nothing added; decided by a person\n", 1)
    adj.write_text(t)
    assert O.preflight_rows(T.SLUG, [], case=tmp_path, held=T.HELD)[0][1] == "ok"


def test_source_text_in_the_committed_record_blocks(tmp_path, monkeypatch):
    T._case(tmp_path, monkeypatch, [])
    (tmp_path / O.RECORD).write_text(json.dumps({"omissions": [{"reason": T.OMITTED, "outcome": "ADD"}]}))
    [row] = O.preflight_rows(T.SLUG, [], case=tmp_path, held=T.HELD)
    assert row[1] == "BLOCKED" and "holds source text" in row[2]


def test_issues_published_before_adoption_are_skipped_by_name(tmp_path, monkeypatch):
    T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED)])
    [row] = O.preflight_rows(T.SLUG, PUBLISHED_EARLY, case=tmp_path, held=T.HELD)
    assert row[1] == "ok" and row[2].startswith("SKIPPED")
    rows = C.preflight_rows(T.SLUG, PUBLISHED_EARLY)
    assert [r[0] for r in rows] == [C.ROW_UNITS, C.ROW_LIST] and all(r[2].startswith("SKIPPED") for r in rows)


def test_publish_preflight_carries_the_rows_and_fails_closed():
    src = (WHU / "publish.py").read_text(encoding="utf-8")
    assert 'omissions = _sibling("omissions")' in src and 'coverage_check = _sibling("coverage_check")' in src
    assert "omissions.preflight_rows(slug, load_record())" in src
    assert "coverage_check.preflight_rows(slug, load_record())" in src
    assert "(omissions.ROW, BAD," in src and "(coverage_check.ROW_UNITS, BAD," in src
