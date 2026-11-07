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
    assert group == ["findings", "conclusions", "audit", "overstatement", "final_gate", "commit_8", "changecheck"]
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
