#!/usr/bin/env python3
"""B15 — a universal negative, searched against our own library.

GAP-001, and the failure that raised it.

Issue one said "The framing was never explained to readers." S019 — KOL Pulse,
sitting in our own library, already bound to other sentences on the same page —
says:

    P=0.0266 (formal hypothesis testing of RFS, overall one-sided alpha=0.10,
    performed at primary analysis)

A document we held, had read, and had bound other claims to, falsified the
sentence. Four passes of our own checks walked past it and an outside reader
found it in one, because every check we owned asked whether a span the page
CITES is present in the document it cites. None asked the opposite question: is
there something in the library that CONTRADICTS a sentence the page asserts?

That question only has teeth for one class of sentence — the universal negative,
"nobody said X", "no trial reported Y", "the only Z in the programme" — because
those are the only claims a single held document can falsify outright.

WHAT THIS DOES NOT DO
---------------------
It does not decide the sentence is false. It cannot: whether a hit really
contradicts the claim needs a person to read it, and a check asserting
otherwise would be making exactly the claim R1 forbids of this layer. It
returns CANDIDATES, and it blocks until each has been read and dispositioned.

WHY THE TRIGGER IS A DECLARATION AND NOT A LIST OF WORDS
--------------------------------------------------------
The obvious build is to detect negation words and search for "the thing". Four
allow-lists in this repository were built from the vocabulary we happened to
meet and all four were wrong within a day. So the ROW says what it claims is
absent, in the same way it already names a field path for a locator and a
subject for B14:

    "negative_over": {"class": "efficacy_figure",
                      "subject": "INTerpath-001",
                      "claim": "none"}

A quantifier B6 cannot map, with no disposition and no declaration, is a
blocking finding whose remedy is two fields. A class not in the registry below
is REFUSED rather than passed, because a claim we cannot express is a claim we
cannot check.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store    # noqa: E402
import spancheck as SC          # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# The classes a negative can be made about. Each is a NOTATION, the same
# discipline as modelbind.dimension: what a figure of this kind looks like on
# the page of a journal, not a list of the words we have seen used about one.
CLASSES = {
    "efficacy_figure": re.compile(
        r"\b(?:HR\s*[=:]|hazard ratio|95%\s*CI|p\s*[=<>]\s*0?\.\d+|"
        r"one-sided p|two-sided p)", re.I),
    "os_estimate": re.compile(
        r"\b(?:overall survival|\bOS\b)\b.{0,120}?"
        r"(?:HR\s*[=:]|hazard ratio|95%\s*CI|\d+(?:\.\d+)?%)", re.I | re.S),
    "alpha_statement": re.compile(
        r"\b(?:one-sided|two-sided|1-sided|2-sided)?\s*alpha\s*(?:of|=|:)\s*0?\.\d+",
        re.I),
}
CLAIMS = ("none", "one")

# A REPORT OF A FIGURE ATTACHES A VALUE TO IT. A DENIAL DOES NOT.
#
# Morning Glory's "No hazard ratios, confidence intervals or p-values for RFS or
# DMFS have been released" matches the efficacy pattern and is our own claim in
# someone else's words. Counting it as a counterexample would be the check
# contradicting a sentence with its agreement.
#
# THE FIRST VERSION OF THIS FILTER READ VOCABULARY — a list of negation words —
# and the test written to watch it caught it immediately: "Although the
# companies did not comment, the trial reported a hazard ratio of 0.55" was
# dropped, because it contains "did not". A positive report, swallowed by a word
# list, which is how four allow-lists in this repository went wrong.
#
# So the test is structural instead, and there is no vocabulary left in it: the
# class token must have a VALUE within a short window after it. "hazard ratio of
# 0.55" reports one; "hazard ratios ... have been released" does not.
#
# The number must also not be part of a name. "The hazard ratio for
# INTerpath-001 has been the subject of comment" carries no figure, and the
# first version counted the 001 in the trial's name as one — the same defect as
# every other figure check in this repository has had, in a fifth place.
VALUE = re.compile(r"(?<![A-Za-z0-9.\-])\d+(?:[.,]\d+)?")
# TWENTY-FIVE CHARACTERS, chosen by running the nine sentences in
# test_the_value_window_separates_a_report_from_a_denial and picking the widest
# window that gets all nine right. At 60 it kept three denials, because "hazard
# ratios have not been disclosed, those 157-patient figures" has a number in it
# forty characters later that belongs to a different claim.
VALUE_WINDOW = 25


def reports_a_value(sentence: str, at: int) -> bool:
    return bool(VALUE.search(sentence[at:at + VALUE_WINDOW]))


def declared(row: dict) -> dict | None:
    d = row.get("negative_over")
    if not isinstance(d, dict):
        return None
    if d.get("class") not in CLASSES or d.get("claim") not in CLAIMS:
        return None
    return d


def _sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text)


def search(slug: str, decl: dict) -> tuple[list[dict], dict]:
    """(candidates, counts). A candidate is a sentence a person has to read."""
    pat = CLASSES[decl["class"]]
    subject = (decl.get("subject") or "").strip()
    srcs = {s.get("id"): s for s in store.sources(slug)}
    names = {n for s in srcs.values() for n in (s.get("also_called") or [])
             if len(n) > 3}
    subj_names = {subject} | {n for s in srcs.values()
                              if (s.get("about") or "") == subject
                              for n in (s.get("also_called") or []) if len(n) > 3}
    subj = re.compile("|".join(re.escape(n) for n in subj_names if n), re.I) \
        if subject else None
    others = [n for n in names if n not in subj_names]
    other = re.compile("|".join(re.escape(n) for n in others), re.I) if others else None

    counts = {"searched": 0, "hits": 0, "reference": 0, "other_trial": 0,
              "no_value": 0}
    out = []
    for sid in sorted(store.held(slug)):
        src = srcs.get(sid) or {}
        text = SC._norm(SC._text(slug, sid) or "")
        sents = _sentences(text)
        counts["searched"] += len(sents)
        for s in sents:
            m = pat.search(s)
            if not m:
                continue
            counts["hits"] += 1
            # A statistics reference explains what a hazard ratio IS. It reports
            # no trial's result and cannot contradict a claim about one.
            if src.get("type") == "reference":
                counts["reference"] += 1
                continue
            if subj is not None:
                names_subject = bool(subj.search(s))
                if not names_subject:
                    if other and other.search(s):
                        counts["other_trial"] += 1
                        continue
                    about = (src.get("about") or "")
                    if about and about != subject:
                        counts["other_trial"] += 1
                        continue
            if not reports_a_value(s, m.end()):
                counts["no_value"] += 1
                continue
            out.append({"source_id": sid, "quote": s[:400]})
    return out, counts


def unread(row: dict, cands: list[dict]) -> list[dict]:
    """Candidates nobody has recorded a reading of."""
    decl = row.get("negative_over") or {}
    seen = set()
    for r in (decl.get("read") or []):
        if (r.get("by") or "").strip() and (r.get("why_not") or "").strip():
            seen.add((r.get("source_id"), SC._norm(r.get("quote") or "")[:120]))
    return [c for c in cands
            if (c["source_id"], SC._norm(c["quote"])[:120]) not in seen]


def rows_needing_this(slug: str) -> list[tuple[str, dict]]:
    """Every on-page row whose quantifier B6 could not map and nobody disposed."""
    import bindings as B
    doc = B.load(slug)
    out = []
    for sha, row in (doc.get("bindings") or {}).items():
        if not row.get("on_page"):
            continue
        if any(f.get("check") == "B6" for f in (row.get("check_flags") or [])):
            out.append((sha, row))
    return out


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    todo = rows_needing_this(slug)
    if not todo:
        return [("universal negatives searched against the library", OK,
                 "no unmapped quantifier is waiting on one")]
    undeclared, blocking, done = [], [], 0
    for sha, row in todo:
        decl = declared(row)
        if decl is None:
            undeclared.append("%s: %s" % (sha[:8], row["sentence"][:70]))
            continue
        cands, counts = search(slug, decl)
        left = unread(row, cands)
        if left:
            blocking.append("%s: %d of %d candidate(s) unread, e.g. [%s] %s"
                            % (sha[:8], len(left), len(cands),
                               left[0]["source_id"], left[0]["quote"][:110]))
        else:
            done += 1
    rows = []
    rows.append(("universal negatives declared",
                 OK if not undeclared else BAD,
                 "every unmapped quantifier says what it claims is absent"
                 if not undeclared else
                 "%d quantifier(s) with no disposition and no negative_over — a "
                 "claim nobody expressed is a claim nothing can check: %s"
                 % (len(undeclared), " || ".join(undeclared[:3]))))
    rows.append(("universal negatives searched against the library",
                 OK if not blocking else BAD,
                 "%d searched, every candidate read" % done if not blocking else
                 "%d negative(s) have candidates nobody has read: %s"
                 % (len(blocking), " || ".join(blocking[:2]))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--row", help="one row's sha, to list its candidates")
    a = ap.parse_args()
    if a.row:
        import bindings as B
        row = (B.load(a.slug).get("bindings") or {}).get(a.row)
        if not row:
            print("no such row"); return 2
        decl = declared(row)
        if decl is None:
            print("row declares no usable negative_over"); return 2
        cands, counts = search(a.slug, decl)
        print("\n  %s over %s, claim=%s" % (decl["class"], decl.get("subject")
                                            or "the whole library", decl["claim"]))
        print("  searched %(searched)d sentence(s); %(hits)d carried the class" % counts)
        for k in ("reference", "other_trial", "no_value"):
            print("    dropped, %-12s %d" % (k, counts[k]))
        left = unread(row, cands)
        print("\n  %d candidate(s), %d unread\n" % (len(cands), len(left)))
        for c in cands:
            mark = " " if c not in left else "*"
            print("  %s [%s] %s\n" % (mark, c["source_id"], c["quote"][:200]))
        return 0
    for name, state, detail in preflight_rows(a.slug):
        print("  %-8s %-52s %s" % (state, name, detail[:150]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
