#!/usr/bin/env python3
"""B15 -- A FINDING IS SETTLED BY A DOCUMENT, NEVER BY THE FINDING.

WHY THIS EXISTS
---------------
MEL-11, the error of 2026-09-01: a check reported three figures as being "in
nothing we hold", and the correction notice published on a live page said they
"came from no document". Two were real. The check had qualified its verdict
precisely and printed, under every run, that a miss is not a falsehood. The
prose written about it did not.

The rule that would have stopped it was already adopted -- "WRITE THE CORRECTION
FROM THE SOURCE RECORD, NOT FROM THE FINDING", error_taxonomy.py, 2026-09-01 --
and it gated nothing, so it did not stop anything.

It is not a rare failure. Every one of these is the same shape:

  2026-08-31  a correction written from a gate finding withdrew a true sentence
              the paper actually contains (CORR-13)
  2026-08-31  "Jacot and colleagues" published from gate output; the paper is
              by Tanguy et al.
  2026-09-01  a review file here claimed a blind spot in B9 that B9 already
              reports, on one binder's say-so
  2026-09-01  an ipilimumab result nearly written into the page from the
              counterexample hunt's citation, for a paper we cannot open
  2026-09-01  the correction notice above -- the only one that reached a reader
  2026-09-02  THE GATE DID IT TOO: it reported the page's account of MLQ News
              as "contradicted" because no MLQ News article appeared in its
              search results. We hold that document. It says, verbatim, what
              the page says it says.

The last one matters most. This is not a failure of one writer being careless
with one check's output. Roles do it to each other, and a role's finding reads
like evidence because it arrives in the same shape as evidence.

THE RULE
--------
A finding may be closed only by a QUOTATION FROM A DOCUMENT WE HOLD, and the
quotation is checked -- mechanically, here -- against the bytes.

    accepted   the finding is right and the page changed. Name the source and
               the sentence in it that shows so.
    rejected   the finding is wrong. Name the source and the sentence that
               shows so. "The check could not reach it" is not a rejection;
               "we hold it and it reads as follows" is.
    judgement  neither the finding nor its rebuttal is a matter of fact. Say
               what the question is and who decided. No quotation required, and
               the count of these is printed, because a bucket with no evidence
               requirement is the one that will silently absorb everything.

WHAT THIS FORECLOSES, BY CONSTRUCTION
-------------------------------------
You cannot cite a document for an absence. There is no sentence in any paper
reading "68.8% appears nowhere". So a claim of that shape can never be settled
under this rule, and therefore can never be published as settled -- which is
exactly the outcome wanted, arrived at without anybody having to remember the
lesson. Absence about our own library is a different claim, it is B13's, and it
is recorded in deletions.json where the search itself is the evidence.

WHAT IT DOES NOT DO
-------------------
It does not check that the quotation SUPPORTS the decision -- only that it
exists, in the document named, as printed. B2's limit, one level up: presence is
not warrant. A person still has to read it. What they can no longer do is close
a finding with prose.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_store as store    # noqa: E402
import spancheck as SC          # noqa: E402
import quotations as Q          # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"
DECISIONS = ("accepted", "rejected", "judgement")
SETTLED_BY_QUOTE = ("accepted", "rejected")


def path(slug: str) -> Path:
    return store.case_dir(slug) / "gate-findings.json"


def load(slug: str) -> dict:
    p = path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"_what_this_is":
            "Every blocking finding a gate run made, and the DOCUMENT that "
            "settled it. See findings.py: a finding is not evidence, and the "
            "quotation below is checked against the bytes.",
            "findings": []}


def save(slug: str, doc: dict) -> None:
    path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def open_findings(report: dict) -> list[dict]:
    """Everything in a gate report that blocks: a verdict that is not VERIFIED
    or INTERNAL, a serious objection, a serious inference, a serious coverage
    contradiction."""
    out = []
    for vid, v in (report.get("verdicts") or {}).items():
        if v.get("verdict") in ("VERIFIED", "INTERNAL"):
            continue
        out.append({"id": vid, "kind": "claim", "verdict": v.get("verdict"),
                    "what": (v.get("found_value") or "")[:400]})
    for i, o in enumerate(report.get("objections") or [], 1):
        if (o.get("severity") or "").upper() == "SERIOUS":
            out.append({"id": "obj-%d" % i, "kind": "fairness",
                        "verdict": o.get("class"),
                        "what": (o.get("objection") or "")[:400]})
    for i, f in enumerate(report.get("inferences") or [], 1):
        if (f.get("severity") or "").upper() == "SERIOUS":
            out.append({"id": "inf-%d" % i, "kind": "inference",
                        "verdict": f.get("class"),
                        "what": (f.get("problem") or "")[:400]})
    cov = (report.get("coverage") or {}).get("contradictions") or []
    for i, c in enumerate(cov, 1):
        if (c.get("severity") or "").upper() == "SERIOUS":
            out.append({"id": "cov-%d" % i, "kind": "coverage",
                        "verdict": "contradicted",
                        "what": (c.get("but") or c.get("quote") or "")[:400]})
    return out


def quote_is_in_source(slug: str, sid: str, quote: str) -> tuple[bool, str]:
    if sid not in store.held(slug):
        return False, "%s is not in the library" % sid
    text = SC._text(slug, sid) or ""
    if Q.norm(quote) in Q.norm(SC._norm(text)):
        return True, "found in %s" % sid
    return False, "not in %s as printed" % sid


def check(slug: str, report: dict) -> list[tuple[str, str, str]]:
    opens = open_findings(report)
    if not opens:
        return [("gate findings settled", OK, "the last run left nothing open")]
    doc = load(slug)
    have = {f.get("id"): f for f in (doc.get("findings") or [])}
    missing, unsettled, unverified, judged = [], [], [], []
    for f in opens:
        r = have.get(f["id"])
        if not r:
            missing.append("%s (%s)" % (f["id"], f["kind"]))
            continue
        d = r.get("decision")
        if d not in DECISIONS:
            unsettled.append("%s: decision %r is not one of %s"
                             % (f["id"], d, ", ".join(DECISIONS)))
            continue
        if d == "judgement":
            judged.append(f["id"])
            if not (r.get("why") or "").strip() or not (r.get("by") or "").strip():
                unsettled.append("%s: a judgement needs a reason and a name"
                                 % f["id"])
            continue
        sid, quote = r.get("source_id"), r.get("quote") or ""
        if not sid or not quote:
            unsettled.append("%s: %r must name a source AND quote the sentence "
                             "in it that settles this" % (f["id"], d))
            continue
        ok, why = quote_is_in_source(slug, sid, quote)
        if not ok:
            unverified.append("%s: %s" % (f["id"], why))
    rows = [("gate findings settled", OK if not missing else BAD,
             "%d open finding(s), each with a decision" % len(opens)
             if not missing else
             "%d finding(s) from the last run have no decision: %s"
             % (len(missing), ", ".join(missing[:6])))]
    rows.append(("findings settled by a document", OK if not unsettled else BAD,
                 "every accepted or rejected finding names a source and a "
                 "quotation" if not unsettled else
                 "%d unsettled: %s" % (len(unsettled), " || ".join(unsettled[:3]))))
    rows.append(("those quotations are in the bytes",
                 OK if not unverified else BAD,
                 "every quotation used to settle a finding is in the document "
                 "named" if not unverified else
                 "%d quotation(s) are not: %s"
                 % (len(unverified), " || ".join(unverified[:3]))))
    if judged:
        rows.append(("findings closed as judgement", WARN,
                     "%d of %d closed without a document, by name: %s — the "
                     "bucket with no evidence requirement is the one to watch"
                     % (len(judged), len(opens), ", ".join(judged[:6]))))
    return rows


def scan(slug: str, report: dict) -> dict:
    doc = load(slug)
    have = {f.get("id") for f in (doc.get("findings") or [])}
    for f in open_findings(report):
        if f["id"] in have:
            continue
        doc["findings"].append({
            "id": f["id"], "kind": f["kind"], "gate_verdict": f["verdict"],
            "gate_said": f["what"],
            "decision": "", "source_id": "", "quote": "", "why": "",
            "by": "", "on": date.today().isoformat(),
            "_fill_in": "decision: %s. accepted/rejected need source_id AND a "
                        "quote that is in that document." % ", ".join(DECISIONS),
        })
    save(slug, doc)
    return doc


def preflight_rows(slug: str, report_path: Path) -> list[tuple[str, str, str]]:
    if not report_path.exists():
        return [("gate findings settled", WARN, "no gate report to read")]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [("gate findings settled", WARN, "unreadable report: %s" % exc)]
    return check(slug, report)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--report", required=True)
    ap.add_argument("--scan", action="store_true")
    a = ap.parse_args()
    report = json.loads(Path(a.report).read_text(encoding="utf-8"))
    if a.scan:
        doc = scan(a.slug, report)
        print("\n  %d finding(s) recorded in %s\n"
              % (len(doc["findings"]), path(a.slug)))
        return 0
    print()
    for label, st, detail in check(a.slug, report):
        print("  %-7s %-34s %s" % ({OK: "ok", BAD: "STOP", WARN: "warn"}[st],
                                   label, detail))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
