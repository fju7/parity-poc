"""Does a held source report results? (advisor's ruling 2 after attempt 11, 2026-11-23; orchestrated runs.)

If no held source reports results, the page stops Not Ready with a code-written reason. Protocols,
registrations, evidence-and-gap maps and commentaries do not report results. A source's type is chosen by a
model at discover and is not enough on its own: attempt 11 typed an evidence-and-gap map "synthesis" and a
protocol "methods". So a source reports results only if its type is one that can, AND its title does not mark
it as one of the four kinds that do not.
"""
from __future__ import annotations

import re

RESULT_TYPES = {"primary", "comparison", "review", "synthesis", "guideline", "assessment_summary", "label",
                "conference", "press_release"}
NOT_RESULTS_TITLE = re.compile(
    r"^\s*protocol\b|\bstudy protocol\b|\bprotocol (?:for|of)\b|\bprotocol\s*:|\breview protocol\b"
    r"|\bevidence[- ](?:and[- ])?gap map|\bgap map\b|\bregistration\b|\bregistered report protocol\b"
    r"|\bcommentary\b|\bcomment on\b",
    re.IGNORECASE)


def why_not(src: dict) -> str | None:
    """None if the source reports results; else the code-written reason it does not."""
    t = src.get("type")
    title = src.get("title") or ""
    m = NOT_RESULTS_TITLE.search(title)
    if m:
        return "its title marks it as %r, which reports no results" % m.group(0).strip(" :")
    if t not in RESULT_TYPES:
        return "its type %r is not one that reports results" % t
    return None


def stop_reason(held: list[dict]) -> str | None:
    """The Not Ready reason when no held source reports results; None when at least one does."""
    if not held or any(why_not(s) is None for s in held):
        return None
    return ("no held source reports results, so the page stops Not Ready: "
            + "; ".join("%s (%s): %s" % (s["id"], (s.get("title") or "")[:80], why_not(s)) for s in held))
