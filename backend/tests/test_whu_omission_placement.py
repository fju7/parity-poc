"""An omission ADD goes only after a body sentence (advisor's ruling 2 on P169). $0, offline.

WHU-OT1-01d stopped at omissions: S003-16's ADD was anchored to the code-written fail-safe sentence "We could not
verify where this belief is published." in the limits block, which Page.insert_after cannot place after.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
CASE = ROOT / "issues" / "WHU-OT1-01d-whu-lean-orch-t1-q1-01d"
UNVERIFIED = "We could not verify where this belief is published."


@pytest.fixture(autouse=True)
def _lean(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")


def _01d():
    if not (CASE / "draft" / "page.json").exists():
        pytest.skip("01d records not present")
    from orch.page import Page
    page = Page.load(CASE / "draft" / "page.json")
    rows = json.loads((CASE / "bindings.json").read_text(encoding="utf-8"))["bindings"]
    return page, page.sentences(), rows


def test_01d_code_written_anchor_goes_after_last_body_sentence_bound_to_its_source():
    import audit_stage as A
    import bindings as B
    import placement as PL
    page, sents, rows = _01d()
    body = PL.body_set(CASE, sents)
    assert UNVERIFIED in sents and UNVERIFIED not in body
    i = sents.index(UNVERIFIED)
    after, how = PL.place(i, sents, rows, body, "S003")
    assert after in body and how.startswith(PL.CODE_WRITTEN_ANCHOR)
    row = rows[B.fingerprint(after)]
    assert row["on_page"] and "S003" in A.sources_of(row)
    # the last such sentence in page order
    later = [s for s in sents[sents.index(after) + 1:] if s in body
             and "S003" in A.sources_of(rows.get(B.fingerprint(s)) or {})
             and (rows.get(B.fingerprint(s)) or {}).get("on_page")]
    assert later == []
    page.insert_after(B.fingerprint(after), "A test sentence.")      # the applier can place it


def test_01d_recorded_anchor_was_not_placeable_by_the_applier():
    import bindings as B
    from orch.page import NotPlaced
    page, _sents, _rows = _01d()
    with pytest.raises(NotPlaced):
        page.insert_after(B.fingerprint(UNVERIFIED), "A test sentence.")


def test_code_written_anchor_with_no_bound_body_sentence_has_no_place():
    import placement as PL
    page, sents, rows = _01d()
    body = PL.body_set(CASE, sents)
    after, how = PL.place(sents.index(UNVERIFIED), sents, rows, body, "S999")
    assert after is None and how.startswith(PL.CODE_WRITTEN_ANCHOR)
    import ruling as R
    # rule_omissions sends "no place for the ADD: <how>" -- under lean, code's NOT_ADDED_NO_PLACE readers' line
    assert ("%s: %s" % (R.NO_PLACE_WHY, how)).startswith(R.NO_PLACE_WHY)


def test_body_anchor_unchanged():
    import placement as PL
    page, sents, rows = _01d()
    body = PL.body_set(CASE, sents)
    k = next(j for j, s in enumerate(sents) if s in body
             and PL.place(j, sents, rows, body, "S003")[1] == "after the anchor")
    assert PL.place(k, sents, rows, body, "S003")[0] == sents[k]


def test_body_without_page_json_excludes_code_written_lines(tmp_path):
    import placement as PL
    sents = ["Reminders may increase attendance [1].", UNVERIFIED,
             "We hold the full text of A review [1].",
             "Outside this question: “x” (A review [1]) (found in our sources)."]
    body = PL.body_set(tmp_path, sents)
    assert body == {"Reminders may increase attendance [1]."}
    after, how = PL.place(1, sents, {}, body, "S001")
    assert after is None and how.startswith(PL.CODE_WRITTEN_ANCHOR)


def test_ruling_placement_passes_body_and_source():
    import ruling as R
    page, sents, rows = _01d()
    import placement as PL
    body = PL.body_set(CASE, sents)
    after, how = R._placement(UNVERIFIED, sents, rows, body, "S003")
    assert after in body
    # without BODY every sentence counts (the old rule) -- kept for callers that pass none
    assert R._placement(UNVERIFIED, sents, rows)[0] == UNVERIFIED


def test_sweep_every_recorded_add_anchor_outside_the_body_is_01d_only():
    import placement as PL
    got = PL.sweep()
    assert got["by_class"]["unresolved"] == 0
    assert [(r["case"], r["key"]) for r in got["outside_body"]] == \
        [("WHU-OT1-01d-whu-lean-orch-t1-q1-01d", "S003@7094-7240")]
