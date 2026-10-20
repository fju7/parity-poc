#!/usr/bin/env python3
"""Did changecheck read every body sentence changed since the first full draft? (RUN.md 9a)

    changecheck_coverage.py SLUG --first <the step-3b commit>

Study ruling 5 (advisor, 2026-10-20): after the final changecheck, a script
confirms that changecheck read every body sentence changed since the first full
draft, and reports any it missed. This is that script.

THE CHANGED SENTENCES are changecheck's own: changecheck.changed(the page at
--first, the page now), so the same body-only reading, the same sentence
splitting, the same normalisation. A sentence changecheck withheld is changed
and unread.

THE READ SET is the union, across every run recorded in change-reviews.json, of
the fingerprints changecheck recorded as read (`read`, since 2026-10-20) in runs
where a model read them (`model_read`). A run recorded before `read` existed, or
with --no-model, contributes nothing and is counted.

Exit 1 when any changed sentence is missing from the read set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def read_set(reviews: dict) -> tuple[set[str], int]:
    """(fingerprints read by a model, runs that contributed nothing)."""
    got, blind = set(), 0
    for r in reviews.get("reviews") or []:
        if "read" not in r or r.get("model_read") is False:
            blind += 1
            continue
        got.update(r["read"])
    return got, blind


def check(first_html: str, now_html: str, reviews: dict) -> dict:
    import changecheck as C
    sent, withheld = C.changed(first_html, now_html)
    changed_now = sent + [w["sentence"] for w in withheld]
    got, blind = read_set(reviews)
    missed = [s for s in changed_now if C.fingerprint(s) not in got]
    return {"changed": len(changed_now), "read_runs": len(reviews.get("reviews") or []) - blind,
            "runs_without_a_read_set": blind, "missed": missed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--first", required=True, help="the step-3b commit: the first full draft")
    a = ap.parse_args(argv)
    import publish as P
    import changecheck as C
    if not P.is_study(a.slug):
        raise SystemExit("%s is not a study issue (issue.json \"study\": true)" % a.slug)
    page = P.issue_cfg(a.slug)["page"]
    first = C.at(a.first, page)
    if not first:
        raise SystemExit("could not read %s at %s" % (page, a.first))
    now = (P.ROOT / page).read_text(encoding="utf-8")
    res = check(first, now, C.load_reviews(a.slug))
    print("\n  %d body sentence(s) changed since %s; changecheck runs with a read set: %d "
          "(%d without one)" % (res["changed"], a.first, res["read_runs"], res["runs_without_a_read_set"]))
    for s in res["missed"]:
        print("  MISSED  %s" % s[:140])
    print("  %s\n" % ("every changed sentence was read" if not res["missed"]
                      else "%d changed sentence(s) changecheck never read" % len(res["missed"])))
    return 1 if res["missed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
