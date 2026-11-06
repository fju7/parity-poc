#!/usr/bin/env python3
"""Non-impact check: the three scored lean pages' preflight output is unchanged.

Runs `WHU_LEAN=1 publish.py check` on whu-lean-q1-01c, -02b and -03b, and prints, for each, whether its full
output is byte-identical to the sixth-freeze output session LT kept (9863fb2; the sha256 of each kept file is
fixed below, so the check needs no private file). Output, one line per page: "<slug> identical|DIFFERS".
Expected stdout sha256 is in patches.jsonl. Offline; no model call.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
STORED = {  # sha256 of session LT's replay_9863fb2/pf<q>_9863fb2.txt
    "whu-lean-q1-01c": "7c5e88dbf37b03276adc178f60e3eb22aa246b4d539b4e97833cdc34d669fcec",
    "whu-lean-q1-02b": "e32af70539e6e8923a6330196e0395443b733e4a99c298b8ef2108101e2c5fbe",
    "whu-lean-q1-03b": "a9962d98775485b0ca1495ebb90c076ab9462993ea839632cbe375ff56653a3a",
}


def line(slug: str, output: str) -> str:
    same = hashlib.sha256(output.encode("utf-8")).hexdigest() == STORED[slug]
    return "%s %s" % (slug, "identical" if same else "DIFFERS")


def main() -> int:
    env = dict(os.environ, WHU_LEAN="1")
    for slug in STORED:
        r = subprocess.run([str(ROOT / "backend/venv/bin/python3"), "backend/scripts/whatholdsup/publish.py",
                            "check", slug], cwd=str(ROOT), env=env, capture_output=True, text=True)
        print(line(slug, r.stdout + r.stderr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
