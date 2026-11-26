"""The replay rehearsal (advisor's ruling 2 on the design review of 2026-11-26): the offline rehearsal (orch/rehearsal.py)
run on a RECORDED paid run's own question, documents and replies, at $0.

`orchestrator.py rehearse <recorded slug> --replay` sets WHU_REHEARSE_REPLAY=1 and WHU_REHEARSE_BASE_SLUG. Then:

  * REPLIES, in this order of preference, each labelled in the rehearsal's events.jsonl ("replayed"):
      raw     -- the reply as received, from the private reply store (reply_store.py), matched by step and the
                 call's order within the step; recorded from 2026-11-26 on, so none exists for 02z-02zd;
      parsed  -- rebuilt from the recorded run's own parsed records, where the record holds the whole answer:
                 the premise rows (premise.json), the discovery proposals (proposals.json) and the belief-outlet
                 proposals of each round (rulings/premise_checks.jsonl);
      synthetic -- the rehearsal's generator, where no record holds the answer (coverage, judgements, the premise
                 reading, whose quotations are recorded as offsets only, the audit, rulings, gate roles). Named, never
                 hidden: the replay proves the plumbing on the run's real inputs, not the model's reading.
  * TOKEN COUNTS: each reply carries the recorded run's own output count for that call (the ledger's row for the
    same step and order), and a count at or over TODAY's limit for the call comes back stop_reason max_tokens -- so
    a reply that would be cut off under the current limits is cut off in the replay, and the doubled re-ask runs.
    A recorded reply that was itself cut off (02zd's premise reading at 1,500) is censored: its full length is not
    known, so it is replayed synthetic and labelled so.
  * DOCUMENTS: the recorded run's held documents are served from its own URLs (the run's library index in the
    private checkpoint after acquire, the bytes from the trial library), seeded into the replay's HTTP cache; every
    other URL is recorded on first use (free registries) or, with --offline, fails as unreachable.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PRIVATE = Path.home() / "Projects" / "whu-study-private"
CHECKPOINTS = PRIVATE / "checkpoints"
LIB_TRIAL = ROOT / "backend" / "data" / "whatholdsup" / "library_trial"
CT = {".xml": "application/xml", ".pdf": "application/pdf", ".html": "text/html", ".htm": "text/html",
      ".txt": "text/plain", ".json": "application/json"}


def active() -> bool:
    return os.environ.get("WHU_REHEARSE_REPLAY") == "1"


def base_slug() -> str:
    return os.environ.get("WHU_REHEARSE_BASE_SLUG", "")


def base_case() -> Path | None:
    p = os.environ.get("WHU_REHEARSE_BASE")
    return Path(p) if p and Path(p).is_dir() else None


# ---------------------------------------------------------------------------------------------------- documents

def library_index(slug: str) -> dict:
    """The recorded run's library index after acquire (sid -> {url, file, ...}), from its private checkpoint."""
    cps = sorted((CHECKPOINTS / slug).glob("*-acquire"))
    for cp in cps[-1:]:
        p = cp / "library" / ("%s.json" % slug)
        try:
            return json.loads(p.read_text(encoding="utf-8")).get("sources") or {}
        except (OSError, ValueError):
            return {}
    return {}


def seed_http(slug: str, http_dir: Path, key_fn) -> list[dict]:
    """Seed HTTP_DIR (the rehearsal's record-then-replay cache) with the recorded run's held documents at the URLs
    they were fetched from. KEY_FN(url) -> the cache key (orch/rehearsal._key). Returns what was seeded."""
    http_dir = Path(http_dir)
    http_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for sid, row in sorted(library_index(slug).items()):
        url, f = row.get("url"), row.get("file")
        src = LIB_TRIAL / f if f else None
        if not url or not src or not src.exists():
            out.append({"source": sid, "url": url, "seeded": False, "why": "no recorded bytes"})
            continue
        k = key_fn(url)
        shutil.copyfile(src, http_dir / (k + ".body"))
        (http_dir / (k + ".json")).write_text(json.dumps({
            "url": url, "status": 200, "headers": {"Content-Type": CT.get(src.suffix.lower(), "application/octet-stream")},
            "final_url": url, "seeded_from": "the recorded run's library (%s)" % f}))
        out.append({"source": sid, "url": url, "seeded": True, "sha256": row.get("sha256")})
    return out


# ---------------------------------------------------------------------------------------------------- order

def _next(state: Path, step: str, name: str) -> tuple[int, int]:
    """(n within the step, n within (step, generator)), both 0-based, counted across the rehearsal's processes."""
    p = Path(state) / "replay_order.json"
    with open(Path(state) / ".replay.lock", "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        d = json.loads(p.read_text()) if p.exists() else {}
        a, b = d.get(step, 0), d.get(step + "|" + name, 0)
        d[step], d[step + "|" + name] = a + 1, b + 1
        p.write_text(json.dumps(d))
    return a, b


def _real_root() -> Path:
    """The repository the recorded run lives in (a rehearsal runs in a Sandbox copy; WHU_REPLAY_ROOT names the
    original)."""
    p = os.environ.get("WHU_REPLAY_ROOT")
    return Path(p) if p else ROOT


def _ledger_rows(slug: str, step: str) -> list[dict]:
    rows = []
    try:
        for line in (_real_root() / "backend" / "data" / "spend" / "ledger.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("issue") == slug and r.get("step") == step:
                    rows.append(r)
    except (OSError, ValueError):
        pass
    return rows


# ---------------------------------------------------------------------------------------------------- replies

def _jsonl(p: Path) -> list[dict]:
    out = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    except (OSError, ValueError):
        pass
    return out


def _premise(case: Path) -> str | None:
    try:
        d = json.loads((case / "premise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    es, sc = d.get("evidence_standard") or {}, d.get("scope") or {}
    belief = (d.get("belief") or {}).get("statement")
    if not belief:
        return None
    return json.dumps({"belief": belief, "kill_condition": d.get("kill_condition") or "",
                       "reader_with_a_decision": d.get("reader_with_a_decision") or "",
                       "scope_covers": sc.get("covers") or "",
                       "scope_out": [{"what": o.get("what", ""), "why": o.get("why", "")} for o in sc.get("out") or []
                                     if isinstance(o, dict)],
                       "weighs": es.get("weighs") or "measured", "measured": es.get("measured") or "",
                       "assessed": es.get("assessed") or ""})


def _proposals(case: Path) -> str | None:
    try:
        d = json.loads((case / "proposals.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    props = d.get("proposals") or []
    return json.dumps({"sources": props}) if props else None


def _belief(case: Path, round_n: int) -> str | None:
    rows = [r for r in _jsonl(case / "rulings" / "premise_checks.jsonl")
            if r.get("check") == "belief-outlet" and int(r.get("round") or 1) == round_n + 1]
    if not rows:
        return None
    return json.dumps({"outlets": [r.get("proposed") or {} for r in rows]})


PARSED = {"premise": _premise, "discover": _proposals}


def reply(state: Path, step: str, name: str, max_tokens: int | None) -> dict:
    """{"text" or None, "output": recorded output tokens or None, "source": raw|parsed|synthetic, "why"} for the
    next call of STEP whose prompt the rehearsal's generator NAME recognises."""
    n_step, n_name = _next(state, step, name)
    slug, case = base_slug(), base_case()
    led = _ledger_rows(slug, step)
    out_tokens = int(led[n_step].get("output") or 0) if n_step < len(led) else None
    # raw: the private reply store, by step and order
    raws = [r for r in _reply_store().load(slug) if r.get("step") == step]
    if n_step < len(raws):
        r = raws[n_step]
        return {"text": r.get("final_text") or r.get("text"), "output": int((r.get("usage") or {}).get("output") or 0),
                "source": "raw", "why": "the reply as received (reply store)"}
    if case is not None and _was_cut_off(case, step, n_step):
        return {"text": None, "output": None, "source": "synthetic",
                "why": "the recorded reply was cut off at %s tokens: its full length is not known" % out_tokens}
    text = None
    if case is not None:
        if name in PARSED:
            text = PARSED[name](case)
        elif name == "belief-outlet":
            text = _belief(case, n_name)
    if text is not None:
        return {"text": text, "output": out_tokens, "source": "parsed",
                "why": "rebuilt from the recorded run's parsed record"}
    return {"text": None, "output": out_tokens, "source": "synthetic", "why": "no record holds this answer"}


def _was_cut_off(case: Path, step: str, n: int) -> bool:
    """Whether the recorded run's N-th call in STEP was cut off: its run record keeps a failed step's replies, with
    cut_off on the one that was."""
    try:
        d = json.loads((case / "orchestrator" / "run_paid.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    for s in d.get("steps") or []:
        if s.get("step") == step:
            reps = s.get("replies") or []
            return n < len(reps) and bool(reps[n].get("cut_off"))
    return False


def _reply_store():
    import importlib.util
    import sys
    m = sys.modules.get("reply_store")
    if m is None:
        p = Path(__file__).resolve().parents[1] / "reply_store.py"
        sp = importlib.util.spec_from_file_location("reply_store", p)
        m = importlib.util.module_from_spec(sp)
        sys.modules["reply_store"] = m
        sp.loader.exec_module(m)
    return m


def stop_for(output: int | None, max_tokens: int | None) -> str:
    return "max_tokens" if (output is not None and max_tokens and output >= int(max_tokens)) else "end_turn"


def log_event(state: Path, row: dict) -> None:
    with open(Path(state) / "events.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(row, event="replayed"), ensure_ascii=False) + "\n")


def code_sha() -> str:
    """One hash of the code a replay gate result is valid for: every .py under whatholdsup/ (orch/ included),
    factcheck_draft.py, spend_ledger.py and provider_retry.py, by path and content."""
    h = hashlib.sha256()
    files = sorted((ROOT / "backend" / "scripts" / "whatholdsup").rglob("*.py")) + [
        ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py",
        ROOT / "backend" / "scripts" / "spend_ledger.py", ROOT / "backend" / "scripts" / "provider_retry.py"]
    for f in files:
        if "__pycache__" in f.parts:
            continue
        h.update(str(f.relative_to(ROOT)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()
