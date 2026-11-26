"""The held-source minimum (advisor's ruling 3 on the design review of 2026-11-26).

Straight after `acquire` (orchestrator.code_acquire), before the first model call that drafts: at least MINIMUM
distinct works held in full text, at least one of them a review or a synthesis (source_store canonical type
"review" or "synthesis"). Below it the run ends with the honest outcome

    Insufficient sources: N of M confirmed sources held (minimum 2); not drafted

(N works held in full text, M confirmed sources in sources.json), and nothing is drafted. That is an outcome, not a
defect: the page could only rest on one document, or on no review. Ruled reading for the second condition (two or
more held, none a review or synthesis): the same sentence with "; none is a review or synthesis" before "; not
drafted".
"""
from __future__ import annotations

import re

MINIMUM = 2
REVIEW_TYPES = {"review", "synthesis"}
FULL_TEXT = "full_text_held"


def _work_key(s: dict) -> str:
    doi = str(s.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    t = re.sub(r"[^a-z0-9]+", " ", str(s.get("title") or "").lower()).strip()
    return "title:" + t if t else "id:" + str(s.get("id"))


def held_works(doc: dict) -> list[dict]:
    """One held-in-full-text source per distinct work (by DOI, else normalised title)."""
    seen, out = set(), []
    for s in (doc or {}).get("sources") or []:
        acc = s.get("access") or {}
        if acc.get("state") != FULL_TEXT or acc.get("not_held"):
            continue
        k = _work_key(s)
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def _canonical(t) -> str:
    try:
        import source_store as store
        return store.canonical_type(t)
    except Exception:
        return str(t or "")


def shortfall(doc: dict) -> str | None:
    """The outcome sentence when the minimum is not met, else None."""
    works = held_works(doc)
    n, m = len(works), len((doc or {}).get("sources") or [])
    if n < MINIMUM:
        return "Insufficient sources: %d of %d confirmed sources held (minimum %d); not drafted" % (n, m, MINIMUM)
    if not any(_canonical(s.get("type")) in REVIEW_TYPES for s in works):
        return ("Insufficient sources: %d of %d confirmed sources held (minimum %d); none is a review or synthesis; "
                "not drafted" % (n, m, MINIMUM))
    return None
