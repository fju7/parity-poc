#!/usr/bin/env python3
"""
index_dates.py — the homepage's dates against the publication record.

WHY THIS EXISTS
---------------
index.html is in guard_published's STANDING set, which means no publication
record governs it and, until this file, nothing checked a word on it. It went
stale for twelve days across four melanoma revisions and nobody noticed, because
every control this repository has is pointed at issue pages.

The homepage is the first thing a reader sees and the only place most of them
will ever look. "Issue one · updated 28 August 2026", on a page republished on
9 September, is a false statement about our own work in the most-read position on
the site.

WHAT IT CHECKS, AND THE DISTINCTION IT REFUSES TO COLLAPSE
----------------------------------------------------------
For each issue linked from the index:

  * "Published <date>" must equal the FIRST publication record.
  * "Updated <date>" must equal the LATEST publication record, and must be
    present whenever the two differ and absent when they do not.
  * "Corrected" must be present when the issue's corrections.md has entries.

An UPDATE and a CORRECTION are different facts and a reader is entitled to tell
them apart. An update is a republication — it may be a new section, a clearer
sentence, a link. A correction is an admission that something published was
wrong. Collapsing them into one word lets the second hide inside the first, and
this publication's whole argument is that the second should be visible.

ORDERING IS NOT CHECKED. The index orders by first publication and an update
does not move an issue up. That is deliberate: ordering by recency would reward
churn and bury an issue nobody has had to correct.

BEHIND IS NOT UNFOUNDED
-----------------------
A disagreement between the index and the record is reported as one of two kinds,
because they call for different work and imply different things about us:

  BEHIND     the index names a real event, and a later one has happened that it
             has not caught up with. Nothing published was false when written;
             the page has gone stale. The repair is to regenerate.
  UNFOUNDED  the index names a date no publication record supports at all. That
             is a date we cannot account for, and it is a different and worse
             problem than staleness — it is either a record that was never
             written or a date that was typed.

Collapsing these would have made the 8 September cdk46 finding unreadable: a
date that is correct in the editorial zone and merely off-by-one in UTC would
have been reported in the same words as a fabrication.

TIMEZONE
--------
See EDITORIAL_TZ below. This file previously called .date() directly on a
UTC-aware datetime, which is the same bug in the checker that it exists to catch
on the page: it would have reported cdk46's correct "28 August" as wrong, and
"corrected" it to the UTC date of an event that happened at 22:22 in New York.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

OK, WARN, BAD = "ok", "warn", "STOP"

# ---------------------------------------------------------------------------
# EDITORIAL_TZ — the zone every reader-facing date on this site is stated in.
#
# An IANA zone name, never a fixed offset. This repository's own commit history
# carries -05:00 and -04:00 in the same year; a fixed offset would be wrong for
# roughly seven months of it, and would silently move a December date by an hour
# in a way nobody would look for.
#
#   * A reader-facing date is the publication's editorial LOCAL date: the date it
#     was in New York when the thing happened.
#   * The record stores UTC. Conversion runs one way only — UTC in the record,
#     converted for display. A displayed date is never written back to the
#     record, and the record is never re-stamped from a displayed date.
#   * The machine's own clock is NOT a default and must never be consulted. The
#     commits in this repository were recorded under four different offsets
#     (-05:00, -04:00, Z, and -06:00 as of 9 September 2026); `datetime.now()`,
#     `astimezone()` with no argument and `--date=iso-local` all answer a
#     question about where the laptop is, not about when we published.
#   * If this constant is ever changed, dates already published are NOT
#     recomputed under the new zone. A published date is a statement we made on
#     a day, in the zone in force that day. Re-deriving history under a new zone
#     would silently rewrite claims readers have already seen; the change applies
#     from the day it is made, and the old dates stand as published.
# ---------------------------------------------------------------------------
EDITORIAL_TZ = ZoneInfo("America/New_York")

ROOT = Path(__file__).resolve().parents[3]
RECORD = ROOT / "backend" / "data" / "whatholdsup" / "published.json"
INDEX = ROOT / "site" / "whatholdsup" / "index.html"

# "Issue one · published 28 August 2026 · corrected 29 August 2026"
CARD = re.compile(r'<a class="issue" href="/(?P<slug>[a-z0-9-]+)">\s*'
                  r'<span class="no">(?P<meta>.*?)</span>', re.S)
DATE = re.compile(r'(published|updated|corrected)\s+'
                  r'(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})', re.I)
MARKER = re.compile(r'\bcorrected\b', re.I)

BEHIND, UNFOUNDED = "BEHIND", "UNFOUNDED"

# WHICH RECORD ROWS ARE A DATE A READER SHOULD SEE.
#
# published.json writes four actions and the words do not mean what they look
# like. "publish" is a publication and "update" is a substantive change to a
# living issue; both are things that happened to the argument, and both belong
# on the homepage. "announce" is an email. "republish" is the misnomer: it is
# what `record-live` writes when a person reads a diff and signs it as NOT
# touching the argument — every row carrying it in this record is a live-sha
# reconciliation, distinguishable by the basis/diff/supersedes keys the
# publication rows do not have.
#
# Counting a reconciliation as an update would have put "Issue three · updated
# 9 September 2026" on the homepage because a nav link to /the-rubric was added
# to the page on 9 September. A reader takes "updated" to mean the assessment
# moved. It did not. This is the same distinction the docstring makes between an
# update and a correction, one step further down: a reconciliation is not an
# update either, and the record's own vocabulary does not draw the line.
PUBLICATION_ACTIONS = (None, "publish", "update")
RECONCILIATION_ACTIONS = ("republish",)


def reconciliations(slug: str) -> list[datetime]:
    """record-live rows. Real events, deliberately not reader-facing dates."""
    try:
        raw = json.loads(RECORD.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = raw.get("published") or raw.get("publications") or (raw if isinstance(raw, list) else [])
    return sorted(datetime.fromisoformat(r["at"].replace("Z", "+00:00"))
                  for r in rows
                  if r.get("issue") == slug
                  and r.get("action") in RECONCILIATION_ACTIONS
                  and r.get("at"))


def _text(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def fmt(d: date) -> str:
    """"9 September 2026" — the form the index already uses."""
    return "%d %s %d" % (d.day, d.strftime("%B"), d.year)


def editorial_date(dt: datetime) -> date:
    """The calendar date this instant fell on in the editorial zone.

    The whole point of the file. dt arrives UTC-aware off the record; taking
    .date() on it answers "what date was it in Greenwich", which is not what any
    sentence on the site claims.
    """
    return dt.astimezone(EDITORIAL_TZ).date()


def publications(slug: str) -> list[datetime]:
    try:
        raw = json.loads(RECORD.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = raw.get("published") or raw.get("publications") or (raw if isinstance(raw, list) else [])
    out = []
    for r in rows:
        if r.get("issue") != slug:
            continue
        if r.get("action") not in PUBLICATION_ACTIONS:
            continue
        at = r.get("at")
        if not at:
            continue
        out.append(datetime.fromisoformat(at.replace("Z", "+00:00")))
    return sorted(out)


def publication_dates(slug: str) -> list[date]:
    """Every publication of this issue, as editorial-local dates, in order."""
    return [editorial_date(d) for d in publications(slug)]


def corrections_count(slug: str) -> int:
    for d in (ROOT / "issues").glob("WHU-*-%s" % slug):
        f = d / "corrections.md"
        if f.exists():
            return sum(1 for ln in f.read_text(encoding="utf-8").splitlines()
                       if ln.startswith("## "))
    return 0


def expected(slug: str) -> dict:
    days = publication_dates(slug)
    if not days:
        return {}
    first, latest = days[0], days[-1]
    exp = {"published": first}
    if latest != first:
        exp["updated"] = latest
    if corrections_count(slug):
        exp["corrected"] = True
    return exp


def shown(meta_text: str) -> dict:
    out = {}
    for kind, when in DATE.findall(meta_text):
        try:
            out[kind.lower()] = datetime.strptime(when, "%d %B %Y").date()
        except ValueError:
            out[kind.lower()] = when
    if MARKER.search(meta_text):
        out.setdefault("corrected", True)
    return out


def _classify(shown_date, days: list[date]) -> str:
    """BEHIND if the index named a real publication; UNFOUNDED if it named a
    date this record cannot account for at all."""
    if isinstance(shown_date, date) and shown_date in days:
        return BEHIND
    return UNFOUNDED


def _behind_by(shown_date, days: list[date]) -> int:
    if not isinstance(shown_date, date):
        return 0
    return sum(1 for d in days if d > shown_date)


def audit(index_html: str | None = None) -> list[str]:
    """One string per disagreement, each labelled BEHIND or UNFOUNDED. Empty
    means the index tells the truth."""
    text = index_html if index_html is not None else INDEX.read_text(encoding="utf-8")
    problems = []
    for m in CARD.finditer(text):
        slug, meta = m.group("slug"), _text(m.group("meta"))
        exp, got = expected(slug), shown(meta)
        days = publication_dates(slug)
        if not exp:
            problems.append("%s [%s]: linked from the index with no publication record"
                            % (slug, UNFOUNDED))
            continue

        if got.get("published") != exp["published"]:
            if "published" not in got:
                problems.append(
                    "%s [%s]: first published %s and the index states no publication date"
                    % (slug, BEHIND, fmt(exp["published"])))
            else:
                kind = _classify(got["published"], days)
                extra = ("; that is a real publication, %d later one(s) exist"
                         % _behind_by(got["published"], days)) if kind == BEHIND else \
                        "; no publication record falls on that date in %s" % EDITORIAL_TZ.key
                problems.append(
                    "%s [%s]: index says published %s, first publication record is %s%s"
                    % (slug, kind, got["published"], fmt(exp["published"]), extra))

        if "updated" in exp:
            if "updated" not in got:
                n = _behind_by(got.get("published"), days)
                problems.append(
                    "%s [%s]: republished %s and the index shows no update date%s"
                    % (slug, BEHIND, fmt(exp["updated"]),
                       "; behind by %d event(s)" % n if n else ""))
            elif got["updated"] != exp["updated"]:
                kind = _classify(got["updated"], days)
                extra = ("; behind by %d event(s)" % _behind_by(got["updated"], days)) \
                    if kind == BEHIND else \
                    "; no publication record falls on that date in %s" % EDITORIAL_TZ.key
                problems.append(
                    "%s [%s]: index says updated %s, latest publication record is %s%s"
                    % (slug, kind, got["updated"], fmt(exp["updated"]), extra))
        elif "updated" in got:
            problems.append(
                "%s [%s]: index shows an update date but there is only one publication record"
                % (slug, UNFOUNDED))

        # A correction is not an update. Its absence from the index is the
        # failure this check exists for; its presence with a stale date is not
        # policed here, because corrections.md carries many dates and the index
        # legitimately shows the marker rather than a running list.
        if exp.get("corrected") and "corrected" not in got:
            problems.append(
                "%s [%s]: corrections.md has %d entr%s and the index shows no correction marker"
                % (slug, BEHIND, corrections_count(slug),
                   "y" if corrections_count(slug) == 1 else "ies"))
        elif got.get("corrected") and not exp.get("corrected"):
            problems.append(
                "%s [%s]: index shows a correction marker and this issue has no corrections log"
                % (slug, UNFOUNDED))
    return problems


def meta_html(slug: str, ordinal: str) -> str | None:
    """The card's meta line, derived. Nothing here is typed by hand — that is
    the point of deriving it, and the reason the 28 August row survived so long
    is that someone typed it once and nothing ever read it again."""
    exp = expected(slug)
    if not exp:
        return None
    bits = ["%s &middot; published %s" % (ordinal, fmt(exp["published"]))]
    if "updated" in exp:
        bits.append("updated %s" % fmt(exp["updated"]))
    if exp.get("corrected"):
        bits.append('<a href="/%s#updates">corrected</a>' % slug)
    return " &middot; ".join(bits)


def preflight_rows(index_html: str | None = None) -> list[tuple[str, str, str]]:
    problems = audit(index_html)
    return [("homepage dates match the record",
             OK if not problems else BAD,
             "every issue on the index shows the dates published.json records"
             if not problems else
             "%d disagreement(s) between the index and published.json: %s"
             % (len(problems), " || ".join(problems)))]


def main() -> int:
    problems = audit()
    print()
    if not problems:
        print("  ok    the index agrees with published.json (dates in %s)" % EDITORIAL_TZ.key)
        print()
        return 0
    print("  %d disagreement(s), dates read in %s:\n" % (len(problems), EDITORIAL_TZ.key))
    for p in problems:
        print("   !! %s" % p)
    print()
    print("  Expected, derived from published.json:")
    for m in CARD.finditer(INDEX.read_text(encoding="utf-8")):
        slug = m.group("slug")
        exp = expected(slug)
        if not exp:
            continue
        bits = ["published %s" % fmt(exp["published"])]
        if "updated" in exp:
            bits.append("updated %s" % fmt(exp["updated"]))
        if exp.get("corrected"):
            bits.append("corrected (%d entries)" % corrections_count(slug))
        rec = reconciliations(slug)
        line = " · ".join(bits)
        if rec:
            line += ("   [+%d live-sha reconciliation(s), latest %s — not shown to readers]"
                     % (len(rec), fmt(editorial_date(rec[-1]))))
        print("    %-11s %s" % (slug, line))
    print()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
