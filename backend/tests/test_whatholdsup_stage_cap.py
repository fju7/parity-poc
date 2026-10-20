"""A paid stage does not start if its estimate exceeds the cap left (2026-10-20).

stage_cap estimates a stage from measured spend (the ledger, audit manifests,
ruling logs) and refuses to start it when the estimate exceeds the cap
remaining today or on the issue, saying so with both numbers. No model is
called; the ledger and caps are stand-ins.
"""
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("stage_cap_t", WHU / "stage_cap.py")
SC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SC)

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _e(role, usd, issue="demo", at=None, script="factcheck_draft.py"):
    return {"at": at or TODAY + "T01:00:00+00:00", "script": script, "role": role, "issue": issue, "usd": usd}


@pytest.fixture
def ledger(monkeypatch, tmp_path):
    rows = []
    monkeypatch.setattr(SC.S, "entries", lambda: list(rows))
    monkeypatch.setattr(SC.S, "caps", lambda: {"default_per_day": 25, "default_per_issue": 40,
                                               "study_per_issue": 50})
    monkeypatch.setattr(SC.S, "is_study_issue", lambda issue: issue == "study")
    monkeypatch.setattr(SC, "ROOT", tmp_path)
    monkeypatch.delenv("WHU_SPEND_OVERRIDE", raising=False)
    return rows


def test_per_unit_figures_are_measured(ledger):
    ledger += [_e("advocate:S1", 0.20, at="2026-10-01T01:00:00+00:00"),
               _e("advocate-requote:S1", 0.10, at="2026-10-01T02:00:00+00:00"),
               _e("advocate:S2", 0.50, at="2026-10-01T01:00:00+00:00"),
               _e("source:Paper", 0.30), _e("recency", 0.50), _e("changecheck", 0.04)]
    assert SC.per_unit("advocate")[0] == pytest.approx(0.40)              # (0.30 + 0.50) / 2 sources
    assert SC.per_unit("gate-narrow")[0] == pytest.approx(0.40)
    assert SC.estimate("changecheck", 1)[0] == pytest.approx(0.04)
    assert "nothing measured" in SC.per_unit("rulings")[1]                 # falls back, and says so


def test_audit_per_unit_is_spend_over_units_across_manifests(ledger, tmp_path):
    for i, (usd, units) in enumerate([(4.0, 40), (2.0, 60)]):
        d = tmp_path / "issues" / "WHU-X" / "audit" / str(i)
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"usd": usd, "units": units}))
    assert SC.per_unit("audit", issues_dir=tmp_path / "issues")[0] == pytest.approx(0.06)


def test_a_stage_that_does_not_fit_in_today_is_refused_with_both_numbers(ledger):
    ledger += [_e("advocate:S1", 0.40), _e("other", 24.20, issue="")]       # $24.60 spent today
    with pytest.raises(SC.StageOverCap) as e:
        SC.check("advocate", "demo", 5)
    msg = str(e.value)
    assert "NOT STARTED" in msg and "$2.00" in msg                         # 5 x $0.40
    assert "Remaining today: $0.40 of the $25.00 day cap" in msg
    assert "Remaining on demo: $39.60 of its $40.00 cap" in msg
    assert "exceeds what is left today." in msg


def test_a_stage_that_does_not_fit_in_the_issue_is_refused(ledger):
    ledger += [_e("advocate:S1", 0.40, at="2026-10-01T01:00:00+00:00"),
               _e("x", 39.0, at="2026-10-01T01:00:00+00:00")]
    with pytest.raises(SC.StageOverCap) as e:
        SC.check("advocate", "demo", 5)
    assert "exceeds what is left the issue." in str(e.value)


def test_a_stage_that_fits_starts(ledger):
    ledger += [_e("advocate:S1", 0.40, at="2026-10-01T01:00:00+00:00")]
    r = SC.check("advocate", "demo", 5)
    assert r["over"] == [] and r["estimate"] == pytest.approx(2.0) and r["day_left"] == 25.0


def test_no_override_on_a_study_issue(ledger, monkeypatch):
    ledger += [_e("advocate:S1", 0.40), _e("x", 24.5, issue="")]
    monkeypatch.setenv("WHU_SPEND_OVERRIDE", "a reason")
    recorded = []
    monkeypatch.setattr(SC.S, "record", lambda **kw: recorded.append(kw))
    with pytest.raises(SC.StageOverCap):
        SC.check("advocate", "study", 5)
    assert SC.check("advocate", "demo", 5)["override"] == "a reason" and recorded   # published: recorded


def test_guard_exits_3_and_says_why(ledger, capsys):
    ledger += [_e("advocate:S1", 0.40), _e("x", 24.9, issue="")]
    with pytest.raises(SystemExit) as e:
        SC.guard("advocate", "demo", 5)
    assert e.value.code == 3 and "NOT STARTED" in capsys.readouterr().err


def test_every_paid_stage_is_guarded_before_its_first_call():
    src = {f: (WHU / f).read_text() for f in ("audit_stage.py", "conclusion_judge.py", "changecheck.py",
                                                  "source_advocate.py", "ruling.py")}
    gate = (WHU.parent / "signal" / "factcheck_draft.py").read_text()
    assert '_stage_guard("gate-full"' in gate and '_stage_guard("gate-narrow"' in gate
    assert gate.index('_stage_guard("gate-full"') < gate.index("claims = extract_claims(draft)")
    assert 'stage_cap.guard("audit"' in src["audit_stage.py"]
    assert 'stage_cap.guard("conclusions"' in src["conclusion_judge.py"]
    assert 'stage_cap.guard("changecheck"' in src["changecheck.py"]
    assert 'stage_cap.guard("rulings"' in src["ruling.py"]
