"""Fred's terms after orchestrator trial 1 attempt 23 (2026-11-24), at $0: the offline rehearsal (A1), resume from a
checkpoint (A2), the harness check on hashes not HEAD (B1), and the mechanical faults the rehearsal found (an unrun
advocate check passed; the preflight's STOP rows were cut off; the sandbox staged the whole tree)."""
import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
import orchestrator as O  # noqa: E402
import source_advocate as SA  # noqa: E402
from orch import checkpoint as CP  # noqa: E402
from orch import manifest as MF  # noqa: E402

RH = O.rehearsal_module()
PR = O.PR()
PLANS = WHU / "orch" / "rehearsal_plans"


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_REHEARSE_STATE", str(tmp_path / "state"))
    return tmp_path / "state"


def _plan(tmp_path, monkeypatch, plan):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan))
    monkeypatch.setenv("WHU_REHEARSE_PLAN", str(p))


# ----------------------------------------------------------------- B1: the harness check compares hashes, not HEAD

def _manifest(commit="aaa", code="1", doc="d", prompt="p"):
    return {"commit": commit, "documents": {"CLAUDE.md": doc, "backend/scripts/whatholdsup/audit_prompts/rule.md": prompt},
            "code": {"backend/scripts/whatholdsup/orchestrator.py": code}, "models": {}, "limits": {}, "tools": {}}


def test_the_runs_own_commits_do_not_count():
    """Attempt 23: HEAD moved with commit_3b and commit_8, and the preflight stopped the run."""
    assert MF.changed(_manifest(commit="5a16769"), _manifest(commit="29145ce")) == []
    assert "commit" not in MF.COMPARED


@pytest.mark.parametrize("new,what", [(_manifest(code="2"), "code"), (_manifest(doc="e"), "documents"),
                                      (_manifest(prompt="q"), "documents")])
def test_any_code_document_or_prompt_change_stops_the_run(new, what):
    got = MF.changed(_manifest(), new)
    assert got and got[0].startswith(what + ":")


def test_the_manifest_hashes_the_prompts_and_the_retry_module():
    m = MF.build(ROOT, [], {})
    assert any(k.startswith("backend/scripts/whatholdsup/audit_prompts/") for k in m["documents"])
    assert "backend/scripts/provider_retry.py" in m["code"]


# ----------------------------------------------------------------- the rehearsal's machinery

def test_rehearse_mode_is_refused_outside_a_sandbox(monkeypatch, capsys):
    monkeypatch.setenv("WHU_LEAN", "1")
    assert not (O.ROOT / O.SANDBOX_MARKER).exists()
    assert O.main(["run", "whu-lean-orch-t1-q1-02w", "--mode", "rehearse"]) == 2
    assert "only inside a Sandbox" in capsys.readouterr().out


def test_each_plan_entry_is_consumed_once_and_in_order(tmp_path, monkeypatch, state):
    _plan(tmp_path, monkeypatch, {"provider": [{"step": "draft", "error": "503"}, {"step": "draft", "error": "429",
                                                                                  "times": 2}]})
    got = [(RH.take("provider", "draft", "x") or {}).get("error") for _ in range(4)]
    assert got == ["503", "429", "429", None]
    assert RH.take("provider", "audit", "x") is None


def test_the_injected_provider_faults_are_the_ones_the_retry_retries():
    for err in ("503", "529", "429", "timeout", "connection"):
        assert PR.transient(RH.fault(err)), err


@pytest.mark.parametrize("shape,ok", [("prose_around", False), ("two_values", False), ("fenced_with_prose", False),
                                      ("mid_reply_revision", False), ("empty", False)])
def test_each_reply_shape_is_not_one_clean_json_object(shape, ok, tmp_path, monkeypatch, state):
    _plan(tmp_path, monkeypatch, {"shape": [{"step": "s", "shape": shape}]})
    text = RH.shaped('{"a": 1}', "s", "w")
    try:
        clean = json.loads(text) == {"a": 1}
    except ValueError:
        clean = False
    assert clean is ok and RH.shaped('{"a": 1}', "s", "w") == '{"a": 1}'      # consumed: the re-ask is clean


def test_narration_falls_between_searches_and_the_reply_is_the_text_after_the_last(tmp_path, monkeypatch, state):
    """Attempts 12-22's shape. factcheck_draft._final_text must give exactly the JSON."""
    _plan(tmp_path, monkeypatch, {"narrate_searches": True})
    blocks, n = RH._blocks('{"studies": []}', True, "gate", "recency")
    sys.path.insert(0, str(ROOT / "backend" / "scripts" / "signal"))
    import factcheck_draft as fc
    reply, narration = fc._final_text(SimpleNamespace(content=blocks))
    assert reply == '{"studies": []}' and len(narration) == 2 and n == 2


def test_the_http_cache_records_then_replays_then_refuses_offline(tmp_path, monkeypatch, state):
    monkeypatch.setenv("WHU_REHEARSE_HTTP", str(tmp_path / "http"))
    calls = []

    def live(req, *a, **k):
        calls.append(req)
        return RH._Resp(b'{"hitCount": 1}', 200, {"Content-Type": "application/json"}, req)
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=x"
    assert RH.cached_urlopen(live, url).read() == b'{"hitCount": 1}'
    assert RH.cached_urlopen(live, url).read() == b'{"hitCount": 1}' and len(calls) == 1      # replayed
    monkeypatch.setenv("WHU_REHEARSE_OFFLINE", "1")
    with pytest.raises(urllib.error.URLError, match="not recorded"):
        RH.cached_urlopen(live, url + "&new=1")


def test_a_planned_registry_fault_is_a_urlerror_the_registry_retry_retries(tmp_path, monkeypatch, state):
    from orch import registry_http as REG
    _plan(tmp_path, monkeypatch, {"registry": [{"step": "*", "error": "timed out"}]})
    monkeypatch.setenv("WHU_REHEARSE_HTTP", str(tmp_path / "http"))
    with pytest.raises(urllib.error.URLError) as e:
        RH.cached_urlopen(lambda *a, **k: None, "https://api.crossref.org/works/x")
    assert REG.transient(e.value)


def test_an_unknown_prompt_is_kept_and_answered_empty(state):
    assert RH.generate("gate", "nothing", "a prompt no generator knows") == ""
    assert list((state / "unknown").glob("*.txt"))


def test_the_stub_client_reply_carries_what_the_meter_reads(tmp_path, monkeypatch, state):
    msg = RH.AnthropicStub().messages.create(model="claude-opus-5-5", max_tokens=10,
                                             messages=[{"role": "user", "content": "x" * 400}])
    assert msg.model == "claude-opus-5-5" and msg.usage.input_tokens == 100 and msg.stop_reason == "end_turn"


# ----------------------------------------------------------------- mechanical faults the rehearsal found

def test_an_advocate_call_with_no_usable_reply_is_an_unrun_check():
    """Rehearsal 3: the advocate's empty reply, after its re-ask, left "-> 0 objections" and exit 0."""
    briefs = [{"source": "S001", "failed": True, "objections": []}, {"source": "S004", "objections": []}]
    assert SA.unrun_sources(briefs) == ["S001"] and SA.UNRUN_EXIT not in (0, 1, 3)
    src = (WHU / "source_advocate.py").read_text(encoding="utf-8")
    assert "if unrun and _strict():" in src and "return UNRUN_EXIT" in src


def test_the_preflight_keeps_every_stop_row(monkeypatch, tmp_path):
    case = tmp_path / "case"
    (case / "orchestrator").mkdir(parents=True)
    (case / "orchestrator" / "manifest.json").write_text("{}")
    out = "\n".join(["   STOP  row %d  reason" % i for i in range(40)] + ["x" * 4000, "BLOCKED — fix every STOP above."])
    monkeypatch.setattr(O.MF, "changed", lambda a, b: [])
    monkeypatch.setattr(O.MF, "build", lambda *a, **k: {})
    monkeypatch.setattr(O.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=out, returncode=1))
    ctx = SimpleNamespace(case=case, slug="x", root=tmp_path, mode="paid", env=lambda step: {})
    got = O.code_preflight(ctx, SimpleNamespace(name="preflight"))
    assert got["outcome"] == "Not Ready" and len(got["stops"]) == 40 and got["stops"][0] == "STOP row 0 reason"


def test_a_rehearsal_commit_is_never_pushed(monkeypatch, tmp_path):
    seen = []

    def fake(argv, **k):
        seen.append(argv)
        if "diff" in argv:
            return SimpleNamespace(stdout="issues/WHU-X/a.json\n", returncode=0)
        return SimpleNamespace(stdout="abc123def456\n", returncode=0)
    monkeypatch.setattr(O.subprocess, "run", fake)
    ctx = SimpleNamespace(mode=O.REHEARSE, root=tmp_path, case=tmp_path / "issues/WHU-X", slug="x", first=None,
                          rel=lambda p: "issues/WHU-X")
    got = O.code_commit(ctx, SimpleNamespace(name="commit_3b"))
    assert not any("push" in a for a in seen) and got["head"] == "abc123def456" and ctx.first == "abc123def456"


# ----------------------------------------------------------------- A2: checkpoints and resume

def _case(tmp_path, steps=("provenance", "premise", "discover")):
    from orch import chain as CH
    case = tmp_path / "issues" / "WHU-OT1-99-whu-x"
    (case / "orchestrator").mkdir(parents=True)
    for k, s in enumerate(steps):
        (case / ("out_%s.json" % s)).write_text(json.dumps({"step": s}))
        CH.append(case, s, CH.snapshot(case, "whu-x"), {"f": k})
        (case / "study_log.md").write_text("logged %s\n" % s)      # written just after the row, as run_step does
        CP.save(case, "whu-x", k, s, CH.rows(case)[-1]["hashes"], ROOT)
    return case


@pytest.fixture
def private(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_PRIVATE_ROOT", str(tmp_path / "private"))
    monkeypatch.setenv("WHU_LIBRARY_ROOT", str(tmp_path / "library"))


NAMES = ["provenance", "premise", "discover", "acquire", "draft"]


def _record(done, failed):
    return {"result": "Not Ready: x", "steps": [{"step": s, "code": {"changed": False}} for s in done] +
            [{"step": failed, "failed": "RunStop: x"}]}


def test_resume_verifies_the_checkpoint_and_restores_what_the_failed_step_wrote(tmp_path, private):
    case = _case(tmp_path)
    (case / "partial_from_acquire.json").write_text("half")              # the failed step's output
    (case / "out_discover.json").write_text("overwritten by the failed step")
    pl = CP.plan(case, "whu-x", _record(["provenance", "premise", "discover"], "acquire"), NAMES, set(), 2)
    assert pl["resume_at"] == "acquire" and pl["index"] == 3 and pl["frozen"] == {"f": 2}
    CP.restore(case, "whu-x", pl["checkpoint"], chain=pl["chain"])
    assert not (case / "partial_from_acquire.json").exists()
    assert json.loads((case / "out_discover.json").read_text()) == {"step": "discover"}


def test_a_tampered_checkpoint_refuses_the_resume(tmp_path, private):
    case = _case(tmp_path)
    cp = tmp_path / "private" / "checkpoints" / "whu-x" / "002-discover" / "case" / "out_discover.json"
    cp.write_text("tampered")
    with pytest.raises(CP.ResumeRefused, match="does not match"):
        CP.plan(case, "whu-x", _record(["provenance", "premise", "discover"], "acquire"), NAMES, set(), 2)


def test_a_record_that_disagrees_with_the_chain_refuses_the_resume(tmp_path, private):
    case = _case(tmp_path)
    with pytest.raises(CP.ResumeRefused, match="not the record's completed steps"):
        CP.plan(case, "whu-x", _record(["provenance"], "premise"), NAMES, set(), 2)


def test_a_run_with_no_failed_step_is_not_resumed(tmp_path, private):
    case = _case(tmp_path)
    with pytest.raises(CP.ResumeRefused, match="no failed step"):
        CP.plan(case, "whu-x", {"result": "Ready.", "steps": [{"step": "provenance"}]}, NAMES, set(), 2)


def test_an_outage_after_a_step_finished_resumes_at_that_step(tmp_path, private):
    """The chain has the outage step's row but there is no checkpoint for it: the row is dropped."""
    from orch import chain as CH
    case = _case(tmp_path)
    CH.append(case, "acquire", CH.snapshot(case, "whu-x"), {})
    pl = CP.plan(case, "whu-x", _record(["provenance", "premise", "discover"], "acquire"), NAMES, set(), 2)
    assert pl["resume_at"] == "acquire" and [r["step"] for r in pl["chain"]] == ["provenance", "premise", "discover"]
    CP.restore(case, "whu-x", pl["checkpoint"], chain=pl["chain"])
    assert [r["step"] for r in CH.rows(case)] == ["provenance", "premise", "discover"]


def test_the_repeat_count_is_rebuilt_as_the_loop_had_it():
    done = [{"step": "findings", "code": {"changed": False}}, {"step": "audit", "code": {"changed": True}},
            {"step": "changecheck", "code": {"changed": False}}, {"step": "findings", "code": {"changed": False}}]
    rec = {"result": "x", "steps": done + [{"step": "audit", "failed": "x"}]}
    # plan() refuses without a chain, so check the rebuild directly through a minimal chain
    repeats, changed = 0, False
    for s in done:
        if s["step"] in {"findings", "audit", "changecheck"} and s["code"]["changed"] and s["step"] != "findings":
            changed = True
        if s["step"] == "changecheck" and changed and repeats < 2:
            repeats, changed = repeats + 1, False
    assert (repeats, changed) == (1, False) and rec["steps"][-1]["failed"]


def test_a_checkpoint_may_never_be_inside_the_repository(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_PRIVATE_ROOT", str(ROOT / "backend" / "data"))
    case = tmp_path / "issues" / "WHU-OT1-99-whu-x"
    case.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="inside the repository"):
        CP.save(case, "whu-x", 0, "provenance", {}, ROOT)


# ----------------------------------------------------------------- the full rehearsals (minutes each; -m rehearsal)

def _rehearse(tmp_path, plan, resume_plan=None):
    state = tmp_path / "state"
    argv = [str(ROOT / "backend/venv/bin/python3"), str(WHU / "orchestrator.py"), "rehearse", "whu-lean-orch-t1-q1-02w",
            "--state", str(state), "--offline", "--plan", str(PLANS / plan)]
    if resume_plan:
        argv += ["--then-resume-plan", str(PLANS / resume_plan)]
    subprocess.run(argv, cwd=str(ROOT), env=dict(__import__("os").environ, WHU_LEAN="1"), capture_output=True,
                   timeout=2400)
    return json.loads((state / "case" / "orchestrator" / "run_rehearse.json").read_text())


@pytest.mark.rehearsal
def test_rehearsal_every_shape_and_fault_recovered_and_every_step_ran(tmp_path):
    r = _rehearse(tmp_path, "shapes_and_faults.json")
    assert r["steps"][-1]["step"] == "archive" and not any(s.get("failed") for s in r["steps"])
    out = {s["step"]: (s.get("code") or {}).get("outcome") for s in r["steps"]}
    assert out["belief"] == "1 outlet(s) verified of 2 proposed"
    assert out["premise_reading"] == "sources show verified; direction narrows; kill condition survived"
    assert out["quotations"].endswith(", 0 unmatched")
    pf = [s for s in r["steps"] if s["step"] == "preflight"][0]["code"]
    assert pf["stops"] == [] and pf["outcome"] == "Ready."


@pytest.mark.rehearsal
def test_rehearsal_a_registry_outage_stops_the_run(tmp_path):
    assert "registry unavailable; run again later" in _rehearse(tmp_path, "registry_outage.json")["result"]


@pytest.mark.rehearsal
def test_rehearsal_a_model_outage_stops_then_the_resume_finishes(tmp_path):
    r = _rehearse(tmp_path, "model_outage.json", "none.json")
    assert "model unavailable; run again later" in r["resumed"]["prior_result"]
    assert r["resumed"]["at"] == "overstatement" and r["steps"][-1]["step"] == "archive"


# ----------------------------------------------------------------- resume after a code change (ruling 3, A/B build)

def test_every_step_records_a_code_hash_that_moves_with_its_code(tmp_path, monkeypatch):
    from orch import code_hash as CHH
    from orch import steps as ST
    h = CHH.all_hashes(ST.STEPS, O.STEP_CODE)
    assert set(h) == set(ST.NAMES) and all(len(v) == 64 for v in h.values())
    gate = ST.BY_NAME["gate"]
    files = {p.name for p in CHH.step_files(gate, O.STEP_CODE)}
    assert {"factcheck_draft.py", "orchestrator.py", "spend_ledger.py", "provider_retry.py"} <= files


def test_resume_keeps_the_steps_before_the_earliest_changed_one():
    done = [{"step": "provenance", "code_hash": "a"}, {"step": "premise", "code_hash": "b"},
            {"step": "discover", "code_hash": "c"}]
    assert O.resume_keep(done, {"provenance": "a", "premise": "b", "discover": "c"}) == 3
    assert O.resume_keep(done, {"provenance": "a", "premise": "B", "discover": "c"}) == 1
    assert O.resume_keep(done, {"provenance": "A", "premise": "b", "discover": "c"}) == 0
    assert O.resume_keep([{"step": "provenance"}], {"provenance": "a"}) == 0          # no hash: changed


def _resumable(tmp_path, monkeypatch, trial=True):
    case = _case(tmp_path)
    (case / "issue.json").write_text(json.dumps({"slug": "whu-x", "round": "orchestrator trial 1" if trial else
                                                 "new-questions test"}))
    from orch import chain as CH
    rows = CH.rows(case)
    rec = {"result": "Not Ready: x", "steps": [{"step": r["step"], "code": {"changed": False}, "code_hash": r["step"]}
                                                for r in rows] + [{"step": "acquire", "failed": "RunStop: x"}]}
    (case / "orchestrator" / "run_paid.json").write_text(json.dumps(rec))
    (case / "orchestrator" / "manifest.json").write_text(json.dumps({"code": {"a.py": "1"}}))
    # each checkpoint was saved before run_paid.json existed: keep that file out of the comparison
    monkeypatch.setattr(O.CH, "ALWAYS_OWNED", O.CH.ALWAYS_OWNED)
    ctx = SimpleNamespace(case=case, slug="whu-x", root=tmp_path, mode="paid")
    return ctx


def _hashes(monkeypatch, current, drift=()):
    from orch import code_hash as CHH
    monkeypatch.setattr(CHH, "all_hashes", lambda steps, code: dict(current))
    monkeypatch.setattr(O.MF, "changed", lambda a, b: list(drift))
    monkeypatch.setattr(O.MF, "build", lambda *a, **k: {"code": {}})


SAME = {"provenance": "provenance", "premise": "premise", "discover": "discover"}


def test_a_trial_resume_with_no_code_change_restarts_at_the_failed_step(tmp_path, monkeypatch, private):
    ctx = _resumable(tmp_path, monkeypatch)
    _hashes(monkeypatch, SAME)
    pl = O.prepare_resume(ctx, "run_paid.json")
    assert pl["resume_at"] == "acquire" and pl["code_changed_from"] is None


def test_a_trial_resume_after_a_code_change_restarts_at_the_earliest_changed_step(tmp_path, monkeypatch, private):
    ctx = _resumable(tmp_path, monkeypatch)
    _hashes(monkeypatch, dict(SAME, premise="changed"))
    pl = O.prepare_resume(ctx, "run_paid.json")
    assert pl["resume_at"] == "premise" and pl["code_changed_from"] == "premise" and pl["seq"] == 0
    assert (ctx.case / "orchestrator" / "runs" / "01-manifest.json").exists()     # both manifests kept


def test_a_trial_whose_first_step_changed_starts_afresh(tmp_path, monkeypatch, private):
    ctx = _resumable(tmp_path, monkeypatch)
    _hashes(monkeypatch, dict(SAME, provenance="changed"))
    with pytest.raises(CP.ResumeRefused, match="start a fresh attempt"):
        O.prepare_resume(ctx, "run_paid.json")


@pytest.mark.parametrize("current,drift", [(dict(SAME, discover="changed"), ()), (SAME, ("documents: CLAUDE.md",))])
def test_a_scored_run_never_resumes_across_a_code_change(tmp_path, monkeypatch, private, current, drift):
    ctx = _resumable(tmp_path, monkeypatch, trial=False)
    _hashes(monkeypatch, current, drift)
    with pytest.raises(CP.ResumeRefused, match="one frozen code version"):
        O.prepare_resume(ctx, "run_paid.json")


def test_a_scored_run_with_no_change_resumes_on_its_one_manifest(tmp_path, monkeypatch, private):
    ctx = _resumable(tmp_path, monkeypatch, trial=False)
    _hashes(monkeypatch, SAME)
    before = (ctx.case / "orchestrator" / "manifest.json").read_text()
    pl = O.prepare_resume(ctx, "run_paid.json")
    assert pl["resume_at"] == "acquire"
    assert (ctx.case / "orchestrator" / "manifest.json").read_text() == before
