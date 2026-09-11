#!/usr/bin/env python3
"""The correction email: what changed, why, and what you should now believe.

WHY THIS EXISTS
---------------
Subscribers hold superseded versions of both issue emails. One of them credits a
finding to the wrong researcher by name. `publish.py` says plainly that an email
cannot be recalled, and there was no mechanism for telling anyone.

WHAT TRIGGERS A SEND, and the threshold is about the READER
------------------------------------------------------------
    CORRECTION  a reader who trusted us came away with something false
                -> ALWAYS sends.
    UPDATE      new evidence, or a revision that does not contradict what we
                said -> batched, or carried in the next issue's email.
    Nav, furniture, record-live, formatting -> never.

The first row's test is the same one the page's own corrections use, so one
definition governs both. Melanoma has been republished five times; five emails
train a reader to ignore the sixth.

WHAT IT SAYS -- three parts, and the third is the point
--------------------------------------------------------
    1. what changed
    2. why -- what we got wrong, and how we found it
    3. WHAT YOU SHOULD NOW BELIEVE THAT DIFFERS FROM WHAT YOU BELIEVED BEFORE

**A correction notice that describes an edit rather than a belief is a
changelog, not a correction.** Part 3 is the reader-facing form of the whole
apparatus and it is the part a generator cannot write: it is a claim about a
reader's mind, and it is drafted by a person and recorded in `drafts/`.

HOW IT IS BUILT
---------------
Assembled from `corrections.md` entries not yet carried by any recorded send --
never from a hand-written summary of them, because a hand-written summary of a
record drifts from the record, in the flattering direction, every time. That is
this repository's single most-applied remedy; see the process document, 11.5.

THE FLOOR IS REAL, NOT ASSUMED
------------------------------
`sent.json` records what was sent and when. Its four seeded rows carry
`covers: "unknown"`, so this module treats every correction older than
2026-09-10 as **of unknown delivery** rather than as delivered or undelivered.
It will not claim to be sending "everything since last time" when nobody knows
what last time carried.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import index_dates as I                                   # noqa: E402
import source_store as store                              # noqa: E402

SENT = I.ROOT / "backend" / "data" / "whatholdsup" / "sent.json"

CORRECTION, UPDATE, NEITHER = "CORRECTION", "UPDATE", "NEITHER"

# A record-live reason, a nav change or a formatting pass never reaches a reader
# as a belief. These are matched on the correction HEADING, which is where this
# publication states what an entry is about.
_NEVER = re.compile(r"\b(nav|navigation|link|formatting|dateline|typo|whitespace)\b", re.I)


def sends() -> list[dict]:
    try:
        return json.loads(SENT.read_text(encoding="utf-8")).get("sends") or []
    except Exception:
        return []


def delivered(row: dict) -> bool:
    """Only a row whose state is exactly "sent" reached anyone.

    `correction_email.py` writes the row BEFORE the send with state "sending"
    and closes it to "sent" or "failed". On 2026-09-11 the first correction
    broadcast failed, its row carried a three-item `covers` list, and this
    module read the list without reading the state -- so three corrections
    nobody had received were dropped from "outstanding". A failed send was
    counting as having told readers.

    The four seeded rows have no state at all. They were real sends, but their
    coverage is "unknown", so they contribute nothing either way; a future row
    with a covers list and no state is a row nobody closed, and the safe
    reading of that is the same as "sending": not delivered. The asymmetry is
    the module's own -- the cost of re-telling is an irritated reader, the cost
    of not telling is a reader who still holds the false belief -- so the
    predicate is strict equality, matching the sender's own check for a
    recorded test send.
    """
    return row.get("state") == "sent"


def covered() -> set[str]:
    """Correction headings a recorded send is known to have carried.

    `unknown` contributes NOTHING. A send whose coverage nobody recorded cannot
    be used to conclude that a reader has already been told. Nor can a send
    that did not happen: see `delivered`.
    """
    out = set()
    for s in sends():
        c = s.get("covers")
        if isinstance(c, list) and delivered(s):
            out |= {" ".join(str(x).split()) for x in c}
    return out


def corrections(slug: str) -> list[dict]:
    """Every entry in this issue's correction history, newest heading first."""
    d = store.case_dir(slug)
    p = d / "corrections.md"
    if not p.exists():
        return []
    out, cur = [], None
    for ln in p.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## "):
            cur = {"slug": slug, "heading": " ".join(ln[3:].split()), "body": []}
            out.append(cur)
        elif cur is not None:
            cur["body"].append(ln)
    for c in out:
        c["body"] = "\n".join(c["body"]).strip()
    return out


def classify(entry: dict) -> str:
    """CORRECTION, UPDATE or NEITHER, from the heading.

    Deliberately crude and deliberately conservative: anything that is not
    clearly furniture is a CORRECTION, because the cost of emailing about a
    change a reader did not need is an irritated reader, and the cost of not
    emailing about a false belief is a reader who still holds it.
    """
    h = entry["heading"]
    if _NEVER.search(h):
        return NEITHER
    return CORRECTION


def outstanding(slug: str | None = None) -> list[dict]:
    """Corrections no recorded send is known to have carried."""
    import publish as P
    done = covered()
    out = []
    for s in ([slug] if slug else sorted(P.ISSUES)):
        for c in corrections(s):
            if classify(c) != CORRECTION:
                continue
            if c["heading"] in done:
                continue
            out.append(c)
    return out


def unknown_delivery() -> int:
    """How many recorded sends have coverage nobody wrote down."""
    return len([s for s in sends() if not isinstance(s.get("covers"), list)])


def main() -> int:
    import publish as P
    print("\n  recorded sends: %d, of which %d have unknown coverage"
          % (len(sends()), unknown_delivery()))
    for s in sorted(P.ISSUES):
        rows = outstanding(s)
        print("\n  %-11s %d correction(s) no send is known to have carried" % (s, len(rows)))
        for c in rows:
            print("     - %s" % c["heading"][:96])
    print("\n  A send is drafted by a person: part 3 -- what a reader should now")
    print("  believe -- is a claim about a reader's mind and is not generated.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
