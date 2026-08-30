#!/usr/bin/env python3
"""Check that an issue's HTML and plain-text emails say the same things.

WHY THIS EXISTS
---------------
Every issue ships two emails. Mail clients choose between them and the
recipient sees exactly one, so the two are not a document and its preview --
they are two independent copies of the same claim, and nothing was comparing
them.

On 2026-08-28 the HTML email carried a paragraph about palbociclib's null
survival result and the plain-text one did not. The gate checked each file on
its own and passed each on its own; a gate cannot notice that a sentence it
never saw was missing. It had been dropped during a restructure of one file
that was not mirrored into the other, and it was found only because a finding
about that paragraph could not be applied to a file that lacked it.

The same shape as brief_diff.py: two documents in the same repository that
must agree, with no check across the gap.

WHAT IT DOES
------------
Splits both files into paragraphs, strips markup, and reports paragraphs
present in one and not the other, plus figures present in one and not the
other. Footers legitimately differ -- the text version carries the raw
unsubscribe token where the HTML has a link -- so a small number of
mismatches at the end is expected and the output says so rather than pretending
otherwise.

Usage:
    python3 email_parity.py site/whatholdsup/email/issue2-cdk46.html \\
                            site/whatholdsup/email/issue2-cdk46.txt
"""

from __future__ import annotations

import argparse
import difflib
import html as _html
import re
import sys
from pathlib import Path

FIGURE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?%?")
MATCH_AT = 0.75          # two paragraphs are "the same" above this ratio


def paragraphs(path: Path) -> list[str]:
    s = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".html", ".htm"):
        s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
        s = re.sub(r"(?s)<!--.*?-->", " ", s)
        s = re.sub(r"<[^>]+>", "\n", s)
        s = _html.unescape(s)
    out = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", s)]
    return [p for p in out if len(p) > 60]


def _key(p: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", p.lower())[:80]


def figures(text: str) -> set[str]:
    out = set()
    for m in FIGURE.finditer(text):
        tok = m.group(0)
        bare = tok.rstrip("%").replace(",", "").lstrip("+-")
        if "." not in bare and not tok.endswith("%"):
            try:
                n = int(bare)
            except ValueError:
                continue
            if n < 10 or 1900 <= n <= 2100:
                continue
        out.add(tok.replace(",", "").lstrip("+"))
    return out


def missing(a: list[str], b: list[str]) -> list[str]:
    bk = [_key(x) for x in b]
    out = []
    for p in a:
        k = _key(p)
        if not any(difflib.SequenceMatcher(None, k, o).ratio() > MATCH_AT for o in bk):
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("html")
    ap.add_argument("text")
    args = ap.parse_args()
    h, t = Path(args.html), Path(args.text)
    for f in (h, t):
        if not f.exists():
            print("[ERROR] not found: %s" % f)
            return 2

    hp, tp = paragraphs(h), paragraphs(t)
    W = 72
    print("=" * W)
    print("EMAIL PARITY")
    print("  html : %s  (%d paragraphs)" % (h, len(hp)))
    print("  text : %s  (%d paragraphs)" % (t, len(tp)))
    print("=" * W)

    only_h, only_t = missing(hp, tp), missing(tp, hp)

    def block(title, items, note):
        print("\n%s  %d" % (title, len(items)))
        if not items:
            print("  none")
            return
        print("  " + note)
        for i in items:
            print("    %s%s" % (i[:150], "..." if len(i) > 150 else ""))

    block("IN THE HTML AND NOT IN THE TEXT", only_h,
          "A recipient whose client chose plain text will not see these.")
    block("IN THE TEXT AND NOT IN THE HTML", only_t,
          "A recipient whose client chose HTML will not see these. Footer "
          "boilerplate legitimately differs; anything else does not.")

    hf, tf = figures(" ".join(hp)), figures(" ".join(tp))
    block("FIGURES IN ONE AND NOT THE OTHER",
          sorted((hf ^ tf), key=lambda x: (len(x), x)),
          "A number one half of the audience sees and the other does not.")

    flagged = len(only_h) + len(only_t) + len(hf ^ tf)
    print("\n" + "-" * W)
    if flagged:
        print("%d difference(s). Expect one or two in the footer, where the text" % flagged)
        print("version carries the unsubscribe token the HTML puts in a link.")
        print("Anything above that is one half of your subscribers reading a")
        print("different issue from the other half.")
    else:
        print("The two versions say the same things.")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())

# ---------------------------------------------------------------------------
# provenance parity
# ---------------------------------------------------------------------------
#
# The email said "Every figure above comes from a trial publication or a drug
# label" while quoting P-VERIFY and PALMARES-2 -- observational comparative
# studies that are neither. The page said it correctly: "a trial publication, a
# drug label, or a comparative study". One half of the audience was told a
# narrower and false thing about where the numbers came from.
#
# Figure parity would never catch this: the figures matched exactly. What
# differed was the sentence describing what the figures ARE. So this compares
# the claims a document makes about its own sourcing, which is a small closed
# set of sentences and worth checking literally.

# [^.\n] rather than [^.]: a sourcing claim does not span a paragraph break.
# With [^.] the match ran backwards past a heading into whatever preceded it,
# so the page's claim was captured as "Sources Every figure above traces to..."
# and the email's identical sentence did not match it.
PROVENANCE = re.compile(
    r"[^.\n]*\b(every figure|all figures|each figure|every number|figures above|"
    r"comes from|traces to|drawn from)\b[^.\n]*\.", re.I)


def provenance_claims(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", m.group(0)).strip()
            for m in PROVENANCE.finditer(text)]


def provenance_parity(page_text: str, email_text: str) -> list[str]:
    """Sourcing claims the email makes that the page does not."""
    pg = {re.sub(r"[^a-z ]", "", c.lower()) for c in provenance_claims(page_text)}
    out = []
    for c in provenance_claims(email_text):
        k = re.sub(r"[^a-z ]", "", c.lower())
        if k in pg:
            continue
        # near-match: same claim, different list of source types
        close = [x for x in pg if len(set(k.split()) & set(x.split())) > 6]
        out.append(c + ("   [page says: " + sorted(close, key=len)[0][:110] + "]"
                        if close else "   [no matching sentence on the page]"))
    return out
