#!/usr/bin/env python3
"""B17 — the displayed source list must be the documents the piece rests on.

WHY
---
The melanoma page told readers: "Every number above traces to one of these,
and none to a news report -- a check that runs before this page can publish
refuses it otherwise."

No such check existed. B9 runs the other way: it takes every LINK on the page
and asks whether the ledger accounts for it. Nothing took the sources the
BINDINGS name and asked whether the reader can see them. On 2026-09-04 an
outside reviewer found the gap, and it was not one missing source: thirteen of
the twenty-two documents the piece rests on were absent from the list a reader
is shown, including the ASCO abstract that is the only source for the
five-year landmark rates the piece prints.

So the page advertised a control that did not exist, in the same sentence that
asked the reader to trust the list. That is worse than having no control: a
reader who checks our sources is entitled to assume the check we describe ran.

WHAT IT CHECKS
--------------
Two directions, because either alone can be satisfied by a list that lies.

  shown_but_unused  a document in the list that no on-page sentence rests on.
                    Not a defect on its own -- a piece may list background it
                    read and did not use -- so this is a WARN.
  used_but_unshown  a document an on-page sentence rests on that the reader
                    cannot see. This is the defect, and it BLOCKS.

Matching is by URL, because that is what the reader actually has: an entry
whose link does not resolve to a source in the ledger is invisible to a reader
trying to follow a figure back, whatever its title says.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bindings as B          # noqa: E402
import source_store as store  # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"
SOURCES_BLOCK = re.compile(r'<div class="sources">(.*?)\n\s*</div>\s*</section>', re.S)
LINK = re.compile(r'<a href="([^"]+)"')


def _norm(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def shown(page_html: str) -> set[str]:
    m = SOURCES_BLOCK.search(page_html)
    if not m:
        return set()
    return {_norm(u) for u in LINK.findall(m.group(1))}


def rested_on(slug: str) -> dict[str, set[str]]:
    """source_id -> the on-page sentences that rest on it."""
    out: dict[str, set[str]] = {}
    for row in B.load(slug).get("bindings", {}).values():
        if not row.get("on_page"):
            continue
        ids = {row["source_id"]} if row.get("source_id") else set()
        ids |= {p["source_id"] for p in (row.get("premises") or [])}
        for sid in ids:
            out.setdefault(sid, set()).add(" ".join(row["sentence"].split()))
    return out


def preflight_rows(slug: str, page_html: str) -> list[tuple[str, str, str]]:
    block = SOURCES_BLOCK.search(page_html)
    if not block:
        return [("the source list a reader sees", BAD,
                 "no <div class=\"sources\"> block on the page — a reader has no "
                 "list at all, and an unrun check is not a pass")]

    seen = shown(page_html)
    by_id = {s["id"]: s for s in store.sources(slug)}
    url_of = {sid: _norm(s.get("url") or "") for sid, s in by_id.items()}
    used = rested_on(slug)

    unshown = sorted(sid for sid in used
                     if url_of.get(sid) and url_of[sid] not in seen)
    shown_ids = {sid for sid, u in url_of.items() if u and u in seen}
    unused = sorted(shown_ids - set(used))

    rows = [("every document the piece rests on is in the list a reader sees",
             OK if not unshown else BAD,
             "all %d document(s) the bindings name are in the source list"
             % len(used) if not unshown else
             "%d document(s) carry sentences on this page and are NOT in the "
             "list a reader sees: %s"
             % (len(unshown), ", ".join(
                 "%s (%d sentence(s): %s…)"
                 % (sid, len(used[sid]), sorted(used[sid])[0][:60])
                 for sid in unshown)))]
    rows.append(("the list a reader sees carries nothing unused",
                 OK if not unused else WARN,
                 "every listed document is one the piece rests on"
                 if not unused else
                 "%d listed document(s) support no sentence on the page: %s. "
                 "Not wrong — a piece may list what it read — but the list "
                 "should say so rather than implying every entry is load-bearing."
                 % (len(unused), ", ".join(unused))))
    return rows


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "melanoma"
    page = B.page_html(slug) if hasattr(B, "page_html") else None
    if page is None:
        import review_packet as RP
        page = RP.page_html()
    bad = 0
    print()
    for name, state, detail in preflight_rows(slug, page):
        print("  %-8s %s\n           %s\n" % (state, name, detail))
        bad += state == BAD
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
