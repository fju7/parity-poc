#!/usr/bin/env python3
"""Let a model propose the span. Let the machine decide whether it exists.

WHY A MODEL AT ALL
------------------
The deterministic binder is at its ceiling. On issue two it binds twelve of a
hundred and fifty-three sentences, and the rest are out of its reach for honest
reasons: their anchors are two loose decimals that identify nothing, or they
rest on sources nobody holds, or the numbers in them are this page's own
arithmetic. Searching harder will not fix that. Reading will.

WHY THIS IS SAFE, WHEN "ASK A MODEL" HAS BEEN THE ERROR ALL DAY
---------------------------------------------------------------
Every error this repository recorded on 2026-09-01 came from a model's PROSE
ABOUT a source being treated as evidence: a correction written from a gate
finding rather than from the paper, an attribution taken from a search result,
a figure carried under the wrong byline.

A proposal here is not prose. It is a claim of the form "this exact string is in
this document", and that claim is decided by string equality against the bytes,
not believed. A model that invents a span fails B2 and the proposal is dropped
with nothing recorded. A model that finds a real one has done the only part of
the job it is better at than a regular expression: reading a sentence and
knowing which paragraph of a paper it came from.

So the division is: the model searches, the machine decides, and the record
carries which. Every accepted row is proposed_by "model", confirmed false, and
still needs the faithfulness signature that no automatic step can give.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store  # noqa: E402
import spancheck as SC        # noqa: E402
import bindings as B          # noqa: E402
import autobind as AB         # noqa: E402


def task(slug: str, limit: int = 40) -> dict:
    """The sentences that need a binding, and the documents available."""
    doc = B.load(slug)
    rows = doc.get("bindings") or {}
    want = []
    for sha, r in rows.items():
        if not r.get("on_page") or r.get("span"):
            continue
        if r.get("locator_type") == "none":       # our own arithmetic
            continue
        if AB.shape_of(r["sentence"]):            # arithmetic / about-a-document
            continue
        want.append({"sha": sha, "sentence": r["sentence"]})
        if len(want) >= limit:
            break
    srcs = []
    for s in store.sources(slug):
        if s["id"] in (store.held(slug) or {}):
            srcs.append({"id": s["id"], "type": s.get("type"),
                         "title": (s.get("title") or "")[:150]})
    return {"slug": slug, "sentences": want, "held_sources": srcs}


# WHAT COUNTS AS SUBJECT MATTER
# -----------------------------
# The first guard counted words of five letters or more and nothing else. On its
# first run at scale it rejected seven of nine melanoma proposals that were
# right: the sentence "the interval runs from 0.165 to 1.345" and the passage
# "the OS HR (95% CI) was 0.471 (0.165 to 1.345)" have, by that measure, nothing
# in common. For a sentence about a figure, THE FIGURE IS THE SUBJECT MATTER,
# and it is more distinctive than any word in either text.
#
# So a shared figure earns points on the same scale as a shared word, and the
# threshold does not move: two independent pieces of evidence, whatever kind.
# Years are excluded -- two documents about the same trial share "2023" for
# reasons that say nothing -- and so are bare one- and two-digit integers, which
# is what kept the RECIST passage ("20%", "30%", "5 mm") from being accepted as
# evidence for a sentence about p-values.

WORD = 2          # a content word in common
FIGURE = 2        # a figure in common
DISTINCTIVE = 4   # a decimal carrying four significant digits: 1.017, 0.0266
ENOUGH = 4        # unchanged: two words, or one four-digit decimal, or a pair

_NUM = re.compile(r"(?<![A-Za-z0-9.])\d{1,3}(?:,\d{3})*(?:\.\d+)?(?![0-9])")


def figures(t: str) -> set[str]:
    """Numbers as they compare ACROSS documents: middle dots and thousands
    separators normalised away, so the Lancet's 0(mid-dot)561 meets our 0.561.
    """
    return {m.group(0).replace(",", "") for m in _NUM.finditer(SC._norm(t))}


def _weight(fig: str) -> int:
    digits = fig.replace(".", "").lstrip("0")
    if "." not in fig:
        if len(digits) == 4 and 1900 <= int(digits) <= 2099:
            return 0                     # a year is not evidence
        return FIGURE if len(digits) >= 3 else 0
    return DISTINCTIVE if len(digits) >= 4 else FIGURE


def relevance(sentence: str, span: str) -> tuple[int, str]:
    """How much this span and this sentence are about the same thing."""
    words = AB.content_words(sentence) & AB.content_words(span)
    figs = {f: _weight(f) for f in (figures(sentence) & figures(span))}
    figs = {f: w for f, w in figs.items() if w}
    score = WORD * len(words) + sum(figs.values())
    return score, "%d word(s) and %d figure(s) in common" % (
        len(words), len(figs))


def accept(slug: str, proposals: list[dict]) -> dict:
    """Record only the proposals whose span is actually in the document named.

    THE WHOLE SAFETY PROPERTY IS HERE. A proposal is a hypothesis; B2 is the
    test; nothing that fails is written.
    """
    doc = B.load(slug)
    rows = doc.get("bindings") or {}
    out = {"accepted": 0, "rejected": [], "unknown_row": 0, "undetermined": 0}
    for p in proposals:
        sha, sid, span = p.get("sha"), p.get("source_id"), (p.get("span") or "")
        row = rows.get(sha)
        if row is None:
            out["unknown_row"] += 1
            continue
        if not sid or not span:
            out["rejected"].append((sha, "no source or no span offered"))
            continue
        present, why = SC.b2_present(span, slug, sid)
        if present is SC.UNDETERMINED:
            out["undetermined"] += 1
            out["rejected"].append((sha, "undetermined: %s" % why[:60]))
            continue
        if present is not True:
            out["rejected"].append(
                (sha, "the proposed span is not in %s" % sid))
            continue
        # B2 CONFIRMS EXISTENCE, NOT RELEVANCE — and within minutes of this
        # harness being built, a hand-made proposal bound a sentence about
        # one-sided p-values to a passage defining RECIST progression. The
        # string was really in the document; it was about something else.
        # autobind has carried this guard since its own first run bound an
        # argument about p-values to a table of patient ages. The model path
        # must not be weaker than the deterministic one.
        score, why_rel = relevance(row["sentence"], span)
        if score < ENOUGH:
            out["rejected"].append(
                (sha, "the span is in %s but shares too little subject matter "
                      "with the sentence (%s)" % (sid, why_rel)))
            continue
        text = SC._text(slug, sid) or ""
        i = SC._norm(text).lower().find(SC._norm(span).lower())
        env = SC._norm(text)[max(0, i - 220):i + len(span) + 220]
        row.update(source_id=sid, span=span[:1200], envelope=env[:2000],
                   locator_type=p.get("locator_type") or "prose",
                   document_sha=(store.held(slug).get(sid) or {}).get("sha256"),
                   proposed_by="model", confirmed=False,
                   proposed_on=date.today().isoformat(),
                   why_bound="a model proposed this span and B2 confirmed the "
                             "string is in %s; nobody has yet signed that the "
                             "sentence is warranted by it" % sid)
        out["accepted"] += 1
    B.save(slug, doc)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("task", help="print the sentences needing a binding")
    t.add_argument("--limit", type=int, default=40)
    a = sub.add_parser("accept", help="read proposals as JSON on stdin")
    args = ap.parse_args()

    if args.cmd == "task":
        print(json.dumps(task(args.slug, args.limit), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "accept":
        props = json.loads(sys.stdin.read())
        res = accept(args.slug, props if isinstance(props, list)
                     else props.get("proposals", []))
        print("\n  %d accepted, %d rejected, %d undetermined, %d unknown row(s)"
              % (res["accepted"], len(res["rejected"]), res["undetermined"],
                 res["unknown_row"]))
        for sha, why in res["rejected"][:12]:
            print("    rejected %s — %s" % (sha[:10], why))
        print()
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
