"""Readers'-list lines: from a record, bound when written, checked both ways (advisor, 2026-11-25, P102/P103).

Found at $0 (P103): every readers'-list line on WHU-OT1-02z (9) and WHU-OT1-02w (attempt 23's paid run, 7) comes from
a record with its source, offsets and verbatim quotation (coverage.json declarations, omissions.json outcomes), but
none was ever bound -- bindings.bind_declaration_lines ran only inside `bindings.py scan` at the bind step, before any
line existed. The out-of-scope lines also leaked into the limits block, so each was on the page twice. And the first
probe of this ran without the run's WHU_LIBRARY_ROOT and reported "1 declaration, empty quotation": a probe error.

Ruled: each line bound from its record whenever orchestrator._rerender writes the list; "Outside this question" lines
only in the readers' list; the standing check holds readers'-list lines both ways (a record and an on-page binding;
every on-page declaration binding is a line of the list); probes read the run's recorded environment
(orch/run_env.py). These tests read the committed records of both runs (read only) and the trial library.
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

import bindings as B          # noqa: E402
import coverage_check as C    # noqa: E402
import orchestrator as O      # noqa: E402
import source_store as store  # noqa: E402
from orch import run_env as RE  # noqa: E402
from orch.page import Page    # noqa: E402

RUNS = {"02z": ("whu-lean-orch-t1-q1-02z", ROOT / "issues" / "WHU-OT1-02z-whu-lean-orch-t1-q1-02z", 9),
        "02w": ("whu-lean-orch-t1-q1-02w", ROOT / "issues" / "WHU-OT1-02w-whu-lean-orch-t1-q1-02w", 7)}

pytestmark = pytest.mark.skipif(not store.LIB_TRIAL.exists(), reason="the trial library is local only (gitignored)")


@pytest.fixture(autouse=True)
def _lists_as_generated_before_p157(monkeypatch):
    """These fixtures replay pages generated before the advisor's rulings 2 and 4 on P157 (2026-11-26): study
    descriptors were headline units then, and a declaration of a unit the page states was still listed. The
    replays run under those rules; the new rules have their own tests (test_whu_study_descriptors.py,
    test_whu_declarations_p157.py)."""
    import coverage_check as _C
    import lean_coverage as _LC
    monkeypatch.setattr(_LC, "study_descriptor", lambda text: False)
    monkeypatch.setattr(_C, "stated_on_page", lambda d, spans, said: None, raising=False)


@pytest.fixture
def run_environment(monkeypatch):
    """The run's own environment (its run record), restored afterwards."""
    snap = RE.snapshot()
    monkeypatch.setenv("WHU_LEAN", "1")                    # restored by monkeypatch; RE.use sets it too
    yield lambda case: RE.use(case)
    RE.restore(snap)


def _ctx(tmp_path, monkeypatch, which):
    slug, case, _n = RUNS[which]
    c = tmp_path / which
    (c / "draft").mkdir(parents=True)
    shutil.copy(case / "draft" / "page.json", c / "draft" / "page.json")
    shutil.copy(case / "draft" / ("%s.html" % slug), c / "draft" / ("%s.html" % slug))
    doc = {"d": json.loads((case / "bindings.json").read_text())}
    monkeypatch.setattr(B, "load", lambda s: copy.deepcopy(doc["d"]))
    monkeypatch.setattr(B, "save", lambda s, d: doc.__setitem__("d", copy.deepcopy(d)))
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case = slug, c
    ctx.page_json, ctx.page = c / "draft" / "page.json", c / "draft" / ("%s.html" % slug)
    return ctx, doc


# ---- the run's environment for probes -------------------------------------------------------------------------

def test_a_run_record_without_an_environment_gives_its_library_root_and_lean(run_environment):
    got = RE.recorded(RUNS["02z"][1])
    assert got["derived"] and got["env"] == {"WHU_LEAN": "1", "WHU_LIBRARY_ROOT": str(store.LIB_TRIAL)}
    run_environment(RUNS["02z"][1])
    assert os.environ["WHU_LIBRARY_ROOT"] == str(store.LIB_TRIAL) and store.LIB == store.LIB_TRIAL


def test_a_recorded_environment_is_used_as_recorded_and_carries_no_secret(tmp_path):
    env = RE.capture({"WHU_LEAN": "1", "WHU_LIBRARY_ROOT": "/x", "WHU_ORCH_PAID_RULED": "trial 1",
                      "WHU_API_KEY": "s", "WHU_TOKEN_X": "s", "ANTHROPIC_API_KEY": "s", "PATH": "/bin"})
    assert env == {"WHU_LEAN": "1", "WHU_LIBRARY_ROOT": "/x", "WHU_ORCH_PAID_RULED": "trial 1"}
    (tmp_path / "orchestrator").mkdir()
    (tmp_path / "orchestrator" / "run_paid.json").write_text(json.dumps({"library_root": "/y", "environment": env}))
    got = RE.recorded(tmp_path)
    assert got == {"env": env, "derived": False, "record": str(tmp_path / "orchestrator" / "run_paid.json")}


def test_probes_of_runs_made_in_different_environments_are_refused(tmp_path, monkeypatch):
    for name, lib in (("a", "/lib1"), ("b", "/lib2")):
        d = tmp_path / "issues" / ("WHU-X-%s" % name) / "orchestrator"
        d.mkdir(parents=True)
        (d / "run_paid.json").write_text(json.dumps({"library_root": lib}))
    with pytest.raises(RE.RunsDisagree):
        RE.use_for(["a", "b"], root=tmp_path)
    assert RE.use_for(["nothing-here"], root=tmp_path) is None


def test_every_loaded_copy_of_source_store_follows_the_run_environment(run_environment):
    """Several test files replace sys.modules["source_store"] with a fresh copy after other modules imported it; a
    probe that switched only sys.modules' copy read the main library through spancheck's (found 2026-11-25, P104)."""
    import importlib.util
    import spancheck as SC
    old = sys.modules["source_store"]
    spec = importlib.util.spec_from_file_location("source_store", W / "source_store.py")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    sys.modules["source_store"] = fresh
    try:
        fresh.LIB = SC.store.LIB = store.LIB_REAL
        run_environment(RUNS["02z"][1])
        assert fresh.LIB == SC.store.LIB == store.LIB_TRIAL
    finally:
        sys.modules["source_store"] = old


def test_the_diagnostics_apply_the_recorded_environment_by_default():
    import inspect
    src = inspect.getsource(O.main)
    assert "RE.use_for(" in src and '("status", "replay", "estimate")' in src
    assert 'out["environment"] = environment' in src


def test_the_1_entry_finding_was_a_probe_without_the_runs_library(run_environment):
    """The probe error reproduced: the main library does not hold the trial copy, so every quotation is empty."""
    import ruling as R
    slug, case, n = RUNS["02z"]
    RE.apply({"WHU_LIBRARY_ROOT": str(store.LIB_REAL)})
    wrong = C.declarations(slug, R.held_texts(slug))
    assert len(wrong) == 1 and wrong[0]["text"] == "" and wrong[0]["state"] == "not_added_no_place"
    run_environment(case)
    right = C.declarations(slug, R.held_texts(slug))
    assert len(right) == n and all(d["text"] for d in right)


# ---- the readers' list ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("which", ["02z", "02w"])
def test_every_line_has_a_record_with_source_offsets_and_its_quotation(which, run_environment):
    import re
    import ruling as R
    slug, case, n = RUNS[which]
    run_environment(case)
    held = R.held_texts(slug)
    lines = O.readers_lines(Page.load(case / "draft" / "page.json"), slug)
    decls = {" ".join(d["sentence"].split()): d for d in C.declarations(slug, held)}
    assert len(lines) == n and set(lines) == set(decls)
    for line in lines:
        d = decls[line]
        q = re.match(r"^[^“]*“(.*?)”", line).group(1).rstrip(" …")
        sid, rng = d["key"].split("@")
        a, b = (int(x) for x in rng.split("-"))
        assert d["source"] == sid and d["text"] == held[sid][a:b] and q in d["text"]


@pytest.mark.parametrize("which", ["02z", "02w"])
def test_as_the_run_left_them_no_line_is_bound_and_the_check_says_so(which, tmp_path, monkeypatch, run_environment):
    ctx, doc = _ctx(tmp_path, monkeypatch, which)
    run_environment(RUNS[which][1])
    page = Page.load(ctx.page_json)
    rows = doc["d"]["bindings"]
    on = {k for k, v in rows.items() if v.get("on_page")}
    bad = O.readers_problems(ctx, page, rows, on)
    n = RUNS[which][2]
    assert len(bad) == n and all("has no on_page binding" in b for b in bad)       # every record is there


@pytest.mark.parametrize("which", ["02z", "02w"])
def test_binding_when_written_makes_the_list_pass_both_ways(which, tmp_path, monkeypatch, run_environment):
    ctx, doc = _ctx(tmp_path, monkeypatch, which)
    run_environment(RUNS[which][1])
    page = Page.load(ctx.page_json)
    got = O.bind_readers_lines(ctx, page)
    assert got == {"bound": RUNS[which][2], "off": 0}
    rows = doc["d"]["bindings"]
    for line in O.readers_lines(page, ctx.slug):
        r = rows[B.fingerprint(line)]
        assert r["on_page"] and B.is_declaration_row(r) and r["span"] and r["offsets"] and r["source_id"]
    on = {k for k, v in rows.items() if v.get("on_page")}
    assert O.readers_problems(ctx, page, rows, on) == []


def test_the_limits_block_carries_no_declaration_line_and_each_appears_once(tmp_path, monkeypatch, run_environment):
    ctx, _doc = _ctx(tmp_path, monkeypatch, "02z")
    run_environment(RUNS["02z"][1])
    old = Page.load(ctx.page_json)
    old_limits = next(b for b in old.blocks() if b.get("section") == "limits" and b.get("tag") == "html")["html"]
    assert old_limits.count("Outside this question:") == 2                     # the leak, as the run left it
    q, limits, readers = O._generated_blocks(ctx)
    assert not any(l in limits for l in set(C.LEAD.values())) and C.HEADING not in limits
    assert readers.count("Outside this question:") == 2 and readers.count(C.HEADING) == 1


def test_a_line_with_no_record_stops(tmp_path, monkeypatch, run_environment):
    ctx, doc = _ctx(tmp_path, monkeypatch, "02z")
    run_environment(RUNS["02z"][1])
    page = Page.load(ctx.page_json)
    O.bind_readers_lines(ctx, page)
    blk = next(b for b in page.blocks() if b.get("section") == "readers")
    blk["html"] += "\n  <p>Outside this question: “A finding nobody recorded” ([1]).</p>"
    rows = doc["d"]["bindings"]
    on = {k for k, v in rows.items() if v.get("on_page")}
    bad = O.readers_problems(ctx, page, rows, on)
    assert len(bad) == 2 and "has no record" in bad[0] and "has no on_page binding" in bad[1]


def test_a_declaration_binding_off_the_list_stops_and_regeneration_takes_it_off(tmp_path, monkeypatch,
                                                                                 run_environment):
    ctx, doc = _ctx(tmp_path, monkeypatch, "02z")
    run_environment(RUNS["02z"][1])
    page = Page.load(ctx.page_json)
    O.bind_readers_lines(ctx, page)
    blk = next(b for b in page.blocks() if b.get("section") == "readers")
    gone = O.readers_lines(page, ctx.slug)[0]
    blk["html"] = "\n".join(l for l in blk["html"].splitlines() if "Twenty" not in l)
    rows = doc["d"]["bindings"]
    on = {k for k, v in rows.items() if v.get("on_page")}
    bad = O.readers_problems(ctx, page, rows, on)
    assert any("is not a readers'-list line" in b and B.fingerprint(gone) in b for b in bad)
    assert O.bind_readers_lines(ctx, page)["off"] == 1
    r = doc["d"]["bindings"][B.fingerprint(gone)]
    assert r["on_page"] is False and r["off_page_by"] == "readers' list regenerated"


def test_binding_problems_runs_the_readers_check():
    import inspect
    assert "readers_problems(ctx, page, rows, on)" in inspect.getsource(O.binding_problems)
    assert "bind_readers_lines(ctx, page)" in inspect.getsource(O._rerender)
