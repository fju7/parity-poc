"""Fix 2, step 8: the omission ruling's stage cap estimate (post-study, 2026-10-27)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import ruling as R                        # noqa: E402
import stage_cap as SC                    # noqa: E402
import test_whatholdsup_fix2_ruling as T  # noqa: E402


def _log(d, recs):
    p = d / "WHU-X01-x" / "rulings" / "rulings.jsonl"
    p.parent.mkdir(parents=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in recs))


def test_the_omission_estimate_is_the_mean_of_omission_rulings_only(tmp_path):
    _log(tmp_path, [{"ruling_kind": "omission", "usage": {"usd": 0.04}},
                    {"ruling_kind": "omission", "usage": {"usd": 0.02}},
                    {"ruling_kind": "advocate", "usage": {"usd": 0.50}}])
    each, how = SC.per_unit("omissions", entries=[], issues_dir=tmp_path)
    assert each == pytest.approx(0.03) and "2 logged omission ruling(s)" in how
    each_all, _ = SC.per_unit("rulings", entries=[], issues_dir=tmp_path)
    assert each_all == pytest.approx(0.56 / 3)


def test_with_nothing_measured_the_design_figure_is_used(tmp_path):
    each, how = SC.per_unit("omissions", entries=[], issues_dir=tmp_path)
    assert each == 0.03 and "nothing measured yet" in how
    assert "omissions" in SC.STAGES and SC.UNIT["omissions"] == "omission unit"


def test_a_reask_counts_twice(tmp_path, monkeypatch):
    T._case(tmp_path, monkeypatch, [T._obj(T.BOUND), T._obj(T.OMITTED)])     # the first will be re-asked
    assert R.omission_units(T.SLUG, 2, case=tmp_path, held=T.HELD, rows=T.ROWS) == 2 + R.REASK_UNITS


def test_the_omissions_mode_is_capped_as_omissions(monkeypatch):
    seen = []

    class Stop(Exception):
        pass

    def guard(stage, slug, units):
        seen.append((stage, units))
        raise Stop()
    monkeypatch.setattr(R, "require_study", lambda slug, P=None: None)
    monkeypatch.setattr(R, "pending", lambda mode, slug, P=None: 4)
    monkeypatch.setattr(R, "unsampled", lambda log, cons, kind: [])
    monkeypatch.setattr(R, "log_path", lambda slug: Path("/nonexistent/rulings.jsonl"))
    monkeypatch.setattr(R, "omission_units", lambda slug, n, **kw: n + 100)
    monkeypatch.setattr(SC, "guard", guard)
    with pytest.raises(Stop):
        R.main(["omissions", "x"])
    with pytest.raises(Stop):
        R.main(["advocate", "x"])
    assert seen[0][0] == "omissions" and seen[0][1] >= 104
    assert seen[1][0] == "rulings" and seen[1][1] < 100
