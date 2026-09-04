#!/usr/bin/env python3
"""B18 — the correction history is claims, and nothing was reading it.

WHY THIS EXISTS
---------------
`bindings.page_sentences` strips <nav>, <header>, <footer> and <aside> before
it does anything. The change log lives in <footer id="updates">. So on the
melanoma page, 154 sentences -- a fifth of the prose, 26 of them carrying
figures -- were invisible to rule 1, rule 2, the span checks, the scope checks
and the binder entirely.

The one part of the page where we tell readers what we got wrong was the only
part with no evidentiary control at all. That is not a coincidence in what went
wrong afterwards; it is the explanation.

WHAT IT COST, TWICE
-------------------
2 September: a correction notice said three figures "came from no document" and
that one "exists nowhere". The check behind it had reported only that they were
in nothing WE HOLD, and said so in its own output. The entry overstated it into
an accusation of invention. Recorded at the time as "the correction notice was
worse than the error".

3-4 September: the scorecard printed 3.4 over a working of 3.35. We recorded
that as a discrepancy, wrote that the figure had been "out by 0.05 against its
own working, for eight days", and corrected it. **3.35 rounds to 3.4.** There
was no discrepancy. We had accused ourselves, in the correction history, of an
arithmetic error we did not make -- and the correction history is exactly where
a reader goes to decide whether we can be trusted about our own mistakes.

Both are the same shape: a check reported precisely, and the sentence written
around it overstated. Neither could be caught, because nothing read that region.

WHAT IT CHECKS
--------------
  C1  Every figure in the change log traces somewhere: a document we hold, the
      body of the page (a restatement of something already checked), or a
      recorded exclusion. Same standard as the body, applied where corrections
      live.

  C2  A sentence that asserts two numbers disagree must be right that they do.
      If one is the correct rounding of the other at the precision printed,
      there is no disagreement, and saying there is one is a false statement
      about our own work. This is the check that would have caught 3.4 / 3.35
      the moment it was written.

C2 is deliberately narrow. It does not ask whether a correction is well
judged -- no check can. It asks whether an arithmetic claim we make about our
own numbers is true, which is the one thing here that is decidable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b13                        # noqa: E402
import bindings as B              # noqa: E402
import source_ledger as ledger    # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

CHANGELOG = re.compile(r"<footer\b[^>]*>(.*?)</footer>", re.S | re.I)

# "did not match", "out by", "disagreed with", "discrepancy", "differs from".
# Only forms that assert a NUMERIC disagreement; "changed from x to y" is a
# correction describing itself and asserts no mismatch.
MISMATCH = re.compile(
    r"\b(did not match|does not match|do not match|didn.t match|"
    r"out by|off by|disagree[sd]?\b|discrepanc(?:y|ies)|"
    r"differs? from|inconsistent with|does not agree|did not agree)\b", re.I)

NUM = re.compile(r"(?<![A-Za-z0-9._-])(\d+\.\d+|\d+)(?![0-9]*[%A-Za-z])")


def changelog_html(slug: str) -> str:
    m = CHANGELOG.search(B._page_html(slug))
    return m.group(1) if m else ""


def paragraphs(slug: str) -> list[str]:
    html = changelog_html(slug)
    if not html:
        return []
    return [" ".join(ledger.plain(m).split())
            for m in re.findall(r"<p\b[^>]*>.*?</p>", html, re.S | re.I)]


def sentences(slug: str) -> list[str]:
    html = changelog_html(slug)
    if not html:
        return []
    return [" ".join(s.split()) for s in ledger.sentences(ledger.plain(html))]


def sentences_in_context(slug: str) -> list[tuple[str, str]]:
    """(sentence, the paragraph it sits in).

    A claim of the form "out by 0.05 against its own working" names ONE number
    and leaves the two it compares to the paragraph around it -- which is how
    the real instance of this error was written, and why a sentence-local check
    passed it. The referents of a correction are local; the paragraph is the
    right window.
    """
    out = []
    for para in paragraphs(slug):
        for sent in ledger.sentences(para):
            out.append((" ".join(sent.split()), para))
    return out


def body_figures(slug: str) -> set[str]:
    """Figures that appear in the part of the page the binder does read."""
    out = set()
    for s in B.page_sentences(slug):
        out |= {m.group(1) for m in NUM.finditer(s)}
    return out


# ---------------------------------------------------------------------------
# C2 — an asserted disagreement between two numbers must be real
# ---------------------------------------------------------------------------

def _rounds_to(a: str, b: str) -> bool:
    """True if a is b rounded to a's printed precision, or the reverse."""
    for x, y in ((a, b), (b, a)):
        try:
            dx, dy = Decimal(x), Decimal(y)
        except InvalidOperation:
            return False
        places = -dx.as_tuple().exponent
        try:
            if dy.quantize(Decimal(1).scaleb(-places)) == dx:
                return True
        except InvalidOperation:
            continue
    return False


# A sentence that SHOWS the rounding relation is discussing it, not asserting a
# bare mismatch. The first version of this check flagged the very sentence that
# retracts the 3.4/3.35 claim -- "the separate claim that its printed 3.4
# disagreed with its own working of 3.35 was itself wrong, since 3.35 rounds to
# 3.4" -- because it contains "disagreed" and the two numbers.
#
# The fix is NOT a list of retraction words. Lists built from the vocabulary
# that happened to appear are wrong here every time this project has tried one.
# The rule is the one the rest of the repository already runs on: a claim that
# shows its working is not an unchecked claim. If the sentence states the
# rounding, the reader can see the arithmetic and judge it.
SHOWS_ROUNDING = re.compile(r"\broun(?:d|ded|ds|ding)\b", re.I)


def false_mismatches(slug: str) -> list[dict]:
    out = []
    for s, para in sentences_in_context(slug):
        if not MISMATCH.search(s):
            continue
        # the paragraph, not just the sentence: if the paragraph shows the
        # rounding, the reader can see the arithmetic wherever it is stated.
        if SHOWS_ROUNDING.search(para):
            continue
        # UNION, not fallback. The real instance named its own number -- "out by
        # 0.05" -- so a fallback that only fired on a numberless sentence never
        # reached the 3.4 and 3.35 it was comparing. The sentence asserts the
        # mismatch; the paragraph supplies what it is between.
        nums = list(dict.fromkeys(
            [m.group(1) for m in NUM.finditer(s)]
            + [m.group(1) for m in NUM.finditer(para)]))
        # the pairs a reader would take as the two sides of the claim
        pairs = {(a, b) for i, a in enumerate(nums) for b in nums[i + 1:]
                 if a != b}
        bad = [(a, b) for a, b in pairs if _rounds_to(a, b)]
        if bad:
            out.append({"sentence": s, "pairs": bad,
                        "why": ("%s is %s rounded to the precision printed, so the "
                                "sentence asserts a disagreement that does not exist"
                                % (bad[0][0], bad[0][1]))})
    return out


# ---------------------------------------------------------------------------
# C1 — every figure in the change log traces somewhere
# ---------------------------------------------------------------------------

def untraceable(slug: str) -> list[dict]:
    body = body_figures(slug)
    excluded = {r.get("figure") for r in b13.load_exclusions(slug)}
    out = []
    for s in sentences(slug):
        for m in b13.FIGURE.finditer(ledger.plain(s)):
            fig = m.group(1).replace(",", "")
            if b13._is_year(fig) or fig in body or fig in excluded:
                continue
            if b13.where(fig, slug):
                continue
            out.append({"figure": fig, "sentence": s})
    return out


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    sents = sentences(slug)
    if not sents:
        return [("the correction history is checked", BAD,
                 "no <footer> change log found on the page — this check has "
                 "nothing to read, and an unrun check is not a pass")]

    fm = false_mismatches(slug)
    rows = [("corrections that assert a false disagreement",
             OK if not fm else BAD,
             "no correction claims two numbers disagree when they do not"
             if not fm else
             "%d correction(s) assert a disagreement that is not there: %s"
             % (len(fm), " || ".join(
                 "%s (%s)" % (f["sentence"][:110], f["why"]) for f in fm[:2])))]

    ut = untraceable(slug)
    rows.append(("figures in the correction history",
                 OK if not ut else BAD,
                 "all %d sentence(s) of change log: every figure is in a held "
                 "document, on the page, or excluded with a reason" % len(sents)
                 if not ut else
                 "%d figure(s) in the change log are in no held document, "
                 "nowhere else on the page, and carry no exclusion: %s"
                 % (len(ut), " || ".join(
                     "%s in '%s'" % (u["figure"], u["sentence"][:80])
                     for u in ut[:3]))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    a = ap.parse_args()
    bad = 0
    print()
    for name, st, detail in preflight_rows(a.slug):
        print("  %-8s %s\n           %s\n" % (st, name, detail))
        bad += st == BAD
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
