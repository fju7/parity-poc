"""One limits table for every model call site of an orchestrated run (advisor's ruling 1 on the design review of
2026-11-26, study/whu-reliability/next_phase/design_review_2026-11.md §1; reply_limits.py).

  * every limit is at least twice the longest reply measured for its call site in the spend ledger's orchestrated
    rows (rows carrying `step`), with pooled older rows censored at the call site's own limit at the time ($0: reads
    the ledger);
  * every orchestrated ledger row maps to a call site in the table; new rows carry `call_site`;
  * no call site writes its own limit;
  * a cut-off reply is re-asked once with the limit doubled at every call site (audit_stage.Caller,
    factcheck_draft.call, orch/google.Gateway); a second cut-off takes the step's existing fail-safe.
Models are stubs; nothing is spent.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
LEDGER = ROOT / "backend" / "data" / "spend" / "ledger.jsonl"

import reply_limits as RL  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# (step) -> [(call site, its limit while the rows were written)] for audit_stage.Caller rows without `call_site`
# (role "audit" for every call). A reply longer than a site's limit at the time would have been cut off and stopped
# the run; so a pooled row counts toward a site only up to that site's limit then.
HISTORICAL_CALLER = {
    "premise": [("premise", 4000)],
    "draft": [("draft", 30000)],
    "coverage": [("coverage", 600)],
    "premise_reading": [("premise-reading", 1500)],
    "judgements": [("ruling", 4000), ("judgement-sentence", 500)],
    "audit": [("audit-read", 12000), ("audit-rule", 1500), ("ruling", 4000)],
}
RULING_STEPS = {"advocate", "omissions", "changecheck", "findings", "conclusions", "dangling", "corrections",
                "corrections_3b", "gate", "final_gate", "overstatement"}


def _orchestrated_rows():
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("step"):
            yield r


def _sites_of(r):
    """[(site, censor)] for one orchestrated ledger row."""
    if r.get("call_site"):
        # A row written before "-requote" was a site suffix (the fresh Q1-01's one "second-read-requote" row,
        # 2026-11-26) carries the raw role; the ledger is never edited, so it is mapped here as the Caller now maps it.
        site = r["call_site"]
        return [(site if site in RL.LIMITS else RL.site_of_role(site), None)]
    script, role, step = r.get("script", ""), r.get("role", ""), r.get("step", "")
    if script == "audit_stage.py":
        if step in HISTORICAL_CALLER:
            return HISTORICAL_CALLER[step]
        if step in RULING_STEPS:
            return [("ruling", 4000)]
        raise AssertionError("an audit_stage.py row in step %r maps to no call site" % step)
    if script == "factcheck_draft.py":
        return [(RL.site_of_label(role), None)]
    if script == "orch/google.py":
        return [(role, None)]
    raise AssertionError("an orchestrated ledger row from %r maps to no call site" % script)


def measured() -> dict:
    out = {}
    for r in _orchestrated_rows():
        for site, censor in _sites_of(r):
            n = int(r.get("output") or 0)
            if censor is not None:
                n = min(n, censor)
            out[site] = max(out.get(site, 0), n)
    return out


def test_every_orchestrated_ledger_row_maps_to_a_call_site_in_the_table():
    sites = measured()
    assert sites, "no orchestrated rows in the ledger"
    assert set(sites) <= set(RL.LIMITS), sorted(set(sites) - set(RL.LIMITS))


def test_every_limit_is_at_least_twice_the_longest_measured_reply():
    short = {s: (RL.LIMITS[s], m) for s, m in measured().items() if RL.LIMITS[s] < 2 * m}
    assert not short, "limit under 2x the measured max (limit, measured): %r" % short


def test_the_limits_found_short_in_the_design_review_are_raised():
    # design review §1: coverage 600 vs 566, premise_reading 1500 vs 1225 (then cut off), belief 1500 vs 2051,
    # discover 4000 vs 2291; judgement_sentence 500 and the audit rule 1500 censored
    assert RL.LIMITS["coverage"] >= 1132 and RL.LIMITS["premise-reading"] >= 3000
    assert RL.LIMITS["fc:belief-outlet"] >= 4102 and RL.LIMITS["fc:discover"] >= 4582
    assert RL.LIMITS["judgement-sentence"] >= 1000 and RL.LIMITS["audit-rule"] >= 3000


def test_no_call_site_writes_its_own_limit():
    import audit_stage as A
    import ruling as R
    from orch import steps as ST
    G = _load("google_rl_t", W / "orch" / "google.py")
    assert A.READ_MAX_OUT == RL.LIMITS["audit-read"] and A.RULE_MAX_OUT == RL.LIMITS["audit-rule"]
    assert R.MAX_OUT == RL.LIMITS["ruling"] and G.MAX_OUT == RL.LIMITS["overstatement"]
    assert ST.REPLY_LIMITS["coverage"] == RL.LIMITS["coverage"]
    assert ST.REPLY_LIMITS["discover"] == RL.LIMITS["fc:discover"]
    pr = (W / "orch" / "premise_reading.py").read_text(encoding="utf-8")
    assert not re.search(r"ask_json\([^)]*\b\d{3,}\b", pr.replace("\n", " ")), "a number in premise_reading's asks"
    assert "max_tokens=600" not in (W / "conclusion_judge.py").read_text(encoding="utf-8")


def test_every_factcheck_label_an_orchestrated_stage_uses_has_a_limit():
    srcs = [p for p in W.glob("*.py")] + [W / "orchestrator.py", ROOT / "backend/scripts/signal/factcheck_draft.py"]
    labels = set()
    for p in srcs:
        for m in re.finditer(r'label\s*=\s*f?["\']([A-Za-z_\-]+)', p.read_text(encoding="utf-8")):
            labels.add(m.group(1))
    missing = {lab for lab in labels if RL.site_of_label(lab) not in RL.LIMITS}
    assert not missing, sorted(missing)


@pytest.mark.parametrize("role,site", [
    ("premise", "premise"), ("judgement_sentence", "judgement-sentence"), ("premise-reading", "premise-reading"),
    ("read", "audit-read"), ("read-escalate", "audit-read"), ("read-summary", "audit-read"),
    ("second-read", "audit-read"), ("rule", "audit-rule"), ("rule-reask", "audit-rule"),
    ("rule-second-reask", "audit-rule"), ("rule-repeat", "audit-rule"), ("rule-relevance", "ruling"),
    ("rule-gate-retry", "ruling"), ("rule-advocate-one-sentence", "ruling"), ("rule-changecheck-repeat", "ruling"),
    ("coverage-cutoff-reask", "coverage")])
def test_caller_roles_map_to_their_call_site(role, site):
    assert RL.site_of_role(role) == site


# --- audit_stage.Caller ------------------------------------------------------------------------------------------

class Model:
    def __init__(self, cuts):
        self.cuts, self.limits = list(cuts), []

    def __call__(self, prompt, max_tokens):
        self.limits.append(max_tokens)
        cut = self.cuts.pop(0) if self.cuts else False
        usage = {"input": 10, "output": max_tokens if cut else 5, "usd": 0.01}
        if cut:
            return '{"a": ', dict(usage, stop_reason="max_tokens")
        return '{"a": 1}', usage


@pytest.fixture
def A():
    return _load("audit_stage_rl_t", W / "audit_stage.py")


def test_caller_outside_an_orchestrated_run_raises_at_once(A, monkeypatch):
    for k in ("WHU_ORCH_STEP", "WHU_ORCH_MODE"):
        monkeypatch.delenv(k, raising=False)
    m = Model([True])
    with pytest.raises(A.ReplyCutOff):
        A.Caller(cap=1, ledger_issue="t", ask=m)("p", 1000, "coverage")
    assert m.limits == [1000]


def test_caller_reasks_once_with_the_limit_doubled(A, monkeypatch, tmp_path):
    monkeypatch.setenv("WHU_ORCH_MODE", "paid")
    log = tmp_path / "cut.jsonl"
    monkeypatch.setenv("WHU_ORCH_CUTOFF_LOG", str(log))
    m = Model([True, False])
    text, _u = A.Caller(cap=1, ledger_issue="t", ask=m)("p", 1200, "coverage")
    assert text == '{"a": 1}' and m.limits == [1200, 2400]
    ev = [json.loads(x)["event"] for x in log.read_text().splitlines()]
    assert ev == ["cut_off", "reask"]


def test_caller_second_cutoff_raises_marked_reasked(A, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_MODE", "paid")
    m = Model([True, True])
    with pytest.raises(A.ReplyCutOff) as e:
        A.Caller(cap=1, ledger_issue="t", ask=m)("p", 3000, "premise-reading")
    assert e.value.reasked is True and m.limits == [3000, 6000]


def test_ruling_does_not_retry_after_a_doubled_reask(A, monkeypatch, tmp_path):
    import ruling as R
    monkeypatch.setenv("WHU_ORCH_MODE", "paid")
    m = Model([True, True, False])
    call = A.Caller(cap=1, ledger_issue="t", ask=m)

    def c(prompt, max_tokens, role):
        try:
            return call(prompt, max_tokens, role)
        except A.ReplyCutOff as e:       # ruling recognises a cut-off by attribute (other module instance)
            raise e
    monkeypatch.setattr(R, "build_prompt", lambda kind, p, grouped=False: "the prompt")
    with pytest.raises(R.RulingFailed):
        R.rule("gate", {"sentence": "s"}, 0, c, tmp_path / "log.jsonl", {})
    assert m.limits == [R.MAX_OUT, 2 * R.MAX_OUT]          # no third call at the same limit


# --- orch/google.Gateway -------------------------------------------------------------------------------------------

def test_google_cutoff_is_detected_and_reasked_doubled(monkeypatch):
    G = _load("google_rl_t2", W / "orch" / "google.py")
    finishes = ["FinishReason.MAX_TOKENS", "FinishReason.STOP"]
    limits = []

    class Models:
        def generate_content(self, model, contents, config):
            limits.append(config["max_output_tokens"] if isinstance(config, dict) else config.max_output_tokens)
            f = finishes.pop(0)
            return types.SimpleNamespace(
                model_version=G.MODEL, text='{"overstates": "no"}' if "STOP" in f else '{"over',
                candidates=[types.SimpleNamespace(finish_reason=f)], prompt_feedback=None,
                usage_metadata=types.SimpleNamespace(prompt_token_count=10, cached_content_token_count=0,
                                                     candidates_token_count=5, thoughts_token_count=0))
    gw = G.Gateway.__new__(G.Gateway)
    gw.issue, gw.preflight_record = "t", {"ok": True}
    gw._client = types.SimpleNamespace(models=Models())
    monkeypatch.setattr(gw, "client", lambda: gw._client, raising=False)
    monkeypatch.setattr(G.S, "orch_guard", lambda *a, **k: None)
    monkeypatch.setattr(G.S, "record", lambda **k: None)
    monkeypatch.setattr(G, "_config", lambda n: {"max_output_tokens": n})
    got = gw.call("text", "overstatement")
    assert limits == [G.MAX_OUT, 2 * G.MAX_OUT] and got["cut_off"] is False and "no" in got["text"]
    finishes[:] = ["FinishReason.MAX_TOKENS", "FinishReason.MAX_TOKENS"]
    limits.clear()
    got = gw.call("text", "overstatement")
    assert got["cut_off"] is True and got["text"] == "" and limits == [G.MAX_OUT, 2 * G.MAX_OUT]


def test_overstatement_takes_its_failsafe_after_a_second_cutoff():
    OV = _load("overstatement_rl_t", W / "orch" / "overstatement.py")
    calls = []

    class GW:
        def call(self, text, role):
            calls.append(role)
            return {"text": "", "model": "m", "usd": 0.0, "refused": False, "finish": "MAX_TOKENS", "cut_off": True}
    row = OV.check_one(GW(), {"passage": "p", "sentence": "s", "sentence_sha": "x", "source_id": "S1"})
    assert row["verdict"] == "yes" and len(calls) == 1


# --- factcheck_draft.call --------------------------------------------------------------------------------------------

class FCClient:
    def __init__(self, fc, cuts):
        self.fc, self.cuts, self.limits = fc, list(cuts), []
        self.messages = self

    def create(self, **kw):
        self.limits.append(kw["max_tokens"])
        cut = self.cuts.pop(0) if self.cuts else False
        return types.SimpleNamespace(
            model=self.fc.SIGNAL_MODEL, stop_reason="max_tokens" if cut else "end_turn",
            usage=types.SimpleNamespace(input_tokens=10, output_tokens=5, cache_creation_input_tokens=0,
                                        cache_read_input_tokens=0, server_tool_use=None),
            content=[types.SimpleNamespace(type="text", text='{"a": ' if cut else '{"a": 1}')])

    def stream(self, **kw):
        import contextlib
        msg = self.create(**kw)
        return contextlib.nullcontext(types.SimpleNamespace(get_final_message=lambda: msg))


@pytest.fixture
def fc(monkeypatch):
    sys.path.insert(0, str(ROOT / "backend" / "scripts" / "signal"))
    import contextlib
    import factcheck_draft as F
    fake = types.SimpleNamespace(orch_guard=lambda *a, **k: None, check_cap=lambda *a, **k: None,
                                 call_site=lambda s: contextlib.nullcontext(), record=lambda **k: None)
    monkeypatch.setattr(F, "_spend", fake)
    monkeypatch.setattr(F, "_ledger_now", lambda entry: None, raising=False)
    monkeypatch.setattr(F, "_LEDGER_ISSUE", "rl-test")
    monkeypatch.setattr(F, "_dump_truncated", lambda *a: "")
    monkeypatch.setattr(F.time, "sleep", lambda s: None)
    return F


def test_factcheck_call_takes_its_limit_from_the_table_and_reasks_doubled(fc, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_STEP", "discover")
    c = FCClient(fc, [True, False])
    monkeypatch.setattr(fc, "_get_client", lambda: c)
    got = fc.call("s", "u", search=False, label="discover", max_tokens=999, raw=True)
    assert got == '{"a": 1}' and c.limits == [RL.LIMITS["fc:discover"], 2 * RL.LIMITS["fc:discover"]]


def test_factcheck_second_cutoff_returns_none(fc, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_STEP", "belief")
    c = FCClient(fc, [True, True])
    monkeypatch.setattr(fc, "_get_client", lambda: c)
    assert fc.call("s", "u", search=False, label="belief-outlet", raw=True) is None
    assert c.limits == [RL.LIMITS["fc:belief-outlet"], 2 * RL.LIMITS["fc:belief-outlet"]]


def test_factcheck_outside_an_orchestrated_run_is_unchanged(fc, monkeypatch):
    for k in ("WHU_ORCH_STEP", "WHU_ORCH_MODE"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(fc, "_spend", None)
    c = FCClient(fc, [True])
    monkeypatch.setattr(fc, "_get_client", lambda: c)
    assert fc.call("s", "u", search=False, label="discover", max_tokens=999, raw=True) is None
    assert c.limits == [999]
