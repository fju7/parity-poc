#!/usr/bin/env python3
"""Lean WHU's fail-safe for ruling.py's person paths (process doc §4.6.1, "The
ruling paths"; advisor's ruling of 5 November 2026 on the Q1-02 lean run).

Under WHU_LEAN=1, a finding that ruling.py would leave for a person because
the sentence it is about is protected (question, reading, scope) or
ambiguous is NOT routed. Its sentence leaves the page instead. This module
records that, and nothing else:

  rulings/lean_removed.jsonl   one row per (path, finding, sentence):
      {at, path, finding, finding_key, sentence, fingerprint, ref,
       outcome: "removed: unresolved finding", by}

No decision, disposition, MERIT line or not_ruled_protected is ever written
for such a finding: it stays unresolved on the record. The page is
re-rendered without the sentence (lean_sentences.generated leaves it out),
and a removed sentence still on the page BLOCKs "generated sentences match
the records". If the sentence is a required page element (the question
restatement, a holdings / sections-read / not-read sentence, a search
sentence, or the readers'-list heading while a line remains under it), that
row BLOCKs for good and the page is Not Ready: that is the result.

    lean_failsafe.py <slug> report     removals by path and finding, and the
                                        "already stated" conversions
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

FILE = "lean_removed.jsonl"
OUTCOME = "removed: unresolved finding"
REQUIRED = "removed: unresolved finding on a required page element"
# A "no place" Not added line (coverage_check.NO_PLACE) is a required page element
# the fail-safe may not remove: a finding on it stops the page (advisor, 2026-11-05).
STOP = "Not Ready: unresolved finding on a required 'Not added' line"
LEAN_RELEVANT_BY = "code (lean: relevance not verified, treated as relevant)"
BY = "code (lean fail-safe, ruling.py)"
# the protected kinds ruling.split_protected gives, and source_advocate.AMBIGUOUS
REMOVABLE = ("question", "reading", "scope", "ambiguous")


def applies(protected: str | None) -> bool:
    """Is an item left for a person for this reason one the fail-safe takes?"""
    import lean
    return lean.enabled() and protected in REMOVABLE


def _words(s: str) -> str:
    import lean_sentences as LS
    return LS.words(s or "")


def is_no_place_line(sentence: str) -> bool:
    import coverage_check as C
    w = " ".join((sentence or "").split())
    return w.startswith(C.LEAD[C.NO_PLACE]) and w.rstrip(".").endswith(C.NO_PLACE_TAIL)


def _key(it: dict) -> str:
    ref = it.get("ref") or {}
    for k in ("finding_key", "advocate_item", "id", "candidate"):
        if ref.get(k):
            return str(ref[k])
    f = it.get("finding") or {}
    if f.get("id"):
        return str(f["id"])
    if ref.get("origins"):
        return ",".join(ref["origins"])
    return ""


def label(r: dict) -> str:
    return "%s (%s, %s)" % (OUTCOME, r.get("path"), r.get("finding"))


def path_for(case_or_log: Path) -> Path:
    """The record beside a rulings log, or in a case folder's rulings/."""
    p = Path(case_or_log)
    return p.with_name(FILE) if p.suffix == ".jsonl" else p / "rulings" / FILE


def load(case_or_log: Path) -> list[dict]:
    p = path_for(case_or_log)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def record(mode: str, it: dict, log: Path) -> dict | None:
    """Record ITEM's sentence as removed by the fail-safe. Idempotent per
    (path, finding key, sentence). Returns the row, or None if it was
    already recorded."""
    import bindings as B
    sentence = it.get("sentence") or ""
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "path": mode,
           "finding": it.get("kind") or "", "finding_key": _key(it), "protected": it.get("protected"),
           "sentence": sentence, "fingerprint": B.fingerprint(sentence), "ref": it.get("ref"),
           "outcome": STOP if is_no_place_line(sentence) else OUTCOME, "by": BY}
    have = load(log)
    if any((h["path"], h["finding_key"], h["fingerprint"]) == (mode, row["finding_key"], row["fingerprint"])
           for h in have):
        return None
    p = path_for(log)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    if row["outcome"] == STOP:
        print("  lean fail-safe: %s (%s, %s) -- the line stays; the page is Not Ready: %r"
              % (STOP, mode, row["finding"], sentence[:80]))
    else:
        print("  lean fail-safe: %s -- the sentence leaves the page: %r" % (label(row), sentence[:80]))
    return row


def case_of(slug: str) -> Path | None:
    import source_store as store
    try:
        return store.case_dir(slug)
    except (Exception, SystemExit):
        return None


def removed(slug: str) -> list[dict]:
    """Every fail-safe record for SLUG (removals and stops)."""
    case = case_of(slug)
    return load(case) if case else []


def stops(slug: str) -> list[dict]:
    return [r for r in removed(slug) if r.get("outcome") == STOP]


def removed_words(slug: str) -> set[str]:
    return {_words(r["sentence"]) for r in removed(slug) if r.get("sentence") and r.get("outcome") == OUTCOME}


FRAGMENT_WORDS = 5     # an ambiguous item's target is a fragment; it removes every sentence holding it


def is_removed(sentence: str, gone: set[str]) -> bool:
    """SENTENCE is a removed sentence, or holds a removed fragment of at least
    FRAGMENT_WORDS words (an ambiguous item's target sits in a protected and an
    unprotected sentence; both leave)."""
    w = _words(sentence)
    return w in gone or any(len(g.split()) >= FRAGMENT_WORDS and g in w for g in gone)


def required_removed(full_gen: list[dict], gone: set[str]) -> list[dict]:
    """The generated sentences in FULL_GEN (lean_sentences.generate, before
    removals) that are required page elements and were removed."""
    import coverage_check as C
    live_lines = [g for g in full_gen if g["kind"] == "scope" and g["field"] != "coverage_check.HEADING"
                  and not is_removed(g["sentence"], gone)]
    out = []
    for g in full_gen:
        if not is_removed(g["sentence"], gone):
            continue
        if g["kind"] in ("question", "reading"):
            out.append(g)
        elif g["field"] == "coverage_check.HEADING" and live_lines:
            out.append(g)
        elif g["sentence"] == C.HEADING and live_lines:
            out.append(g)
    return out


def report(slug: str) -> dict:
    import coverage_check as C
    import ruling as R
    hidden: list[dict] = []
    try:
        C.declarations(slug, R.held_texts(slug), hidden=hidden)
    except (Exception, SystemExit):
        pass
    conv = [{"key": d["key"], "source": d["source"], "from": d.get("converted_from"),
             "stated_by": d.get("stated_by")} for d in hidden if d.get("converted_from")]
    rem = [r for r in removed(slug) if r.get("outcome") == OUTCOME]
    by = {}
    for r in rem:
        by.setdefault(r["path"], []).append({"finding": r["finding"], "finding_key": r["finding_key"],
                                             "sentence": r["sentence"]})
    case = case_of(slug)
    import judgements as J
    import omissions as O
    rel = [k for k, e in ((J.load(case).get("candidates") or {}).items() if case else [])
           if e.get("by") == LEAN_RELEVANT_BY]
    np_ = [e["key"] for e in (O.load(case).get("omissions") or [] if case else [])
           if e.get("outcome") == O.NOT_ADDED_NO_PLACE]
    st = stops(slug)
    return {"slug": slug, "removed": len(rem), "removed_by_path": by,
            "already_stated_conversions": len(conv), "conversions": conv,
            "relevance_treated_as_relevant": len(rel), "relevance_keys": rel,
            "not_added_no_place_lines": len(np_), "not_added_keys": np_,
            "stops_on_not_added_lines": len(st),
            "stops": [{"path": r["path"], "finding": r["finding"], "sentence": r["sentence"]} for r in st]}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    import lean
    argv = lean.strip_flag(argv)
    if len(argv) != 2 or argv[1] != "report":
        print(__doc__)
        return 2
    print(json.dumps(report(argv[0]), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
