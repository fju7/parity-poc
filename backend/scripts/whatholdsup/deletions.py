#!/usr/bin/env python3
"""B14 -- THE DELETION RULE. What a correction TOOK OUT is not checked.

WHY THIS EXISTS, AND WHY IT IS LATE
-----------------------------------
The claim-bindings spec, section 8, written 2026-09-01:

    A correction that deletes a claim must point at a row whose span was
    absent. On 31 August a correction withdrew the Shaaban paper's own "29
    blocks with block size of four" as our arithmetic. Under this rule that
    deletion is refused, because the span is in the paper.

It was specified, deferred, and not built. On 2026-09-01 -- the same day -- three
figures were removed from the live melanoma page on the strength of a check that
said they were "in nothing we hold". Two of them were real: five-year landmark
rates reported from the same analysis in a document nobody had entered as a
source. The correction notice told readers we had invented them.

That is the second instance of the class the rule was written for, and the first
to reach a reader.

WHAT THE ERROR TAXONOMY ALREADY SAID
------------------------------------
Of seventeen adjudicated corrections on issue two, SIX -- 35% -- were introduced
by an earlier correction, and one deleted a true statement. error_taxonomy.py
ends:

    Corrections are the least-checked text on this page and the likeliest place
    for the next error. That is measurable, it is 35% of everything found, and
    nothing currently gates a correction harder than it gates the prose it
    corrects.

Every other check in this repository asks whether a claim ON the page is
supported. None asks whether a REMOVAL was. A pipeline that validates only what
the page says is blind to what a correction took out, and removal is where a
third of the errors come from.

THE RULE
--------
A figure that readers can see now, and that the draft no longer carries, must be
accounted for. The account is one of:

    UNSOURCED   we cannot show where it came from. Not the same claim as
                absent, and the one that should almost always be used: it is
                about our library, which is the only thing a library is evidence
                about. Record what was searched.
    REWRITTEN   the figure is still on the page in another form -- rounded,
                relabelled, moved. Detected automatically; nothing to record.
    SUPERSEDED  a newer readout replaced it. Name the source id that carries the
                replacement.
    WRONG       it was wrong. Name the source id and the span that shows it.
    ABSENT      it is in no document -- THE HARDEST ONE TO EARN, AND THE ONE
                THAT WENT WRONG. Absence is only knowable about a library, so a
                deletion for absence must record, at the time: which sources
                were unheld, which documents the page cites without a source
                entry, and a bound row whose span B2 reported absent from the
                source that row names.

The last requirement is the spec's own, and it is what would have stopped this:
none of the three removed figures was bound to anything, so there was no row to
point at, and "it is in no document" was never available as a reason.

WHAT THIS DOES NOT DO
---------------------
It does not decide whether a deletion was right. It asks what the deletion was
argued from, and refuses one argued from the absence of evidence in a library
that was not complete. A person can still be wrong; they cannot be silently
wrong.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_store as store   # noqa: E402
import source_ledger as ledger  # noqa: E402
import bindings as B            # noqa: E402
import b13                      # noqa: E402
import spancheck as SC          # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# THE VOCABULARY IS THE LESSON.
#
# The correction of 2026-09-01 had only one word available for "we could not
# find this", and it was ABSENT, so the notice told readers the figures "came
# from no document". The true statement was narrower and much less damaging:
# WE CANNOT SHOW WHERE THIS CAME FROM. One is a claim about the world, the other
# about our own shelf, and a library is only ever evidence about the shelf.
#
# UNSOURCED is that word. It is the reason nearly every removal should carry,
# and ABSENT should be rare and hard, because it asserts something no library
# can establish.
REASONS = ("rewritten", "superseded", "wrong", "unsourced", "absent")


def path(slug: str) -> Path:
    return store.case_dir(slug) / "deletions.json"


def load(slug: str) -> dict:
    p = path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"_what_this_is":
            "Figures a correction removed from this page, and what each removal "
            "was argued from. See deletions.py: a removal is the least-checked "
            "text here and 35% of recorded errors came in with one.",
            "deletions": []}


def save(slug: str, doc: dict) -> None:
    path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def figures_in(html: str) -> set[str]:
    """Every checkable figure in a page's text, by b13's definition."""
    out = set()
    for sent in ledger.sentences(ledger.plain(ledger.body_only(html))):
        for m in b13.FIGURE.finditer(SC._norm(sent)):
            f = m.group(1).replace(",", "")
            if not b13._is_year(f):
                out.add(f)
    return out


def gone(slug: str, live_html: str, draft_html: str) -> list[str]:
    """Figures readers can see that the draft no longer carries."""
    return sorted(figures_in(live_html) - figures_in(draft_html))


def _absence_is_knowable(slug: str) -> tuple[bool, str]:
    """Could 'it is in no document' have been earned at all?"""
    unheld = b13.unheld(slug)
    if unheld:
        return False, ("%d source(s) are unheld (%s), so this library cannot "
                       "answer whether a figure is anywhere"
                       % (len(unheld), ", ".join(unheld[:6])))
    return True, "every source this issue names is held"


def check(slug: str, live_html: str, draft_html: str) -> list[tuple[str, str, str]]:
    missing = gone(slug, live_html, draft_html)
    if not missing:
        return [("figures a correction removed", OK,
                 "no figure readers can see has left the draft")]

    doc = load(slug)
    recorded = {d.get("figure"): d for d in (doc.get("deletions") or [])}
    rows, unaccounted, unearned = [], [], []
    for f in missing:
        d = recorded.get(f)
        if not d:
            unaccounted.append(f)
            continue
        if d.get("reason") not in REASONS:
            unearned.append("%s: reason %r is not one of %s"
                            % (f, d.get("reason"), ", ".join(REASONS)))
            continue
        if d["reason"] == "unsourced" and not (d.get("searched") or "").strip():
            unearned.append("%s: %r must say what was searched — it is a "
                            "statement about our shelf, so the shelf has to be "
                            "described" % (f, d["reason"]))
        if d["reason"] in ("superseded", "wrong") and not d.get("source_id"):
            unearned.append("%s: %r must name the source that settles it"
                            % (f, d["reason"]))
        if d["reason"] == "absent":
            ok, why = _absence_is_knowable(slug)
            if not ok:
                unearned.append("%s: removed for ABSENCE, and %s" % (f, why))
            elif not d.get("bound_row_absent"):
                unearned.append(
                    "%s: removed for ABSENCE with no bound row whose span a "
                    "check reported missing from the source it names. The spec's "
                    "own rule: a correction that deletes a claim must point at a "
                    "row whose span was absent" % f)
    rows.append(("figures a correction removed",
                 OK if not unaccounted else BAD,
                 "%d removed figure(s), each accounted for" % len(missing)
                 if not unaccounted else
                 "%d figure(s) readers can see have left the draft with no "
                 "record of why: %s — run deletions.py %s scan"
                 % (len(unaccounted), ", ".join(unaccounted[:8]), slug)))
    rows.append(("removals argued from something",
                 OK if not unearned else BAD,
                 "every removal names what settled it"
                 if not unearned else
                 "%d removal(s) not earned: %s"
                 % (len(unearned), " || ".join(unearned[:3]))))
    return rows


def scan(slug: str, live_html: str, draft_html: str) -> dict:
    doc = load(slug)
    have = {d.get("figure") for d in (doc.get("deletions") or [])}
    ok, why = _absence_is_knowable(slug)
    for f in gone(slug, live_html, draft_html):
        if f in have:
            continue
        doc["deletions"].append({
            "figure": f,
            "removed_on": date.today().isoformat(),
            "reason": "",
            "source_id": "",
            "bound_row_absent": "",
            "by": "",
            "library_at_the_time": why,
            "_fill_in": "reason: %s. `absent` additionally needs a bound row "
                        "whose span a check reported missing." % ", ".join(REASONS),
        })
    save(slug, doc)
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--live", required=True, help="path to the published version")
    ap.add_argument("--draft", required=True)
    ap.add_argument("--scan", action="store_true")
    a = ap.parse_args()
    live = Path(a.live).read_text(encoding="utf-8")
    draft = Path(a.draft).read_text(encoding="utf-8")
    if a.scan:
        doc = scan(a.slug, live, draft)
        print("\n  %d recorded removal(s) in %s\n"
              % (len(doc["deletions"]), path(a.slug)))
        return 0
    print()
    for label, st, detail in check(a.slug, live, draft):
        print("  %-7s %-34s %s" % ({OK: "ok", BAD: "STOP", WARN: "warn"}[st],
                                   label, detail))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
