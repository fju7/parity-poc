#!/usr/bin/env python3
"""B16 -- READ WHAT CHANGED, BEFORE IT IS THE ONLY THING NOBODY HAS READ.

THE PROBLEM, MEASURED
---------------------
Two page-gate runs on issue one produced eleven findings that were right. What
kind of comparison settles each:

    a claim about a document NOT IN THE LIBRARY .................. 4
    the page contradicting itself, or arithmetic on its own text .. 2
    a factual claim carrying no citation .......................... 2
    a claim contradicted by sources we DO hold .................... 1
    our own inference, presented as fact .......................... 1
    a source reading nobody has confirmed ......................... 1

Every deterministic check in this repository asks ONE question: is this string
in that document. It is a good question and it answers, at best, two of the
eleven. Nine are about the page's relation to itself, or to a claim it never
sourced, or to an inference it never marked.

That is why fixing errors produces errors. A correction is new prose, written
fast, in exactly those classes -- and it is the least-checked text on the page.
error_taxonomy measured it before this file existed: 35% of adjudicated
corrections on issue two were introduced by an earlier correction.

WHY THE GATE IS NOT THE ANSWER
------------------------------
The gate does ask these questions, and it costs about $6 because it re-reads
the whole page every time: 21 model calls, 85 web searches, 1.5M tokens. At that
price it runs twice per issue, so between the two runs every correction goes out
unread by anything.

A correction changes five sentences. Reading five sentences is not a $6 problem.

WHAT THIS DOES
--------------
Takes the page as it was and the page as it is, and looks ONLY at what changed.

  free, deterministic:
    - a changed sentence carrying a figure that is in no held document
    - a changed sentence carrying a figure and bound to nothing

  one model call, over the changed sentences and the page they now sit in:
    - does this sentence contradict something else on this page?
    - does it assert a fact the page sources nowhere?
    - is it our own inference or arithmetic, presented as fact?

Those three questions are the nine findings the deterministic checks cannot
reach. Scoped to a diff they are one call, not twenty-one.

WHAT IT IS NOT
--------------
Not a replacement for the gate: it never looks outside the library, so it cannot
find that a figure belongs to a different readout, or that an outlet said
something else. It is the check that runs BETWEEN gate runs, so that a
correction is not the only text on the page nobody has read.
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_ledger as ledger  # noqa: E402
import bindings as B            # noqa: E402
import b13                      # noqa: E402
import spancheck as SC          # noqa: E402
import autobind as AB           # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OK, BAD, WARN = "ok", "BLOCKED", "warn"

SYSTEM = """You are reading sentences that were just added to or changed in a
published evidence-assessment page, against the page they now sit in.

You have three questions and no others. Do not comment on style, emphasis or
word choice. Do not check anything against the outside world -- you cannot see
it, and a guess about a source is the error this publication makes most.

  1 CONTRADICTION. Does the changed sentence contradict something else on this
    page?

    THE OTHER SIDE IS USUALLY NOT IN YOUR LIST. A contradiction is created as
    often by changing one side as the other: the sentence you are given may now
    contradict a HEADING, a summary bullet, a table note or a source note that
    nobody touched. Go looking for the other side in the whole page, not among
    the changed sentences.

    Read every heading and subheading in the page as a claim, because a reader
    does. "The distinction the coverage collapsed", standing above a paragraph
    that says every outlet attributed correctly, is a contradiction even though
    the heading is old and the paragraph is new.

    An accusation the page elsewhere says it cannot evidence is a contradiction:
    "that is what the headlines did", where the page has just said every outlet
    it holds attributed the figures correctly and it holds no counter-example.

  2 UNSOURCED. Does it assert a fact about the world that this page attributes
    to nothing? Not "is it true" -- is there any named source for it here.

  3 OURS. Is it an inference, a calculation or a comparison the page performed,
    presented as though it were reported? An interval nobody published, a
    subtraction, a "which means" that goes beyond what a source said.

Return JSON: {"findings":[{"sentence":"<the changed sentence, verbatim>",
"kind":"CONTRADICTION|UNSOURCED|OURS","why":"<one sentence>",
"other":"<the sentence it contradicts, verbatim, or empty>"}]}
Empty findings list if there is nothing. Quote sentences exactly as given."""


def sentences_of(html: str) -> list[str]:
    return [" ".join(s.split())
            for s in ledger.sentences(ledger.plain(ledger.body_only(html)))]


def changed(before: str, after: str) -> list[str]:
    a, b = sentences_of(before), sentences_of(after)
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag in ("replace", "insert"):
            out.extend(x for x in b[j1:j2] if len(x) > 40)
    return out


def at(rev: str, path: str) -> str:
    return subprocess.run(["git", "show", "%s:%s" % (rev, path)],
                          cwd=str(ROOT), capture_output=True, text=True).stdout


def deterministic(slug: str, new: list[str]) -> list[dict]:
    """The two questions that need no model."""
    doc = B.load(slug)
    # A JUDGEMENT rests on premises, not on a single span -- that is what the
    # bucket means. Testing only for `span` reported two correctly-bound
    # inferences as "resting on nothing this system can name", which is the
    # check describing an absence it was not equipped to see. Both shapes count
    # as bound; a row with neither still does not.
    bound = {r["sentence"][:80] for r in (doc.get("bindings") or {}).values()
             if r.get("span") or r.get("premises")}
    out = []
    for s in new:
        figs = [m.group(1).replace(",", "")
                for m in b13.FIGURE.finditer(SC._norm(s))
                if not b13._is_year(m.group(1).replace(",", ""))]
        if not figs:
            continue
        for f in figs:
            if not b13.where(f, slug):
                out.append({"sentence": s, "kind": "FIGURE_IN_NOTHING_HELD",
                            "why": "%s is in no document this issue holds, and "
                                   "this sentence is new" % f, "other": ""})
        if s[:80] not in bound:
            out.append({"sentence": s, "kind": "NEW_AND_UNBOUND",
                        "why": "carries %s and rests on nothing this system can "
                               "name" % ", ".join(figs[:3]), "other": ""})
    return out


def review(slug: str, new: list[str], page: str) -> list[dict]:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fc", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
    fc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fc)
    fc.enter_issue(slug)
    body = " ".join(sentences_of(page))
    user = json.dumps({"changed_sentences": new, "the_page": body[:120000]},
                      ensure_ascii=False)
    out = fc.call(SYSTEM, user, search=False, label="changecheck")
    if not out:
        return [{"sentence": "", "kind": "UNRUN",
                 "why": "the review call returned nothing usable — an unrun "
                        "check is not a pass", "other": ""}]
    if isinstance(out, dict):
        out = out.get("findings") or []
    return out


def preflight_rows(slug: str, findings: list[dict],
                   n_changed: int) -> list[tuple[str, str, str]]:
    if not n_changed:
        return [("changed sentences reviewed", OK, "nothing has changed")]
    if not findings:
        return [("changed sentences reviewed", OK,
                 "%d changed sentence(s), nothing found" % n_changed)]
    return [("changed sentences reviewed", BAD,
             "%d finding(s) in %d changed sentence(s): %s"
             % (len(findings), n_changed,
                " || ".join("%s: %s" % (f.get("kind"), (f.get("why") or "")[:70])
                            for f in findings[:3])))]



# ---------------------------------------------------------------------------
# the record, and the gate row
# ---------------------------------------------------------------------------
#
# A review is bound to the page's CONTENT HASH. Edit the page and the review
# stops applying, which is the whole point: the text nobody has read is always
# the text written last.

import hashlib   # noqa: E402
import source_store as store  # noqa: E402


def page_sha(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]


def record_path(slug: str) -> Path:
    return store.case_dir(slug) / "change-reviews.json"


def load_reviews(slug: str) -> dict:
    p = record_path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"_what_this_is":
            "Reviews of what changed, bound to the page's content hash. See "
            "changecheck.py: between two gate runs every correction is text "
            "nobody has read, and 35% of recorded errors came in with one.",
            "reviews": []}


def save_review(slug: str, html: str, before: str, n: int,
                findings: list[dict]) -> None:
    from datetime import datetime, timezone
    doc = load_reviews(slug)
    doc["reviews"].append({
        "sha": page_sha(html), "against": before, "changed": n,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "findings": findings,
    })
    record_path(slug).write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def gate_rows(slug: str, html: str) -> list[tuple[str, str, str]]:
    doc = load_reviews(slug)
    sha = page_sha(html)
    mine = [r for r in (doc.get("reviews") or []) if r.get("sha") == sha]
    if not mine:
        return [("changed sentences reviewed", BAD,
                 "the page has changed since the last review of what changed, "
                 "and nothing has read the new text. It costs about three cents: "
                 "changecheck.py %s --page <page> --before <rev>" % slug)]
    last = mine[-1]
    open_ = last.get("findings") or []
    if open_:
        return [("changed sentences reviewed", BAD,
                 "%d finding(s) in the %d sentence(s) changed since %s: %s"
                 % (len(open_), last.get("changed", 0), last.get("against", "?"),
                    " || ".join("%s" % f.get("kind") for f in open_[:4])))]
    return [("changed sentences reviewed", OK,
             "%d changed sentence(s) reviewed against the page, nothing found"
             % last.get("changed", 0))]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", required=True)
    ap.add_argument("--before", required=True,
                    help="git rev to compare against")
    ap.add_argument("--after", help="a file to use as the new version, for "
                    "replaying a past state instead of the working page")
    ap.add_argument("--no-model", action="store_true",
                    help="deterministic questions only")
    a = ap.parse_args()

    after = Path(a.after if a.after else ROOT / a.page).read_text(encoding="utf-8")
    before = at(a.before, a.page)
    if not before:
        print("\n  could not read %s at %s\n" % (a.page, a.before))
        return 2
    new = changed(before, after)
    print("\n  %d changed sentence(s) since %s\n" % (len(new), a.before))
    found = deterministic(a.slug, new)
    if not a.no_model and new:
        found += review(a.slug, new, after)
    for f in found:
        print("  %-24s %s" % (f.get("kind"), (f.get("why") or "")[:96]))
        print("      %s" % (f.get("sentence") or "")[:110])
        if f.get("other"):
            print("      against: %s" % f["other"][:110])
    save_review(a.slug, after, a.before, len(new), found)
    if not found:
        print("  nothing found")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
