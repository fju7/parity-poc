#!/usr/bin/env python3
"""
What Holds Up: the counterexample hunter.

WHY THIS EXISTS
---------------
On 2026-08-29 a reviewer found that issue two said, four times and without
qualification, that no randomised trial had ever compared these drugs against
each other. Two exist. A randomised phase III open-label trial of ribociclib
versus palbociclib, each with fulvestrant, was published in the Asian Pacific
Journal of Cancer Prevention in 2024; HARMONIA (NCT05207709) is a registered
head-to-head phase III of the same two drugs.

The claim came from NCCN, which says "the CDK4/6 inhibitors have not been
directly compared in clinical trials". We verified that the guideline says
that -- the operator opened the guideline and confirmed the sentence word for
word -- and then wrote it as our own unscoped assertion about the world.

Nothing in the pipeline was pointed at breaking it. Every role either checks
our figures against sources we chose, or argues on behalf of a source we
named. The source advocate for NCCN was asked whether the guideline says there
is no head-to-head trial, and answered yes, which is true and is not the
question. Nobody was arguing the other side of the sentence.

The lint already finds these sentences. Until now its output was a checklist
nobody was required to act on, which is documentation rather than a control.
This turns the list into an input.

WHAT MAKES IT WORK
------------------
The same thing that made the source advocate work: posture. A role asked to
"assess whether this claim is well supported" produces a balanced paragraph and
finds nothing. A role told "your job is to break this sentence, and you have
failed if you come back empty-handed without saying exactly where you looked"
goes hunting.

And it must search REGISTRIES, not only literature. Both missed trials are in
a registry: one terminated early, one published in a journal outside the
high-visibility set that a coverage sweep surfaces. A literature-and-coverage
search is a search of what got attention. A registry is a list of what was
started.

A NULL RESULT MUST BE DESCRIBED
-------------------------------
"I found no counterexample" and "I did not look properly" are the same string
unless the role is made to name what it searched. So every survival verdict
carries the queries run and the registries checked, and a verdict with neither
is treated as an unrun check rather than a clean one.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

fc = _load("factcheck_draft", ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py")
lint = _load("lint_claims", HERE / "lint_claims.py")
sl = _load("source_ledger", HERE / "source_ledger.py")

OK, BAD, WARN = "ok", "BLOCKED", "warn"

REGISTRIES = [
    "ClinicalTrials.gov (search by both drug names and by condition, and include "
    "terminated, withdrawn and unknown-status records)",
    "the WHO ICTRP portal",
    "EudraCT / CTIS, and ISRCTN",
    "FDA Drugs@FDA review documents — medical and statistical reviews",
    "EMA EPAR assessment reports",
    "conference abstracts, including trial-in-progress (TiP) abstracts, which are "
    "where a head-to-head trial appears years before it publishes",
]

SYSTEM = """You are a hostile reader with one job: BREAK THE SENTENCE BELOW.

You are not assessing whether it is well supported. You are not writing a
balanced view. You are looking for ONE counterexample, and if one exists and
you do not find it, you have failed.

WHY THIS ROLE EXISTS, stated plainly so you can look for the same shape.
A publication wrote, four times and without qualification, that no randomised
trial had ever compared three named drugs against one another. Two such trials
existed. The claim had been taken from a clinical guideline that said something
narrower, about one treatment setting, and was repeated by every summary of
that guideline — so it looked corroborated when it was only echoed. One of the
missed trials was terminated early; the other was published in a journal
outside the set a coverage search surfaces. Both were in a trial registry the
whole time.

SEARCH THE REGISTRIES, NOT ONLY THE LITERATURE. A literature-and-news search is
a search of what got attention. A registry is a list of what was started. You
must search, and name in your answer, at least these:
{registries}

HOW TO ATTACK A SENTENCE.

1. Strip it to its logical form. "No X has ever Y" is a universal negative over
   the whole world. One instance defeats it.
2. Ask what the claim would look like if it were FALSE, and search for that
   thing directly. Do not search for the topic; search for the counterexample.
3. Vary the vocabulary. The counterexample will not use our words. Try the drug
   names alone, the generic and brand names, "head-to-head", "versus",
   "comparative", "randomized" with a z and with an s, and the condition.
4. Check whether the claim was inherited. If our sentence restates something a
   guideline, a review or a press release says, find the ORIGINAL wording — it
   is usually narrower than ours, scoped to a setting or a line of therapy, and
   the scope was dropped when we adopted it. Report the original wording.
5. Look for the near-miss. A trial that is terminated, unpublished, in another
   language, in a small journal, or in a different line of therapy still breaks
   an unqualified universal.

RETURN ONLY a JSON array, one object per claim you were given:

{{
  "claim":        "the sentence, verbatim",
  "verdict":      "BROKEN" | "NARROWED" | "SURVIVED",
  "counterexample": "what breaks it, in one sentence. Empty if none found.",
  "citation":     "URL, registry ID, or full journal citation. Empty if none.",
  "quote":        "the source's own words establishing it — quoted, not paraphrased",
  "why_it_still_matters": "does this change the piece's conclusion, or only the
                   sentence? Say which. A counterexample that agrees with our
                   conclusion still breaks our sentence.",
  "inherited_from": "if our claim restates a source, that source's ACTUAL wording
                     and its scope. Empty if the claim is our own.",
  "searched":     "EVERY registry and database you searched and the queries you
                   ran. Required whatever the verdict. A survival verdict with
                   no search record is not a finding, it is an unrun check.",
  "confidence":   "HIGH" | "MEDIUM" | "LOW"
}}

BROKEN   a counterexample exists and you have cited it.
NARROWED the claim is true in a narrower scope than it is written in; give the
         scope in which it holds.
SURVIVED you searched properly and found nothing. Say where you looked.

Do not invent a counterexample. A fabricated citation is worse than a survival
verdict, because it will be printed. If you are not sure a thing exists, say
LOW confidence and give the search that would settle it.
"""


def universal_negatives(text: str) -> list[str]:
    """The sentences worth attacking: universal claims over a body of evidence."""
    out = []
    for s in lint.sentences(text):
        m = lint.GOVERNS.search(s)
        if not m:
            continue
        head = m.group(0).lower()
        if not re.match(r"\b(no|none|nobody|not one|never|the only|only)\b", head):
            continue
        out.append(re.sub(r"\s+", " ", s).strip())
    seen, uniq = set(), []
    for s in out:
        k = s[:80].lower()
        if k not in seen:
            seen.add(k); uniq.append(s)
    return uniq


LEADS = ROOT / "issues" / "leads"


def case_dir(slug: str) -> Path:
    """Where this hunt's files belong.

    A hunt run with --claim is candidate-stage work, and candidates live
    under issues/leads/<slug>, not issues/WHU-nnn-<slug>. On 2026-08-29
    seven such hunts -- on minors' social-media access, on the Australian
    impact analysis, on AI and cognition -- were written into
    issues/WHU-002-cdk46, because that was the only slug source_ledger's
    case_dir could resolve and it was the slug to hand. They then appeared
    in issue two's preflight as eleven unadjudicated counterexample
    verdicts against a page that mentions none of those subjects, and
    blocked its republication.

    That is not a filing error. It is a false finding about a different
    piece, sitting inside that piece's case file, indistinguishable from a
    real one. Leads resolve first, and a --claim run into a published case
    file has to be asked for twice.
    """
    lead = LEADS / slug
    if lead.is_dir():
        return lead
    return sl.case_dir(slug)


def hunt(claims: list[str]) -> list[dict] | None:
    user = json.dumps({"claims_to_break": claims}, indent=1, ensure_ascii=False)
    out = fc.call(SYSTEM.format(registries="\n".join("  - " + r for r in REGISTRIES)),
                  user, search=True, label="counterexample")
    if out is None:
        return None
    if isinstance(out, dict):
        out = out.get("results") or out.get("claims") or out.get("findings") or []
    return out


# ---------------------------------------------------------------------------

def _dir(slug: str) -> Path:
    d = case_dir(slug) / "counterexample"
    d.mkdir(exist_ok=True)
    return d


def write_template(slug: str, day: str, rows: list[dict]) -> Path:
    p = _dir(slug) / f"{day}-adjudication.md"
    out = [f"# {slug} — counterexample hunt, {day}", "",
           "One section per universal negative on the page. A claim is not cleared",
           "by a SURVIVED verdict alone: somebody has to read what was searched and",
           "say whether that search would have found the thing.", "",
           "    VERDICT: broken | narrowed | survived   — yours, not the role's",
           "    BASIS:   what you read to decide, with a locator",
           "    DID:     what changed on the page, or nothing and why", ""]
    n = 0
    for r in rows:
        n += 1
        out += ["", "---", "", f"### CE-{n:02d} — role says {r.get('verdict','?')}"
                               f" ({r.get('confidence','?')} confidence)", "",
                f"**We say.** {r.get('claim','')}", ""]
        if r.get("counterexample"):
            out += [f"**What breaks it.** {r['counterexample']}", "",
                    f"**Citation.** {r.get('citation','(none given)')}", ""]
            if r.get("quote"):
                out += [f"**Their words.** “{r['quote']}”", ""]
        if r.get("inherited_from"):
            out += [f"**We inherited this.** The original says: {r['inherited_from']}", ""]
        out += [f"**Does it change the conclusion.** {r.get('why_it_still_matters','')}", "",
                f"**Searched.** {r.get('searched','(NOTHING RECORDED — treat as an unrun check)')}", "",
                "VERDICT: ", "BASIS:   ", "DID:     ", ""]
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return p


VERDICT = re.compile(r"^\s*VERDICT:\s*(broken|narrowed|survived)\b", re.I | re.M)
BASIS = re.compile(r"^\s*BASIS:\s*(\S.*)$", re.M)


def open_items(slug: str) -> list[str]:
    d = case_dir(slug) / "counterexample"
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*-adjudication.md")):
        if "TEST" in f.name:      # regression runs against a known-broken page
            continue
        text = f.read_text(encoding="utf-8")
        for chunk in re.split(r"(?=^### )", text, flags=re.M)[1:]:
            head = chunk.splitlines()[0][4:].strip()
            if not (VERDICT.search(chunk) and BASIS.search(chunk)):
                out.append(f"{f.name}: {head}")
    return out


def preflight_rows(slug: str, page_text: str) -> list[tuple[str, str, str]]:
    claims = universal_negatives(page_text)
    d = case_dir(slug) / "counterexample"
    runs = [f for f in (sorted(d.glob("*-briefs.json")) if d.exists() else [])
            if "TEST" not in f.name]
    if not claims:
        return [("counterexample hunt", OK, "no universal negatives on the page")]
    if not runs:
        return [("counterexample hunt", BAD,
                 f"{len(claims)} universal negative(s) on the page and nobody has "
                 f"tried to break any of them. This is how 'no randomised trial has "
                 f"compared these drugs' published, twice, with two such trials in "
                 f"the registry")]
    try:
        done = {r.get("claim", "")[:60] for r in
                json.loads(runs[-1].read_text(encoding="utf-8"))}
    except Exception:
        done = set()
    missed = [c for c in claims if c[:60] not in done]
    rows = [("counterexample hunt", OK if not missed else BAD,
             f"{len(runs)} run(s), latest {runs[-1].name[:10]}, covering "
             f"{len(claims) - len(missed)} of {len(claims)} universal negative(s)"
             if not missed else
             f"{len(missed)} universal negative(s) added since the last hunt and "
             f"never attacked: " + " || ".join(c[:70] for c in missed[:2]))]
    op = open_items(slug)
    rows.append(("counterexample verdicts recorded", OK if not op else BAD,
                 "every claim attacked has a verdict and a basis"
                 if not op else
                 f"{len(op)} with no VERDICT/BASIS written: " + "; ".join(op[:3])))
    return rows


def cmd_run(args) -> int:
    if args.claim:
        claims = list(args.claim)
        if not (LEADS / args.slug).is_dir() and not args.anyway:
            print("\n  %s is a published case file, not a lead." % args.slug)
            print("  A --claim hunt is candidate-stage work and its verdicts will sit in")
            print("  that issue's preflight forever, unadjudicated, blocking it. Seven of")
            print("  these landed in cdk46 on 2026-08-29 and did exactly that.\n")
            print("  If this claim really is about %s's page, say so:" % args.slug)
            print("      ... run %s --claim \"...\" --anyway\n" % args.slug)
            print("  Otherwise make the lead first:")
            print("      mkdir -p issues/leads/<slug>\n")
            return 2
    else:
        if not args.page:
            print("  give --page or --claim")
            return 2
        page = ROOT / args.page
        text = lint.plain(page.read_text(encoding="utf-8"))
        claims = universal_negatives(text)
    if args.only:
        claims = [c for c in claims if any(k.lower() in c.lower() for k in args.only)]
    if not claims:
        print("  no universal negatives found")
        return 0
    print(f"  attacking {len(claims)} claim(s):")
    for c in claims:
        print("   -", c[:96])
    rows = hunt(claims)
    if rows is None:
        print("\n  THE CALL RETURNED NOTHING. This is an unrun check, not a clean one.")
        return 1
    day = args.day or date.today().isoformat()
    (_dir(args.slug) / f"{day}-briefs.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    p = write_template(args.slug, day, rows)
    broken = [r for r in rows if str(r.get("verdict", "")).upper() in ("BROKEN", "NARROWED")]
    print()
    for r in rows:
        print(f"  [{r.get('verdict','?'):8}] {str(r.get('claim',''))[:80]}")
        if r.get("counterexample"):
            print(f"             {str(r['counterexample'])[:110]}")
            print(f"             {str(r.get('citation',''))[:100]}")
    print(f"\n  {len(broken)} of {len(rows)} claim(s) broken or narrowed")
    print(f"  adjudicate  {p.relative_to(ROOT)}")
    return 0


def cmd_list(args) -> int:
    page = ROOT / args.page
    text = lint.plain(page.read_text(encoding="utf-8"))
    for c in universal_negatives(text):
        print(" -", c[:150])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="try to break the page's universal negatives")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("slug")
    r.add_argument("--page"); r.add_argument("--only", nargs="*")
    r.add_argument("--claim", action="append",
                   help="attack this sentence directly, instead of extracting from a page. "
                        "Use it at CANDIDATE stage, before anything is drafted, and use it "
                        "above all on the novelty claim: 'nobody has already made this "
                        "argument in public'. That claim is a universal negative over "
                        "everything anyone has published, this publication makes it in every "
                        "issue, and until 2026-08-29 nothing attacked it. Two consecutive "
                        "issues had their central contribution already in print.")
    r.add_argument("--day")
    r.add_argument("--anyway", action="store_true",
                   help="write a --claim hunt into a published case file anyway. "
                        "Only when the claim is genuinely about that issue's page.")
    r.set_defaults(fn=cmd_run)
    l = sub.add_parser("list"); l.add_argument("slug")
    l.add_argument("--page", required=True); l.set_defaults(fn=cmd_list)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
