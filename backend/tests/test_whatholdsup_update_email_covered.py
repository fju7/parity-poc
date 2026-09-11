"""A failed send does not mark a correction covered.

On 2026-09-11 the first correction broadcast failed. Its sent.json row carried
a three-item `covers` list and `state: "failed"`, and `update_email.covered()`
read the list without reading the state, so three corrections nobody had
received disappeared from "outstanding". Only a row closed as "sent" counts;
"sending" is a row nobody closed, "failed" is a send that did not happen, and a
row with no state is not evidence of delivery.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import update_email as U  # noqa: E402

HEADING = "9 September 2026 — an outside review, and a self-accusation that overstated what we did"


def _with_rows(monkeypatch, tmp_path, rows):
    p = tmp_path / "sent.json"
    p.write_text(json.dumps({"sends": rows}), encoding="utf-8")
    monkeypatch.setattr(U, "SENT", p)


def test_a_failed_row_does_not_cover(monkeypatch, tmp_path):
    _with_rows(monkeypatch, tmp_path,
               [{"state": "failed", "covers": [HEADING], "kind": "broadcast"}])
    assert HEADING not in U.covered()


def test_an_unclosed_row_does_not_cover(monkeypatch, tmp_path):
    _with_rows(monkeypatch, tmp_path,
               [{"state": "sending", "covers": [HEADING], "kind": "broadcast"}])
    assert HEADING not in U.covered()


def test_a_stateless_row_with_a_list_does_not_cover(monkeypatch, tmp_path):
    _with_rows(monkeypatch, tmp_path, [{"covers": [HEADING]}])
    assert HEADING not in U.covered()


def test_unknown_coverage_contributes_nothing(monkeypatch, tmp_path):
    _with_rows(monkeypatch, tmp_path, [{"state": "sent", "covers": "unknown"}])
    assert U.covered() == set()


def test_a_sent_row_covers(monkeypatch, tmp_path):
    _with_rows(monkeypatch, tmp_path,
               [{"state": "sent", "covers": [HEADING], "kind": "broadcast"}])
    assert HEADING in U.covered()


def test_the_real_record_only_covers_through_sent_rows():
    """Against the repository's own sent.json: every covered heading is
    carried by a row closed as "sent", and no failed or unclosed row
    contributes. (This test first asserted covered() == set(), which was a
    snapshot of the record on the morning of 11 September; the first
    successful send that afternoon turned it red at the pre-commit hook. A
    test of the world's state on a given day is not a test of the property.)"""
    rows = json.loads(U.SENT.read_text(encoding="utf-8")).get("sends") or []
    from_sent = set()
    for r in rows:
        if r.get("state") == "sent" and isinstance(r.get("covers"), list):
            from_sent |= {" ".join(str(x).split()) for x in r["covers"]}
    assert U.covered() == from_sent
    for r in rows:
        if r.get("state") != "sent" and isinstance(r.get("covers"), list):
            for h in r["covers"]:
                assert " ".join(str(h).split()) not in U.covered() or " ".join(str(h).split()) in from_sent
