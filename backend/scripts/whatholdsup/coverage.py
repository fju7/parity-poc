#!/usr/bin/env python3
"""What each check did NOT examine — reported as a number, next to its findings.

WHY
---
On 2026-09-01 the substance test — the check this project was built around,
the one that says identity is not substance — was not running on eighteen of
the nineteen documents held for a live issue. Nothing was broken. substance()
is scoped by an ARTICLE_TYPES allow-list, issue three's vocabulary (synthesis,
critique, prior_art, carrier, secondary, editorial) is not in that list, and
everything outside the list was recorded as "a complete document of its own
kind" without anything looking at it. Two of those documents turned out to be
2.7 KB Elsevier redirect stubs holding eleven characters of text, both marked
full_text_held, both on a page readers can see.

The check found nothing wrong because the check never ran. Its output said so
in no way at all.

THE RULE THIS FILE ENFORCES
---------------------------
A check reports THREE things, never one: what it examined, what it did not
examine, and why not. A finding of zero problems from a check that examined
zero things must not read like a finding of zero problems.

Every allow-list in this repository has been wrong within a day of being
written — the wall blocklist, ARTICLE_TYPES twice, the errata type list,
CLOSENESS. The lists will keep being wrong, because they are built from the
nouns we have met. What can be fixed is that being wrong stops being silent.

AND: AN UNDECLARED TYPE IS A DEFECT
-----------------------------------
The same argument as undefined_states in source_ledger, which found forty-four
sources on two live pages carrying a state the ledger no longer defined. A
source type decides which tests apply, so a type nobody declared is a source
that quietly opts out of them. Declaring one is two lines. Not declaring one
costs what it cost tonight.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store  # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# The registry lives in source_store, beside the test it governs.
TYPES = store.TYPES


def undeclared_types(slug: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for s in store.sources(slug):
        t = s.get("type")
        if t and t not in TYPES:
            out.setdefault(t, []).append(s.get("id", "?"))
    return out


def substance_coverage(slug: str) -> dict:
    """Which held documents the article test actually examined."""
    types = {s["id"]: s.get("type", "") for s in store.sources(slug)}
    lib = store.held(slug) or {}
    article, floor_only, unknown = [], [], []
    for sid in sorted(lib):
        t = types.get(sid, "")
        src = next((x for x in store.sources(slug) if x["id"] == sid), {})
        form = store.form_of(src)
        if form == "article":
            article.append(sid)
        elif form is None:
            unknown.append(sid)
        elif t in TYPES:
            floor_only.append(sid)
        else:
            unknown.append(sid)
    return {"held": len(lib), "article_test": article,
            "length_floor_only": floor_only, "type_unknown": unknown}


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    rows = []
    try:
        und = undeclared_types(slug)
        cov = substance_coverage(slug)
    except Exception as exc:
        return [("check coverage", WARN, "did not run: %s" % exc)]

    if und:
        rows.append(("source types nobody declared", BAD,
                     "%d type(s) are not declared in coverage.TYPES, so nothing "
                     "decides which tests apply to them: %s — a type nobody "
                     "declared is a source that quietly opts out"
                     % (len(und), "; ".join("%s (%s)" % (t, ", ".join(v[:4]))
                                            for t, v in und.items()))))

    held = cov["held"]
    art, floor = len(cov["article_test"]), len(cov["length_floor_only"])
    if held:
        state = OK if art == held else WARN
        rows.append(("documents the article test examined", state,
                     "%d of %d held document(s). %d were checked only against a "
                     "length floor because their kind does not carry an "
                     "article's furniture%s"
                     % (art, held, floor,
                        "" if not cov["type_unknown"] else
                        ", and %d are UNDETERMINED — their type does not settle "
                        "whether they are journal articles and they declare no "
                        "form, so NO substance test has run on them: %s"
                        % (len(cov["type_unknown"]),
                           ", ".join(cov["type_unknown"][:8])))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?", default="")
    args = ap.parse_args()
    slugs = [args.slug] if args.slug else ["melanoma", "cdk46", "deskilling"]
    for slug in slugs:
        print("\n### %s" % slug)
        for label, state, detail in preflight_rows(slug):
            print("  %-7s %-38s %s" % (state, label, detail[:150]))
        cov = substance_coverage(slug)
        if cov["length_floor_only"]:
            print("      length floor only: %s"
                  % ", ".join(cov["length_floor_only"]))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
