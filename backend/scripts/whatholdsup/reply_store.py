"""Every model reply of a paid orchestrated run, recorded raw and privately (advisor's ruling 2 on the design review
of 2026-11-26).

One JSON line per API response, at ~/Projects/whu-study-private/replies/<issue>/replies.jsonl (WHU_REPLY_STORE
overrides the root; outside the repository, as for the other private study files, because a reply quotes publisher
text). Each line: when, issue, step, call site, role, model, max_tokens, stop_reason, usage, the prompt's sha256 and
length, and the reply's text exactly as received (the joined text blocks; for a web-search call, also the final
text after the last search). Never a key: a key-shaped string in a reply is replaced before it is written.

Written only when a real provider answered in a PAID orchestrated run (WHU_ORCH_MODE=paid): a rehearsal's or a
replay's stub replies are not replies. Never raises: recording must not break a run.

The replay rehearsal (orch/replay_rehearsal.py) reads these back; until this store existed only parsed replies were
kept (proposals.json, premise.json, coverage.json, judgements.json, rulings, audit verdicts).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

KEYLIKE = re.compile(r"(sk-ant-[A-Za-z0-9_\-]{8,}|AIza[0-9A-Za-z_\-]{20,}|sk-[A-Za-z0-9]{20,})")


def root() -> Path:
    return Path(os.environ.get("WHU_REPLY_STORE") or (Path.home() / "Projects" / "whu-study-private" / "replies"))


def active() -> bool:
    return os.environ.get("WHU_ORCH_MODE") == "paid"


def path_for(issue: str) -> Path:
    return root() / re.sub(r"[^A-Za-z0-9_.\-]+", "-", issue or "no-issue") / "replies.jsonl"


def _clean(text: str) -> str:
    return KEYLIKE.sub("[key-shaped string removed]", text or "")


def record(*, issue: str, site: str, role: str, model: str, max_tokens: int, stop_reason: str | None,
           usage: dict | None, prompt: str, text: str, final_text: str | None = None) -> None:
    if not active():
        return
    try:
        row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "issue": issue,
               "step": os.environ.get("WHU_ORCH_STEP", ""), "call_site": site, "role": role, "model": model,
               "max_tokens": int(max_tokens or 0), "stop_reason": stop_reason, "usage": usage or {},
               "prompt_sha256": hashlib.sha256((prompt or "").encode("utf-8")).hexdigest(),
               "prompt_chars": len(prompt or ""), "text": _clean(text), "raw": True}
        if final_text is not None and final_text != text:
            row["final_text"] = _clean(final_text)
        p = path_for(issue)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load(issue: str) -> list[dict]:
    p = path_for(issue)
    out = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    except (OSError, ValueError):
        pass
    return out
