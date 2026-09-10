#!/usr/bin/env python3
"""The same four facts about every issue, including the ones that are zero.

WHY THIS EXISTS
---------------
Until 2026-09-10 the homepage showed each issue's dates and, where it applied, a
`corrected` marker. That made the two issues anyone had examined look damaged and
the one nobody had examined look clean:

    Issue three   published 30 August                       <- reads as sound
    Issue two     published 28 August · updated 31 August · corrected
    Issue one     published 28 August · updated 10 September · corrected

**The reality is the inverse.** Issue one has been through four revisions, an
outside review with twenty-two findings, an adjudication, a verification by a
non-author and an operator acceptance. Issue three has had none of that. It has
no corrections because nobody has looked as hard, not because it is sounder.

So the page did two wrong things, and the second is worse than the first: it
rendered "we found and fixed an error" as a demerit, in a publication whose
premise is that a checkable claim beats an uncheckable one — and it let **the
absence of a marker read as a positive signal when it is an absence of
information.** A reader left believing issue three was the most reliable, and no
sentence on the page said so.

THE FIX IS NOT TO INVERT THE BADGE
----------------------------------
"Most rigorously reviewed" would be the same failure pointed the other way: an
unverifiable claim about our own virtue, in the one place a reader cannot check
it. What works is what has worked all week —

    show the structure, not a verdict word.

Every issue carries the same four facts in the same slots, including the zeroes.
Then "no corrections" sits beside "no outside review" and means something, and
"fourteen corrections" sits beside "outside review, 8 September" and also means
something. **A correction count is only weighable beside how hard anyone looked.**

Everything here is derived. Nothing is typed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import index_dates as I                                   # noqa: E402


def _record():
    try:
        return json.loads(I.RECORD.read_text(encoding="utf-8")).get("published") or []
    except Exception:
        return []


def corrections(slug: str) -> int:
    return I.corrections_count(slug)


def _first_publication_instant(slug: str):
    from datetime import datetime
    for r in _record():
        if r.get("issue") == slug and r.get("action") == "publish" and r.get("at"):
            return datetime.fromisoformat(str(r["at"]).replace("Z", "+00:00"))
    return None


def outside_reviews(slug: str) -> list[dict]:
    """Every recorded outside review, with WHICH KIND it was.

    ONE SLOT WAS HOLDING TWO EVENTS, and the homepage inherited it.

    `reviews.json` records both a **pre-publication read** — an independent
    reader given the page before it goes out — and a **post-publication review**,
    an adversarial read of what is already live. They are not the same claim
    about an issue. On 2026-09-10 the homepage printed both as "outside review
    <date>", so deskilling's pre-publication read of 30 August (2 findings, 28
    minutes before it published) sat in the same slot as melanoma's
    post-publication review of 8 September (22 findings, eleven days after), and
    a reader could not tell them apart. Worse, deskilling's date EQUALS its
    publication date, which reads as though the review followed the page.

    b13's two-notions-of-"used", one layer out: the record already distinguished
    them in prose — one row's `reviewer` field literally says "post-publication"
    — and nothing read it.

    The kind is DERIVED, by comparing the review's instant to the issue's first
    publication. Not typed, and not taken from the prose.
    """
    from datetime import datetime, timezone
    try:
        import publish as P
        rows = json.loads(P.REVIEWS.read_text(encoding="utf-8")).get("reviews") or []
    except Exception:
        return []
    first = _first_publication_instant(slug)
    out = []
    for r in rows:
        if r.get("issue") != slug or not r.get("at"):
            continue
        d = datetime.fromisoformat(str(r["at"]).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        out.append({"on": I.editorial_date(d),
                    "kind": "pre" if (first and d < first) else "post",
                    "findings": r.get("findings"),
                    "reviewer": r.get("reviewer") or ""})
    return sorted(out, key=lambda x: x["on"])


def sources_checked(slug: str):
    """The most recent date every source's bibliographic record was read for
    errata. A date, or None when no sweep has run."""
    from datetime import date
    import source_store as store
    p = store.case_dir(slug) / "errata.json"
    if not p.exists():
        return None
    try:
        rows = (json.loads(p.read_text(encoding="utf-8")).get("checked") or {}).values()
    except Exception:
        return None
    days = sorted({r.get("checked_on") for r in rows if r.get("checked_on")})
    return date.fromisoformat(days[-1]) if days else None


def facts(slug: str) -> dict:
    days = I.publication_dates(slug)
    revs = outside_reviews(slug)
    return {"slug": slug,
            "published": days[0] if days else None,
            "revised": days[-1] if days and days[-1] != days[0] else None,
            "corrections": corrections(slug),
            "reviews": revs,
            "sources_checked": sources_checked(slug)}


def line(slug: str, ordinal: str) -> str | None:
    """The homepage card's meta line. Four facts, same slots, zeroes included."""
    f = facts(slug)
    if not f["published"]:
        return None
    bits = ["%s &middot; published %s" % (ordinal, I.fmt(f["published"]))]
    bits.append("revised %s" % I.fmt(f["revised"]) if f["revised"] else "not revised")
    # NO NESTED ANCHOR. The card is itself an <a>, so an <a> inside it is
    # invalid HTML: a browser closes the outer link at the inner one, and every
    # fact after "14 corrections" falls outside the clickable card. The first
    # version of this line did exactly that and it was served for twenty
    # minutes. The count is text; the card already links to the issue.
    n = f["corrections"]
    bits.append(("1 correction" if n == 1 else "%d corrections" % n)
                if n else "no corrections")
    pre  = [r for r in f["reviews"] if r["kind"] == "pre"]
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


def main() -> int:
    import publish as P
    for slug in sorted(P.ISSUES):
        f = facts(slug)
        print("\n  %s" % slug)
        print("    published        %s" % (I.fmt(f["published"]) if f["published"] else "—"))
        print("    revised          %s" % (I.fmt(f["revised"]) if f["revised"] else "not revised"))
        print("    corrections      %d" % f["corrections"])
        for r in f["reviews"] or []:
            print("    review           %-18s %s-publication, %s finding(s)"
                  % (I.fmt(r["on"]), r["kind"], r["findings"]))
        if not f["reviews"]:
            print("    review           none")
        print("    sources checked  %s" % (I.fmt(f["sources_checked"])
                                           if f["sources_checked"] else "never"))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
