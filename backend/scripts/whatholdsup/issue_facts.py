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


def outside_reviews(slug: str) -> list[str]:
    """Editorial dates of every recorded outside review, oldest first."""
    from datetime import datetime
    try:
        import publish as P
        rows = json.loads(P.REVIEWS.read_text(encoding="utf-8")).get("reviews") or []
    except Exception:
        return []
    out = []
    for r in rows:
        if r.get("issue") != slug or not r.get("at"):
            continue
        d = datetime.fromisoformat(str(r["at"]).replace("Z", "+00:00"))
        if d.tzinfo is None:
            from datetime import timezone
            d = d.replace(tzinfo=timezone.utc)
        out.append(I.editorial_date(d))
    return sorted(out)


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
    n = f["corrections"]
    bits.append('<a href="/%s#updates">%s</a>'
                % (slug, "1 correction" if n == 1 else "%d corrections" % n)
                if n else "no corrections")
    bits.append("outside review %s" % I.fmt(f["reviews"][-1]) if f["reviews"]
                else "no outside review")
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
        print("    outside reviews  %s" % (", ".join(I.fmt(d) for d in f["reviews"])
                                           or "none"))
        print("    sources checked  %s" % (I.fmt(f["sources_checked"])
                                           if f["sources_checked"] else "never"))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
