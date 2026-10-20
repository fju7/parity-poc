"""findings.check(): a skeleton row is not a decision.

Run:  cd backend && python3 -m pytest tests/whatholdsup/test_findings_skeleton_not_settled.py -q

WHY THIS EXISTS
On 2026-09-15 `findings.py deskilling --scan` wrote forty skeleton rows, every
one with decision "". The board's first row changed from

    STOP  gate findings settled   40 finding(s) ... have no decision
to
    ok    gate findings settled   40 open finding(s), each with a decision

because `missing` was computed as "no row at all" (`if not r`), so a row that
existed left `missing` and fell through to `unsettled` one row down. The
publish stayed BLOCKED -- nothing reached a reader -- but the board asserted
something false in the direction of reassurance.

The underlying defect was that `unsettled` did two jobs: "no valid decision
word" and "decided but not evidenced". Those are an editorial gap and an
evidence gap, and only the second belongs under "settled by a document".

COUNTERFACTUAL. Each test below is red under exactly one single-condition
mutation of findings.check(), and each mutation kills exactly one test. The
matrix was run, not reasoned -- an earlier version of this docstring claimed
the first two tests both guarded row 1's state, and the second does not: it
passes under `blocked = missing` and guards the WORDING of the split instead.

    blocked = missing              (drop undecided)   -> test 1 red
    blocked = undecided            (drop missing)     -> test 4 red
    one undifferentiated count     (merge the bits)   -> test 2 red
    unevidenced routed into row 1  (wrong bucket)     -> test 3 red

Test 4 exists because the first three all PASS under `blocked = undecided`.
That mutation is the symmetric form of the defect this file was written for:
a record from an earlier run plus a report that has since gained findings
gives undecided == [] and missing == [new ids], and row 1 would read ok while
findings nobody ever recorded sat unblocked.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import findings as F        # noqa: E402

SLUG = "deskilling"
REPORT = {
    "claims": [{"id": "c1", "claim": "one"}, {"id": "c2", "claim": "two"}],
    "verdicts": {"c1": {"verdict": "NOT_FOUND", "found_value": "a"},
                 "c2": {"verdict": "NOT_FOUND", "found_value": "b"}},
}


@pytest.fixture
def rec(tmp_path, monkeypatch):
    """The record is redirected to a temp file; no issue record is touched.
    attestation_for is stubbed: it is orthogonal to what these tests check,
    and stubbing it keeps them independent of any issue's source ledger."""
    p = tmp_path / "gate-findings.json"
    monkeypatch.setattr(F, "path", lambda slug: p)
    monkeypatch.setattr(F, "attestation_for", lambda slug, claim: None)
    return p


def test_skeleton_rows_do_not_read_as_settled(rec):
    F.scan(SLUG, REPORT)
    doc = json.loads(rec.read_text(encoding="utf-8"))
    assert [f["id"] for f in doc["findings"]] == ["c1", "c2"]
    assert all(f["decision"] == "" for f in doc["findings"])

    label, state, detail = F.check(SLUG, REPORT)[0]
    assert label == "gate findings settled"
    assert state == F.BAD, "skeleton rows read as settled: %r" % detail
    assert "c1" in detail and "c2" in detail


def test_missing_and_undecided_are_reported_apart(rec):
    F.scan(SLUG, REPORT)
    doc = json.loads(rec.read_text(encoding="utf-8"))
    doc["findings"] = [f for f in doc["findings"] if f["id"] != "c2"]
    rec.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    label, state, detail = F.check(SLUG, REPORT)[0]
    assert state == F.BAD
    assert "never recorded" in detail and "c2" in detail, detail
    assert "no decision yet" in detail and "c1" in detail, detail


def test_decided_but_unevidenced_still_stops_the_document_row(rec):
    F.scan(SLUG, REPORT)
    doc = json.loads(rec.read_text(encoding="utf-8"))
    for f in doc["findings"]:
        f["decision"] = "accepted"          # decided, but names no source
    rec.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    rows = {r[0]: r for r in F.check(SLUG, REPORT)}
    assert rows["gate findings settled"][1] == F.OK
    doc_row = rows["findings settled by a document"]
    assert doc_row[1] == F.BAD
    assert "must name a source" in doc_row[2], doc_row[2]


def test_an_unrecorded_finding_alone_still_stops_row_one(rec):
    """`undecided` is EMPTY here: the only recorded row is properly closed as
    a judgement. c2 was never recorded at all. Row 1 must still STOP -- this
    is what `blocked = undecided` would silently let through."""
    F.scan(SLUG, REPORT)
    doc = json.loads(rec.read_text(encoding="utf-8"))
    doc["findings"] = [f for f in doc["findings"] if f["id"] == "c1"]
    doc["findings"][0].update({"decision": "judgement",
                               "why": "closed on the record, no document",
                               "by": "claude"})
    rec.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    label, state, detail = F.check(SLUG, REPORT)[0]
    assert state == F.BAD, (
        "an unrecorded finding alone did not stop row 1: %r" % detail)
    assert "c2" in detail, detail
