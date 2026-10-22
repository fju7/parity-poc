"""The study's frozen files are pinned by sha256 (protocol rev 38): RUN.md,
the ruling prompts (rule.md, rule_cite.md and the two group prompts), the
audit's reader and summary prompts, and the blinding list. Code refuses to
run on a changed one, as for M1 and M2. A change is simulated by changing the
recorded hash, never the frozen file. No model is called."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
STUDY = ROOT / "study" / "whu-reliability"
sys.path.insert(0, str(WHU))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


import stage_cap  # noqa: E402
FZ = stage_cap._load_frozen()


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_every_frozen_file_is_as_recorded():
    assert FZ.mismatches() == []
    assert set(FZ.FROZEN_SHA256) == {
        "backend/scripts/whatholdsup/audit_prompts/%s" % n for n in
        ("rule.md", "rule_cite.md", "rule_group.md", "rule_group_cite.md", "read.md", "summary.md")} | {
        "study/whu-reliability/RUN.md"}
    import ruling as R
    for name, want in R.GROUP_PROMPT_SHA256.items():                 # one record, two places, agreeing
        assert FZ.FROZEN_SHA256["backend/scripts/whatholdsup/audit_prompts/" + name] == want
    B = _load("blind_frozen_t", STUDY / "blinding" / "blind.py")
    assert B.PHRASES_SHA256 == _sha(STUDY / "blinding" / "blind_phrases.json")


@pytest.fixture
def changed(monkeypatch):
    """Record a different hash for REL: the file now reads as changed."""
    def go(rel):
        monkeypatch.setitem(FZ.FROZEN_SHA256, rel, "0" * 64)
    return go


def test_a_changed_ruling_prompt_is_refused_before_any_call(changed):
    import ruling as R
    changed("backend/scripts/whatholdsup/audit_prompts/rule.md")
    p = {k: "x" for k in R.RULE_FIELDS}
    with pytest.raises(FZ.FrozenFileChanged):
        R.build_prompt("conclusion", p)
    changed("backend/scripts/whatholdsup/audit_prompts/rule_cite.md")
    with pytest.raises(FZ.FrozenFileChanged):
        R.build_prompt("gate", p)
    changed("backend/scripts/whatholdsup/audit_prompts/rule_group.md")
    with pytest.raises(FZ.FrozenFileChanged):
        R.build_prompt("conclusion", {k: "x" for k in R.GROUP_FIELDS}, grouped=True)


@pytest.mark.parametrize("name", ["read.md", "summary.md", "rule.md"])
def test_a_changed_audit_prompt_stops_the_audit_before_any_call(changed, tmp_path, name):
    A = _load("audit_stage_frozen_t", WHU / "audit_stage.py")
    T = _load("audit_fixtures_frozen_t", ROOT / "backend" / "tests" / "test_whatholdsup_audit_stage.py")
    changed("backend/scripts/whatholdsup/audit_prompts/" + name)
    fake = T.FakeModel()
    u = T._unit("u1", "The study found 226 of 795 detected an adenoma (28.4%).")
    us = [u] if name != "summary.md" else [dict(u, part="card")]
    m = A.run("demo", out_dir=tmp_path, ask=fake, held=T.HELD, unit_list=us, cap=1.0, licensed=set())
    if name == "rule.md":
        assert m["status"] == "failed" and "frozen" in m["failure"]
        assert not any("THE FINDING:" in p for p in fake.prompts)       # no ruling call
    else:
        assert m["status"] == "failed" and "frozen" in m["failure"] and fake.prompts == []


def test_a_paid_stage_of_a_study_issue_does_not_start_on_a_changed_run_md(changed, monkeypatch, capsys):
    changed("study/whu-reliability/RUN.md")
    monkeypatch.setattr(FZ, "is_study", lambda slug: True)
    monkeypatch.setattr(stage_cap, "check", lambda *a: pytest.fail("the cap was consulted"))
    with pytest.raises(SystemExit) as e:
        stage_cap.guard("audit", "some-study", 10)
    assert e.value.code == 6 and "RUN.md" in capsys.readouterr().err


def test_a_published_issue_is_not_held_to_run_md(changed, monkeypatch):
    changed("study/whu-reliability/RUN.md")
    monkeypatch.setattr(FZ, "is_study", lambda slug: False)
    monkeypatch.setattr(stage_cap, "check", lambda *a: {"estimate": 0.0, "how": "t", "day_left": 1.0,
                                                        "issue_left": 1.0})
    stage_cap.guard("audit", "melanoma", 1)                        # no exit


def test_a_changed_blinding_list_is_refused(tmp_path, monkeypatch):
    B = _load("blind_frozen_t2", STUDY / "blinding" / "blind.py")
    f = tmp_path / "blind_phrases.json"
    f.write_text(json.dumps(dict(json.loads((STUDY / "blinding" / "blind_phrases.json").read_text()), extra=1)))
    monkeypatch.setattr(B, "PHRASES_FILE", f)
    with pytest.raises(SystemExit) as e:
        B.load_phrases()
    assert "blind_phrases.json" in str(e.value)


def test_is_study_reads_issue_json():
    assert FZ.is_study("greenhouse-gas-emissions-growth") is True
    assert FZ.is_study("melanoma") is False
