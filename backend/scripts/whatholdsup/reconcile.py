#!/usr/bin/env python3
"""B9 — every document the page links must be a source. B8 — is there a closer one.

B9, PAGE TO LEDGER
------------------
On 2026-09-01 the published page carried eight figures from a reconstructed
patient-data comparison in Cancers 2023: its own paragraph, its own entry in the
visible source list, its own link. It had NO row in sources.json. No id, no
access record, nothing in the library, and no place in the twenty-five sources
we publish as our count.

Every control this project owns starts from sources.json, so every one of them
was blind to it: the ledger could not say who opened it, the quotation check
could not ask, the gap list could not report it missing, preflight could not
block. A source you forgot to write down is invisible to controls that begin
with the list of sources you wrote down.

So this check starts from the PAGE. Every external link in the body is a
document the page sends a reader to. If it is not in the ledger, either it is a
source we failed to record, or it is a link that should not be there.

B8, IS THERE A CLOSER SOURCE
----------------------------
The page told readers that the direction of MONALEESA-7's survival test was
stated in an ASCO conference abstract and confirmed in a registry posting. The
NEJM paper it cites says it directly: "The one-sided stratified log-rank P value
was 0.00973." The construction existed because on 29 August nobody could open
the paper, and it survived into a version where we hold it.

Nothing was false. But a reader is told the fact comes from a conference
abstract, and infers the publication did not say it. When a span is present in a
document CLOSER to the claim than the one cited, that is worth knowing.

Closeness is by kind, not by preference: the study's own publication is closer
than a conference abstract of the same analysis, which is closer than a registry
posting of it, which is closer than a label or a piece of coverage.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store  # noqa: E402
import spancheck as SC        # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# Nearest to the claim first.
# Nearest to the claim first. A press_release is a company's account of its own
# study and ranks BELOW the registry posting of that study: the registry is at
# least a structured record filed under a regulator's rules, while a release is
# written to be read a particular way. B8 must never offer one as a closer
# source than the publication.
CLOSENESS = {"primary": 0, "corrigendum": 0, "methods": 1, "comparison": 1,
             "review": 2, "conference": 3, "registry": 4, "guideline": 4,
             "label": 4, "coverage": 5, "secondary": 5, "critique": 5,
             "press_release": 6}

# ONLY ANCHORS. A stylesheet or a preconnect is not a document the page sends a
# reader to, and the first run reported Google Fonts as three missing sources on
# every page — a check crying wolf on its first output is a check that gets
# waived on its second.
HREF = re.compile(r'<a\b[^>]*\bhref="(https?://[^"]+)"', re.I)
# Our own estate, and the ordinary furniture of a web page. A link here is not a
# source and never was.
OURS = re.compile(r"whatholdsup\.org|civicscale|mailto:|/feed|/rss|"
                  r"twitter\.com|x\.com|linkedin\.com|bsky\.", re.I)

IDENT = (r"10\.\d{4,9}/[^\s?#\"]+", r"PMC\d+", r"NCT\d{8}",
         r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})")


def identifiers_in(text: str) -> set[str]:
    out = set()
    for pat in IDENT:
        for m in re.finditer(pat, text, re.I):
            out.add((m.group(1) if m.groups() else m.group(0)).rstrip(".,;)/").lower())
    return out


def page_links(page_html: str) -> list[str]:
    seen, out = set(), []
    for m in HREF.finditer(page_html):
        u = m.group(1)
        if OURS.search(u) or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def b9_unreconciled(slug: str, page_html: str) -> list[str]:
    """Links on the page that no source in the ledger accounts for."""
    srcs = store.sources(slug)
    known_urls = {(s.get("url") or "").rstrip("/").lower() for s in srcs}
    known_ids = set()
    for s in srcs:
        known_ids |= identifiers_in((s.get("url") or "") + " " +
                                    " ".join(str(v) for v in
                                             (s.get("pubmed"), s.get("doi"),
                                              s.get("nct")) if v))
    out = []
    for u in page_links(page_html):
        if u.rstrip("/").lower() in known_urls:
            continue
        if identifiers_in(u) & known_ids:
            continue
        # THE SAME DOCUMENT UNDER ANOTHER NAME. The page links the Shaaban
        # paper by its APJCP DOI while the ledger carries its PMC address. That
        # is one document with two identifiers, not a missing source, and the
        # library can tell the difference: if the linked identifier is printed
        # inside a document we already hold, it is that document.
        ident = identifiers_in(u)
        same = None
        if ident:
            for sid in sorted(store.held(slug) or {}):
                doc = SC._text(slug, sid)
                if doc and any(i in doc.lower() for i in ident):
                    same = sid
                    break
        out.append({"url": u, "same_as": same,
                    "why": ("linked by an identifier the ledger does not carry "
                            "for %s, which we hold" % same) if same else
                           "no source entry, and no held document prints this "
                           "identifier"})
    return out


def b8_closer(slug: str, span: str, cited: str) -> tuple[str | None, str]:
    """Is this span also in a document closer to the claim than the one cited?

    ONLY FOR A DISTINCTIVE SPAN. Asked about "One-sided stratified log-rank
    test", the first version cheerfully offered MONALEESA-2's paper as a closer
    source for a claim about MONALEESA-7, because that sentence is standard
    methodological wording and appears in both. A phrase that many documents
    share identifies none of them; reattributing on it would manufacture
    exactly the error B2 and B3 exist to catch.
    """
    import autobind as AB
    anchors = AB.anchors_of(span)
    strength = sum(AB.anchor_strength(a) for a in anchors)
    if strength < AB.STRONG:
        return None, ("the span carries nothing distinctive enough to identify a "
                      "document (strength %d, need %d) — a shared phrase is not "
                      "evidence of where a claim came from"
                      % (strength, AB.MIN_STRENGTH))
    srcs = {s["id"]: s for s in store.sources(slug)}
    here = CLOSENESS.get((srcs.get(cited) or {}).get("type", ""), 9)
    best = None
    for sid in sorted(store.held(slug) or {}):
        if sid == cited:
            continue
        rank = CLOSENESS.get((srcs.get(sid) or {}).get("type", ""), 9)
        if rank >= here:
            continue
        doc = SC._text(slug, sid)
        if doc and SC._norm(span).lower() in SC._norm(doc).lower():
            if best is None or rank < best[1]:
                best = (sid, rank)
    if not best:
        return None, "no closer held document contains this span"
    sid = best[0]
    return sid, ("%s (%s) also contains this span and is closer to the claim "
                 "than %s (%s)" % (sid, srcs[sid].get("type"), cited,
                                   (srcs.get(cited) or {}).get("type")))


def preflight_rows(slug: str, page_html: str = "") -> list[tuple[str, str, str]]:
    if not page_html:
        return []
    try:
        loose = b9_unreconciled(slug, page_html)
    except Exception as exc:
        return [("page to ledger", WARN, "did not run: %s" % exc)]
    if not loose:
        return [("every document the page links is a source", OK,
                 "every external link on the page is accounted for in the ledger")]
    unknown = [r for r in loose if not r["same_as"]]
    aliases = [r for r in loose if r["same_as"]]
    rows = []
    if unknown:
        rows.append(("documents the page links that the ledger does not know", BAD,
                     "%d link(s) have no source entry and no held document prints "
                     "their identifier: %s — a source nobody wrote down is "
                     "invisible to every check that starts from the source list"
                     % (len(unknown), " || ".join(r["url"] for r in unknown[:4]))))
    if aliases:
        rows.append(("sources linked under an identifier the ledger lacks", WARN,
                     "%d link(s) point at documents we hold, by a name the ledger "
                     "does not carry: %s"
                     % (len(aliases), " || ".join("%s -> %s" % (r["url"][:52],
                                                               r["same_as"])
                                                  for r in aliases[:4]))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", default="")
    args = ap.parse_args()
    if args.page:
        html = Path(args.page).read_text(encoding="utf-8")
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "pub", str(Path(__file__).resolve().parent / "publish.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        html = (m.ROOT / m.ISSUES[args.slug]["page"]).read_text(encoding="utf-8")
    print()
    for label, state, detail in preflight_rows(args.slug, html):
        print("  %-6s %-46s %s" % (state, label, detail[:120]))
    for r in b9_unreconciled(args.slug, html):
        print("      %-58s %s" % (r["url"][:58], r["why"][:60]))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
