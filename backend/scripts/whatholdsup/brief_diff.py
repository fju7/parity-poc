#!/usr/bin/env python3
"""Diff a draft page against the working brief it was written from.

WHY THIS EXISTS
---------------
On 2026-08-28 the CDK4/6 draft went to the fact-check gate missing the one fact
its whole argument turned on: which overall-survival results were statistically
significant. The gate found it, four times over, at a cost of $3.96 for the run.

The fact had not been missed in research. It was in the working brief, in the
brief's own version of the same table, in a fifth column headed "OS significant"
-- MONARCH 3 no, MONALEESA-2 yes. The page has four columns. It was lost in
transcription, between two documents in the same repository, and nothing
compared them.

No role in the gate can catch that. The gate reads the page; it has never been
shown the brief. A fact we already had, written down, in the same directory, was
rediscovered by a language model doing web searches. This script is the check
that should have run first, and it costs nothing.

WHAT IT DOES, AND WHAT IT DOES NOT
----------------------------------
It reports three things:

  columns    a heading in one document's tables and not the other's
  dropped    a figure in the brief that appears nowhere on the page
  invented   a figure on the page that appears nowhere in the brief

None of the three is automatically an error. A brief is a working document: it
holds figures considered and discarded, and the page is entitled to be shorter
than it. A page may carry a figure the brief recorded in prose rather than in a
table. The output is a list of questions, not a list of faults.

The one thing it will not do is let a figure onto the page that nobody wrote
down first. That direction -- "invented" -- is the one to read closely, because
a number with no provenance in the brief has no provenance anywhere: the brief
is where provenance is recorded.

It compares figures, not meaning. It cannot tell you a figure is wrong. It tells
you the two documents disagree about what is in them.
"""

from __future__ import annotations

import argparse
import html as _html
import re
import sys
from pathlib import Path

# A figure is a run of digits that may carry thousands separators, a decimal
# part, a leading sign and a trailing percent. Years and small integers are
# excluded below rather than here, so that the pattern stays readable.
FIGURE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?%?")

# Figures too common to be evidence of anything. A page and a brief will share
# these by coincidence, and their absence proves nothing.
def _is_noise(tok: str) -> bool:
    bare = tok.rstrip("%").replace(",", "").lstrip("+-")
    if "." in bare:
        return False                      # any decimal is worth comparing
    if tok.endswith("%"):
        return False                      # any percentage is worth comparing
    try:
        n = int(bare)
    except ValueError:
        return True
    if 1900 <= n <= 2100:
        return True                       # a year
    return n < 10                         # single digits: counts, list markers


def figures(text: str) -> set[str]:
    """Every figure in the text, normalised so 4,415 and 4415 are one thing."""
    out = set()
    for m in FIGURE.finditer(text):
        tok = m.group(0)
        if _is_noise(tok):
            continue
        out.add(tok.replace(",", "").lstrip("+"))
    return out


def visible_prose(raw: str) -> str:
    """The page's text, with script, style, attributes and markup removed.

    Attributes are stripped rather than kept because a chart drawn in CSS puts
    its geometry in style="left:52%; width:26.67%" -- numbers that are the
    picture, not the evidence. The first version of this script reported the
    axis ticks 0.5, 1.0 and 1.5 as figures with no provenance in the brief,
    which is the kind of noise that teaches people to stop reading a check.
    """
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return _html.unescape(raw)


def _rounds_from(page_tok: str, brief_toks: set[str]) -> bool:
    """True if some brief figure rounds to this page figure.

    A page is entitled to round what the brief records: the brief holds
    0.568 and 0.712 because that is what the papers say, and the page prints
    0.57 and 0.71 because that is how a hazard ratio is written. Reporting
    those as figures with no provenance is false -- their provenance is the
    line above them -- and a check that cries wolf on every rounded number
    will not be run twice.

    Only rounding is accepted, and only downward in precision. A page figure
    with MORE decimal places than anything in the brief is still flagged:
    that is the direction that invents precision, which is the mistake this
    issue actually made.
    """
    bare = page_tok.rstrip("%")
    if "." not in bare:
        return False
    places = len(bare.split(".")[1])
    try:
        want = float(bare)
    except ValueError:
        return False
    pct = page_tok.endswith("%")
    for b in brief_toks:
        if b.endswith("%") != pct:
            continue
        try:
            v = float(b.rstrip("%"))
        except ValueError:
            continue
        if round(v, places) == want and len(b.rstrip("%").split(".")[-1]) >= places:
            return True
    return False


def md_tables(text: str) -> list[list[list[str]]]:
    """Markdown pipe tables, as lists of rows of cells."""
    tables, rows = [], []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            # the |---|---| separator row carries no content
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(cells)
        elif rows:
            tables.append(rows); rows = []
    if rows:
        tables.append(rows)
    return tables


def html_tables(raw: str) -> list[list[list[str]]]:
    """HTML tables, as lists of rows of cells, markup stripped from each cell."""
    tables = []
    for tbl in re.findall(r"(?is)<table\b.*?</table>", raw):
        rows = []
        for tr in re.findall(r"(?is)<tr\b.*?</tr>", tbl):
            cells = [" ".join(visible_prose(c).split())
                     for c in re.findall(r"(?is)<t[hd]\b.*?</t[hd]>", tr)]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def _key(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()


def headings(tables: list[list[list[str]]]) -> set[str]:
    out = set()
    for t in tables:
        if not t:
            continue
        for h in t[0]:
            k = _key(h)
            if k:
                out.add(k)
    return out


def report(brief: Path, page: Path) -> int:
    btext = brief.read_text(encoding="utf-8")
    praw = page.read_text(encoding="utf-8")
    ptext = visible_prose(praw)

    bt, pt = md_tables(btext), html_tables(praw)
    bh, ph = headings(bt), headings(pt)

    # A heading matches if either name contains the other: "os significant"
    # against "overall survival" should not be called a match, but "os" against
    # "os significant" should.
    def matched(h: str, others: set[str]) -> bool:
        return any(h == o or h in o.split() or o in h.split() or
                   (len(h) > 3 and h in o) or (len(o) > 3 and o in h)
                   for o in others)

    lost_cols = sorted(h for h in bh if not matched(h, ph))
    new_cols = sorted(h for h in ph if not matched(h, bh))

    bf, pf = figures(btext), figures(ptext)
    dropped = sorted(bf - pf, key=lambda x: (len(x), x))
    unmatched = pf - bf
    rounded = {t for t in unmatched if _rounds_from(t, bf)}
    invented = sorted(unmatched - rounded, key=lambda x: (len(x), x))

    W = 72
    print("=" * W)
    print("BRIEF-TO-PAGE DIFF")
    print("  brief : %s  (%d table(s))" % (brief, len(bt)))
    print("  page  : %s  (%d table(s))" % (page, len(pt)))
    print("=" * W)

    def block(title, items, note):
        print("\n%s  %d" % (title, len(items)))
        if not items:
            print("  none")
            return
        print("  " + note)
        for i in items:
            print("    %s" % i)

    block("COLUMNS IN THE BRIEF AND NOT ON THE PAGE",
          lost_cols,
          "A column the research produced and the page does not carry.")
    block("COLUMNS ON THE PAGE AND NOT IN THE BRIEF",
          new_cols,
          "Usually presentation. Worth a glance.")
    block("FIGURES IN THE BRIEF AND NOT ON THE PAGE",
          dropped,
          "Expected: a brief holds more than a page. Read for anything load-bearing.")
    block("FIGURES ON THE PAGE AND NOT IN THE BRIEF",
          invented,
          "Read every one. A figure the brief never recorded has no provenance.")
    if rounded:
        print("\n  (%d page figure(s) matched a brief figure by rounding, not listed: %s)"
              % (len(rounded), ", ".join(sorted(rounded))))

    flagged = len(lost_cols) + len(invented)
    print("\n" + "-" * W)
    if flagged:
        print("%d item(s) to answer before the gate runs." % flagged)
        print("Answer them in the brief, not in your head: the brief is the record.")
    else:
        print("Nothing to answer. Every page figure is in the brief and no")
        print("brief column was dropped.")
    return 1 if flagged else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Diff a draft page against the working brief it came from.")
    ap.add_argument("brief", help="the working brief (markdown)")
    ap.add_argument("page", help="the draft page (HTML)")
    args = ap.parse_args()
    b, p = Path(args.brief), Path(args.page)
    for f in (b, p):
        if not f.exists():
            print("[ERROR] not found: %s" % f)
            return 2
    return report(b, p)


if __name__ == "__main__":
    sys.exit(main())
