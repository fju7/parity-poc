"""Advisor's ruling after orchestrator trial 1 attempt 22 (2026-11-24, option 3), at $0: in orchestrated mode every
model-provider call retries 4 times with backoff on 503, 529, 429, timeouts and connection errors; still unavailable,
the run stops Not Ready "model unavailable; run again later" (an outage stop); a check that could not run never
passes. Attempt 22 stopped on one Google 503 after 24 good overstatement calls."""
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "backend" / "scripts"
WHU = SCRIPTS / "whatholdsup"
sys.path.insert(0, str(WHU))
import orchestrator as O  # noqa: E402
from orch import google as G  # noqa: E402

PR = O.PR()
# the text of attempt 22's stop
GOOGLE_503 = ("503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. "
              "Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}")


class ServerError(Exception):           # google.genai.errors.ServerError carries .code
    def __init__(self, msg, code=503):
        super().__init__(msg)
        self.code = code


class APIStatusError(Exception):        # anthropic / openai status errors carry .status_code
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


class APITimeoutError(Exception):
    pass


class APIConnectionError(Exception):
    pass


@pytest.fixture
def orchestrated(tmp_path, monkeypatch):
    log = tmp_path / "model.jsonl"
    log.write_text("")
    monkeypatch.setenv(PR.LOG_ENV, str(log))
    slept = []
    monkeypatch.setattr(PR, "_sleep", slept.append)
    return SimpleNamespace(log=log, slept=slept)


def _flaky(fails, exc):
    n = {"calls": 0}

    def fn():
        n["calls"] += 1
        if n["calls"] <= fails:
            raise exc
        return "ok"
    return fn, n


# ----------------------------------------------------------------- the retry rule

@pytest.mark.parametrize("exc", [
    ServerError(GOOGLE_503), APIStatusError("overloaded_error", 529), APIStatusError("rate_limit_error", 429),
    APITimeoutError("Request timed out."), APIConnectionError("Connection error."), TimeoutError("read timeout"),
    ConnectionResetError("reset by peer"), Exception(GOOGLE_503)])
def test_each_ruled_error_is_retried(exc, orchestrated):
    fn, n = _flaky(2, exc)
    assert PR.call(fn, "google", "overstatement") == "ok" and n["calls"] == 3
    assert orchestrated.slept == [5, 15] and orchestrated.log.read_text() == ""


def test_four_retries_then_model_unavailable_logged(orchestrated):
    fn, n = _flaky(99, ServerError(GOOGLE_503))
    with pytest.raises(PR.ModelUnavailable, match="model unavailable; run again later"):
        PR.call(fn, "google", "overstatement")
    assert n["calls"] == 5 and orchestrated.slept == list(PR.RETRY_DELAYS) and len(PR.RETRY_DELAYS) == 4
    (line,) = PR.outages(orchestrated.log)
    assert line["provider"] == "google" and line["what"] == "overstatement" and line["attempts"] == 5


@pytest.mark.parametrize("exc", [APIStatusError("invalid_request_error", 400), APIStatusError("server", 500),
                                 ValueError("bad JSON"), KeyError("x")])
def test_other_errors_are_not_retried(exc, orchestrated):
    fn, n = _flaky(1, exc)
    with pytest.raises(type(exc)):
        PR.call(fn, "anthropic", "read")
    assert n["calls"] == 1 and orchestrated.slept == []


def test_outside_orchestrated_mode_nothing_changes(monkeypatch):
    monkeypatch.delenv(PR.LOG_ENV, raising=False)
    fn, n = _flaky(1, ServerError(GOOGLE_503))
    with pytest.raises(ServerError):
        PR.call(fn, "google", "x")
    assert n["calls"] == 1


# ----------------------------------------------------------------- the providers

class _Models:
    def __init__(self, fails):
        self.fails, self.calls = fails, 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        if self.calls <= self.fails:
            raise ServerError(GOOGLE_503)
        return SimpleNamespace(model_version=G.MODEL, usage_metadata=None, candidates=[], prompt_feedback=None,
                               text='{"x": 1}')


@pytest.fixture
def quiet_ledger(monkeypatch):
    monkeypatch.setattr(G.S, "orch_guard", lambda *a, **k: None)
    monkeypatch.setattr(G.S, "record", lambda **k: None)


def test_google_a_503_mid_run_is_retried_and_the_call_answers(orchestrated, quiet_ledger):
    gw = G.Gateway("whu-x", client=SimpleNamespace(models=_Models(0)))
    gw.preflight()
    gw._client.models.fails, gw._client.models.calls = 2, 0
    assert gw.call("text", "overstatement")["text"] == '{"x": 1}' and gw._client.models.calls == 3


def test_google_still_unavailable_is_model_unavailable_not_a_verdict(orchestrated, quiet_ledger):
    gw = G.Gateway("whu-x", client=SimpleNamespace(models=_Models(0)))
    gw.preflight()
    gw._client.models.fails, gw._client.models.calls = 99, 0
    with pytest.raises(PR.ModelUnavailable):
        gw.call("text", "overstatement")
    assert gw._client.models.calls == 5


def test_google_outside_orchestrated_mode_stops_as_before(monkeypatch, quiet_ledger):
    monkeypatch.delenv(PR.LOG_ENV, raising=False)
    gw = G.Gateway("whu-x", client=SimpleNamespace(models=_Models(0)))
    gw.preflight()
    gw._client.models.fails, gw._client.models.calls = 1, 0
    with pytest.raises(G.Stop, match="no reply from"):
        gw.call("text", "overstatement")


def _fc():
    if str(SCRIPTS / "signal") not in sys.path:
        sys.path.insert(0, str(SCRIPTS / "signal"))
    import factcheck_draft as fc
    return fc


class _Messages:
    def __init__(self, exc):
        self.exc, self.calls = exc, 0

    def create(self, **k):
        self.calls += 1
        raise self.exc


def _drive_fc(monkeypatch, exc):
    fc = _fc()
    msgs = _Messages(exc)
    monkeypatch.setattr(fc, "_LEDGER_ISSUE", "whu-x")
    monkeypatch.setattr(fc, "_spend", SimpleNamespace(orch_guard=lambda *a, **k: None, check_cap=lambda *a, **k: None))
    monkeypatch.setattr(fc, "_get_client", lambda: SimpleNamespace(messages=msgs))
    monkeypatch.setattr(fc.time, "sleep", lambda s: None)
    return fc, msgs


def test_anthropic_drafter_call_raises_model_unavailable_instead_of_returning_none(monkeypatch, orchestrated):
    fc, msgs = _drive_fc(monkeypatch, APIStatusError("overloaded_error", 529))
    with pytest.raises(PR.ModelUnavailable):
        fc.call("sys", "user", search=False, label="draft", raw=True, max_tokens=100)
    assert msgs.calls == 5


def test_anthropic_drafter_call_outside_orchestrated_mode_is_unchanged(monkeypatch):
    monkeypatch.delenv(PR.LOG_ENV, raising=False)
    fc, msgs = _drive_fc(monkeypatch, APIStatusError("invalid", 400))
    assert fc.call("sys", "user", search=False, label="draft", raw=True, max_tokens=100) is None and msgs.calls == 1


def test_every_provider_call_in_the_orchestrated_path_goes_through_the_retry():
    """No messages.create / messages.stream / count_tokens / generate_content in these modules outside
    provider_retry.call (the calls are wrapped in a lambda or a local _one() passed to it)."""
    call = re.compile(r"\.(messages\.create|messages\.stream|messages\.count_tokens|generate_content)\(")
    for p in (WHU / "audit_stage.py", WHU / "orch" / "google.py", SCRIPTS / "signal" / "factcheck_draft.py"):
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            if call.search(ln) and not ln.lstrip().startswith("#"):
                window = "\n".join(lines[max(0, i - 4):i + 1])
                assert "_PR().call(" in window or "def _one" in window, "%s:%d %s" % (p.name, i + 1, ln.strip())


# ----------------------------------------------------------------- the run stops

def test_a_logged_model_outage_stops_the_run_even_if_the_stage_carried_on(tmp_path):
    log = tmp_path / "m.jsonl"
    log.write_text(json.dumps({"provider": "google", "what": "overstatement", "error": "ServerError: 503"}) + "\n")
    ctx = SimpleNamespace(model_log=log, unavailable_log=tmp_path / "none.jsonl")
    with pytest.raises(O.RunStop, match=r"^overstatement: model unavailable; run again later \(google overstatement"):
        O._stop_if_unavailable(ctx, SimpleNamespace(name="overstatement"))


def test_no_logged_outage_does_not_stop(tmp_path):
    ctx = SimpleNamespace(model_log=tmp_path / "empty.jsonl", unavailable_log=tmp_path / "none.jsonl")
    O._stop_if_unavailable(ctx, SimpleNamespace(name="draft"))


def test_every_step_subprocess_gets_the_model_log(tmp_path):
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.mode, ctx.lock, ctx.model_log = "whu-x", "paid", None, tmp_path / "m.jsonl"
    step = SimpleNamespace(name="draft", cap_usd=1.0, max_calls=3, models=(), )
    import orch.steps as ST
    real = ST.allow_for
    try:
        ST.allow_for = lambda s: {"models": [], "roles": []}
        env = O.Ctx.env(ctx, step)
    finally:
        ST.allow_for = real
    assert env[O.MODEL_LOG_ENV] == str(tmp_path / "m.jsonl")
