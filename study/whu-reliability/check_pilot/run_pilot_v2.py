#!/usr/bin/env python3
"""The check-an-answer pilot, v2 (docs/whu-check-an-answer-pilot.md §9).

    run_pilot_v2.py draw | prepare | run --cap 35 | compare

run_pilot.py's commands, unchanged, on v2's pipeline (pipeline_v2.py), v2's sample (§9.6),
ledger issue whu-check-pilot-v2 and its own private folder
(~/Projects/whu-study-private/check_pilot_v2/). Counts only are committed:
check_pilot/pilot_v2_counts.json.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline_v2  # noqa: E402
import run_pilot as R  # noqa: E402

V1_DRAW = R.draw


def draw() -> list[tuple[str, str]]:
    """§9.6: for each system, 2 of its questions not in v1's sample."""
    rng = random.Random("%d/check-pilot-v2" % R.SEED)
    v1 = set(V1_DRAW())
    out = []
    for s in R.SYSTEMS:
        left = [q for q in R.QUESTIONS if (q, s) not in v1]
        out += [(q, s) for q in sorted(rng.sample(left, 2))]
    return out


R.P = pipeline_v2
R.draw = draw
R.ISSUE = "whu-check-pilot-v2"
R.OUT = R.PRIVATE / "check_pilot_v2"
R.COUNTS = HERE / "pilot_v2_counts.json"

if __name__ == "__main__":
    raise SystemExit(R.main())
