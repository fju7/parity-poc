#!/usr/bin/env python3
"""Perplexity add-on: spec (d)'s takeaway comparison, WHU against Perplexity on
WHU-S01 to WHU-S04 (exploratory, outside H1 and H2).

    takeaway_perplexity.py estimate | run | report

Plan: study/whu-reliability/perplexity_plan.md. The code is spec (d)'s own
runner, ~/Projects/whu-study-private/scoring/takeaway/takeaway.py (the two
prompts verbatim from machine_only_plan.md, Claude Opus 5.5 and gpt-6-astra
through judge_m1.py's call code, its parse and quote check), loaded unchanged
with these settings changed:

  tasks: extraction of Perplexity's four blinded answers, and one comparison
    per question of WHU against Perplexity, A/B order from
    random.Random("<SEED>/takeaway/<question>/WHU-Perplexity") (recorded).
    WHU's S01-S04 extractions are spec (d)'s, reused, not re-run.
  answers: WHU's blinded text checked against scoring/blinded_manifest.txt,
    Perplexity's against results/perplexity/blinded_manifest.txt.
  spend: ledger issue whu-reliability-judging-perplexity, the add-on's one
    issue, so the $47.81 run cap covers judging and this together; the
    judging day cap applies as in takeaway.py.
  replies: ~/Projects/whu-study-private/scoring/perplexity/takeaway/<judge>/.

"report" writes results/perplexity/takeaway_perplexity.json: the ratings per
question and judge, direct_answer and confidence_conveyed per answer and
judge, and the quote-check and form counts. No answer text.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
PRIV = Path.home() / "Projects" / "whu-study-private" / "scoring"
PPLX = PRIV / "perplexity"
_spec = importlib.util.spec_from_file_location("takeaway", PRIV / "takeaway" / "takeaway.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)
J1 = T.J1

ISSUE = "whu-reliability-judging-perplexity"
CAP = 47.81                 # $390 less $342.19 (Fred, 2026-10-27; was $32.82 under the $375 check)
QUESTIONS = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"]


def _manifest(path: Path) -> dict:
    out = {}
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        out[(f[1], f[2])] = f[0]
    return out


def answers() -> dict:
    out = {}
    for q in QUESTIONS:
        for s, base, man in (("WHU", PRIV, STUDY / "scoring" / "blinded_manifest.txt"),
                             ("Perplexity", PPLX, HERE / "blinded_manifest.txt")):
            b = (base / "blinded" / q / ("%s.blind.txt" % s.lower())).read_bytes()
            if hashlib.sha256(b).hexdigest() != _manifest(man)[(q, s)]:
                raise SystemExit("STOP: %s %s blinded text does not match its manifest" % (q, s))
            out[(q, s)] = b.decode("utf-8")
    return out


def tasks(ans: dict) -> list[dict]:
    ts = [{"id": "X-%s-Perplexity" % q, "kind": "extract", "q": q, "systems": ["Perplexity"],
           "prefix": "ANSWER:\n\n" + ans[(q, "Perplexity")], "rest": "\n\n" + T.EXTRACT} for q in QUESTIONS]
    for q in QUESTIONS:
        rng = random.Random("%d/takeaway/%s/WHU-Perplexity" % (J1.CONSISTENCY_SEED, q))
        a, b = ("WHU", "Perplexity") if rng.random() < 0.5 else ("Perplexity", "WHU")
        ts.append({"id": "C-%s-WHU-Perplexity" % q, "kind": "compare", "q": q, "systems": [a, b],
                   "prefix": "ANSWER A:\n\n" + ans[(q, a)] + "\n\nANSWER B:\n\n" + ans[(q, b)],
                   "rest": "\n\n" + T.COMPARE})
    return ts


def configure() -> None:
    T.ISSUE, T.CAP, T.OUT = ISSUE, CAP, PPLX / "takeaway"
    T.QUESTIONS, T.SYSTEMS = QUESTIONS, ["WHU", "Perplexity"]
    T.answers, T.tasks = answers, tasks
    T.SCRIPT = "study/whu-reliability/results/perplexity/takeaway_perplexity.py"


def report() -> int:
    ans = answers()
    out = {"label": "Exploratory, outside H1 and H2: spec (d) takeaway comparison, WHU against Perplexity, "
                    "AI judges only; disagreements reported, not resolved",
           "questions": QUESTIONS, "comparisons": {}, "extractions": {}, "quote_check": [], "form_problems": [],
           "whu_extractions_reused_from": "spec (d) run, scoring/takeaway/<judge>/X-<question>-WHU.json"}
    for q in QUESTIONS:
        for j in T.JUDGES:
            for s, f in (("WHU", PRIV / "takeaway" / j / ("X-%s-WHU.json" % q)),
                         ("Perplexity", PPLX / "takeaway" / j / ("X-%s-Perplexity.json" % q))):
                r = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
                p = r.get("parsed") or {}
                out["extractions"].setdefault(q, {}).setdefault(s, {})[j] = {
                    "direct_answer": p.get("direct_answer"), "confidence_conveyed": p.get("confidence_conveyed"),
                    "recommended_actions": len(p.get("recommended_actions") or []),
                    "key_caveats": len(p.get("key_caveats") or []), "replied": bool(r)}
                if r.get("form_problems"):
                    out["form_problems"].append({"id": r["id"], "judge": j, "problems": r["form_problems"]})
            f = PPLX / "takeaway" / j / ("C-%s-WHU-Perplexity.json" % q)
            if not f.exists():
                out["comparisons"].setdefault(q, {})[j] = None
                continue
            r = json.loads(f.read_text(encoding="utf-8"))
            p, order = r["parsed"] or {}, r["blinded_order"]
            row = {"rating": p.get("rating"), "rating_valid": p.get("rating") in T.RATINGS,
                   "a_was": order["A"], "difference_given": bool(p.get("difference"))}
            for side in "AB":
                qv = p.get("quote_" + side.lower())
                if qv is None:
                    continue
                ok = isinstance(qv, str) and T.quote_ok(qv, ans[(q, order[side])])
                words = len(qv.split()) if isinstance(qv, str) else None
                row["quote_%s_found" % order[side]] = ok
                out["quote_check"].append({"id": r["id"], "judge": j, "quote_of": order[side], "found": ok,
                                           "words": words, "over_40_words": (words or 0) > 40})
            if r.get("form_problems"):
                out["form_problems"].append({"id": r["id"], "judge": j, "problems": r["form_problems"]})
            out["comparisons"].setdefault(q, {})[j] = row
        c = out["comparisons"].get(q, {})
        out["comparisons"][q]["judges_agree"] = (None if not all(c.get(j) for j in T.JUDGES)
                                                 else c["claude"]["rating"] == c["openai"]["rating"])
    out["rating_counts"] = {j: {k: sum(1 for q in QUESTIONS if (out["comparisons"][q].get(j) or {}).get("rating") == k)
                                for k in T.RATINGS} for j in T.JUDGES}
    out["spend_on_issue"] = round(J1.spent(ISSUE), 4)
    (HERE / "takeaway_perplexity.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({q: {j: (out["comparisons"][q].get(j) or {}).get("rating") for j in T.JUDGES}
                      for q in QUESTIONS}, indent=1))
    return 0


if __name__ == "__main__":
    configure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "estimate"
    sys.exit({"estimate": lambda: (T.estimate(), 0)[1], "run": T.run, "report": report}[cmd]())
