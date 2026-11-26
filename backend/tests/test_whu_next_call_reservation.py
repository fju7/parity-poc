"""A multi-call stage reserves only its NEXT call's bound (advisor's ruling 2 on P146, 2026-11-26).

Q1-01 run 2 reached the gate with $2.42 left of a $5.00 cap; the advocate would then have reserved 6 sources x
$1.394 = $8.36 up front and refused a run that might have fitted. In an orchestrated run a stage now checks one
call's bound up front (stage_cap.check / guard_amount) and again before every paid call (spend_ledger._reserve_next
inside orch_guard). The per-call bounds are unchanged. A call that does not fit stops the run as a cap stop with
the calls made and the calls left, and the step's partial output never stays on the page.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import orchestrator as O  # noqa: E402
import stage_cap as SC  # noqa: E402

SL = SC.S                   # spend_ledger, as stage_cap loads it (backend/scripts never goes on sys.path)

ISSUE = "whu-lean-orch-t1-q1-01"
PER_SOURCE = 1.394          # Q1-01's advocate bound per source: $0.697 (02z S001) x 2


@pytest.fixture
def q101(monkeypatch):
    """Q1-01 at the advocate: $2.58 spent of a $5.00 cap (run 2's figures)."""
    monkeypatch.setattr(SC.S, "caps", lambda: {"default_per_day": 60})
    monkeypatch.setattr(SC.S, "entries", lambda: [])
    monkeypatch.setattr(SC.S, "cap_for", lambda issue: 5.0)
    monkeypatch.setattr(SC.S, "spent", lambda issue=None, **k: 2.5755)
    monkeypatch.setattr(SC.S, "check_cap", lambda issue, about_to_spend=0.0: None)
    monkeypatch.setattr(SC, "per_unit", lambda stage, **kw: (PER_SOURCE, "the highest of 16 same-config x 2"))
    monkeypatch.delenv(SL.NEXT_BOUND_ENV, raising=False)


def test_q101s_six_sources_no_longer_need_8_36_up_front(q101, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_STEP", "advocate")
    r = SC.check("advocate", ISSUE, 6)
    assert r["over"] == [] and r["estimate"] == pytest.approx(PER_SOURCE)
    assert "$8.36, not reserved up front" in r["how"]
    nb = json.loads(__import__("os").environ[SL.NEXT_BOUND_ENV])
    assert nb["bound"] == pytest.approx(PER_SOURCE) and nb["units"] == 6 and nb["stage"] == "advocate"


def test_outside_an_orchestrated_run_the_summed_bound_is_unchanged(q101, monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    with pytest.raises(SC.StageOverCap, match=r"8\.36"):
        SC.check("advocate", ISSUE, 6)


def test_the_gate_reserves_one_call_in_an_orchestrated_run(q101, monkeypatch):
    seen = {}
    monkeypatch.setattr(SC.S, "check_cap", lambda issue, about_to_spend=0.0: seen.setdefault("a", about_to_spend))
    monkeypatch.setattr(SC, "_frozen", lambda: type("F", (), {"is_study": staticmethod(lambda i: False)}))
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    SC.guard_amount("the machine gate (narrow)", ISSUE, 1.50, "run bound", next_bound=(1.50, "one call"))
    assert seen["a"] == pytest.approx(1.50)
    monkeypatch.delenv("WHU_ORCH_STEP")
    seen.clear()
    SC.guard_amount("the machine gate (narrow)", ISSUE, 3.10, "run bound", next_bound=(1.50, "one call"))
    assert seen["a"] == pytest.approx(3.10)                       # outside a run: the run's bound, as before


def _ledger(monkeypatch, tmp_path, spent, cap):
    monkeypatch.setattr(SL, "spent", lambda issue=None, **k: spent)
    monkeypatch.setattr(SL, "cap_for", lambda issue: cap)

    def check_cap(issue, about_to_spend=0.0):
        if spent + about_to_spend > cap:
            raise SL.OverCap("%s has spent $%.2f of a $%.2f cap and this run would add about $%.2f"
                             % (issue, spent, cap, about_to_spend))
    monkeypatch.setattr(SL, "check_cap", check_cap)
    stop = tmp_path / "orchestrator" / "cap_stop.json"
    monkeypatch.setenv(SL.CAP_STOP_ENV, str(stop))
    monkeypatch.setenv(SL.NEXT_BOUND_ENV, json.dumps({"stage": "advocate", "bound": PER_SOURCE, "units": 6,
                                                      "how": "x"}))
    return stop


def test_each_call_is_checked_and_a_call_that_fits_goes_ahead(monkeypatch, tmp_path):
    stop = _ledger(monkeypatch, tmp_path, spent=3.0, cap=5.0)
    SL._reserve_next(ISSUE, "advocate", 1, 120)                   # $3.00 + $1.394 <= $5.00
    assert not stop.exists()


def test_a_call_that_does_not_fit_is_a_cap_stop_with_calls_made_and_left(monkeypatch, tmp_path):
    stop = _ledger(monkeypatch, tmp_path, spent=4.0, cap=5.0)
    with pytest.raises(SL.ReservationStop, match="cap stop in step 'advocate'"):
        SL._reserve_next(ISSUE, "advocate", 7, 120)
    rec = json.loads(stop.read_text())
    assert (rec["calls_made"], rec["calls_left_at_most"], rec["units_planned"]) == (7, 113, 6)
    assert rec["bound"] == pytest.approx(PER_SOURCE) and rec["spent_on_issue"] == 4.0
    assert isinstance(SL.ReservationStop("x"), SL.OverCap)        # a cap stop, as every cap refusal


def test_once_stopped_every_later_call_of_the_step_is_refused(monkeypatch, tmp_path):
    stop = _ledger(monkeypatch, tmp_path, spent=4.0, cap=5.0)
    with pytest.raises(SL.ReservationStop):
        SL._reserve_next(ISSUE, "advocate", 7, 120)
    monkeypatch.setattr(SL, "check_cap", lambda issue, about_to_spend=0.0: None)   # even if money appeared
    with pytest.raises(SL.ReservationStop, match="already stopped"):
        SL._reserve_next(ISSUE, "advocate", 7, 120)
    assert stop.exists()


def _ctx(tmp_path, monkeypatch):
    c = tmp_path / "case"
    (c / "orchestrator").mkdir(parents=True)
    (c / "draft").mkdir()
    (c / "issue.json").write_text("{}")
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.frozen, ctx.log = "orch-x", c, "trial", tmp_path, None, {}, []
    monkeypatch.setattr(O, "_study_log", lambda *a: None)
    monkeypatch.setattr(O, "_account_page", lambda ctx, step: [])
    (c / "draft" / "orch-x.html").write_text("<p>The page before the step.</p>")
    (c / "draft" / "page.json").write_text('{"v": 1}')
    (c / "bindings.json").write_text('{"bindings": {}}')
    return ctx


def _partial_step(ctx, step, raise_after=True):
    (ctx.case / "draft" / "orch-x.html").write_text("<p>half a page</p>")
    (ctx.case / "draft" / "page.json").write_text('{"v": 2}')
    (ctx.case / "bindings.json").write_text('{"bindings": {"x": 1}}')
    (ctx.case / O.CAP_STOP).write_text(json.dumps({"step": step.name, "bound": PER_SOURCE, "calls_made": 7,
                                                   "calls_left_at_most": 113, "reason": "over the issue cap"}))
    if raise_after:
        raise SL.ReservationStop("cap stop in step %r" % step.name)


@pytest.mark.parametrize("raise_after", [True, False])     # False: a stage that caught the stop and exited 0
def test_a_mid_step_cap_stop_stops_cleanly_with_nothing_partial_on_the_page(tmp_path, monkeypatch, raise_after):
    from orch import steps as ST
    ctx = _ctx(tmp_path, monkeypatch)
    before = {p: (ctx.case / p).read_text() for p in ("draft/orch-x.html", "draft/page.json", "bindings.json")}
    monkeypatch.setitem(O.STEP_CODE, "partial", lambda c, s: _partial_step(c, s, raise_after))
    with pytest.raises(O.RunStop, match="advocate: cap stop: .*7 call\\(s\\) made, at most 113 left"):
        O.run_step(ctx, ST.Step("advocate", "code", owns=("bindings.json", "draft/*"), code="partial"))
    for p, text in before.items():
        assert (ctx.case / p).read_text() == text
    assert sorted(ctx.cap_stop["page_restored"]) == ["bindings.json", "draft/orch-x.html", "draft/page.json"]
    assert ctx.log[-1]["failed"].startswith("RunStop: advocate: cap stop")
    assert not O.CH.rows(ctx.case)                                # no chain row: the step did not complete


def test_a_stale_cap_stop_from_an_earlier_step_is_cleared(tmp_path, monkeypatch):
    from orch import steps as ST
    ctx = _ctx(tmp_path, monkeypatch)
    (ctx.case / O.CAP_STOP).write_text(json.dumps({"step": "gate"}))
    monkeypatch.setitem(O.STEP_CODE, "quiet", lambda c, s: None)
    O.run_step(ctx, ST.Step("advocate", "code", owns=("bindings.json",), code="quiet"))
    assert not (ctx.case / O.CAP_STOP).exists()


def test_every_step_env_names_the_cap_stop_file(tmp_path, monkeypatch):
    from orch import steps as ST
    ctx = _ctx(tmp_path, monkeypatch)
    assert O.Ctx.env(ctx, ST.BY_NAME["advocate"])["WHU_ORCH_CAP_STOP"] == str(ctx.case / O.CAP_STOP)
