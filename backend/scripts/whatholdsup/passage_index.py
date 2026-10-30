#!/usr/bin/env python3
"""Passage retrieval, shared by lean WHU's audit and the check pilot's v4.

A held source is split into passages (whole sentences, about PASSAGE_CHARS
characters each, never across a blank-line paragraph break), each with its
(start, end) offsets in the held text. `Index.top(query, k)` returns the k
passages most relevant to a sentence or claim by BM25 (Okapi; k1 1.5, b 0.75),
no embeddings and no model call.

A passage is RELEVANT only above the threshold: a BM25 score of at least
MIN_SCORE and at least MIN_TERMS distinct query terms in it. When nothing
clears it, `retrieve` returns no retrieved passage and says so
(`below_threshold`), and the caller falls back to the bound passage alone --
never to the whole source -- and logs it.

    python3 passage_index.py FILE "query"    print the top passages of a text file
"""
from __future__ import annotations

import functools
import hashlib
import math
import re
import sys
import unicodedata
from dataclasses import dataclass

PASSAGE_CHARS = 900          # a passage is whole sentences up to about this long
PASSAGE_MAX = 2400           # a single sentence longer than this is cut at a space
K = 4                        # passages retrieved per sentence, beside its bound ones
MIN_SCORE = 2.0
MIN_TERMS = 2
K1, B = 1.5, 0.75
DOC_SEP = "\n[… text omitted …]\n"   # audit_stage.DOC_SEP: the reader sees where text is left out

STOP = frozenset("""a an and are as at be been but by can could did do does for from had has have he her
his how i if in into is it its may might more most no not of on or our she should so such than that
the their them then there these they this those to was we were what when where which while who will
with would also only other some any each per its""".split())
_SENT_END = re.compile(r"(?<=[.!?;])[\"”’)\]]*\s+(?=[\"“(\[]?[A-Z0-9])")
_PARA = re.compile(r"\n\s*\n")
_TOKEN = re.compile(r"\d+(?:[.,]\d+)*%?|[a-z][a-z'-]+")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("−", "-")):
        s = s.replace(a, b)
    return s.lower()


def tokens(s: str) -> list[str]:
    out = []
    for t in _TOKEN.findall(_fold(s)):
        t = t.strip("'-")
        if len(t) < 2 or t in STOP:
            continue
        if t[0].isalpha() and len(t) > 4 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]                               # plural folded: "extremes" ~ "extreme"
        out.append(t)
    return out


@dataclass(frozen=True)
class Passage:
    idx: int
    start: int
    end: int


def _sentence_spans(text: str, a: int, b: int) -> list[tuple[int, int]]:
    out, i = [], a
    for m in _SENT_END.finditer(text, a, b):
        if m.start() > i:
            out.append((i, m.start()))
        i = m.end()
    if i < b and text[i:b].strip():
        out.append((i, b))
    return out


def split(text: str, size: int = PASSAGE_CHARS) -> list[Passage]:
    """Passages covering TEXT: whole sentences, grouped up to SIZE characters,
    never across a paragraph break; offsets are into TEXT."""
    paras, i = [], 0
    for m in _PARA.finditer(text):
        paras.append((i, m.start()))
        i = m.end()
    paras.append((i, len(text)))
    out: list[Passage] = []

    def emit(s: int, e: int) -> None:
        while e - s > PASSAGE_MAX:                   # one runaway "sentence" (a table, a list)
            cut = text.rfind(" ", s + size, s + PASSAGE_MAX)
            cut = cut if cut > s else s + PASSAGE_MAX
            out.append(Passage(len(out), s, cut))
            s = cut
        if text[s:e].strip():
            out.append(Passage(len(out), s, e))

    for a, b in paras:
        if not text[a:b].strip():
            continue
        cur = None
        for s, e in _sentence_spans(text, a, b):
            if cur is None:
                cur = [s, e]
            elif e - cur[0] <= size:
                cur[1] = e
            else:
                emit(*cur)
                cur = [s, e]
        if cur:
            emit(*cur)
    return out


class Index:
    """BM25 over one text's passages."""

    def __init__(self, text: str, size: int = PASSAGE_CHARS):
        self.text = text
        self.passages = split(text, size)
        self.tf = []
        df: dict[str, int] = {}
        for p in self.passages:
            counts: dict[str, int] = {}
            for t in tokens(text[p.start:p.end]):
                counts[t] = counts.get(t, 0) + 1
            self.tf.append(counts)
            for t in counts:
                df[t] = df.get(t, 0) + 1
        self.n = len(self.passages)
        self.avg = (sum(sum(c.values()) for c in self.tf) / self.n) if self.n else 0.0
        self.idf = {t: math.log(1 + (self.n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def score(self, i: int, q: list[str]) -> tuple[float, int]:
        c = self.tf[i]
        dl = sum(c.values()) or 1
        s, hit = 0.0, 0
        for t in set(q):
            f = c.get(t)
            if not f:
                continue
            hit += 1
            s += self.idf.get(t, 0.0) * f * (K1 + 1) / (f + K1 * (1 - B + B * dl / (self.avg or 1)))
        return s, hit

    def top(self, query: str, k: int = K, exclude: set[int] | frozenset = frozenset(),
            min_score: float = MIN_SCORE, min_terms: int = MIN_TERMS) -> list[tuple[Passage, float]]:
        """The K best passages above the threshold, best first (ties: document order)."""
        q = tokens(query)
        if not q:
            return []
        scored = []
        for i in range(self.n):
            if i in exclude:
                continue
            s, hit = self.score(i, q)
            if s >= min_score and hit >= min(min_terms, len(set(q))):
                scored.append((-s, i))
        scored.sort()
        return [(self.passages[i], -ns) for ns, i in scored[:k]]

    def covering(self, start: int, end: int) -> list[int]:
        """Indexes of the passages that overlap TEXT[start:end]."""
        return [p.idx for p in self.passages if p.start < end and start < p.end]


@functools.lru_cache(maxsize=16)
def _index(digest: str, text: str) -> Index:
    return Index(text)


def index_of(text: str) -> Index:
    return _index(hashlib.sha256(text.encode("utf-8")).hexdigest(), text)


def find_span(text: str, span: str) -> tuple[int, int] | None:
    """Where a bound span sits in TEXT: exact (case folded), else as the audit's
    delivery check compares (audit_stage.norm), via its offset map."""
    if not span:
        return None
    i = text.lower().find(span.lower())
    if i >= 0:
        return i, i + len(span)
    try:
        import audit_stage as A
    except Exception:
        return None
    at = A.locate(span, text)
    return at


def retrieve(text: str, query: str, bound_spans: list[str] | tuple = (), k: int = K) -> dict:
    """What to send for one sentence or claim against one held text.

    {"bound": [(start, end)], the bound passages (the span itself widened to its
     covering passages); "retrieved": [(start, end, score)], up to K more
     passages above the threshold; "below_threshold": True when retrieval found
     none, in which case only the bound passages go; "unlocated": the bound
     spans not found in the text (the caller's delivery check reports them)}."""
    ix = index_of(text)
    bound, have, unlocated = [], set(), []
    for sp in bound_spans or ():
        at = find_span(text, sp)
        if at is None:
            unlocated.append(sp)
            continue
        cov = ix.covering(*at)
        lo = min([at[0]] + [ix.passages[i].start for i in cov])
        hi = max([at[1]] + [ix.passages[i].end for i in cov])
        bound.append((lo, hi))
        have.update(cov)
    got = ix.top(query, k, exclude=have)
    return {"bound": merge(bound), "retrieved": [(p.start, p.end, round(s, 3)) for p, s in got],
            "below_threshold": not got, "unlocated": unlocated}


def merge(ranges) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for a, b in sorted((r[0], r[1]) for r in ranges):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def deliver(text: str, ranges) -> str:
    """The passages, merged and in document order, joined with DOC_SEP."""
    return DOC_SEP.join(text[a:b] for a, b in merge(ranges))


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    text = open(argv[0], encoding="utf-8", errors="replace").read()
    r = retrieve(text, argv[1])
    print("%d passages; below threshold: %s" % (len(index_of(text).passages), r["below_threshold"]))
    for a, b, s in r["retrieved"]:
        print("--- %d-%d score %.2f\n%s" % (a, b, s, text[a:b][:400]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
