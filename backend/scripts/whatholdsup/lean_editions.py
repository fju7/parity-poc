#!/usr/bin/env python3
"""A newer edition (lean WHU, rule 3b; process doc §4.6.1, "What 'we read'
means"; advisor's rulings of 5 November 2026 after Q1-04).

A gate recency study with status SUPERSEDED or UNKNOWN is never routed to a
person under lean. It is first matched to a page source by every identifier
(match(): DOI, PMID, PMCID, URL; first author and title; title overlap), and
code settles it (advisor's rulings after Q1-04 and after Q1-01b):

  USED       a held source records "newer_edition_of": "<old source id>" in
             sources.json, and every on-page bound span on the old source is
             found in the newer edition's held text: code rebinds those rows
             to the newer source (bindings.json; each row keeps
             "rebound_from"), logs it in rulings/lean_editions.jsonl, and the
             finding is decided "accepted" by code, citing one rebound span in
             the newer edition.
  DISCLOSED  SUPERSEDED, matched, newer edition not used: the code line
                 A newer edition exists of <title>; this page uses <edition>.
             (both from sources.json; never the gate's prose or figures).
  UNKNOWN    UNKNOWN, matched: We could not establish whether <title> has a newer edition.
  UNTIED     not matched: recorded, and counted on the page in one code line,
                 N recency questions not tied to any source on this page were
                 recorded and not acted on.
             Each line is a required page element, protected as "reading"
             (bindings.NEWER_EDITION). The finding is decided "judgement" by
             code, naming its line; never dismissed.

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
# Code-known text only (advisor's ruling after Q1-01b): the source's sources.json
# title and edition; the gate's prose and figures stay in the records.
FRAME = "A newer edition exists of %s; this page uses %s."
# After Q1-04c (advisor's ruling, option (b); process doc §4.6.1): the line says whose
# check it was, and what it searched when the gate's recency record lists that. An
# UNKNOWN line resting on a record with no list of registries searched STOPs the row
# below, whatever the wording: missing provenance stops the page.
UNKNOWN_FRAME = "Our recency check could not establish whether %s has a newer edition."
UNKNOWN_FRAME_SEARCHED = "Our recency check (searched: %s) could not establish whether %s has a newer edition."
OLD_UNKNOWN_LEAD = "We could not establish whether "     # lines decided before the sixth freeze
COUNT_FRAME = "%d recency questions not tied to any source on this page were recorded and not acted on."
COUNT_FRAME_ONE = "1 recency question not tied to any source on this page was recorded and not acted on."
LEADS = ("A newer edition exists of ", "Our recency check ", OLD_UNKNOWN_LEAD)
COUNT_RE = __import__("re").compile(r"^\d+ recency questions? not tied to any source on this page")
BY = "code (lean rule 3b: newer edition)"
USED, DISCLOSED, UNKNOWN_LINE, UNTIED = "used", "disclosed", "unknown", "untied"
SUPERSEDED, UNKNOWN = "SUPERSEDED", "UNKNOWN"
HANDLED = (SUPERSEDED, UNKNOWN)
COUNT_KEY = "untied recency questions (count)"


def searched_of(study: dict) -> list[str]:
    """The registries the gate's recency record says it searched ([] when it lists none)."""
    got = study.get("searched") or study.get("registries_searched") or []
    if isinstance(got, str):
        got = [got]
    return [" ".join(str(x).split()) for x in got if str(x).strip()]


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
    """Every SUPERSEDED or UNKNOWN recency study in the case's gate reports, once each."""
    seen, out = set(), []
    for p in sorted(glob.glob(str(case / "draft" / "*.gate.json"))):
        try:
            rep = json.loads(Path(p).read_text(encoding="utf-8"))
        except ValueError:
            continue
        for s in (rep.get("recency") or {}).get("studies") or []:
            if isinstance(s, dict) and s.get("status") in HANDLED and study_key(s) not in seen:
                seen.add(study_key(s))
                out.append(s)
    return out


def _one_sentence(s: str) -> bool:
    import source_ledger as ledger
    return len(ledger.sentences(s)) == 1


def title_of(sources: list[dict], sid: str) -> str:
    """The source's sources.json title, or its numbered label when the title
    would be cut by the page's splitter (lean_sentences.cite)."""
    import lean_sentences as LS
    s = next((x for x in sources if x.get("id") == sid), {})
    t = _clean(s.get("title"))
    if t and _one_sentence(UNKNOWN_FRAME % t):
        return t
    return LS.cite(sources, sid)


def edition_of(sources: list[dict], sid: str) -> str:
    import lean_sentences as LS
    s = next((x for x in sources if x.get("id") == sid), {})
    e = _clean(s.get("edition"))
    if e and _one_sentence(UNKNOWN_FRAME % e):
        return e
    return "the edition listed as %s" % LS.cite(sources, sid)


def line_for(sources: list[dict], sid: str) -> str:
    return FRAME % (title_of(sources, sid), edition_of(sources, sid))


def count_line(n: int) -> str:
    return COUNT_FRAME_ONE if n == 1 else COUNT_FRAME % n


def lines(case: Path) -> list[dict]:
    """The code lines, in decision order: [{key, sentence}], one per disclosed or
    unknown study, then one count line for the untied ones."""
    out, seen, untied = [], set(), set()
    for d in decisions(case):
        if d["key"] in seen:
            continue
        seen.add(d["key"])
        if d.get("outcome") in (DISCLOSED, UNKNOWN_LINE):
            out.append({"key": d["key"], "sentence": d["sentence"]})
        elif d.get("outcome") == UNTIED:
            untied.add(d["key"])
    if untied:
        out.append({"key": COUNT_KEY, "sentence": count_line(len(untied))})
    return out


def is_code_line(sentence: str) -> bool:
    w = " ".join((sentence or "").split())
    return w.startswith(LEADS) or bool(COUNT_RE.match(w))


# ------------------------------------------------------------------ matching

_DOI = __import__("re").compile(r"10\.\d{4,9}/[^\s\"'<>),;]+", __import__("re").I)
_PMID = __import__("re").compile(r"\bPMID:?\s*(\d{5,9})\b", __import__("re").I)
_PMC = __import__("re").compile(r"\bPMC\d{5,9}\b", __import__("re").I)
_URL = __import__("re").compile(r"https?://[^\s\"'<>)]+", __import__("re").I)


def _ids_of(text: str) -> set:
    out = set()
    for m in _DOI.finditer(text or ""):
        out.add("doi:" + m.group(0).lower().rstrip("."))
    for m in _PMID.finditer(text or ""):
        out.add("pmid:" + m.group(1))
    for m in _PMC.finditer(text or ""):
        out.add("pmcid:" + m.group(0).upper())
    for m in _URL.finditer(text or ""):
        u = m.group(0).lower().rstrip("./")
        u = __import__("re").sub(r"^https?://(?:www\.)?", "", u)
        out.add("url:" + u)
    return out


def _source_ids(s: dict) -> set:
    bits = [str(s.get(k) or "") for k in ("doi", "url", "identifier", "citation")]
    bits += ["PMID %s" % s["pmid"]] if s.get("pmid") else []
    bits += ["PMID %s" % s["pubmed"]] if isinstance(s.get("pubmed"), (str, int)) and str(s.get("pubmed")).isdigit() else []
    bits += [str(s.get("pmcid") or "")] + [str(x) for x in s.get("also_called") or []]
    ids = _ids_of(" ".join(bits))
    if s.get("doi"):
        ids.add("doi:" + str(s["doi"]).lower().replace("https://doi.org/", "").replace("doi:", "").strip())
    return ids


def match(slug: str, study: dict, sources: list[dict], rows: dict) -> tuple:
    """(source id or None, how): the one page source STUDY is about, by every
    identifier in turn (advisor's ruling after Q1-01b): a DOI, PMID, PMCID or
    URL; first author and title (findings.recency_targets); title overlap."""
    import findings as F
    sid_ids = {s.get("id"): _source_ids(s) for s in sources if s.get("id")}
    mine = _ids_of(" ".join(str(study.get(k) or "") for k in ("name", "url", "draft_uses")))
    hits = sorted({sid for sid, ids in sid_ids.items() if ids & mine})
    if len(hits) == 1:
        both = sorted(sid_ids[hits[0]] & mine)
        return hits[0], "identifier (%s)" % ", ".join(both)
    if len(hits) > 1:
        return None, "identifiers match %d sources (%s)" % (len(hits), ", ".join(hits))
    try:
        sids, _keys = F.recency_targets(slug, study.get("name") or "", rows)
    except (Exception, SystemExit):           # no case for SLUG: the identifier and title tests still run
        sids = []
    if sids:
        return sids[0], "first author and title (findings.recency_targets)"
    sw = F._words(study.get("name") or "")
    best = []
    for s in sources:
        tw = F._words(s.get("title") or "")
        shared = tw & sw
        if tw and sw and len(shared) >= F.TITLE_MIN_SHARED and len(shared) / min(len(tw), len(sw)) >= F.TITLE_OVERLAP:
            best.append(s.get("id"))
    if len(best) == 1:
        return best[0], "title overlap (no author)"
    if best:
        return None, "title overlap with %d sources (%s)" % (len(best), ", ".join(best))
    return None, "no DOI, PMID, PMCID, URL, author or title matches a page source"


def _spans_on(row: dict, sid: str) -> list[tuple[str, str]]:
    out = []
    for where, x in [("row", row)] + [("also_rests_on", y) for y in row.get("also_rests_on") or []] \
            + [("premises", y) for y in row.get("premises") or []]:
        if isinstance(x, dict) and x.get("source_id") == sid and x.get("span"):
            out.append((where, x["span"]))
    return out


def decide(slug: str, case: Path, study: dict, matched_sid: str | None, sources: list[dict],
           rows: dict, held: dict[str, str], write_rows=None, matched_by: str = "") -> dict:
    """Settle one SUPERSEDED study. Returns the decision record (also logged).
    WRITE_ROWS(rows): saves rebound rows (bindings.json); a test passes a fake."""
    import audit_stage as A
    key = study_key(study)
    for d in decisions(case):
        if d.get("key") == key:
            return d                                  # decided once; never re-decided
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "key": key, "by": BY,
           "study": study.get("name"), "status": study.get("status"), "latest_known": study.get("latest_known"),
           "old_source": matched_sid, "matched_by": matched_by}
    if not matched_sid:
        rec.update({"outcome": UNTIED, "sentence": None, "new_source": None})
        return _append(case, rec)
    if study.get("status") != SUPERSEDED:
        searched = searched_of(study)
        title = title_of(sources, matched_sid)
        line = UNKNOWN_FRAME_SEARCHED % (_clean(", ".join(searched)), title) if searched else UNKNOWN_FRAME % title
        if searched and not _one_sentence(line):
            line = UNKNOWN_FRAME_SEARCHED % ("%d registries" % len(searched), title)
        rec.update({"outcome": UNKNOWN_LINE, "sentence": line, "searched": searched, "new_source": None})
        return _append(case, rec)
    newer = [s.get("id") for s in sources if s.get("newer_edition_of") == matched_sid and s.get("id") in held]
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
    rec.update({"outcome": DISCLOSED, "sentence": line_for(sources, matched_sid), "new_source": None})
    return _append(case, rec)


def settle_finding(f: dict, d: dict) -> None:
    """The gate-findings.json record for a decided study."""
    on = datetime.now(timezone.utc).date().isoformat()
    if d["outcome"] == USED:
        f.update({"decision": "accepted", "source_id": d["new_source"], "quote": d["quote"] or "",
                  "why": "newer edition used: %d row(s) rebound from %s to %s, every bound span found in "
                         "the newer edition (lean rule 3b)" % (len(d["rows"]), d["old_source"], d["new_source"]),
                  "by": BY, "on": on, "ruled": "lean_editions.decide"})
    elif d["outcome"] == UNTIED:
        f.update({"decision": "judgement", "source_id": "", "quote": "",
                  "why": "recency question not tied to any source on this page (%s); recorded and counted "
                         "on the page, not acted on (lean rule 3b)" % d.get("matched_by", ""),
                  "by": BY, "on": on, "ruled": "lean_editions.decide"})
    else:
        f.update({"decision": "judgement", "source_id": "", "quote": "",
                  "why": "%s on the page (lean rule 3b; matched by %s): %s"
                         % ("newer edition disclosed" if d["outcome"] == DISCLOSED else "unknown recency stated",
                            d.get("matched_by", ""), d["sentence"]),
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
    for ln in lines(case):
        if LS.words(ln["sentence"]) not in on:
            absent.append(ln["sentence"])
    # missing provenance (after Q1-04c): an UNKNOWN line whose recency record lists no registry searched
    blind = [d for d in ds.values() if d.get("outcome") == UNKNOWN_LINE and not d.get("searched")]
    if open_ or absent or blind:
        bits = []
        if open_:
            bits.append("%d SUPERSEDED or UNKNOWN stud(ies) not yet decided (run ruling.py gate): %s"
                        % (len(open_), "; ".join(open_[:3])))
        if absent:
            bits.append("%d code line(s) not on the page (paste lean_sentences.py render): %r"
                        % (len(absent), absent[0][:120]))
        if blind:
            bits.append("%d UNKNOWN recency stud(ies) rest on a gate record that lists no registry searched, "
                        "so nothing shows where the check looked (missing provenance stops the page): %s"
                        % (len(blind), "; ".join((d.get("study") or "?")[:80] for d in blind[:3])))
        return [(ROW, BAD, "; ".join(bits))]
    by = {}
    for s in studies:
        o = ds[study_key(s)]["outcome"]
        by[o] = by.get(o, 0) + 1
    how = "; ".join("%s: %s" % ((s.get("name") or "?")[:50], ds[study_key(s)].get("matched_by") or "-")
                    for s in studies)
    return [(ROW, OK, "%d recency stud(ies) not CURRENT: %s. Matched by: %s"
             % (len(studies), ", ".join("%d %s" % (n, o) for o, n in sorted(by.items())), how))]


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
