#!/usr/bin/env python3
"""Which claims still need the paid gate: the ones the free checks cannot decide.

WHY
---
Phase B (16 October 2026, T01) spent $4.63 on eighteen calls. Its one real
error was a wording claim (T01 s80), which B22 now catches for nothing. Of its
fourteen figure findings none was a wrong value, and every figure in the four
test issues is in the held text of the source it is bound to. A model with web
search, asked to find a figure we already hold, is paying to read a document
we have already read -- and it was wrong more often than it was right
(PHASE_B.md: A1-A3 and I6 confidently false).

So the default gate asks the model only what the free checks cannot answer:
a figure or a quotation whose evidence the checks cannot read -- its source is
fragment_only, blocked or not_opened, its held text has a defective layer, or
the span is in no held text we could search. That is spancheck.b2_present's
UNDETERMINED, the third answer rule 1 already counts as "covered on the
binder's word, reported separately".

WHAT IS NOT SELECTED, AND WHY
-----------------------------
  * a figure in a span that IS in its held document: rule 1, B12, B13 and the
    rounding note settle it;
  * a figure in no span at all, or a span not in its held document: rule 1
    BLOCKS it already -- a free STOP is not sent to a paid reader;
  * a sentence with no binding row: rule 1's backlog row reports it;
  * a quotation whose source is held: quotations.py reads it against the bytes,
    and blocks if it is not there;
  * a `figure` row (attested by a named person) and any source whose licence
    forbids machine reading: nothing automated may read those (spec section 7).

Writes nothing. Reads bindings.json, sources.json, quotations.json and the held
library.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store      # noqa: E402
import bindings as B              # noqa: E402
import figure_text as FT          # noqa: E402

UNREAD_STATES = ("fragment_only", "blocked", "not_opened")


def _state(src: dict) -> str:
    a = src.get("access")
    return (a.get("state") if isinstance(a, dict) else a) or "not_opened"


def _in_span(fig: str, span: str) -> bool:
    import modelbind as MB
    import spancheck as SC
    s = SC._norm(span)
    figs = MB.figures(s) | MB.figures(FT.comma_grouped(s))
    return (B._as_numbers([fig]) <= B._as_numbers(figs) or B._bare_integer_in(fig, s)
            or any(FT.rounds_to(h, fig) for h in figs))


def select(slug: str, page_text: str | None = None) -> dict:
    """{"claims": [...], "considered": n, "excluded": [...]}.

    Each claim has the shape audit_sources() takes -- id, figure, claim,
    attributed_to, scope "external" -- plus why it is undetermined, so the paid
    role receives these claims and nothing else.

    Figures come from the binding rows. Quotations come from quotations.json,
    the record quotations.py checks, restricted to the passages quoted on
    `page_text` when it is given.
    """
    import modelbind as MB
    import spancheck as SC
    rows = {k: v for k, v in (B.load(slug).get("bindings") or {}).items()
            if v.get("on_page")}
    srcs = {s["id"]: s for s in store.sources(slug)}
    names = B.trial_names(list(srcs.values()))
    claims, excluded, considered = [], [], 0

    def label(sid):
        s = srcs.get(sid) or {}
        return "%s: %s" % (sid, s.get("title") or s.get("url") or "untitled")

    def licensed_out(sid):
        return bool((srcs.get(sid) or {}).get("licence_forbids_machine_reading"))

    for sha, row in rows.items():
        sent = row.get("sentence") or ""
        figs = sorted(f for f in B._claim_figures(FT.comma_grouped(sent), names)
                      if MB._weight(f))
        if not figs:
            continue
        considered += 1
        if (row.get("bucket") or "") == "figure":
            excluded.append({"sentence_sha": sha, "why": "attested figure row"})
            continue
        cover = B.covering_spans(row)
        reads = [(sid, span, SC.b2_present(span, slug, sid)) for sid, span in cover]
        undet = [(sid, span, why) for sid, span, (ok, why) in reads
                 if ok is SC.UNDETERMINED]
        held_spans = [span for sid, span, (ok, _) in reads if ok is True]
        if not cover:
            # Unbound. Only a cited source we cannot read makes it a paid
            # question; otherwise rule 1's backlog row already owns it.
            undet = [(sid, "", "%s is %s" % (sid, _state(srcs[sid])))
                     for sid in B.support_ids(row)
                     if sid in srcs and _state(srcs[sid]) in UNREAD_STATES]
        if not undet:
            continue
        for f in figs:
            if any(_in_span(f, s) for s in held_spans):
                continue                # a held span settles it
            for sid, span, why in undet:
                if span and not _in_span(f, span):
                    continue
                if licensed_out(sid):
                    excluded.append({"sentence_sha": sha, "source_id": sid,
                                     "why": "licence forbids machine reading"})
                    break
                claims.append({
                    "id": "n%d" % (len(claims) + 1), "figure": f, "claim": sent,
                    "attributed_to": label(sid), "scope": "external",
                    "sentence_sha": sha, "source_id": sid,
                    "access": _state(srcs.get(sid) or {}),
                    "undetermined_because": why[:240]})
                break

    import quotations as Q
    on_page = None
    if page_text is not None:
        on_page = {Q.norm(q) for q in Q.extract(page_text)}
    held = set(store.held(slug) or {})
    for r in Q._records(Q.load(slug) or {}):
        q, sid = r.get("quote") or "", r.get("source_id") or ""
        if not q or r.get("kind") == "rhetorical":
            continue
        if on_page is not None and Q.norm(q) not in on_page:
            continue
        considered += 1
        if sid in held:
            continue                    # quotations.py reads it against the bytes
        if not sid or sid not in srcs:
            # quotations.py already BLOCKS a quotation that names no source in
            # sources.json ("nothing recorded as the source's wording"); a free
            # STOP is not sent to a paid reader, which could only guess a source.
            excluded.append({"quotation": r.get("id"), "source_id": sid,
                             "why": "no source recorded; quotations.py blocks it"})
            continue
        if licensed_out(sid):
            excluded.append({"quotation": r.get("id"), "source_id": sid,
                             "why": "licence forbids machine reading"})
            continue
        claims.append({
            "id": "n%d" % (len(claims) + 1), "figure": "“%s”" % q,
            "claim": "quoted on the page as the words of %s" % sid,
            "attributed_to": label(sid),
            "scope": "external", "quotation_id": r.get("id"), "source_id": sid,
            "quote_key": Q.norm(q),
            "access": _state(srcs.get(sid) or {}),
            "undetermined_because": "%s is not held, so the quotation cannot be "
                                    "matched against its bytes" % (sid or "no source")})
    return {"claims": claims, "considered": considered, "excluded": excluded}


def page_state(slug: str, page_text: str) -> dict:
    """What a gate run saw of the page, so a later run can tell what changed:
    the fingerprint of every page sentence (bindings.page_sentences, the keys
    binding rows use) and every quotation on it (quotations.norm)."""
    import quotations as Q
    return {"sentence_shas": sorted({B.fingerprint(x) for x in B.page_sentences(slug)}),
            "quotations": sorted({Q.norm(q) for q in Q.extract(page_text)})}


def changed(prior: dict, now: dict) -> tuple[set, set]:
    """(sentence fingerprints, quotations) on the page NOW and not in PRIOR."""
    return (set(now.get("sentence_shas") or []) - set(prior.get("sentence_shas") or []),
            set(now.get("quotations") or []) - set(prior.get("quotations") or []))


def only_changed(claims: list[dict], sentences: set, quotations: set) -> list[dict]:
    """The claims about a changed sentence or a new quotation."""
    return [c for c in claims
            if (c.get("sentence_sha") in sentences) or (c.get("quote_key") in quotations)]


def main() -> int:
    import json
    if len(sys.argv) != 2:
        print("usage: narrow_gate.py <slug>")
        return 2
    print(json.dumps(select(sys.argv[1]), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
