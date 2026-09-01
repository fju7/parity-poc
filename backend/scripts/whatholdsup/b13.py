#!/usr/bin/env python3
"""B13 -- IS THIS FIGURE IN ANYTHING WE HOLD?

WHY THIS CHECK EXISTS
---------------------
On 2026-09-01, three figures were found on the live melanoma page that appear
in NONE of the eight documents that issue holds:

    68.8%   a recurrence-free rate "at five years". The cited paper prints
            72.4% at four years, against the 49.1% the page pairs it with.
    35.4    the lower bound of a survival interval, attributed to The ASCO
            Post, whose full text we hold and which prints no such number.
    0.0075  a one-sided p-value, quoted from a "20 January 2026 topline" that
            has no entry in the source list at all.

Not one was caught. Every check in this repository asks a question that starts
one step too late:

    B2  is this span in the source THIS ROW NAMES     -- needs a binding first
    B12 does the cited source carry this precision    -- needs a citation first
    B9  is this anchor in the ledger                   -- reads links, not digits
    B6  is this scope word carried by the span         -- reads words, not digits

All four presuppose that the figure came from somewhere. The question none of
them asks is the one a reader would ask first:

    DOES THIS NUMBER APPEAR ANYWHERE IN ANYTHING WE HOLD?

It needs no binding, no citation and no judgement. It runs over every figure on
a page in one pass, and it would have caught all three on the day they were
written.

WHAT A HIT AND A MISS MEAN -- AND DO NOT MEAN
---------------------------------------------
A HIT IS NOT "TRUE". 49.1% is in the paper and the sentence around it is still
wrong: the page calls it a five-year figure and pairs it with a number that
does not exist. Presence is presence. R1 governs here as everywhere.

A MISS IS NOT "FALSE". A figure can be absent for an honest reason -- most
often because the document it came from is not held. cdk46's MONARCH 3 row
prints HR 0.54 (0.41-0.72) from the 2017 primary paper, which is
`fragment_only`; the figures are missing from the library, not from the
literature. So every report of an absence carries the count of sources this
issue names and does not hold, and the check refuses to say more than it knows.

AN ABSENCE OBSERVED BY SOMETHING THAT COULD NOT HAVE SEEN THE THING IS NOT AN
ABSENCE. Recorded here for the ninth time. The whole value of this check is in
reporting absence, so the two ways it could report a false one are closed
explicitly: the normaliser handles The Lancet's middle dot (the eighth
occurrence, caused by a character), and the page's OWN ARITHMETIC -- figures
this page computed and says it computed -- is excluded rather than searched
for, because no source will ever contain it.

WHAT COUNTS AS A FIGURE
-----------------------
Decimals, and integers of three digits or more. Not bare one- and two-digit
integers: "eight trainees", "three conditions", "50 patients" are in every
document ever written and finding them proves nothing. Not years. Percentages
count when they carry a decimal (68.8%) or three digits, because those are the
ones a page gets wrong; a bare "70%" is excluded for the same reason "8" is.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_store as store   # noqa: E402
import source_ledger as ledger  # noqa: E402
import spancheck as SC          # noqa: E402
import bindings as B            # noqa: E402
import autobind as AB           # noqa: E402

# a decimal, or an integer of three digits or more (with optional separators)
FIGURE = re.compile(r"(?<![A-Za-z0-9.$-])"
                    r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{3,})"
                    r"(?![0-9])")

# Figures that mean something other than a measurement, in the page's own voice.
NOT_A_MEASUREMENT = re.compile(
    r"NCT\d+|10\.\d{4,9}/|ISSN|ISBN|\d+\.\d+\.\d+"
    # An identifier is not a measurement. The NCCN guideline's edition is
    # "version 6.2026" and Europe PMC's record is "PMID 41093689"; both were
    # reported as figures in no held document, which is true and useless.
    r"|\bversion\b|\bPMID\b|\bPMCID\b|\bPMC\d|\bISRCTN\b|\bEudraCT\b", re.I)


def _is_year(f: str) -> bool:
    return "." not in f and "," not in f and len(f) == 4 and 1900 <= int(f) <= 2099


def figures_on_page(slug: str) -> list[tuple[str, str]]:
    """(figure, the sentence it is in) for every checkable figure on the page."""
    out, seen = [], set()
    for sent in B.page_sentences(slug):
        if AB.OURS.search(sent):
            continue                      # the page says it did this sum itself
        for m in FIGURE.finditer(SC._norm(sent)):
            f = m.group(1).replace(",", "")
            if _is_year(f) or NOT_A_MEASUREMENT.search(
                    sent[max(0, m.start() - 12):m.end() + 12]):
                continue
            if (f, sent) in seen:
                continue
            seen.add((f, sent))
            out.append((f, sent))
    return out


def _forms(fig: str) -> list[str]:
    """The ways a document may print this figure.

    The page writes "1,137" and the press release writes "1,137", but this
    check strips separators so that both reduce to one figure -- and then
    searched the sources for the STRIPPED form, which is in neither. It
    reported a figure printed identically in both documents as being in nothing
    we hold, four times on one page. An absence reported by something that
    could not have seen the thing is not an absence.
    """
    forms = {fig}
    if "." not in fig and len(fig) > 3:
        whole = fig
    else:
        whole = fig.split(".")[0]
    if len(whole) > 3:
        grouped = ""
        while len(whole) > 3:
            grouped = "," + whole[-3:] + grouped
            whole = whole[:-3]
        grouped = whole + grouped
        forms.add(grouped + fig[len(fig.split(".")[0]):])
    return sorted(forms)


def where(fig: str, slug: str) -> list[str]:
    """Every held source whose bytes carry this figure, however it prints it."""
    pat = re.compile("|".join(r"(?<![0-9.])%s(?![0-9])" % re.escape(f)
                              for f in _forms(fig)))
    hits = []
    for sid in sorted(store.held(slug)):
        text = SC._text(slug, sid) or ""
        if pat.search(SC._norm(text)):
            hits.append(sid)
    return hits


def unheld(slug: str) -> list[str]:
    held = store.held(slug)
    return [s["id"] for s in store.sources(slug) if s["id"] not in held]



# ---------------------------------------------------------------------------
# declared exclusions
# ---------------------------------------------------------------------------
#
# Some figures on a page are not claims about any document. "Below 0.05 is
# called statistically significant" is a convention being explained, not a
# number taken out of a paper, and no source will ever contain it in that
# sense.
#
# The wrong fix is an allow-list built from vocabulary this check has met --
# "ignore 0.05", "ignore round numbers" -- which is the mistake this repository
# has now made twice. The right one is a DECLARED exclusion: a person writes
# down the figure, enough of the sentence to pin it to that sentence and no
# other, and why. It is a signature, not a filter.
#
# Every exclusion is counted in the report, so a page cannot quietly acquire
# them, and one that no longer matches any sentence is named as stale rather
# than dropped -- an exclusion outliving the sentence it was written for is how
# a filter starts.

def exclusions_path(slug: str) -> Path:
    return store.case_dir(slug) / "figure-exclusions.json"


def load_exclusions(slug: str) -> list[dict]:
    p = exclusions_path(slug)
    if not p.exists():
        return []
    import json
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc.get("exclusions") or []


def _excluded(fig: str, sent: str, rules: list[dict]) -> dict | None:
    for r in rules:
        if r.get("figure") == fig and (r.get("in_sentence") or "") and \
                r["in_sentence"] in sent:
            return r
    return None


def run(slug: str) -> dict:
    rules = load_exclusions(slug)
    used: set[int] = set()
    missing, present, excluded = [], 0, []
    for fig, sent in figures_on_page(slug):
        hits = where(fig, slug)
        if hits:
            present += 1
            continue
        r = _excluded(fig, sent, rules)
        if r is not None:
            used.add(id(r))
            excluded.append((fig, r))
            continue
        missing.append((fig, sent))
    stale = [r for r in rules if id(r) not in used]
    return {"checked": present + len(missing) + len(excluded), "present": present,
            "missing": missing, "excluded": excluded, "stale": stale,
            "unheld": unheld(slug), "sources": len(store.sources(slug))}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--limit", type=int, default=60)
    a = ap.parse_args()

    r = run(a.slug)
    print("\n  %d figure(s) on the page checked against every held document"
          % r["checked"])
    print("  %d found in something we hold, %d in nothing we hold"
          % (r["present"], len(r["missing"])))
    print("  %d of this issue's %d sources are not held -- an absence below "
          "may be theirs" % (len(r["unheld"]), r["sources"]))
    if r["unheld"]:
        print("  not held: %s" % ", ".join(r["unheld"]))
    print()
    for fig, sent in r["missing"][:a.limit]:
        print("  %-10s %s" % (fig, sent[:110]))
    if len(r["missing"]) > a.limit:
        print("  ... %d more" % (len(r["missing"]) - a.limit))
    for fig, rule in r["excluded"]:
        print("  %-10s excluded by %s on %s: %s"
              % (fig, rule.get("by", "?"), rule.get("on", "?"),
                 rule.get("why", "")[:80]))
    for rule in r["stale"]:
        print("  %-10s STALE EXCLUSION — matches no sentence on the page now"
              % rule.get("figure", "?"))
    print("\n  A figure found is not a sentence that is true. A figure missing "
          "is not a\n  sentence that is false. Both are questions for a "
          "person.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------
#
# WHY THIS IS A STOP AND NOT A WARNING.
#
# The three figures this check was built for reached a published page because
# NOTHING IN THE PROCESS EVER REQUIRED A DOCUMENT TO EXIST BEFORE A SENTENCE
# ABOUT IT COULD BE WRITTEN. The dates are in the history:
#
#   2026-08-26  the melanoma page is written, carrying 35.4 and 0.0075
#   2026-08-27  68.8% is added, as "the five-year absolute rates"
#   2026-08-28  the issue's source ledger is created -- two days later, with
#               no access state on any of its ten entries
#   2026-08-29  S004, the paper that settles all three, is entered for the
#               first time, in the state `machine_read`, whose only evidence
#               was that a URL had appeared in a gate report's citation list
#   2026-09-01  S004's full text is held for the first time, six days after
#               the sentence that misquotes it was published
#
# Every gate ran downstream of the writing. They asked whether the page was
# internally consistent, whether its links resolved, whether its coverage
# claims were supported. None asked whether the numbers came from anywhere,
# because on 26 August there was nowhere for them to come from.
#
# So this is not another check on prose. It is the check that says the library
# has to exist first.

# The same three strings every other check module uses. Defining BAD as "bad"
# here instead of "BLOCKED" made this row vanish from the preflight entirely --
# printed under a mark the display had no key for -- which is a check that does
# not run being indistinguishable from a check that passes.
OK, BAD, WARN = "ok", "BLOCKED", "warn"


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    r = run(slug)
    if not r["checked"]:
        return [("figures in held documents", WARN,
                 "no figures found on the page to check")]
    if r["stale"]:
        return [("figures in held documents", BAD,
                 "%d declared exclusion(s) no longer match any sentence on the "
                 "page: %s. An exclusion that outlives its sentence is a filter."
                 % (len(r["stale"]),
                    ", ".join(x.get("figure", "?") for x in r["stale"])))]
    n = len(r["missing"])
    if not n:
        note = ("" if not r["excluded"] else
                "; %d declared exclusion(s)" % len(r["excluded"]))
        return [("figures in held documents", OK,
                 "all %d figure(s) on the page appear in a document we hold%s"
                 % (r["checked"], note))]
    shown = ", ".join(f for f, _s in r["missing"][:6])
    why = ("%d of %d figure(s) are in no document this issue holds: %s%s"
           % (n, r["checked"], shown, " ..." if n > 6 else ""))
    if r["unheld"]:
        # An absence observed by something that could not have seen the thing
        # is not an absence. With sources unheld, this cannot be a STOP.
        return [("figures in held documents", WARN,
                 "%s — but %d of %d source(s) are unheld (%s), so an absence "
                 "here may be theirs. Acquire them and this becomes decidable."
                 % (why, len(r["unheld"]), r["sources"],
                    ", ".join(r["unheld"][:8])))]
    return [("figures in held documents", BAD,
             "%s — and every source is held, so there is nowhere else they "
             "could have come from. Run b13.py %s." % (why, slug))]
