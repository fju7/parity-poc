"""A model-written page sentence must be ONE sentence as the audit's splitter reads it (advisor's ruling,
2026-11-23, after attempt 15: the judgements model wrote two sentences into one, and the audit read the stored
sentence as two units). In lean / orchestrated mode a reply whose sentence is more than one is re-asked once with
REASK; a second such reply goes to the step's existing fail-safe. Every case is noted to the run record.
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

import source_ledger as ledger

REASK = "\n\nWrite exactly one sentence."


def strict() -> bool:
    return (os.environ.get("WHU_LEAN", "").strip() in ("1", "true", "yes", "on")
            or bool(os.environ.get("WHU_ORCH_STEP")))


def count(text: str) -> int:
    """How many sentences the audit's splitter (bindings.page_sentences: source_ledger.sentences over
    source_ledger.plain of the rendered page) reads in TEXT, rendered as one paragraph."""
    return len([s for s in ledger.sentences(ledger.plain("<p>%s</p>" % html.escape(text or "", quote=False)))
                if s.strip()])


def is_one(text: str) -> bool:
    return count(text) == 1


def note(role: str, event: str, text: str = "") -> None:
    """To the orchestrator's per-run log (WHU_ORCH_MALFORMED_LOG), counted in run_paid.json."""
    path = os.environ.get("WHU_ORCH_MALFORMED_LOG")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"role": role, "event": event, "text": (text or "")[:20000],
                                 "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                ensure_ascii=False) + "\n")
    except OSError:
        pass
