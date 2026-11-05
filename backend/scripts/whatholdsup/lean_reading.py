#!/usr/bin/env python3
"""Lean WHU's reading rows (process doc §4.6.1, "What 'we read' means";
advisor's rulings of 5 November 2026 after Q1-04). Offline, $0.

  ROW_STATEMENT  "reading statement matches what the checking stages received"
                 (fix 6): every reading sentence code generates from the
                 measurement (lean_received.py) is on the page, and no page
                 sentence says a section was read that the measurement does not
                 show received in full.
  ROW_RESTS      "sentences rest on received text" (fix 5): every on-page bound
                 span on a full_text_held source lies, to FULL, inside the text
                 some checking stage received (stages added together here). A
                 sentence inside the visible source list is exempt.
  ROW_NOT_READ   "not-read records kept" (fix 4): an access.not_read entry in any
                 committed version of sources.json (git history) or the working
                 copy that is gone stops the page, unless access.covers_not_read
                 maps that exact entry to a section listed in access.sections.

    python3 lean_reading.py <slug>    the three rows
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

OK, BAD = "ok", "BLOCKED"
ROW_STATEMENT = "reading statement matches what the checking stages received"
ROW_RESTS = "sentences rest on received text"
ROW_NOT_READ = "not-read records kept"


def _clean(x) -> str:
    import lean_sentences as LS
    return LS._clean(x)


# ------------------------------------------------------------------ fix 6

def statement_row(page_sentences: list[str], gen: list[dict]) -> tuple[str, str, str]:
    import lean_sentences as LS
    on = {LS.words(s) for s in page_sentences}
    mine = [g for g in gen if g["kind"] == "reading" and (g.get("field") or "").startswith("access.sections")]
    missing = [g["sentence"] for g in mine if LS.words(g["sentence"]) not in on]
    want = {LS.words(g["sentence"]) for g in mine}
    claims = [s for s in page_sentences if LS.words(s).startswith("Of ") and ", we read: " in LS.words(s)
              and LS.words(s) not in want]
    if missing or claims:
        bits = []
        if claims:
            bits.append("%d page sentence(s) say a section was read that no checking stage received in full "
                        "(or that the records no longer list): %r" % (len(claims), claims[0][:140]))
        if missing:
            bits.append("%d generated reading sentence(s) not on the page (paste lean_sentences.py render): %r"
                        % (len(missing), missing[0][:140]))
        return (ROW_STATEMENT, BAD, "; ".join(bits))
    return (ROW_STATEMENT, OK, "%d reading sentence(s), each as the measurement gives it" % len(mine))


# ------------------------------------------------------------------ fix 5

def _source_list_sentence(sentence: str, entries) -> bool:
    import lean_sentences as LS
    w = LS.words(sentence)
    return any(w and w in LS.words(txt) for txt, _links in entries or [])


def rests_row(rows: dict, held: dict[str, str], unions: dict[str, bytearray],
              entries=None) -> tuple[str, str, str]:
    """UNIONS: {sid: union mask} for every full_text_held source (lean_received)."""
    import audit_stage as A
    import lean_received as LR
    bad, n = [], 0
    for k, r in rows.items():
        if not r.get("on_page") or _source_list_sentence(r.get("sentence") or "", entries):
            continue
        for x in [r] + list(r.get("also_rests_on") or []) + list(r.get("premises") or []):
            if not isinstance(x, dict):
                continue
            sid, sp = x.get("source_id"), x.get("span")
            if not sid or not sp or sid not in unions:
                continue
            n += 1
            at = A.locate(sp, held.get(sid) or "")
            if not at:
                bad.append("%s: span not found in %s's held text" % (k, sid))
                continue
            sh = LR.share(held[sid], unions[sid], at[0], at[1])
            if sh < LR.FULL:
                bad.append("%s on %s@%d-%d: %.0f%% received (%r)" % (k, sid, at[0], at[1], 100 * sh,
                                                                    (r.get("sentence") or "")[:80]))
    if bad:
        return (ROW_RESTS, BAD, "%d of %d bound span(s) rest on text no checking stage received: %s"
                % (len(bad), n, " || ".join(bad[:3])))
    return (ROW_RESTS, OK, "%d bound span(s) on full-text sources, each inside received text" % n)


# ------------------------------------------------------------------ fix 4

def removed_not_read(history: list[dict], current: dict) -> list[str]:
    """'<sid>: <entry>' for every not_read entry in any document of HISTORY (and
    CURRENT) that CURRENT no longer carries and does not cover with a listed
    section (access.covers_not_read)."""
    now = {s.get("id"): s for s in current.get("sources") or []}
    out = []
    seen = set()
    for doc in list(history) + [current]:
        for s in doc.get("sources") or []:
            for e in (s.get("access") or {}).get("not_read") or []:
                key = (s.get("id"), _clean(e))
                if key in seen:
                    continue
                seen.add(key)
                cur = now.get(s.get("id")) or {}
                acc = cur.get("access") or {}
                if key[1] in {_clean(x) for x in acc.get("not_read") or []}:
                    continue
                covers = {_clean(a): b for a, b in (acc.get("covers_not_read") or {}).items()}
                sec = covers.get(key[1])
                if sec and sec in (acc.get("sections") or []):
                    continue
                out.append("%s: %s" % key)
    return out


def history_of(path: Path) -> list[dict]:
    """Every committed version of PATH (sources.json), oldest first; [] when git
    has none."""
    try:
        rel = path.resolve().relative_to(ROOT)
        hs = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%H", "--", str(rel)],
                            capture_output=True, text=True, check=True).stdout.split()
    except Exception:
        return []
    out = []
    for h in reversed(hs):
        try:
            t = subprocess.run(["git", "-C", str(ROOT), "show", "%s:%s" % (h, rel)],
                               capture_output=True, text=True, check=True).stdout
            out.append(json.loads(t))
        except Exception:
            continue
    return out


def not_read_row(history: list[dict], current: dict) -> tuple[str, str, str]:
    gone = removed_not_read(history, current)
    if gone:
        return (ROW_NOT_READ, BAD, "%d not-read record(s) removed with no covering read record "
                "(access.covers_not_read -> a listed section): %s" % (len(gone), " || ".join(gone[:3])))
    return (ROW_NOT_READ, OK, "every not-read record kept, or covered by a listed section")


# ------------------------------------------------------------------ the rows

def preflight_rows(slug: str, page_sentences: list[str] | None = None) -> list[tuple[str, str, str]]:
    import bindings as B
    import lean_received as LR
    import lean_sentences as LS
    import ruling as R
    import source_store as store
    case = store.case_dir(slug)
    sp = case / "sources.json"
    current = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    ps = page_sentences if page_sentences is not None else B.page_sentences(slug)
    held = R.held_texts(slug)
    m = LR.measure(slug, held=held, sources=current.get("sources") or [], case=case)
    unions = {sid: LR.union(v["masks"]) for sid, v in m.items()}
    rows = (B.load(slug).get("bindings") or {})
    try:
        entries = B.page_markup(slug)[2]
    except Exception:
        entries = []
    return [statement_row(ps, LS.generated(slug)), rests_row(rows, held, unions, entries),
            not_read_row(history_of(sp), current)]


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print(__doc__)
        return 2
    for row in preflight_rows(argv[0]):
        print("  %-6s %-60s %s" % (row[1], row[0], row[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
