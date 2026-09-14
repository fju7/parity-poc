"""changecheck: a sentence the floor withholds is recorded, verbatim, with why.

Run:  cd backend && python3 -m pytest tests/whatholdsup/test_changecheck_withheld.py -q

WHY THIS EXISTS
changecheck.changed() dropped every changed sentence of 40 characters or fewer
and told nobody. On 2026-09-14 the run that cleared melanoma's "changed
sentences reviewed" STOP found 9 changed sentences, reviewed 8, and withheld
"We have now read the notice." -- the sentence stating the correction's central
claim -- while the row read "changed: 8, nothing found". The floor is now ZERO
(operator's directive, 14 September); the withheld machinery stays for any
future filter, the row records withheld sentences beside `changed` (whose
meaning, the number REVIEWED, is kept), and the verdict is ok only when
nothing was withheld -- a row that predates the field is NOT ESTABLISHED.
No model is called; the record is redirected to a temporary file.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import changecheck as C        # noqa: E402

LONG = "This is a sentence comfortably longer than the forty-character floor, with a figure of 42%."
SHORT = "We have now read the notice."
BEFORE = "<html><body><p>An unchanged opening sentence that stays exactly the same throughout.</p></body></html>"
AFTER = BEFORE.replace("</p>", "</p><p>%s</p><p>%s</p>" % (LONG, SHORT))


def test_the_floor_is_zero_and_every_changed_sentence_is_sent():
    assert C.SHORT_FLOOR == 0
    send, withheld = C.changed(BEFORE, AFTER)
    assert send == [LONG, SHORT] and withheld == []


def test_changed_returns_sent_and_withheld_with_reason(monkeypatch):
    """The machinery stays for any future filter: with a floor set, a sentence
    under it comes back in the withheld list, verbatim, with why."""
    monkeypatch.setattr(C, "SHORT_FLOOR", 40)
    send, withheld = C.changed(BEFORE, AFTER)
    assert send == [LONG]
    assert len(withheld) == 1
    assert withheld[0]["sentence"] == SHORT
    assert withheld[0]["reason"] == "under the 40-character floor (28 chars)"
    assert len(SHORT) == 28


def test_the_row_records_the_withheld_sentence_verbatim(tmp_path, monkeypatch):
    rec = tmp_path / "change-reviews.json"
    monkeypatch.setattr(C, "record_path", lambda slug: rec)
    monkeypatch.setattr(C, "SHORT_FLOOR", 40)
    send, withheld = C.changed(BEFORE, AFTER)
    C.save_review("melanoma", AFTER, "abc1234", len(send), [], withheld)
    row = json.loads(rec.read_text())["reviews"][-1]
    assert row["changed"] == 1                       # what was REVIEWED; meaning unchanged
    assert row["changed_total"] == 2
    assert row["withheld"] == [{"sentence": SHORT, "reason": "under the 40-character floor (28 chars)"}]
    assert "1 changed sentence(s) were NOT reviewed" in row["withheld_note"]


def test_a_row_with_nothing_withheld_says_so(tmp_path, monkeypatch):
    rec = tmp_path / "change-reviews.json"
    monkeypatch.setattr(C, "record_path", lambda slug: rec)
    C.save_review("melanoma", BEFORE, "abc1234", 0, [], [])
    row = json.loads(rec.read_text())["reviews"][-1]
    assert row["withheld"] == [] and row["changed_total"] == 0
    assert row["withheld_note"] == "every changed sentence was reviewed"


def test_a_row_without_the_field_is_not_established_not_ok(tmp_path, monkeypatch):
    """Rows written before 2026-09-14 carry no withheld field. They were written
    under a 40-character floor, so whether every changed sentence was reviewed
    is NOT ESTABLISHED -- and "changed sentences reviewed" may not read ok."""
    rec = tmp_path / "change-reviews.json"
    monkeypatch.setattr(C, "record_path", lambda slug: rec)
    old_row = {"sha": C.page_sha(AFTER), "against": "1b3f3a4", "changed": 8,
               "at": "2026-09-14T19:08:04+00:00", "findings": []}
    rec.write_text(json.dumps({"reviews": [old_row]}))
    rows = C.gate_rows("melanoma", AFTER)
    assert rows[0][1] == C.BAD and "not established" in rows[0][2]
    assert C.load_reviews("melanoma")["reviews"][0].get("withheld") is None   # the row itself is untouched


def test_ok_requires_nothing_withheld(tmp_path, monkeypatch):
    rec = tmp_path / "change-reviews.json"
    monkeypatch.setattr(C, "record_path", lambda slug: rec)
    base = {"sha": C.page_sha(AFTER), "against": "1b3f3a4", "changed": 8,
            "at": "2026-09-14T20:13:10+00:00", "findings": []}
    rec.write_text(json.dumps({"reviews": [dict(base, withheld=[{"sentence": SHORT, "reason": "floor"}])]}))
    rows = C.gate_rows("melanoma", AFTER)
    assert rows[0][1] == C.BAD and "NOT reviewed" in rows[0][2] and SHORT in rows[0][2]
    rec.write_text(json.dumps({"reviews": [dict(base, withheld=[])]}))
    rows = C.gate_rows("melanoma", AFTER)
    assert rows[0][1] == C.OK
