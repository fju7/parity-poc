#!/usr/bin/env python3
"""Generate /issues — one row per issue, with its subject in plain words.

WHY THIS EXISTS
---------------
The navigation read `Issue one | Issue two | Issue three`. That breaks at about
five, and it was never what a reader wants: nobody looks for "issue seven", they
look for *the melanoma one*.

**Titles carry character; subjects carry navigation.** *The Melanoma Result*,
*The Category Difference* and *What Happens to the Experts First* are good titles
and they are allusive, and an index of allusive titles is unnavigable. So each
row carries both, in separate columns, plus the question the issue answers.

THE SUBJECT COLUMN WITHHOLDS THE FINDING, DELIBERATELY
------------------------------------------------------
A first draft of issue two's subject read "how a guideline's evidence grades get
misread". That asserts the misreading -- which is the page's *finding* -- in the
column whose job is to let a reader decide whether to care before being told what
to think. It now reads "a guideline that grades one drug above two similar ones",
which is what the page is about and not what it concludes. The question column
carries the rest.

THE FOUR FACTS ARE DERIVED
--------------------------
Same four as the homepage, from `issue_facts`: published and last revised;
corrections including none; outside review, distinguishing a pre-publication read
from a post-publication one; and when the sources were last checked for errata.
Nothing on this page is typed except the titles, subjects and questions.

NO CATEGORIES. Three issues is too few to know what the categories are, and a
taxonomy fitted to the first three will fight the next ten. Recorded as a decision
to be made at eight issues -- see docs/whatholdsup-open-gaps.md.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import index_dates as I                                   # noqa: E402
import issue_facts                                        # noqa: E402

OUT = I.ROOT / "site" / "whatholdsup" / "issues.html"

# Titles are the pages' own. Subjects and questions are editorial, approved by
# the operator on 2026-09-10, and live here rather than in each page because an
# index that repeats a page's own words is a copy, not an index.
# The copy lives in issue_facts.COPY, in one place, because the homepage needs
# the same subjects and questions and two copies would drift.
ISSUES = [(slug,) + issue_facts.COPY[slug]
          for slug in ("melanoma", "cdk46", "deskilling")]

NAV = """<nav class="sitenav">
  <a class="brand" href="/">What Holds Up</a>
  <a href="/what-this-is">What this is</a>
  <a href="/the-rubric">The rubric</a>
  <a href="/issues">Issues</a>
  <a href="/who-pays-for-this">Who pays for this</a>
</nav>"""


def facts_line(slug: str) -> str:
    f = issue_facts.facts(slug)
    bits = []
    bits.append("Published %s" % I.fmt(f["published"]) if f["published"] else "Not published")
    bits.append("revised %s" % I.fmt(f["revised"]) if f["revised"] else "not revised")
    # NO NESTED ANCHOR. The card is itself an <a>, so an <a> inside it is
    # invalid HTML: a browser closes the outer link at the inner one, and every
    # fact after "14 corrections" falls outside the clickable card. The first
    # version of this line did exactly that and it was served for twenty
    # minutes. The count is text; the card already links to the issue.
    n = f["corrections"]
    bits.append(("1 correction" if n == 1 else "%d corrections" % n)
                if n else "no corrections")
    pre = [r for r in f["reviews"] if r["kind"] == "pre"]
    post = [r for r in f["reviews"] if r["kind"] == "post"]
    if post:
        bits.append("reviewed after publication %s" % I.fmt(post[-1]["on"]))
    elif pre:
        bits.append("reviewed before publication %s" % I.fmt(pre[-1]["on"]))
    else:
        bits.append("no outside review")
    bits.append("sources checked %s" % I.fmt(f["sources_checked"])
                if f["sources_checked"] else "sources not checked")
    return " &middot; ".join(bits)


def render() -> str:
    style = (I.ROOT / "site" / "whatholdsup" / "index.html").read_text(encoding="utf-8")
    head = style[:style.index("</head>")]
    head = head.replace("<title>", "<title>Issues &mdash; ", 1)
    rows = []
    for slug, ordinal, title, subject, question in ISSUES:
        rows.append("""  <a class="issue" href="/%s">
    <span class="no">%s</span>
    <h3>%s</h3>
    <p class="subject">%s</p>
    <p>%s</p>
    <span class="more">Read the assessment &rarr;</span>
    <span class="prov">%s</span>
  </a>""" % (slug, ordinal, html.escape(title), html.escape(subject),
             html.escape(question), facts_line(slug)))
    return """%s
</head>
<body>
<div class="wrap">

%s

<header class="hero">
  <div class="eyebrow">Every assessment</div>
  <h1>Issues</h1>
  <p class="standfirst">Each one is a contested question worked through claim by
  claim. The title says what it is called; the line under it says what it is
  about, and the line under that is the question it answers. The facts beside
  each are the same four for every issue, including the ones that are zero &mdash;
  a correction count only means something beside how hard anyone looked.</p>
</header>

<section>
%s
</section>

<footer>
  <p class="fineprint">Every date on this site is the publication's editorial
  local date &mdash; the date it was in New York when we published, updated or
  corrected a piece.</p>
  <p>Published by CivicScale. Corrections and challenges:
  <a href="mailto:corrections@whatholdsup.org">corrections@whatholdsup.org</a>
  &mdash; acknowledged within 48 hours, resolved or explained within 10 business
  days.</p>
</footer>

</div>
</body>
</html>
""" % (head, NAV, "\n\n".join(rows))


def main() -> int:
    OUT.write_text(render(), encoding="utf-8")
    print("wrote %s (%d bytes)" % (OUT.relative_to(I.ROOT), OUT.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
