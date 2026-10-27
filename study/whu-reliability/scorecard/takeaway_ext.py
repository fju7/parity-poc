#!/usr/bin/env python3
"""Scorecard: spec (d)'s takeaway comparison on WHU-S05 to WHU-S08 (exploratory,
outside H1 and H2), for WHU, Claude Research, ChatGPT and Gemini.

    takeaway_ext.py estimate | run

The code is spec (d)'s own runner, ~/Projects/whu-study-private/scoring/takeaway/
takeaway.py (the two prompts verbatim from machine_only_plan.md, both judges
through judge_m1.py's call code, its parse), loaded unchanged with these
settings changed:

  questions: WHU-S05 to WHU-S08, the four systems, every extraction and every
    pair, as for S01-S04.
  A/B order: takeaway.py's one stream, random.Random(CONSISTENCY_SEED), drawn in
    its order over all eight questions; S05-S08 take the draws after S01-S04's.
    The S01-S04 draws are checked against the orders recorded in the S01-S04
    replies before anything runs.
  spend: ledger issue whu-scorecard-takeaway, run cap $12. That issue is not a
    whu-reliability-judging* issue, so before each call its spend is also added
    to the judging day cap and to the $390 study total check (quotecheck_m1.py's
    STUDY_TOTAL, less WHU's spend), so neither is bypassed.
  replies: ~/Projects/whu-study-private/scoring/takeaway_ext/<judge>/.

ChatGPT performed no web search on S05-S08 (deviations 2026-10-26); its answers
are compared as captured, and every output that reports them says so.
"""
from __future__ import annotations

import importlib.util
import itertools
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
PRIV = Path.home() / "Projects" / "whu-study-private" / "scoring"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load("takeaway", PRIV / "takeaway" / "takeaway.py")
J1 = T.J1
QC = _load("quotecheck_m1", STUDY / "results" / "machine_only" / "quotecheck_m1.py")

ISSUE = "whu-scorecard-takeaway"
CAP = 12.0
ALL = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04", "WHU-S05", "WHU-S06", "WHU-S07", "WHU-S08"]
QUESTIONS = ALL[4:]
NOTE = "ChatGPT performed no web search on WHU-S05 to WHU-S08 (deviations 2026-10-26)"


def orders() -> dict:
    """takeaway.py's A/B draw, continued over all eight questions."""
    rng, out = random.Random(J1.CONSISTENCY_SEED), {}
    for q in ALL:
        for s1, s2 in itertools.combinations(T.SYSTEMS, 2):
            out[(q, s1, s2)] = (s1, s2) if rng.random() < 0.5 else (s2, s1)
    return out


def check_s01_s04(o: dict) -> None:
    for (q, s1, s2), ab in o.items():
        if q not in ALL[:4]:
            continue
        for j in T.JUDGES:
            r = json.loads((PRIV / "takeaway" / j / ("C-%s-%s-%s.json" % (q, s1, s2))).read_text(encoding="utf-8"))
            if (r["blinded_order"]["A"], r["blinded_order"]["B"]) != ab:
                raise SystemExit("STOP: the A/B stream does not reproduce %s %s-%s's recorded order" % (q, s1, s2))


def tasks(ans: dict) -> list[dict]:
    o = orders()
    check_s01_s04(o)
    ts = [{"id": "X-%s-%s" % (q, s), "kind": "extract", "q": q, "systems": [s],
           "prefix": "ANSWER:\n\n" + ans[(q, s)], "rest": "\n\n" + T.EXTRACT}
          for q in QUESTIONS for s in T.SYSTEMS]
    for q in QUESTIONS:
        for s1, s2 in itertools.combinations(T.SYSTEMS, 2):
            a, b = o[(q, s1, s2)]
            ts.append({"id": "C-%s-%s-%s" % (q, s1, s2), "kind": "compare", "q": q, "systems": [a, b],
                       "prefix": "ANSWER A:\n\n" + ans[(q, a)] + "\n\nANSWER B:\n\n" + ans[(q, b)],
                       "rest": "\n\n" + T.COMPARE})
    return ts


_day_cap_stop = J1.day_cap_stop


def day_cap_and_total_stop(worst: float, now: datetime | None = None) -> str | None:
    """The judging day cap and the study total, with this issue's spend counted in both."""
    today = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    mine_today = sum(float(e.get("usd") or 0) for e in J1.S.entries()
                     if e.get("issue") == ISSUE and (e.get("at") or "").startswith(today))
    why = _day_cap_stop(worst + mine_today, now)
    if why:
        return why
    allj = sum(float(e.get("usd") or 0) for e in J1.S.entries()
               if (e.get("issue") or "").startswith(J1.JUDGING_ISSUE_PREFIX))
    total = allj + J1.spent(ISSUE) + QC.whu_spent()
    if total + worst > QC.STUDY_TOTAL:
        return "STUDY TOTAL: $%.3f spent of the $%.2f check; next call up to $%.3f" % (total, QC.STUDY_TOTAL, worst)
    return None


def configure() -> None:
    T.ISSUE, T.CAP, T.OUT = ISSUE, CAP, PRIV / "takeaway_ext"
    T.QUESTIONS = QUESTIONS
    T.tasks = tasks
    T.SCRIPT = "study/whu-reliability/scorecard/takeaway_ext.py"
    J1.day_cap_stop = day_cap_and_total_stop


if __name__ == "__main__":
    configure()
    print(NOTE)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "estimate"
    sys.exit({"estimate": lambda: (T.estimate(), 0)[1], "run": T.run}[cmd]())
