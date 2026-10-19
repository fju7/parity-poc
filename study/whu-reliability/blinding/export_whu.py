#!/usr/bin/env python3
"""Export a WHU page as the tools' answers look: sentences with [n] markers.

Blinding ruling (19 October 2026): "WHU's export adds [n] markers from its
bindings, in the same style as the tools' answers. This is done by script
from stored data, not by rewording."

Usage:
    export_whu.py SLUG [SLUG ...] --out DIR

For each slug writes DIR/<slug>.export.txt (paragraphs, each sentence followed
by its markers, then a numbered reference list of citation and URL) and
DIR/<slug>.sentences.jsonl (one row per sentence: text with markers, the
binding row sha, the sources, the section it sits in, and whether it may be
sampled).

WHERE THE MARKERS COME FROM. A sentence is split exactly as bindings.py splits
the page (ledger.sentences over ledger.plain), so its fingerprint is the key
of its row in bindings.json. Its sources are the row's source_id, then each
also_rests_on source, then each premise's source, in that order, keeping only
ids sources.json lists. References are numbered in order of first citation,
which is how the tools' answers number theirs. A sentence with no bound
source gets no marker; nothing is guessed.

The markers go before the sentence's closing punctuation ("… adopted it
[1][2]."), the commonest placement in the pilot's converted Claude answers.

WHAT IS NOT SAMPLABLE (blinding ruling, "Process sentences are not sampled").
The watch section and the change history (the footer, which this export drops
as page furniture) are excluded whole; any other sentence is excluded if
blind.process_reason() says it is about how the answer was made. The same
function is applied to every system's answers (blind.py --sentences).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
sys.path.insert(0, str(HERE))
import bindings as B  # noqa: E402
import source_ledger as ledger  # noqa: E402
import blind  # noqa: E402

BLOCK = re.compile(r"<(p|li|blockquote|td|th|dd|figcaption)\b([^>]*)>(.*?)</\1>", re.S | re.I)
# Not sampled (ruling of 19 October 2026, prep round 2): chart descriptions and
# rubric scores are WHU's own judgements, not claims about a source. A chart
# caption is p.ci-cap or a figcaption; the scorecard and anything else the page
# generates about itself carries data-whu (furniture.py's mark).
CHART_CLASSES = ("ci-cap",)


def marked_regions(html: str) -> list[tuple[int, int, str]]:
    """(start, end, mark) for every element carrying data-whu, its whole subtree."""
    out = []
    for m in re.finditer(r'<([a-zA-Z][\w-]*)\b[^>]*\bdata-whu="([^"]+)"[^>]*>', html):
        tag, depth, pos = m.group(1).lower(), 1, m.end()
        for t in re.finditer(r"<(/?)%s\b[^>]*>" % tag, html[pos:], re.I):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                out.append((m.start(), pos + t.end(), m.group(2)))
                break
    return out
SECTION = re.compile(r'<h2[^>]*\bid="([^"]+)"', re.I)
NOT_SAMPLED_SECTIONS = {"watch", "sources", "updates"}


def case_dir(slug: str) -> Path:
    for d in (ROOT / "issues").iterdir():
        if d.is_dir() and d.name.lower().endswith("-" + slug):
            return d
    raise SystemExit("no case directory for %s" % slug)


def body_html(slug: str) -> str:
    """The page as bindings.py reads it: head gone, header reduced to its
    prose (standfirst), furniture gone. The source list and the footer are
    cut too: the references are rebuilt from sources.json below, and the
    change history is process."""
    html = B._page_html(slug)
    html = B.HEAD.sub(" ", html)
    html = B.HEADER.sub(B._header_prose, html)
    # The masthead's date line and the correction notices are page furniture
    # about the page's history, not part of the answer.
    html = re.sub(r'<span\b[^>]*class="meta"[^>]*>.*?</span>', " ", html, flags=re.S | re.I)
    html = re.sub(r'<div\b[^>]*class="note"[^>]*>.*?</div>', " ", html, flags=re.S | re.I)
    html = re.sub(r'<p\b[^>]*class="note"[^>]*>.*?</p>', " ", html, flags=re.S | re.I)
    html = B.FURNITURE.sub(" ", html)
    html = B.FOOTER.sub(" ", html)
    html = re.sub(r'<div class="srclist".*', " ", html, flags=re.S)
    return html


def sources_of(row: dict | None, known: set[str]) -> list[str]:
    if not row:
        return []
    ids = [row.get("source_id")]
    ids += [x.get("source_id") for x in row.get("also_rests_on") or []]
    ids += [x.get("source_id") for x in row.get("premises") or []]
    out = []
    for i in ids:
        if i and i in known and i not in out:
            out.append(i)
    return out


def with_markers(sentence: str, nums: list[int]) -> str:
    if not nums:
        return sentence
    marks = "".join("[%d]" % n for n in nums)
    m = re.search(r"([.!?]['\"”’)]*)\s*$", sentence)
    if m:
        return sentence[:m.start()] + " " + marks + m.group(1)
    return sentence + " " + marks


def export(slug: str) -> tuple[str, list[dict]]:
    rows = B.load(slug)["bindings"]
    srcs = json.loads((case_dir(slug) / "sources.json").read_text())["sources"]
    by_id = {s["id"]: s for s in srcs}
    order: list[str] = []
    paragraphs, out_rows = [], []
    html = body_html(slug)
    # Which section each block sits in: the nearest <h2 id> before it.
    heads = [(m.start(), m.group(1)) for m in SECTION.finditer(html)]
    regions = marked_regions(html)
    for bm in BLOCK.finditer(html):
        section = ""
        for pos, sid in heads:
            if pos < bm.start():
                section = sid
        attrs = bm.group(2) or ""
        chart = bm.group(1).lower() == "figcaption" or any(
            re.search(r'class="[^"]*\b%s\b' % c, attrs) for c in CHART_CLASSES)
        mark = next((r[2] for r in regions if r[0] <= bm.start() < r[1]), "")
        struct_why = ("chart_description" if chart or mark == "scale" else
                      "rubric_score" if mark else "")
        sents = [" ".join(s.split()) for s in ledger.sentences(ledger.plain(bm.group(0)))]
        sents = [s for s in sents if s]
        if not sents:
            continue
        para = []
        for s in sents:
            row = rows.get(B.fingerprint(s))
            ids = sources_of(row, set(by_id))
            for i in ids:
                if i not in order:
                    order.append(i)
            nums = [order.index(i) + 1 for i in ids]
            text = with_markers(s, nums)
            reason = (("section: " + section) if section in NOT_SAMPLED_SECTIONS else
                      struct_why or blind.process_reason(s))
            out_rows.append({"slug": slug, "row_sha": B.fingerprint(s), "bound": row is not None,
                             "sources": ids, "markers": nums, "section": section,
                             "text": text, "samplable": not reason, "not_samplable_why": reason})
            para.append(text)
        paragraphs.append(" ".join(para))
    refs = []
    for n, i in enumerate(order, 1):
        s = by_id[i]
        refs.append("[%d] %s %s" % (n, s.get("title") or i, s.get("url") or ""))
    text = "\n\n".join(paragraphs) + "\n\nReferences\n" + "\n".join(refs)
    return text, out_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for slug in a.slugs:
        text, rows = export(slug)
        (out / (slug + ".export.txt")).write_text(text, encoding="utf-8")
        with open(out / (slug + ".sentences.jsonl"), "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        marked = sum(1 for r in rows if r["markers"])
        print("%-11s %4d sentences, %4d bound, %4d with markers, %4d samplable, %3d references"
              % (slug, len(rows), sum(r["bound"] for r in rows), marked,
                 sum(r["samplable"] for r in rows), text.count("\n[")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
