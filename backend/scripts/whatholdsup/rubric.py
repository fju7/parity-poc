#!/usr/bin/env python3
"""Two scores, because one verdict cannot answer two questions.

WHY THIS EXISTS
---------------
The outside review of 2026-09-03 found that a single composite breaches rule 8
of the editorial standard -- distinguish confidence in DIRECTION from
confidence in MAGNITUDE, because these are separate questions and one verdict
cannot express both.

Issue one is the case that proves it. A double-blind 1,137-patient phase 3
crossed its prespecified threshold on recurrence, and released no effect size
at all. The old rubric averaged an excellent study and an empty release into
"3.35, moderate", a number that is wrong about both halves: it understates how
good the trial is and overstates how much we know about the size of what it
found. The editor's answer was to score the two questions separately, always.

THE SPLIT, AND WHY IT IS NOT A NEW SET OF WEIGHTS
-------------------------------------------------
No weight is invented here. The six dimensions and their weights are imported
from the scoring engine, which is the single place they are defined; this
module only says which QUESTION each dimension answers, and renormalises the
existing weights within each group so they still sum to 1.

    direction  is the effect real, and in the direction claimed?
               source_quality, reproducibility, consensus, recency, rigor
    magnitude  how large is it, and how well pinned down?
               data_support

MAGNITUDE RESTS ON ONE DIMENSION, AND THAT IS THE FINDING
---------------------------------------------------------
Only data_support's anchors speak about magnitude at all: 5 is "specific
statistical results (p-values, confidence intervals, effect sizes)" and 1 is
"purely qualitative assertion with no numeric support". Every other dimension
asks about the evidence's provenance, replication, currency or design, all of
which bear on whether an effect is real and none of which tell a reader how big
it is.

The tempting move is to fold rigor into magnitude -- a phase 3 estimates an
effect size more precisely than a case series -- and it is wrong here. It would
let a superb trial that released no numbers score above 1 for magnitude, which
is the reviewer's objection reappearing in a new place. A trial's quality
governs how much you could learn from its numbers, not how much you have
learned from numbers nobody published.

So the honest statement is that this rubric measures magnitude with a single
instrument. Printed rather than hidden, on the published rubric page and here.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ENGINE = (Path(__file__).resolve().parents[1] / "signal" / "score_claims.py")


def _engine():
    """The dimensions, weights and bands, from the one file that defines them."""
    spec = importlib.util.spec_from_file_location("score_claims", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    here = str(ENGINE.parent.parent.parent)
    sys.path.insert(0, here)
    sys.path.insert(0, str(ENGINE.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(ENGINE.parent))
        sys.path.remove(here)
    return mod


# Which question each dimension answers. This is the whole of what this module
# adds, and it is a claim about the ANCHORS -- read them before changing it.
ANSWERS = {
    "source_quality": ("direction",),
    "data_support": ("magnitude",),
    "reproducibility": ("direction",),
    "consensus": ("direction",),
    "recency": ("direction",),
    "rigor": ("direction",),
}

QUESTIONS = ("direction", "magnitude")


def weights(question: str) -> dict[str, float]:
    """The engine's own weights, restricted to one question and renormalised."""
    if question not in QUESTIONS:
        raise ValueError("no such question: %r" % question)
    w = _engine().DEFAULT_WEIGHTS
    part = {d: v for d, v in w.items() if question in ANSWERS[d]}
    total = sum(part.values())
    if not total:
        raise ValueError("no dimension answers %r" % question)
    return {d: v / total for d, v in part.items()}


def band(value: float) -> str:
    for floor, name in _engine().EVIDENCE_CATEGORIES:
        if value >= floor:
            return name
    return "weak"


def score(scores: dict[str, int]) -> dict:
    """Two composites and their working, from six hand-assigned integers."""
    eng = _engine()
    missing = [d for d in eng.DIMENSIONS if d not in scores]
    if missing:
        raise ValueError("no score for: %s" % ", ".join(missing))
    out = {}
    for q in QUESTIONS:
        raw = {d: v for d, v in eng.DEFAULT_WEIGHTS.items() if q in ANSWERS[d]}
        div = sum(raw.values())
        total = sum(scores[d] * v for d, v in raw.items()) / div
        # THE WORKING MUST BE REDOABLE BY A READER, so it shows the engine's own
        # weights and the divisor, not the renormalised weights. Renormalised
        # weights print as 0.188 and 0.312 and do not reproduce the answer at
        # the precision shown; "over 0.80" is exact and shows the
        # renormalisation instead of hiding it.
        terms = " + ".join("%d×%s" % (scores[d], ("%.2f" % raw[d]).lstrip("0"))
                           for d in sorted(raw))
        out[q] = {
            "value": round(total, 2),
            "band": band(total),
            "dimensions": sorted(raw),
            "divisor": round(div, 2),
            "working": "(%s) ÷ %s" % (terms, ("%.2f" % div).lstrip("0")),
        }
    return out


def drifted() -> list[str]:
    """Every dimension the engine defines that this module has not placed.

    The rubric is published on the site as a single thing. If the engine gains
    a dimension and nobody says which question it answers, the published page
    silently stops describing the rubric it claims to describe.
    """
    return [d for d in _engine().DIMENSIONS if d not in ANSWERS]


if __name__ == "__main__":
    import json
    demo = {"source_quality": 3, "data_support": 1, "reproducibility": 4,
            "consensus": 4, "recency": 5, "rigor": 5}
    print(json.dumps(score(demo), indent=2))
    print("unplaced dimensions:", drifted() or "none")
