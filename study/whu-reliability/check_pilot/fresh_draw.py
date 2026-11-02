#!/usr/bin/env python3
"""The check pilot's fresh-set question draw (docs/whu-check-an-answer-pilot.md §16.1, §16.9).

    fresh_draw.py --commit <the §16 freeze commit> --cache DIR [--offline] [--frames cochrane,campbell,ipcc]
                  [--redraw N]
    fresh_draw.py import-pages --cache DIR      Fred's hand-saved AR6 SPM pages (§16.10) into the fetch cache

Round 1's draw (quarterly/round1_draw.py), imported unchanged, with the three differences §16.1 states:
  * two draws per frame (the IPCC two from different AR6 reports, round 1's test (d));
  * the shuffle is seeded with random.Random("%d/check-fresh-set" % SEED), SEED the freeze commit read as a
    hexadecimal integer, so the order is not round 1's;
  * the "used before" table adds round 1's four draws, and the duplicate test adds round 1's four questions and
    WHU-P03 (antimalarial prophylaxis, not in frames.WHU_QUESTIONS); the study's, the pilots' and P02/P04's entries
    are already in round 1's tables.
Every candidate checked is logged. Output: check_pilot/fresh_set/draws/<frame>-<commit>.json, written once.
Free: no model is called.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import random
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
_spec = importlib.util.spec_from_file_location("round1_draw", STUDY / "quarterly" / "round1_draw.py")
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
F = R.F

LABEL = "%d/check-fresh-set"
PLAN = {"cochrane": 2, "campbell": 2, "ipcc": 2}
OUT = HERE / "fresh_set" / "draws"
FREEZE_DOC = STUDY.parents[1] / "docs" / "whu-check-an-answer-pilot.md"
USED = {"cochrane": {"10.1002/14651858.CD012925.pub2": "WHU-Q1-01"},
        "campbell": {"10.1002/cl2.70016": "WHU-Q1-02"},
        "ipcc": {"AR6-SYR-B.1.3": "WHU-Q1-03", "AR6-WGIII-C.11.4": "WHU-Q1-04"}}
# §16.10: rejected on closer reading after the first draw, as round 1 rejected CD005632.pub4. A redraw (--redraw N)
# repeats the same shuffle with these in the "used before" table and is written to a second record.
CLOSER_READING = {"campbell": {"10.1002/cl2.1419": "drawn for the fresh set (c970903), rejected on closer reading "
                                                   "(advisor, 2026-11-02): a measurement-properties review does not "
                                                   "yield a question a member of the public would ask"}}
# §16.10: the file name Fred saves each AR6 SPM page as, in --cache, by the URL frames.ipcc_texts reads it from.
SAVED_PAGES = {"ipcc-ar6-wg1-spm.html": "https://www.ipcc.ch/report/ar6/wg1/chapter/summary-for-policymakers/",
               "ipcc-ar6-wg2-spm.html": "https://www.ipcc.ch/report/ar6/wg2/chapter/summary-for-policymakers/",
               "ipcc-ar6-wg3-spm.html": "https://www.ipcc.ch/report/ar6/wg3/chapter/summary-for-policymakers/",
               "ipcc-ar6-syr-spm.html": "https://www.ipcc.ch/report/ar6/syr/summary-for-policymakers/"}
PATTERNS = {
    "WHU-Q1-01 (digital tracking, decision support and client reminders in primary care)":
        [r"(?=.*(?:digital|mobile|mHealth|electronic|tablet|phone|SMS|text messag))"
         r"(?=.*(?:tracking|decision support|client communication|reminder))", "text"],
    "WHU-Q1-02 (education programmes for children with disabilities)":
        [r"(?=.*disabilit)(?=.*(?:educat|school|learning))", "text"],
    "WHU-Q1-03 (further warming: water cycle, extremes, ice, sea level, oceans)":
        [r"(?=.*\b(?:further|continued|future|additional|every increment of) (?:global )?warming\b)"
         r"(?=.*\b(?:water cycle|precipitation|sea level|ice|ocean|extremes?)\b)", "first sentence"],
    "WHU-Q1-04 (carbon dioxide removal and net zero)":
        [r"carbon dioxide removal|\bCDR\b|remov\w* (?:of )?(?:CO ?2|CO₂|carbon dioxide)|negative emissions|"
         r"direct air (?:carbon )?capture|\bBECCS\b|\bDACCS\b", "text"],
    "WHU-P03 (antimalarial prophylaxis)":
        [r"antimalarial|anti-malarial|malaria\w* (?:chemo)?prophyla|mefloquine|chloroquine|atovaquone|"
         r"doxycycline[^.]{0,80}malaria", "text"],
}


def extend(extra: dict, redraw: int = 0) -> dict:
    """round1_duplicates.json plus round 1's four draws (used before) and §16.1's added patterns; on a redraw, the
    entries rejected on closer reading as well."""
    out = copy.deepcopy(extra)
    for frame, rows in USED.items():
        out["used_entries"][frame].update(rows)
    if redraw:
        for frame, rows in CLOSER_READING.items():
            out["used_entries"][frame].update(rows)
    out["patterns"].update(PATTERNS)
    return out


def labelled_random(seed: int) -> random.Random:
    return random.Random(LABEL % seed)


def draw(frame: str, commit: str, texts: dict | None, get=None, pause: float = 1.0, redraw: int = 0) -> dict:
    """round1_draw.draw with this set's plan, tables and labelled seed; the record says so."""
    saved = R.PLAN, R.EXTRA, R.random
    R.PLAN, R.EXTRA = PLAN, extend(saved[1], redraw)
    R.random = types.SimpleNamespace(Random=labelled_random)
    try:
        res = R.draw(frame, commit, texts, get, pause)
    finally:
        R.PLAN, R.EXTRA, R.random = saved
    res.update(round="check-fresh-set", seed_label=LABEL % res["seed"],
               seed_rule=F.SEED_RULE + "; shuffled with random.Random(\"%d/check-fresh-set\" % seed) (pilot doc §16.1)",
               procedure=res["procedure"].replace("round1_draw.py: random.Random(seed)",
                                                  "check_pilot/fresh_draw.py (round1_draw.py's procedure): "
                                                  "random.Random(\"%d/check-fresh-set\" % seed)"))
    if redraw:
        res["redraw"] = {"n": redraw, "rejected_on_closer_reading": CLOSER_READING.get(frame, {}),
                         "why": "pilot doc §16.10: the same shuffle, with the rejected entries as used before"}
    return res


def import_pages(cache: Path) -> int:
    """Store each hand-saved page under the URL it was saved from, in frames.Fetcher's cache format; nothing is
    edited. Round 1's test (a) still checks every statement against the frame's statement_sha256."""
    import gzip
    rc = 0
    for name, url in SAVED_PAGES.items():
        src = cache / name
        if not src.exists():
            print("missing %s (save %s as this name)" % (src, url))
            rc = 1
            continue
        body = src.read_bytes()
        n = len(F.spm_statements(body))
        (cache / (F.sha(url)[:32] + ".gz")).write_bytes(gzip.compress(body))
        print("%s: %d bytes, sha256 %s, %d numbered statements -> cache for %s" % (name, len(body), F.sha(body), n, url))
        rc |= 0 if n else 1
    return rc


def main() -> int:
    if sys.argv[1:2] == ["import-pages"]:
        ap = argparse.ArgumentParser()
        ap.add_argument("--cache", required=True)
        return import_pages(Path(ap.parse_args(sys.argv[2:]).cache).expanduser())
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--cache", required=True, help="directory for fetched pages (never committed)")
    ap.add_argument("--frames", default="cochrane,campbell,ipcc")
    ap.add_argument("--offline", action="store_true", help="read IPCC pages from the cache only; fetch nothing")
    ap.add_argument("--redraw", type=int, default=0, help="a redraw after a rejection on closer reading (§16.10)")
    a = ap.parse_args()
    F.seed_from_commit(a.commit)
    frozen = R.F.frame_at_commit(FREEZE_DOC, a.commit)
    if frozen is None:
        raise SystemExit("commit %s does not hold %s" % (a.commit, FREEZE_DOC.name))
    import subprocess
    doc = subprocess.run(["git", "-C", str(STUDY.parents[1]), "show", "%s:docs/%s" % (a.commit, FREEZE_DOC.name)],
                         capture_output=True, text=True).stdout
    if "**16.9 Advisor ruling" not in doc:
        raise SystemExit("commit %s does not hold §16.9: the seed is the commit that freezes §16" % a.commit)
    rc = 0
    for frame in a.frames.split(","):
        ff = STUDY / "frames" / ("%s.json" % frame)
        if F.frame_at_commit(ff, a.commit) != F.sha(ff.read_bytes()):
            raise SystemExit("%s is not as committed in %s" % (ff, a.commit))
        out = OUT / ("%s-%s%s.json" % (frame, a.commit, "-redraw%d" % a.redraw if a.redraw else ""))
        if out.exists():
            raise SystemExit("%s exists: a draw is made once" % out)
        texts = None
        if frame == "ipcc":
            fe = F.Fetcher(Path(a.cache), nap_pause=20.0)
            fe.offline = a.offline
            texts = F.ipcc_texts(fe)
        res = draw(frame, a.commit, texts, redraw=a.redraw)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print("fresh-set draw %s from %s: checked %d of %d eligible; drawn %s -> %s" % (
            frame, a.commit[:12], res["checked"], res["eligible"],
            ", ".join(str(d.get("id") or d.get("pmid")) for d in res["drawn"]) or "nothing", out))
        rc |= 0 if len(res["drawn"]) == PLAN[frame] else 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
