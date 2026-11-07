"""Harness-state provenance (post-test item 3; docs/whu-orchestrator.md §2.6).

orchestrator/manifest.json, written by step 0 and compared again at the preflight step: the code commit,
sha256 of CLAUDE.md, the process doc, the orchestrator design and every .py the run executes, each step's
models, and each external tool's settings. The clock is read from the system, never estimated.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def tools() -> dict:
    import sys
    here = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(here))
    out = {}
    try:
        import tls
        out["fetch_user_agent"] = tls.USER_AGENT
    except Exception as e:                       # recorded, not hidden
        out["fetch_user_agent"] = "unreadable: %s" % e
    try:
        import passage_index as P
        out["passage_retrieval"] = {k: getattr(P, k) for k in ("PASSAGE_CHARS", "MIN_SCORE", "MIN_TERMS")
                                    if hasattr(P, k)}
    except Exception as e:
        out["passage_retrieval"] = "unreadable: %s" % e
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location("fc_settings", here.parent / "signal" / "factcheck_draft.py")
        src = (here.parent / "signal" / "factcheck_draft.py").read_text(encoding="utf-8")
        import re
        m = re.search(r"^MAX_SEARCHES_PER_CALL\s*=\s*(\d+)", src, re.M)
        out["web_search_max_uses"] = int(m.group(1)) if m else None
    except Exception as e:
        out["web_search_max_uses"] = "unreadable: %s" % e
    return out


def _model_sources(steps) -> dict:
    try:
        from orch import model_map as MM
        return MM.step_models(steps)
    except Exception as e:                  # recorded, never silently empty
        return {"_error": "%s: %s" % (type(e).__name__, e)}


def build(root: Path, steps, extra: dict | None = None) -> dict:
    code = sorted(list((root / "backend/scripts/whatholdsup").rglob("*.py")) +
                  [root / "backend/scripts/signal/factcheck_draft.py", root / "backend/scripts/spend_ledger.py"])
    try:
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                                text=True).stdout.strip() or None
    except Exception:
        commit = None
    return {
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": commit,
        "documents": {p: _sha(root / p) for p in ("CLAUDE.md", "docs/whatholdsup-process.md",
                                                  "docs/whu-orchestrator.md")},
        "code": {p.relative_to(root).as_posix(): _sha(p) for p in code if "__pycache__" not in p.parts},
        "models": {s.name: list(s.models) for s in steps},
        # every model each step may call and where it comes from, read from the code (advisor, after attempt 8)
        "model_sources": _model_sources(steps),
        "limits": {s.name: {"max_calls": s.max_calls, "cap_usd": s.cap_usd} for s in steps},
        "tools": tools(),
        **(extra or {}),
    }


def changed(old: dict, new: dict) -> list[str]:
    """What differs between two manifests in what the run depends on (not the clock)."""
    out = []
    for k in ("commit", "documents", "code", "models", "limits", "tools"):
        a, b = old.get(k), new.get(k)
        if isinstance(a, dict) and isinstance(b, dict):
            out += ["%s: %s" % (k, x) for x in sorted(set(a) | set(b)) if a.get(x) != b.get(x)]
        elif a != b:
            out.append(k)
    return out
