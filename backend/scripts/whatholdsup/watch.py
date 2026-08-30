#!/usr/bin/env python3
"""
What Holds Up: living issues — the watch list and the changelog.

WHY THIS EXISTS
---------------
Some subjects are not settled when we publish them. Issue three is one: the
question is standing rather than closed, the literature is active, and the
authors of its strongest study explicitly called for the randomised crossover
trial that would change the answer. A piece like that is wrong within months
unless somebody keeps looking.

THE DANGER IT INTRODUCES, WHICH IS THE WHOLE POINT OF THIS FILE
---------------------------------------------------------------
A dated page makes a modest promise. "Checked as of 28 August 2026" tells a
reader exactly what they have. A page with a changelog makes a much stronger
one: it implies THIS IS CURRENT. If the watch does not actually run, we have
published a stale page that claims freshness — an unrun check reported as a
pass, in public, on a page a reader trusts MORE because of the very feature
that failed.

So the rule this module enforces is:

    THE PAGE DISPLAYS THE DATE OF THE LAST CHECK, NOT THE LAST CHANGE.

"Last reviewed 12 September; nothing has changed" is honest and only survives
if somebody looked. "Last updated 29 August" on a page nobody has opened since
is a lie told by omission, and it is the kind this publication exists to point
at in other people.

TWO HISTORIES, NEVER MERGED
---------------------------
  corrections.md   WE WERE WRONG. What a reader who saw the earlier version
                   needs to know.
  changelog.md     THE EVIDENCE MOVED. New work appeared and the piece changed
                   to match it.

Merging them would let us bury errors as updates and would make other people's
new findings look like our mistakes. Both are dishonest and they run in
opposite directions, which is how you know they are different things.

THE WATCH LIST IS THE KILL CONDITIONS
-------------------------------------
Before drafting, the premise records the specific findings that would change
or kill the piece. For a settled issue those are a one-shot test. For a living
one they are the standing query set, and `init` seeds the watch straight from
them. A kill condition that fires after publication is not an embarrassment;
it is the piece working.

USAGE
-----
    watch.py init    <slug>                    seed from the premise's kill conditions
    watch.py status  <slug>                    how stale is this watch
    watch.py check   <slug> --searched ... --found ...   record that a check ran
    watch.py entry   <slug> --what ... --changed ...     add a changelog entry
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path

import source_ledger as sl

ROOT = Path(__file__).resolve().parents[3]
OK, WARN, BAD = "ok", "warn", "STOP"

DEFAULT_INTERVAL_DAYS = 30

MONTHS = ("January February March April May June July August September "
          "October November December").split()


def pretty(d: date) -> str:
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year)


def case_dir(slug: str) -> Path:
    return sl.case_dir(slug)


def watch_path(slug: str) -> Path:
    return case_dir(slug) / "watch.json"


def changelog_path(slug: str) -> Path:
    return case_dir(slug) / "changelog.md"


def load(slug: str) -> dict | None:
    p = watch_path(slug)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def save(slug: str, doc: dict) -> None:
    watch_path(slug).write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def last_check(doc: dict) -> dict | None:
    checks = doc.get("checks") or []
    return checks[-1] if checks else None


def days_since_check(doc: dict) -> int | None:
    c = last_check(doc)
    if not c:
        return None
    try:
        return (date.today() - datetime.strptime(c["on"], "%Y-%m-%d").date()).days
    except Exception:
        return None


# ---------------------------------------------------------------------------
# the page's own claim about when it was last looked at
# ---------------------------------------------------------------------------

REVIEWED_RE = re.compile(
    r"last\s+reviewed\s*:?\s*(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})", re.I)


def reviewed_date_on_page(html: str) -> str | None:
    """What the page tells a reader about when it was last checked.

    Deliberately looks for 'last reviewed' and NOT for 'last updated'. A page
    that says when it last CHANGED tells a reader nothing about whether anyone
    has looked since, which is the exact misreading this module exists to
    prevent. If the page says 'updated', this returns None and the check fails,
    which is correct: the wrong word is the wrong promise.
    """
    m = REVIEWED_RE.search(html)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def preflight_rows(slug: str, page_html: str) -> list[tuple[str, str, str]]:
    """Rows for publish.py. Empty when the issue is not declared living.

    An issue is living only if somebody wrote watch.json. Silence is not a
    living issue, and this must never invent one: a page without a changelog
    makes the modest promise, which is always safe.
    """
    doc = load(slug)
    if doc is None:
        return []

    out: list[tuple[str, str, str]] = []
    interval = int(doc.get("review_interval_days") or DEFAULT_INTERVAL_DAYS)

    qs = [q for q in doc.get("questions", []) if q.get("status") == "open"]
    out.append(("living issue — open questions", OK if qs else BAD,
                "%d question(s) being watched" % len(qs) if qs else
                "watch.json exists and nothing is open. A living issue with no "
                "open question is a settled issue wearing a changelog; either "
                "open a question or delete watch.json."))

    n = days_since_check(doc)
    if n is None:
        out.append(("watch has been run", BAD,
                    "no check recorded. The page is about to promise a reader "
                    "it is current, and nobody has looked."))
    else:
        st = OK if n <= interval else (WARN if n <= 2 * interval else BAD)
        out.append(("watch has been run", st,
                    "last checked %d day(s) ago, against a %d-day interval"
                    % (n, interval)))

    shown = reviewed_date_on_page(page_html)
    c = last_check(doc)
    want = pretty(datetime.strptime(c["on"], "%Y-%m-%d").date()) if c else None
    if shown is None:
        out.append(("page says when it was last reviewed", BAD,
                    "no 'Last reviewed <date>' on the page. A changelog without "
                    "it tells a reader when we last CHANGED something, which is "
                    "not the same as when we last LOOKED."))
    elif want and shown != want:
        out.append(("page says when it was last reviewed", BAD,
                    "page says %s; the last recorded check was %s" % (shown, want)))
    else:
        out.append(("page says when it was last reviewed", OK, "says %s" % shown))

    # Every changelog entry binds to the sha it was written against, for the
    # same reason acceptances and announces do: an entry unbound from the
    # content it describes is a claim nobody can check.
    entries = doc.get("changelog", [])
    unbound = [e for e in entries if not e.get("page_sha")]
    out.append(("changelog entries bound to a sha", OK if not unbound else BAD,
                "%d entry/entries" % len(entries) if not unbound else
                "%d entry/entries with no sha: %s"
                % (len(unbound), ", ".join(e.get("on", "?") for e in unbound))))

    # The two histories must stay different things.
    corr = case_dir(slug) / "corrections.md"
    if corr.exists() and entries:
        ctext = corr.read_text(encoding="utf-8").lower()
        overlap = [e for e in entries
                   if (e.get("what") or "")[:60].lower() in ctext]
        out.append(("changelog is not the correction history",
                    OK if not overlap else BAD,
                    "the two histories are distinct" if not overlap else
                    "%d changelog entry/entries also appear in corrections.md. "
                    "One of them is in the wrong place: a correction is us being "
                    "wrong, an update is the evidence moving." % len(overlap)))
    return out


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_init(args) -> int:
    d = case_dir(args.slug)
    if watch_path(args.slug).exists() and not args.force:
        print("\n  %s already exists. --force to reseed.\n"
              % watch_path(args.slug).relative_to(ROOT))
        return 1

    prem = d / "premise.json"
    seeded: list[dict] = []
    if prem.exists():
        try:
            kc = json.loads(prem.read_text(encoding="utf-8")).get("kill_condition")
            if isinstance(kc, str) and kc.strip():
                # Kill conditions are written as one sentence with numbered
                # clauses. Split on the numbering rather than on punctuation,
                # because these sentences contain plenty of semicolons.
                parts = [p.strip(" ;.") for p in re.split(r"\(\d+\)", kc) if p.strip(" ;.")]
                for i, p in enumerate(parts[1:] if len(parts) > 1 else parts, start=1):
                    seeded.append({
                        "id": "W%d" % i,
                        "question": p,
                        "would_change": "seeded from the premise's kill condition — "
                                        "say explicitly what it would change",
                        "queries": [],
                        "status": "open",
                        "opened": date.today().isoformat(),
                    })
        except Exception as e:
            print("  could not read premise.json (%s); seeding empty." % e)

    doc = {
        "what_this_is":
            "The standing watch on a LIVING issue. These are the findings that "
            "would change or kill the piece, carried forward past publication "
            "instead of being tested once and forgotten. A kill condition that "
            "fires after publication is the process working.",
        "living": True,
        "review_interval_days": DEFAULT_INTERVAL_DAYS,
        "the_promise":
            "The page displays the date of the LAST CHECK, not the last change. "
            "'Last reviewed <date>; nothing has changed' is the honest line and "
            "the only one that cannot be told by a page nobody has opened.",
        "questions": seeded,
        "checks": [],
        "changelog": [],
    }
    save(args.slug, doc)
    print("\n  wrote %s with %d seeded question(s)."
          % (watch_path(args.slug).relative_to(ROOT), len(seeded)))
    if seeded:
        for q in seeded:
            print("    %s  %s" % (q["id"], q["question"][:88]))
        print("\n  Each needs `queries` filled in — what you would actually search")
        print("  to find out — and `would_change` written properly. A watch with")
        print("  no queries is a wish.\n")
    return 0


def cmd_status(args) -> int:
    doc = load(args.slug)
    if doc is None:
        print("\n  %s is not a living issue — no watch.json.\n" % args.slug)
        return 0
    n = days_since_check(doc)
    interval = int(doc.get("review_interval_days") or DEFAULT_INTERVAL_DAYS)
    print("\n  %s — %d open question(s), %d check(s), %d changelog entry/entries"
          % (args.slug,
             len([q for q in doc.get("questions", []) if q.get("status") == "open"]),
             len(doc.get("checks", [])), len(doc.get("changelog", []))))
    print("  last checked: %s"
          % ("never" if n is None else "%d day(s) ago (interval %d)" % (n, interval)))
    print()
    for q in doc.get("questions", []):
        print("   [%s] %s  %s" % (q.get("status", "?")[:6].ljust(6), q["id"],
                                  q["question"][:92]))
        if not q.get("queries"):
            print("           no queries recorded — this one cannot actually be watched")
    print()
    return 0


def cmd_check(args) -> int:
    doc = load(args.slug)
    if doc is None:
        print("\n  %s is not a living issue.\n" % args.slug)
        return 2
    if not args.searched or not args.found:
        print("\n  A check needs BOTH --searched and --found. 'Nothing new' is a")
        print("  real and valuable result, but it has to say what was searched to")
        print("  reach it — an unrun check must not look like a check that found")
        print("  nothing.\n")
        return 2
    doc.setdefault("checks", []).append({
        "on": date.today().isoformat(),
        "by": args.by,
        "questions_checked": args.question or
                             [q["id"] for q in doc.get("questions", [])
                              if q.get("status") == "open"],
        "searched": list(args.searched),
        "found": args.found,
    })
    save(args.slug, doc)
    print("\n  Recorded. The page must now say: Last reviewed %s\n"
          % pretty(date.today()))
    return 0


def cmd_entry(args) -> int:
    doc = load(args.slug)
    if doc is None:
        print("\n  %s is not a living issue.\n" % args.slug)
        return 2
    import publish as pub  # for the configured page path
    cfg = pub.ISSUES.get(args.slug)
    if not cfg:
        print("\n  %s has no page configured in publish.py.\n" % args.slug)
        return 2
    page = ROOT / cfg["page"]
    doc.setdefault("changelog", []).append({
        "on": date.today().isoformat(),
        "by": args.by,
        "what": args.what,
        "changed": args.changed,
        "source": args.source,
        "page_sha": hashlib.sha256(page.read_bytes()).hexdigest(),
    })
    save(args.slug, doc)
    print("\n  Recorded against page sha %s."
          % hashlib.sha256(page.read_bytes()).hexdigest()[:16])
    print("  Now write the reader-facing version into %s — this file is the"
          % changelog_path(args.slug).relative_to(ROOT))
    print("  record, not the page.\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="seed a watch from the premise's kill conditions")
    i.add_argument("slug"); i.add_argument("--force", action="store_true")
    i.set_defaults(fn=cmd_init)

    s = sub.add_parser("status", help="how stale is this watch")
    s.add_argument("slug"); s.set_defaults(fn=cmd_status)

    c = sub.add_parser("check", help="record that a check ran, and what it found")
    c.add_argument("slug")
    c.add_argument("--searched", action="append",
                   help="what was actually searched. Repeatable. Required.")
    c.add_argument("--found", help="what it turned up. 'nothing new' is fine. Required.")
    c.add_argument("--question", action="append", help="limit to these question ids")
    c.add_argument("--by", default="claude")
    c.set_defaults(fn=cmd_check)

    e = sub.add_parser("entry", help="record a changelog entry against the page sha")
    e.add_argument("slug")
    e.add_argument("--what", required=True, help="what appeared in the world")
    e.add_argument("--changed", required=True, help="what changed on the page")
    e.add_argument("--source", help="the new source's id in sources.json")
    e.add_argument("--by", default="claude")
    e.set_defaults(fn=cmd_entry)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
