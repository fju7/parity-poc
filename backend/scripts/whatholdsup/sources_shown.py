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

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bindings as B          # noqa: E402
import source_store as store  # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"
# The three issues do not agree on the class name: melanoma and cdk46 use
# "sources", deskilling uses "srclist". The first version of this looked only
# for "sources" and reported deskilling as having no source list at all, which
# is a check whose reach is narrower than its own claim -- the failure this
# whole file exists to catch, committed inside the fix for it. Both names, and
# the BLOCK message says which it looked for.
SOURCES_CLASSES = ("sources", "srclist")
SOURCES_BLOCK = re.compile(
    r'<div class="(?:%s)">(.*?)\n\s*</div>\s*</section>' % "|".join(SOURCES_CLASSES),
    re.S)
LINK = re.compile(r'<a href="([^"]+)"')


def _norm(url: str) -> str:
    return (url or "").strip().rstrip("/").lower()


def shown(page_html: str) -> set[str]:
    m = SOURCES_BLOCK.search(page_html)
    if not m:
        return set()
    return {_norm(u) for u in LINK.findall(m.group(1))}


def rested_on(slug: str) -> dict[str, set[str]]:
    """source_id -> the on-page sentences and quotations that rest on it.

    BINDINGS ARE NOT THE ONLY WAY A PAGE RESTS ON A DOCUMENT. The first version
    of this read only bindings, said all 22 documents were in the list, and was
    wrong twice: S008 supplies the quoted words "1-sided alpha of 0.1 per
    protocol", and S015 supplies three quoted passages including the five-year
    landmark rates -- and neither was in the list a reader sees. A quotation is
    the strongest possible dependence on a document, because the page puts that
    document's words inside quotation marks, and it was the one this check
    could not see. Found the same afternoon the check was written, by the same
    question asked one layer down.
    """
    out: dict[str, set[str]] = {}
    for row in B.load(slug).get("bindings", {}).values():
        if not row.get("on_page"):
            continue
        ids = {row["source_id"]} if row.get("source_id") else set()
        ids |= {p["source_id"] for p in (row.get("premises") or [])}
        for sid in ids:
            out.setdefault(sid, set()).add(" ".join(row["sentence"].split()))
    case = store.case_dir(slug)
    qf = (case / "quotations.json") if case else None
    if qf and qf.exists():
        try:
            rows = json.loads(qf.read_text(encoding="utf-8")).get("quotations", [])
        except Exception:
            rows = []
        for r in rows:
            sid = r.get("source_id")
            if sid:
                out.setdefault(sid, set()).add(
                    "quoted: %s" % " ".join((r.get("quote") or "").split())[:120])
    return out


def preflight_rows(slug: str, page_html: str) -> list[tuple[str, str, str]]:
    block = SOURCES_BLOCK.search(page_html)
    if not block:
        return [("the source list a reader sees", BAD,
                 "no source list on the page: looked for a <div> of class %s. "
                 "A reader has no list at all, and an unrun check is not a pass"
                 % " or ".join(SOURCES_CLASSES))]

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
    # THE SLUG MUST PICK THE PAGE. The first version of this asked bindings for
    # a `page_html` it does not have (the function is `_page_html`), so the
    # hasattr test failed silently and every slug fell back to review_packet,
    # which is hardcoded to melanoma. Running it against cdk46 read melanoma's
    # HTML with cdk46's bindings and reported twelve missing documents that are
    # not missing. A check pointed at the wrong document is not a check.
    slug = sys.argv[1] if len(sys.argv) > 1 else "melanoma"
    page = B._page_html(slug)
    bad = 0
    print()
    for name, state, detail in preflight_rows(slug, page):
        print("  %-8s %s\n           %s\n" % (state, name, detail))
        bad += state == BAD
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
