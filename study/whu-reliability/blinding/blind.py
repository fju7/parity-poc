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
import hashlib
import html as H
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The blinding list, pinned by sha256 as the spelling map is (protocol rev 38):
# a changed list is refused.
PHRASES_FILE = HERE / "blind_phrases.json"
PHRASES_SHA256 = "ccb61c7f0639cdc332a258beecc723ec432702e56a2316816909d42ae9c39757"


def load_phrases() -> dict:
    raw = PHRASES_FILE.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != PHRASES_SHA256:
        raise SystemExit("blind_phrases.json has sha256 %s, not the pinned %s" % (got, PHRASES_SHA256))
    return json.loads(raw.decode("utf-8"))


PHRASES = load_phrases()

# The British-to-American spelling list (pre-freeze ruling, protocol rev 33): a
# fixed word list identified by its sha256. A changed list is refused, so the
# list a blinded answer went through is always the one named here.
SPELLING_FILE = HERE / "spelling_us.json"
SPELLING_SHA256 = "6a0eec29ed625c9e70770588298a541448253d1faeadf87302debb2e3d3db0ad"


def load_spelling() -> dict[str, str]:
    raw = SPELLING_FILE.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != SPELLING_SHA256:
        raise SystemExit("spelling_us.json has sha256 %s, not the pinned %s" % (got, SPELLING_SHA256))
    return json.loads(raw.decode("utf-8"))["words"]


SPELLING = load_spelling()

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


# A value the export could not capture (Gemini's formulas came out as images).
# Kept as an invisible token so the sentence can be marked not samplable, then
# removed from what a judge would read.
LOST = "\u2063LOST\u2063"
# A URL may hold one level of parentheses ("…/S1550-4131(19)30248-7").
URL = r"https?://(?:[^()\s]|\([^()\s]*\))+"
LINK = r"\[[^\]\n]{1,60}\]\(" + URL + r"\)"


def empty_cells(t: str) -> str:
    """Runs of empty table cells (" ; ; ; ;", left where a lost value stood)
    become one separator."""
    return re.sub(r";(?:[ \t]*;)+", ";", t)


def is_chip(text: str, url: str) -> bool:
    """A link that is a citation marker, not prose: its text is its own URL, or
    a site's name -- one word (an optional " +2", "two more sources", after it)
    that the URL's host contains, ignoring case and hyphens ("Wikipedia" for
    en.wikipedia.org, "sciencedaily +2", "news-medical"). The same test for
    every system's answer (pre-freeze ruling, protocol rev 33)."""
    t = text.replace("\\", "").strip()
    if re.match(r"^https?://", t) or t == url:
        return True
    core = re.sub(r"\s*\+\d+$", "", t)
    if not core or re.search(r"\s", core) or len(core) > 40:
        return False
    host = re.sub(r"^https?://", "", url).split("/")[0].lower().replace("-", "")
    return core.lower().replace("-", "") in host


def from_markdown(raw: str) -> tuple[str, list[str]]:
    """One plain format for every tool: text, then [n] markers placed before the
    sentence's closing punctuation (as export_whu.py places WHU's), then the
    numbered reference list.

    Claude Research cites with site-name chips after the sentence
    ("... in 2009. [preventncd](url)"); a chip becomes [n] and moves inside the
    full stop. Gemini cites with numerals glued to the last word
    ("impairment1."); those become [n] too. Links whose text is prose keep
    their text, followed by [n]. ChatGPT's answers carry no links."""
    gemini = "Works cited" in raw
    t = re.sub(r"<!--.*?-->", " ", raw, flags=re.S)                         # capture metadata
    # Private-use glyphs: Claude's citation chips carry one ("nih\ue015").
    t = re.sub("[\ue000-\uf8ff]", "", t)
    # Escaped brackets ("\\[cite: 5\\]" in a markdown table) are brackets.
    t = re.sub(r"\\([\[\]])", r"\1", t)
    # A fenced code block (ChatGPT's mermaid diagrams) is markup, not prose.
    t = re.sub(r"(?ms)^[ \t]*```.*?^[ \t]*```[ \t]*$", "\n", t)
    # HTML left in an export (ChatGPT's tables and figures): cells become
    # " ; ", as markdown table cells do; every other tag goes. A tag starts
    # with a letter or "/": "<20%" is text, and must not swallow everything
    # up to the next ">".
    t = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " ; ", t, flags=re.I)
    t = re.sub(r"</?(tr|table|thead|tbody|p|div|br|figure|figcaption|li|ul|ol)\b[^>]*>", "\n", t, flags=re.I)
    t = re.sub(r"</?[A-Za-z][^<>]*>", " ", t)
    # Gemini's "[cite: 11, 22]" is a citation marker like any other.
    t = re.sub(r"\[cite:\s*([\d,\s]+)\]", lambda m: "".join("[%s]" % x.strip() for x in m.group(1).split(",") if x.strip()), t)
    if gemini:
        # The reference list is rebuilt below; Gemini's own is dropped.
        t = re.split(r"(?m)^#{1,6}\s*\**Works cited\**\s*$", t)[0]
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s.*$", "", t)                              # headings removed
    t = re.sub(r"(?m)^\s*\|?\s*:?-{3,}.*$", "", t)                            # table rules
    t = re.sub(r"(?m)^\s*\|(.*)\|\s*$", lambda m: " ; ".join(c.strip() for c in m.group(1).split("|")), t)
    refs: list[str] = []
    index: dict[str, int] = {}

    def num(url: str) -> int:
        if url not in index:
            refs.append(url); index[url] = len(refs)
        return index[url]
    t = re.sub(r"!\[\]\[image\d+\]", LOST, t)                                  # Gemini's lost formulas
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)                               # images
    # Chips after a full stop (and any closing quote) move inside it:
    # "x." [site](u) [site2](u2)" -> "x [1][2]."".
    def chips_inside(m):
        links = re.findall(r"\[([^\]\n]{1,60})\]\((" + URL + r")\)", m.group(2))
        if not all(is_chip(tx, u) for tx, u in links):
            return m.group(0)
        return " " + "".join("[%d]" % num(u) for _tx, u in links) + m.group(1)
    t = re.sub(r"([.!?]['\"”’)]*)((?:[ \t]*" + LINK + r")+)", chips_inside, t)

    def link(m):
        text, url = m.group(1), m.group(2)
        if is_chip(text, url):
            return "[%d]" % num(url)
        return "%s [%d]" % (text, num(url))
    t = re.sub(r"\[([^\]]+)\]\((" + URL + r")[^)]*\)", link, t)
    t = re.sub(r"(\*\*|__|\*|_)(\S.*?\S|\S)\1", r"\2", t)                     # emphasis
    # A citation numeral glued to "et al." ("Lane et al.3", "et al.1,4"), for
    # every system: "et al. [3]".
    t = re.sub(r"\bet al\.(\d{1,2}(?:,\d{1,2})*)(?![\d.]\d)",
               lambda m: "et al. " + "".join("[%s]" % x for x in m.group(1).split(",")), t)
    if gemini:
        # Glued citation numerals: after a lowercase word, a closing bracket
        # or a closing quote ('"limited"47'), before punctuation or a space.
        # Not after a capital (MUC2, D3), so names with digits are left alone.
        t = re.sub(r"(?:(?<=[a-z]{3})|(?<=[)\]])|(?<=[a-z][\"”’]))(\d{1,2}(?:,\d{1,2})*)(?=[\s.,;:]|$)",
                   lambda m: " " + "".join("[%s]" % x for x in m.group(1).split(",")), t)
        t = re.sub(r"(?<=[a-z]) (\[\d+\](?:\[\d+\])*)([.,;:])", r" \1\2", t)
    t = re.sub(r"(?m)^\s*([-*+]|\d+\.)\s+", "", t)                            # list markers
    t = t.replace("\\", "")
    return t, refs


def apply_rules(t: str) -> tuple[str, dict[str, int]]:
    fired: dict[str, int] = {}
    for r in PHRASES["rules"]:
        if "upper_group" in r:
            # A deletion at the start of a sentence: the word after it now
            # starts the sentence and takes its capital.
            g = r["upper_group"]
            t, n = re.subn(r["pattern"], lambda m: m.group(g)[:1].upper() + m.group(g)[1:], t)
        else:
            t, n = re.subn(r["pattern"], r["replace"], t)
        if n:
            fired[r["id"]] = n
    sp = SPELLING
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


def blind(path: Path, keep_lost: bool = False) -> tuple[str, dict[str, int]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.name.endswith(".export.txt"):
        # export_whu.py's output: already plain text with [n] markers and its
        # reference list; only the rewrite rules remain to be applied.
        body, refs = raw, []
    else:
        body, refs = (from_html(raw) if path.suffix.lower() in (".html", ".htm") else from_markdown(raw))
    # Whitespace first: the line-anchored rules (the confidence line) need a
    # paragraph to start at the start of a line, not after markup's indent.
    body = re.sub(r"[ \t]+", " ", _typography(body))
    body = re.sub(r" *\n[ \n]*", "\n\n", body).strip()
    body, fired = apply_rules(body)
    if not keep_lost:
        body = empty_cells(re.sub(r" ?" + LOST + r" ?", " ", body))
    if refs:
        refs_t, _ = apply_rules(_typography("\n".join(refs)))
        body += "\n\nReferences\n" + "\n".join("[%d] %s" % (i + 1, r) for i, r in enumerate(refs_t.splitlines()))
    return body, fired


def process_reason(sentence: str) -> str:
    """Why SENTENCE is about how the answer was made, or "" if it is not.

    Blinding ruling (19 October 2026): notes on unread sources, dated process
    notes, change history and the watch section are not sampled, for every
    system. One function, applied to every system's sentences, so the
    exclusion cannot favour one of them."""
    for name, pat in PHRASES["process"].items():
        if name.startswith("_"):
            continue
        if re.search(pat, sentence, flags=re.I | re.M):
            return name
    return ""


def split_sentences(text: str) -> list[str]:
    """WHU's own splitter (ledger.sentences), used for every system so that no
    system's sentences are cut differently from another's."""
    sys.path.insert(0, str(HERE.parents[2] / "backend" / "scripts" / "whatholdsup"))
    import source_ledger as ledger
    out = []
    abbrev = r"\b(e\.g|i\.e|et al|vs|cf|approx|Fig|Figs|No|Dr|Prof|Ref|Vol|Suppl)\."
    text = re.sub(abbrev, lambda m: m.group(0).replace(".", "\u2024"), text)
    for para in re.split(r"\n\s*\n", text):
        if para.strip() == "References" or re.match(r"^\[\d+\]\s", para.strip()):
            continue                     # the reference list is not prose
        out += [" ".join(s.split()).replace("\u2024", ".") for s in ledger.sentences(para) if s.strip()]
    return out


def sentence_rows(path: Path, system: str, context_chars: int = 400) -> list[dict]:
    """One row per blinded sentence, with the ~400 characters before it (what
    an M1 judge is shown) and whether it may be sampled.

    A WHU export brings its own sentence list (export_whu.py splits the page
    exactly as bindings.py does and knows each sentence's section, so the watch
    section is excluded whole); each is blinded by the same rules. Any other
    answer is blinded whole and then split."""
    side = path.with_name(path.name.replace(".export.txt", ".sentences.jsonl"))
    if path.name.endswith(".export.txt") and side.exists():
        src = [json.loads(l) for l in side.read_text(encoding="utf-8").splitlines() if l.strip()]
        pairs = []
        for r in src:
            t = re.sub(r"[ \t]+", " ", _typography(r["text"])).strip()
            t, _f = apply_rules(t)
            pre = "" if r.get("samplable") else r.get("not_samplable_why", "")
            pairs.append((t, pre))
    else:
        text, _fired = blind(path, keep_lost=True)
        pairs = [(s, "") for s in split_sentences(text.split("\n\nReferences\n")[0])]
    rows, so_far = [], ""
    for i, (s, pre) in enumerate(pairs):
        lost = LOST in s or re.search(r"\(\s*(to|-|,|;|vs\.?)?\s*\)", s)
        why = pre or ("value_not_captured" if lost else "") or process_reason(s)
        s = empty_cells(" ".join(s.replace(LOST, " ").split()))
        rows.append({"system": system, "doc": path.name, "idx": i, "text": s,
                     "context": so_far[-context_chars:], "samplable": not why, "not_samplable_why": why})
        so_far += " " + s
    return rows


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
    ap.add_argument("--sentences", metavar="SYSTEM",
                    help="also write <name>.sentences.blind.jsonl: one row per sentence, for sampling")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for f in a.files:
        p = Path(f)
        text, fired = blind(p)
        (out / (p.stem + ".blind.txt")).write_text(text, encoding="utf-8")
        if a.sentences:
            rows = sentence_rows(p, a.sentences)
            with open(out / (p.stem + ".sentences.blind.jsonl"), "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
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
