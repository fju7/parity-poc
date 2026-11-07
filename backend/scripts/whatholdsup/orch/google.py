"""The orchestrator's Google gateway (docs/whu-orchestrator.md §3). The only way an orchestrator step
gets a Google client.

- PAID-TIER PREFLIGHT FIRST (advisor's ruling of 2026-10-30, after the free-tier incident in
  study/whu-reliability/next_phase/deviations.md): one tiny generate call carrying no content of the
  run; a Free Tier refusal or any error is a STOP. Once per process, before any other Google call.
- Never count_tokens: estimates are local (APPROX_CHARS_PER_TOKEN).
- Every call passes spend_ledger.orch_guard first and is recorded in the ledger at
  spend_ledger.rates("gemini-4-argon"); a reply from any other model is a STOP.

`Gateway(client=...)` takes a client for tests; with none it builds google.genai.Client from
GEMINI_API_KEY in backend/.env. This build makes no call: the tests use a stub.
"""
from __future__ import annotations

import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

MODEL = "gemini-4-argon"
SCRIPT = "orch/google.py"
PREFLIGHT_TEXT = "Reply with the single word: ok"
APPROX_CHARS_PER_TOKEN = 3.0
MAX_OUT = 2800   # orch/steps.py REPLY_LIMITS["overstatement"]: thinking counts towards it


class Stop(RuntimeError):
    pass


def free_tier(err) -> bool:
    blob = json.dumps(getattr(err, "details", None) or {}, default=str) + " " + str(err)
    return "FreeTier" in blob or "Free Tier" in blob or "free_tier" in blob


def approx_tokens(text: str) -> int:
    return int(-(-len(text or "") // APPROX_CHARS_PER_TOKEN)) if text else 0


def worst_usd(n_in: int, max_out: int = MAX_OUT) -> float:
    p = S.rates(MODEL, n_in)
    return (n_in * p["input"] + max_out * p["output"]) / 1e6


def _key() -> str:
    for line in (ROOT / "backend" / ".env").read_text().splitlines():
        m = re.match(r"^GEMINI_API_KEY=(.*)$", line.strip())
        if m:
            return m.group(1).strip().strip("'\"")
    raise Stop("no GEMINI_API_KEY in backend/.env")


def _config(max_out: int):
    try:
        from google.genai import types
        return types.GenerateContentConfig(max_output_tokens=max_out)
    except Exception:                      # a stub client in tests
        return {"max_output_tokens": max_out}


def _usage(r):
    u = getattr(r, "usage_metadata", None)
    g = (lambda k: int(getattr(u, k, 0) or 0)) if u is not None else (lambda k: 0)
    return g("prompt_token_count"), g("cached_content_token_count"), g("candidates_token_count"), \
        g("thoughts_token_count")


class Gateway:
    def __init__(self, issue: str, client=None):
        self.issue = issue
        self._client = client
        self.preflight_record = None

    def client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=_key())
        return self._client

    def preflight(self) -> dict:
        if self.preflight_record:
            return self.preflight_record
        S.orch_guard(MODEL, SCRIPT, "google-preflight", self.issue, 0.001)
        try:
            r = self.client().models.generate_content(model=MODEL, contents=PREFLIGHT_TEXT, config=_config(64))
        except Exception as e:
            if free_tier(e):
                raise Stop("PREFLIGHT: the key is on Google's Free Tier; no Google call is made")
            raise Stop("PREFLIGHT: the tiny call failed (%s); cannot confirm a paid tier" % str(e)[:200])
        tin, _c, tout, think = _usage(r)
        p = S.rates(MODEL, 0)
        usd = (tin * p["input"] + (tout + think) * p["output"]) / 1e6
        S.record(script=SCRIPT, role="google-preflight", issue=self.issue, usd=usd, input_tokens=tin,
                 output_tokens=tout + think, note="paid-tier preflight; %s" % (getattr(r, "model_version", "") or MODEL))
        self.preflight_record = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "usd": round(usd, 6), "model": getattr(r, "model_version", None)}
        return self.preflight_record

    def call(self, text: str, role: str) -> dict:
        """One generate call. {"text", "model", "usd", "refused", "finish", "tokens"}. Raises Stop on a transport
        error (no reply: not a verdict) and on a reply from another model."""
        self.preflight()
        n_in = approx_tokens(text)
        S.orch_guard(MODEL, SCRIPT, role, self.issue, worst_usd(n_in))
        try:
            r = self.client().models.generate_content(model=MODEL, contents=text, config=_config(MAX_OUT))
        except Exception as e:
            raise Stop("no reply from %s (%s)" % (MODEL, str(e)[:200]))
        mv = getattr(r, "model_version", None) or ""
        if mv and not mv.startswith(MODEL):
            raise Stop("the reply came from model %r, not %s" % (mv, MODEL))
        prompt, cached, cand, think = _usage(r)
        p = S.rates(MODEL, prompt)
        usd = ((prompt - cached) * p["input"] + cached * p["cache_read"] + (cand + think) * p["output"]) / 1e6
        cands = getattr(r, "candidates", None) or []
        finish = str(getattr(cands[0], "finish_reason", "")) if cands else ""
        fb = getattr(r, "prompt_feedback", None)
        refused = bool(fb and getattr(fb, "block_reason", None)) or any(
            k in finish for k in ("SAFETY", "PROHIBITED", "BLOCKLIST"))
        try:
            out = r.text or ""
        except Exception:
            out = ""
        S.record(script=SCRIPT, role=role, issue=self.issue, usd=usd, input_tokens=prompt,
                 output_tokens=cand + think, note="%s; cached=%d; thinking=%d; finish=%s" % (mv or MODEL, cached,
                                                                                         think, finish))
        return {"text": out, "model": mv or MODEL, "usd": round(usd, 6), "refused": refused, "finish": finish,
                "tokens": {"input": prompt, "cached": cached, "output": cand, "thinking": think}}
