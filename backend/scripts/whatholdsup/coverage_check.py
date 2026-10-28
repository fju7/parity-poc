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
under the heading "Findings in our sources we judged outside this question".
These are scope statements, protected under fix 1 (bindings.protected_kind,
kind "scope"). The row STOPs if a declaration is not on the page word for word,
or if the page carries such a sentence with no declaration behind it.
Declarations past omissions.declaration_budget need a person's sign-off.
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
DECLARED = ("out_of_scope", "not_material")
HEADING = "Findings in our sources we judged outside this question"
LEAD = {"out_of_scope": "Outside this question:", "not_material": "Judged not material to this question:"}

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


def load(case: Path) -> dict:
    p = case / RECORD
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"units": [], "declarations": {}}


def _overlaps(a: list, b: list) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def bound_ranges(rows: dict, held: dict[str, str]) -> dict[str, list[list[int]]]:
    """{source id: [[start, end]]} of every on-page binding span, located in its held text."""
    import audit_stage as A
    import ruling as R
    spans: dict[str, list[list[int]]] = {}
    for r in rows.values():
        if not r.get("on_page"):
            continue
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
            dec = [e for e in hits if e.get("outcome") in ("OUT_OF_SCOPE", "NOT_MATERIAL")]
            if add:
                state, how = "added", add[0].get("key")
            elif k in declarations:
                state, how = declarations[k]["state"], "declared in coverage.json"
            elif dec:
                state, how = dec[0]["outcome"].lower(), "omission ruling %s" % dec[0].get("ruling")
        out.append(dict(u, key=k, state=state, how=how))
    return out


# ---------------------------------------------------------------- the readers' list

def short_span(text: str, words: int = SPAN_WORDS) -> str:
    """The first sentence of TEXT, at most WORDS words, verbatim; an ellipsis
    marks a cut. Collapsed whitespace only."""
    first = _SENT.split(" ".join((text or "").split()), maxsplit=1)[0]
    w = first.split()
    return " ".join(w[:words]) + (" …" if len(w) > words else "")


def one_line(reason: str) -> str:
    r = _SENT.split(" ".join((reason or "").split()), maxsplit=1)[0].rstrip(" .;")
    return r[:200]


def declaration_sentence(state: str, span: str, label: str, reason: str) -> str:
    """One sentence, as the page is split (source_ledger.sentences): a span the
    splitter would break ("e.g. ...") is shortened, with an ellipsis, until the
    whole line is one sentence -- a second sentence would not carry the lead
    and so would not be protected."""
    import source_ledger as ledger
    cut = span.endswith(" …")
    words = span[:-2].split() if cut else span.split()
    while True:
        s = "%s “%s” (%s); %s." % (LEAD[state], " ".join(words) + (" …" if cut else ""), label, one_line(reason))
        if len(ledger.sentences(s)) <= 1:
            return s
        dotted = [i for i, w in enumerate(words) if "." in w]
        words = words[:dotted[0]] if dotted and dotted[0] > 0 else words[:-1]
        cut = True
        if not words:
            return "%s “…” (%s); %s." % (LEAD[state], label, one_line(reason))


def _label(sources: list[dict], sid: str) -> str:
    s = next((x for x in sources if x.get("id") == sid), {})
    for a in s.get("also_called") or []:
        if a and not a.lower().startswith("10."):
            return a
    t = (s.get("title") or sid).split(" — ")[0]
    return t[:60]


def declarations(slug: str, held: dict[str, str], case: Path | None = None) -> list[dict]:
    """Every declared finding the readers' list must show, oldest first:
    [{key, state, source, span, reason, by, signature, sentence, at}]."""
    import omissions as O
    import source_store as store
    case = case or store.case_dir(slug)
    srcs = _sources(slug)
    out = []
    for e in O.load(case).get("omissions") or []:
        if e.get("outcome") in ("OUT_OF_SCOPE", "NOT_MATERIAL") and e.get("at"):
            text = (held.get(e["source"]) or "")[e["at"][0]:e["at"][1]]
            out.append({"key": e["key"], "state": e["outcome"].lower(), "source": e["source"], "text": text,
                        "reason": e.get("reason") or "", "by": e.get("by"), "signature": e.get("signature"),
                        "decided_at": e.get("decided_at") or ""})
    for k, d in (load(case).get("declarations") or {}).items():
        sid, rng = k.split("@")
        a, b = (int(x) for x in rng.split("-"))
        out.append({"key": k, "state": d["state"], "source": sid, "text": (held.get(sid) or "")[a:b],
                    "reason": d.get("reason") or "", "by": d.get("by"), "signature": d.get("signature"),
                    "decided_at": d.get("decided_at") or ""})
    out.sort(key=lambda d: d["decided_at"])
    for d in out:
        d["sentence"] = declaration_sentence(d["state"], short_span(d["text"]), _label(srcs, d["source"]), d["reason"])
    return out


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

    units, no_units = [], []
    spans = bound_ranges(rows, held)
    for sid in relied_on(slug, rows, premise_doc):
        if sid not in held:
            continue
        got = units_of(srcs.get(sid) or {"id": sid}, held[sid], spans.get(sid))
        if got:
            units.extend(got)
        elif not groups_of(held[sid])[0]:
            no_units.append(sid)          # an assessment whose bound groups yield none is not "no structure"
    acc = account(units, rows, held, O.load(case), cov.get("declarations") or {})
    bad_el = [k for k, d in (cov.get("declarations") or {}).items()
              if d["state"] == "out_of_scope" and not O.scope_element_ok(d.get("element") or "", scope)[0]]
    none = [u for u in acc if u["state"] == "none"]
    counts = {s: len([u for u in acc if u["state"] == s]) for s in ("used", "added") + DECLARED}
    detail = "%d unit(s) in %d relied-on source(s): %s. %s" % (
        len(acc), len({u["source"] for u in acc}),
        ", ".join("%d %s" % (n, s) for s, n in counts.items() if n) or "none accounted", LIMIT)
    if none or bad_el:
        bits = []
        if none:
            bits.append("%d with no state: use, add or declare each (e.g. %s, %s)"
                        % (len(none), none[0]["key"], none[0]["section"]))
        if bad_el:
            bits.append("%d out-of-scope declaration(s) name no words of the question or scope.out (e.g. %s)"
                        % (len(bad_el), bad_el[0]))
        out.append((ROW_UNITS, BAD, "; ".join(bits) + ". " + detail))
    elif no_units:
        out.append((ROW_UNITS, WARN, "no headline section found in %s; declare its headline conclusions by "
                    "hand. %s" % (", ".join(no_units), detail)))
    else:
        out.append((ROW_UNITS, OK, detail))

    decls = declarations(slug, held, case)
    page = {" ".join(s.split()) for s in page_sentences}
    missing = [d for d in decls if " ".join(d["sentence"].split()) not in page]
    wanted = {" ".join(d["sentence"].split()) for d in decls}
    stray = [s for s in page if any(s.startswith(l) for l in LEAD.values()) and s not in wanted]
    budget = O.declaration_budget(len(page_sentences))
    over = []
    for d in decls[budget:]:
        ok = d.get("by") and not signers.is_agent(d["by"]) and \
            signers.check_value(d["by"], d.get("signature"), *( [root] if root else []))[0]
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
            bits.append("%d declaration(s) past the budget of %d with no person's sign-off"
                        % (len(over), budget))
        out.append((ROW_LIST, BAD, "; ".join(bits)))
    else:
        out.append((ROW_LIST, OK, "%d declared finding(s), each on the page; budget %d" % (len(decls), budget)))
    return out


def declare(slug: str, key: str, state: str, why: str, by: str, element: str = "",
            signature: dict | None = None, case: Path | None = None) -> dict:
    import source_store as store
    if state not in DECLARED:
        raise SystemExit("state must be one of %s" % ", ".join(DECLARED))
    if not why.strip() or not by.strip():
        raise SystemExit("a declaration needs --why and --by")
    if state == "out_of_scope" and not element.strip():
        raise SystemExit("out_of_scope needs --element: words of the question or a scope.out entry")
    case = case or store.case_dir(slug)
    doc = load(case)
    doc.setdefault("declarations", {})[key] = {
        "state": state, "reason": why, "by": by, "element": element,
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
    a = ap.parse_args(argv)
    if a.cmd == "declare":
        print(json.dumps(declare(a.slug, a.key, a.state, a.why, a.by, a.element), indent=1))
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
