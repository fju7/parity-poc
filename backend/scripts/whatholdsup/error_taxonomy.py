#!/usr/bin/env python3
"""What kind of thing settles each error we have actually made.

WHY THIS EXISTS
---------------
On 2026-09-01 the operator asked the question this project has been avoiding:
every gate run finds new errors, so is the process converging at all, or is
accurate evidence assessment simply beyond what we can build?

It is answerable, because the errors are written down. Seventeen adjudicated
corrections on issue two, each with what it was, how it was found and what
settled it. This file classifies every one by the ONLY question that matters
for reliability:

    WHAT KIND OF THING WOULD HAVE CAUGHT THIS BEFORE A READER SAW IT?

    REGISTRY    a structured field in a trial record. Free, instant, exact.
    LEDGER      our own repository contradicting itself. Free.
    QUOTATION   a string that is or is not in a document we hold.
    ARITHMETIC  a relation between numbers already on the page.
    READING     somebody has to open a document and understand a claim.
    HUMAN       a judgment: is this fair, is this the right emphasis.

The number that answers the operator's question is the share of real errors
that fall in the first four buckets, and how much of that share now has a
check that runs without being asked.

WHAT THIS IS NOT
----------------
It is not a claim that the classification is objective. Each row records the
evidence that settled the error in fact, not a guess about what might have.
Where an error was settled by a person reading a paper, it is READING even if
one could imagine a machine doing it.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REGISTRY, LEDGER, QUOTATION, ARITHMETIC, READING, HUMAN = (
    "REGISTRY", "LEDGER", "QUOTATION", "ARITHMETIC", "READING", "HUMAN")

# Every adjudicated correction on issue two, and what actually settled it.
# `check` is the module that would catch it today, or "" if nothing would.
ERRORS = [
 dict(id="CORR-01", what="four sentences said no randomised trial had compared any pair; two exist",
      settled_by=REGISTRY, check="counterexample + registry_facts",
      found_by="counterexample hunt", introduced_by=""),
 dict(id="CORR-02", what="test direction declared unestablishable; the registry posted it",
      settled_by=REGISTRY, check="registry_facts", found_by="preflight lint",
      introduced_by=""),
 dict(id="CORR-03", what="corrigendum called paywalled, then open access; first was right",
      settled_by=READING, check="", found_by="gate", introduced_by="CORR-era fix"),
 dict(id="CORR-04", what="email asserted a sourcing absence the page did not",
      settled_by=LEDGER, check="email_parity", found_by="parity check",
      introduced_by=""),
 dict(id="CORR-05", what="wrong first author, fixed in repo, never published",
      settled_by=READING, check="attributions.json", found_by="human",
      introduced_by=""),
 dict(id="CORR-06", what="MONALEESA-7 cited with PALOMA-2's registry number",
      settled_by=REGISTRY, check="registry_settle identity", found_by="gate",
      introduced_by="CORR-02"),
 dict(id="CORR-07", what="'year of updated data 2023' quoted; the string is not in the paper",
      settled_by=QUOTATION, check="quotations", found_by="quotation matcher",
      introduced_by=""),
 dict(id="CORR-08", what="source prints 73.3 and 70.2; page printed one silently",
      settled_by=READING, check="", found_by="gate", introduced_by=""),
 dict(id="CORR-09", what="three corrections recorded in the repo and not on the page",
      settled_by=LEDGER, check="", found_by="claude", introduced_by=""),
 dict(id="CORR-10", what="page said a paper was behind a wall; the ledger says it was read",
      settled_by=LEDGER, check="source_ledger.inaccessibility_claims", found_by="gate",
      introduced_by=""),
 dict(id="CORR-11", what="NEJM's p=0.008 called one-sided; registry's one-sided p is 0.004",
      settled_by=ARITHMETIC, check="", found_by="gate", introduced_by="CORR-02"),
 dict(id="CORR-12", what="HARMONIA credited with finding no difference; it never reported",
      settled_by=REGISTRY, check="", found_by="gate", introduced_by="CORR-01"),
 dict(id="CORR-13", what="'29 blocks of four' is 116/4, our arithmetic as the paper's",
      settled_by=ARITHMETIC, check="", found_by="gate", introduced_by=""),
 dict(id="CORR-14", what="our interval-width observation attributed to Tanguy, who never makes it",
      settled_by=READING, check="", found_by="gate on the email", introduced_by=""),
 dict(id="CORR-15", what="'neither is first line with an AI'; HARMONIA's arms include letrozole",
      settled_by=REGISTRY, check="", found_by="gate", introduced_by="CORR-01"),
 dict(id="CORR-16", what="PALMARES-2's registered primary endpoint called exploratory",
      settled_by=REGISTRY, check="", found_by="gate", introduced_by=""),
 dict(id="CORR-17", what="third sentence crediting HARMONIA with a finding it never reported",
      settled_by=REGISTRY, check="", found_by="gate", introduced_by="CORR-01"),
]

MECHANICAL = (REGISTRY, LEDGER, QUOTATION, ARITHMETIC)


def report() -> str:
    L = []
    n = len(ERRORS)
    by = Counter(e["settled_by"] for e in ERRORS)
    mech = [e for e in ERRORS if e["settled_by"] in MECHANICAL]
    covered = [e for e in mech if e["check"]]
    uncovered = [e for e in mech if not e["check"]]
    judgment = [e for e in ERRORS if e["settled_by"] not in MECHANICAL]
    introduced = [e for e in ERRORS if e["introduced_by"]]

    L.append("=" * 72)
    L.append("WHAT WOULD HAVE CAUGHT IT — %d adjudicated errors on issue two" % n)
    L.append("=" * 72)
    L.append("")
    for k in (REGISTRY, LEDGER, QUOTATION, ARITHMETIC, READING, HUMAN):
        if by.get(k):
            L.append("  %-11s %2d  (%2d%%)" % (k, by[k], round(100 * by[k] / n)))
    L.append("")
    L.append("  MECHANICALLY SETTLEABLE          %2d of %d  (%d%%)"
             % (len(mech), n, round(100 * len(mech) / n)))
    L.append("     of those, a check exists      %2d        (%d%% of mechanical)"
             % (len(covered), round(100 * len(covered) / max(len(mech), 1))))
    L.append("     of those, nothing checks yet  %2d" % len(uncovered))
    L.append("")
    L.append("  NEEDS A PERSON TO READ OR JUDGE  %2d of %d  (%d%%)"
             % (len(judgment), n, round(100 * len(judgment) / n)))
    L.append("")
    L.append("-" * 72)
    L.append("STILL UNCOVERED, AND MECHANICAL — this is the buildable list")
    L.append("-" * 72)
    for e in uncovered:
        L.append("  %-9s [%s] %s" % (e["id"], e["settled_by"], e["what"]))
    L.append("")
    L.append("-" * 72)
    L.append("INTRODUCED BY AN EARLIER CORRECTION — %d of %d (%d%%)"
             % (len(introduced), n, round(100 * len(introduced) / n)))
    L.append("-" * 72)
    for e in introduced:
        L.append("  %-9s came in with %-10s %s" % (e["id"], e["introduced_by"], e["what"]))
    L.append("")
    L.append("  Corrections are the least-checked text on this page and the")
    L.append("  likeliest place for the next error. That is measurable, it is")
    L.append("  %d%% of everything found, and nothing currently gates a" % round(100 * len(introduced) / n))
    L.append("  correction harder than it gates the prose it corrects.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.json:
        print(json.dumps(ERRORS, indent=2))
    else:
        print(report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
