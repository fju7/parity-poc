"""Advisor's rulings 1 and 2 on P140 (2026-11-26): pre-step cap checks are same-config measured upper bounds.

1. The gate (factcheck_draft.py, before its first paid call): max(its dry-run estimate, the highest measured gate run
   among gate reports with the same lean_config) x 2, checked against the day, issue and line caps; a refusal is
   "stopped before spending" (exit 3) for every cap class. It replaced a fixed $3.00 that refused 02-batch run 1
   (WHU-OT1-04, Q1-04: $1.24 spent of a $3.00 cap, the gate's dry run 1 call x $0.75).
2. Every stage estimate in stage_cap.per_unit that was a pooled mean is the highest same-config figure x 2 (config:
   model and orchestrated; the reply-limits table is recorded, not matched); with no same-config record, the higher of
   the fallback and the highest of any config, x 2. The audit's (P114) is unchanged.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "signal"))
import stage_cap as SC  # noqa: E402

Q104 = ROOT / "issues" / "WHU-OT1-04-whu-lean-orch-t1-q1-04"


def _fc():
    import factcheck_draft as F
    return F


# --- 1. the gate --------------------------------------------------------------------------------------------------

def test_q1_04s_gate_now_fits_its_cap(tmp_path, monkeypatch):
    """Q1-04's own figures: $1.24 spent of $3.00 (the ledger), dry run 1 call x $0.75 (its recorded dry run); the
    highest measured orchestrated gate run in the ledger is 02n's $0.6288 -> bound max(0.75, 0.6288) x 2 = $1.50 <=
    $1.76 left: the gate starts."""
    rec = json.loads((Q104 / "orchestrator" / "run_paid.json").read_text(encoding="utf-8"))
    gate = next(s for s in rec["steps"] if s["step"] == "gate")
    assert "calls that would be made: 1" in gate["cmds"][0]["tail"] and "$0.75" in gate["cmds"][0]["tail"]
    F = _fc()
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    monkeypatch.setenv("WHU_LEAN", "1")
    cfg = F.gate_config("narrow")
    amount, how = SC.gate_bound(cfg, F.gate_dry_estimate("narrow", 1), issues_dir=tmp_path)
    assert amount == pytest.approx(1.50) and "same-config gate run(s) $0.6288 (whu-lean-orch-t1-q1-02n)" in how
    spent = sum(s.get("usd") or 0 for s in rec["steps"])
    assert spent == pytest.approx(1.2429, abs=1e-3) and amount <= 3.00 - spent
    assert 3.00 > 3.00 - spent                                  # the old fixed $3.00 could never fit


def _report(case: Path, name: str, cfg: dict, usd: float):
    d = case / "draft"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps({"cost": {"lean_config": cfg, "usd": usd}}))


def test_the_gate_bound_takes_the_highest_same_config_run_and_ignores_others(tmp_path, monkeypatch):
    F = _fc()
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    cfg = F.gate_config("narrow")
    other = dict(cfg, model="another-model")
    _report(tmp_path / "D", "d.html.gate.json", dict(cfg, limits={"fc:recency": 1}), 0.62)   # limits: not matched
    _report(tmp_path / "A", "a.html.gate.json", cfg, 0.62)
    _report(tmp_path / "B", "b.html.gate-final.json", cfg, 0.41)
    _report(tmp_path / "C", "c.html.gate.json", other, 5.00)              # another configuration: not pooled
    amount, how = SC.gate_bound(cfg, 0.75 * 1, issues_dir=tmp_path, entries=[])
    assert amount == pytest.approx(0.75 * 2)                                # the dry run is higher
    amount, how = SC.gate_bound(cfg, 0.25, issues_dir=tmp_path, entries=[])
    assert amount == pytest.approx(0.62 * 2) and "3 same-config" in how and "(A)" in how
    rows = [{"script": "factcheck_draft.py", "step": "gate", "model": cfg["model"], "issue": "q", "usd": 0.5},
            {"script": "factcheck_draft.py", "step": "gate", "model": cfg["model"], "issue": "q", "usd": 0.4},
            {"script": "factcheck_draft.py", "step": "gate", "model": "another-model", "issue": "r", "usd": 9.0}]
    amount, how = SC.gate_bound(cfg, 0.25, issues_dir=tmp_path, entries=rows)
    assert amount == pytest.approx(0.90 * 2)                                # one ledger run, 0.5 + 0.4


def test_the_gate_config_names_the_limits_it_runs_under(monkeypatch):
    F = _fc()
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    cfg = F.gate_config("narrow")
    assert cfg["orchestrated"] and cfg["limits"] == {"fc:recency": F._RL.limit("fc:recency"),
                                                     "fc:source": F._RL.limit("fc:source")}
    monkeypatch.delenv("WHU_ORCH_STEP")
    monkeypatch.delenv("WHU_ORCH_MODE", raising=False)
    assert F.gate_config("narrow")["limits"] is None and F.gate_dry_estimate("narrow", 3) == pytest.approx(2.25)


@pytest.mark.parametrize("exc", ["OverCap", "OverIssueCap", "OverLineCap"])
def test_a_gate_refused_by_any_cap_stops_before_spending(monkeypatch, capsys, exc):
    S = SC.S
    monkeypatch.setattr(SC.S, "check_cap", lambda issue, about_to_spend=0.0: (_ for _ in ()).throw(
        getattr(SC.S, exc)("over")))
    monkeypatch.setattr(SC, "_frozen", lambda: type("F", (), {"is_study": staticmethod(lambda s: False)}))
    with pytest.raises(SystemExit) as e:
        SC.guard_amount("the machine gate (narrow)", "x", 1.5, "how")
    assert e.value.code == 3 and "NOT STARTED" in capsys.readouterr().err
    assert issubclass(getattr(S, exc), S.OverCap)


def test_the_fixed_three_dollars_is_gone_and_the_report_records_its_cost():
    src = (ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py").read_text(encoding="utf-8")
    assert "about_to_spend=3.0" not in src and 'type(_exc).__name__ == "OverCap"' not in src
    assert '_gate_guard("narrow"' in src and '_gate_guard("full"' in src and '"cost": _gate_cost(mode)' in src
    assert '_stage_guard("gate-' not in src                     # the pooled-mean gate guard is replaced, not doubled


# --- 2. the sweep: every pooled stage estimate is a same-config bound -------------------------------------------

def _row(role, usd, model="m1", step=None, limits=None, issue="i", at="2026-11-26T00:00:00"):
    r = {"script": "factcheck_draft.py", "role": role, "usd": usd, "model": model, "issue": issue, "at": at}
    if step:
        r["step"] = step
    if limits:
        r["limits_sha"] = limits
    return r


@pytest.mark.parametrize("stage,role", [("gate-narrow", "recency"), ("conclusions", "conclusion_judge/x"),
                                        ("changecheck", "changecheck")])
def test_a_call_priced_stage_is_the_highest_same_config_call_x2(tmp_path, monkeypatch, stage, role):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    es = [_row(role, 0.10), _row(role, 0.30), _row(role, 9.0, step="gate", limits="L")]   # the last: orchestrated
    each, how = SC.per_unit(stage, entries=es, issues_dir=tmp_path)
    assert each == pytest.approx(0.60) and "same-config" in how
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    monkeypatch.setenv("WHU_ORCH_LIMITS_SHA", "L")
    assert SC.per_unit(stage, entries=es, issues_dir=tmp_path)[0] == pytest.approx(18.0)


def test_with_no_same_config_record_it_is_the_higher_of_fallback_and_any_config(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    es = [_row("recency", 0.10), _row("recency", 1.10)]                        # neither orchestrated
    each, how = SC.per_unit("gate-narrow", entries=es, issues_dir=tmp_path)
    assert each == pytest.approx(max(SC.FALLBACK["gate-narrow"][0], 1.10) * 2) and "no same-config" in how


def test_the_limits_table_is_recorded_but_not_matched(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    monkeypatch.setenv("WHU_ORCH_LIMITS_SHA", "NEW")
    es = [_row("recency", 0.30, step="gate", limits="OLD"), _row("recency", 0.10, step="gate")]
    each, how = SC.per_unit("gate-narrow", entries=es, issues_dir=tmp_path)
    assert each == pytest.approx(0.60) and "2 same-config" in how


def test_the_model_is_matched_when_the_caller_names_it(tmp_path, monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    es = [_row("conclusion_judge/x", 0.01, model="judge"), _row("conclusion_judge/x", 0.50, model="other")]
    assert SC.per_unit("conclusions", entries=es, issues_dir=tmp_path, model="judge")[0] == pytest.approx(0.02)
    assert SC.per_unit("conclusions", entries=es, issues_dir=tmp_path)[0] == pytest.approx(1.00)


def test_rulings_pool_by_model_orchestrated_and_limits(tmp_path, monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    for case, usd, extra in (("WHU-S01-x", 0.01, {}), ("WHU-S02-y", 0.03, {}), ("WHU-OT1-02-z", 0.90, {"limits_sha": "L"})):
        d = tmp_path / case / "rulings"
        d.mkdir(parents=True)
        (d / "rulings.jsonl").write_text(json.dumps(dict({"model": "m", "usage": {"usd": usd}}, **extra)) + "\n")
    assert SC.per_unit("rulings", entries=[], issues_dir=tmp_path)[0] == pytest.approx(0.06)
    monkeypatch.setenv("WHU_ORCH_STEP", "audit")
    monkeypatch.setenv("WHU_ORCH_LIMITS_SHA", "L")
    assert SC.per_unit("rulings", entries=[], issues_dir=tmp_path)[0] == pytest.approx(1.80)


def test_the_advocate_is_the_highest_source_total_x2(tmp_path, monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    es = [_row("advocate:S1", 0.30, issue="a"), _row("advocate-requote:S1", 0.10, issue="a"),
          _row("advocate:S2", 0.20, issue="a")]
    each, how = SC.per_unit("advocate", entries=es, issues_dir=tmp_path)
    assert each == pytest.approx(0.80) and "highest" in how


def test_the_ledger_and_rulings_record_the_limits_table_in_an_orchestrated_step(tmp_path, monkeypatch):
    S = SC.S
    import reply_limits as RL
    assert len(RL.sha()) == 16 and RL.sha() == RL.sha()
    led = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(S, "LEDGER", led)
    monkeypatch.setenv("WHU_ORCH_STEP", "gate")
    monkeypatch.setenv("WHU_ORCH_LIMITS_SHA", RL.sha())
    S.record(script="x.py", role="r", issue="i", usd=0.01)
    assert json.loads(led.read_text().splitlines()[-1])["limits_sha"] == RL.sha()
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    assert '"WHU_ORCH_LIMITS_SHA": _limits_sha()' in src
    assert 'os.environ["WHU_ORCH_LIMITS_SHA"]' in (W / "ruling.py").read_text(encoding="utf-8")


def test_every_stage_guard_caller_is_accounted_for():
    """The sweep's list, pinned: every stage_cap.guard / check / gate bound call site in the pipeline."""
    import re
    sites = {}
    for f in list(W.glob("*.py")) + list((W / "orch").glob("*.py")) + [ROOT / "backend/scripts/signal/factcheck_draft.py"]:
        for m in re.finditer(r"stage_cap\.(guard|check)\(\"([a-z-]+)\"|_gate_guard\(\"(narrow|full)\"",
                             f.read_text(encoding="utf-8")):
            sites.setdefault(f.name, set()).add(m.group(2) or "gate-" + m.group(3))
    assert sites == {"audit_stage.py": {"audit"}, "consistency.py": {"rulings"}, "conclusion_judge.py": {"conclusions"},
                     "changecheck.py": {"changecheck"}, "source_advocate.py": {"advocate"},
                     "ruling.py": {"omissions", "judgements", "rulings"},
                     "factcheck_draft.py": {"gate-narrow", "gate-full"}}
