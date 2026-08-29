#!/usr/bin/env python3
"""
What Holds Up: the entry gate.

WHY THIS EXISTS
---------------
Issue two was selected the wrong way round, and the selection error caused the
reporting error.

What Holds Up exists for questions where wide coverage missed a fact or a
nuance readers would want. Issue one fits: Merck and Moderna announced a large
trial had succeeded, released no numbers, and the coverage carried it anyway.
The antagonist was already standing in public; the piece did not have to invent
an angle, and none of its errors were about its premise.

Issue two came from a Signal inquiry -- somebody wanted to know which breast
cancer drug worked best. There was no public claim. So the work ran backwards:
we found the category difference first, asked what would make it matter, and
wrote the sentence that made it matter. That sentence -- "a guideline grades one
of them above the other two" -- is the one that turned out to be false, and it
was false because it had been fitted to the finding rather than found in the
world.

Eighteen fact-check runs passed it. They had to: every check runs *against* a
premise, and none runs *on* one. A page's premise is the one claim nothing
downstream examines.

THE THRESHOLD QUESTION
----------------------
    Is there a falsifiable proposition here worth evaluating and writing about?

Falsifiable is the operative word, and it has a mechanical test: you can write
down, in advance, what you would have to find for there to be no story. That is
the `kill_condition` field, and it is the whole point of this file.

Had issue two carried "if the guideline turns out to list all three as equally
preferred, there is no piece here", the fact that killed the framing would have
been the thing we were actively hunting for. Instead it was the one fact nobody
in the pipeline had any reason to look for. That is not a model failure; it is
an incentive structure, and writing the condition down before the search starts
is most of the fix.

    A PREMISE NOBODY TRIED TO KILL IS NOT A PREMISE THAT SURVIVED.

ON REUSING SIGNAL WORK
----------------------
Signal answers a question somebody asked; its output is an answer. What Holds Up
examines a claim already in circulation; its output is a correction to a public
record. A Signal inquiry is a fine *lead* -- it can tell you a topic is contested
and where the evidence is thin. It cannot supply the premise. The pipeline has
to run forward: lead, then find the public claim, then verify it is real and
carried, then report.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "issues"
OK, BAD, WARN = "ok", "BLOCKED", "warn"

TEMPLATE = {
    "_what_this_is": (
        "The entry gate for this issue, answered BEFORE drafting. The threshold "
        "question is whether there is a falsifiable proposition here worth "
        "evaluating and writing about. Every field below is answered from the "
        "world, not from what we have already found."),
    "falsifiable_proposition": (
        "The one sentence this issue tests. It must be capable of being false."),
    "public_claim": {
        "_note": ("The sentence already in circulation that this issue examines. "
                  "Not the subject -- the sentence. If you cannot quote it and say "
                  "where it was said, there is no subject yet, and what you have is "
                  "a Signal inquiry."),
        "quote": "",
        "who_said_it": "",
        "url": "",
        "date": "",
    },
    "carried_by": [
        {"_note": "Outlets that carried it. Name them. If the honest answer is "
                  "that nobody carried it, this is not a What Holds Up issue.",
         "outlet": "", "url": "", "date": ""},
    ],
    "we_think_missing": (
        "What we believe the coverage missed -- written BEFORE going looking, so "
        "that what we find can contradict it."),
    "kill_condition": (
        "What we would have to find for there to be no story. Specific enough "
        "that someone could go and check it. This is the field that decides "
        "whether the proposition is falsifiable at all."),
    "kill_condition_tested": {
        "_note": ("Filled in AFTER going to look, by whoever looked. An untested "
                  "kill condition blocks the publish: a premise nobody tried to "
                  "kill is not a premise that survived."),
        "by": "", "on": "", "result": "", "_result_values": ["survived", "narrowed", "killed"],
        "note": "",
    },
    "lead_came_from": "",
}


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r}")
    return hits[0]


def path(slug: str) -> Path:
    return case_dir(slug) / "premise.json"


def load(slug: str) -> dict | None:
    p = path(slug)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# The template ships with prose in every field explaining what belongs there.
# A file where that prose is still sitting in the slot is an unanswered file,
# and treating it as answered would make this gate worse than nothing -- a
# process that reports "premise recorded" over an empty premise is exactly the
# kind of check that teaches people to stop reading the board.
_PLACEHOLDERS = {str(v).strip() for v in (
    TEMPLATE["falsifiable_proposition"], TEMPLATE["we_think_missing"],
    TEMPLATE["kill_condition"])}


def _filled(v) -> bool:
    t = str(v or "").strip()
    return bool(t) and t not in _PLACEHOLDERS


def preflight_rows(slug: str, *, already_published: bool = False) -> list[tuple[str, str, str]]:
    """Rows for the board.

    `already_published` downgrades every block to a warning. A correction to a
    live page must not be held up by an entry test the piece could not have
    taken, because the gate did not exist when it was drafted -- blocking a
    correction is worse than the error it corrects. The gate binds from the
    next issue, where it belongs: before drafting, not after publishing.
    """
    d = load(slug)
    lvl = WARN if already_published else BAD
    if d is None:
        return [("premise recorded", lvl,
                 f"no premise.json — nothing recorded the public claim this issue "
                 f"examines, or what would have meant there was no story. "
                 f"Write one: publish.py premise init {slug}")]
    rows = []

    claim = d.get("public_claim") or {}
    have = _filled(claim.get("quote")) and (_filled(claim.get("url"))
                                            or _filled(claim.get("who_said_it")))
    rows.append(("public claim quoted", OK if have else lvl,
                 f"{claim.get('who_said_it') or 'source'}: "
                 f"{str(claim.get('quote'))[:80]}" if have else
                 "no quoted claim with a source — the subject has not been shown "
                 "to exist outside this page"))

    carried = [c for c in (d.get("carried_by") or [])
               if _filled(c.get("outlet"))]
    rows.append(("claim carried in public", OK if carried else WARN,
                 f"{len(carried)} outlet(s): "
                 + ", ".join(c["outlet"] for c in carried[:4]) if carried else
                 "no outlet named. A claim nobody carried may be a fine Signal "
                 "inquiry and is not a What Holds Up issue"))

    kill = d.get("kill_condition")
    rows.append(("kill condition written", OK if _filled(kill) else lvl,
                 str(kill)[:90] if _filled(kill) else
                 "nothing recorded that would have meant there was no story. "
                 "An unfalsifiable premise is the one issue two shipped"))

    t = d.get("kill_condition_tested") or {}
    tested = _filled(t.get("by")) and t.get("result") in ("survived", "narrowed", "killed")
    rows.append(("kill condition tested", OK if tested else lvl,
                 f"{t.get('result')} — tested by {t.get('by')} on {t.get('on')}"
                 if tested else
                 "nobody went looking for the fact that would have killed this. "
                 "A premise nobody tried to kill is not a premise that survived"))
    if tested and t.get("result") == "killed":
        rows.append(("premise survived", lvl,
                     "the kill condition was met: %s" % (t.get("note") or "no note")))
    return rows


def cmd_init(args) -> int:
    p = path(args.slug)
    if p.exists() and not args.force:
        print(f"  {p.relative_to(ROOT)} already exists (use --force to overwrite)")
        return 1
    p.write_text(json.dumps(TEMPLATE, indent=2, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    print(f"  wrote {p.relative_to(ROOT)}")
    print("  Answer it before drafting. The kill condition is the field that matters.")
    return 0


def cmd_status(args) -> int:
    print()
    for label, st, detail in preflight_rows(args.slug):
        print(f"{ {OK:'  ok ', BAD:' STOP', WARN:' warn'}[st]:>7}  {label:26} {detail}")
    print()
    return 0


def cmd_test(args) -> int:
    """Record the result of going to look for the fact that would kill it."""
    d = load(args.slug)
    if d is None:
        print("no premise.json — nothing to test"); return 1
    d["kill_condition_tested"] = {
        "_note": d.get("kill_condition_tested", {}).get("_note", ""),
        "by": args.by, "on": args.on or date.today().isoformat(),
        "result": args.result, "note": args.note or "",
    }
    path(args.slug).write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    print(f"  {args.slug}: kill condition {args.result}, tested by {args.by}")
    if args.result == "killed":
        print("  This issue does not publish. That is the gate working.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="the entry gate: is there a falsifiable "
                                             "proposition here worth writing about?")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("slug")
    i.add_argument("--force", action="store_true"); i.set_defaults(fn=cmd_init)
    s = sub.add_parser("status"); s.add_argument("slug"); s.set_defaults(fn=cmd_status)
    t = sub.add_parser("test", help="record what happened when you went to kill it")
    t.add_argument("slug")
    t.add_argument("--result", choices=("survived", "narrowed", "killed"), required=True)
    t.add_argument("--by", required=True)
    t.add_argument("--on")
    t.add_argument("--note")
    t.set_defaults(fn=cmd_test)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
