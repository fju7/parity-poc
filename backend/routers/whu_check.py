"""What Holds Up — "check an AI answer" preview (unlisted, pilot).

POST /api/whu/check        create a job from a pasted AI answer; returns its id
GET  /api/whu/check/{id}   the job's status and, when done, its per-claim result

The pipeline is the reliability study's, reused by path, not copied:
study/whu-reliability/check_pilot/pipeline.py (design: docs/whu-check-an-answer-pilot.md).
Each claim is BACKED / NOT BACKED / NO SOURCE / COULDN'T CHECK, judged by Claude with the
study's frozen M1 v3 prompt, against openly licensed copies of its sources only.

Access: every request carries X-Check-Code equal to env WHU_CHECK_CODE (401 otherwise);
with WHU_CHECK_CODE unset every request gets 503. There is no default code.
Spend: ledger issue whu-check-preview; caps.json per_issue (total) and per_issue_per_day,
and the all-spend day cap, checked before a job's first model call (402, and no call).
Limits: 20,000 characters, 40 claims, one job at a time.
Pasted text is held in memory for the job only; its working files are deleted when the
job ends. The operator log (backend/data/whu_check/jobs.jsonl, not committed) keeps the
time, claim count, labels, cost and the input's sha256, never the text.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
PIPELINE = REPO_ROOT / "study" / "whu-reliability" / "check_pilot" / "pipeline.py"
JOBS_LOG = BACKEND_ROOT / "data" / "whu_check" / "jobs.jsonl"

ISSUE = "whu-check-preview"
MAX_CHARS = 20_000
MAX_CLAIMS = 40
ALLOWED_ORIGIN = "https://whatholdsup.org"
JOB_TTL_SECONDS = 3600

router = APIRouter(prefix="/api/whu", tags=["whu-check"])

_jobs: dict[str, dict] = {}
_lock = threading.Lock()
_running: Optional[str] = None
_P = None


def pipeline():
    """The study pipeline, loaded on first use (503 if this deploy does not have it)."""
    global _P
    if _P is None:
        if not PIPELINE.exists():
            raise HTTPException(503, "the check pipeline is not available on this server")
        spec = importlib.util.spec_from_file_location("whu_check_pipeline", PIPELINE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _P = m
    return _P


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# Access
# --------------------------------------------------------------------------

def require_code(x_check_code: Optional[str] = Header(None)) -> None:
    want = os.environ.get("WHU_CHECK_CODE", "")
    if not want:
        raise HTTPException(503, "checking is not enabled on this server")
    if not x_check_code or not hmac.compare_digest(x_check_code.encode(), want.encode()):
        raise HTTPException(401, "a valid access code is required")


class OriginGuard:
    """CORS for /api/whu/* alone: browsers may call it from whatholdsup.org only.
    Registered outside the app-wide CORSMiddleware, so that middleware's origins are
    neither widened for other routes nor applied here."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/api/whu/"):
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        origin = headers.get("origin")
        if origin and origin != ALLOWED_ORIGIN:
            res = JSONResponse({"detail": "origin not allowed"}, status_code=403)
            return await res(scope, receive, send)
        cors = [(b"access-control-allow-origin", ALLOWED_ORIGIN.encode()), (b"vary", b"Origin")] if origin else []
        if scope["method"] == "OPTIONS" and origin:
            res = JSONResponse({}, status_code=200)
            res.raw_headers.extend(cors + [(b"access-control-allow-methods", b"GET, POST, OPTIONS"),
                                           (b"access-control-allow-headers", b"Content-Type, X-Check-Code"),
                                           (b"access-control-max-age", b"600")])
            return await res(scope, receive, send)

        async def send_with_cors(message):
            if message["type"] == "http.response.start" and cors:
                kept = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"access-control-allow-origin"]
                message = {**message, "headers": kept + cors}
            await send(message)
        return await self.app(scope, receive, send_with_cors)


# --------------------------------------------------------------------------
# Spend
# --------------------------------------------------------------------------

def _caps() -> tuple[float, float]:
    S = pipeline().S
    c = S.caps()
    total = (c.get("per_issue") or {}).get(ISSUE)
    day = (c.get("per_issue_per_day") or {}).get(ISSUE)
    if total is None or day is None:
        raise HTTPException(503, "caps.json has no cap for %s; checking does not run without one" % ISSUE)
    return float(total), float(day)


def cap_stop(worst: float) -> Optional[str]:
    """None if spending up to WORST more fits every cap, else the reason. Fails closed."""
    S = pipeline().S
    total_cap, day_cap = _caps()
    if S.unpriced(issue=ISSUE):
        return "a ledger line for %s has no established cost" % ISSUE
    total = S.spent(issue=ISSUE)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day = sum(float(e.get("usd") or 0) for e in S.entries()
              if e.get("issue") == ISSUE and (e.get("at") or "").startswith(today))
    if total >= total_cap or total + worst > total_cap:
        return "%s has spent $%.2f of its $%.2f cap; this check could cost up to $%.2f" % (ISSUE, total, total_cap, worst)
    if day >= day_cap or day + worst > day_cap:
        return "%s has spent $%.2f today of its $%.2f daily cap; this check could cost up to $%.2f" % (
            ISSUE, day, day_cap, worst)
    try:
        S.check_day_cap(worst)
    except S.OverCap as e:
        return str(e).splitlines()[0]
    return None


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------

def _log(rec: dict) -> None:
    JOBS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def _prune() -> None:
    cut = time.time() - JOB_TTL_SECONDS
    for k in [k for k, j in _jobs.items() if j["created"] < cut and j["status"] not in ("queued", "running")]:
        _jobs.pop(k, None)


def _clients():
    """(metered client, token counter). Separate so the tests can replace it."""
    import anthropic
    P = pipeline()
    raw = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return P.S.metered(raw, script="backend/routers/whu_check.py", issue=ISSUE, role="check-preview-claude"), \
        P.count_tokens_fn(raw)


# Network steps, replaceable in tests.
LICENCE_FN = None
RETRIEVE_FN = None


def _run(job_id: str, text: str, fmt: Optional[str]) -> None:
    global _running
    P = pipeline()
    job = _jobs[job_id]
    work = Path(tempfile.mkdtemp(prefix="whu-check-"))
    spent_before = P.S.spent(issue=ISSUE)
    try:
        job["status"] = "running"
        client, count = _clients()
        prep = P.prepare(text, work, fmt=fmt, max_claims=MAX_CLAIMS, count=count,
                         licence_fn=LICENCE_FN or P.licence_of, retrieve_fn=RETRIEVE_FN or P.retrieve_url)
        why = cap_stop(prep["worst_usd"])
        if why:
            job.update(status="over_cap", error=why)
            return

        def before_call(worst):
            w = cap_stop(worst)
            if w:
                raise P.Stop(w)
        try:
            results = P.judge(prep["planned"], client, before_call)
        except P.Stop as e:
            job.update(status="over_cap", error=str(e))
            return
        t = P.totals(results)
        job.update(status="done", result={"claims": P.public(results, prep["manifest"]), "totals": t,
                                          "beyond_limit": len(prep["beyond_limit"]), "format": prep["format"]})
    except Exception as e:  # reported to the requester without the text
        job.update(status="failed", error="%s: %s" % (type(e).__name__, str(e)[:300]))
    finally:
        shutil.rmtree(work, ignore_errors=True)
        res = job.get("result") or {}
        _log({"at": now(), "job": job_id, "status": job["status"], "input_sha256": job["input_sha256"],
              "claims": job.get("claims"), "labels": {k: v for k, v in (res.get("totals") or {}).items()
                                                      if k in P.LABELS},
              "usd": round(P.S.spent(issue=ISSUE) - spent_before, 6), "error": job.get("error")})
        with _lock:
            _running = None


class CheckIn(BaseModel):
    answer: str
    format: Optional[str] = None


@router.post("/check", dependencies=[Depends(require_code)])
def create_check(body: CheckIn):
    global _running
    P = pipeline()
    text = body.answer or ""
    if not text.strip():
        raise HTTPException(422, "paste an answer to check")
    if len(text) > MAX_CHARS:
        raise HTTPException(413, "answers are limited to %d characters; this one has %d" % (MAX_CHARS, len(text)))
    with tempfile.TemporaryDirectory(prefix="whu-check-count-") as d:
        try:
            md, cited, fmt = P.adapt_answer(text, body.format)
            rows, refs = P.sentences(md, cited, Path(d))
        except P.adapt.AdaptError as e:
            raise HTTPException(422, "could not read the answer's citations: %s" % e)
    claims, beyond = P.claims_of(rows, refs, max_claims=10 ** 6)
    if not claims:
        raise HTTPException(422, "no checkable claims found (a claim is a sentence of 8 to 70 words with a "
                                 "number or a citation marker)")
    if len(claims) > MAX_CLAIMS:
        raise HTTPException(422, "answers are limited to %d claims; this one has %d" % (MAX_CLAIMS, len(claims)))
    why = cap_stop(0.0)
    if why:
        raise HTTPException(402, why)
    with _lock:
        _prune()
        if _running:
            raise HTTPException(409, "another check is running; try again in a few minutes")
        job_id = uuid.uuid4().hex
        _running = job_id
        _jobs[job_id] = {"id": job_id, "status": "queued", "created": time.time(), "claims": len(claims),
                         "format": fmt, "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    threading.Thread(target=_run, args=(job_id, text, fmt), daemon=True).start()
    return {"id": job_id, "status": "queued", "claims": len(claims), "format": fmt}


@router.get("/check/{job_id}", dependencies=[Depends(require_code)])
def get_check(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "no such check (results are kept for an hour)")
    out = {k: v for k, v in job.items() if k not in ("created", "input_sha256")}
    if job["status"] == "over_cap":
        return JSONResponse(out, status_code=402)
    return out
