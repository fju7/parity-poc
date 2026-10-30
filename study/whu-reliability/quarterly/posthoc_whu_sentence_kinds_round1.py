#!/usr/bin/env python3
"""POST-HOC (after the §6 results; not pre-stated): WHU's drawn M1 sentences by
kind, and a sensitivity of WHU's M1 failure rate without readers'-list lines
and protected process sentences, round 1 and the study.

    posthoc_whu_sentence_kinds_round1.py

Writes quarterly/round1_scoring/posthoc_whu_sentence_kinds_round1.json: item
ids and counts only. Free: no model is called. The pre-stated §6B verdict
(analyse_round1.py: conditions 2 and 3 not met) is unchanged; this is reported
beside it, never instead of it.

KINDS, from the drawn sentence's text (items.json / uncited.json "claim") and
its page's bindings.json:
  (a) readers'-list line: starts with one of coverage_check.py's leads
      ("Outside this question:", "Judged not material to this question:",
      "Not added:");
  (b) protected process sentence: starts with "We " (what WHU held, read,
      obtained or searched) or "The question is" (the question restated), or
      matches a binding row marked protected "question" or "reading";
  (c) other.
STUDY. WHU's M1 rows on WHU-S01 to S08, read by analyse_eight.py's setup
(replies "" and "_ext", EVERY rule), pages issues/WHU-S0N-*/ (not the re-runs).
SENSITIVITY. analyse.py's two-judge combined and each judge's M1 failure
rate, with (a) and (b) items removed from both sets; the difference round 1
minus study with analyse_round1.part_b's bootstrap (questions resampled
within each set, 10,000 resamples, random.Random(int(round-1 freeze, 16))).
"""
from __future__ import annotations

import importlib.util
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("analyse_round1_ph", HERE / "analyse_round1.py")
AR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AR)
A = AR.A
STUDY_RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "m1"
OUT = AR.LOG / "posthoc_whu_sentence_kinds_round1.json"
LEADS = ("Outside this question:", "Judged not material to this question:", "Not added:")
TAG = "POST-HOC sensitivity (after the §6 results; not pre-stated; the §6B verdict stands)"


def norm(t: str) -> str:
    t = re.sub(r"\[\d+(?:[,–-]\s*\d+)*\]", " ", t or "")
    return " ".join(re.findall(r"[a-z0-9]+", t.lower()))


def protected_sentences(q: str) -> set:
    d = next((REPO / "issues").glob(q + "-*"))
    b = json.loads((d / "bindings.json").read_text())["bindings"]
    return {norm(r["sentence"]) for r in b.values() if r.get("protected") in ("question", "reading")}


def kind(text: str, prot: set) -> str:
    t = " ".join((text or "").split())
    if t.startswith(LEADS):
        return "a"
    s = norm(t)
    if t.startswith("We ") or t.startswith("The question is") or \
            any(s == p or (len(s) >= 30 and (s in p or p in s)) for p in prot):
        return "b"
    return "c"


def kinds_for(run: Path, rows: list[dict]) -> dict:
    texts = {}
    for f in ("items.json", "uncited.json"):
        for it in json.loads((run / f).read_text()):
            texts[it["item"]] = it["claim"]
    prot = {q: protected_sentences(q) for q in sorted({r["question"] for r in rows})}
    return {r["item"]: kind(texts[r["item"]], prot[r["question"]]) for r in rows}


def describe(rows, kinds, qs) -> dict:
    out = {"by_question": {q: {k: sum(1 for r in rows if r["question"] == q and kinds[r["item"]] == k)
                               for k in "abc"} for q in qs},
           "total": {k: sum(1 for r in rows if kinds[r["item"]] == k) for k in "abc"},
           "countable_by_kind_combined": {}, "labels": {}}
    for k in "ab":
        its = [r for r in rows if kinds[r["item"]] == k]
        out["labels"][k] = {"items": [{"item": r["item"], "question": r["question"], "uncited": r["uncited"],
                                       **{j: r["labels"][j] for j in A.JUDGES}} for r in its],
                            "counts": {j: {l: sum(1 for r in its if r["labels"][j] == l)
                                           for l in sorted({str(r["labels"][j]) for r in its})} for j in A.JUDGES}}
    return out


def rates(r1, st, q1, qs) -> dict:
    rng = random.Random(AR.SEED)
    boots = [([rng.choice(q1) for _ in q1], [rng.choice(qs) for _ in qs]) for _ in range(A.B)]
    out = {}
    for vn in ("combined", "claude_judge", "openai_judge"):
        t1, ts = AR.tally(r1, "M1_failure", vn), AR.tally(st, "M1_failure", vn)
        a, b = A.rate(t1, "WHU", q1), A.rate(ts, "WHU", qs)
        diffs = [x - y for x, y in ((A.rate(t1, "WHU", b1), A.rate(ts, "WHU", b2)) for b1, b2 in boots)
                 if x is not None and y is not None]
        out[vn] = {"label": TAG, "round1": A.r4(a), "round1_countable": sum(t1.get((q, "WHU"), [0, 0])[1] for q in q1),
                   "study": A.r4(b), "study_countable": sum(ts.get((q, "WHU"), [0, 0])[1] for q in qs),
                   "difference_round1_minus_study": A.r4(None if a is None or b is None else a - b),
                   "difference_ci95": [A.r4(A.pct(diffs, 0.025)), A.r4(A.pct(diffs, 0.975))]}
    return out


def main() -> int:
    m1, _ = AR.round1_rows()
    r1 = [r for r in m1 if r["system"] == "WHU"]
    k1 = kinds_for(AR.RUN / "m1", r1)
    s1, _, sq = AR.study_whu_rows()
    ks = kinds_for(STUDY_RUN, s1)
    keep = lambda rows, k: [r for r in rows if k[r["item"]] == "c"]
    countable = lambda rows, k, kk: sum(1 for r in rows if k[r["item"]] == kk and any(
        r["labels"][j] in A.M1_FAIL | A.M1_PASS for j in A.JUDGES))
    res = {"label": TAG, "rules": "quarterly/posthoc_whu_sentence_kinds_round1.py docstring",
           "pre_stated_verdict_6B": "fixes 1-3 not reported as having held: conditions 2 and 3 not met "
                                    "(round1_ai_only.json); unchanged by this analysis",
           "round1": describe(r1, k1, AR.QS), "study": describe(s1, ks, sq),
           "study_readers_list_lines_confirmed_zero": all(v != "a" for v in ks.values()),
           "countable_items_by_kind": {"round1": {k: countable(r1, k1, k) for k in "abc"},
                                       "study": {k: countable(s1, ks, k) for k in "abc"}},
           "sensitivity_M1_excluding_a_and_b": {
               "all_four": rates(keep(r1, k1), keep(s1, ks), AR.QS, sq),
               "without_Q1_02": rates([r for r in keep(r1, k1) if r["question"] != "WHU-Q1-02"], keep(s1, ks),
                                      AR.SETS["without_Q1_02"], sq)},
           "as_judged_for_reference": {"all_four": rates(r1, s1, AR.QS, sq)}}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(TAG)
    print(json.dumps({k: res[k] for k in ("countable_items_by_kind", "study_readers_list_lines_confirmed_zero")}))
    for side in ("round1", "study"):
        print(side, res[side]["total"], res[side]["by_question"], json.dumps(res[side]["labels"]["a"]["counts"]),
              json.dumps(res[side]["labels"]["b"]["counts"]))
    for st, v in res["sensitivity_M1_excluding_a_and_b"].items():
        for vn, x in v.items():
            print("POST-HOC", st, vn, x["round1"], x["round1_countable"], x["study"], x["study_countable"],
                  x["difference_round1_minus_study"], x["difference_ci95"])
    for vn, x in res["as_judged_for_reference"]["all_four"].items():
        print("as judged", vn, x["round1"], x["study"], x["difference_round1_minus_study"], x["difference_ci95"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
