"""The one holdings record: for every source of an issue, held / not held / blocked, with its reason.

Advisor's ruling C after orchestrator trial 1 attempt 21 (2026-11-24). Attempt 21's acquire held S001 and blocked
S002 (a correction it could not hold) and S003 (a correction that does not name it) -- in sources.json. But the
library's issue index still listed all three, and every text reader went through that index
(source_store.held -> spancheck._text -> audit_stage.held_for_audit -> ruling.held_texts). So the draft drew
12 of its 38 passages from the two blocked sources (S003 8, S002 4) and cited [2] and [3]; coverage and judgements
quoted S003 on the readers' list; and the dangling ruling was shown S003's text (PMC9700054). Attempts 4-9
(WHU-OT1-02d .. 02i) carried the same leak.

The record is derived, never kept by hand, from the two places that hold the facts:
  * sources.json `access` (the stages' own record of what happened when we tried): state "blocked" or a
    `not_held` line -> BLOCKED, with that line and its reason;
  * the library's issue index (which bytes are stored): a source not blocked whose bytes are stored -> HELD;
    otherwise NOT_HELD.
source_store.held() -- the gate every text reader goes through -- returns HELD sources only, so no stage can load
a blocked or unheld source's text. The preflight row "page cites held sources only" STOPs a page any of whose
sentences cites a source that is not held; the code-generated record sentences (lean_sentences: "A newer edition
exists of ...", "We found ... but could not hold it ...") name a source without drawing on it and are exempt.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

HELD, NOT_HELD, BLOCKED = "held", "not held", "blocked"
ROW = "page cites held sources only"
MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def record(slug: str) -> dict[str, dict]:
    """{source id: {"holding": HELD | NOT_HELD | BLOCKED, "state": access state, "reason": str | None}}, in
    sources.json order."""
    import source_store as store
    return classify(store.sources(slug), store.library_held(slug))


def classify(sources: list[dict], stored) -> dict[str, dict]:
    """The record from SOURCES (sources.json's list) and STORED (the ids whose bytes the library stores)."""
    lib = set(stored or ())
    out = {}
    for s in sources or []:
        if not isinstance(s, dict):
            continue
        sid, acc = s.get("id"), s.get("access") or {}
        nh = acc.get("not_held") or {}
        if acc.get("state") == "blocked" or nh:
            why = ("%s: %s" % (nh.get("line"), nh.get("why"))) if nh else (acc.get("blocked_by") or "blocked")
            out[sid] = {"holding": BLOCKED, "state": acc.get("state"), "reason": why}
        elif sid in lib:
            out[sid] = {"holding": HELD, "state": acc.get("state"), "reason": None}
        else:
            out[sid] = {"holding": NOT_HELD, "state": acc.get("state"),
                        "reason": "no document stored (%s)" % (acc.get("state") or "no state")}
    return out


def held_ids(slug: str) -> set:
    return {k for k, v in record(slug).items() if v["holding"] == HELD}


def cites(sentence: str) -> list[int]:
    return [int(n) for m in MARKER.finditer(sentence or "") for n in re.split(r"\s*,\s*", m.group(1))]


def page_problems(slug: str, page_sentences: list[str], generated: list | None = None,
                  sources: list[dict] | None = None, rec: dict | None = None) -> list[str]:
    """Each page sentence that cites a source the record does not hold (or a number with no source). SOURCES and
    REC default to the issue's own (sources.json, record(slug))."""
    import lean_sentences as LS
    import source_store as store
    if sources is None:
        sources = store.sources(slug)
    ids = [s.get("id") for s in sources if isinstance(s, dict)]
    if rec is None:
        rec = record(slug)
    if generated is None:
        try:
            generated = LS.generated(slug)
        except (Exception, SystemExit):
            generated = []
    out = []
    for s in page_sentences:
        nums = cites(s)
        if not nums or (generated and LS.matches(s, generated)):
            continue
        bad = []
        for n in nums:
            if not 1 <= n <= len(ids):
                bad.append("[%d] names no source" % n)
            elif rec.get(ids[n - 1], {}).get("holding") != HELD:
                r = rec.get(ids[n - 1]) or {}
                bad.append("[%d] %s is %s (%s)" % (n, ids[n - 1], r.get("holding", NOT_HELD), r.get("reason")))
        if bad:
            out.append("%s -- %s" % (" ".join(s.split())[:120], "; ".join(bad)))
    return out


def preflight_rows(slug: str, page: Path, ok: str, bad: str) -> list[tuple[str, str, str]]:
    import bindings as B
    if not Path(page).exists():
        return [(ROW, bad, "no page at %s" % page)]
    found = page_problems(slug, B.page_sentences(slug, Path(page).read_text(encoding="utf-8")))
    if found:
        return [(ROW, bad, "%d sentence(s) cite a source not held: %s" % (len(found), " | ".join(found[:4])))]
    return [(ROW, ok, "every citing sentence cites held sources")]


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="the holdings record of an issue")
    ap.add_argument("slug")
    a = ap.parse_args(argv)
    print(json.dumps(record(a.slug), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
