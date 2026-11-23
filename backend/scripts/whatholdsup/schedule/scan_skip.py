#!/usr/bin/env python3
"""Which issue folders the weekly lead scan skips (advisor's ruling 4, 2026-11-23).

    scan_skip.py <issue folder>     exit 0 and print the reason: skip it; exit 1: sweep it

Skipped: orchestrator trial folders (WHU-OT1-*), seeded-defect copies (WHU-SD-*), and any folder an
orchestrator lock names (backend/data/whatholdsup/orchestrator.lock carries the running issue's slug; a file
left by a killed run is treated the same, which is the safe side). Their records belong to a run, and the scan
writing into them (it wrote an identifier into WHU-OT1-02c on 9 Nov) mixes scheduled output into run records.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LOCK = ROOT / "backend" / "data" / "whatholdsup" / "orchestrator.lock"
PREFIXES = ("WHU-OT1-", "WHU-SD-")


def _slug(case: Path) -> str:
    try:
        return json.loads((case / "issue.json").read_text(encoding="utf-8")).get("slug") or ""
    except (OSError, ValueError):
        return ""


def skip(case: Path, lock: Path = LOCK) -> str | None:
    name = case.name
    for pre in PREFIXES:
        if name.startswith(pre):
            return "%s* folder (a trial or seeded-defect run)" % pre
    try:
        held = json.loads(lock.read_text(encoding="utf-8")).get("slug") or ""
    except (OSError, ValueError, AttributeError):
        held = ""
    if held and (held == _slug(case) or name.endswith("-" + held)):
        return "named in the orchestrator lock (%s)" % held
    return None


if __name__ == "__main__":
    why = skip(Path(sys.argv[1]))
    if why:
        print(why)
    sys.exit(0 if why else 1)
