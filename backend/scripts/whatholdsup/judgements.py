#!/usr/bin/env python3
"""Assessment judgements in the held sources, and which bear on the question.

Post-study fix 3, step 2 (2026-10-27). docs/whu-fix3-evidence-standard.md
sections 3.2 and 3.3; the advisor's rulings of 27 October (R1; always on).

CANDIDATES (code). In every held source:
  - each assessment Executive Summary paragraph or numbered statement carrying
    calibrated language (coverage_check.groups_of, detected by structure),
    WHOLE -- not only the ones the page binds: the coverage check's known
    limit is exactly the judgement the page never binds (WHU-S03: Chapter 13's
    Executive Summary paragraph 7);
  - in a systematic review's abstract, every sentence of its conclusions, and
    every results sentence carrying a certainty or confidence term.
Each is stored by source and offsets (judgements.json, committed): never its text.

RELEVANCE (ruling.py judgements, one call per candidate). The model answers
whether the judgement bears on the question. A "relevant" answer must quote
words of the issue.json question or of the premise's scope (covers, or a
scope.out entry), and code checks that those words are there
(omissions.scope_element_ok). An answer code cannot verify, or a reply that is
not usable, goes to a person and the candidate stays undecided.

THE RULE (preflight row "assessment judgements stated", always on). Every
relevant judgement is stated on the page with its certainty -- an on-page
binding span lies inside it, and the bound sentence carries the judgement's
certainty or confidence terms (bindings.grade_terms) -- or is declared on the
readers' list (coverage_check.py declare, with the candidate's key). A
candidate not yet ruled, or sent to a person and not decided, blocks.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

RECORD = "judgements.json"
ROW = "assessment judgements stated"
OK, BAD, WARN = "ok", "BLOCKED", "warn"


def sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def key(sid: str, at: list[int]) -> str:
    return "%s@%d-%d" % (sid, at[0], at[1])


def candidates_of(sid: str, text: str) -> list[dict]:
    """[{key, source, at, section, kind}] of one held document."""
    import coverage_check as C
    out = []
    kind, groups = C.groups_of(text)
    if kind:
        for g0, g1, section in groups:
            if C.CALIBRATED.search(text[g0:g1]):
                out.append({"key": key(sid, [g0, g1]), "source": sid, "at": [g0, g1], "section": section,
                            "kind": "assessment"})
        return out
    m = C._CONCL.search(text)
    review = m is not None or bool(C._SR.search(text[:C.ABSTRACT_CHARS]))
    if not review:
        return out
    for u in C.units_of({"id": sid}, text, []):
        graded = bool(C.CALIBRATED.search(u["text"]))
        if u["section"] == "abstract conclusions" or graded:
            out.append({"key": key(sid, u["at"]), "source": sid, "at": u["at"], "section": u["section"],
                        "kind": "review"})
    return out


def candidates(held: dict[str, str]) -> list[dict]:
    out = []
    for sid in sorted(held):
        out += candidates_of(sid, held[sid])
    return out


def scope_for_words(scope: dict) -> dict:
    """premise.scope_of's dict with `covers` added as a place the words may come from."""
    out = list(scope.get("out") or [])
    if (scope.get("covers") or "").strip():
        out.append({"what": scope["covers"], "why": "covers"})
    return dict(scope, out=out)


def verify_words(words: str, scope: dict) -> tuple[bool, str]:
    import omissions as O
    return O.scope_element_ok(words, scope_for_words(scope))


# ---------------------------------------------------------------- the record

def load(case: Path) -> dict:
    p = case / RECORD
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"candidates": {}}


def record(case: Path, c: dict, held_text: str, *, relevant, words: str, reason: str, by: str,
           ruling: str | None = None, to_person: bool = False) -> dict:
    doc = load(case)
    e = {"source": c["source"], "at": c["at"], "section": c["section"], "kind": c["kind"],
         "text_sha256": sha(held_text[c["at"][0]:c["at"][1]]), "relevant": relevant, "words": words,
         "reason": reason, "by": by, "ruling": ruling, "to_person": to_person,
         "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    doc.setdefault("candidates", {})[c["key"]] = e
    (case / RECORD).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return e


def undecided(cands: list[dict], doc: dict, held: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """(to rule: no decision on the current text; with a person: sent to a
    person and not yet decided). The model never re-rules the second."""
    rule, person = [], []
    for c in cands:
        e = (doc.get("candidates") or {}).get(c["key"])
        t = held[c["source"]][c["at"][0]:c["at"][1]]
        if e is None or e.get("text_sha256") != sha(t):
            rule.append(c)
        elif e.get("relevant") is None:
            person.append(c)
    return rule, person


# ---------------------------------------------------------------- the rule (fix 3, step 3)

def _terms(text: str) -> set[tuple[str, str]]:
    import bindings as B
    return {(fam, lvl) for fam, lvls in B.grade_terms(text).items() for lvl in lvls}


def bound_sentences(rows: dict, held: dict[str, str]) -> list[tuple[str, list[int], str]]:
    """(source, offsets, page sentence) of every on-page binding span, located once."""
    import audit_stage as A
    import ruling as R
    out = []
    for r in rows.values():
        if not r.get("on_page"):
            continue
        for sid, q in R.quotations(r, held):
            at = A.locate(q, held.get(sid) or "")
            if at:
                out.append((sid, list(at), r.get("sentence") or ""))
    return out


def state_of(c: dict, held_text: str, rows: dict, held: dict[str, str], declared: dict,
             omissions_doc: dict, bound: list | None = None) -> tuple[str, str]:
    """("stated" | "bound without its certainty" | "declared" | "not stated", how)."""
    text = held_text[c["at"][0]:c["at"][1]]
    want = _terms(text)
    bound = bound if bound is not None else bound_sentences(rows, held)
    bound_sents = [s for sid, at, s in bound
                   if sid == c["source"] and c["at"][0] <= at[0] and at[1] <= c["at"][1]]
    if bound_sents:
        if not want or any(_terms(s) & want for s in bound_sents):
            return "stated", "bound, with its certainty" if want else "bound (it states no certainty term)"
    if c["key"] in declared:
        return "declared", declared[c["key"]].get("state", "declared")
    for e in omissions_doc.get("omissions") or []:
        if (e.get("source") == c["source"] and e.get("at") and e.get("outcome") in ("OUT_OF_SCOPE", "NOT_MATERIAL")
                and e["at"][0] < c["at"][1] and c["at"][0] < e["at"][1]):
            return "declared", e["outcome"].lower()
    if bound_sents:
        return "bound without its certainty", "the page binds it but no bound sentence carries %s" % (
            ", ".join("%s %s" % (lvl, fam) for fam, lvl in sorted(want)))
    return "not stated", ""


def preflight_rows(slug: str, record_rows: list[dict] | None = None, *, held: dict | None = None,
                   rows: dict | None = None, case: Path | None = None) -> list[tuple[str, str, str]]:
    """Always on (advisor's ruling, 27 October): every relevant held assessment
    judgement is stated with its certainty, or declared on the readers' list."""
    import bindings as B
    import coverage_check as C
    import omissions as O
    import ruling as R
    import source_store as store
    s = O.skipped(slug, record_rows, ROW)
    if s:
        return s
    case = case or store.case_dir(slug)
    held = held if held is not None else R.held_texts(slug)
    rows = rows if rows is not None else (B.load(slug).get("bindings") or {})
    cands = candidates(held)
    doc = load(case)
    to_rule, person = undecided(cands, doc, held)
    declared = C.load(case).get("declarations") or {}
    om = O.load(case)
    relevant = [c for c in cands if c not in to_rule and c not in person
                and (doc["candidates"].get(c["key"]) or {}).get("relevant") is True]
    bad = []
    counts: dict[str, int] = {}
    bound = bound_sentences(rows, held)
    for c in relevant:
        st, how = state_of(c, held[c["source"]], rows, held, declared, om, bound)
        counts[st] = counts.get(st, 0) + 1
        if st in ("not stated", "bound without its certainty"):
            bad.append((c, st, how))
    if to_rule or person or bad:
        bits = []
        if to_rule:
            bits.append("%d held assessment judgement(s) not yet ruled for relevance: ruling.py judgements %s"
                        % (len(to_rule), slug))
        if person:
            bits.append("%d with a person for a relevance decision (e.g. %s)" % (len(person), person[0]["key"]))
        if bad:
            c, st, how = bad[0]
            bits.append("%d relevant judgement(s) neither stated with their certainty nor declared on the "
                        "readers' list (e.g. %s, %s: %s%s)" % (len(bad), c["key"], c["section"], st,
                                                                 "; " + how if how else ""))
        return [(ROW, BAD, "; ".join(bits))]
    return [(ROW, OK, "%d held assessment judgement(s), %d relevant: %s" % (
        len(cands), len(relevant), ", ".join("%d %s" % (n, k) for k, n in sorted(counts.items())) or "none"))]
