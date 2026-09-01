#!/usr/bin/env python3
"""Propose a binding for every empirical sentence — deterministically first.

WHY DETERMINISTIC FIRST
-----------------------
The obvious way to bind 338 sentences is to ask a model where each one came
from. That may still be needed for the residue. It should not be the first
move, for the reason this whole day has been about: a model returns prose about
a source, and prose about a source is what we have been writing corrections
from.

There is a free pass available before that. A sentence that says "63.9 vs 51.4
months, HR 0.76 (95% CI 0.63-0.93), two-sided P = 0.008" carries five anchors
-- strings that either are or are not in a given document. Search every document
in the library for all of them. If exactly ONE contains all five, that is not a
guess; it is the only document in the corpus that could have supplied the
sentence. If several do, or none, the sentence goes to the residue and a person
or a model looks at it.

WHAT A PROPOSAL IS AND IS NOT
-----------------------------
Every row this writes is marked proposed_by "autobind" and confirmed false. A
proposal is a claim that a span EXISTS, verified by string equality at the
moment of writing. It is not a claim that the sentence is warranted by it --
that is the third question in the spec and it needs a signature this module
cannot give. R1 governs here as everywhere.

The span is deliberately widened to its sentence boundaries in the source, and
an envelope of surrounding text is stored with it, because a bare span is how
"8%" gets recorded for a document that says "8% to 20%".
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store   # noqa: E402
import bindings as B           # noqa: E402
import spancheck as SC         # noqa: E402

# An anchor is a string specific enough that its presence is evidence. Bare
# small integers are not: "four" and "19" appear in every document.
ANCHOR = re.compile(
    r"NCT\d{8}"
    r"|10\.\d{4,9}/\S{4,}"
    r"|\d+\.\d{2,}"
    r"|\d{1,3}(?:,\d{3})+"
    r"|\d+\.\d\s?%"
    r"|\d+\.\d\b")
QUOTE = re.compile(r"[“\"]([^”\"]{25,200})[”\"]")

MAX_WINDOW = 700     # anchors further apart than this are not one passage
MIN_ANCHORS = 2      # one number is a coincidence

# ANCHOR STRENGTH, added after the first run bound three of its first five
# sentences to the wrong document.
#
# "0.52, 0.58" appear together in P-VERIFY's subgroup table, so a sentence about
# eight progression-free readouts across four trials was bound to a real-world
# cohort study. "0.008, 0.004" appear together in the same paper's patient
# characteristics table, so MONALEESA-2's one-sided/two-sided argument was bound
# to it too. Two loose two-decimal numbers are not evidence of provenance; they
# are a coincidence that a large enough corpus guarantees.
#
# A registry identifier, a DOI or a quoted passage identifies a document. Three
# significant digits nearly does. Two does not.
STRONG, MEDIUM, WEAK = 3, 2, 1


def anchor_strength(a: str) -> int:
    if re.match(r"NCT\d{8}|10\.\d{4,9}/", a) or len(a) > 24:
        return STRONG
    digits = re.sub(r"[^0-9]", "", a).lstrip("0")
    if len(digits) >= 4:
        # 0.00973, 0.337750, 0.7531 — a four-significant-digit number is not a
        # coincidence in a corpus this size.
        return STRONG
    return MEDIUM if len(digits) >= 3 else WEAK


MIN_STRENGTH = 4     # one strong, or two medium, or a medium and two weak


def content_words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{5,}", t.lower())
            if w not in store.STOP}


# THE TWO SHAPES AUTOBIND GOT WRONG, detectable before any search runs.
#
# OUR OWN ARITHMETIC. "0.29 / 0.30 = 96.7%" and "abemaciclib's by 0.08 and
# ribociclib's by 0.05" are subtractions this page performed. No source contains
# them, so the binder went looking and found a coincidence in a table of patient
# ages. A sentence that shows its own working is bound to nothing, and saying so
# is more useful than a false span.
# The first version of this matched "= \d", which is in "P = 0.008" and
# therefore in nearly every figure sentence on the page. It classified 31
# sentences as our own arithmetic and swallowed half the good bindings. A
# pattern that fires on the commonest punctuation in the corpus is not a
# detector. Explicit markers only.
OURS = re.compile(
    r"[÷×]"
    r"|\d+(?:\.\d+)?\s*[-−–+÷×/]\s*\d+(?:\.\d+)?\s*="
    r"|\bthe figure is ours\b"
    r"|\bour (?:own )?(?:arithmetic|subtraction|calculation|figure)\b"
    r"|\b(?:subtraction|subtracting|divided by|multiplied by)\b"
    r"|\bis exactly (?:twice|half|double)\b"
    r"|\bnot a published (?:one|figure)\b", re.I)

# A CLAIM ABOUT ANOTHER DOCUMENT. "The unrounded 0.576 (0.463-0.718) appears in
# the 2019 extended-follow-up paper" is a statement about where a figure lives.
# Its numbers are findable — in the registry, which is not the paper the
# sentence is about — so the binder attributed the sentence to the wrong place.
ABOUT = re.compile(
    r"\b(?:appears?|appeared|does not appear|is not in|is in|are in|prints?|"
    r"printed|posts?|posted|states?|lists?|carries|records?)\b[^.]{0,80}"
    r"\b(?:in|on)\b[^.]{0,40}"
    r"\b(?:paper|publication|abstract|posting|record|registry|article|"
    r"appendix|table|supplement)\b", re.I)


def shape_of(sentence: str) -> tuple[str, str] | None:
    m = OURS.search(sentence)
    if m:
        return "arithmetic", ("the sentence shows its own working (%r) — it rests "
                              "on figures already on the page, not on a source"
                              % m.group(0)[:40])
    m = ABOUT.search(sentence)
    if m:
        return "about_a_document", ("the sentence is a claim about WHERE a figure "
                                    "appears (%r), so its numbers will be found "
                                    "somewhere that is not what the sentence is "
                                    "about" % m.group(0)[:60])
    return None


def anchors_of(sentence: str) -> list[str]:
    out = [m.group(0) for m in ANCHOR.finditer(sentence)]
    out += [m.group(1) for m in QUOTE.finditer(sentence)]
    seen, uniq = set(), []
    for a in out:
        k = SC._norm(a).lower()
        if k not in seen:
            seen.add(k)
            uniq.append(a)
    return uniq


def _identifiers_of(src: dict) -> list[str]:
    """Identifiers a sentence could NAME: the registry number, the DOI, the PMID."""
    url = src.get("url") or ""
    out = []
    for pat in (r"(NCT\d{8})", r"(10\.\d{4,9}/[^\s?#]+)",
                r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})"):
        m = re.search(pat, url, re.I)
        if m:
            out.append(m.group(1).rstrip(".,;)"))
    for k in ("nct", "doi", "pubmed"):
        if src.get(k):
            out.append(str(src[k]))
    return out


def _doc_texts(slug: str) -> dict[str, str]:
    out = {}
    for sid in sorted(store.held(slug) or {}):
        t = SC._text(slug, sid)
        if t:
            out[sid] = SC._norm(t)
    return out


def _window(doc: str, anchors: list[str]) -> tuple[str, str] | None:
    """(span, envelope) — the smallest passage containing every anchor,
    widened to sentence boundaries, with context either side."""
    low = doc.lower()
    pos = []
    for a in anchors:
        i = low.find(SC._norm(a).lower())
        if i < 0:
            return None
        pos.append((i, i + len(a)))
    start, end = min(p[0] for p in pos), max(p[1] for p in pos)
    if end - start > MAX_WINDOW:
        return None
    # widen to the source's own sentence boundaries
    s = doc.rfind(". ", 0, start)
    s = 0 if s < 0 else s + 2
    e = doc.find(". ", end)
    e = len(doc) if e < 0 else e + 1
    span = doc[s:e].strip()
    env = doc[max(0, s - 220):min(len(doc), e + 220)].strip()
    return span, env


def propose(slug: str, *, limit: int | None = None) -> dict:
    doc = B.load(slug)
    rows = doc.get("bindings") or {}
    texts = _doc_texts(slug)
    stat = {"proposed": 0, "ambiguous": 0, "no_anchor": 0, "not_found": 0,
            "already": 0, "b5_flag": 0, "b6_flag": 0}
    done = 0
    for sha, row in rows.items():
        if not row.get("on_page"):
            continue
        if row.get("span"):
            stat["already"] += 1
            continue
        if limit and done >= limit:
            break
        shape = shape_of(row["sentence"])
        if shape:
            stat[shape[0]] = stat.get(shape[0], 0) + 1
            row["locator_type"] = "none" if shape[0] == "arithmetic" else None
            row["autobind"] = shape[1]
            continue
        anc = anchors_of(row["sentence"])
        strength = sum(anchor_strength(a) for a in anc)
        if len(anc) < MIN_ANCHORS or strength < MIN_STRENGTH:
            stat["no_anchor"] += 1
            row["autobind"] = ("anchors too weak to identify a document: %s "
                               "(strength %d, need %d)"
                               % (", ".join(anc[:6]) or "none", strength,
                                  MIN_STRENGTH))
            continue
        # A SENTENCE THAT NAMES AN IDENTIFIER HAS NAMED ITS SOURCE.
        #
        # "the trial's own results posting on ClinicalTrials.gov (NCT01958021)"
        # says where it came from. Search found NCT01958021 and "2.5%" together
        # in a repository abstract page and bound the sentence there, while the
        # registry record it names sat in the library unconsidered. Provenance
        # the sentence states beats provenance inferred from co-occurrence.
        named = [sid for sid, src in
                 ((x["id"], x) for x in store.sources(slug))
                 if sid in texts and any(
                     re.search(r"\b%s\b" % re.escape(i), row["sentence"], re.I)
                     for i in _identifiers_of(src))]
        candidates = {k: texts[k] for k in named} if len(named) == 1 else texts
        hits = []
        for sid, text in candidates.items():
            w = _window(text, anc)
            if w:
                hits.append((sid, w))
        done += 1
        if not hits:
            stat["not_found"] += 1
            row["autobind"] = ("no held document contains all %d anchors: %s"
                               % (len(anc), ", ".join(anc[:5])))
            continue
        if len(hits) > 1:
            stat["ambiguous"] += 1
            row["autobind"] = ("%d held documents contain all these anchors (%s) "
                               "— which one the sentence rests on is not "
                               "decidable by presence alone"
                               % (len(hits), ", ".join(h[0] for h in hits[:5])))
            continue
        sid, (span, env) = hits[0]
        # THE SPAN MUST BE ABOUT WHAT THE SENTENCE IS ABOUT. A passage that
        # shares only digits with the sentence is a coincidence of numbers; the
        # first run bound an argument about p-values to a table of patient
        # characteristics on exactly that basis.
        shared = content_words(row["sentence"]) & content_words(span)
        if len(shared) < 2:
            stat["ambiguous"] += 1
            row["autobind"] = ("the only document with these anchors (%s) shares "
                               "no subject matter with the sentence — %d word(s) "
                               "in common, so the numbers coincide and the "
                               "passage does not" % (sid, len(shared)))
            continue
        row.update(source_id=sid, span=span[:1200], envelope=env[:2000],
                   locator_type="prose",
                   document_sha=(store.held(slug).get(sid) or {}).get("sha256"),
                   proposed_by="autobind", confirmed=False,
                   autobind="the only held document containing all %d anchors "
                            "(%s), sharing %d subject word(s) with the sentence: %s"
                            % (len(anc), ", ".join(anc[:5]), len(shared),
                               ", ".join(sorted(shared)[:6])))
        stat["proposed"] += 1
        ok5, why5 = SC.b5_complete(span[:1200], slug, sid)
        if not ok5:
            row.setdefault("flags", []).append({"check": "B5", "why": why5})
            stat["b5_flag"] += 1
        bad6 = SC.b6_scope(row["sentence"], span)
        if bad6:
            row.setdefault("flags", []).append(
                {"check": "B6", "why": "; ".join(w for w, _ in bad6)})
            stat["b6_flag"] += 1
    B.save(slug, doc)
    return stat


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    st = propose(args.slug, limit=args.limit)
    total = sum(st.get(k, 0) for k in ("proposed", "ambiguous", "no_anchor",
                                       "not_found", "already", "arithmetic",
                                       "about_a_document"))
    print("\n  %s — %d empirical sentence(s)\n" % (args.slug, total))
    print("    %4d bound by autobind, unconfirmed" % st["proposed"])
    print("    %4d already had a span" % st["already"])
    print("    %4d ambiguous — several held documents contain all the anchors"
          % st["ambiguous"])
    print("    %4d no held document contains all the anchors" % st["not_found"])
    print("    %4d too few anchors to search on" % st["no_anchor"])
    print("    %4d our own arithmetic — bound to nothing, correctly"
          % st.get("arithmetic", 0))
    print("    %4d a claim about where a figure appears, not a claim from it"
          % st.get("about_a_document", 0))
    print()
    print("    of the proposals: %d flagged by B5 (truncation), %d by B6 (scope)"
          % (st["b5_flag"], st["b6_flag"]))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
