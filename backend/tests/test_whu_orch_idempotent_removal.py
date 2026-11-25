"""Advisor's rulings after orchestrator trial 1 attempt 24's second fresh run (2026-11-25, P100).

Attempt 24's second fresh run (WHU-OT1-02z) stopped at `overstatement`: "a ruling could not be placed by code: not
found on the page: 'A systematic review of 28 studies concludes ...'". The overstatement check reads a sentence
against each passage it is bound to; three sentences were judged "yes" on two passages each, so the lean fail-safe
wrote two removal rows per sentence, and orch/apply.apply_all deleted the sentence on the first and could not find it
on the second.

  (1) When several findings remove the same sentence, it is removed once and every finding is recorded against
      that removal. Applying rulings is idempotent: a removal of a sentence already removed earlier in the same run
      is recorded, not an error; a removal of a sentence never on the page remains an error.

The fixture is this run's own records (backend/tests/fixtures/whu_orch_02z/): the saved page (the step raised
before saving, so it is the page the overstatement apply started from), the fail-safe log, and the applied log as it
stood before the overstatement step (the one removal the failed apply marked is left out).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
FIX = ROOT / "backend" / "tests" / "fixtures" / "whu_orch_02z"

from orch import apply as AP                 # noqa: E402
from orch.page import Page, NotPlaced, norm, fingerprint  # noqa: E402

FIRST = "A systematic review of 28 studies concludes"
STALE = "9fc13686538d780b"     # the old text of a sentence advocate ruling rulings.jsonl:10 had rewritten


def _case(tmp_path: Path, stale: bool = False) -> tuple[Path, Page]:
    """The run's records; without STALE's two rows unless STALE (they name a sentence no longer on the page)."""
    c = tmp_path / "case"
    (c / "rulings").mkdir(parents=True)
    (c / "orchestrator").mkdir()
    (c / "draft").mkdir()
    rows = [l for l in (FIX / "lean_removed.jsonl").read_text().splitlines()
            if l.strip() and (stale or json.loads(l)["fingerprint"] != STALE)]
    (c / "rulings" / "lean_removed.jsonl").write_text("\n".join(rows) + "\n")
    shutil.copy(FIX / "applied_before_overstatement.jsonl", c / "orchestrator" / "applied.jsonl")
    shutil.copy(FIX / "page.json", c / "draft" / "page.json")
    return c, Page.load(c / "draft" / "page.json")


def _rows():
    return [json.loads(l) for l in (FIX / "lean_removed.jsonl").read_text().splitlines() if l.strip()]


def _applied(c: Path) -> list[dict]:
    return [json.loads(l) for l in (c / "orchestrator" / "applied.jsonl").read_text().splitlines() if l.strip()]


def test_the_fixture_is_what_attempt_24s_second_run_met():
    rows = [r for r in _rows() if r["path"] == "overstatement"]
    fps = [r["fingerprint"] for r in rows]
    assert len(rows) == 8 and len(set(fps)) == 5
    assert sorted(fp for fp in set(fps) if fps.count(fp) == 2) == ["3be2742c7ee7bf5c", "93fd1341d10cd6a8",
                                                                   "9fc13686538d780b"]
    page = Page.load(FIX / "page.json")
    on = {fingerprint(s) for s in page.sentences()}
    assert set(fps) - on == {STALE}                           # one named sentence had been rewritten already
    replaced = [json.loads(l) for l in (FIX / "applied_before_overstatement.jsonl").read_text().splitlines()
                if json.loads(l)["key"] == "ruling:rulings/rulings.jsonl:10"]
    assert len(replaced) == 1 and fingerprint(replaced[0]["old"]) == STALE and replaced[0]["new"]
    assert not any(l.startswith('{"key": "failsafe:') for l in (FIX / "applied_before_overstatement.jsonl")
                   .read_text().splitlines())


def test_the_old_applier_reproduces_the_stop(tmp_path):
    """What attempt 24's second run did: every pending removal applied as a delete, no matter what came before."""
    c, page = _case(tmp_path, stale=True)
    with pytest.raises(NotPlaced) as e:
        for _key, _at, op in AP.pending(c):
            page.delete(op["old"])
    assert "not found on the page" in str(e.value) and FIRST in str(e.value)


def test_several_findings_remove_a_sentence_once_and_every_finding_is_recorded(tmp_path):
    c, page = _case(tmp_path)
    before = len(page.sentences())
    ops = AP.apply_all(c, page)
    assert len(ops) == 6                                        # every finding is in the applied record
    deleted = [o for o in ops if not o.get("already_removed")]
    repeats = [o for o in ops if o.get("already_removed")]
    assert len(deleted) == 4 and len(repeats) == 2
    assert len(page.sentences()) == before - 4                  # each sentence removed once
    assert not any(s.startswith(FIRST) for s in page.sentences())
    by_key = {o["key"]: o for o in deleted}
    for r in repeats:                                           # recorded against the removal that took it
        first = by_key[r["removed_by"]]
        assert norm(first["old"]) == norm(r["old"]) and first["key"] != r["key"]
    log = _applied(c)
    assert {o["key"] for o in ops} <= {r["key"] for r in log}
    assert sum(1 for r in log if r.get("already_removed")) == 2
    assert AP.pending(c) == []                                  # a re-run of the applier applies nothing more
    assert AP.apply_all(c, page) == []


def test_a_removal_already_applied_in_an_earlier_step_is_recorded_not_an_error(tmp_path):
    c, page = _case(tmp_path)
    AP.apply_all(c, page)                                       # the overstatement step's removals
    s = next(r["sentence"] for r in _rows() if r["fingerprint"] == "3eaef99bdf5c3c89")
    with (c / "rulings" / "lean_removed.jsonl").open("a") as fh:   # a later step finds the same sentence again
        fh.write(json.dumps({"at": "2026-11-25T15:00:00+00:00", "path": "later_step", "finding": "x",
                             "finding_key": "k-later", "fingerprint": "3eaef99bdf5c3c89", "sentence": s,
                             "outcome": "removed: unresolved finding"}) + "\n")
    ops = AP.apply_all(c, page)
    assert len(ops) == 1 and ops[0]["already_removed"] and ops[0]["removed_by"].startswith("failsafe:overstatement:")


def test_a_removal_of_a_sentence_never_on_the_page_is_still_an_error(tmp_path):
    c, page = _case(tmp_path)
    with (c / "rulings" / "lean_removed.jsonl").open("a") as fh:
        fh.write(json.dumps({"at": "2026-11-25T14:00:00+00:00", "path": "overstatement", "finding": "overstatement",
                             "finding_key": "k-never", "fingerprint": "0000000000000000",
                             "sentence": "This sentence was never on the page [1].",
                             "outcome": "removed: unresolved finding"}) + "\n")
    with pytest.raises(NotPlaced) as e:
        AP.apply_all(c, page)
    assert "never on the page" in str(e.value)


def test_a_replacement_of_a_removed_sentence_is_still_an_error(tmp_path):
    """Only a removal is idempotent: a ruling that rewrites a sentence no longer on the page cannot be placed."""
    c, page = _case(tmp_path)
    AP.apply_all(c, page)
    s = next(r["sentence"] for r in _rows() if r["fingerprint"] == "3be2742c7ee7bf5c")
    with (c / "rulings" / "rulings.jsonl").open("a") as fh:
        fh.write(json.dumps({"id": "r-late", "at": "2026-11-25T15:00:00+00:00", "ruling": "amend",
                             "inputs": {"sentence": s}, "text": "A rewritten sentence [1]."}) + "\n")
    with pytest.raises(NotPlaced) as e:
        AP.apply_all(c, page)
    assert "not found on the page" in str(e.value)


def test_the_runs_own_records_still_stop_on_the_rewritten_sentence(tmp_path):
    """With every row of the run: the repeated removal of FIRST is recorded, and the removal of a sentence that is not
    on the page and that no record of the run removed (STALE: rewritten by a ruling, not removed) stays an error."""
    c, page = _case(tmp_path, stale=True)
    with pytest.raises(NotPlaced) as e:
        AP.apply_all(c, page)
    assert "not found on the page" in str(e.value) and "d = 4.60 from two studies" in str(e.value)
    log = _applied(c)
    assert any(r.get("already_removed") and r["old"].startswith(FIRST) for r in log)
