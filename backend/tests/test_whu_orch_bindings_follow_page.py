"""Advisor's ruling after the P100 build (2026-11-25, P101): bindings follow the page.

Found while building P100 from attempt 24's second fresh run (WHU-OT1-02z): bindings.json kept on_page: true for six
sentences applied rulings had replaced (advocate rulings rulings.jsonl:9-11, audit rulings 1-3), and the overstatement
check, which reads on_page entries, checked three of them; one "yes" made the fail-safe remove a sentence that was
no longer on the page.

  (1) When a ruling replaces or removes a sentence, its bindings entry is set on_page: false with the ruling id, and
      the replacement gets its own entry; every later step reads only on_page entries.
  (2) A standing check after every page-changing step: the on_page bindings equal the page's sentences by text
      hash, both directions (code-written lines in the first direction only: they are bound by their generators with
      their own sentence split); a mismatch stops at $0 before any paid step.

Records: the committed folder issues/WHU-OT1-02z-whu-lean-orch-t1-q1-02z/ (read only) and its applied log.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
SLUG = "whu-lean-orch-t1-q1-02z"
CASE = ROOT / "issues" / "WHU-OT1-02z-whu-lean-orch-t1-q1-02z"
STALE = {"210f93b98d355f52", "9fc13686538d780b", "ec453feacd29f205",      # advocate rulings rulings.jsonl:9-11
         "27a340e5c0135a9b", "33659dd3a16cca21", "139255974e7d305c"}      # audit rulings 1-3

import bindings as B          # noqa: E402
import orchestrator as O      # noqa: E402
from orch.page import Page, split    # noqa: E402


@pytest.fixture(autouse=True)
def lean_run(monkeypatch):
    """The run's own environment (P103, orch/run_env.py): lean (WHU_LEAN=1; lean splits "et al." and initials as the
    run did; conftest clears it) and its library root (the trial library), restored afterwards."""
    import source_store as store
    from orch import run_env as RE
    if not store.LIB_TRIAL.exists():
        pytest.skip("the trial library is local only (gitignored)")
    snap = RE.snapshot()
    monkeypatch.setenv("WHU_LEAN", "1")
    RE.use(CASE)
    yield
    RE.restore(snap)


def _applied():
    return [json.loads(l) for l in (CASE / "orchestrator" / "applied.jsonl").read_text().splitlines() if l.strip()]


def _ruling_ops():
    """The six applied rulings. (The applied log's last line is the overstatement removal the failed apply marked;
    the page was never saved, so its sentence is still on the page and its entry correctly stays on.)"""
    return [dict(op) for op in _applied() if op["op"] in ("replace", "delete") and op["key"].startswith("ruling:")]


@pytest.fixture
def run(tmp_path, monkeypatch):
    """A Ctx on a copy of 02z's page, with bindings.json held in memory (B.load / B.save patched)."""
    c = tmp_path / "case"
    (c / "draft").mkdir(parents=True)
    shutil.copy(CASE / "draft" / "page.json", c / "draft" / "page.json")
    shutil.copy(CASE / "draft" / ("%s.html" % SLUG), c / "draft" / ("%s.html" % SLUG))
    shutil.copy(CASE / "sources.json", c / "sources.json")
    doc = {"d": json.loads((CASE / "bindings.json").read_text())}
    monkeypatch.setattr(B, "load", lambda slug: copy.deepcopy(doc["d"]))
    monkeypatch.setattr(B, "save", lambda slug, d: doc.__setitem__("d", copy.deepcopy(d)))
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case = SLUG, c
    ctx.page_json, ctx.page = c / "draft" / "page.json", c / "draft" / ("%s.html" % SLUG)
    O.bind_readers_lines(ctx, Page.load(ctx.page_json))   # P103: as every regeneration of the list now does
    return ctx, doc


def _check(ctx):
    return O.binding_problems(ctx, Page.load(ctx.page_json), ctx.page.read_text(encoding="utf-8"))


def test_02z_records_carry_the_six_stale_entries():
    rows = json.loads((CASE / "bindings.json").read_text())["bindings"]
    page = Page.load(CASE / "draft" / "page.json")
    here = {B.fingerprint(s) for s in page.sentences()} | {B.fingerprint(s) for s in B.page_sentences(SLUG)}
    stale = {k for k, v in rows.items() if v.get("on_page") and k not in here}
    assert stale == STALE
    ruled = {B.fingerprint(op["old"]): bool(op["new"]) for op in _applied() if op["op"] == "replace"}
    assert set(ruled) == STALE                       # each one is the old text of an applied ruling:
    assert sorted(ruled.values()) == [False] * 3 + [True] * 3    # three rewritten, three removed (audit, new "")


def test_the_standing_check_finds_the_six_stale_entries_and_nothing_else(run):
    ctx, _doc = run
    bad = _check(ctx)
    assert len(bad) == 6 and all(b.startswith(O.BINDING_PREFIX + "on_page entry ") for b in bad)
    assert {b.split("on_page entry ")[1][:16] for b in bad} == STALE


def test_a_ruling_takes_its_sentences_binding_off_the_page_with_its_id(run):
    ctx, doc = run
    ops = _ruling_ops()
    assert len(ops) == 6
    assert O.bindings_off_page(ctx, ops) == 6
    rows = doc["d"]["bindings"]
    for op in ops:
        r = rows[B.fingerprint(op["old"])]
        assert r["on_page"] is False and r["off_page_by"] == op["key"] and r["left_page"]
        new = [B.fingerprint(x) for x in split(op["new"])]
        assert r.get("replaced_by") == (new or None)
        for f in new:                                # the replacement has its own on_page entry
            assert rows[f]["on_page"] is True
    assert _check(ctx) == []                         # bindings and page now agree, both directions


def test_a_repeated_removal_is_recorded_on_the_entry_it_took_off(run):
    ctx, doc = run
    page = Page.load(ctx.page_json)
    s = next(x for x in page.sentences() if x.startswith("A systematic review of 28 studies"))
    page.delete(s)
    page.save(ctx.page_json)
    first = {"op": "delete", "old": s, "key": "failsafe:overstatement:d5b7:3be2742c7ee7bf5c"}
    again = {"op": "delete", "old": s, "key": "failsafe:overstatement:c395:3be2742c7ee7bf5c",
             "already_removed": True, "removed_by": first["key"]}
    O.bindings_off_page(ctx, [first, again])
    r = doc["d"]["bindings"][B.fingerprint(s)]
    assert r["on_page"] is False and r["off_page_by"] == first["key"] and r["also_removed_by"] == [again["key"]]
    assert "replaced_by" not in r


def test_code_bind_never_puts_a_replaced_sentence_back_on_the_page(run, monkeypatch):
    ctx, doc = run
    O.bindings_off_page(ctx, _ruling_ops())
    prov = Page.load(ctx.page_json).doc["provenance"]
    assert STALE & {B.fingerprint(k) for k in prov}  # provenance still names replaced sentences
    O.code_bind(ctx, None)                           # an unrestricted bind, as the judgements step runs it
    rows = doc["d"]["bindings"]
    assert not any(rows[k]["on_page"] for k in STALE)
    assert _check(ctx) == []


def test_a_page_sentence_resting_on_passages_with_no_entry_is_found(run):
    ctx, doc = run
    O.bindings_off_page(ctx, _ruling_ops())
    page = Page.load(ctx.page_json)
    s = next(x for x in page.blocks() if x.get("tag") == "p")["sentences"][0]
    doc["d"]["bindings"][B.fingerprint(s)]["on_page"] = False
    bad = _check(ctx)
    assert bad == [O.BINDING_PREFIX + "page sentence %s has no on_page entry: %r" % (B.fingerprint(s), s[:100])]


def test_no_bindings_yet_means_nothing_to_check(run):
    ctx, doc = run
    doc["d"] = {"bindings": {}}
    assert _check(ctx) == []


def test_a_mismatch_stops_the_step_at_zero_with_the_check_wording(tmp_path, monkeypatch):
    from orch import steps as ST
    c = tmp_path / "case"
    (c / "orchestrator").mkdir(parents=True)
    (c / "issue.json").write_text("{}")
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.frozen, ctx.log = "orch-x", c, "trial", tmp_path, None, {}, []
    monkeypatch.setattr(O, "_study_log", lambda *a: None)
    finding = O.BINDING_PREFIX + "on_page entry 9fc13686538d780b is not on the page: 'For example ...'"
    monkeypatch.setattr(O, "_account_page", lambda ctx, step: [finding])
    monkeypatch.setitem(O.STEP_CODE, "quiet", lambda ctx, step: None)
    with pytest.raises(O.RunStop) as e:
        O.run_step(ctx, ST.Step("advocate", "code", owns=("bindings.json",), code="quiet"))
    assert str(e.value) == "advocate: %s: %s" % (O.CHECK_STOP, finding)


def test_account_page_runs_the_binding_check(monkeypatch):
    import inspect
    assert "binding_problems(ctx, page, html)" in inspect.getsource(O._account_page)
