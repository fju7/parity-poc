#!/usr/bin/env python3
"""Was every accepted ruling applied to the page word for word? (RUN.md 5a)

    applied_check.py SLUG

Study ruling 1 (advisor, 2026-10-20): accepted ruling text is applied word for
word by the drafting session, and a script then checks that each applied
sentence on the page equals the ruling's text exactly, and logs it. This is
that script. It runs on a study issue only.

WHICH RULINGS
-------------
Every ruling of "accept" or "amend" in the issue's logs: rulings/rulings.jsonl
(gate and conclusion rulings, ruling.py) and audit/<run>/rulings.jsonl (audit
and second-reader rulings). A ruling the audit stage marked "apply": false (a
card or meta wording left for a person) is skipped and listed. Rulings from a
run marked withdrawn in its manifest are not read at all. A ruling is
SUPERSEDED when a later ruling took its text as the sentence it ruled on and
accepted or amended it again: only the last text in such a chain is expected on
the page. A "reject" leaves the sentence as written and expects nothing.

WHAT "EQUALS" MEANS
-------------------
Normalised only as changecheck normalises (changecheck.sentences_of): the text
is split into sentences by source_ledger.sentences after source_ledger.plain,
and each sentence's whitespace is collapsed. The page is read through
changecheck.sentences_of, so the body only, without the source list's tags
(GAP-017). A ruling's text is applied when
every one of its sentences is a sentence of the page. A ruling whose text is ""
(cut) is applied when the sentence it ruled on is no longer on the page.

The result is appended to rulings/applied_check.jsonl. Exit 1 on any mismatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import source_ledger as ledger  # noqa: E402

APPLIED = ("accept", "amend")


def norm_sentences(text: str) -> list[str]:
    """changecheck's normalisation, for a ruling's plain text."""
    return [" ".join(s.split()) for s in ledger.sentences(ledger.plain(text or ""))]


def page_sentences(page_html: str) -> list[str]:
    import changecheck
    return changecheck.sentences_of(page_html, drop_tags=True)   # study only (GAP-017)


def load_rulings(case: Path) -> list[dict]:
    """Every ruling record, oldest first, each tagged with the log it came from."""
    logs = [case / "rulings" / "rulings.jsonl"] + sorted(
        p for p in (case / "audit").glob("*/rulings.jsonl") if not _withdrawn(p.parent))
    out = []
    for p in logs:
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                r = json.loads(line)
                r["_log"] = "%s:%d" % (p.relative_to(case), n)
                out.append(r)
    return sorted(out, key=lambda r: r.get("at") or "")


def _withdrawn(run_dir: Path) -> bool:
    """A run marked withdrawn in its manifest (audit_stage.py withdraw): its
    rulings are not expected on the page."""
    try:
        w = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")).get("withdrawn")
    except Exception:
        return False
    return isinstance(w, dict) and bool(w.get("reason"))


def _ruled_on(r: dict) -> str:
    """The sentence a ruling was about: its inputs (ruling.py, and the audit
    stage since 2026-10-20)."""
    return ((r.get("inputs") or {}).get("sentence")) or ""


def check(case: Path, page_html: str) -> dict:
    """{"checked": [...], "mismatches": [...], "superseded": [...], "skipped": [...]}"""
    rulings = load_rulings(case)
    page = set(page_sentences(page_html))
    applied = [r for r in rulings if r.get("ruling") in APPLIED]
    out = {"checked": [], "mismatches": [], "superseded": [], "skipped": []}
    for i, r in enumerate(applied):
        ref = {"log": r["_log"], "ruling": r.get("ruling"), "ruling_kind": r.get("ruling_kind") or "audit",
               "ruled_on": _ruled_on(r), "text": r.get("text")}
        if r.get("apply") is False:
            out["skipped"].append(dict(ref, why="left for a person; the stage does not apply it"))
            continue
        new = " ".join((r.get("text") or "").split())
        later = [x for x in applied[i + 1:] if new and " ".join(_ruled_on(x).split()) == new]
        if later:
            out["superseded"].append(dict(ref, by=later[0]["_log"]))
            continue
        if new:
            want = norm_sentences(new)
            missing = [s for s in want if s not in page]
            row = dict(ref, expected=want, missing=missing)
            (out["mismatches"] if missing or not want else out["checked"]).append(row)
        else:
            old = norm_sentences(_ruled_on(r))
            still = [s for s in old if s in page]
            row = dict(ref, expected="cut", still_on_page=still)
            (out["mismatches"] if (still or not old) else out["checked"]).append(row)
    return out


# --------------------------------------------------------------------------
# References a ruling left pointing at nothing (GAP-016)
# --------------------------------------------------------------------------
#
# Rulings are applied one sentence at a time, so a ruling can remove a name or
# a term a later sentence relies on. WHU-P02: 'UPDATE' was removed from the
# sentence that introduced the trial, and a later sentence still says "The
# UPDATE authors"; the reader and the second reader both held it.

_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)*\b")
_NAME = re.compile(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b")
_NOT_NAMES = {"The", "This", "That", "These", "Those", "There", "Their", "They", "In", "On", "At",
              "As", "An", "And", "But", "For", "Of", "Or", "It", "Its", "We", "Our", "Us", "If",
              "When", "Where", "Which", "What", "Who", "With", "From", "By", "To", "Into", "Each",
              "All", "Some", "Both", "One", "Two", "Three", "Most", "Many", "No", "Not", "Yet"}


def terms(sentence: str) -> set[str]:
    """Acronyms and defined short forms (UPDATE, UPF, NOVA, HR), and capitalised
    names not at the start of the sentence (Hall, Monteiro)."""
    s = sentence or ""
    out = {m.group(0) for m in _ACRONYM.finditer(s) if len(m.group(0)) >= 2}
    first = re.match(r"\s*\W*(\w+)", s)
    for m in _NAME.finditer(s):
        w = m.group(0)
        if w in _NOT_NAMES or (first and m.start(0) == first.start(1)):
            continue
        out.add(w)
    return out


def _uses(term: str, sentence: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(term), sentence or "") is not None


def dangling(case: Path, page_html: str) -> list[dict]:
    """Every term an applied ruling removed that a later sentence still uses
    while no earlier sentence now introduces it. One finding per (term, later
    sentence)."""
    res = check(case, page_html)
    page = page_sentences(page_html)
    out, seen = [], set()
    for r in res["checked"]:
        old = " ".join((r.get("ruled_on") or "").split())
        new = " ".join((r.get("text") or "").split())
        removed = terms(old) - terms(new)
        if not removed:
            continue
        new_first = norm_sentences(new)[0] if new else None
        at = page.index(new_first) if new_first in page else -1        # -1: cut, or not found
        for term in sorted(removed):
            first = next((i for i, s in enumerate(page) if _uses(term, s)), None)
            if first is None or first <= at:
                continue                                                # unused, or still introduced earlier
            key = (term, page[first])
            if key in seen:
                continue
            seen.add(key)
            out.append({"term": term, "applied_sentence": new or "(cut)", "ruled_on": old,
                        "later_sentence": page[first], "log": r["log"]})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--dangling", action="store_true",
                    help="list references an applied ruling left pointing at nothing (GAP-016)")
    a = ap.parse_args(argv)
    import publish as P
    import source_store as store
    if not P.is_study(a.slug):
        raise SystemExit("%s is not a study issue (issue.json \"study\": true)" % a.slug)
    case = store.case_dir(a.slug)
    page_html = (P.ROOT / P.issue_cfg(a.slug)["page"]).read_text(encoding="utf-8")
    if a.dangling:
        found = dangling(case, page_html)
        for f in found:
            print("  DANGLING  %r: removed from %r; still used in %r"
                  % (f["term"], f["applied_sentence"][:80], f["later_sentence"][:80]))
        print("\n  %d reference(s) pointing at nothing\n" % len(found))
        return 1 if found else 0
    res = check(case, page_html)
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "page_sha256": hashlib.sha256(page_html.encode("utf-8")).hexdigest(),
           "checked": len(res["checked"]), "mismatches": res["mismatches"],
           "superseded": len(res["superseded"]), "skipped": res["skipped"]}
    log = case / "rulings" / "applied_check.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("\n  %d applied ruling(s) on the page as ruled, %d superseded, %d left for a person, "
          "%d MISMATCH(ES)" % (len(res["checked"]), len(res["superseded"]), len(res["skipped"]),
                               len(res["mismatches"])))
    for m in res["mismatches"]:
        if m.get("expected") == "cut":
            print("  MISMATCH  %s: ruled cut, still on the page: %r" % (m["log"], (m["still_on_page"] or [""])[0][:100]))
        else:
            print("  MISMATCH  %s: not on the page as ruled: %r" % (m["log"], (m["missing"] or [""])[0][:100]))
    print("  log: %s\n" % log)
    return 1 if res["mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
