"""The audit's stage-cap estimate is an upper bound from runs of the same kind (advisor's ruling 3 on P112, 2026-11-25).

Found on orchestrator trial 1 attempt 24 (WHU-OT1-02za): the audit was refused at $0 on an estimate of $2.48
(102 units x $0.0243), against $2.41 left of its cap. $0.0243 was the pooled MEAN over all 69 audit runs, 46 of
them non-lean audits reading whole held texts ($0.0338 a unit); lean audits ran $0.0038 a unit on average. Ruled:
pool only runs with the same lean_config; the estimate per unit is the highest observed per-unit cost in that pool
x 2; the per-call cap check stays the hard backstop.

The real pools are the local audit records (60 of the 69 manifests are gitignored), so those tests skip elsewhere.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("stage_cap_est", WHU / "stage_cap.py")
SC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SC)

LEAN_CONFIG = {"k": 4, "min_score": 2.0, "min_terms": 2, "passage_chars": 900,
               "models": {"audit_escalate": "claude-opus-5-5", "audit_first": "claude-sonnet-5-5",
                          "audit_rule": "claude-opus-5-5", "audit_second": "claude-opus-5-5"}}

# The audit manifests with usd and units on 2026-11-25, before attempt 25 (69 runs): the pools the ruling names.
NONLEAN_MAX = ("WHU-P02-ultra-processed-foods", "20261020T173234Z", 0.11342057142857144)
LEAN_MAX = ("WHU-L1-02b-whu-lean-q1-02b", "20261106T002750Z", 0.007693735294117647)
OT1_MAX = ("WHU-OT1-02o-whu-lean-orch-t1-q1-02o", "20261123T193544Z", 0.00654356043956044)


def _m(d: Path, usd, units, lean_config=None):
    d.mkdir(parents=True)
    m = {"usd": usd, "units": units}
    if lean_config is not None:
        m["lean_config"] = lean_config
    (d / "manifest.json").write_text(json.dumps(m))


def test_only_runs_with_the_same_lean_config_are_pooled(tmp_path):
    i = tmp_path / "issues"
    _m(i / "A" / "audit" / "1", 11.34, 100)                      # non-lean: $0.1134 a unit
    _m(i / "B" / "audit" / "1", 0.77, 100, LEAN_CONFIG)          # lean: $0.0077
    _m(i / "C" / "audit" / "1", 0.30, 100, LEAN_CONFIG)          # lean: $0.0030
    other = dict(LEAN_CONFIG, k=8)
    _m(i / "D" / "audit" / "1", 5.00, 100, other)                # another lean_config: not this pool
    each, how = SC.per_unit("audit", issues_dir=i, config=LEAN_CONFIG)
    assert each == pytest.approx(0.0154)                         # the highest, 0.0077, x 2; not the mean
    assert "2 audit run(s)" in how and "B/1" in how and "x 2" in how
    assert SC.per_unit("audit", issues_dir=i, config=None)[0] == pytest.approx(0.2268)
    assert SC.per_unit("audit", issues_dir=i, config=other)[0] == pytest.approx(0.10)


def test_a_pool_with_nothing_measured_falls_back_and_says_so(tmp_path):
    i = tmp_path / "issues"
    _m(i / "A" / "audit" / "1", 11.34, 100)
    each, how = SC.per_unit("audit", issues_dir=i, config=LEAN_CONFIG)
    assert each == SC.FALLBACK["audit"][0] and "nothing measured" in how


def test_runs_with_no_spend_or_no_units_are_not_counted(tmp_path):
    i = tmp_path / "issues"
    _m(i / "A" / "audit" / "1", 0, 100, LEAN_CONFIG)
    _m(i / "B" / "audit" / "1", 0.5, 0, LEAN_CONFIG)
    _m(i / "C" / "audit" / "1", 0.2, 100, LEAN_CONFIG)
    assert SC.per_unit("audit", issues_dir=i, config=LEAN_CONFIG)[0] == pytest.approx(0.004)


def test_the_default_pool_is_this_runs_own_config(monkeypatch, tmp_path):
    i = tmp_path / "issues"
    _m(i / "A" / "audit" / "1", 11.34, 100)
    _m(i / "B" / "audit" / "1", 0.77, 100, LEAN_CONFIG)
    monkeypatch.delenv("WHU_LEAN", raising=False)
    assert SC.audit_config() is None
    assert SC.per_unit("audit", issues_dir=i)[0] == pytest.approx(0.2268)
    monkeypatch.setenv("WHU_LEAN", "1")
    assert SC.audit_config() == LEAN_CONFIG                      # what lean audits record today
    assert SC.per_unit("audit", issues_dir=i)[0] == pytest.approx(0.0154)


def test_the_manifest_records_the_config_the_estimate_pools_by():
    src = (WHU / "audit_stage.py").read_text(encoding="utf-8")
    assert 'manifest["lean_config"] = stage_cap.audit_config()' in src
    assert src.count('manifest["lean_config"]') == 1


def _real():
    i = ROOT / "issues"
    need = [i / n / "audit" / r / "manifest.json" for n, r, _ in (NONLEAN_MAX, LEAN_MAX, OT1_MAX)]
    if not all(p.exists() for p in need):
        pytest.skip("the audit records are local only (gitignored)")
    return i


def test_on_the_real_pools_and_02za(monkeypatch):
    """Lean orchestrated, lean and non-lean: the orchestrated runs record the same lean_config as the other lean
    runs, so by the ruling's rule they are one pool. 02za's 102 units come to about $1.57 (was $2.48)."""
    i = _real()
    lean_cfgs = []
    for f in i.glob("*/audit/*/manifest.json"):
        m = json.loads(f.read_text())
        if m.get("usd") and m.get("units") and m.get("lean_config") is not None:
            lean_cfgs.append((f.parts[-4].startswith("WHU-OT1-"), m["lean_config"]))
    assert any(o for o, _ in lean_cfgs) and any(not o for o, _ in lean_cfgs)
    assert all(c == LEAN_CONFIG for _, c in lean_cfgs)          # one lean pool, orchestrated runs included
    each, how = SC.per_unit("audit", issues_dir=i, config=None)
    assert each >= 2 * NONLEAN_MAX[2] - 1e-12                    # a later non-lean run can only raise it
    each, how = SC.per_unit("audit", issues_dir=i, config=LEAN_CONFIG)
    assert each >= 2 * LEAN_MAX[2] - 1e-12 and each >= 2 * OT1_MAX[2]
    if "%s/%s" % LEAN_MAX[:2] in how:                            # the pool as of 2026-11-25
        assert each == pytest.approx(0.015387, abs=1e-6)
        assert SC.estimate("audit", 102, issues_dir=i, config=LEAN_CONFIG)[0] == pytest.approx(1.57, abs=0.005)
    monkeypatch.setenv("WHU_LEAN", "1")
    assert SC.per_unit("audit", issues_dir=i)[0] == each       # an orchestrated (lean) run pools exactly so
