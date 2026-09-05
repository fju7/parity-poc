#!/usr/bin/env python3
"""The WHU semantic-verification benchmark.

WHAT IT IS FOR
--------------
Every check in this repository was written after a specific incident and is
validated against that incident. That is good regression practice and it is not
an evaluation: nobody knows the false-negative rate against errors not yet made,
because there was no held-out corpus and no scoring. Ninety checks and twenty
thousand lines FEEL like rigour, and the only evidence about whether they work
is that errors keep arriving from regions nobody modelled.

This file makes that measurable, and it is the reason to stop adding checks
until it has been run.

THE QUESTION EACH CASE ASKS
---------------------------
One sentence, the evidence a production reviewer would actually have had at
that point, and one narrow question:

    Should this sentence be cleared for publication against this evidence?

Nothing else. Not "is it well written", not "could it be clearer". The judge
returns CLEAR or BLOCK and a reason.

THE METRIC THAT MATTERS
-----------------------
Not accuracy. **Publication-worthy false clears** -- a sentence that reached
readers and should not have. Accuracy averages that together with false blocks
and hides it. A judge that blocks everything scores 77% accuracy on this set
and is useless; a judge that clears everything scores 23% and is dangerous.

False blocks are reported too, and they are not free: a check that
over-triggers is one the operator learns to wave through, and it takes the
findings that mattered with it. But they are a different cost, so they are a
different number.

WHY THE CASES ARE REAL
----------------------
Every BLOCK case is a sentence that was actually drafted or published here, with
the actual span from the actual document. Every span was verified present in the
held bytes before the file was written. The CLEAR cases are the corrected forms
and their known-good neighbours, so a judge cannot score by blocking anything
that looks complicated.

Three of the CLEAR cases are deliberately adversarial:
  WHU-B-021 is a universal negative that is CORRECT because it is scoped;
  WHU-B-022 contains the word "Placebo" in a span for a trial with no placebo
  arm -- the exact misreading one of our own adversarial runs made at high
  confidence;
  WHU-B-002 and -004 are the fixes for -001 and -003, so a judge that blocks
  the whole neighbourhood is caught.

HOLDOUTS
--------
`--holdout FAMILY` withholds entire error families from any tuning set, because
the failure mode of the current architecture was fitting each check to the one
incident that prompted it. Reserve families, not individual cases.

RUNNING IT
----------
    benchmark.py --judge <cmd>      a command reading one JSON case on stdin and
                                    writing {"verdict": "...", "why": "..."}
    benchmark.py --dry-run          print the packets a judge would receive
    benchmark.py --baseline span    the straw man: clear anything whose figures
                                    all appear in a cited span. This is what the
                                    current architecture effectively does, and
                                    its score is the number any new layer has to
                                    beat.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "backend/data/whatholdsup/benchmark/cases.jsonl"
CLEAR, BLOCK = "CLEAR", "BLOCK"

QUESTION = (
    "You are deciding whether one sentence may be published.\n\n"
    "Below is the sentence, and the evidence available at the time it was "
    "written: the source documents' own words, quoted exactly.\n\n"
    "Answer one question: should this sentence be cleared for publication "
    "against this evidence?\n\n"
    "BLOCK it if the sentence asserts anything the evidence does not support -- "
    "including where every quoted number is correct. Attend to the SUBJECT the "
    "claim is about, the POPULATION it ranges over, whose VOICE a "
    "characterisation is in, what a negation actually denies, whether a "
    "composite endpoint has been shortened, and whether a claim about the "
    "publication's own process or library is true.\n\n"
    "CLEAR it if the sentence says no more than the evidence carries. Do not "
    "block a claim merely for being a negative, for being complicated, or for "
    "quoting an awkward source.\n\n"
    "Reply with JSON: {\"verdict\": \"CLEAR\" or \"BLOCK\", \"why\": \"one sentence\"}"
)


def load(holdout: list[str] | None = None, only: list[str] | None = None) -> list[dict]:
    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    if holdout:
        rows = [r for r in rows if r["family"] not in holdout]
    if only:
        rows = [r for r in rows if r["family"] in only]
    return rows


def packet(case: dict) -> str:
    """Exactly what a production reviewer would have had. NOT the answer.

    `why`, `provenance` and `verdict` are withheld: they are the grading key.
    Handing a judge the reason the sentence is wrong and asking whether it is
    wrong measures nothing.
    """
    ev = "\n\n".join(
        "SOURCE %s says, verbatim:\n  “%s”" % (e["source_id"], e["span"])
        for e in case["evidence"]) or "(no source is cited for this sentence)"
    return "%s\n\n---\n\nSENTENCE:\n  %s\n\n---\n\nEVIDENCE:\n\n%s" % (
        QUESTION, case["sentence"], ev)


# ---------------------------------------------------------------------------
# the straw man: what the current architecture effectively decides
# ---------------------------------------------------------------------------

NUM = re.compile(r"\d+(?:\.\d+)?")


def span_baseline(case: dict) -> tuple[str, str]:
    """Clear a sentence if every figure it carries appears in a cited span.

    This is the architecture's present logic stated as a judge. Its score is
    the floor: a semantic layer that does not beat it is buying nothing.
    """
    ev = " ".join(e["span"] for e in case["evidence"])
    figs = set(NUM.findall(case["sentence"]))
    if not case["evidence"]:
        return BLOCK, "no source is cited"
    missing = [f for f in figs if f not in ev]
    if missing:
        return BLOCK, "figures not in any cited span: %s" % ", ".join(sorted(missing)[:3])
    return CLEAR, "every figure it carries is in a cited span"


def run_judge(cmd: str, case: dict) -> tuple[str, str]:
    p = subprocess.run(cmd, shell=True, input=json.dumps({
        "id": case["id"], "prompt": packet(case),
        "sentence": case["sentence"], "evidence": case["evidence"]}),
        capture_output=True, text=True, timeout=180)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
        v = str(out.get("verdict", "")).upper()
        return (v if v in (CLEAR, BLOCK) else BLOCK), str(out.get("why", ""))[:300]
    except Exception as exc:                                   # noqa: BLE001
        return BLOCK, "judge output unparseable (%s): %s" % (exc, p.stdout[:120])


def score(results: list[tuple[dict, str, str]]) -> dict:
    fam = defaultdict(lambda: {"n": 0, "false_clear": 0, "false_block": 0, "right": 0})
    tot = Counter()
    for case, got, _why in results:
        want = case["verdict"]
        f = fam[case["family"]]
        f["n"] += 1
        tot["n"] += 1
        if got == want:
            f["right"] += 1; tot["right"] += 1
        elif want == BLOCK and got == CLEAR:
            f["false_clear"] += 1; tot["false_clear"] += 1
        else:
            f["false_block"] += 1; tot["false_block"] += 1
    return {"by_family": dict(fam), "total": dict(tot)}


def report(results, s) -> None:
    t = s["total"]
    print()
    print("  %d case(s)" % t["n"])
    print("  FALSE CLEARS      %d   <- sentences that would have reached readers"
          % t.get("false_clear", 0))
    print("  false blocks      %d   (a different cost: over-triggering gets waived)"
          % t.get("false_block", 0))
    print("  correct           %d" % t.get("right", 0))
    print()
    print("  %-52s %5s %5s %5s" % ("FAMILY", "n", "MISS", "over"))
    for name, f in sorted(s["by_family"].items(),
                          key=lambda kv: (-kv[1]["false_clear"], kv[0])):
        mark = " <<<" if f["false_clear"] else ""
        print("  %-52s %5d %5d %5d%s" % (name[:52], f["n"], f["false_clear"],
                                         f["false_block"], mark))
    print()
    misses = [(c, g, w) for c, g, w in results
              if c["verdict"] == BLOCK and g == CLEAR]
    if misses:
        print("  CLEARED WHEN IT SHOULD HAVE BLOCKED")
        for c, _g, w in misses:
            print("    %-11s %s" % (c["id"], c["sentence"][:78]))
            print("                the judge said: %s" % (w or "(no reason)")[:96])
            print("                actually wrong because: %s" % c["why"][:96])
        print()
    print("  A judge that BLOCKS everything scores 0 false clears and is useless.")
    print("  Read the two numbers together, and never the accuracy alone.")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--judge", help="command reading a JSON case on stdin")
    ap.add_argument("--baseline", choices=("span",),
                    help="run a built-in straw man instead of a model")
    ap.add_argument("--holdout", action="append", default=[],
                    help="withhold an error FAMILY (repeatable)")
    ap.add_argument("--only", action="append", default=[],
                    help="run only this FAMILY (repeatable)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the packets a judge would receive, and stop")
    ap.add_argument("--json", metavar="FILE", help="write raw results")
    a = ap.parse_args()

    cases = load(a.holdout or None, a.only or None)
    if not cases:
        print("no cases match those filters"); return 2

    if a.dry_run:
        for c in cases:
            print("=" * 72); print("%s  [%s]" % (c["id"], c["family"]))
            print(packet(c)); print()
        return 0

    if a.baseline:
        results = [(c, *span_baseline(c)) for c in cases]
        print("\n  BASELINE: clear a sentence if every figure it carries is in a cited span.")
        print("  This is the current architecture's logic, stated as a judge.")
    elif a.judge:
        results = [(c, *run_judge(a.judge, c)) for c in cases]
        print("\n  JUDGE: %s" % a.judge)
    else:
        print("give --judge, --baseline or --dry-run"); return 2

    if a.holdout:
        print("  HELD OUT: %s" % ", ".join(a.holdout))
    s = score(results)
    report(results, s)
    if a.json:
        Path(a.json).write_text(json.dumps(
            {"results": [{"id": c["id"], "family": c["family"],
                          "want": c["verdict"], "got": g, "why": w}
                         for c, g, w in results], "score": s},
            indent=2), encoding="utf-8")
        print("  wrote %s\n" % a.json)
    return 1 if s["total"].get("false_clear") else 0


if __name__ == "__main__":
    raise SystemExit(main())
