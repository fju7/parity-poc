#!/usr/bin/env python3
"""Blind an answer: one plain format, house style removed, residual tells counted.

Protocol, Blinding:
  - One plain format: plain text with numbered references and URLs; headings,
    layout and visual style removed.
  - House style removed: phrases that identify WHU or a tool are rewritten to
    neutral wording by a fixed list (blind_phrases.json), applied by script.

Usage:
    blind.py FILE [FILE ...] [--out DIR] [--report]

FILE is a WHU page (.html) or a tool export (.md). For each, writes
DIR/<name>.blind.txt and, with --report, prints which rules fired and every
residual tell left after blinding, with examples. Free: no model calls.

WHAT THIS DOES NOT DO, and the report says so rather than implying otherwise:
it does not restructure an answer. A WHU answer still discusses its news
coverage and says what would settle the question; a tool's answer still has
its own section order. Those are content, and rewriting content is not
blinding. The blinding check (a model guessing the system from 20 claims) is
what measures whether what is left is enough to identify a system.
"""
from __future__ import annotations

import argparse
import html as H
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHRASES = json.loads((HERE / "blind_phrases.json").read_text(encoding="utf-8"))

# WHU page furniture that a reader sees around the answer, not the answer:
# the masthead and kicker, the corrections notice, the change history.
WHU_DROP = [
    r'<div class="kicker-row".*?</div>',
    r'<div class="domain".*?</div>',
    r'<p class="note"[^>]*>.*?</p>',
    r'<div class="note"[^>]*>.*?</div>',
    r'<footer\b.*?</footer>',
    # Not <header> wholesale: it holds the standfirst, which is part of the answer.
    r'<nav\b.*?</nav>',
]


def _typography(t: str) -> str:
    t = t.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\s*[—–]\s*", " - ", t)
    t = t.replace("−", "-").replace(" ", " ").replace(" ", " ").replace(" ", " ")
    return t


def from_html(raw: str) -> tuple[str, list[str]]:
    t = re.sub(r"<(script|style|svg|head|title)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    for pat in WHU_DROP:
        t = re.sub(pat, " ", t, flags=re.S | re.I)
    refs: list[str] = []
    # The source list becomes numbered references: its text and first URL.
    m = re.search(r'<div class="srclist".*', t, flags=re.S)
    if m:
        for src in re.findall(r'<div class="src"[^>]*>(.*?)</div>', m.group(0), flags=re.S):
            url = (re.findall(r'href="(https?://[^"]+)"', src) or [""])[0]
            # The citation only. WHU's source notes (what each source was used
            # for, what was not read, what was corrected) and its type tags are
            # house style no tool produces; a reference is author, title, venue.
            src = re.sub(r'<span class="(note|tag)"[^>]*>.*?</span>', " ", src, flags=re.S)
            txt = H.unescape(re.sub(r"<[^>]+>", " ", src))
            refs.append(" ".join(txt.split()) + (" " + url if url and url not in txt else ""))
        t = t[:m.start()]
        t = re.sub(r'<h2[^>]*id="sources"[^>]*>.*?</h2>', " ", t, flags=re.S)
    t = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", "\n", t, flags=re.S | re.I)      # headings removed
    t = re.sub(r"<br\s*/?>|</(p|div|li|blockquote|tr)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = H.unescape(t)
    return t, refs


def from_markdown(raw: str) -> tuple[str, list[str]]:
    t = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)                         # capture metadata
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s.*$", "", t)                              # headings removed
    t = re.sub(r"(?m)^\s*\|?\s*:?-{3,}.*$", "", t)                            # table rules
    t = re.sub(r"(?m)^\s*\|(.*)\|\s*$", lambda m: " ; ".join(c.strip() for c in m.group(1).split("|")), t)
    refs: list[str] = []
    index: dict[str, int] = {}

    def link(m):
        text, url = m.group(1), m.group(2)
        if url not in index:
            refs.append(url); index[url] = len(refs)
        return "%s [%d]" % (text, index[url])
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)                               # images
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)[^)]*\)", link, t)
    t = re.sub(r"(\*\*|__|\*|_)(\S.*?\S|\S)\1", r"\2", t)                     # emphasis
    t = re.sub(r"(?m)^\s*([-*+]|\d+\.)\s+", "", t)                            # list markers
    t = t.replace("\\", "")
    return t, refs


def apply_rules(t: str) -> tuple[str, dict[str, int]]:
    fired: dict[str, int] = {}
    for r in PHRASES["rules"]:
        t, n = re.subn(r["pattern"], r["replace"], t)
        if n:
            fired[r["id"]] = n
    sp = {k: v for k, v in PHRASES["spelling"].items() if not k.startswith("_")}
    n_sp = 0

    def swap(m):
        nonlocal n_sp
        w = m.group(0); low = w.lower()
        # Lowercase words only: a capitalised "Centre" is usually a name
        # (Science Media Centre), and a name is not spelling.
        if low not in sp or w != low:
            return w
        n_sp += 1
        rep = sp[low]
        return rep.capitalize() if w[0].isupper() else rep
    t = re.sub(r"\b[A-Za-z]+\b", swap, t)
    if n_sp:
        fired["spelling"] = n_sp
    return t, fired


def blind(path: Path) -> tuple[str, dict[str, int]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    body, refs = (from_html(raw) if path.suffix.lower() in (".html", ".htm") else from_markdown(raw))
    # Whitespace first: the line-anchored rules (the confidence line) need a
    # paragraph to start at the start of a line, not after markup's indent.
    body = re.sub(r"[ \t]+", " ", _typography(body))
    body = re.sub(r" *\n[ \n]*", "\n\n", body).strip()
    body, fired = apply_rules(body)
    if refs:
        refs_t, _ = apply_rules(_typography("\n".join(refs)))
        body += "\n\nReferences\n" + "\n".join("[%d] %s" % (i + 1, r) for i, r in enumerate(refs_t.splitlines()))
    return body, fired


def tells(text: str) -> dict[str, list[str]]:
    out = {}
    for name, pat in PHRASES["tells"].items():
        if name.startswith("_"):
            continue
        hits = []
        for m in re.finditer(pat, text, flags=re.I):
            a, b = max(0, m.start() - 60), min(len(text), m.end() + 60)
            hits.append(" ".join(text[a:b].split()))
        if hits:
            out[name] = hits
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=".")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for f in a.files:
        p = Path(f)
        text, fired = blind(p)
        (out / (p.stem + ".blind.txt")).write_text(text, encoding="utf-8")
        words = len(text.split())
        tl = tells(text)
        summary[p.name] = {"words": words, "fired": fired,
                           "tells": {k: {"count": len(v), "per_1000_words": round(1000 * len(v) / max(words, 1), 2),
                                         "examples": v[:4]} for k, v in tl.items()}}
        if a.report:
            print("\n=== %s  (%d words)" % (p.name, words))
            print("  rules fired: %s" % (", ".join("%s x%d" % kv for kv in fired.items()) or "none"))
            for k, v in tl.items():
                print("  tell %-22s %3d  (%.2f per 1,000 words)  e.g. %s" % (k, len(v), 1000 * len(v) / max(words, 1), v[0][:110]))
    if a.json:
        Path(a.json).write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
