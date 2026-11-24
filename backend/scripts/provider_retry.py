"""Model-provider calls in an orchestrated run: retried, and an outage stops the run (advisor's ruling after
orchestrator trial 1 attempt 22, 2026-11-24, option 3).

Attempt 22 stopped at the overstatement step on one Google 503 ("This model is currently experiencing high
demand") after 24 good calls: orch/google.Gateway did not retry. Now, in ORCHESTRATED mode (the orchestrator sets
WHU_ORCH_MODEL_LOG in its own process and in every step's subprocess), every model-provider call -- Google,
Anthropic, OpenAI -- goes through `call`:

  * on 503, 529, 429, a timeout or a connection error it is retried 4 times (5 attempts in all) with backoff
    RETRY_DELAYS;
  * still unavailable, one line goes to the log and ModelUnavailable is raised ("model unavailable; run again
    later"). After every step the orchestrator reads the log and stops the run Not Ready with that reason, however
    the stage handled the exception -- a stage that swallowed it cannot pass. It is an outage stop under revised
    ruling 3 (wait 30 minutes; at most three per UTC day).

Outside orchestrated mode `call(fn)` is `fn()`: nothing else changes. The SDKs' own retries (Anthropic's client
retries twice by default) still run inside each attempt.

Load it by path (`load()`), never by putting backend/scripts on sys.path: that would shadow the stdlib `signal`
module with backend/scripts/signal (factcheck_draft.py's note on spend_ledger). One module object is shared under
sys.modules["provider_retry"], so ModelUnavailable is one class everywhere.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

LOG_ENV = "WHU_ORCH_MODEL_LOG"
RETRIES = 4
RETRY_DELAYS = (5, 15, 45, 90)
STATUSES = {503, 529, 429}
TRANSIENT_NAMES = ("Timeout", "TimeoutError", "APITimeoutError", "ReadTimeout", "ConnectTimeout",
                   "APIConnectionError", "ConnectionError", "ConnectError", "RemoteProtocolError",
                   "ServiceUnavailable", "ServerError", "InternalServerError", "OverloadedError",
                   "RateLimitError", "ResourceExhausted", "DeadlineExceeded")
TRANSIENT_WORDS = ("503", "529", "429", "UNAVAILABLE", "overloaded", "Overloaded", "RESOURCE_EXHAUSTED",
                   "rate limit", "timed out", "Timeout", "Connection error", "connection reset")
_sleep = time.sleep


class ModelUnavailable(Exception):
    """Still unavailable after the retries: the run stops "model unavailable; run again later"."""


def orchestrated() -> bool:
    return bool(os.environ.get(LOG_ENV))


def status_of(e: BaseException):
    for k in ("status_code", "code", "status"):
        v = getattr(e, k, None)
        if isinstance(v, int):
            return v
    resp = getattr(e, "response", None)
    v = getattr(resp, "status_code", None)
    return v if isinstance(v, int) else None


def transient(e: BaseException) -> bool:
    if isinstance(e, ModelUnavailable):
        return False
    st = status_of(e)
    if st is not None:
        return st in STATUSES
    names = {c.__name__ for c in type(e).__mro__}
    if names & set(TRANSIENT_NAMES) or isinstance(e, (TimeoutError, ConnectionError)):
        return True
    msg = str(e)
    return any(w in msg for w in TRANSIENT_WORDS)


def _log(provider: str, what: str, e: BaseException) -> None:
    p = os.environ.get(LOG_ENV)
    if not p:
        return
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"provider": provider, "what": what, "error": "%s: %s" % (type(e).__name__, str(e)[:300]),
                             "attempts": RETRIES + 1,
                             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}) + "\n")


def call(fn, provider: str, what: str = ""):
    """FN() in orchestrated mode retried RETRIES times on a transient provider error, then ModelUnavailable."""
    if not orchestrated():
        return fn()
    for i in range(RETRIES + 1):
        try:
            return fn()
        except Exception as e:
            if not transient(e):
                raise
            if i >= RETRIES:
                _log(provider, what, e)
                raise ModelUnavailable("model unavailable; run again later (%s %s: %s: %s)"
                                       % (provider, what, type(e).__name__, str(e)[:200])) from e
            print("  [RETRY] %s %s: %s; retry %d/%d in %ds" % (provider, what, type(e).__name__, i + 1, RETRIES,
                                                                RETRY_DELAYS[i]))
            _sleep(RETRY_DELAYS[i])


def outages(path) -> list[dict]:
    out = []
    try:
        for ln in open(path, encoding="utf-8").read().splitlines():
            if ln.strip():
                out.append(json.loads(ln))
    except (OSError, ValueError, TypeError):
        pass
    return out


def load_from(path):
    """The shared module object (sys.modules["provider_retry"]), loading the file at PATH the first time. Each
    caller carries a copy of this loader (it cannot import this module to get it)."""
    import importlib.util
    import sys
    m = sys.modules.get("provider_retry")
    if m is None:
        spec = importlib.util.spec_from_file_location("provider_retry", str(path))
        m = importlib.util.module_from_spec(spec)
        sys.modules["provider_retry"] = m
        spec.loader.exec_module(m)
    return m
