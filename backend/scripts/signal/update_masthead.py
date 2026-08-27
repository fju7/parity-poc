"""
Rewrite the masthead's stability sentence from the latest sweep.

WHY THIS EXISTS
---------------
"Who Pays for This" carries a specific, checkable claim: on such-and-such a
date we re-ran every published assessment, this many still matched, this many
did not. It is the strongest sentence on the page and the only one that decays
on its own — the sweep runs, the numbers move, and the page keeps asserting
last week's figure with last week's date.

Being dated makes it defensible rather than false. It does not make it useful.
A publication whose headline honesty claim is quietly out of date is running
the same failure it was written to admit.

So the sentence is generated, not typed. The page keeps a marked region:

    <!-- STABILITY:BEGIN --> ... <!-- STABILITY:END -->

and this replaces what is between the markers. No build step, no runtime
JavaScript, no dependency at page load — the number is baked in at publish
time and is true as of the date printed beside it.

THE STALENESS GUARD
-------------------
The page also implies a cadence. If the newest sweep is older than --max-age
days, that implication is false and this exits non-zero, because a page
claiming a weekly check backed by a three-week-old measurement is worse than
one claiming nothing.

Usage:
    cd backend && source venv/bin/activate

    python scripts/signal/update_masthead.py --check     # report only, exit 1 if stale or out of date
    python scripts/signal/update_masthead.py             # rewrite the page
    python scripts/signal/update_masthead.py --max-age 14
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SWEEP = ROOT / "backend" / "data" / "signal" / "stability_sweep.json"
PAGE = ROOT / "site" / "whatholdsup" / "who-pays-for-this.html"
BEGIN, END = "<!-- STABILITY:BEGIN", "<!-- STABILITY:END -->"

ONES = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven",
        8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve"}


def words(n: int, spell: bool) -> str:
    """Spell out only when both numbers in the pair can be spelled out.
    'Forty-seven still match. Five do not.' reads well; so does
    '46 still match. 7 do not.' Mixing them does not."""
    return ONES[n] if spell and n in ONES else f"{n:,}"


def sentence(total: int, agree: int, drift: int, when: date) -> str:
    when_s = f"{when.day} {when:%B %Y}"
    spell = agree in ONES and drift in ONES
    if drift == 0:
        tail = "Every one still matches."
    elif drift == 1:
        tail = f"{words(agree, spell)} still match. {'One' if spell else '1'} does not."
    else:
        tail = f"{words(agree, spell)} still match. {words(drift, spell)} do not."
    return (f'<p class="lede">On {when_s} we checked all {total} published assessments '
            f'against what our own method produces today. {tail}</p>')


def main() -> None:
    ap = argparse.ArgumentParser(description="Regenerate the masthead stability sentence.")
    ap.add_argument("--check", action="store_true", help="Report only. Exit 1 if the page is out of date or the sweep is stale.")
    ap.add_argument("--max-age", type=int, default=10, help="Days before the sweep itself is considered stale (default 10).")
    ap.add_argument("--sweep", default=str(SWEEP))
    ap.add_argument("--page", default=str(PAGE))
    args = ap.parse_args()

    sweep_path, page_path = Path(args.sweep), Path(args.page)
    if not sweep_path.exists():
        sys.exit(f"[ERROR] No sweep at {sweep_path}. Run stability_sweep.py first.")
    if not page_path.exists():
        sys.exit(f"[ERROR] No page at {page_path}.")

    report = json.loads(sweep_path.read_text())
    rows = report.get("results", [])
    if not rows:
        sys.exit("[ERROR] The sweep has no results. Refusing to publish a figure from an empty run.")

    total = len(rows)
    agree = sum(1 for r in rows if r.get("agrees"))
    drift = total - agree

    mtime = datetime.fromtimestamp(sweep_path.stat().st_mtime).date()
    age = (date.today() - mtime).days
    print(f"sweep    : {sweep_path.name}, {mtime.isoformat()} ({age} day{'' if age == 1 else 's'} old)")
    print(f"measured : {total} categories — {agree} agree, {drift} drifted")

    page = page_path.read_text(encoding="utf-8")
    i, j = page.find(BEGIN), page.find(END)
    if i == -1 or j == -1 or j < i:
        sys.exit(f"[ERROR] No STABILITY:BEGIN/END markers in {page_path.name}. "
                 "Add them around the sentence so it can be generated.")

    block = page[i:j + len(END)]
    new_line = sentence(total, agree, drift, mtime)
    current = re.search(r'<p class="lede">.*?</p>', block, re.S)
    unchanged = bool(current) and current.group(0) == new_line

    print(f"\nwould read: {new_line}")

    stale = age > args.max_age
    if stale:
        print(f"\n[STALE]  The newest sweep is {age} days old, past the {args.max_age}-day limit.")
        print("         The page implies a regular check. Run stability_sweep.py before publishing this.")

    if args.check:
        if unchanged and not stale:
            print("\nPage is current.")
            return
        if not unchanged:
            print("\n[OUT OF DATE] The page does not match the latest sweep.")
        sys.exit(1)

    if stale:
        sys.exit(1)
    if unchanged:
        print("\nAlready correct. Nothing written.")
        return

    head = block[:block.index("-->") + 3]
    page_path.write_text(page[:i] + head + "\n  " + new_line + "\n  " + END + page[j + len(END):],
                         encoding="utf-8")
    print(f"\nRewrote {page_path.name}. Commit and push to publish it.")


if __name__ == "__main__":
    main()
