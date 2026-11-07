"""The WHU orchestrator and the post-test list (docs/whu-orchestrator.md). Offline: no model call, no network,
the real ledger and records untouched (each test that could touch them asserts so)."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "signal"))
LEDGER = ROOT / "backend" / "data" / "spend" / "ledger.jsonl"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def _ledger_module():
    sp = importlib.util.spec_from_file_location("spend_ledger_t", ROOT / "backend/scripts/spend_ledger.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


@pytest.fixture
def S(monkeypatch, tmp_path):
    m = _ledger_module()
    monkeypatch.setattr(m, "entries", lambda: [])
    monkeypatch.setattr(m, "issue_meta", lambda issue: {"orchestrated": True} if issue == "orch-x" else {})
    monkeypatch.setenv("WHU_ORCH_LOCK", str(tmp_path / "orch.lock"))
    for k in list(os.environ):
        if k.startswith("WHU_ORCH_") and k != "WHU_ORCH_LOCK":
            monkeypatch.delenv(k)
    return m


def _in_run(monkeypatch, tmp_path, step="s1", models=("m1",), token="t0k", lock_step=None, **extra):
    (tmp_path / "orch.lock").write_text(json.dumps({"token": "t0k", "step": lock_step or step}))
    monkeypatch.setenv("WHU_ORCH_STEP", step)
    monkeypatch.setenv("WHU_ORCH_TOKEN", token)
    monkeypatch.setenv("WHU_ORCH_ISSUE", "orch-x")
    monkeypatch.setenv("WHU_ORCH_ALLOW", json.dumps({"models": list(models), "roles": []}))
    monkeypatch.setenv("WHU_ORCH_STEP_START", "2026-11-06T00:00:00+00:00")
    for k, v in extra.items():
        monkeypatch.setenv(k, str(v))


# ---------------------------------------------------------------------------------------------------- the guard

def test_guard_is_inert_off_an_orchestrated_issue(S):
    S.orch_guard("m1", "x.py", "r", "some-other-issue")         # nothing raised: stages run as before


def test_trial_mode_makes_no_paid_call(S, monkeypatch):
    for mode in ("trial", "replay"):
        monkeypatch.setenv("WHU_ORCH_MODE", mode)
        with pytest.raises(S.OrchestratorRefused):
            S.orch_guard("m1", "x.py", "r", "some-other-issue")


def test_guard_refuses_call_outside_orchestrator(S):
    with pytest.raises(S.OrchestratorRefused, match="orchestrated issue"):
        S.orch_guard("m1", "ruling.py", "omissions", "orch-x")


def test_guard_allows_a_declared_call_inside_its_step(S, monkeypatch, tmp_path):
    _in_run(monkeypatch, tmp_path)
    S.orch_guard("m1", "x.py", "r", "orch-x")


def test_e4_guard_refuses_foreign_token(S, monkeypatch, tmp_path):
    _in_run(monkeypatch, tmp_path, token="not-the-lock's")
    with pytest.raises(S.OrchestratorRefused, match="token"):
        S.orch_guard("m1", "x.py", "r", "orch-x")


def test_guard_refuses_wrong_step_model_and_issue(S, monkeypatch, tmp_path):
    _in_run(monkeypatch, tmp_path, lock_step="another")
    with pytest.raises(S.OrchestratorRefused, match="current step"):
        S.orch_guard("m1", "x.py", "r", "orch-x")
    _in_run(monkeypatch, tmp_path)
    with pytest.raises(S.OrchestratorRefused, match="does not declare model"):
        S.orch_guard("m2", "x.py", "r", "orch-x")
    with pytest.raises(S.OrchestratorRefused, match="inside a run"):
        S.orch_guard("m1", "x.py", "r", "elsewhere")


def test_guard_holds_the_step_to_its_calls_and_cap(S, monkeypatch, tmp_path):
    rows = [{"issue": "orch-x", "at": "2026-11-06T01:00:00+00:00", "usd": 0.4, "role": "a"}] * 3
    monkeypatch.setattr(S, "entries", lambda: rows)
    _in_run(monkeypatch, tmp_path, WHU_ORCH_STEP_CALLS=3)
    with pytest.raises(S.OrchestratorRefused, match="made its 3 calls"):
        S.orch_guard("m1", "x.py", "r", "orch-x")
    _in_run(monkeypatch, tmp_path, WHU_ORCH_STEP_CALLS=10, WHU_ORCH_STEP_CAP=1.25)
    with pytest.raises(S.OrchestratorRefused, match="cap"):
        S.orch_guard("m1", "x.py", "r", "orch-x", about_to_spend=0.1)


def test_metered_client_runs_the_guard_before_the_call(S, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_MODE", "trial")
    called = []
    inner = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: called.append(kw)))
    c = S.MeteredClient(inner, script="t", issue="i", role="r")
    with pytest.raises(S.OrchestratorRefused):
        c.messages.create(model="claude-opus-5-5", max_tokens=1, messages=[])
    assert called == []


def _calls_in(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        src = ast.get_source_segment(path.read_text(encoding="utf-8"), fn) or ""
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and \
                    node.func.attr in ("create", "stream", "generate_content"):
                v = node.func.value
                recv = ast.unparse(v)
                if node.func.attr == "generate_content" or recv.endswith("messages"):
                    yield fn.name, recv, ("orch_guard" in src)


# (file, function) whose call goes through spend_ledger's metered client, which runs the guard itself.
METERED = {("audit_stage.py", "__call__")}


def test_every_paid_call_site_passes_the_guard():
    files = sorted(W.rglob("*.py")) + [ROOT / "backend/scripts/signal/factcheck_draft.py"]
    seen, bad = 0, []
    for f in files:
        for fn, recv, guarded in _calls_in(f):
            seen += 1
            if not guarded and (f.name, fn) not in METERED:
                bad.append("%s:%s (%s)" % (f.relative_to(ROOT), fn, recv))
    assert seen >= 3
    assert bad == [], "paid call sites not dominated by orch_guard: %s" % bad
    src = (W / "audit_stage.py").read_text(encoding="utf-8")
    assert "S.metered(self._raw" in src       # the audit's client is the metered one


# ---------------------------------------------------------------------------------------------------- chain

from orch import chain as CH  # noqa: E402
from orch import steps as ST  # noqa: E402


def _case(tmp_path) -> Path:
    c = tmp_path / "issues" / "WHU-T-orch-x"
    (c / "draft").mkdir(parents=True)
    (c / "issue.json").write_text(json.dumps({"slug": "orch-x", "orchestrated": True}))
    (c / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "type": "synthesis", "title": "A review", "url": "u",
         "access": {"state": "full_text_held", "not_read": ["the figures"]}}]}))
    (c / "premise.json").write_text(json.dumps({"belief": {"statement": "b"}, "kill_condition": "k",
                                                "scope": {"covers": "c"}, "evidence_standard": {"weighs": "measured"},
                                                "direction": {"value": None}}))
    (c / "omissions.json").write_text(json.dumps({"omissions": []}))
    return c


def test_chain_sees_a_write_outside_the_owner(tmp_path):
    c = _case(tmp_path)
    before = CH.snapshot(c, "orch-x")
    (c / "omissions.json").write_text(json.dumps({"omissions": [{"reason": "hand-redacted"}]}))
    (c / "orchestrator").mkdir()
    (c / "orchestrator" / "applied.jsonl").write_text("{}\n")
    v = CH.violations(CH.diff(before, CH.snapshot(c, "orch-x")), ST.owns_for(ST.BY_NAME["bind"], "orch-x"))
    assert v == ["changed omissions.json"]            # the orchestrator's own folder is always owned


def test_e3_omissions_edit_outside_step_stops(tmp_path):
    c = _case(tmp_path)
    before = CH.snapshot(c, "orch-x")
    (c / "omissions.json").write_text(json.dumps({"omissions": [{"reason": "[redacted by hand]"}]}))
    d = CH.diff(before, CH.snapshot(c, "orch-x"))
    for name in ST.NAMES:
        if name == "omissions":
            assert not CH.violations(d, ST.owns_for(ST.BY_NAME[name], "orch-x"))
        else:
            assert CH.violations(d, ST.owns_for(ST.BY_NAME[name], "orch-x")), name


def test_e1_not_read_edit_outside_owner_stops(tmp_path):
    c = _case(tmp_path)
    frozen = {"reading": CH.reading_fp(c)}
    doc = json.loads((c / "sources.json").read_text())
    doc["sources"][0]["access"].pop("not_read")                # Q1-01's deletion
    (c / "sources.json").write_text(json.dumps(doc))
    assert CH.frozen_breaks(c, frozen) and "reading" in CH.frozen_breaks(c, frozen)[0]


def test_e5_source_list_frozen_after_discover(tmp_path):
    c = _case(tmp_path)
    frozen = {"source_list": CH.source_list_fp(c)}
    doc = json.loads((c / "sources.json").read_text())
    doc["sources"][0]["edition"] = "3rd"                        # Q1-04's switch
    (c / "sources.json").write_text(json.dumps(doc))
    assert CH.frozen_breaks(c, frozen)
    doc["sources"][0].pop("edition")
    doc["sources"].append({"id": "S002", "type": "review", "title": "new"})
    (c / "sources.json").write_text(json.dumps(doc))
    assert CH.frozen_breaks(c, frozen)


def test_premise_before_sources_and_frozen(tmp_path):
    c = _case(tmp_path)
    frozen = {"premise": CH.premise_fp(c)}
    d = json.loads((c / "premise.json").read_text())
    d["direction"] = {"value": "CORRECTS"}                      # a row filled after looking: allowed
    (c / "premise.json").write_text(json.dumps(d))
    assert not CH.frozen_breaks(c, frozen)
    d["kill_condition"] = "rewritten after looking"             # a fixed row: never
    (c / "premise.json").write_text(json.dumps(d))
    assert CH.frozen_breaks(c, frozen)
    assert ST.NAMES.index("premise") < ST.NAMES.index("discover") < ST.NAMES.index("acquire")
    import orchestrator as O
    ctx = SimpleNamespace(case=c)
    with pytest.raises(O.RunStop, match="before any source"):
        O.code_premise(ctx, ST.BY_NAME["premise"])


def test_chain_check_for_the_preflight(tmp_path):
    c = _case(tmp_path)
    assert CH.check(c, "orch-x") == ["no orchestrator chain (orchestrator/chain.jsonl)"]
    CH.append(c, "bind", CH.snapshot(c, "orch-x"), CH.frozen_now(c))
    assert CH.check(c, "orch-x") == []
    (c / "omissions.json").write_text("{}")
    assert CH.check(c, "orch-x") == ["changed omissions.json"]


def test_no_step_owns_a_human_record():
    for s in ST.STEPS:
        for pat in ST.owns_for(s, "x"):
            assert not any(n in pat for n in ST.NEVER_WRITTEN), (s.name, pat)
    assert not any(CH.owned(n, ()) for n in ST.NEVER_WRITTEN)


def test_run_step_stops_on_a_write_outside_the_step(tmp_path, monkeypatch):
    import orchestrator as O
    c = _case(tmp_path)
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.frozen, ctx.log = "orch-x", c, "trial", tmp_path, None, {}, []
    monkeypatch.setattr(O, "_study_log", lambda *a: None)
    monkeypatch.setitem(O.STEP_CODE, "rogue", lambda ctx, step: (c / "omissions.json").write_text("{}"))
    rogue = ST.Step("bind", "code", owns=("bindings.json",), code="rogue")
    with pytest.raises(O.RunStop, match="outside the step that owns it"):
        O.run_step(ctx, rogue)


# ---------------------------------------------------------------------------------------------------- the lock

def test_e4_second_orchestrator_refused(tmp_path):
    from orch.lock import RunLock, Busy
    p = tmp_path / "orch.lock"
    with RunLock("a", "trial", path=p) as lk:
        lk.set_step("audit")
        assert json.loads(p.read_text())["step"] == "audit"
        with pytest.raises(Busy):
            with RunLock("b", "trial", path=p):
                pass
    with RunLock("b", "trial", path=p):
        pass


def test_steps_run_in_one_fixed_sequence():
    assert len(set(ST.NAMES)) == len(ST.NAMES)
    assert ST.NAMES[0] == "provenance" and ST.NAMES[-2:] == ("preflight", "archive")
    group = [s.name for s in ST.STEPS if s.repeat_group]
    assert group == ["findings", "conclusions", "audit", "overstatement", "corrections", "final_gate", "commit_8",
                     "changecheck"]
    for s in ST.STEPS:
        assert (s.max_calls == 0) == (not s.models), s.name


# ---------------------------------------------------------------------------------------------------- applier, E2

from orch.page import Page, NotPlaced, fingerprint  # noqa: E402


def _page():
    return Page({"title": "T", "blocks": [
        {"tag": "h2", "section": "answer", "text": "The short answer"},
        {"tag": "p", "section": "answer", "sentences": ["One is true [1].", "Two may be true [1]."]},
        {"tag": "html", "section": "readers", "html": "  <p>Judged not material to this question: “x.” (y [1]).</p>"}]})


def test_applier_replaces_deletes_and_inserts_word_for_word():
    p = _page()
    p.replace("Two may be true [1].", "Two may be true in adults [1].")
    p.insert_after(fingerprint("One is true [1]."), "Inserted. Second inserted.")
    p.insert_after(fingerprint("One is true [1]."), "Third.")
    assert p.blocks()[1]["sentences"] == ["One is true [1].", "Inserted.", "Second inserted.", "Third.",
                                          "Two may be true in adults [1]."]
    p.delete("Third.")
    assert "Third." not in p.sentences()
    html = p.render()
    assert "<p>One is true [1]. Inserted. Second inserted. Two may be true in adults [1].</p>" in html


def test_applier_never_guesses_and_never_rewrites_a_code_line():
    p = _page()
    with pytest.raises(NotPlaced):
        p.replace("A sentence not on the page.", "x")
    with pytest.raises(NotPlaced, match="never rewritten"):
        p.replace("Judged not material to this question: “x.” (y [1]).", "softer")
    p.delete("Judged not material to this question: “x.” (y [1]).")      # a removal is allowed
    assert not any("Judged" in s for s in p.sentences())


def test_e2_binding_without_ruling_refused():
    from orch import apply as AP
    ops = [{"op": "replace", "old": "a", "new": "The ruled text [1].", "why": "ruling"}]
    assert AP.bind_changed(["The ruled text [1]."], ops) == ["The ruled text [1]."]
    with pytest.raises(AP.UnruledBinding, match="E2"):
        AP.bind_changed(["The sentence a finding named [1]."], ops)


# ---------------------------------------------------------------------------------------------------- E6, A

def test_e6_form_derived_not_chosen():
    from orch import model_steps as M
    import source_store as store
    good = {"sources": [{"title": "IPCC AR6 WGI Summary for Policymakers", "first_author": "IPCC", "year": 2021,
                         "type": "assessment_summary"}]}
    assert M.discover_proposals(good, set(store.TYPES), 8)[0]["type"] == "assessment_summary"
    with pytest.raises(M.StepFailed, match="form"):
        M.discover_proposals({"sources": [dict(good["sources"][0], form="page")]}, set(store.TYPES), 8)
    with pytest.raises(M.StepFailed, match="TYPES"):
        M.discover_proposals({"sources": [dict(good["sources"][0], type="summary")]}, set(store.TYPES), 8)
    assert store.form_of({"type": "assessment_summary"}) == "assessment summary"
    assert store.form_of({"type": "guideline", "form": None}) == "record"


def test_fetch_user_agent_is_generic():
    import tls
    import acquire_sources
    import errata
    import find_access
    import registry_facts
    ua = tls.USER_AGENT
    assert ua == "WHU-fetch/1.0 (automated research client)"
    assert not re.search(r"Mozilla|Chrome|Safari|@", ua)
    assert acquire_sources.UA["User-Agent"] == ua and errata.UA == ua
    assert find_access.UA["User-Agent"] == ua and registry_facts.UA["User-Agent"] == ua


def test_assessment_summary_form():
    import source_store as store
    assert "assessment summary" in store.FORMS
    body = ("Summary for Policymakers. Headline Statements. " + "The climate warmed. " * 200).encode()
    assert store.substance_assessment_summary(body, "text/plain")[0] == "document"
    assert store.substance_assessment_summary(b"Summary for Policymakers. Short.", "text/plain")[0] == "stub"
    assert store.substance_assessment_summary(("An essay. " * 400).encode(), "text/plain")[0] == "undetermined"


# ---------------------------------------------------------------------------------------------------- items 6, 7

def test_recency_records_registries_and_queries(monkeypatch):
    import factcheck_draft as fc
    resp = SimpleNamespace(content=[
        SimpleNamespace(type="server_tool_use", input={"query": "IPCC AR6 SPM latest"}),
        SimpleNamespace(type="web_search_tool_result", content=[SimpleNamespace(url="https://www.ipcc.ch/report/"),
                                                                  SimpleNamespace(url="https://api.crossref.org/x")]),
        SimpleNamespace(type="text", text="{}")])
    got = fc.searches_in(resp)
    assert got == {"queries": ["IPCC AR6 SPM latest"], "domains": ["ipcc.ch", "api.crossref.org"]}

    def fake_call(*a, **k):
        fc.LAST_SEARCH.update(got)
        return {"studies": [{"name": "AR6", "status": "UNKNOWN"}]}
    monkeypatch.setattr(fc, "call", fake_call)
    out = fc.sweep_recency("draft", "2026-11-06")
    assert out["studies"][0]["searched"] == ["ipcc.ch", "api.crossref.org"]
    assert out["studies"][0]["queries"] == ["IPCC AR6 SPM latest"] and out["queries"] == got["queries"]
    import lean_editions as LE
    assert LE.searched_of(out["studies"][0]) == ["ipcc.ch", "api.crossref.org"]


@pytest.mark.parametrize("s", [
    "Our recency check could not establish whether State of CDR [3] has a newer edition.",
    "We could not establish whether the trial finished.",
    "The authors were unable to determine the dose.",
    "Whether it helps cannot be determined.",
    "It could not be established which edition is current.",
    "It is not possible to determine the cause.",
    "The review failed to establish a benefit.",
])
def test_unknowability_every_form(s):
    import lint_claims as L
    assert L.unknowability(s), s


def test_unknowability_names_its_search():
    import lint_claims as L
    assert not L.unknowability("Our recency check (searched: ipcc.ch, crossref.org) could not establish whether "
                               "the report [1] has a newer edition.")
    assert L.unknowability("Our recency check (searched: ) could not establish whether the report has a newer "
                           "edition.")
    assert not L.unknowability("We could not establish it from ClinicalTrials.gov NCT01234567.")


# ---------------------------------------------------------------------------------------------------- overstatement

class FakeResp:
    def __init__(self, text, model="gemini-4-argon-001", refused=False):
        self.text = text
        self.model_version = model
        self.usage_metadata = SimpleNamespace(prompt_token_count=900, cached_content_token_count=0,
                                              candidates_token_count=40, thoughts_token_count=60)
        self.candidates = [SimpleNamespace(finish_reason="SAFETY" if refused else "STOP")]
        self.prompt_feedback = None


class FakeGoogle:
    def __init__(self, replies, fail=None):
        self.replies, self.sent, self.fail = list(replies), [], fail
        self.models = self

    def generate_content(self, model, contents, config):
        self.sent.append(contents)
        if self.fail:
            raise self.fail
        if contents == "Reply with the single word: ok":
            return FakeResp("ok")
        return self.replies.pop(0)


@pytest.fixture
def quiet_ledger(monkeypatch):
    from orch import google as G
    rec = []
    monkeypatch.setattr(G.S, "record", lambda **kw: rec.append(kw))
    monkeypatch.setattr(G.S, "orch_guard", lambda *a, **k: None)
    return rec


def _rows():
    return {"aaa": {"sentence": "The review found X in all adults [1].", "on_page": True, "source_id": "S001",
                    "span": "X was found in some adults."},
            "bbb": {"sentence": "Judged not material to this question: “Y held.” (the review [1]).", "on_page": True,
                    "source_id": "S001", "span": "Y held."},
            "ccc": {"sentence": "The question is: “Q?”", "on_page": True, "source_id": None, "span": None}}


HELD = {"S001": "Intro. X was found in some adults. Then Y held. End."}


def _locate(q, hay):
    i = hay.find(q)
    return (i, i + len(q)) if i >= 0 else None


def test_overstatement_sends_only_sentence_and_passage_and_removes_on_yes(tmp_path, quiet_ledger, monkeypatch):
    from orch import overstatement as O
    from orch.google import Gateway
    import lean
    monkeypatch.setattr(lean, "enabled", lambda: True)
    import lean_failsafe as FS
    g = FakeGoogle([FakeResp('{"overstates": "yes", "how": "generalises", "why": "some, not all"}'),
                    FakeResp('{"overstates": "no", "how": "none", "why": "verbatim"}')])
    gw = Gateway("orch-x", client=g)
    case = tmp_path
    (case / "rulings").mkdir()
    log = case / "rulings" / "rulings.jsonl"
    counts = O.run(case, _rows(), HELD, _locate, gw, lambda it: FS.record(O.PATH, it, log))
    assert g.sent[0] == "Reply with the single word: ok"         # the paid-tier preflight first
    assert counts["pairs"] == 2 and counts["yes"] == 1 and counts["no"] == 1
    first = g.sent[1]
    assert "X was found in some adults." in first and "all adults" in first
    assert "Q?" not in first and "Y held" not in first          # nothing but its own sentence and passage
    removed = FS.load(case)
    assert [r["outcome"] for r in removed] == [FS.OUTCOME] and removed[0]["path"] == "overstatement"
    # carried: nothing re-sent
    n = len(g.sent)
    O.run(case, _rows(), HELD, _locate, gw, lambda it: FS.record(O.PATH, it, log))
    assert len(g.sent) == n
    row = O.preflight_row(case, ["The review found X in all adults [1].", _rows()["bbb"]["sentence"]], _rows(),
                          HELD, _locate)
    assert row[1] == "BLOCKED"
    row = O.preflight_row(case, [_rows()["bbb"]["sentence"]], _rows(), HELD, _locate)
    assert row[1] == "ok"


def test_overstatement_yes_on_a_required_line_stops(tmp_path, quiet_ledger, monkeypatch):
    from orch import overstatement as O
    from orch.google import Gateway
    import lean
    monkeypatch.setattr(lean, "enabled", lambda: True)
    import lean_failsafe as FS
    rows = {"bbb": _rows()["bbb"]}
    g = FakeGoogle([FakeResp('{"overstates": "yes", "how": "more", "why": "w"}')])
    (tmp_path / "rulings").mkdir()
    O.run(tmp_path, rows, HELD, _locate, Gateway("orch-x", client=g),
          lambda it: FS.record(O.PATH, it, tmp_path / "rulings" / "rulings.jsonl"))
    assert [r["outcome"] for r in FS.load(tmp_path)] == [FS.STOP]


def test_overstatement_bad_reply_twice_is_treated_as_yes(tmp_path, quiet_ledger):
    from orch import overstatement as O
    from orch.google import Gateway
    g = FakeGoogle([FakeResp("I think it is fine."), FakeResp("", refused=True)])
    p = O.pairs({"aaa": _rows()["aaa"]}, HELD, _locate)[0]
    row = O.check_one(Gateway("orch-x", client=g), p)
    assert row["verdict"] == "yes" and row["why"] == O.TREATED_AS_YES and len(row["replies"]) == 2


def test_google_gateway_stops_on_free_tier_transport_error_and_wrong_model(quiet_ledger):
    from orch.google import Gateway, Stop
    with pytest.raises(Stop, match="Free Tier"):
        Gateway("i", client=FakeGoogle([], fail=RuntimeError("429 quotaId GenerateContentFreeTier"))).preflight()
    g = FakeGoogle([FakeResp("{}", model="gemini-2-flash")])
    with pytest.raises(Stop, match="not gemini-4-argon"):
        Gateway("i", client=g).call("x", "overstatement")


def test_google_gateway_passes_the_guard_before_any_call(S, monkeypatch):
    from orch import google as G
    monkeypatch.setattr(G, "S", S)
    monkeypatch.setenv("WHU_ORCH_MODE", "trial")
    g = FakeGoogle([])
    with pytest.raises(S.OrchestratorRefused):
        G.Gateway("orch-x", client=g).preflight()
    assert g.sent == []


def test_passage_is_the_span_widened_to_sentences():
    from orch import overstatement as O
    t = "First sentence here. The bound span sits here. Last one."
    a = t.index("bound span")
    lo, hi = O.passage_around(t, a, a + len("bound span"))
    assert t[lo:hi].strip() == "The bound span sits here."


# ---------------------------------------------------------------------------------------------------- model steps

def test_model_steps_reject_replies_outside_their_schema():
    from orch import model_steps as M
    ok = json.dumps({"belief": "b", "kill_condition": "k", "reader_with_a_decision": "r", "scope_covers": "c",
                     "scope_out": [{"what": "w", "why": "y"}], "weighs": "measured", "measured": "m",
                     "assessed": "a"})
    d = M.premise("Q?", lambda *a: ok, by="claude-opus-5-5")
    assert d["scope"]["by"] == "claude-opus-5-5" and d["evidence_standard"]["when_they_differ"] == "state both"
    with pytest.raises(M.StepFailed):
        M.premise("Q?", lambda *a: "Sure! Here is a premise.", by="m")
    passages = {"S001#3": {"source": "S001", "start": 0, "end": 5, "text": "abc"}}
    good = {"title": "T", "sections": [{"id": i, "heading": "H", "blocks": [
        {"sentences": [{"text": "It may help [1].", "passages": ["S001#3"]}]}]} for i in M.SECTION_IDS]}
    out = M.draft_page(good, passages)
    assert out["sections"][0]["blocks"][0]["sentences"][0]["text"] == "It may help."   # code adds the numbers
    bad = json.loads(json.dumps(good))
    bad["sections"][0]["blocks"][0]["sentences"][0]["passages"] = ["S009#1"]
    with pytest.raises(M.StepFailed, match="not sent"):
        M.draft_page(bad, passages)


def test_resolve_proposals_never_mints_an_identifier():
    import orchestrator as O
    found = SimpleNamespace(identifier=SimpleNamespace(kind="doi", value="10.1/real"), heading="Real title",
                            registry="crossref", extra={})
    miss = SimpleNamespace(reason="no registry title matched", status="NOT_FOUND")
    props = [{"title": "Real title", "first_author": "A", "year": 2020, "type": "review", "url": "https://x.org/a"},
             {"title": "Invented", "first_author": "B", "year": 2021, "type": "review", "url": "https://blog.example/"},
             {"title": "WHO guideline", "first_author": "WHO", "year": 2019, "type": "guideline",
              "url": "https://iris.who.int/handle/1"},
             {"title": "Lancet paper", "first_author": "C", "year": 2022, "type": "primary",
              "url": "https://www.thelancet.com/x"}]
    answers = {"Real title": found, "Invented": miss, "WHO guideline": miss,
               "Lancet paper": SimpleNamespace(identifier=SimpleNamespace(kind="doi", value="10.1016/x"),
                                               heading="Lancet paper", registry="crossref", extra={})}
    srcs, unresolved = O.resolve_proposals(props, lambda t, a, y, k: answers[t])
    assert [s["title"] for s in srcs] == ["Real title", "WHO guideline", "Lancet paper"]
    assert srcs[0]["doi"] == "10.1/real" and "doi" not in srcs[1]
    assert srcs[2]["url"] is None and srcs[2]["access"]["reason"] == "publisher terms"
    assert [u["proposal"]["title"] for u in unresolved] == ["Invented"]


# ---------------------------------------------------------------------------------------------------- provenance

def test_manifest_records_hashes_models_tools():
    from orch import manifest as MF
    m = MF.build(ROOT, ST.STEPS)
    assert m["documents"]["CLAUDE.md"] and m["documents"]["docs/whu-orchestrator.md"]
    assert "backend/scripts/whatholdsup/orchestrator.py" in m["code"]
    assert m["models"]["overstatement"] == ["gemini-4-argon"]
    assert m["tools"]["fetch_user_agent"] == "WHU-fetch/1.0 (automated research client)"
    m2 = json.loads(json.dumps(m))
    m2["code"]["backend/scripts/whatholdsup/orchestrator.py"] = "0" * 64
    assert MF.changed(m, m2) == ["code: backend/scripts/whatholdsup/orchestrator.py"]


# ---------------------------------------------------------------------------------------------------- CLI, trial

def _cli(*args, env=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith("WHU_ORCH") and k != "WHU_LEAN"}
    e.update(env or {})
    return subprocess.run([sys.executable, str(W / "orchestrator.py"), *args], cwd=str(ROOT), env=e,
                          capture_output=True, text=True, timeout=600)


def test_paid_mode_is_refused_until_ruled():
    r = _cli("run", "whu-lean-q1-01c", "--mode", "paid", env={"WHU_LEAN": "1"})
    assert r.returncode == 2 and "no paid run until the advisor rules" in r.stdout
    r = _cli("run", "whu-lean-q1-01c", "--mode", "trial")
    assert r.returncode == 2 and "WHU_LEAN=1" in r.stdout


def test_trial_outputs_discarded():
    """A trial on a real case runs in a scratch copy, is refused at its first rule (the lean-test issue is not
    orchestrated), spends nothing, and leaves no file behind."""
    import tempfile
    tmp = Path(tempfile.gettempdir())
    before_dirs = set(tmp.glob("whu-orch-*"))
    case = next((ROOT / "issues").glob("WHU-*-whu-lean-q1-01c"))
    before_case = {p.relative_to(case).as_posix(): _sha(p) for p in case.rglob("*") if p.is_file()}
    before_ledger = _sha(LEDGER)
    r = _cli("run", "whu-lean-q1-01c", "--mode", "trial", env={"WHU_LEAN": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["result"].startswith("Not Ready") and "orchestrated" in out["result"]
    assert _sha(LEDGER) == before_ledger
    assert {p.relative_to(case).as_posix(): _sha(p) for p in case.rglob("*") if p.is_file()} == before_case
    assert set(tmp.glob("whu-orch-*")) == before_dirs


def test_internal_resolver_takes_identifiers_only_from_the_record():
    from orch import resolve as RV
    rec = {"title": "Digital tracking, provider decision support systems and targeted client communication",
           "authorString": "Agarwal S, Chin WY", "pubYear": "2025", "doi": "10.1002/x", "pmcid": "PMC1"}
    got = RV.search("Digital tracking provider decision support systems targeted client communication", "Agarwal",
                    2025, lookup=lambda t, f: rec)
    assert got.identifier.value == "10.1002/x" and got.extra["pmcid"] == "PMC1"
    assert isinstance(RV.search("Digital tracking provider decision support systems targeted client",
                                "Smith", 2025, lookup=lambda t, f: rec), RV.Unresolved)
    assert isinstance(RV.search("Digital tracking provider decision support systems targeted client",
                                "Agarwal", 2019, lookup=lambda t, f: rec), RV.Unresolved)
    assert isinstance(RV.search("x", None, None, lookup=lambda t, f: None), RV.Unresolved)


def test_caller_in_trial_mode_needs_no_key_and_makes_no_call(monkeypatch):
    import audit_stage as A
    monkeypatch.setenv("WHU_ORCH_MODE", "replay")
    c = A.Caller(cap=1.0, ledger_issue="nobody")
    with pytest.raises(Exception, match="makes no paid call"):
        c("prompt", 10, "audit")


def _draft_ctx(tmp_path, monkeypatch):
    import orchestrator as O
    c = _case(tmp_path)
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.root, ctx.mode = "orch-x", c, tmp_path, "trial"
    ctx.page, ctx.page_json = c / "draft" / "orch-x.html", c / "draft" / "page.json"
    passages = {"S001#4": {"source": "S001", "start": 10, "end": 40, "text": "X was found in some adults."}}
    monkeypatch.setattr(O, "_passages", lambda ctx: passages)
    monkeypatch.setattr(O, "_cite_numbers", lambda ctx: {"S001": 1})
    monkeypatch.setattr(O, "_generated_blocks", lambda ctx: ("  <p>The question is: “Q?”</p>",
                                                             "  <p>We hold the full text of R [1].</p>", ""))
    monkeypatch.setattr(O, "_source_list", lambda ctx: '<div class="src">[1] R.</div>')
    reply = json.dumps({"title": "T", "sections": [
        {"id": "answer", "heading": "The short answer",
         "blocks": [{"sentences": [{"text": "X was found in some adults [3].", "passages": ["S001#4"]}]}]},
        {"id": "findings", "heading": "What it found", "blocks": [{"h3": "Adults"}, {"sentences": [
            {"text": "That is the main finding.", "passages": []}]}]},
        {"id": "verdict", "heading": "What holds up", "blocks": [{"sentences": [
            {"text": "It holds for some adults.", "passages": ["S001#4"]}]}]}]})
    ctx.ask = lambda prompt, n, role: reply
    return O, ctx


def test_draft_step_renders_code_citations_and_records_what_each_sentence_rests_on(tmp_path, monkeypatch):
    O, ctx = _draft_ctx(tmp_path, monkeypatch)
    out = O.code_draft(ctx, ST.BY_NAME["draft"])
    assert out["outcome"].startswith("3 sentences")
    page = json.loads(ctx.page_json.read_text())
    assert page["provenance"]["X was found in some adults [1]."] == [{"source": "S001", "start": 10, "end": 40}]
    assert page["provenance"]["That is the main finding."] == []
    html = ctx.page.read_text()
    assert "[3]" not in html and "X was found in some adults [1]." in html
    assert html.index("The question is") < html.index("The short answer") < html.index("We hold the full text")


def test_apply_step_carries_what_a_replaced_sentence_rested_on(tmp_path, monkeypatch):
    O, ctx = _draft_ctx(tmp_path, monkeypatch)
    O.code_draft(ctx, ST.BY_NAME["draft"])
    from orch import apply as AP
    op = {"op": "replace", "old": "X was found in some adults [1].", "new": "X was found in some adults, the "
          "review says [1].", "why": "ruling r1"}
    monkeypatch.setattr(AP, "pending", lambda case: [("ruling:r1", "t", op)])
    bound = []
    monkeypatch.setattr(O, "code_bind", lambda ctx, step, only=None: bound.append(only))
    import applied_check as AC
    monkeypatch.setattr(AC, "check", lambda case, html: {"mismatches": []})
    monkeypatch.setattr(AC, "dangling", lambda case, html: [])
    out = O.code_apply(ctx, ST.BY_NAME["advocate"])
    page = json.loads(ctx.page_json.read_text())
    assert out["changed"] and page["provenance"]["X was found in some adults, the review says [1]."] == \
        [{"source": "S001", "start": 10, "end": 40}]
    assert bound == [["X was found in some adults, the review says [1]."]]
    assert "X was found in some adults, the review says [1]." in ctx.page.read_text()


# ---------------------------------------------------------------------------------------------------- E7, E8, E9
# The replay's three unrecorded drafter edits (advisor's ruling 2026-11-07): each is stopped by orch/accounting.py
# after any step that owns the page.

from orch import accounting as AA  # noqa: E402

SRC = '<div class="sources">\n<div class="src"><span class="tag">[1]</span> A. A review. 2020.</div>\n</div>'


def _acc_case(tmp_path):
    c = tmp_path / "case"
    (c / "orchestrator").mkdir(parents=True, exist_ok=True)
    page = Page({"title": "T", "provenance": {"One is true [1].": [], "Two may be true [1].": []}, "blocks": [
        {"tag": "p", "section": "answer", "sentences": ["One is true [1].", "Two may be true [1]."]},
        {"tag": "html", "section": "sources", "html": SRC}]})
    return c, page, {"sources": SRC}


def test_e7_a_hand_edited_source_line_stops(tmp_path):
    c, page, gen = _acc_case(tmp_path)
    assert AA.problems(c, page, gen, None) == []
    page.blocks()[1]["html"] = SRC.replace("A review. 2020.", "A review (3rd edition). 2021.")
    bad = AA.problems(c, page, gen, AA.on_page(_acc_case(tmp_path)[1]))
    assert bad and all(b.startswith(("E7", "E9")) for b in bad) and any(b.startswith("E7") for b in bad)


def test_e8_a_first_read_proposal_is_never_applied_and_a_hand_placed_one_stops(tmp_path):
    from orch import apply as AP
    c, page, gen = _acc_case(tmp_path)
    (c / "audit" / "r1").mkdir(parents=True)
    (c / "audit" / "r1" / "rulings.jsonl").write_text("\n".join(json.dumps(r) for r in [
        {"id": "a1", "at": "2026-11-07T10:00:00Z", "ruling": "refer", "inputs": {"sentence": "One is true [1]."},
         "proposed_text": "One may be true [1]."},                                # a first read: not a ruling
        {"id": "a2", "at": "2026-11-07T10:01:00Z", "ruling": "amend", "inputs": {"sentence": "Two may be true [1]."},
         "proposed_text": "Two is probably true [1].", "text": "Two may be true in adults [1]."}]) + "\n")
    ops = AP.apply_all(c, page)
    assert [o["new"] for o in ops] == ["Two may be true in adults [1]."]          # the ruling's text, never the proposal
    assert "One is true [1]." in page.sentences() and "One may be true [1]." not in page.sentences()
    prev = AA.on_page(page)
    assert AA.problems(c, page, gen, prev) == []
    page.blocks()[0]["sentences"][0] = "One may be true [1]."                     # Q1-03b: the proposal placed by hand
    bad = AA.problems(c, page, gen, prev)
    assert any(b.startswith("E8") for b in bad) and any(b.startswith("E9") for b in bad)


def test_e9_a_removal_with_no_record_stops_and_a_recorded_one_passes(tmp_path):
    c, page, gen = _acc_case(tmp_path)
    prev = AA.on_page(page)
    page.blocks()[0]["sentences"].remove("Two may be true [1].")
    assert [b[:2] for b in AA.problems(c, page, gen, prev)] == ["E9"]
    (c / "orchestrator" / "applied.jsonl").write_text(json.dumps(
        {"key": "cut:x", "op": "delete", "old": "Two may be true [1].", "why": "audit cut"}) + "\n")
    assert AA.problems(c, page, gen, prev) == []


def test_e7_e9_run_after_every_page_owning_step(tmp_path, monkeypatch):
    import orchestrator as O
    c = _case(tmp_path)
    c2, page, gen = _acc_case(tmp_path)
    page.save(c / "draft" / "page.json")
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.frozen, ctx.log = "orch-x", c, "trial", tmp_path, None, {}, []
    ctx.page_json, ctx.page = c / "draft" / "page.json", c / "draft" / "orch-x.html"
    ctx.page_prev = AA.on_page(page)
    monkeypatch.setattr(O, "_study_log", lambda *a: None)
    monkeypatch.setattr(O, "_generated_blocks", lambda ctx: ("", "", ""))
    monkeypatch.setattr(O, "_source_list", lambda ctx: SRC)

    def rogue(ctx, step):                                  # a page-owning step's code drops a sentence unrecorded
        p = Page.load(ctx.page_json)
        p.blocks()[0]["sentences"].pop()
        p.save(ctx.page_json)
    monkeypatch.setitem(O.STEP_CODE, "rogue", rogue)
    with pytest.raises(O.RunStop, match="E9"):
        O.run_step(ctx, ST.Step("omissions", "code", owns=ST.PAGE, code="rogue"))
    owners = [s.name for s in ST.STEPS if "draft/page.json" in ST.owns_for(s, "x")]
    assert owners and "gate" not in owners and "preflight" not in owners      # the rest may not touch it at all


# ---------------------------------------------------------------------------------------------------- trial-1 fixes
# Advisor's ruling 2026-11-07 after orchestrator trial 1 stopped at the premise: reply limits from the stored records;
# every cut-off or unusable reply kept; a failed step logged with cost and reason; every ledger row names its step.

def test_reply_limits_cover_the_stored_records_with_a_margin():
    rec = json.loads((ROOT / "study/whu-reliability/next_phase/results/orchestrator/reply_limits.json").read_text())
    assert set(rec["steps"]) == set(ST.REPLY_LIMITS)
    for k, v in rec["steps"].items():
        assert ST.REPLY_LIMITS[k] == v["new_limit"] >= 1.5 * v["basis_tokens"], k
    assert ST.REPLY_LIMITS["premise"] == 4000
    from orch import google as G
    assert G.MAX_OUT == ST.REPLY_LIMITS["overstatement"]


def test_each_model_step_asks_with_its_limit():
    from orch import model_steps as M
    seen = {}

    def ask(prompt, max_tokens, role):
        seen[role] = max_tokens
        return {"premise": json.dumps({"belief": "b", "kill_condition": "k", "reader_with_a_decision": "r",
                                       "scope_covers": "c", "scope_out": [], "weighs": "measured",
                                       "measured": "m", "assessed": "a"}),
                "coverage": json.dumps({"decision": "not_material", "why": "w", "sentence": ""}),
                "judgement_sentence": json.dumps({"sentence": "s"})}[role]
    M.premise("q?", ask, by="x")
    M.coverage_decision("q?", "{}", "u", ask)
    M.judgement_sentence("t", ask)
    assert seen == {k: ST.REPLY_LIMITS[k] for k in ("premise", "coverage", "judgement_sentence")}
    src = (W / "orchestrator.py").read_text()
    assert 'ST.REPLY_LIMITS["draft"]' in src and src.count('ST.REPLY_LIMITS["discover"]') >= 2


def test_a_cut_off_reply_keeps_its_text():
    import audit_stage as A
    c = A.Caller(cap=1.0, ledger_issue="orch-x", ask=lambda prompt, n: ("{\"belief\": \"half a rep", {"input": 3, "output": n, "usd": 0.01,
                                                                     "stop_reason": "max_tokens"}))
    with pytest.raises(A.ReplyCutOff) as e:
        c("p", 10, "premise")
    assert e.value.text.startswith("{\"belief\"") and e.value.usage["output"] == 10


def test_a_long_reply_limit_sends_an_explicit_timeout():
    import audit_stage as A
    src = (W / "audit_stage.py").read_text()
    assert A.LONG_REPLY_TOKENS < 21333 < ST.REPLY_LIMITS["draft"]
    assert 'kw = {"timeout": LONG_REPLY_TIMEOUT_S} if max_tokens > LONG_REPLY_TOKENS else {}' in src


def test_a_failed_step_is_logged_with_cost_reason_and_its_cut_off_reply(tmp_path, monkeypatch):
    import orchestrator as O
    import audit_stage as A
    c = _case(tmp_path)
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.frozen, ctx.log = "orch-x", c, "trial", tmp_path, None, {}, []
    ctx.page_json = c / "draft" / "page.json"
    ctx.ask = lambda prompt, n, role: (_ for _ in ()).throw(A.ReplyCutOff("reply cut off at %d tokens (%s)" % (n, role),
                                                                       {"output": n}, "{\"belief\": \"cut"))
    rows = []
    monkeypatch.setattr(O, "_study_log", lambda ctx, r: rows.append(dict(r, usd=0.0314)))
    monkeypatch.setitem(O.STEP_CODE, "asks", lambda ctx, step: O._ask_for(ctx, step, "m")("p", 4000, "premise"))
    with pytest.raises(A.ReplyCutOff):
        O.run_step(ctx, ST.Step("premise", "model", owns=("premise.json",), models=("m",), code="asks"))
    assert len(ctx.log) == 1 and ctx.log[0]["step"] == "premise"
    f = ctx.log[0]
    assert f["failed"].startswith("ReplyCutOff: reply cut off at 4000 tokens (premise)") and f["end"]
    assert f["replies"] == [{"role": "premise", "max_tokens": 4000, "cut_off": True, "text": "{\"belief\": \"cut",
                             "usage": {"output": 4000}}]
    assert rows and rows[0]["failed"] == f["failed"]


def test_study_log_row_of_a_failed_step_says_failed_with_its_cost(tmp_path, monkeypatch):
    import orchestrator as O
    c = _case(tmp_path)
    ctx = SimpleNamespace(case=c, slug="orch-x", root=ROOT)
    r = {"step": "premise", "start": "2999-01-01T00:00:00+00:00", "end": "2999-01-01T00:00:01+00:00",
         "failed": "StepFailed: weighs must be measured, assessed or both"}
    O._study_log(ctx, r)
    row = (c / "study_log.md").read_text().splitlines()[-1]
    assert row.startswith("| premise (orchestrator) |") and "FAILED: StepFailed: weighs must be" in row
    assert r["usd"] == 0.0 and "$0.0000" in row


def test_a_failed_command_keeps_its_exit_code_and_output(tmp_path):
    import orchestrator as O
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.first = "orch-x", tmp_path, "trial", tmp_path, None, None
    ctx.page, ctx.gate = tmp_path / "p.html", tmp_path / "p.html.gate.json"
    step = ST.Step("gate", "stage", cmds=((sys.executable, "-c", "import sys; print('why it stopped'); sys.exit(3)"),))
    with pytest.raises(O.RunStop) as e:
        O.run_cmds(ctx, step)
    assert e.value.cmds[0]["rc"] == 3 and "why it stopped" in e.value.cmds[0]["tail"]


def test_every_ledger_row_inside_a_step_names_the_step(S, monkeypatch, tmp_path):
    monkeypatch.setattr(S, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    S.record(script="x.py", role="r", issue="i", usd=0.1)
    monkeypatch.setenv("WHU_ORCH_STEP", "premise")
    S.record(script="audit_stage.py", role="audit", issue="i", usd=0.1)
    a, b = [json.loads(l) for l in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert "step" not in a and b["step"] == "premise"


def test_field_limits_are_twice_the_longest_stored_value():
    rec = json.loads((ROOT / "study/whu-reliability/next_phase/results/orchestrator/field_limits.json").read_text())
    assert set(rec["fields"]) == set(ST.FIELD_LIMITS)
    for k, v in rec["fields"].items():
        assert ST.FIELD_LIMITS[k] == v["new_limit"] >= (v["old_limit"] or 0), k
        if v["longest_seen"]:
            assert v["new_limit"] >= 2 * v["longest_seen"], k
    assert ST.FIELD_LIMITS["premise.measured"] >= 2 * 434          # trial 1 attempt 2's real reply
    src = (W / "orch" / "model_steps.py").read_text()
    assert not re.search(r'_str\([a-z]+, "[a-z_]+", \d+', src)    # no limit written outside the table


# ---------------------------------------------------------------------------------------------------- rulings (a)-(d)
# Advisor's rulings after trial 1's attempt 3 (2026-11-07).

def test_a_an_unheld_source_does_not_stop_the_run_and_is_recorded_not_held(tmp_path):
    import orchestrator as O
    c = _case(tmp_path)
    doc = {"sources": [
        {"id": "S001", "type": "review", "title": "Held review", "used_for": "x",
         "access": {"state": "full_text_held", "held": {"file": "f"}}},
        {"id": "S002", "type": "review", "title": "A map we could not hold", "used_for": "x",
         "access": {"last_fetch": {"on": "2026-11-07", "result": "not fetched", "why": "form check failed"}}}]}
    (c / "sources.json").write_text(json.dumps(doc))
    out = O.code_acquire(SimpleNamespace(case=c), ST.BY_NAME["acquire"])
    assert out["not_held"] == ["S002"] and out["outcome"] == "1 held, 1 not held"
    got = json.loads((c / "sources.json").read_text())["sources"][1]["access"]
    assert got["not_held"] == {"line": "could_not_hold", "why": "form check failed"}
    assert got["state"] == "blocked" and "form check failed" in got["blocked_by"]   # the ledger's own state
    for s in doc["sources"]:
        s["access"] = {"last_fetch": {"why": "nothing"}}
    (c / "sources.json").write_text(json.dumps(doc))
    with pytest.raises(O.RunStop, match="no source is held"):
        O.code_acquire(SimpleNamespace(case=c), ST.BY_NAME["acquire"])


def test_a_acquire_exit_1_is_accepted_only_from_acquire_sources_in_acquire(tmp_path):
    import orchestrator as O
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.first = "orch-x", tmp_path, "trial", tmp_path, None, None
    ctx.page, ctx.gate = tmp_path / "p.html", tmp_path / "p.html.gate.json"
    (tmp_path / "acquire_sources.py").write_text("import sys; sys.exit(1)\n")
    (tmp_path / "errata.py").write_text("import sys; sys.exit(1)\n")
    ok = ST.Step("acquire", "code", cmds=((sys.executable, str(tmp_path / "acquire_sources.py")),))
    assert O.run_cmds(ctx, ok)[0]["rc"] == 1
    with pytest.raises(O.RunStop):
        O.run_cmds(ctx, ST.Step("acquire", "code", cmds=((sys.executable, str(tmp_path / "errata.py")),)))
    with pytest.raises(O.RunStop):
        O.run_cmds(ctx, ST.Step("gate", "stage", cmds=((sys.executable, str(tmp_path / "acquire_sources.py")),)))


def test_a_orchestrated_runs_print_no_human_search_list():
    src = (W / "acquire_sources.py").read_text()
    i = src.index('if failed and os.environ.get("WHU_ORCH_ISSUE") == args.slug:')
    j = src.index("HUMAN SEARCH LIST", i)
    assert i < j and "elif failed:" in src[i:j]


def test_a_b_the_page_lines_are_code_written_and_nothing_draws_on_the_source():
    import lean_sentences as LS
    srcs = [{"id": "S001", "title": "Held review", "access": {"state": "full_text_held"}},
            {"id": "S002", "title": "Evidence and gap map of interventions",
             "access": {"state": "blocked", "not_held": {"line": "could_not_hold"}}}]
    gen = LS.generate({"question": "Q?"}, srcs, not_of_a_type=[{"title": "Inclusion Matters"}])
    lines = [g["sentence"] for g in gen if g["field"] in ("access.not_held", "sources.json not_of_a_type")]
    assert lines == ["We found Evidence and gap map of interventions but could not hold it, so nothing on this "
                     "page draws on it.",
                     "We found Inclusion Matters but it is not of a type we can check, so nothing on this page "
                     "draws on it."]
    assert not any("We could not obtain" in g["sentence"] for g in gen)     # one line per unheld source
    assert all(LS.is_framed(x) for x in lines)                              # recognised as generated
    import orchestrator as O
    src = (W / "orchestrator.py").read_text()
    assert "held = R.held_texts(ctx.slug)" in src[src.index("def _passages"):src.index("def _cite_numbers")]


def test_b_none_of_these_is_allowed_and_recorded_never_forced(tmp_path):
    import orchestrator as O
    from orch import model_steps as M
    assert M.NO_TYPE == O.NO_TYPE == "none of these"
    assert "none of these" in M.discover_prompt("q?", 8, ["review"])
    rows = M.discover_proposals({"sources": [
        {"title": "A map", "first_author": "W", "year": 2021, "type": "none of these", "url": "u"},
        {"title": "A review", "first_author": "S", "year": 2024, "type": "review", "url": "u"}]}, {"review"}, 8)
    assert [r["type"] for r in rows] == ["none of these", "review"]
    with pytest.raises(M.StepFailed):
        M.discover_proposals({"sources": [{"title": "x", "first_author": "y", "type": "made up"}]}, {"review"}, 8)
    c = _case(tmp_path)
    (c / "sources.json").unlink()
    found = SimpleNamespace(identifier=SimpleNamespace(kind="doi", value="10.1/x"), heading="Found title",
                            registry="europepmc", extra={})
    reply = json.dumps({"sources": [
        {"title": "A map", "first_author": "W", "year": 2021, "type": "none of these", "url": "https://x.org/m"},
        {"title": "A review", "first_author": "S", "year": 2024, "type": "review", "url": "https://x.org/r"}]})
    ctx = SimpleNamespace(case=c, slug="orch-x", ask=lambda p, n, r: reply, search=lambda t, a, y, k: found,
                          replies=[])
    O.code_discover(ctx, ST.BY_NAME["discover"])
    doc = json.loads((c / "sources.json").read_text())
    assert [s["type"] for s in doc["sources"]] == ["review"]                 # never forced into a type
    assert doc["not_of_a_type"][0]["title"] == "Found title"


def test_c_a_pmc_article_is_confirmed_through_europe_pmc_never_as_an_agency_site():
    import orchestrator as O
    miss = SimpleNamespace(reason="Europe PMC returned no record for the title", status="NOT_FOUND")
    prop = [{"title": "A systematic review of academic performance", "first_author": "K", "year": 2024,
             "type": "review", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10844053/"}]
    seen = []

    def by_pmcid(pmcid, title, a, y):
        seen.append(pmcid)
        return SimpleNamespace(identifier=SimpleNamespace(kind="pmid", value="38322967"), heading=title,
                               registry="europepmc", extra={"pmcid": pmcid})
    srcs, unres = O.resolve_proposals(prop, lambda t, a, y, k: miss, by_pmcid)
    assert seen == ["PMC10844053"] and srcs[0]["registry"] == "europepmc" and srcs[0]["pmid"] == "38322967"
    assert srcs[0]["url"] == "https://europepmc.org/article/PMC/PMC10844053"
    srcs, unres = O.resolve_proposals(prop, lambda t, a, y, k: miss, lambda *a: miss)
    assert srcs == [] and len(unres) == 1                                    # not admitted as an agency site
    assert O.is_pmc("pmc.ncbi.nlm.nih.gov", "") and not O.is_pmc("who.int", "")
    srcs, _ = O.resolve_proposals([dict(prop[0], url="https://www.cdc.gov/x", title="CDC page")],
                                  lambda t, a, y, k: miss, lambda *a: miss)
    assert srcs and "agency" in srcs[0]["registry"]                          # the agency rule still stands


def test_c_resolver_checks_a_pmcid_record_like_a_title_search():
    from orch import resolve as RV
    rec = {"title": "A systematic review of academic performance of children", "authorString": "Kim A, Lee B.",
           "pubYear": "2024", "pmid": "38322967", "pmcid": "PMC10844053"}
    got = RV.search_pmcid("PMC10844053", "A systematic review of academic performance of children", "Kim", 2024,
                          lookup=lambda v, f: rec if (v, f) == ("PMC10844053", "PMCID") else None)
    assert got.identifier.value == "38322967" and got.extra["pmcid"] == "PMC10844053"
    bad = RV.search_pmcid("PMC10844053", "Something else entirely about fish", "Kim", 2024, lookup=lambda v, f: rec)
    assert isinstance(bad, RV.Unresolved)


def test_d_study_log_cost_is_the_steps_own_ledger_rows():
    import orchestrator as O
    rows = [{"issue": "x", "step": "premise", "at": "2026-11-07T10:21:00+00:00", "usd": 0.034},
            {"issue": "x", "step": "discover", "at": "2026-11-07T10:21:40+00:00", "usd": 0.49},
            {"issue": "y", "step": "discover", "at": "2026-11-07T10:21:40+00:00", "usd": 5.0},
            {"issue": "x", "step": "discover", "at": "2026-11-07T09:00:00+00:00", "usd": 7.0}]
    assert round(O.step_cost(rows, "x", "discover", "2026-11-07T10:21:00+00:00"), 3) == 0.49


# ---------------------------------------------------------------------------------------------------- corrections
# Advisor's ruling 2026-11-07 on corrections and retractions; recorded Europe PMC and Crossref responses for attempt
# 3's S002 (retracted) and S003 (erratum, not held), and a synthetic held-source erratum that changes a figure.

FX = ROOT / "backend/tests/fixtures/whu_orch_corrections"


def _rec(name):
    return json.loads((FX / name).read_text())["resultList"]["result"][0]


def _lookup(kind, value):
    table = {("PMCID", "PMC10844053"): "epmc_PMC10844053.json", ("PMCID", "PMC8356326"): "epmc_PMC8356326.json",
             ("PMID", "37133285"): "epmc_MED_37133285.json", ("PMID", "40535238"): "epmc_MED_40535238.json"}
    name = table.get((kind, value))
    return (_rec(name), "matched") if name else (None, "Europe PMC has no record for %s %s" % (kind, value))


def _crossref(doi):
    if doi.lower() == "10.1016/j.heliyon.2024.e25216":
        return json.loads((FX / "crossref_heliyon_e25216.json").read_text())["message"], "matched"
    return None, "Crossref returned no record for DOI %s" % doi


def _fulltext(pmcid):
    return None, "HTTP 500 (recorded: %s)" % (FX / "epmc_fulltext_PMC8356339_http500.json").read_text()[:40]


S002 = {"id": "S002", "type": "review", "used_for": "x", "pmcid": "PMC10844053",
        "title": "A systematic review of academic performance of Children with Disabilities (CWDs) in inclusive "
                 "education schools in Low and Middle-Income Countries (LMICs)",
        "url": "https://europepmc.org/article/PMC/PMC10844053", "access": {"state": "full_text_held"}}
S003 = {"id": "S003", "type": "assessment_summary", "used_for": "x", "doi": "10.1002/cl2.1070",
        "title": "Evidence and gap map of studies assessing the effectiveness of interventions for people with "
                 "disabilities in low-and middle-income countries.",
        "url": "https://europepmc.org/article/PMC/PMC8356326",
        "access": {"last_fetch": {"on": "2026-11-07", "result": "not fetched", "why": "form check"}}}


def test_retraction_found_in_europe_pmc_and_crossref_for_attempt_3s_s002():
    from orch import corrections as CR
    st = CR.status(S002, _lookup, _crossref)
    assert st["retracted"]
    assert "Europe PMC pubType: Retracted Publication" in st["why"]
    assert any(w.startswith("Europe PMC: Retraction in 40535238") for w in st["why"])
    assert any(w.startswith("Crossref: retraction 10.1016/j.heliyon.2025.e43334") for w in st["why"])


def test_acquire_treats_a_retracted_source_as_not_held_and_the_page_says_so(tmp_path):
    import orchestrator as O
    import lean_sentences as LS
    c = _case(tmp_path)
    held = {"id": "S001", "type": "review", "title": "A held review", "used_for": "x",
            "access": {"state": "full_text_held"}}
    (c / "sources.json").write_text(json.dumps({"sources": [held, S002, S003]}))
    ctx = SimpleNamespace(case=c, lookup=_lookup, crossref=_crossref, fulltext=_fulltext)
    out = O.code_acquire(ctx, ST.BY_NAME["acquire"])
    assert out["lines"] == {"S002": "retracted", "S003": "could_not_hold"} and out["outcome"] == "1 held, 2 not held"
    doc = json.loads((c / "sources.json").read_text())
    s2, s3 = doc["sources"][1], doc["sources"][2]
    assert s2["access"]["state"] == "blocked" and s2["retraction_check"]["retracted"]
    assert "correction_notices" not in s3                          # (2): a correction to a source not held: nothing
    assert s3["retraction_check"]["corrections"] == [{"id": "37133285", "registry": "MED", "type": "Erratum in"}]
    lines = [g["sentence"] for g in LS.generate({}, doc["sources"]) if g["field"] == "access.not_held"]
    assert lines[0] == ("We found %s but it has been retracted, so nothing on this page draws on it."
                        % LS.found_label(doc["sources"], S002["title"], "S002"))
    assert lines[1].endswith("but could not hold it, so nothing on this page draws on it.")


def test_errata_passes_a_correction_to_a_source_not_held_and_one_held_as_a_linked_record(monkeypatch):
    import errata as E
    srcs = [dict(S003, access={"state": "blocked", "not_held": {"line": "could_not_hold"}}),
            {"id": "S004", "title": "T", "access": {"state": "full_text_held"},
             "correction_notices": [{"id": "999", "held": True}]},
            {"id": "S005", "title": "U", "access": {"state": "full_text_held"}}]
    checked = {"S003": {"state": "AMENDED", "amendments": [{"type": "Erratum in", "id": "37133285"}]},
               "S004": {"state": "AMENDED", "amendments": [{"type": "Erratum in", "id": "999"}]},
               "S005": {"state": "AMENDED", "amendments": [{"type": "Erratum in", "id": "777"}]}}
    monkeypatch.setattr(E.store, "sources", lambda slug: srcs)
    monkeypatch.setattr(E.store, "held", lambda slug: {"S004": {}, "S005": {}})
    monkeypatch.setattr(E, "load", lambda slug: {"checked": checked})
    rows = {r[0]: r for r in E.preflight_rows("x")}
    assert rows["corrections to sources not held"][1] == "ok" and rows["corrections to sources not held"][2].endswith("S003")
    assert rows["corrections obtained and read"][1] == "ok" and rows["corrections obtained and read"][2].endswith("S004")
    assert rows["corrections not yet read"][1] == "BLOCKED" and "S005" in rows["corrections not yet read"][2]


def test_a_held_sources_notice_that_cannot_be_held_makes_it_not_held(tmp_path):
    import orchestrator as O
    import lean_sentences as LS
    c = _case(tmp_path)
    held = dict(S003, access={"state": "full_text_held"})           # S003 as if held; its notice serves no text
    (c / "sources.json").write_text(json.dumps({"sources": [held]}))
    ctx = SimpleNamespace(case=c, lookup=_lookup, crossref=lambda d: (None, "none"), fulltext=_fulltext)
    with pytest.raises(O.RunStop, match="no source is held"):
        O.code_acquire(ctx, ST.BY_NAME["acquire"])
    doc = json.loads((c / "sources.json").read_text())
    assert doc["sources"][0]["access"]["not_held"]["line"] == "correction_not_held"
    line = [g["sentence"] for g in LS.generate({}, doc["sources"]) if g["field"] == "access.not_held"][0]
    assert line.endswith("but it has a published correction we could not hold, so nothing on this page draws on it.")


NOTICE = ("Correction to: Smith et al. In the Results, the sentence 'the pooled effect on attendance was 0.45 "
          "(95% CI 0.30 to 0.60)' should read 'the pooled effect on attendance was 0.54 (95% CI 0.39 to 0.69)'. "
          "The authors apologise for the error.")


def test_a_held_source_erratum_that_changes_a_figure_removes_the_sentence_unless_it_rebinds(tmp_path):
    from orch import corrections as CR
    c = tmp_path / "case"
    (c / "corrections").mkdir(parents=True)
    (c / "corrections" / "N1.txt").write_text(NOTICE)
    (c / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "access": {"state": "full_text_held"},
         "correction_notices": [{"id": "N1", "held": True, "file": "corrections/N1.txt"}]},
        {"id": "S002", "access": {"state": "full_text_held"}}]}))
    span = "In the pooled analysis the effect on attendance was 0.45 (95% CI 0.30 to 0.60) across 12 trials."
    rows = {"a": {"sentence": "Programmes raised attendance by 0.45 standard deviations [1].", "source_id": "S001",
                  "span": span},
            "b": {"sentence": "Programmes raised attendance by 0.54 standard deviations [1].", "source_id": "S001",
                  "span": span},
            "c": {"sentence": "Teacher training was the most common programme [1].", "source_id": "S001",
                  "span": "Teacher training appeared in most included studies of the review."},
            "d": {"sentence": "Another source says 0.45 too [2].", "source_id": "S002", "span": span}}
    removed = []
    counts = CR.sweep(c, rows, [r["sentence"] for r in rows.values()], removed.append)
    assert [r["sentence"] for r in removed] == [rows["a"]["sentence"]]
    assert removed[0]["ref"]["reason"] == "removed: affected by correction N1"
    assert rows["b"]["corrected_by"] == "N1" and "corrected_by" not in rows["c"] and "corrected_by" not in rows["d"]
    assert counts == {"checked": 3, "removed": 1, "rebound": 1}
    assert CR.affected("they found no effect on attendance was large", NOTICE) is False
    assert CR.affected("In the Results, the sentence on the pooled effect on attendance was large", NOTICE) is True  # 5-word run
    assert CR.figures("In Table 2 of 2019, 3 trials found 0.45 and 12%") == {"0.45", "12%"}


def test_the_corrections_step_runs_before_the_first_commit_and_in_the_repeat_group():
    i = ST.NAMES.index
    assert i("judgements") < i("corrections_3b") < i("commit_3b")
    assert i("overstatement") < i("corrections") < i("final_gate") and ST.BY_NAME["corrections"].repeat_group
    assert "corrections/*" in ST.BY_NAME["acquire"].owns


def test_identifiers_may_be_added_after_discover_never_changed(tmp_path):
    c = _case(tmp_path)
    frozen = CH.frozen_now(c)
    doc = json.loads((c / "sources.json").read_text())
    doc["sources"][0]["pmid"] = "38322967"                       # sweep_sources confirms a PMID: allowed
    (c / "sources.json").write_text(json.dumps(doc))
    assert not CH.frozen_breaks(c, {"identifiers": frozen["identifiers"], "source_list": frozen["source_list"]})
    frozen = CH.frozen_now(c)
    doc["sources"][0]["pmid"] = "11111111"                       # a changed one: never
    (c / "sources.json").write_text(json.dumps(doc))
    assert CH.frozen_breaks(c, {"identifiers": frozen["identifiers"]})


# ---------------------------------------------------------------------------------------------------- expression of concern
# Advisor's ruling 2026-11-07 (after attempt 4): an expression of concern on any source is treated like a retraction.

def test_an_expression_of_concern_is_found_in_europe_pmc_and_crossref():
    from orch import corrections as CR
    src = {"id": "S001", "pmcid": "PMC1", "doi": "10.1/x", "title": "A trial of something"}
    rec = {"title": "A trial of something", "pmcid": "PMC1", "doi": "10.1/x",
           "commentCorrectionList": {"commentCorrection": [{"type": "Expression of concern in", "id": "123",
                                                            "source": "MED"}]}}
    st = CR.status(src, lambda k, v: (rec, "matched") if v == "PMC1" else (None, "no"), lambda d: (None, "no"))
    assert st["concern"] and not st["retracted"] and st["why"] == ["Europe PMC: Expression of concern in 123"]
    msg = {"title": ["A trial of something"], "updated-by": [{"DOI": "10.1/eoc", "type": "expression_of_concern"}]}
    st = CR.status(src, lambda k, v: (None, "no"), lambda d: (msg, "matched"))
    assert st["concern"] and st["why"] == ["Crossref: expression_of_concern 10.1/eoc"]


def test_acquire_treats_an_expression_of_concern_like_a_retraction(tmp_path):
    import orchestrator as O
    import lean_sentences as LS
    c = _case(tmp_path)
    eoc = {"id": "S002", "type": "review", "title": "A review under concern", "used_for": "x", "doi": "10.1/eoc-src",
           "access": {"state": "full_text_held"}}
    held = {"id": "S001", "type": "review", "title": "A held review", "used_for": "x",
            "access": {"state": "full_text_held"}}
    (c / "sources.json").write_text(json.dumps({"sources": [held, eoc]}))
    msg = {"title": ["A review under concern"], "updated-by": [{"DOI": "10.1/n", "type": "expression_of_concern"}]}
    ctx = SimpleNamespace(case=c, lookup=lambda k, v: (None, "no"),
                          crossref=lambda d: (msg, "matched") if d == "10.1/eoc-src" else (None, "no"))
    out = O.code_acquire(ctx, ST.BY_NAME["acquire"])
    assert out["lines"] == {"S002": "concern"} and out["outcome"] == "1 held, 1 not held"
    doc = json.loads((c / "sources.json").read_text())
    assert doc["sources"][1]["access"]["state"] == "blocked" and doc["sources"][1]["retraction_check"]["concern"]
    line = [g["sentence"] for g in LS.generate({}, doc["sources"]) if g["field"] == "access.not_held"][0]
    assert line == ("We found A review under concern but its journal has issued an expression of concern, so "
                    "nothing on this page draws on it.")


def test_a_notice_is_its_body_never_its_front_matter():
    from orch import corrections as CR
    xml = (FX / "epmc_fulltext_PMC9968378.xml").read_text()       # attempt 4's held notice for S002
    body = CR._notice_body(xml)
    assert body.startswith("The article listed below") and "9968378" not in body and "36913230" not in body
    assert "2023" not in CR.figures(body) and "1315" not in CR.figures(body)


def test_a_stage_librarys_system_exit_is_recorded_and_the_run_record_written(tmp_path, monkeypatch):
    import orchestrator as O
    c = _case(tmp_path)
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.frozen, ctx.log = "orch-x", c, "trial", tmp_path, None, {}, []
    ctx.page_json = c / "draft" / "page.json"
    monkeypatch.setattr(O, "_study_log", lambda *a: None)
    monkeypatch.setattr(O.ST, "STEPS", (ST.Step("coverage", "code", code="exits"),))

    def exits(ctx, step):
        raise SystemExit("out_of_scope needs --element: words of the question or a scope.out entry")
    monkeypatch.setitem(O.STEP_CODE, "exits", exits)
    monkeypatch.setenv("WHU_ORCH_LOCK", str(tmp_path / "lock"))
    out = O.run(ctx)
    assert out["result"] == "Not Ready: SystemExit: out_of_scope needs --element: words of the question or a scope.out entry"
    assert out["steps"][0]["step"] == "coverage" and out["steps"][0]["failed"].startswith("SystemExit")


# ---------------------------------------------------------------------------------------------------- after attempt 4
# Advisor's rulings 2026-11-07: (1) coverage out_of_scope needs a checked element; (2) a multi-article notice applies
# to a held source only if its text names the source.

OUTS = ["Education outcomes in high-income countries", "Health or employment outcomes of disabled adults"]
QUESTION = ("In low- and middle-income countries, do programmes meant to improve education for children and young "
            "people with disabilities work, and which kinds work best?")


def test_coverage_element_must_be_an_entry_or_a_question_phrase():
    from orch import model_steps as M
    assert M.element_ok("Education outcomes in high-income countries", OUTS, QUESTION)
    assert M.element_ok("  education outcomes in high-income countries. ", OUTS, QUESTION)     # case, spacing
    assert M.element_ok("children and young people", OUTS, QUESTION)
    assert not M.element_ok("young", OUTS, QUESTION)                                          # one word
    assert not M.element_ok("adult literacy programmes", OUTS, QUESTION)                      # neither
    assert not M.element_ok("", OUTS, QUESTION)


def test_coverage_re_asks_once_then_leaves_the_finding_in_scope_never_not_material():
    from orch import model_steps as M
    prompts = []

    def ask(prompt, n, role):
        prompts.append(prompt)
        return json.dumps({"decision": "out_of_scope", "why": "w", "element": "adult literacy", "sentence": ""})
    d = M.coverage_decision(QUESTION, "{}", "a finding", ask, OUTS)
    assert d["decision"] == "in_scope" and len(prompts) == 2
    assert "OUT-OF-SCOPE ENTRIES:\n- Education outcomes in high-income countries" in prompts[0]
    assert "Your last answer was out_of_scope" in prompts[1] and "Your last answer" not in prompts[0]
    replies = iter([json.dumps({"decision": "out_of_scope", "why": "w", "element": "adult literacy"}),
                    json.dumps({"decision": "out_of_scope", "why": "w", "element": OUTS[1]})])
    d = M.coverage_decision(QUESTION, "{}", "a finding", lambda p, n, r: next(replies), OUTS)
    assert d == {"decision": "out_of_scope", "why": "w", "element": OUTS[1]}


def test_coverage_step_declares_with_the_element_and_leaves_in_scope_findings_open(tmp_path, monkeypatch):
    import orchestrator as O
    import coverage_check as C
    c = _case(tmp_path)
    (c / "premise.json").write_text(json.dumps({"scope": {"covers": "c", "out": [{"what": OUTS[0], "why": "y"}]}}))
    (c / "issue.json").write_text(json.dumps({"slug": "orch-x", "question": QUESTION}))
    Page({"title": "T", "blocks": []}).save(c / "draft" / "page.json")
    declared = []
    monkeypatch.setattr(C, "declare", lambda slug, key, state, why, by, element="": declared.append((key, state, element)))
    monkeypatch.setattr(O, "_open_units", lambda ctx: [{"key": "S001@1-2", "text": "u1"}, {"key": "S001@3-4", "text": "u2"}])
    monkeypatch.setattr(O, "_rerender", lambda ctx, page: None)
    replies = iter([json.dumps({"decision": "out_of_scope", "why": "w", "element": OUTS[0]}),
                    json.dumps({"decision": "out_of_scope", "why": "w", "element": "x y z"}),
                    json.dumps({"decision": "out_of_scope", "why": "w", "element": "x y z"})])
    ctx = SimpleNamespace(case=c, slug="orch-x", page_json=c / "draft" / "page.json", ask=lambda p, n, r: next(replies),
                          replies=[])
    out = O.code_coverage(ctx, ST.BY_NAME["coverage"])
    assert declared == [("S001@1-2", "out_of_scope", OUTS[0])]                  # never "not_material" by default
    assert out["outcome"] == "2 coverage decision(s), 1 left in scope"
    row = json.loads((c / "rulings" / "coverage_in_scope.jsonl").read_text().splitlines()[0])
    assert row["unit"] == "S001@3-4"
    assert "rulings/coverage_in_scope.jsonl" in ST.BY_NAME["coverage"].owns


def test_a_multi_article_notice_that_does_not_name_the_source_is_a_correction_we_could_not_read(tmp_path):
    import orchestrator as O
    import lean_sentences as LS
    from orch import corrections as CR
    s002 = {"id": "S002", "type": "synthesis", "used_for": "x", "pmcid": "PMC9700054", "doi": "10.1002/cl2.1287",
            "title": "Teacher professional development for disability inclusion in low- and middle-income "
                     "Asia-Pacific countries: An evidence and gap map.",
            "url": "https://europepmc.org/article/PMC/PMC9700054", "access": {"state": "full_text_held"}}
    body = CR._notice_body((FX / "epmc_fulltext_PMC9968378.xml").read_text())
    assert not CR.names_source(body, s002)                                     # attempt 4's S002 and its notice
    assert CR.names_source("This corrects the article doi: 10.1002/cl2.1287. Table 2 should read 0.54.", s002)
    assert CR.names_source("In 'Teacher professional development for disability inclusion in low- and middle-income "
                           "Asia-Pacific countries: An evidence and gap map', Table 2 should read 0.54.", s002)
    assert not CR.names_source("doi 10.1002/cl2.12870 is another article", s002)
    held = {"id": "S001", "type": "review", "title": "A held review", "used_for": "x",
            "access": {"state": "full_text_held"}}
    c = _case(tmp_path)
    (c / "sources.json").write_text(json.dumps({"sources": [held, s002]}))

    def lookup(kind, value):
        table = {("PMCID", "PMC9700054"): "epmc_PMC9700054.json", ("PMID", "36913230"): "epmc_MED_36913230.json"}
        return (_rec(table[(kind, value)]), "matched") if (kind, value) in table else (None, "no record")
    ctx = SimpleNamespace(case=c, lookup=lookup, crossref=lambda d: (None, "no"),
                          fulltext=lambda pmcid: (CR._notice_body((FX / "epmc_fulltext_PMC9968378.xml").read_text()),
                                                  "recorded"))
    out = O.code_acquire(ctx, ST.BY_NAME["acquire"])
    assert out["lines"] == {"S002": "correction_unread"}
    doc = json.loads((c / "sources.json").read_text())
    line = [g["sentence"] for g in LS.generate({}, doc["sources"]) if g["field"] == "access.not_held"][0]
    assert line.endswith("but it has a published correction we could not read, so nothing on this page draws on it.")
    assert "correction_notices" not in doc["sources"][1]


# ---------------------------------------------------------------------------------------------------- after attempt 5
# Advisor's ruling 2026-11-07: the commit step's git runs in the shell's own environment; the tests are hermetic.

def test_no_whu_variable_reaches_a_test():
    assert not [k for k in os.environ if k.startswith("WHU_")]


def test_the_commit_step_runs_git_without_any_whu_variable_and_keeps_its_checks(tmp_path, monkeypatch):
    import orchestrator as O
    for k, v in {"WHU_LEAN": "1", "WHU_ORCH_MODE": "paid", "WHU_ORCH_STEP": "commit_3b", "WHU_ORCH_TOKEN": "t",
                 "WHU_ORCH_PAID_RULED": "orchestrator trial 1"}.items():
        monkeypatch.setenv(k, v)
    c = tmp_path / "issues" / "WHU-T-orch-x"
    c.mkdir(parents=True)
    seen, staged, pushed = [], ["issues/WHU-T-orch-x/a.json"], {"out": "abc..def  main -> main"}

    def run(argv, **kw):
        seen.append((argv[3], kw.get("env")))
        out = {"diff": "\n".join(staged), "push": pushed["out"], "rev-parse": "deadbeef" * 5}.get(argv[3], "")
        return SimpleNamespace(stdout=out, stderr="", returncode=0)
    monkeypatch.setattr(O.subprocess, "run", run)
    ctx = SimpleNamespace(mode="paid", root=tmp_path, case=c, slug="orch-x", rel=lambda p: p.relative_to(tmp_path).as_posix(),
                          first=None)
    out = O.code_commit(ctx, ST.BY_NAME["commit_3b"])
    assert out["outcome"].startswith("committed") and ctx.first
    assert [a for a, _ in seen] == ["add", "diff", "commit", "push", "rev-parse"]
    assert all(env is not None and not [k for k in env if k.startswith("WHU_")] for _, env in seen)
    assert os.environ["WHU_LEAN"] == "1"                                    # the orchestrator's own env is untouched
    staged[:] = ["issues/WHU-T-orch-x/a.json", "backend/data/spend/ledger.jsonl"]
    with pytest.raises(O.RunStop, match="outside the case folder"):
        O.code_commit(ctx, ST.BY_NAME["commit_3b"])
    staged[:] = ["issues/WHU-T-orch-x/a.json"]
    pushed["out"] = "Everything up-to-date"
    with pytest.raises(O.RunStop, match="main -> main"):
        O.code_commit(ctx, ST.BY_NAME["commit_3b"])
