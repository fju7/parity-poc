#!/usr/bin/env python3
"""A newer edition (lean WHU, rule 3b; process doc §4.6.1, "What 'we read'
means"; advisor's rulings of 5 November 2026 after Q1-04).

A gate recency study with status SUPERSEDED is never routed to a person under
lean, matched to a source or not. Code settles it one of two ways:

  USED       a held source records "newer_edition_of": "<old source id>" in
             sources.json, and every on-page bound span on the old source is
             found in the newer edition's held text: code rebinds those rows
             to the newer source (bindings.json; each row keeps
             "rebound_from"), logs it in rulings/lean_editions.jsonl, and the
             finding is decided "accepted" by code, citing one rebound span in
             the newer edition.
  DISCLOSED  otherwise: the page carries the code-written line
                 A newer edition exists: <latest known>; this page uses <edition>.
             (<latest known> as the gate records it; <edition> the old source's
             sources.json title, or the gate's study name when no source
             matched). A required page element, protected as "reading"
             (bindings.NEWER_EDITION). The finding is decided "judgement" by
             code, naming the line.

The drafting session never fetches, adds or switches to a newer edition itself.
No path drops or dismisses the finding; the preflight row "newer editions
handled" STOPs while a SUPERSEDED study has neither outcome, or its line is not
on the page.

    python3 lean_editions.py <slug> check    the preflight row
"""
from __future__ import annotations

import glob
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OK, BAD = "ok", "BLOCKED"
ROW = "newer editions handled"
FRAME = "A newer edition exists: %s; this page uses %s."
LEAD = "A newer edition exists: "
BY = "code (lean rule 3b: newer edition)"
USED, DISCLOSED = "used", "disclosed"
SUPERSEDED = "SUPERSEDED"


def _clean(s: str) -> str:
    return " ".join(str(s or "").split()).rstrip(" .;").replace(";", ",")


def log_path(case: Path) -> Path:
    return case / "rulings" / "lean_editions.jsonl"


def decisions(case: Path) -> list[dict]:
    p = log_path(case)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _append(case: Path, rec: dict) -> dict:
    p = log_path(case)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def study_key(study: dict) -> str:
    return "%s || %s" % (_clean(study.get("name")), _clean(study.get("latest_known")))


def superseded(case: Path) -> list[dict]:
    """Every SUPERSEDED recency study in the case's gate reports, once each."""
    seen, out = set(), []
    for p in sorted(glob.glob(str(case / "draft" / "*.gate.json"))):
        try:
            rep = json.loads(Path(p).read_text(encoding="utf-8"))
        except ValueError:
            continue
        for s in (rep.get("recency") or {}).get("studies") or []:
            if isinstance(s, dict) and s.get("status") == SUPERSEDED and study_key(s) not in seen:
                seen.add(study_key(s))
                out.append(s)
    return out


def line_for(study: dict, edition: str) -> str:
    return FRAME % (_clean(study.get("latest_known")) or "a later edition", _clean(edition) or "an earlier edition")


def lines(case: Path) -> list[dict]:
    """The DISCLOSED lines, in decision order: [{key, sentence}] (one per study)."""
    out, seen = [], set()
    for d in decisions(case):
        if d.get("outcome") == DISCLOSED and d["key"] not in seen:
            seen.add(d["key"])
            out.append({"key": d["key"], "sentence": d["sentence"]})
    return out


def _spans_on(row: dict, sid: str) -> list[tuple[str, str]]:
    out = []
    for where, x in [("row", row)] + [("also_rests_on", y) for y in row.get("also_rests_on") or []] \
            + [("premises", y) for y in row.get("premises") or []]:
        if isinstance(x, dict) and x.get("source_id") == sid and x.get("span"):
            out.append((where, x["span"]))
    return out


def decide(slug: str, case: Path, study: dict, matched_sid: str | None, sources: list[dict],
           rows: dict, held: dict[str, str], write_rows=None) -> dict:
    """Settle one SUPERSEDED study. Returns the decision record (also logged).
    WRITE_ROWS(rows): saves rebound rows (bindings.json); a test passes a fake."""
    import audit_stage as A
    key = study_key(study)
    for d in decisions(case):
        if d.get("key") == key:
            return d                                  # decided once; never re-decided
    title = {s.get("id"): s.get("title") or "" for s in sources}
    newer = [s.get("id") for s in sources if matched_sid and s.get("newer_edition_of") == matched_sid
             and s.get("id") in held]
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "key": key, "by": BY,
           "study": study.get("name"), "latest_known": study.get("latest_known"), "old_source": matched_sid}
    if newer:
        nid = newer[0]
        on = [(k, r) for k, r in rows.items() if r.get("on_page") and _spans_on(r, matched_sid)]
        missing = [(k, sp[:80]) for k, r in on for _w, sp in _spans_on(r, matched_sid)
                   if A.locate(sp, held[nid]) is None]
        if on and not missing:
            import source_store as store
            dsha = (store.held(slug).get(nid) or {}).get("sha256")
            first = None
            for k, r in on:
                for x in [r] + list(r.get("also_rests_on") or []) + list(r.get("premises") or []):
                    if isinstance(x, dict) and x.get("source_id") == matched_sid:
                        x["source_id"] = nid
                        x["rebound_from"] = matched_sid
                        if "document_sha" in x:
                            x["document_sha"] = dsha
                        first = first or x.get("span")
            if write_rows:
                write_rows(rows)
            rec.update({"outcome": USED, "new_source": nid, "rows": [k for k, _r in on],
                        "quote": first, "sentence": None})
            return _append(case, rec)
        rec["not_used_because"] = ("no on-page sentence rests on the old source" if not on else
                                   "%d bound span(s) not in the newer edition (e.g. %s: %r)"
                                   % (len(missing), missing[0][0], missing[0][1]))
    edition = title.get(matched_sid) if matched_sid else study.get("name")
    rec.update({"outcome": DISCLOSED, "sentence": line_for(study, edition or study.get("name") or ""),
                "new_source": None})
    return _append(case, rec)


def settle_finding(f: dict, d: dict) -> None:
    """The gate-findings.json record for a decided study."""
    on = datetime.now(timezone.utc).date().isoformat()
    if d["outcome"] == USED:
        f.update({"decision": "accepted", "source_id": d["new_source"], "quote": d["quote"] or "",
                  "why": "newer edition used: %d row(s) rebound from %s to %s, every bound span found in "
                         "the newer edition (lean rule 3b)" % (len(d["rows"]), d["old_source"], d["new_source"]),
                  "by": BY, "on": on, "ruled": "lean_editions.decide"})
    else:
        f.update({"decision": "judgement", "source_id": "", "quote": "",
                  "why": "newer edition disclosed on the page (lean rule 3b): %s" % d["sentence"],
                  "by": BY, "on": on, "ruled": "lean_editions.decide"})
    f.pop("_fill_in", None)


def preflight_rows(slug: str, page_sentences: list[str] | None = None) -> list[tuple[str, str, str]]:
    import bindings as B
    import lean_sentences as LS
    import source_store as store
    case = store.case_dir(slug)
    studies = superseded(case)
    if not studies:
        return [(ROW, OK, "no gate recency study is SUPERSEDED")]
    ds = {d["key"]: d for d in decisions(case)}
    ps = page_sentences if page_sentences is not None else B.page_sentences(slug)
    on = {LS.words(s) for s in ps}
    open_, absent = [], []
    for s in studies:
        d = ds.get(study_key(s))
        if not d:
            open_.append(s.get("name") or "a study")
        elif d["outcome"] == DISCLOSED and LS.words(d["sentence"]) not in on:
            absent.append(d["sentence"])
    if open_ or absent:
        bits = []
        if open_:
            bits.append("%d SUPERSEDED stud(ies) neither used nor disclosed (run ruling.py gate): %s"
                        % (len(open_), "; ".join(open_[:3])))
        if absent:
            bits.append("%d disclosure line(s) not on the page (paste lean_sentences.py render): %r"
                        % (len(absent), absent[0][:120]))
        return [(ROW, BAD, "; ".join(bits))]
    n_used = sum(1 for d in ds.values() if d["outcome"] == USED)
    return [(ROW, OK, "%d SUPERSEDED stud(ies): %d newer edition(s) used, %d disclosed on the page"
             % (len(studies), n_used, len(studies) - n_used))]


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[1] != "check":
        print(__doc__)
        return 2
    for row in preflight_rows(argv[0]):
        print("  %-6s %-30s %s" % (row[1], row[0], row[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
