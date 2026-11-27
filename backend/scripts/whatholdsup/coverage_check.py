#!/usr/bin/env python3
"""Which of its sources' headline conclusions does the page account for?

Post-study fix 2, step 7 (2026-10-27). docs/whu-fix2-omission-rulings-design.md,
section 3; the advisor's ruling 3 of 27 October 2026 for the reader-facing list.

    coverage_check.py SLUG                     the units, their states, and the rows
    coverage_check.py SLUG declare KEY out_of_scope|not_material --why "..." --by "..." [--element "..."]
    coverage_check.py SLUG render              the HTML for the page's list of declared findings

Every check before this one starts from a sentence on the page. This one starts
from a SOURCE the page relies on and lists its headline conclusions, so that a
finding the draft never wrote is visible (WHU-S07: the page used one sentence
of SPM C.8.2 and none of the three after it).

WHICH SOURCES. Relied on: named in premise.json what_the_sources_show.sources,
or the source of at least RELIED_ROWS on-page binding rows.

WHICH UNITS. Read from the document's own structure, in the held text the
binding checks read (ruling.held_texts), never from any answer key or study
tool (design ruling 1), and never from a title (advisor's ruling on step 7,
2026-10-27: S08's chapter was missed because its title lacks "Chapter"):
  - an assessment chapter -- an "Executive Summary" heading followed by
    calibrated language: each Executive Summary PARAGRAPH (IPCC paragraphs end
    with their "{6.1; 6.2}" section references) that the page binds, IN FULL;
  - an assessment summary -- at least SPM_MIN_LABELS numbered statements (A.1,
    C.8.2, ...) followed by calibrated language: each numbered statement the
    page binds, IN FULL (to the next numbered statement, heading, or "Figure
    SPM." / "Table SPM." caption, whichever comes first);
  - otherwise an abstract: every sentence after the first "Authors'
    conclusions" heading (or a "Conclusion(s)" / "Interpretation" heading in
    the first ABSTRACT_CHARS characters) up to the next heading, WHOLE; in a
    systematic review's abstract (an "Authors' conclusions" heading, or
    "systematic review" / "meta-analysis" in its opening), every sentence of
    its "Main results" / "Synthesis of results" section too; and the other
    sentences before the conclusions that carry a certainty or confidence term
    (abstract results).
A source with none of these yields no units, and the row says so (WARN).

KNOWN LIMIT (recorded in the row's own output). An assessment conclusion in a
numbered statement or Executive Summary paragraph the page never binds is not a
unit here, so this check cannot see it; the source advocate's LEAVES_OUT
objections (ruling.py omissions) are the second net. Taking every statement
instead gave WHU-S07 367 units -- unaccountable by hand.

THE STATES. used (an on-page binding span lies inside the unit); added (an ADD
in omissions.json overlaps it); declared (out_of_scope or not_material: here, by
`declare`, or by an omission ruling in omissions.json); none -- a STOP.

THE READERS' LIST (ruling 3). Every declared finding, from either place, is
shown on the page inside the limits section, one sentence each:
    Outside this question: "<short verbatim span>" (<source>); <reason>.
    Judged not material to this question: "<span>" (<source>); <reason>.
    Not added: "<span>" (<source>); the page's limit for additions|declarations was reached.
under the heading "Findings in our sources we judged outside this question".
These are scope statements, protected under fix 1 (bindings.protected_kind,
kind "scope"). The row STOPs if a declaration is not on the page word for word,
or if the page carries such a sentence with no declaration behind it.
Declarations past omissions.declaration_budget need a person's sign-off. The
budget counts agent declarations (out_of_scope, not_material); a not_added_cap
line follows from a cap and is not counted (2026-10-28).
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OK, BAD, WARN = "ok", "BLOCKED", "warn"
ROW_UNITS = "headline conclusions accounted for"
ROW_LIST = "declared findings shown to readers"
RECORD = "coverage.json"
RELIED_ROWS = 3
ABSTRACT_CHARS = 8000
SECTION_MAX = 2500
SPAN_WORDS = 25
DECLARED = ("out_of_scope", "not_material", "not_added_cap")
COUNTED = ("out_of_scope", "not_material")    # what the declarations budget counts
HEADING = "Findings in our sources we judged outside this question"
LEAD = {"out_of_scope": "Outside this question:", "not_material": "Judged not material to this question:",
        "not_added_cap": "Not added:", "not_added_no_place": "Not added:", "not_added_beyond": "Not added:",
        "not_added_over_budget": "Not added:", "not_added_not_one_sentence": "Not added:",
        "not_added_anchor_removed": "Not added:", "not_stated_removed": "Not added:"}
# Lean WHU (process doc §4.6.1, the ruling paths): code's own line for an ADD with no
# place on the page; a required page element, and not counted against the budget.
NO_PLACE = "not_added_no_place"
NO_PLACE_TAIL = "(no place on the page)"
# Lean rule 3a: an ADD whose span is not in the finding (code refused it).
BEYOND = "not_added_beyond"
BEYOND_TAIL = "(the proposed sentence went beyond the finding)"
# Lean, after Q1-04b: an ADD past the additions budget (code's line; no person asked).
OVER_BUDGET = "not_added_over_budget"
OVER_BUDGET_TAIL = "(over the additions budget)"
# After attempt 15 (advisor, 2026-11-23): a sentence the model could not write as one sentence, twice.
NOT_ONE = "not_added_not_one_sentence"
NOT_ONE_TAIL = "(it could not be written as one sentence)"
# Advisor's ruling 1 on P152: an ADD removed with the sentence it followed (orch/apply.py, the anchor cascade).
ANCHOR = "not_added_anchor_removed"
ANCHOR_TAIL = "(found in our sources, not stated on this page: the sentence it followed was removed)"
# Advisor's ruling 3 on P152: a headline unit coverage decided as USED whose every on-page statement a later record
# removed (the fresh Q1-01's two S003 units, removed by the overstatement fail-safe) -- computed by load(), never
# written to coverage.json; not counted against the declarations budget.
REMOVED = "not_stated_removed"
REMOVED_TAIL = "(found in our sources, not stated on this page: the sentence that stated it was removed)"
CODE_LINES = {NO_PLACE: NO_PLACE_TAIL, BEYOND: BEYOND_TAIL, OVER_BUDGET: OVER_BUDGET_TAIL, NOT_ONE: NOT_ONE_TAIL,
              ANCHOR: ANCHOR_TAIL, REMOVED: REMOVED_TAIL}
CAP_REASON = "the page's limit for %s was reached"     # not_added_cap's reader-facing reason

CALIBRATED = re.compile(r"\b(?:very\s+low|low|medium|high|very\s+high)\s+confidence"
                        r"|\b(?:limited|medium|robust)\s+evidence\b"
                        r"|\b(?:low|medium|high)\s+agreement"
                        r"|\b(?:very\s+low|low|moderate|high)[\s-]+(?:certainty|quality)\b", re.I)
_CONCL = re.compile(r"\bAuthors[’']?\s+[Cc]onclusions\b")
_CONCL_ABSTRACT = re.compile(r"(?<![a-z])(?:Conclusions?|Interpretation)\s*:?\s+(?=[A-Z])")
_SR = re.compile(r"\bsystematic review|\bmeta-?analys[ie]s\b", re.I)
_MAIN_RESULTS = re.compile(r"\b(?:Main [Rr]esults|Synthesis of results)\b")
_STOP_HEADING = re.compile(
    r"\b(?:Implications for (?:practice|research)|Funding|Registration|Plain [Ll]anguage [Ss]ummary|"
    r"PLAIN LANGUAGE SUMMARY|Summary of findings|Editorial note|Keywords|Key words|Background|BACKGROUND|"
    r"Introduction|INTRODUCTION|\d+\.\s+[A-Z][A-Z ]{4,})\b")
_SPM_LABEL = re.compile(r"(?<![\w.])([A-E]\.\d{1,2}(?:\.\d{1,2})?)\s+\x07?(?=[A-Z])")
SPM_MIN_LABELS = 5
SPM_MAX = 3000                   # a statement with no boundary found runs this far, as before
# WHERE AN SPM STATEMENT STOPS (post-study, mid-rerun tool fix, 2026-10-28):
# the next numbered statement, a section heading ("B. Recent developments"),
# or a figure or table caption ("Figure SPM.3", "Table SPM.1"), whichever comes
# first. Before, it ran to the next numbered statement, so a caption printed
# between two statements was read as part of the first (WHU-S07r). A caption
# or heading named inside a statement's own brackets -- "{3.2; Figure SPM.2}"
# -- is a reference, not a boundary.
_SPM_HEADING = re.compile(r"(?<![\w.])[A-E][.:]\s+(?=[A-Z][a-z])")
_SPM_CAPTION = re.compile(r"\b(?:Figure|Table)\s+SPM\.")
ES_MAX = 30000                   # an Executive Summary is a few pages, never the chapter
LIMIT = ("Known limit: an assessment conclusion in a statement or Executive Summary paragraph the page "
         "never binds is not covered here; the advocate's LEAVES_OUT objections are the second net.")
_ES = re.compile(r"Executive Summary\s+(?=[A-Z][a-z])")
_ES_END = re.compile(r"\b\d{1,2}\.1\s+Introduction\b|Frequently Asked Questions|\bFAQ\s+\d")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(“\"])")


def sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _sentences(text: str, base: int) -> list[tuple[int, int, str]]:
    """(start, end, text) of each sentence of TEXT, offsets shifted by BASE."""
    out, i = [], 0
    for m in list(_SENT.finditer(text)) + [None]:
        j = m.start() if m else len(text)
        s = text[i:j]
        lead = len(s) - len(s.lstrip())
        s = s.strip()
        if len(s.split()) >= 5:
            out.append((base + i + lead, base + i + lead + len(s), s))
        i = m.end() if m else j
    return out


def _region(text: str, start: int, cap: int = SECTION_MAX) -> tuple[int, int]:
    end = min(len(text), start + cap)
    m = _STOP_HEADING.search(text, start + 1, end)
    return start, (m.start() if m else end)


def _es_region(text: str) -> tuple[int, int] | None:
    """The Executive Summary's body: after a heading followed by calibrated
    language (not the table of contents), up to the first numbered section."""
    for m in _ES.finditer(text):
        if CALIBRATED.search(text[m.end():m.end() + 400]):
            end_m = _ES_END.search(text, m.end(), m.end() + ES_MAX)
            return m.end(), (end_m.start() if end_m else min(len(text), m.end() + ES_MAX))
    return None


def _spm_labels(text: str) -> list:
    """Numbered statements followed by calibrated language, when there are at
    least SPM_MIN_LABELS of them; else none (an assessment summary's shape)."""
    labels = list(_SPM_LABEL.finditer(text))
    real = [m for k, m in enumerate(labels)
            if CALIBRATED.search(text[m.end():(labels[k + 1].start() if k + 1 < len(labels) else m.end() + 3000)])]
    return labels if len(real) >= SPM_MIN_LABELS else []


def _spm_end(text: str, start: int, end: int) -> int:
    """The first heading or caption in text[start:end] outside the statement's
    own brackets, else END."""
    hits = sorted([m.start() for m in _SPM_HEADING.finditer(text, start, end)]
                  + [m.start() for m in _SPM_CAPTION.finditer(text, start, end)])
    for h in hits:
        depth = 0
        for ch in text[start:h]:
            if ch in "{([":
                depth += 1
            elif ch in "})]" and depth:
                depth -= 1
        if not depth:
            return h
    return end


def groups_of(text: str) -> tuple[str, list[tuple[int, int, str]]]:
    """(kind, [(start, end, section)]) of an assessment's statements or
    Executive Summary paragraphs; ("", []) for any other document."""
    es = _es_region(text)
    if es:
        s0, e0 = es
        out, i, n = [], s0, 0
        for m in re.finditer(r"\}", text[s0:e0]):
            j = s0 + m.end()
            if len(text[i:j].split()) >= 8:
                n += 1
                out.append((i, j, "Executive Summary \u00b6%d" % n))
            i = j
        # Text after the last "{...}" is not a paragraph: every IPCC Executive
        # Summary paragraph ends with its section references (WHU-S07's
        # chapter 10, whose end heading was not found, ran to 341,628 chars).
        return "chapter", out
    labels = _spm_labels(text)
    if labels:
        out = []
        for k, m in enumerate(labels):
            e = labels[k + 1].start() if k + 1 < len(labels) else min(len(text), m.end() + SPM_MAX)
            out.append((m.start(), _spm_end(text, m.end(), e), "SPM %s" % m.group(1)))
        return "summary", out
    return "", []


def units_of(source: dict, text: str, bound: list[list[int]] | None = None) -> list[dict]:
    """Headline units of one held document: [{source, at, section, text}].
    BOUND: the offsets of the page's binding spans in this document; an
    assessment's statement or paragraph is a unit group only if one lies in it."""
    sid = source.get("id")
    bound = bound or []
    out: list[dict] = []

    def add(s: int, e: int, section: str):
        if not any(u["at"] == [s, e] for u in out):
            out.append({"source": sid, "at": [s, e], "section": section, "text": text[s:e]})

    kind, groups = groups_of(text)
    if kind:
        for g0, g1, section in groups:
            if any(b[0] < g1 and g0 < b[1] for b in bound):
                for s, e, _t in _sentences(text[g0:g1], g0):
                    add(s, e, section)
        return out
    m = _CONCL.search(text)
    review = m is not None or bool(_SR.search(text[:ABSTRACT_CHARS]))
    if m is None:
        m = _CONCL_ABSTRACT.search(text, 0, ABSTRACT_CHARS)
    if m is not None:
        a0 = max(0, m.start() - ABSTRACT_CHARS)
        # A SYSTEMATIC REVIEW's abstract: every sentence of its main-results
        # section is a unit, as its conclusions are (advisor's ruling,
        # 2026-10-27: WHU-S06's conditions-for-engagement finding sits in "Main
        # Results" and carries its confidence in the NEXT sentence). Elsewhere a
        # results sentence counts only if it carries a certainty term.
        mr = None
        if review:
            mr = [x for x in _MAIN_RESULTS.finditer(text, a0, m.start())]
            mr = mr[-1] if mr else None
        if mr is not None:
            for s, e, _t in _sentences(text[mr.end():m.start()], mr.end()):
                add(s, e, "abstract main results")
        for s, e, tx in _sentences(text[a0:m.start()], a0):
            if CALIBRATED.search(tx) and not (mr is not None and e > mr.start()):
                add(s, e, "abstract results")
        s0, e0 = _region(text, m.end())
        for s, e, _t in _sentences(text[s0:e0], s0):
            add(s, e, "abstract conclusions")
    return out


# ---------------------------------------------------------------- the issue

def _sources(slug: str) -> list[dict]:
    import source_store as store
    p = store.case_dir(slug) / "sources.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    return [s for s in (d.get("sources", d) if isinstance(d, dict) else d) if isinstance(s, dict)]


def relied_on(slug: str, rows: dict, premise_doc: dict | None, sources: list[dict] | None = None) -> list[str]:
    """Named in the premise, the source of RELIED_ROWS on-page rows, or an
    assessment summary added for a chapter held (acquire_sources, fix 3)."""
    import audit_stage as A
    named = list(((premise_doc or {}).get("what_the_sources_show") or {}).get("sources") or [])
    srcs = sources if sources is not None else _sources(slug)
    named += [s["id"] for s in srcs if str(s.get("added_by") or "").startswith("acquire_sources.py: assessment-summary")]
    counts: dict[str, int] = {}
    for r in rows.values():
        if r.get("on_page"):
            for sid in A.sources_of(r):
                counts[sid] = counts.get(sid, 0) + 1
    return list(dict.fromkeys(named + sorted(s for s, n in counts.items() if n >= RELIED_ROWS)))


def unit_key(u: dict) -> str:
    return "%s@%d-%d" % (u["source"], u["at"][0], u["at"][1])


def load(case: Path, raw: bool = False) -> dict:
    """coverage.json; unless RAW, with every headline unit whose on-page statement a later record removed added as a
    REMOVED declaration (removed_units; an existing decision for the unit is kept). Writers load RAW."""
    p = case / RECORD
    doc = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"units": [], "declarations": {}}
    if not raw:
        decl = doc.setdefault("declarations", {})
        for k, v in removed_units(case).items():
            decl.setdefault(k, v)
    return doc


def removed_units(case: Path) -> dict:
    """{unit key: declaration} for each headline unit of a relied-on source that has NO on-page binding now and an
    off-page one a record removed (off_page_by): the page stated it and a later step took the statement off. Code's
    own line on the readers' list (REMOVED); computed from bindings.json each time, never written."""
    case = Path(case)
    bp = case / "bindings.json"
    if not bp.exists():
        return {}
    try:
        rows = json.loads(bp.read_text(encoding="utf-8")).get("bindings") or {}
    except ValueError:
        return {}
    import bindings as B
    gone = [r for r in rows.values() if not r.get("on_page") and r.get("off_page_by") and not B.is_declaration_row(r)]
    if not gone:
        return {}
    try:
        slug = json.loads((case / "issue.json").read_text(encoding="utf-8")).get("slug")
    except (OSError, ValueError):
        return {}
    import premise as PM
    import ruling as R
    import audit_stage as A
    held = R.held_texts(slug)
    on = bound_ranges(rows, held)
    off: dict[str, list] = {}
    for r in gone:
        for sid, q in R.quotations(r, held):
            at = A.locate(q, held.get(sid) or "")
            if at:
                off.setdefault(sid, []).append((list(at), r.get("off_page_by")))
    if not off:
        return {}
    import lean
    srcs = {s["id"]: s for s in _sources(slug)}
    out = {}
    for sid in relied_on(slug, rows, PM.load(slug) or {}):
        if sid not in off or sid not in held:
            continue
        units = units_of(srcs.get(sid) or {"id": sid}, held[sid], on.get(sid))
        if lean.enabled():
            import lean_coverage as LC
            units = LC.split_units(units)[0]
        for u in units:
            if any(_overlaps(x, u["at"]) for x in on.get(sid, [])):
                continue
            by = sorted({b for at, b in off[sid] if _overlaps(at, u["at"]) and b})
            if by:
                out[unit_key(u)] = {"state": REMOVED, "reason": "the page sentence that stated it was removed",
                                    "removed_by": by, "by": "code (ruling 3 on P152)", "decided_at": ""}
    return out


def _overlaps(a: list, b: list) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def bound_ranges(rows: dict, held: dict[str, str]) -> dict[str, list[list[int]]]:
    """{source id: [[start, end]]} of every on-page binding span, located in its held text."""
    import audit_stage as A
    import ruling as R
    spans: dict[str, list[list[int]]] = {}
    import bindings as B
    for r in rows.values():
        if not r.get("on_page") or B.is_declaration_row(r):
            continue               # a readers'-list line shows a declaration; it does not use the unit
        for sid, q in R.quotations(r, held):
            at = A.locate(q, held.get(sid) or "")
            if at:
                spans.setdefault(sid, []).append(list(at))
    return spans


def account(units: list[dict], rows: dict, held: dict[str, str], omissions_doc: dict,
            declarations: dict) -> list[dict]:
    """Each unit with its state: used, added, declared (with how), or none."""
    spans = bound_ranges(rows, held)
    out = []
    for u in units:
        k = unit_key(u)
        state, how = "none", ""
        if any(_overlaps(s, u["at"]) for s in spans.get(u["source"], [])):
            state = "used"
        else:
            hits = [e for e in omissions_doc.get("omissions") or []
                    if e.get("source") == u["source"] and e.get("at") and _overlaps(e["at"], u["at"])]
            add = [e for e in hits if e.get("outcome") == "ADD"]
            dec = [e for e in hits if e.get("outcome") in ("OUT_OF_SCOPE", "NOT_MATERIAL", "NOT_ADDED_CAP",
                                                           "NOT_ADDED_NO_PLACE", "NOT_ADDED_BEYOND",
                                                           "NOT_ADDED_OVER_BUDGET", "NOT_ADDED_NOT_ONE_SENTENCE",
                                                           "NOT_ADDED_ANCHOR_REMOVED")]
            if add:
                state, how = "added", add[0].get("key")
            elif k in declarations:
                state, how = declarations[k]["state"], "declared in coverage.json"
                if state == "already_stated":
                    how = "already stated on the page (lean WHU)"
            elif dec:
                state, how = dec[0]["outcome"].lower(), "omission ruling %s" % dec[0].get("ruling")
        out.append(dict(u, key=k, state=state, how=how))
    return out


# ---------------------------------------------------------------- the readers' list

def short_span(text: str, words: int = SPAN_WORDS) -> str:
    """TEXT -- the finding's own source span -- cut at WORDS words, verbatim; a
    trailing ellipsis marks a cut. Collapsed whitespace only. A span of more than
    one sentence is cut to one by declaration_sentence (2026-10-28: was cut at
    its first sentence here, with no ellipsis to say so)."""
    w = (text or "").split()
    return " ".join(w[:words]) + (" …" if len(w) > words else "")


# A STANDARD PHRASE WHERE THE REASON CARRIES LOCATIONS (post-study, mid-rerun
# tool fix, 2026-10-28). A public reason that quoted the source has the quotation
# replaced by its location ("[S003@1204-1311]", omissions.redact), which means
# nothing to a reader. With no reason_for_reader, the line says the outcome in
# standard words instead; the quotation is always the finding's own span.
_LOC_TAG = re.compile(r"\[S\w*@\d+-\d+\]")
STANDARD_REASON = {"out_of_scope": "Judged outside this question",
                   "not_material": "Judged not material"}


def line_reason(d: dict) -> str:
    """The reason a readers'-list line carries for declaration D: for
    not_added_cap, which cap; else the reader line (reader_reason), or the
    standard phrase for the outcome when that text carries a location tag or
    has no sentence that is not the ruling's working (one_line is empty)."""
    import omissions as O
    if d["state"] == "not_added_cap":
        return CAP_REASON % O.cap_of(d["reason"])
    text = d.get("for_reader") or ""
    return STANDARD_REASON[d["state"]] if _LOC_TAG.search(text) or not one_line(text) else text


# ONE READER-FACING LINE, NOT THE RULING'S WORKING (post-study, mid-rerun tool
# fix, 2026-10-28). WHU-S01r's reasons read "Step 1: The finding is in scope.
# Step 2: ..." and the readers' list printed "Step 1: The finding is in scope".
# The line is the record's reason_for_reader when it has one, else the reason's
# FINAL sentence -- its conclusion -- and never the ruling's working.
# WORKING IS ANY SENTENCE THAT MENTIONS "Step N" (post-study, mid-rerun tool fix
# 13, 2026-10-28), not only one that starts with it: WHU-S01r printed "Step 2 also
# fails: ..." and "Step 2 is therefore not reached." When every sentence is
# working, one_line is empty and line_reason gives the standard outcome phrase.
_STEP = re.compile(r"^\s*Step\s*\d+\s*[:.)\-–—]\s*", re.I)
_WORKING = re.compile(r"\bStep\s*\d+", re.I)


def one_line(reason: str) -> str:
    """The reason's last sentence that is not working (_WORKING), or ""."""
    parts = [p.strip() for line in (reason or "").splitlines()
             for p in _SENT.split(" ".join(line.split())) if p.strip()]
    plain = [p for p in parts if not _WORKING.search(p)]
    return plain[-1].rstrip(" .;")[:200] if plain else ""


def reader_reason(d: dict) -> str:
    """The reason a readers'-list line carries: reason_for_reader if present."""
    return (d.get("reason_for_reader") or "").strip() or d.get("reason") or ""


_CITE_NUMBER = re.compile(r"\s*(\[\d+\])\s*$")
_END_STOP = re.compile(r"[\s.?!\u2026]+$")


def safe_label(state: str, label: str, reason: str | None = None) -> str:
    """The label as it may stand in a readers'-list line (advisor's ruling 1 on P162, the text-assembly sweep): one
    that keeps the line one sentence whatever the span. A title's own end punctuation (".", "?", "!", "...") is dropped
    before its citation number (01c's S005, "... appointments. [5]"); if the label still splits the line, the line
    names the source by its number alone ("source [5]"), as lean_sentences.cite does."""
    import source_ledger as ledger

    def probe(lab: str) -> bool:
        return len(ledger.sentences(declaration_frame(state, "x", lab, reason))) == 1

    if probe(label or ""):
        return label or ""                  # a label that keeps the line one sentence is used exactly as given
    lab = " ".join((label or "").split())
    if probe(lab):
        return lab
    m = _CITE_NUMBER.search(lab)
    num, title = (m.group(1), lab[:m.start()]) if m else ("", lab)
    stripped = (_END_STOP.sub("", title) + (" " + num if num else "")).strip()
    if stripped and probe(stripped):
        return stripped
    return "source %s" % num if num else "source"


def declaration_frame(state: str, quoted: str, label: str, reason: str | None) -> str:
    """The readers'-list line for a quotation, a label and (non-lean) a reason, with nothing shortened."""
    if state in CODE_LINES:
        return "%s “%s” (%s) %s." % (LEAD[state], quoted, label, CODE_LINES[state])
    if reason is None:
        return "%s “%s” (%s)." % (LEAD[state], quoted, label)
    return "%s “%s” (%s); %s." % (LEAD[state], quoted, label, one_line(reason))


def declaration_sentence(state: str, span: str, label: str, reason: str | None) -> str:
    """One sentence, as the page is split (source_ledger.sentences): a span the
    splitter would break ("e.g. ...") is shortened, with an ellipsis, until the
    whole line is one sentence -- a second sentence would not carry the lead
    and so would not be protected."""
    import source_ledger as ledger
    cut = span.endswith(" …")
    words = span[:-2].split() if cut else span.split()
    label = safe_label(state, label, reason)

    def line(ws: list[str], c: bool) -> str:
        if state in CODE_LINES:
            # code's own words only: the span, the label, and why it was not added
            return "%s “%s” (%s) %s." % (LEAD[state], " ".join(ws) + (" …" if c else ""), label, CODE_LINES[state])
        if reason is None:
            # Lean WHU (process doc §4.6.1): no reason clause, no model-written prose.
            return "%s “%s” (%s)." % (LEAD[state], " ".join(ws) + (" …" if c else ""), label)
        return "%s “%s” (%s); %s." % (LEAD[state], " ".join(ws) + (" …" if c else ""), label, one_line(reason))

    while True:
        s = line(words, cut)
        if len(ledger.sentences(s)) <= 1:
            return s
        dotted = [i for i, w in enumerate(words) if "." in w]
        # first try ending at the first full stop, the stop dropped for the
        # ellipsis (". …" would split), so a span of two sentences keeps its
        # first; then before the word that carries it ("e.g.")
        if dotted and dotted[0] + 1 < len(words) and "." not in words[dotted[0]].rstrip("."):
            first = words[:dotted[0]] + [words[dotted[0]].rstrip(".")]
            if len(ledger.sentences(line(first, True))) <= 1:
                return line(first, True)
        words = words[:dotted[0]] if dotted and dotted[0] > 0 else words[:-1]
        cut = True
        if not words:
            return line([], True).replace("“ …”", "“…”")


def _label(sources: list[dict], sid: str) -> str:
    s = next((x for x in sources if x.get("id") == sid), {})
    for a in s.get("also_called") or []:
        if a and not a.lower().startswith("10."):
            return a
    t = (s.get("title") or sid).split(" — ")[0]
    return t[:60]


_CI_CLAUSE = re.compile(r"\([^()]*\b(?:IQR|CI|interquartile|confidence interval)\b[^()]*\)"
                        r"|\b(?:95\s*%\s*)?(?:CI|IQR)\b[^;)]*", re.I)
_FIG = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")
FIGURES_MIN = 2


def result_figures(text: str) -> list[str]:
    """The numbers a finding reports, without those inside a confidence or interquartile interval."""
    t = " ".join((text or "").replace("\u2010", "-").split())
    return _FIG.findall(_CI_CLAUSE.sub(" ", t))


def stated_by_figures(text: str, sentences: list[str]) -> str | None:
    """Ruling 4 on P157: the one sentence (bound to the declaration's source) that states every result figure of
    TEXT -- at least FIGURES_MIN of them -- else None."""
    want = set(result_figures(text))
    if len(want) < FIGURES_MIN:
        return None
    for s in sentences:
        if want <= set(_FIG.findall(" ".join((s or "").split()))):
            return s
    return None


def stated_on_page(d: dict, spans: dict, said: dict) -> str | None:
    """Ruling 4 on P157: how the page states declaration D's unit, or None. SPANS: {source: on-page binding spans};
    SAID: {source: on-page sentences bound to it}. A code line (CODE_LINES) is never dropped."""
    if d.get("state") in CODE_LINES or not d.get("at"):
        return None
    if any(_overlaps(x, d["at"]) for x in spans.get(d["source"], [])):
        return "an on-page binding of %s" % d["source"]
    return stated_by_figures(d.get("text") or "", said.get(d["source"], []))


def acquire_began(case: Path) -> str | None:
    """When the run's acquire step began: the chain row of the step before it (acquire starts as that step ends);
    None with no chain or no acquire row (then every declaration counts)."""
    p = Path(case) / "orchestrator" / "chain.jsonl"
    if not p.exists():
        return None
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    names = [r.get("step") for r in rows]
    if "acquire" not in names or names.index("acquire") == 0:
        return None
    return rows[names.index("acquire") - 1].get("at")


def budget_exempt(d: dict, scope: dict, case: Path, written_at: str | None = None) -> bool:
    """Ruling 1 on P157: an out_of_scope declaration does not count against the budget when code confirms its
    element names a specific scope.out element (scope_element_ok against scope.out only, not the question) AND the
    scope was written before the run's acquire began. Not material, an element naming no scope.out entry, or a scope
    written after acquire began: it counts."""
    import omissions as O
    if d.get("state") != "out_of_scope" or not (d.get("element") or "").strip():
        return False
    ok, _why = O.scope_element_ok(d["element"], dict(scope or {}, question=""))
    began, written = acquire_began(case), written_at or (scope or {}).get("written_at") or ""
    return bool(ok and began and written and written < began)


def budget_count(decls: list[dict], scope: dict | None = None, case: Path | None = None,
                 written_at: str | None = None) -> tuple[list, list, list]:
    """(counted, exempt, counted once already) over the declarations the budget counts (COUNTED states), in order."""
    counted, exempt, twice = [], [], []
    for d in decls:
        if d["state"] not in COUNTED:
            continue
        if case is not None and budget_exempt(d, scope or {}, case, written_at):
            exempt.append(d)
        elif any(c["source"] == d["source"] and c.get("at") and d.get("at") and _overlaps(c["at"], d["at"])
                 for c in counted):
            twice.append(d)
        else:
            counted.append(d)
    return counted, exempt, twice


def declarations(slug: str, held: dict[str, str], case: Path | None = None,
                 hidden: list | None = None) -> list[dict]:
    """Every declared finding the readers' list must show, oldest first:
    [{key, state, source, span, reason, by, signature, sentence, at}].
    HIDDEN, when given, receives the declarations lean keeps off the list
    (already stated, furniture), each with its reason."""
    import omissions as O
    import source_store as store
    case = case or store.case_dir(slug)
    srcs = _sources(slug)
    out = []
    for e in O.load(case).get("omissions") or []:
        if e.get("outcome") in ("OUT_OF_SCOPE", "NOT_MATERIAL", "NOT_ADDED_CAP", "NOT_ADDED_NO_PLACE",
                                "NOT_ADDED_BEYOND", "NOT_ADDED_OVER_BUDGET", "NOT_ADDED_NOT_ONE_SENTENCE",
                                "NOT_ADDED_ANCHOR_REMOVED") and e.get("at"):
            text = (held.get(e["source"]) or "")[e["at"][0]:e["at"][1]]
            out.append({"key": e["key"], "state": e["outcome"].lower(), "source": e["source"], "text": text,
                        "from": "omissions", "element": e.get("element") or "", "at": list(e["at"]),
                        "reason": e.get("reason") or "", "for_reader": reader_reason(e),
                        "by": e.get("by"), "signature": e.get("signature"),
                        "decided_at": e.get("decided_at") or ""})
    for k, d in (load(case).get("declarations") or {}).items():
        sid, rng = k.split("@")
        a, b = (int(x) for x in rng.split("-"))
        out.append({"key": k, "state": d["state"], "source": sid, "text": (held.get(sid) or "")[a:b],
                    "element": d.get("element") or "", "at": [a, b],
                    "reason": d.get("reason") or "", "for_reader": reader_reason(d),
                    "by": d.get("by"), "signature": d.get("signature"),
                    "decided_at": d.get("decided_at") or ""})
    out.sort(key=lambda d: d["decided_at"])
    import lean
    if lean.enabled():
        # Lean WHU (lean_coverage.py): a declaration of a finding the page
        # already states, or of text that is no finding at all (furniture), is
        # not shown to readers, and each line cites its
        # source by number.
        import lean_coverage as LC
        # "Not material" that the page's body already states becomes "already
        # stated" (process doc §4.6.1, the ruling paths; advisor, 2026-11-05):
        # lean coverage's own test, against BODY sentences only, so a
        # readers'-list line cannot state its own finding. The model's ruling
        # stays in omissions.json; this is computed from the records each time.
        body = _body_sentences(slug)
        for d in out:
            if d["state"] == "not_material" and d.get("from") == "omissions" and body:
                got = LC.already_stated(d["text"], body)
                if got:
                    d.update(state=LC.ALREADY, converted_from="not_material", stated_by=got)
        # A UNIT STATED ON THE PAGE IS NEVER DECLARED (advisor's ruling 4 on P157): a declaration whose span lies
        # under an on-page binding of its source, or whose result figures one on-page sentence bound to its source
        # states (stated_by_figures), is dropped from the readers' list; the record keeps the model's ruling.
        import bindings as _B
        try:
            _rows = _B.load(slug).get("bindings") or {}
        except (Exception, SystemExit):                 # no case folder (a demo slug): nothing is bound
            _rows = {}
        _spans = bound_ranges(_rows, held)
        _said: dict[str, list[str]] = {}
        import audit_stage as _A
        for r in _rows.values():
            if r.get("on_page") and not _B.is_declaration_row(r) and r.get("sentence"):
                for sid in _A.sources_of(r):
                    _said.setdefault(sid, []).append(r["sentence"])
        for d in out:
            got = stated_on_page(d, _spans, _said)
            if got:
                d.update(state=LC.ALREADY, converted_from=d["state"], stated_by=got)
        # a "no place" Not added line is code's, and required: never dropped as furniture
        def _off(d):
            return d["state"] == LC.ALREADY or (d["state"] not in CODE_LINES and LC.furniture(d["text"]))
        if hidden is not None:
            hidden.extend(d for d in out if _off(d))
        out = [d for d in out if not _off(d)]
    for d in out:
        label = _label(srcs, d["source"])
        if lean.enabled():
            label = LC.cite_label(label, srcs, d["source"])
        # Lean WHU (process doc §4.6.1): the line is generated from the records only;
        # a declaration's reason is model-written prose and stays in the record.
        # not_added_cap's reason is code's own wording (CAP_REASON) and is kept.
        reason = line_reason(d) if not lean.enabled() or d["state"] == "not_added_cap" else None
        d["sentence"] = declaration_sentence(d["state"], short_span(d["text"]), label, reason)
    if lean.enabled():
        # Lean's fail-safe (lean_failsafe.py; process doc §4.6.1, the ruling
        # paths): a line removed over an unresolved finding is not rendered. Its
        # declaration stays in the records. (After Q1-04c every readers'-list
        # line is a required element, so the fail-safe no longer removes one;
        # this still honours removals recorded before that.)
        import lean_failsafe as LF
        gone = LF.removed_words(slug)
        if gone:
            cut = [dict(d, removed=LF.OUTCOME) for d in out if LF.is_removed(d["sentence"], gone)]
            if hidden is not None:
                hidden.extend(cut)
            out = [d for d in out if not LF.is_removed(d["sentence"], gone)]
    return out


def _body_sentences(slug: str) -> list[str]:
    """The page's sentences that are neither protected (bindings.protected_kind)
    nor in a generated frame (lean_sentences.is_framed); [] with no page."""
    import bindings as B
    import lean_sentences as LS
    try:
        ps = B.page_sentences(slug)
    except (Exception, SystemExit):
        return []
    return [s for s in ps if not B.protected_kind(s) and not LS.is_framed(s)]


def render(decls: list[dict]) -> str:
    """The HTML for the limits section: the heading and one paragraph each."""
    if not decls:
        return ""
    return ("  <p><strong>%s</strong></p>\n" % HEADING
            + "".join("  <p>%s</p>\n" % _html.escape(d["sentence"], quote=False) for d in decls))


# ---------------------------------------------------------------- the rows

def preflight_rows(slug: str, record_rows: list[dict] | None = None, *, rows: dict | None = None,
                   held: dict | None = None, page_sentences: list[str] | None = None,
                   premise_doc: dict | None = None, case: Path | None = None,
                   root: Path | None = None) -> list[tuple[str, str, str]]:
    import omissions as _O
    s = _O.skipped(slug, record_rows, ROW_UNITS)
    if s:
        return s + _O.skipped(slug, record_rows, ROW_LIST)
    import bindings as B
    import omissions as O
    import premise as PM
    import ruling as R
    import signers
    import source_store as store
    case = case or store.case_dir(slug)
    rows = rows if rows is not None else (B.load(slug).get("bindings") or {})
    held = held if held is not None else R.held_texts(slug)
    page_sentences = page_sentences if page_sentences is not None else B.page_sentences(slug)
    premise_doc = premise_doc if premise_doc is not None else (PM.load(slug) or {})
    scope = PM.scope_of(slug)
    srcs = {s["id"]: s for s in _sources(slug)}
    cov = load(case)
    out = []

    import lean
    LEAN = lean.enabled()
    if LEAN:
        import lean_coverage as LC
    units, no_units, furniture = [], [], []
    spans = bound_ranges(rows, held)
    for sid in relied_on(slug, rows, premise_doc):
        if sid not in held:
            continue
        got = units_of(srcs.get(sid) or {"id": sid}, held[sid], spans.get(sid))
        if LEAN:
            got, cut = LC.split_units(got)
            furniture += cut
        if got:
            units.extend(got)
        elif not groups_of(held[sid])[0]:
            no_units.append(sid)          # an assessment whose bound groups yield none is not "no structure"
    acc = account(units, rows, held, O.load(case), cov.get("declarations") or {})
    stated = []
    if LEAN:
        for u in acc:
            if u["state"] == "none":
                got = LC.already_stated(u["text"], page_sentences)
                if got:
                    u.update(state=LC.ALREADY, how="already stated on the page: %r" % got[:60])
                    stated.append(u)
    bad_el = [k for k, d in (cov.get("declarations") or {}).items()
              if d["state"] == "out_of_scope" and not O.scope_element_ok(d.get("element") or "", scope)[0]]
    none = [u for u in acc if u["state"] == "none"]
    counts = {s: len([u for u in acc if u["state"] == s])
              for s in ("used", "added") + DECLARED + (("already_stated", NO_PLACE, BEYOND, OVER_BUDGET, NOT_ONE, ANCHOR,
                                                         REMOVED) if LEAN else ())}
    detail = "%d unit(s) in %d relied-on source(s): %s. %s" % (
        len(acc), len({u["source"] for u in acc}),
        ", ".join("%d %s" % (n, s) for s, n in counts.items() if n) or "none accounted", LIMIT)
    if LEAN and furniture:
        from collections import Counter
        kinds = Counter(u["furniture"] for u in furniture)
        detail += " Not headline units (lean WHU): %s." % ", ".join("%d %s" % (n, k) for k, n in sorted(kinds.items()))
    if none or bad_el:
        bits = []
        if none:
            bits.append("%d with no state in %s: use, add or declare each (e.g. %s, %s)"
                        % (len(none), ", ".join(sorted({u["source"] for u in none})), none[0]["key"],
                           none[0]["section"]))       # every source named: the replay gate reads them (ruling 1)
        if bad_el:
            bits.append("%d out-of-scope declaration(s) name no words of the question or scope.out (e.g. %s)"
                        % (len(bad_el), bad_el[0]))
        out.append((ROW_UNITS, BAD, "; ".join(bits) + ". " + detail))
    elif no_units:
        out.append((ROW_UNITS, WARN, "no headline section found in %s; declare its headline conclusions by "
                    "hand. %s" % (", ".join(no_units), detail)))
    else:
        out.append((ROW_UNITS, OK, detail))

    hidden: list = []
    decls = declarations(slug, held, case, hidden=hidden)
    removed_lines = [d for d in hidden if d.get("removed")]
    page = {" ".join(s.split()) for s in page_sentences}
    missing = [d for d in decls if " ".join(d["sentence"].split()) not in page]
    wanted = {" ".join(d["sentence"].split()) for d in decls}
    stray = [s for s in page if any(s.startswith(l) for l in LEAD.values()) and s not in wanted]
    budget = O.declaration_budget(len(page_sentences))
    # WHAT THE BUDGET COUNTS (post-study, mid-rerun tool fix, 2026-10-28): an
    # agent's declarations (out_of_scope, not_material, relevance not
    # established). A not_added_cap line follows from a cap being reached, not
    # from anybody's choice, so it is shown but not counted (WHU-S01r).
    # Ruling 1 on P157: a declaration naming a scope.out element, with the scope written before acquire, is exempt.
    # Ruling 3 on P157: a unit is counted once, whether coverage.json or omissions.json declares it (same source,
    # overlapping offsets).
    counted, exempt, twice = budget_count(decls, scope, case, ((premise_doc or {}).get("scope") or {}).get("written_at"))
    over = []
    for d in counted[budget:]:
        ok = d.get("by") and not signers.is_agent(d["by"]) and \
            signers.check_value(d["by"], d.get("signature"), *( [root] if root else []))[0]
        if LEAN:
            ok = False                    # lean WHU: past the budget is a STOP, signed off or not
        if not ok:
            over.append(d)
    if missing or stray or over:
        bits = []
        if missing:
            bits.append("%d declared finding(s) not on the page word for word (e.g. %r); "
                        "coverage_check.py %s render" % (len(missing), missing[0]["sentence"][:90], slug))
        if stray:
            bits.append("%d sentence(s) in the readers' list with no declaration behind it (e.g. %r)"
                        % (len(stray), stray[0][:90]))
        if over:
            bits.append(("%d declaration(s) past the budget of %d (lean WHU: a STOP; use, add or cut them)"
                         if LEAN else "%d declaration(s) past the budget of %d with no person's sign-off")
                        % (len(over), budget) +
                        ("; not counted: %d naming a scope.out element (scope fixed before acquire), %d counted "
                         "once already" % (len(exempt), len(twice)) if (exempt or twice) else ""))
        out.append((ROW_LIST, BAD, "; ".join(bits)))
    else:
        out.append((ROW_LIST, OK, "%d declared finding(s), each on the page; %d counted against the budget of %d%s%s"
                    % (len(decls), len(counted), budget,
                       ("; not counted: %d naming a scope.out element (scope fixed before acquire), %d counted once "
                        "already" % (len(exempt), len(twice))) if (exempt or twice) else "",
                       ("; %d listed declaration(s) removed by the lean fail-safe (removed: unresolved "
                        "finding), their declarations kept in the records" % len(removed_lines))
                       if removed_lines else "")))
    return out


def declare(slug: str, key: str, state: str, why: str, by: str, element: str = "",
            signature: dict | None = None, case: Path | None = None, for_reader: str = "") -> dict:
    import source_store as store
    if state not in DECLARED:
        raise SystemExit("state must be one of %s" % ", ".join(DECLARED))
    if not why.strip() or not by.strip():
        raise SystemExit("a declaration needs --why and --by")
    if state == "not_added_cap":
        import omissions as O
        if not O.cap_of(why):
            raise SystemExit("not_added_cap needs --why naming which cap: additions or declarations")
    if state == "out_of_scope" and not element.strip():
        raise SystemExit("out_of_scope needs --element: words of the question or a scope.out entry")
    case = case or store.case_dir(slug)
    doc = load(case, raw=True)
    doc.setdefault("declarations", {})[key] = {
        "state": state, "reason": why, "by": by, "element": element,
        **({"reason_for_reader": for_reader} if for_reader.strip() else {}),
        **({"signature": signature} if signature else {}),
        "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (case / RECORD).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc["declarations"][key]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("cmd", nargs="?", default="status", choices=("status", "declare", "render"))
    ap.add_argument("key", nargs="?")
    ap.add_argument("state", nargs="?")
    ap.add_argument("--why", default="")
    ap.add_argument("--by", default="")
    ap.add_argument("--element", default="")
    ap.add_argument("--for-reader", default="", help="the one line the readers' list shows (else --why's last sentence)")
    a = ap.parse_args(argv)
    if a.cmd == "declare":
        print(json.dumps(declare(a.slug, a.key, a.state, a.why, a.by, a.element, for_reader=a.for_reader),
                         indent=1))
        return 0
    import ruling as R
    if a.cmd == "render":
        print(render(declarations(a.slug, R.held_texts(a.slug))))
        return 0
    rc = 0
    for label, st, detail in preflight_rows(a.slug):
        print("  %-8s %-38s %s" % (st, label, detail))
        rc = rc or (1 if st == BAD else 0)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
