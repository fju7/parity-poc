#!/usr/bin/env python3
"""How a figure is written: thousands separators, one-place rounding, and a
comma-and-space grouping that only extracted text produces.

One module, so that rule 1 (bindings.rule_rows), B12 (spancheck.b12_precision)
and B13 (b13.py) read a figure with the same rules and cannot drift. Pure
string functions; no I/O, no imports from this package.
"""
from __future__ import annotations

import re


# --- thousands separators ----------------------------------------------------
#
# FOUR SEPARATORS, ONE NUMBER. A source may print fourteen thousand one hundred
# and seventy as "14,170", "14 170", "14\u00a0170" (no-break space) or
# "14\u2009170" (thin space); _norm turns the last two into a plain space. On
# 2026-10-17 six figures in the four test issues were reported as in no span
# they were bound to while every one of them sat in the span, printed with a
# space: T01's 14,170, T02's 9,888,373 and 100,000, T04's 21,315, 60,000 and
# 53,537. Rule 1 and b13 read only the comma.
#
# A separator bug in a figure reader is value corruption, not a matching
# failure (CLAUDE.md, SAP-Signal-7), so the reading is narrow: a lead group of
# one to three digits, then groups of exactly three, with no digit, decimal
# point or separator-and-digit on either side.
GROUP_SEP = ",\u00a0\u2009\u202f "
_SEP = "[%s]" % GROUP_SEP
_GROUPED = re.compile(r"(?<![\d.,])(?<!\d%s)(\d{1,3})((?:%s\d{3})+)(?!\d)" % (_SEP, _SEP))


def comma_grouped(text: str) -> str:
    """The text with every grouped integer written with commas: "14 170" and
    "14\u00a0170" become "14,170". Commas are the one separator the figure
    readers (modelbind._NUM, b13.FIGURE) already understand."""
    return _GROUPED.sub(lambda m: m.group(1) + re.sub(_SEP, ",", m.group(2)), text)


def figure_pattern(figure: str) -> str:
    """A regex for this one figure however its thousands are separated: none,
    comma, space, no-break space or thin space. Bounded on both sides so that
    14170 matches neither 114170 nor "3 14 170" nor "14 170 000"."""
    f = figure.replace(",", "")
    whole, dot, frac = f.partition(".")
    if len(whole) > 3 and whole.isdigit():
        lead = len(whole) % 3 or 3
        groups = [whole[:lead]] + [whole[i:i + 3] for i in range(lead, len(whole), 3)]
        body = ("%s?" % _SEP).join(re.escape(g) for g in groups)
    else:
        body = re.escape(whole)
    if dot:
        body += re.escape(dot + frac)
    return (r"(?<![\d.])(?<!\d%s)%s(?!\d)(?!%s\d{3}(?!\d))" % (_SEP, body, _SEP))


# --- a comma and one space between groups, in extracted text only -------------
#
# S001's PDF prints 1,222 and pdftotext returns "1, 222": a comma, one space,
# three digits. _GROUPED will not read that as one number, rightly, because on
# a page "1, 222 and 3" is a list. So this is never applied to a page sentence
# and never rewrites a text: it asks of held text only whether THIS figure is
# printed there with ", " between its groups, and the caller records that it
# read it so (an INFO note, never silent). A figure it does not equal -- 222
# against "1, 222" -- gets nothing from it. 2026-10-18.
def split_grouped(figure: str, text: str) -> str | None:
    """The run in `text` that prints `figure` with a comma and exactly one
    space between its thousands groups ("1, 222" for 1,222), or None. Bounded
    like figure_pattern, and refused where the run continues a list ("5, 1,
    222"), runs on into another group ("1, 222, 333" is not 1,222) or opens a
    bracket."""
    whole, dot, frac = figure.replace(",", "").partition(".")
    if not whole.isdigit() or len(whole) <= 3 or (dot and not frac.isdigit()):
        return None
    lead = len(whole) % 3 or 3
    groups = [whole[:lead]] + [whole[i:i + 3] for i in range(lead, len(whole), 3)]
    body = ", ".join(re.escape(g) for g in groups)
    if dot:
        body += re.escape("." + frac)
    # Not straight after "(": "F (3, 581)" is a pair of degrees of freedom.
    m = re.search(r"(?<![\d.,(])(?<!\d, )%s(?![\d])(?!\.\d)(?!, \d)" % body, text)
    return m.group(0) if m else None


def rounds_to(value: str, printed: str, *, min_places: int = 1) -> bool:
    """Is `printed` `value` with at most one decimal place dropped, correctly
    rounded? (Exactly one dropped here; equal strings are matched before this
    is asked.)

    The precision rule B12 has always applied, as one function so that B12 and
    rule 1 cannot drift: one place at a time ("ONE DECIMAL PLACE AT A TIME"
    below), the correct rounding and not a truncation (0.008 is 0.01, never
    0.00), half away from zero as journals print it, and never shorter than
    `min_places` -- B12 asks 2, because a bare 0.5 in a document is a digit and
    not a statement; rule 1 asks 1, because there the longer figure is in the
    very span the sentence is bound to.

    So 0.946 -> 0.95 and 0.43 -> 0.4 are roundings; 0.946 -> 0.9 is not (two
    places, not one), and nor is 0.946 -> 0.94 (a truncation).
    """
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
    v, p = value.replace(",", "").lstrip("-"), printed.replace(",", "").lstrip("-")
    if "." not in v:
        return False
    places = len(p.partition(".")[2])
    if places < min_places or places != len(v.partition(".")[2]) - 1:
        return False
    try:
        got = Decimal(v).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        return got == Decimal(p)
    except InvalidOperation:
        return False
