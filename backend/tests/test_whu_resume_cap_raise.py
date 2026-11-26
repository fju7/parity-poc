"""A resume may carry a run cap raised after its checkpoint (advisor's ruling 1 on Q1-01, 2026-11-26).

Q1-01's resume restored issue.json from the checkpoint and so put run_cap_usd back from $5.00 to $3.00. Now
run_cap_usd alone is carried: only upward, only within caps.json's per-issue cap, only with --cap-approval, and the
change is logged in the run record as a relay. Every other checkpointed record keeps its tamper check.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import orchestrator as O  # noqa: E402
from orch import checkpoint as CP  # noqa: E402
from orch import code_hash as CHH  # noqa: E402

SLUG = "whu-x"
APPROVAL = "approved by Fred via the advisor, 2026-11-26"
STEPS = ("provenance", "premise", "discover")


@pytest.fixture
def private(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_PRIVATE_ROOT", str(tmp_path / "private"))
    monkeypatch.setenv("WHU_LIBRARY_ROOT", str(tmp_path / "library"))


def _issue(cap, **extra):
    return json.dumps(dict({"slug": SLUG, "round": "orchestrator trial 1", "study": True, "run_cap_usd": cap,
                            "_run_cap_note": "the checkpoint's note"}, **extra), indent=2) + "\n"


def _ctx(tmp_path, monkeypatch, per_issue=5.0):
    from orch import chain as CH
    case = tmp_path / "issues" / "WHU-OT1-99-whu-x"
    (case / "orchestrator").mkdir(parents=True)
    (case / "issue.json").write_text(_issue(3.0))
    for k, s in enumerate(STEPS):
        (case / ("out_%s.json" % s)).write_text(json.dumps({"step": s}))
        CH.append(case, s, CH.snapshot(case, SLUG), {"f": k})
        CP.save(case, SLUG, k, s, CH.rows(case)[-1]["hashes"], ROOT)
    rec = {"result": "Not Ready: x", "steps": [{"step": s, "code": {"changed": False}, "code_hash": s}
                                                for s in STEPS] + [{"step": "acquire", "failed": "RunStop: x"}]}
    (case / "orchestrator" / "run_paid.json").write_text(json.dumps(rec))
    (case / "orchestrator" / "manifest.json").write_text(json.dumps({"code": {}}))
    caps = tmp_path / "backend" / "data" / "spend" / "caps.json"
    caps.parent.mkdir(parents=True)
    caps.write_text(json.dumps({"default_per_issue": 40, "study_per_issue": 50, "per_issue": {SLUG: per_issue}}))
    monkeypatch.setattr(CHH, "all_hashes", lambda steps, code: {s: s for s in STEPS})
    monkeypatch.setattr(O.MF, "changed", lambda a, b: [])
    monkeypatch.setattr(O.MF, "build", lambda *a, **k: {"code": {}})
    return SimpleNamespace(case=case, slug=SLUG, root=tmp_path, mode="paid")


def _live(ctx, cap, **extra):
    (ctx.case / "issue.json").write_text(_issue(cap, **extra))


def test_a_raised_cap_is_picked_up_and_logged_as_a_relay(tmp_path, monkeypatch, private):
    ctx = _ctx(tmp_path, monkeypatch)
    _live(ctx, 5.0, _run_cap_note="a newer note")
    pl = O.prepare_resume(ctx, "run_paid.json", APPROVAL)
    after = json.loads((ctx.case / "issue.json").read_text())
    assert after["run_cap_usd"] == 5.0
    assert after["_run_cap_note"] == "the checkpoint's note"           # only run_cap_usd is carried
    r = pl["cap_raise"]
    assert (r["old"], r["new"], r["approval_relayed"]) == (3.0, 5.0, APPROVAL)
    assert r["at"] and "not an attestation" in r["relay"]


def test_with_the_same_cap_nothing_is_carried(tmp_path, monkeypatch, private):
    ctx = _ctx(tmp_path, monkeypatch)
    assert O.prepare_resume(ctx, "run_paid.json")["cap_raise"] is None


def test_an_unapproved_raise_is_refused_before_anything_is_restored(tmp_path, monkeypatch, private):
    ctx = _ctx(tmp_path, monkeypatch)
    _live(ctx, 5.0)
    (ctx.case / "partial.json").write_text("the failed step's output")
    with pytest.raises(CP.ResumeRefused, match="no approval"):
        O.prepare_resume(ctx, "run_paid.json")
    assert (ctx.case / "partial.json").exists()                         # refused before the restore


def test_a_lowered_cap_is_refused(tmp_path, monkeypatch, private):
    ctx = _ctx(tmp_path, monkeypatch)
    _live(ctx, 2.0)
    with pytest.raises(CP.ResumeRefused, match="lowered"):
        O.prepare_resume(ctx, "run_paid.json", APPROVAL)


def test_a_raise_past_caps_json_is_refused(tmp_path, monkeypatch, private):
    ctx = _ctx(tmp_path, monkeypatch, per_issue=4.0)
    _live(ctx, 5.0)
    with pytest.raises(CP.ResumeRefused, match="past caps.json"):
        O.prepare_resume(ctx, "run_paid.json", APPROVAL)


def test_a_non_number_cap_is_refused(tmp_path, monkeypatch, private):
    ctx = _ctx(tmp_path, monkeypatch)
    _live(ctx, "5")
    with pytest.raises(CP.ResumeRefused, match="only a number"):
        O.prepare_resume(ctx, "run_paid.json", APPROVAL)


@pytest.mark.parametrize("tamper", ["issue", "other"])
def test_any_other_checkpoint_change_is_still_refused(tmp_path, monkeypatch, private, tamper):
    ctx = _ctx(tmp_path, monkeypatch)
    _live(ctx, 5.0)
    d = CP.root(SLUG) / "002-discover" / "case"
    if tamper == "issue":                   # the checkpoint's own issue.json edited: the tamper check refuses
        (d / "issue.json").write_text(_issue(5.0))
    else:
        (d / "out_discover.json").write_text("edited")
    with pytest.raises(CP.ResumeRefused, match="does not match the chain"):
        O.prepare_resume(ctx, "run_paid.json", APPROVAL)


def test_the_run_record_carries_the_change():
    src = (WHU / "orchestrator.py").read_text(encoding="utf-8")
    assert '"cap_raise": resumed.get("cap_raise")' in src and '"--cap-approval"' in src
