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
Not "is this interesting" and not "has anybody said this". Both of those failed.
Interest picked four subjects in one day and killed all four; novelty kills
everything, because on any contested question somebody has published something.

    A well-informed non-expert would confidently believe X.
    The primary sources do not support X.

Both halves are falsifiable. The first is checkable against the coverage. The
second is the only thing this publication is actually good at.

The reader is specific: someone who reads widely, has a degree in something
else, follows an argument comfortably, and cannot evaluate a hazard ratio or
find an endnote. What they need is not what is trending. It is the place where
a view they hold from general reading does not survive its own sources.

WHY THIS REPLACED THE NOVELTY TEST
----------------------------------
On 2026-08-29 four candidates died on prior art in eight hours: the MONARCH 3
power argument (Tanguy 2018), the tobacco evidentiary comparison (Rutar 2026),
"what evidence would settle this" (National Academies 2024), and the audit of
Australia's cited evidence (Horwood 2026, citing four earlier critiques).

Every time, the prior art was in the ACADEMIC record while we were reading the
NEWS record. So the question is not whether anybody has published this. It is
whether anybody has published it WHERE THIS READER WOULD FIND IT. A finding
established in a journal and absent from the coverage is a subject. A finding
absent from both usually means we have not looked hard enough.

The tobacco analogy is the clean negative case. It died not because Rutar got
there first -- that is survivable, you cite him -- but because a well-read
person holds no confident belief about the evidentiary comparison at all. They
have never considered it. There was nothing to correct, which is why the piece
felt clever and read thin.

THE CONTRARIANISM GUARD
-----------------------
A test of the form "people believe X, the sources don't support X" rots into a
pose if the answer is always no. The guard is a required field: every candidate
records whether it CORRECTS, CONFIRMS or NARROWS the belief -- and a
publication that has never once confirmed a widely held belief has stopped
assessing evidence and started performing scepticism. The check below counts
across issues and says so.

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
        "The entry gate, answered BEFORE drafting. The threshold question is whether a "
        "well-informed non-expert would confidently believe something the primary sources do "
        "not support."),
    "belief": {
        "_note": ("What the reader already believes, stated as they would state it. If you "
                  "cannot write this sentence, there is nothing to correct and no subject -- "
                  "which is how the tobacco-analogy candidate died."),
        "statement": "",
        "how_we_know_they_believe_it": ("The coverage that settled it. Named outlets, quoted "
                                        "headlines. Not 'it is widely assumed'."),
        "carried_by": [{"outlet": "", "url": "", "date": "", "what_it_said": ""}],
    },
    "what_the_sources_show": {
        "_note": "What the primary sources actually support, and which sources.",
        "statement": "",
        "sources": [],
    },
    "direction": {
        "_note": ("CORRECTS, CONFIRMS or NARROWS. This field exists so the contrarianism guard "
                  "can count. A publication whose answer is always CORRECTS is performing "
                  "scepticism rather than assessing evidence, and is not to be trusted."),
        "value": "",
        "_values": ["corrects", "confirms", "narrows"],
    },
    "reader_with_a_decision": (
        "Who has a decision to make, a real cost of being wrong, and no time to read the "
        "literature? Name them. A subject with no such reader is interesting rather than "
        "useful, and interesting is how four candidates died in one day."),
    "public_record_check": {
        "_note": ("NOT 'has anybody published this'. On any contested question, somebody has. "
                  "The question is whether it has been carried WHERE THIS READER WOULD FIND IT. "
                  "Run the counterexample hunter on the belief statement, not on the finding."),
        "prior_art_found": [],
        "carried_in_general_coverage": "",
        "our_contribution": "translation, extension, or correction of the prior art -- say which",
    },
    "sources_are_open": "",
    "evidence_base_is_bounded": "",
    "kill_condition": (
        "What we would have to find for there to be no story. Usually one of: the reader does "
        "not actually believe this; the sources do support it; or it has already been carried "
        "in general coverage."),
    "kill_condition_tested": {
        "_note": "Filled in AFTER going to look, by whoever looked.",
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
    TEMPLATE["kill_condition"], TEMPLATE["reader_with_a_decision"],
    TEMPLATE["public_record_check"]["our_contribution"])}


def _filled(v) -> bool:
    t = str(v or "").strip()
    return bool(t) and t not in _PLACEHOLDERS


def _all_directions() -> dict:
    """Every recorded direction across every issue and candidate."""
    out = {}
    for d in list(CASES.glob("WHU-*")) + list((CASES / "leads").glob("*")):
        f = d / "premise.json"
        if not f.exists():
            continue
        try:
            v = (json.loads(f.read_text(encoding="utf-8"))
                 .get("direction") or {}).get("value", "")
        except Exception:
            continue
        if v:
            out[d.name] = v
    return out


def contrarianism_guard() -> tuple[str, str]:
    """Has this publication ever confirmed a widely held belief?"""
    dirs = _all_directions()
    if not dirs:
        return WARN, "no issue records a direction yet"
    confirms = [k for k, v in dirs.items() if v == "confirms"]
    n = len(dirs)
    if confirms:
        return OK, ("%d issue(s) recorded; %d confirm a widely held belief (%s)"
                    % (n, len(confirms), ", ".join(confirms[:3])))
    if n < 4:
        return WARN, ("%d issue(s) recorded, none confirming a widely held belief. Too few "
                      "to mean anything yet, and worth watching." % n)
    return BAD, ("%d issues and not one has confirmed a widely held belief. A test of the form "
                 "'people believe X, the sources do not support X' whose answer is always no is "
                 "not an evidence assessment, it is a pose. Either a subject where the belief "
                 "holds is overdue, or the selection is picking for the answer." % n)


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
                 "no premise.json — nothing records the belief this issue corrects, or what "
                 "would have meant there was no story. publish.py premise init %s" % slug)]
    rows = []

    b = d.get("belief") or {}
    have_belief = _filled(b.get("statement"))
    carried = [c for c in (b.get("carried_by") or []) if _filled(c.get("outlet"))]
    rows.append(("belief stated", OK if have_belief else lvl,
                 str(b.get("statement"))[:90] if have_belief else
                 "no belief recorded. If you cannot write what the reader already believes, "
                 "there is nothing to correct — which is how the tobacco-analogy candidate died"))
    rows.append(("belief shown to be held", OK if carried else lvl,
                 "%d outlet(s): %s" % (len(carried), ", ".join(c["outlet"] for c in carried[:4]))
                 if carried else
                 "no outlet named. 'Widely assumed' is not evidence that anyone assumes it"))

    w = d.get("what_the_sources_show") or {}
    rows.append(("what the sources show", OK if _filled(w.get("statement")) else lvl,
                 str(w.get("statement"))[:90] if _filled(w.get("statement")) else
                 "not recorded"))

    dirv = (d.get("direction") or {}).get("value", "")
    rows.append(("direction recorded", OK if dirv in ("corrects", "confirms", "narrows") else lvl,
                 dirv or "must be corrects, confirms or narrows — the contrarianism guard counts it"))

    st, detail = contrarianism_guard()
    rows.append(("contrarianism guard", st if not already_published else WARN, detail))

    rows.append(("reader with a decision", OK if _filled(d.get("reader_with_a_decision")) else lvl,
                 str(d.get("reader_with_a_decision"))[:90]
                 if _filled(d.get("reader_with_a_decision")) else
                 "nobody named. A subject with no reader who has a decision is interesting "
                 "rather than useful, and interesting killed four candidates in one day"))

    pr = d.get("public_record_check") or {}
    rows.append(("carried in general coverage?",
                 OK if _filled(pr.get("carried_in_general_coverage")) else lvl,
                 str(pr.get("carried_in_general_coverage"))[:90]
                 if _filled(pr.get("carried_in_general_coverage")) else
                 "not checked. The question is not whether anyone published it — somebody "
                 "always has — but whether this reader would have met it"))
    rows.append(("our contribution named", OK if _filled(pr.get("our_contribution")) else WARN,
                 str(pr.get("our_contribution"))[:90]
                 if _filled(pr.get("our_contribution")) else
                 "translation, extension or correction of the prior art — say which"))

    kill = d.get("kill_condition")
    rows.append(("kill condition written", OK if _filled(kill) else lvl,
                 str(kill)[:90] if _filled(kill) else "nothing recorded"))
    t = d.get("kill_condition_tested") or {}
    tested = _filled(t.get("by")) and t.get("result") in ("survived", "narrowed", "killed")
    rows.append(("kill condition tested", OK if tested else lvl,
                 "%s — tested by %s on %s" % (t.get("result"), t.get("by"), t.get("on"))
                 if tested else "nobody went looking for the fact that would have killed this"))
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
    g = sub.add_parser("guard", help="has this publication ever confirmed a widely held belief?")
    g.set_defaults(fn=lambda a: (print("\n  %s  %s\n" % contrarianism_guard()), 0)[1])
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
