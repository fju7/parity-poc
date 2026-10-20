"""The source advocate saves as it goes and resumes after a cap stop (2026-10-20).

On 2026-10-20 WHU-P02's advocate drafted 27 objections for $4.28 and was
stopped by the day cap during its quotation check, before writing anything.
Now each source's brief and each quotation check is saved when it completes;
a cap stop leaves a run directory marked "stopped"; `run --resume RUN_DIR`
refuses if any input changed and never redoes saved work. The cap here is a
stub: no model is called and nothing is spent.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("source_advocate_resume_t", WHU / "source_advocate.py")
SA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SA)

HELD = {"S1": "Alpha says the effect was 2 kg.", "S2": "Beta reports 30 participants.",
        "S3": "Gamma found no difference."}


class OverCap(Exception):
    """Named as spend_ledger's is: the advocate recognises a cap stop by name."""


class Model:
    """fc.call stand-in. Allows `budget` calls, then raises OverCap."""

    def __init__(self, budget):
        self.budget, self.calls = budget, []

    def __call__(self, system, user, search=False, label="", **kw):
        if len(self.calls) >= self.budget:
            raise OverCap("$25.00 has been spent today against a $25.00 daily cap")
        self.calls.append(label)
        sid = label.split(":")[-1]
        if label.startswith("advocate-requote:"):
            return {"source_says": HELD[sid].split(" ", 1)[1], "locator": "p1"}
        says = {"S1": "the effect was 2 kg", "S2": "Beta reports 31 participants", "S3": "no difference"}[sid]
        return {"objections": [{"severity": "SERIOUS", "claim_quoted": "c-" + sid, "objection": "o",
                                "why": "w", "source_says": says}]}


@pytest.fixture
def case(tmp_path, monkeypatch):
    d = tmp_path / "issues" / "WHU-X-demo"
    d.mkdir(parents=True)
    (tmp_path / "page.html").write_text("<html><body><p>Alpha Beta Gamma.</p></body></html>")
    doc = {"sources": [{"id": s, "title": "T" + s, "type": "primary"} for s in ("S1", "S2", "S3")]}
    monkeypatch.setattr(SA, "ROOT", tmp_path)
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: d)
    monkeypatch.setattr(SA.sl, "load", lambda slug: doc)
    monkeypatch.setattr(SA.sl, "access_of", lambda s: {"state": "machine-readable"})
    monkeypatch.setattr(SA, "mentions", lambda text, s: ["a sentence about " + s["id"]])
    import audit_stage, stage_cap
    monkeypatch.setattr(audit_stage, "held_for_audit", lambda slug: dict(HELD))
    guarded = []
    monkeypatch.setattr(stage_cap, "guard", lambda stage, slug, units: guarded.append((stage, units)))
    return types.SimpleNamespace(dir=d, root=tmp_path, doc=doc, guarded=guarded)


def _args(**kw):
    return types.SimpleNamespace(**dict(dict(slug="demo", page="page.html", only=None, day="2026-10-21",
                                             resume=None), **kw))


def _run(monkeypatch, model, **kw):
    monkeypatch.setattr(SA.fc, "call", model)
    return SA.cmd_run(_args(**kw))


def _run_dir(case):
    return sorted((case.dir / "advocate" / "runs").iterdir())[-1]


def test_a_cap_stop_in_the_quotation_check_resumes_without_redoing_anything(case, monkeypatch):
    # three advocate calls succeed; the S2 re-ask hits the cap
    m1 = Model(budget=3)
    assert _run(monkeypatch, m1) == 3
    rd = _run_dir(case)
    assert json.loads((rd / "state.json").read_text())["status"] == "stopped"
    saved = [json.loads(l) for l in (rd / "briefs.jsonl").read_text().splitlines()]
    assert [b["source"] for b in saved] == ["S1", "S2", "S3"]              # every objection kept
    checks = [json.loads(l) for l in (rd / "quote_checks.jsonl").read_text().splitlines()]
    assert [c["key"] for c in checks] == ["S1#0"]                          # the one decided before the stop
    assert not (case.dir / "advocate" / "2026-10-21-briefs.json").exists()
    # resume: only the S2 re-ask is paid for; nothing saved is asked again
    m2 = Model(budget=10)
    assert _run(monkeypatch, m2, day=None, resume=str(rd)) == 0
    assert m2.calls == ["advocate-requote:S2"]
    assert case.guarded[-1] == ("advocate", 0)                             # no source left to read
    out = json.loads((case.dir / "advocate" / "2026-10-21-briefs.json").read_text())
    qc = {b["source"]: b["objections"][0]["quotation_check"] for b in out}
    assert qc["S1"] == {"in_held_text": True, "asked": 1}                  # carried from the saved check
    assert qc["S2"]["in_held_text"] is True and qc["S2"]["asked"] == 2
    assert (case.dir / "advocate" / "2026-10-21-adjudication.md").exists()
    assert json.loads((rd / "state.json").read_text())["status"] == "complete"


def test_a_cap_stop_between_sources_resumes_with_the_sources_not_yet_read(case, monkeypatch):
    m1 = Model(budget=1)
    assert _run(monkeypatch, m1) == 3
    rd = _run_dir(case)
    assert [json.loads(l)["source"] for l in (rd / "briefs.jsonl").read_text().splitlines()] == ["S1"]
    m2 = Model(budget=10)
    assert _run(monkeypatch, m2, day=None, resume=rd.name) == 0
    assert m2.calls == ["advocate:S2", "advocate:S3", "advocate-requote:S2"]
    assert case.guarded[-1] == ("advocate", 2)                             # the estimate covers what is left


def test_a_resume_refuses_if_any_input_changed(case, monkeypatch):
    assert _run(monkeypatch, Model(budget=1)) == 3
    rd = _run_dir(case)
    (case.root / "page.html").write_text("<html><body><p>Alpha Beta Gamma, changed.</p></body></html>")
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, Model(budget=10), day=None, resume=str(rd))
    assert "page_body_sha256" in str(e.value)
    (case.root / "page.html").write_text("<html><body><p>Alpha Beta Gamma.</p></body></html>")
    import audit_stage
    monkeypatch.setattr(audit_stage, "held_for_audit", lambda slug: dict(HELD, S3="Gamma, re-extracted."))
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, Model(budget=10), day=None, resume=str(rd))
    assert "held_sha256" in str(e.value)


def test_only_a_stopped_run_resumes(case, monkeypatch):
    assert _run(monkeypatch, Model(budget=10)) == 0
    with pytest.raises(SystemExit) as e:
        _run(monkeypatch, Model(budget=10), day=None, resume=str(_run_dir(case)))
    assert "complete" in str(e.value)


def test_another_failure_is_not_a_stop(case, monkeypatch):
    def broken(*a, **k):
        raise ValueError("not a cap")
    monkeypatch.setattr(SA.fc, "call", broken)
    with pytest.raises(ValueError):
        SA.cmd_run(_args())
    assert json.loads((_run_dir(case) / "state.json").read_text())["status"] == "failed"
