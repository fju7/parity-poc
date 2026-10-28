#!/usr/bin/env python3
"""Round 1's question draw (round1_protocol.md §1).

    round1_draw.py --commit <freeze commit> --cache DIR [--frames cochrane,campbell,ipcc]

Uses the study's frames.py unchanged (imported, not edited): its frame files, seed rule,
shuffle, statement fetch and duplicate test. Follows frames.draw_study's procedure and adds
the round's tests, in this order, for each candidate in the shuffle:
  (a) IPCC: the statement as fetched hashes to the frame's statement_sha256;
  (b) not an entry the study or the pilots used (round1_duplicates.json "used_entries");
  (c) the duplicate test: frames.WHU_QUESTIONS plus round1_duplicates.json "patterns";
  (d) IPCC's second question: not from the same AR6 report as the first;
  (e) Cochrane and Campbell: Option 2 (deviations 2026-10-24): Europe PMC's license field is
      CC BY, CC BY-NC or CC BY-NC-ND, and its fullTextXML answers HTTP 200 with an XML content
      type (status and content type only; the text is neither read nor saved).
The first candidate passing all is the draw. Every candidate checked is logged. Output:
quarterly/draws/<frame>-<commit>.json, written once. Free: no model is called.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
_spec = importlib.util.spec_from_file_location("frames", STUDY / "scripts" / "frames.py")
F = importlib.util.module_from_spec(_spec)
sys.modules["frames"] = F
_spec.loader.exec_module(F)

EXTRA = json.loads((HERE / "round1_duplicates.json").read_text(encoding="utf-8"))
PLAN = F.STUDY_DRAW_PLAN                      # cochrane 1, campbell 1, ipcc 2
OPEN = {"cc by", "cc by-nc", "cc by-nc-nd"}
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:%s%%20AND%%20SRC:MED&resultType=core&format=json"
FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML"


def questions() -> dict:
    """frames.WHU_QUESTIONS plus round 1's patterns, as {name: (pattern, scope)}."""
    return {**F.WHU_QUESTIONS, **{k: (v[0], v[1]) for k, v in EXTRA["patterns"].items()}}


def duplicates(text: str) -> list[str]:
    out = []
    for name, (pat, scope) in questions().items():
        if re.search(pat, F.first_sentence(text) if scope == "first sentence" else text, re.I | re.S):
            out.append(name)
    return out


def used(frame: str, r: dict) -> str | None:
    table = EXTRA["used_entries"][frame]
    for key in (r.get("doi"), r.get("id"), r.get("pmid")):
        if key and key in table:
            return table[key]
    return None


def option2(pmid: str, get=None) -> dict:
    """Europe PMC licence and full-text availability, by status and content type only."""
    import requests
    get = get or requests.get
    r = get(EPMC % pmid, timeout=60)
    res = (r.json().get("resultList") or {}).get("result") or []
    rec = res[0] if res else {}
    lic, pmcid = (rec.get("license") or None), rec.get("pmcid")
    out = {"europepmc_license": lic, "pmcid": pmcid}
    if not lic or lic.strip().lower() not in OPEN:
        return {**out, "ok": False, "why": "Europe PMC license %r, not CC BY / CC BY-NC / CC BY-NC-ND" % lic}
    if not pmcid:
        return {**out, "ok": False, "why": "no PMCID in Europe PMC"}
    t = get(FULLTEXT % pmcid, timeout=60, stream=True)
    ctype = t.headers.get("content-type", "")
    t.close()
    out.update(fulltext_status=t.status_code, fulltext_content_type=ctype)
    if t.status_code != 200 or "xml" not in ctype.lower():
        return {**out, "ok": False, "why": "fullTextXML answered HTTP %s, %s" % (t.status_code, ctype or "no content type")}
    return {**out, "ok": True}


def draw(frame: str, commit: str, texts: dict | None, get=None, pause: float = 1.0) -> dict:
    ff = STUDY / "frames" / ("%s.json" % frame)
    seed = F.seed_from_commit(commit)
    fr = json.loads(ff.read_text(encoding="utf-8"))
    rows = {r["n"]: r for r in fr["rows"]}
    elig = {e["k"]: e for e in fr["eligible"]}
    order = sorted(elig)
    random.Random(seed).shuffle(order)
    log, drawn, want = [], [], PLAN[frame]
    for i, k in enumerate(order, 1):
        if len(drawn) >= want:
            break
        r = rows[elig[k]["n"]]
        rid = r.get("id") or r.get("pmid")
        rec = {"checked": i, "k": k, "n": r["n"], "id": rid}
        if texts is not None:
            t = texts.get(rid)
            if t is None or F.sha(t) != r.get("statement_sha256"):
                rec.update(result="undetermined", why="the statement as fetched now is %s"
                           % ("missing" if t is None else "not the one the frame hashed (sha256 differs)"))
                log.append(rec)
                continue
        else:
            t = r.get("title") or ""
        rec["text_sha256"] = F.sha(t)
        u = used(frame, r)
        dup = duplicates(t)
        if u:
            rec.update(result="ineligible", why="used before: %s" % u)
        elif dup:
            rec.update(result="ineligible", why="its question would duplicate one WHU has published, tested or "
                                                 "studied: " + "; ".join(dup))
        elif drawn and r.get("report") and any(d.get("report") == r.get("report") for d in drawn):
            rec.update(result="passed over", why="from the same AR6 report as an earlier draw (%s)" % r["report"])
        elif frame in ("cochrane", "campbell"):
            o = option2(r["pmid"], get)
            time.sleep(pause)
            rec["option2"] = {k2: v for k2, v in o.items() if k2 != "ok"}
            if not o["ok"]:
                rec.update(result="ineligible", why="Option 2: " + o["why"])
            else:
                rec.update(result="drawn", draw=len(drawn) + 1)
                drawn.append(r)
        else:
            rec.update(result="drawn", draw=len(drawn) + 1)
            drawn.append(r)
        log.append(rec)
    keep = ("n", "id", "pmid", "doi", "title", "date", "report", "year", "url", "level", "statement_sha256")
    return {"round": "Q1", "frame_file": "frames/%s.json" % frame, "frame_sha256": F.sha(ff.read_bytes()),
            "commit": commit, "seed": seed, "seed_rule": F.SEED_RULE,
            "procedure": "round1_draw.py: random.Random(seed).shuffle of the frame's eligible numbers k (as "
                         "frames.draw_study); in that order (a) statement hash (IPCC), (b) not used before, "
                         "(c) duplicate test, (d) different AR6 report (IPCC's second), (e) Option 2 (Cochrane, "
                         "Campbell); the first that passes all is the draw",
            "whu_questions": {k2: {"pattern": v[0], "applied_to": v[1]} for k2, v in questions().items()},
            "used_entries": EXTRA["used_entries"][frame],
            "draws_wanted": want, "eligible": len(order), "checked": len(log),
            "drawn": [{x: d[x] for x in keep if x in d} for d in drawn], "drawn_at": F.now(), "log": log}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--cache", required=True, help="scratch directory for fetched pages (never committed)")
    ap.add_argument("--frames", default="cochrane,campbell,ipcc")
    ap.add_argument("--offline", action="store_true",
                    help="read IPCC pages from the cache only (frames.Fetcher.offline); fetch nothing")
    a = ap.parse_args()
    F.seed_from_commit(a.commit)
    if F.frame_at_commit(HERE / "round1_protocol.md", a.commit) is None:
        raise SystemExit("commit %s does not hold quarterly/round1_protocol.md: the seed is the freeze commit" % a.commit)
    rc = 0
    for frame in a.frames.split(","):
        ff = STUDY / "frames" / ("%s.json" % frame)
        if F.frame_at_commit(ff, a.commit) != F.sha(ff.read_bytes()):
            raise SystemExit("%s is not as committed in %s" % (ff, a.commit))
        out = HERE / "draws" / ("%s-%s.json" % (frame, a.commit))
        if out.exists():
            raise SystemExit("%s exists: a draw is made once" % out)
        texts = None
        if frame == "ipcc":
            fe = F.Fetcher(Path(a.cache), nap_pause=20.0)
            fe.offline = a.offline
            texts = F.ipcc_texts(fe)
        res = draw(frame, a.commit, texts)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("round 1 draw %s from %s: checked %d of %d eligible; drawn %s -> %s" % (
            frame, a.commit[:12], res["checked"], res["eligible"],
            ", ".join(str(d.get("id") or d.get("pmid")) for d in res["drawn"]) or "nothing", out))
        rc |= 0 if len(res["drawn"]) == PLAN[frame] else 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
