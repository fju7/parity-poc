#!/usr/bin/env python3
"""Lean WHU's coverage rules (lean.py item 4), used by coverage_check only when
lean.enabled().

(a) NOT A HEADLINE UNIT. coverage_check.units_of cuts a source's headline
    sections into sentences by structure, and a PDF's text layer puts figure
    text, axis ticks, legends, table cells, author and abbreviation lists and
    running heads inside those sections. In round 1 each was taken as a
    finding: WHO's recommendation-category legend (WHU-Q1-01), an
    abbreviations list and the author line "Kuper H, Saran A, White H"
    (WHU-Q1-02), SPM figure and page text (WHU-Q1-03, WHU-Q1-04).
    `furniture(text)` names which of these a unit is, or None; such a unit is
    never a headline unit (it is listed apart in the row, with its kind).
(b) ALREADY STATED. A unit the page already states (a page sentence carrying
    its content words and every number it gives, `already_stated`) is
    recorded as "already stated" -- accounted for, not counted against the
    declarations budget, never on the readers' list.
(c) THE DECLARATIONS BUDGET IS ENFORCED: past the budget is a STOP, whether
    or not someone signed the extra declarations off.
(d) Each readers'-list line names its source with a numbered citation, the
    source's place in sources.json ("<label> [n]", lean_sentences.number).

    python3 lean_coverage.py <slug> record   write "already stated" for the
                                             units the page states (coverage.json)
"""
from __future__ import annotations

import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ALREADY = "already_stated"
STATED_SHARE = 0.6               # content words of the unit found in one page sentence
STATED_MIN_WORDS = 4

_FUNCTION = frozenset("""a an and are as at be been by can for from has have in into is it its may of on or
that the their there these this those to was were which will with would than not more over under
between during since per while""".split())
_NUM = re.compile(r"(?<![A-Za-z])[–−-]?\d+(?:[.,]\d+)?%?(?![A-Za-z])")
_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_PANEL_END = re.compile(r"(?:^|\s)\(?[a-h][.)]\s*$")
_UNITS = re.compile(r"\byr\s*[–−-]\s*1\b|\(°C\)|\bGtCO2|\bMtN2O|\bMtCH4|\bGtC\b|\(standard deviation", re.I)
_RUNNING = re.compile(r"\b\d{1,3}\s+SPM\s+Summary for Policymakers\b|\bSummary for Policymakers\s+[a-z]\b"
                      r"|\bSPM\s+Summary for Policymakers\s*$|^\W*Summary for Policymakers\b")
_FOOTER = re.compile(r"pre-final-publication version|subject to (?:final )?(?:copy-?editing|error correction)"
                     r"|\bDownloaded from\b|\bPage \d+ of \d+\b|\bAll rights reserved\b|^\s*©"
                     r"|\bThis article is protected by copyright\b", re.I)
_XREF = re.compile(r"^\W*See (?:footnote|Figure|Table|Box|Section|Annex|Chapter)\b")
_CAPTION = re.compile(r"^\W*(?:Figure|Fig\.|Table|Panel)\s*(?:SPM|TS)?[.\s]*[\dA-Z(]")
_AUTHORS_LEAD = re.compile(r"^\W*(?:Authors?|With support from|Contributors?|Affiliations?|Correspondence"
                           r"|Corresponding author|Peer reviewers?|Editors?)\s*:", re.I)
_CITE_NAME = re.compile(r"\b[A-Z][a-z’'-]+\s[A-Z]{1,3}\b,?")                  # "Kuper H,"
_FULL_NAME = re.compile(r"\b[A-Z][a-z]+\s[A-Z][a-z’'-]+\d")                   # "Hannah Kuper1"
_ABBREV_LEAD = re.compile(r"^\W*(?:List of )?Abbreviations?\b|^\W*Acronyms\b", re.I)
_ACRONYM = re.compile(r"\b(?:\d?[A-Z]{2,}[a-z]?\d*|\d[a-z]{1,3})\b")


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("−", "-"), ("\x07", " ")):
        s = s.replace(a, b)
    return " ".join(s.split())


_REFS = re.compile(r"\{[^{}]*\}|\((?:Figure|Table|Box|Glossary|Cross-)[^()]*\)"
                   r"|\((?:very low|low|medium|high|very high) confidence\)", re.I)
_NAME_LIST = re.compile(r"(?:\b[A-Z][a-z’'-]+ [A-Z]{1,3},\s*){2,}(?:and\s+)?[A-Z][a-z’'-]+ [A-Z]{1,3}\b")
STATEMENT_WORDS = 8              # a remainder this long, once furniture is removed, is a statement


def _strip(t: str) -> str:
    """T without its section references, running heads and footers."""
    t = _REFS.sub(" ", t)
    t = _RUNNING.sub(" ", t)
    t = re.sub(r"This pre-final-publication version of the AR6 \w+ SPM approved text is subject to error "
               r"correction\.?", " ", t)
    t = _FOOTER.sub(" ", t)
    return " ".join(t.split())


def furniture(text: str) -> str | None:
    """Which kind of non-finding text TEXT is, or None for a finding."""
    t = _fold(text)
    lead = t.split(" ", 1)[0] if t else ""
    if lead and all(not c.isascii() and unicodedata.category(c)[0] in "LS" for c in lead) \
            and len(t.split()) > 1 and t.split()[1][:1].islower():
        return "legend text"                               # icon-font glyphs then a category label
    if _AUTHORS_LEAD.search(t) or _NAME_LIST.search(t) or len(_FULL_NAME.findall(t)) >= 2:
        return "author list"
    if _ABBREV_LEAD.search(t):
        return "abbreviation list"
    rest = _strip(t)
    words = _WORD.findall(rest)
    nums = _NUM.findall(rest)
    if _XREF.search(rest):
        return "page header or footer"
    if (_FOOTER.search(t) or _RUNNING.search(t)) and len(words) < STATEMENT_WORDS:
        return "page header or footer"
    if len(words) < 3:
        return "section references or bare numbers"
    func = sum(1 for w in words if w.lower() in _FUNCTION)
    if len(nums) >= 6 and len(nums) / (len(words) + len(nums)) >= 0.35 and func / len(words) < 0.15:
        return "figure or table text"
    if _CAPTION.search(rest) and len(words) < 2 * STATEMENT_WORDS and func / len(words) < 0.2:
        return "figure axis or legend text"
    if (_PANEL_END.search(rest) or _UNITS.search(rest)) and len(words) <= 10:
        return "figure axis or legend text"
    return None


def _content(s: str) -> list[str]:
    import passage_index as P
    return [w for w in P.tokens(s) if not w[0].isdigit()]


_LABEL = re.compile(r"(?<![\w.])[A-E]\.\d{1,2}(?:\.\d{1,2})?\b")


def _numbers(s: str) -> set[str]:
    """The figures S gives: section references and statement labels (A.1.7) aside."""
    t = _LABEL.sub(" ", _REFS.sub(" ", _fold(s)))
    return {n.lstrip("-–−").rstrip("%") for n in _NUM.findall(t)}


def already_stated(text: str, page_sentences: list[str]) -> str | None:
    """The page sentence that states TEXT, or None: one carrying at least
    STATED_SHARE of the unit's content words and every number the unit gives."""
    want = set(_content(text))
    nums = _numbers(text)
    if len(want) < STATED_MIN_WORDS:
        return None
    best, score = None, 0.0
    for s in page_sentences:
        have = set(_content(s))
        share = len(want & have) / len(want)
        if share >= STATED_SHARE and nums <= _numbers(s) and share > score:
            best, score = s, share
    return best


def cite_label(label: str, sources: list[dict], sid: str) -> str:
    """"<label> [n]" (d)."""
    import lean_sentences as LS
    try:
        return "%s [%d]" % (label, LS.number(sources, sid))
    except KeyError:
        return label


def split_units(units: list[dict]) -> tuple[list[dict], list[dict]]:
    """(headline units, the furniture units with their kind) (a)."""
    keep, out = [], []
    for u in units:
        k = furniture(u.get("text") or "")
        (out if k else keep).append(dict(u, furniture=k) if k else u)
    return keep, out


def record(slug: str, by: str = "code (lean_coverage.py)") -> list[dict]:
    """Write "already stated" into coverage.json for every headline unit with
    no state that the page states, with the page sentence's fingerprint."""
    import bindings as B
    import coverage_check as C
    import json
    import ruling as R
    import source_store as store
    case = store.case_dir(slug)
    rows = B.load(slug).get("bindings") or {}
    held = R.held_texts(slug)
    page = B.page_sentences(slug)
    import omissions as O
    import premise as PM
    srcs = {s["id"]: s for s in C._sources(slug)}
    spans = C.bound_ranges(rows, held)
    units = []
    for sid in C.relied_on(slug, rows, PM.load(slug) or {}):
        if sid in held:
            units += split_units(C.units_of(srcs.get(sid) or {"id": sid}, held[sid], spans.get(sid)))[0]
    cov = C.load(case)
    decl = cov.setdefault("declarations", {})
    done = []
    for u in C.account(units, rows, held, O.load(case), decl):
        if u["state"] != "none":
            continue
        s = already_stated(u["text"], page)
        if s:
            decl[u["key"]] = {"state": ALREADY, "reason": "already stated on the page", "by": by,
                              "page_sentence_sha": B.fingerprint(s), "text_sha256": C.sha(u["text"]),
                              "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            done.append({"key": u["key"], "sentence": s})
    if done:
        (case / C.RECORD).write_text(json.dumps(cov, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return done


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[1] != "record":
        print(__doc__)
        return 2
    for d in record(argv[0]):
        print("  %s already stated: %r" % (d["key"], d["sentence"][:90]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
