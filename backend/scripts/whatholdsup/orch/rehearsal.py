"""The offline rehearsal (Fred's term A1 after orchestrator trial 1 attempt 23, 2026-11-24).

`orchestrator.py rehearse SLUG` runs every orchestrator step end to end at $0, inside a Sandbox (a scratch copy of
the repository, deleted at the end), with WHU_ORCH_MODE=rehearse:

  * MODELS: every client a stage builds (audit_stage.Caller, factcheck_draft._get_client, orch/google.Gateway) is a
    stub from this module. A stub reads the prompt and writes a reply of the shape the step asks for (synthetic, from
    the prompt's own ids, passages and sentences). The guard, the meter, the caps, provider_retry and every parser run
    as in a paid run; the "spend" lands in the copy's ledger.
  * HTTP: every urllib call (registries, document fetches) is served from a record-then-replay cache kept OUTSIDE the
    repository (WHU_REHEARSE_HTTP, default ~/Projects/whu-study-private/rehearsal_http/, since held documents carry
    publisher text); with WHU_REHEARSE_OFFLINE=1 a URL not recorded fails as unreachable.
  * FAULTS AND SHAPES (WHU_REHEARSE_PLAN, a JSON file): provider errors (503 / 529 / 429 / timeout / connection),
    registry errors and outages, an empty reply, and the reply shapes already met -- prose around one value, two
    values, narration between searches, a fenced block with prose, a mid-reply revision, a multi-sentence sentence.
    Each is consumed once, in order, by the first matching call; state is a file under WHU_REHEARSE_STATE, so it
    holds across the step subprocesses.
  * GIT: the run's commits go to the Sandbox's own clone and are never pushed.

A prompt no generator recognises is saved under <state>/unknown/ and answered with an empty reply, so the rehearsal
names the next generator to write instead of guessing.
"""
from __future__ import annotations

import fcntl
import hashlib
import io
import json
import os
import re
import urllib.error
from email.message import Message
from pathlib import Path
from types import SimpleNamespace

MODE = "rehearse"


def active() -> bool:
    return os.environ.get("WHU_ORCH_MODE") == MODE


def state_dir() -> Path:
    p = Path(os.environ.get("WHU_REHEARSE_STATE") or "/tmp/whu-rehearse-state")
    p.mkdir(parents=True, exist_ok=True)
    return p


# ------------------------------------------------------------------------------------------------ the plan

def _plan() -> dict:
    p = os.environ.get("WHU_REHEARSE_PLAN")
    if not p:
        return {}
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _matches(rule: dict, step: str, what: str) -> bool:
    return (rule.get("step", "*") in ("*", step)) and (rule.get("what", "*") in ("*", what) or
                                                          (rule.get("what", "").endswith("*") and
                                                           what.startswith(rule["what"][:-1])))


def take(kind: str, step: str, what: str):
    """The next unconsumed plan entry of KIND matching (STEP, WHAT), consumed; None if there is none."""
    plan = _plan().get(kind) or []
    sp = state_dir() / "consumed.json"
    with open(state_dir() / ".lock", "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        used = json.loads(sp.read_text()) if sp.exists() else {}
        for i, rule in enumerate(plan):
            key = "%s:%d" % (kind, i)
            n = used.get(key, 0)
            if n < int(rule.get("times", 1)) and _matches(rule, step, what):
                used[key] = n + 1
                sp.write_text(json.dumps(used))
                log("plan", {"kind": kind, "rule": i, "step": step, "what": what, "entry": rule})
                return rule
    return None


def log(event: str, data: dict) -> None:
    with open(state_dir() / "events.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(data, event=event), ensure_ascii=False, default=str) + "\n")


# ------------------------------------------------------------------------------------------------ provider faults

class StubStatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


class APITimeoutError(Exception):
    pass


class APIConnectionError(Exception):
    pass


def fault(err: str) -> Exception:
    return {"503": StubStatusError("503 UNAVAILABLE (rehearsal)", 503),
            "529": StubStatusError("overloaded_error (rehearsal)", 529),
            "429": StubStatusError("rate_limit_error (rehearsal)", 429),
            "timeout": APITimeoutError("Request timed out. (rehearsal)"),
            "connection": APIConnectionError("Connection error. (rehearsal)")}[err]


def maybe_fault(provider: str, step: str, what: str) -> None:
    """Called by provider_retry.call before each attempt in rehearse mode."""
    rule = take("provider", step, what)
    if rule:
        raise fault(rule.get("error", "503"))


# ------------------------------------------------------------------------------------------------ reply shapes

def shaped(text: str, step: str, what: str) -> str:
    """TEXT (a clean JSON reply) in the shape the plan asks for, once."""
    rule = take("shape", step, what)
    if not rule:
        return text
    s = rule.get("shape")
    if s == "prose_around":
        return "Here is my answer.\n\n" + text + "\n\nI hope this helps."
    if s == "two_values":
        return text + "\n\n" + text
    if s == "fenced_with_prose":
        return "My reading follows.\n```json\n" + text + "\n```\nThat is all."
    if s == "mid_reply_revision":
        return text + "\n\nWait -- on reflection I revise that:\n" + text
    if s == "empty":
        return ""
    if s == "multi_sentence":
        # a field meant to be one sentence comes back as two
        try:
            d = json.loads(text)
        except ValueError:
            return text
        for k in ("sentence", "text"):
            if isinstance(d.get(k), str) and d[k]:
                d[k] = d[k].rstrip(".") + ". It also holds in other settings."
                return json.dumps(d)
        return text
    return text


# ------------------------------------------------------------------------------------------------ stub clients

def _now_step() -> str:
    return os.environ.get("WHU_ORCH_STEP", "")


def _current_what() -> str:
    import sys
    pr = sys.modules.get("provider_retry")
    return (getattr(pr, "CURRENT", None) or {}).get("what", "") if pr else ""


def _text_of(messages) -> str:
    out = []
    for m in messages or []:
        c = m.get("content") if isinstance(m, dict) else None
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            out += [b.get("text", "") for b in c if isinstance(b, dict)]
    return "\n".join(out)


def _usage(prompt: str, out: str, searches: int = 0):
    return SimpleNamespace(input_tokens=max(1, len(prompt) // 4), output_tokens=max(1, len(out) // 4),
                           cache_creation_input_tokens=0, cache_read_input_tokens=0,
                           server_tool_use=SimpleNamespace(web_search_requests=searches) if searches else None)


def _blocks(final: str, search: bool, step: str, what: str):
    if not search:
        return [SimpleNamespace(type="text", text=final)], 0
    narrate = bool(_plan().get("narrate_searches"))
    blocks = []
    # Narration BETWEEN searches (attempts 12-22's shape): text before each search; the reply is the text after the
    # last search (factcheck_draft._final_text).
    for i, line in enumerate(("I'll search for the latest versions of these sources.",
                              "Now let me check for corrections.")):
        if narrate:
            blocks.append(SimpleNamespace(type="text", text=line))
        blocks.append(SimpleNamespace(type="server_tool_use", name="web_search", input={"query": "rehearsal %d" % i}))
        blocks.append(SimpleNamespace(type="web_search_tool_result",
                                      content=[SimpleNamespace(url="https://europepmc.org/", title="Europe PMC")]))
    blocks.append(SimpleNamespace(type="text", text=final))
    return blocks, 2


class _Message(SimpleNamespace):
    pass


class _Stream:
    def __init__(self, msg):
        self.msg = msg

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self.msg


def _replay():
    """orch/replay_rehearsal.py, by path (the replay rehearsal, ruling 2 on the design review), or None."""
    import importlib.util
    import sys
    m = sys.modules.get("whu_replay_rehearsal")
    if m is None:
        p = Path(__file__).with_name("replay_rehearsal.py")
        spec = importlib.util.spec_from_file_location("whu_replay_rehearsal", str(p))
        m = importlib.util.module_from_spec(spec)
        sys.modules["whu_replay_rehearsal"] = m
        spec.loader.exec_module(m)
    return m if m.active() else None


def generator_name(prompt: str, step: str, what: str, provider: str = "anthropic") -> str:
    for name, match, _make in GENERATORS:
        try:
            if match(prompt, step, what, provider):
                return name
        except Exception:
            continue
    return "unknown"


class _AnthropicMessages:
    def _reply(self, kw):
        step, what = _now_step(), _current_what()
        system = kw.get("system") or ""
        prompt = (system + "\n\n" if isinstance(system, str) else "") + _text_of(kw.get("messages"))
        search = bool(kw.get("tools"))
        stop, out_tokens = "end_turn", None
        RR = _replay()
        if RR is not None:
            name = generator_name(prompt, step, what)
            rr = RR.reply(state_dir(), step, name, kw.get("max_tokens"))
            text = shaped(rr["text"] if rr["text"] is not None else generate(step, what, prompt, search=search),
                          step, what)
            out_tokens = rr["output"]
            stop = RR.stop_for(out_tokens, kw.get("max_tokens"))
            if stop == "max_tokens":
                text = text[: max(1, len(text) // 2)]          # cut off, as the recorded length would be today
            RR.log_event(state_dir(), {"step": step, "generator": name, "source": rr["source"], "why": rr["why"],
                                       "output": out_tokens, "max_tokens": kw.get("max_tokens"), "stop": stop})
        else:
            text = shaped(generate(step, what, prompt, search=search), step, what)
        blocks, n = _blocks(text, search, step, what)
        log("anthropic", {"step": step, "what": what, "model": kw.get("model"), "chars": len(text),
                          "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12]})
        usage = _usage(prompt, text, n)
        if out_tokens:
            usage.output_tokens = int(out_tokens)
        return _Message(content=blocks, usage=usage, model=kw.get("model"),
                        stop_reason=stop, id="rehearsal", type="message", role="assistant")

    def create(self, **kw):
        return self._reply(kw)

    def stream(self, **kw):
        return _Stream(self._reply(kw))

    def count_tokens(self, **kw):
        return SimpleNamespace(input_tokens=max(1, len(_text_of(kw.get("messages"))) // 4))


class AnthropicStub:
    def __init__(self):
        self.messages = _AnthropicMessages()


class _GoogleModels:
    def generate_content(self, model, contents, config=None):
        step, what = _now_step(), _current_what()
        text = contents if isinstance(contents, str) else str(contents)
        out = shaped(generate(step, what or "google", text, search=False, provider="google"), step, what)
        RR = _replay()
        if RR is not None:
            RR.log_event(state_dir(), {"step": step, "generator": generator_name(text, step, what or "google", "google"),
                                       "source": "synthetic", "why": "no record holds a Google verdict's reply"})
        log("google", {"step": step, "what": what, "chars": len(out)})
        return SimpleNamespace(model_version=model, text=out, prompt_feedback=None,
                               candidates=[SimpleNamespace(finish_reason="STOP")],
                               usage_metadata=SimpleNamespace(prompt_token_count=max(1, len(text) // 4),
                                                              cached_content_token_count=0,
                                                              candidates_token_count=max(1, len(out) // 4),
                                                              thoughts_token_count=0))


class GoogleStub:
    def __init__(self):
        self.models = _GoogleModels()


# ------------------------------------------------------------------------------------------------ HTTP

def http_dir() -> Path:
    p = Path(os.environ.get("WHU_REHEARSE_HTTP") or (Path.home() / "Projects" / "whu-study-private" /
                                                      "rehearsal_http"))
    p.mkdir(parents=True, exist_ok=True)
    return p


class _Resp(io.BytesIO):
    def __init__(self, body: bytes, status: int, headers: dict, url: str):
        super().__init__(body)
        self.status = self.code = status
        self.url = url
        m = Message()
        for k, v in headers.items():
            m[k] = v
        self.headers = self.msg = m

    def getcode(self):
        return self.status

    def geturl(self):
        return self.url

    def info(self):
        return self.headers

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def _key(req) -> str:
    import urllib.request
    url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
    data = req.data if isinstance(req, urllib.request.Request) else None
    return hashlib.sha256((url + "\n" + (data.decode("latin-1") if isinstance(data, bytes) else "")).encode()
                          ).hexdigest()


def cached_urlopen(orig, req, *a, **kw):
    """ORIG (urllib.request.urlopen, or the retry wrapper's original) behind the record-then-replay cache, with
    the plan's registry faults."""
    import urllib.request
    url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
    step = _now_step()
    rule = take("registry", step, url)
    if rule:
        err = str(rule.get("error", "timed out"))
        if err.isdigit():                    # an HTTP status (ruling after attempt 24: Europe PMC answering 503)
            raise urllib.error.HTTPError(url, int(err), "rehearsal registry fault", Message(), io.BytesIO(b""))
        raise urllib.error.URLError("rehearsal registry fault: %s" % err)
    k = _key(req)
    meta, body = http_dir() / (k + ".json"), http_dir() / (k + ".body")
    if meta.exists():
        m = json.loads(meta.read_text())
        log("http", {"url": url[:200], "from": "cache", "status": m["status"]})
        if m["status"] >= 400:
            raise urllib.error.HTTPError(url, m["status"], m.get("reason") or "", Message(), io.BytesIO(
                body.read_bytes() if body.exists() else b""))
        return _Resp(body.read_bytes(), m["status"], m.get("headers") or {}, m.get("url") or url)
    if os.environ.get("WHU_REHEARSE_OFFLINE") == "1":
        log("http", {"url": url[:200], "from": "offline-miss"})
        raise urllib.error.URLError("rehearsal offline: %s was not recorded" % url[:120])
    try:
        r = orig(req, *a, **kw)
        data = r.read()
        st = getattr(r, "status", None) or r.getcode()
        hdrs = {k2: v for k2, v in (r.headers.items() if getattr(r, "headers", None) else [])}
        meta.write_text(json.dumps({"url": url, "status": st, "headers": hdrs,
                                    "final_url": getattr(r, "url", url)}))
        body.write_bytes(data)
        log("http", {"url": url[:200], "from": "live", "status": st})
        return _Resp(data, st, hdrs, getattr(r, "url", url))
    except urllib.error.HTTPError as e:
        data = e.read() if hasattr(e, "read") else b""
        meta.write_text(json.dumps({"url": url, "status": e.code, "reason": str(e.reason)}))
        body.write_bytes(data or b"")
        log("http", {"url": url[:200], "from": "live", "status": e.code})
        raise urllib.error.HTTPError(url, e.code, e.reason, e.headers, io.BytesIO(data or b""))


def install_http() -> None:
    """Put the cache in front of urllib.request.urlopen in this process (before registry_http's retry wrapper, so
    the wrapper's retries see the plan's faults)."""
    import urllib.request
    if getattr(urllib.request.urlopen, "_whu_rehearsal", False):
        return
    orig = urllib.request.urlopen

    def opener(req, *a, **kw):
        return cached_urlopen(orig, req, *a, **kw)
    opener._whu_rehearsal = True
    urllib.request.urlopen = opener


# ------------------------------------------------------------------------------------------------ replies

GENERATORS: list = []          # (name, match(prompt, step, what, provider) -> bool, make(prompt, step, what) -> str)


def generator(name, match):
    def deco(fn):
        GENERATORS.append((name, match, fn))
        return fn
    return deco


def generate(step: str, what: str, prompt: str, search: bool = False, provider: str = "anthropic") -> str:
    for name, match, make in GENERATORS:
        try:
            ok = match(prompt, step, what, provider)
        except Exception:
            ok = False
        if ok:
            out = make(prompt, step, what)
            log("generated", {"step": step, "what": what, "generator": name})
            return out
    d = state_dir() / "unknown"
    d.mkdir(exist_ok=True)
    n = len(list(d.glob("*.txt")))
    (d / ("%03d-%s-%s.txt" % (n, step or "nostep", re.sub(r"\W+", "_", what or "x")[:40]))).write_text(prompt)
    log("unknown", {"step": step, "what": what, "head": prompt[:200]})
    return ""


def load(path=None):
    """This module, loaded by path once and shared as sys.modules["whu_rehearsal"] (stages that cannot import the
    orch package -- factcheck_draft -- load it this way too), with its reply generators registered."""
    import importlib.util
    import sys
    m = sys.modules.get("whu_rehearsal")
    if m is None:
        p = Path(path) if path else Path(__file__)
        spec = importlib.util.spec_from_file_location("whu_rehearsal", str(p))
        m = importlib.util.module_from_spec(spec)
        sys.modules["whu_rehearsal"] = m
        spec.loader.exec_module(m)
    if not getattr(m, "_replies_loaded", False):
        m._replies_loaded = True
        rp = Path(m.__file__).with_name("rehearsal_replies.py")
        spec = importlib.util.spec_from_file_location("whu_rehearsal_replies", str(rp))
        rm = importlib.util.module_from_spec(spec)
        sys.modules["whu_rehearsal_replies"] = rm
        spec.loader.exec_module(rm)
    return m
