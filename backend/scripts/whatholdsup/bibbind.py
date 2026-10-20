#!/usr/bin/env python3
"""Bind a source list's title and author lines to the document they cite.

Every sentence on the page now has a row (bindings.is_empirical, 2026-10-18),
and a source-list entry contributes two kinds the anchor binder cannot place:
the title and the author list. They carry no figure and no quotation, so
autobind finds nothing to search for. They are still claims about a document,
and a wrong one is an error a reader acts on -- this page printed "Royal College
of Pathologists" over an article by a named author, and "Kirschner PA" over a
byline that reads "P. Kirschner".

TITLE LINE. Bound when the line, without its final full stop, occurs verbatim
in the entry's held text under spancheck's normalisation (dashes, quotes,
ligatures, whitespace -- NOT case). A corrigendum that amends the entry's source
(`amends` in sources.json) is searched as well, because it prints the published
title: S045 does for S021, whose held copy is the accepted manuscript.

AUTHOR LINE. "Wang DY, Ding J, Sun AL, et al." Bound when every listed surname
occurs in the held text with given names whose initials are the listed ones,
read on either side of the surname (papers print "Ding-Yu Wang" and registries
print "Pedersen Tom Andre"). "et al." is not a name: only the names listed are
checked. A name with no initials ("Liu, Christian, ...") is checked by surname
only. Accents are folded for the comparison, and a match that needed the fold
says so ("matched ignoring accents: Stanković / Stankovic").

The span is the held passage from the first matched name to the last, so B2 can
find it. A line that does not match is not bound; the reason is returned.

This writes nothing. It returns proposals; a person confirms them.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bindings as B           # noqa: E402
import source_ledger as ledger  # noqa: E402
import source_store as store    # noqa: E402
import spancheck as SC          # noqa: E402

CITATION = re.compile(r"\b(?:19|20)\d\d\b|\barXiv\b|\bdoi\b|;\s*\d|\bhttps?://", re.I)
MAX_AUTHOR_SPAN = 900
REFERENCES = re.compile(r"\b(?:References|REFERENCES|Bibliography)\b")
SUPERSCRIPT = re.compile(r"[\d∗*†‡§¶+✉,|]+")


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _entries(slug: str) -> list[dict]:
    """Each <div class="src">: its label, the sentences of its link text, its links."""
    import html as _h
    raw = B.HEAD.sub(" ", B._page_html(slug))
    out = []
    for blk in re.findall(r'<div class="src">(.*?)</div>', raw, re.S):
        lab = re.search(r'<span class="tag">(.*?)</span>', blk, re.S)
        a = re.search(r"<a\b[^>]*>(.*?)</a>", blk, re.S)
        if not a:
            continue
        sents = [" ".join(s.split()) for s in ledger.sentences(ledger.plain(a.group(1)))]
        out.append({"label": " ".join(_h.unescape(re.sub(r"<[^>]+>", " ", lab.group(1))).split()) if lab else "",
                    "sentences": [s for s in sents if s],
                    "hrefs": re.findall(r'href="([^"]+)"', blk)})
    return out


def lines(slug: str) -> list[dict]:
    """Every title and author line on the page: kind, page sentence, entry source."""
    srcs = store.sources(slug)
    out = []
    for e in _entries(slug):
        if not e["sentences"]:
            continue
        subj = B.entry_subject(" ".join(e["sentences"]), [(" ".join(e["sentences"]), e["hrefs"])], srcs)
        first = e["sentences"][0]
        # THE TAG IS NOT PART OF THE LINE where the splitter drops it (GAP-017:
        # bindings.page_sentences, study issues), so the proposal carries the
        # sentence a row is keyed by. A published issue keeps the tagged form
        # until its next republish moves it to the new splitter.
        page = ("%s %s" % (e["label"], first)).strip() if e["label"] and not B._is_study(slug) else first
        out.append({"kind": "author", "sentence": page, "body": first, "sources": subj})
        for s in e["sentences"][1:]:
            if CITATION.search(s):
                break
            out.append({"kind": "title", "sentence": s, "body": s, "sources": subj})
    return out


def _texts(slug: str, sids: list[str]) -> list[tuple[str, str]]:
    ids = list(sids)
    for s in store.sources(slug):
        if s.get("amends") in sids and s["id"] not in ids:
            ids.append(s["id"])
    return [(sid, SC._norm(t or "")) for sid in ids for _f, t in SC._texts(slug, sid)]


def bind_title(line: dict, slug: str) -> dict:
    want = SC._norm(line["body"]).rstrip(".").strip()
    for sid, t in _texts(slug, line["sources"]):
        i = t.find(want)
        if i >= 0:
            return {"ok": True, "source_id": sid, "span": t[i:i + len(want)],
                    "why": "title verbatim in %s" % sid}
    return {"ok": False, "why": "title not verbatim in %s (case and wording as printed)"
            % (", ".join(line["sources"]) or "no entry source")}


def parse_authors(body: str) -> list[tuple[str, str]]:
    """[(surname, initials)] from 'Wang DY, Ding J, Sun AL, et al.'"""
    b = re.sub(r",?\s*et al\.?\s*$", "", body.strip()).rstrip(".")
    out = []
    for part in re.split(r",|&|\band\b", b):
        toks = part.split()
        if not toks:
            continue
        if len(toks) > 1 and re.fullmatch(r"[A-Z]{1,3}", toks[-1]):
            out.append((" ".join(toks[:-1]), toks[-1]))
        else:
            out.append((" ".join(toks), ""))
    return out


def _initials(tokens: list[str]) -> str:
    out = ""
    for t in tokens:
        for piece in re.split(r"-", t):
            piece = piece.strip(".")
            if piece[:1].isalpha():
                out += piece[0].upper()
    return out


def _given(text: str, start: int, end: int) -> list[tuple[list[str], int, int]]:
    """Candidate given names for a surname at [start, end): every run of one to
    three capitalised tokens immediately before it, and immediately after it,
    each with the offsets the matched passage would run between. The nearest
    tokens are tried first, so the previous author's surname is never read as
    this one's given name."""
    pre = text[max(0, start - 60):start]
    before = [(m.group(0), max(0, start - 60) + m.start())
              for m in re.finditer(r"[^\s\d∗*†‡§¶+✉,|]+", pre)]
    after = [(m.group(0), end + m.end()) for m in re.finditer(r"[^\s\d∗*†‡§¶+✉,|]+", text[end:end + 60])]
    out = []
    for n in (1, 2, 3):
        run = before[-n:] if len(before) >= n else []
        if run and all(re.fullmatch(r"[A-Z][\w.'-]*", t) for t, _o in run):
            out.append(([t for t, _o in run], run[0][1], end))
        a = after[:n]
        if len(a) == n and all(re.fullmatch(r"[A-Z][\w.'-]*", t) and t not in TITLES for t, _o in a):
            out.append(([t for t, _o in a], start, a[-1][1]))
    return out


TITLES = {"MD", "PhD", "Prof", "Prof.", "Dr", "Dr.", "MS", "MSc", "BSc"}


def _occurrences(ft: str, sur: str, ini: str) -> list[tuple[int, int]]:
    """Every place this surname is printed with the listed initials."""
    out = []
    # Not followed by a LETTER: a superscript affiliation digit ("Crochet2")
    # still ends the name.
    for m in re.finditer(r"(?<![^\W\d_])%s(?![^\W\d_])" % re.escape(fold(sur)), ft):
        if not ini:
            out.append((m.start(), m.end()))
            continue
        g = next(((lo, hi) for toks, lo, hi in _given(ft, m.start(), m.end()) if _initials(toks) == ini), None)
        if g is not None:
            out.append(g)
    return out


def bind_authors(line: dict, slug: str) -> dict:
    names = parse_authors(line["body"])
    if not names:
        return {"ok": False, "why": "no names parsed"}
    best = None
    for sid, t in _texts(slug, line["sources"]):
        # THE AUTHOR LIST, NOT THE REFERENCES. A reference list cites the same
        # names with full initials ("Kirschner, P. A.") where the byline prints
        # "P. Kirschner"; the claim is about the byline.
        m = REFERENCES.search(t)
        t = t[:m.start()] if m else t
        ft = fold(t)
        if len(ft) != len(t):          # the fold must not move offsets
            ft = t
        occ = [_occurrences(ft, sur, ini) for sur, ini in names]
        missing = ["%s %s" % (sur, ini) if ini else sur for (sur, ini), o in zip(names, occ) if not o]
        if missing:
            cand = {"ok": False, "why": "in %s, not found with matching initials: %s" % (sid, ", ".join(missing)), "_n": len(missing)}
            if best is None or len(missing) < best.get("_n", 99):
                best = cand
            continue
        # The FIRST printing that holds every listed name together -- the
        # byline, before any reference list that happens to cite the same
        # authors: anchor on each printing of the first name in document order,
        # take the nearest printing of every other one.
        pick = None
        for a0 in occ[0]:
            chosen = [a0] + [min(o, key=lambda x: abs(x[0] - a0[0])) for o in occ[1:]]
            lo, hi = min(c[0] for c in chosen), max(c[1] for c in chosen)
            if hi - lo <= MAX_AUTHOR_SPAN:
                pick = (lo, hi)
                break
        if pick is None:
            best = best or {"ok": False, "_n": 0, "why": "in %s, the names are never printed together with the listed "
                            "initials (each is found, but only far apart)" % sid}
            continue
        passage = t[pick[0]:pick[1]]
        # A surname that matched only once accents were folded, on either side.
        folded = []
        for sur, _i in names:
            if sur in passage:
                continue
            held = next((w for w in re.findall(r"[^\W\d_](?:[^\W\d_]|['-])*", passage) if fold(w) == fold(sur)), "")
            if held or fold(sur) != sur:
                folded.append("%s / %s" % (held or sur, sur if held else fold(sur)))
        why = "every listed author in %s with matching initials" % sid
        if folded:
            why += "; INFO: matched ignoring accents: %s" % "; ".join(folded)
        return {"ok": True, "source_id": sid, "span": t[pick[0]:pick[1]], "why": why}
    best = best or {"ok": False, "why": "no held text for %s" % (", ".join(line["sources"]) or "this entry")}
    best.pop("_n", None)
    return best


def pending_corrections(doc_path: Path) -> set[str]:
    """Row shas the revision doc already carries as corrections: not to be bound."""
    if not doc_path.exists():
        return set()
    return set(re.findall(r"^## \d+\. ([0-9a-f]{8})\b", doc_path.read_text(encoding="utf-8"), re.M))


def propose(slug: str) -> list[dict]:
    rows = B.load(slug).get("bindings") or {}
    by_text = {" ".join((v.get("sentence") or "").split()): k for k, v in rows.items() if v.get("on_page")}
    out = []
    for ln in lines(slug):
        sha = by_text.get(ln["sentence"])
        r = (bind_title if ln["kind"] == "title" else bind_authors)(ln, slug) if ln["sources"] else \
            {"ok": False, "why": "the entry's link names no source in sources.json"}
        out.append(dict(ln, sha=sha, **r))
    return out


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "deskilling"
    for p in propose(slug):
        print("%-6s %-6s %s %-60s %s" % ("BIND" if p["ok"] else "--", p["kind"], (p.get("sha") or "-")[:8],
                                        p["sentence"][:60], p["why"][:120]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
