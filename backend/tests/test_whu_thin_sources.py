"""The held-source minimum (advisor's ruling 3 on the design review of 2026-11-26; thin_sources.py).

At least 2 distinct works held in full text, at least one a review or synthesis, checked straight after acquire;
below it the run ends "Insufficient sources: N of M confirmed sources held (minimum 2); not drafted" -- an honest
outcome, not Not Ready, and nothing is drafted. Registries are faked; nothing is fetched or spent.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import thin_sources as TS  # noqa: E402


def _src(i, held=True, typ="review", doi=None, title=None):
    return {"id": "S%03d" % i, "type": typ, "title": title or "Work %d" % i, "doi": doi,
            "access": {"state": "full_text_held" if held else "blocked"}}


def test_one_held_work_is_insufficient_with_the_ruled_sentence():
    doc = {"sources": [_src(1), _src(2, held=False), _src(3, held=False), _src(4, held=False)]}
    assert TS.shortfall(doc) == "Insufficient sources: 1 of 4 confirmed sources held (minimum 2); not drafted"


def test_two_held_works_one_a_review_pass():
    assert TS.shortfall({"sources": [_src(1, typ="primary"), _src(2, typ="synthesis")]}) is None


def test_two_copies_of_one_work_count_once():
    doc = {"sources": [_src(1, doi="10.1/X"), _src(2, doi="10.1/x"), _src(3, held=False)]}
    assert TS.shortfall(doc).startswith("Insufficient sources: 1 of 3 confirmed sources held (minimum 2)")


def test_two_held_works_with_no_review_or_synthesis_are_insufficient():
    got = TS.shortfall({"sources": [_src(1, typ="primary"), _src(2, typ="guideline")]})
    assert got == ("Insufficient sources: 2 of 2 confirmed sources held (minimum 2); none is a review or synthesis; "
                   "not drafted")


def test_an_abstract_or_blocked_source_is_not_held_in_full_text():
    a = _src(2)
    a["access"]["state"] = "abstract_held"
    b = _src(3)
    b["access"]["not_held"] = {"line": "retracted", "why": "x"}
    assert TS.shortfall({"sources": [_src(1), a, b]}).startswith("Insufficient sources: 1 of 3")


@pytest.mark.parametrize("held_states", [(True, False, False), (True, True, False)])
def test_acquire_ends_insufficient_or_goes_on(tmp_path, monkeypatch, held_states):
    import orchestrator as O
    from orch import corrections as CR
    from orch import results as RS
    case = tmp_path / "issues" / "WHU-T-thin"
    case.mkdir(parents=True)
    srcs = [_src(i + 1, held=h) for i, h in enumerate(held_states)]
    (case / "sources.json").write_text(json.dumps({"sources": srcs}))
    monkeypatch.setattr(CR, "status", lambda s, *a: {"retracted": False, "concern": False, "why": [], "answered": [],
                                                    "corrections": [], "registries": []})
    monkeypatch.setattr(RS, "stop_reason", lambda held: None)
    ctx = types.SimpleNamespace(case=case, slug="thin")
    if sum(held_states) < 2:
        with pytest.raises(O.InsufficientSources) as e:
            O.code_acquire(ctx, None)
        assert str(e.value) == "Insufficient sources: 1 of 3 confirmed sources held (minimum 2); not drafted"
        assert isinstance(e.value, O.RunStop)
    else:
        out = O.code_acquire(ctx, None)
        assert out["outcome"].startswith("2 held")


def test_the_run_records_the_outcome_as_it_is_and_exits_3():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    i, j = src.index("except InsufficientSources as e:"), src.index("except (RunStop, StepFailed, Busy) as e:")
    assert i < j                                         # caught before the Not Ready handler
    assert 'result = str(e)' in src[i:j]
    assert "return 3" in src and 'INSUFFICIENT = "Insufficient sources:"' in src
