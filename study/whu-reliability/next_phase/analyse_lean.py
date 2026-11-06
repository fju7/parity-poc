#!/usr/bin/env python3
"""Lean four-question test: the pass rule and the secondary views
(lean_test_rule.md §3-5; validity_plan.md §10), AI judges only.

    analyse_lean.py

Writes next_phase/results/lean/lean_ai_only.json: numbers, item ids and
hashes only, no answer, key or source text. Free: no model is called.

SCORED. The lean pages that reached `Ready.` on the sixth freeze 9863fb2:
WHU-Q1-01 (whu-lean-q1-01c), WHU-Q1-02 (whu-lean-q1-02b), WHU-Q1-03
(whu-lean-q1-03b). WHU-Q1-04 (whu-lean-q1-04c) is Not Ready: "recorded, not
scored, and it fails the bars it cannot meet" (lean_test_rule.md §3).

RULES. Round 1's, through its own code: quarterly/analyse_round1.py's
measures, views and bootstrap (analyse.py via analyse_eight.py: each judge's
first-read label after the refusal rule; Uncited is an M1 failure;
Unreachable, INCOMPLETE_SOURCES and NOT_VERIFIABLE_ABSTRACT excluded;
two-judge combined = the mean of the judges' failure indicators; whole
questions resampled, 10,000 resamples, random.Random(int(round-1 freeze, 16))).
analyse.analyse_view compares every system with the one named "WHU", so here
lean's rows carry the name "WHU" and round 1's full-WHU rows "WHU-full"; the
output names them "WHU-lean" and "WHU-full".

COMPARISON SETS. The three scored questions; and without WHU-Q1-02 (as round 1
reports). Round 1's answers and labels are unchanged; they are read for the
same questions only (Gemini and Perplexity have all three; Perplexity's Q1-01 and Q1-02 are
inline answers, scored as captured, as in round 1).

BAR 3's second view (lean_test_rule.md §3.3; check 3c): M1 with readers'-list
lines and protected process sentences removed, by
posthoc_whu_sentence_kinds_round1.kind's rule, applied to each lean page's
own bindings.json.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import statistics as st
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
LOG = HERE / "results" / "lean"
RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "lean"
QS = ["WHU-Q1-01", "WHU-Q1-02", "WHU-Q1-03"]
SLUGS = {"WHU-Q1-01": "whu-lean-q1-01c", "WHU-Q1-02": "whu-lean-q1-02b", "WHU-Q1-03": "whu-lean-q1-03b"}
FOLDERS = {"WHU-Q1-01": "WHU-L1-01c-whu-lean-q1-01c", "WHU-Q1-02": "WHU-L1-02b-whu-lean-q1-02b",
           "WHU-Q1-03": "WHU-L1-03b-whu-lean-q1-03b"}
NOT_READY = {"WHU-Q1-04": {"slug": "whu-lean-q1-04c", "freeze": "9863fb2",
                           "why": "Not Ready: lint_claims.unknowability on the rule-3b line, and "
                                  "'newer editions handled' (no registry list in the gate record)"}}
LEAN_ISSUES = ["whu-lean-q1-01c", "whu-lean-q1-02b", "whu-lean-q1-03b", "whu-lean-q1-04c"]
JUDGING = "whu-reliability-judging-lean"
SETS = {"three_scored": QS, "without_Q1_02": ["WHU-Q1-01", "WHU-Q1-03"]}
TOOLS = ["Claude", "ChatGPT", "Gemini", "Perplexity"]
SYSTEMS = ["WHU", "WHU-full"] + TOOLS          # "WHU" here is lean (see the docstring)
NAME = {"WHU": "WHU-lean", "WHU-full": "WHU-full"}
# round 1's WHU, all four questions (lean_test_rule.md §3; quarterly/round1_scoring/round1_ai_only.json)
R1 = {"M1_combined": 0.1203, "M1_excl_process_declaration": 0.0299,
      "M2_understates_omits": {"claude_judge": 0.0, "openai_judge": 0.0526},
      "M2_overstates_contradicts": {"claude_judge": 0.0, "openai_judge": 0.1053}}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


AR = _load("analyse_round1_lean", STUDY / "quarterly" / "analyse_round1.py")
PH = _load("posthoc_kinds_lean", STUDY / "quarterly" / "posthoc_whu_sentence_kinds_round1.py")
A = AR.A


def lean_rows():
    A.PRIVATE, A.QUESTIONS, A.TAGS = RUN, list(QS), ("",)
    m1, m2 = A.items_m1(), A.items_m2()
    AR.C.abstract_correct(m1)
    for r in m1 + m2:
        assert r["system"] == "WHU-lean", r["system"]
        r["system"] = "WHU"
    return m1, m2


def round1_rows():
    A.PRIVATE, A.QUESTIONS, A.TAGS = AR.RUN, list(QS), ("",)
    m1, m2 = A.items_m1(), A.items_m2()
    AR.C.abstract_correct(m1)
    for r in m1 + m2:
        if r["system"] == "WHU":
            r["system"] = "WHU-full"
    return m1, m2


def view(rows, qs, systems, measure, vn):
    _, fail, ok = AR.MEASURES[measure]
    A.QUESTIONS, A.SYSTEMS, A.SEED = list(qs), list(systems), AR.SEED
    A.HEALTH, A.FRAME = {"WHU-Q1-01"} & set(qs), {q: q for q in qs}
    rs = [r for r in rows if r["question"] in qs and r["system"] in systems]
    return A.analyse_view(A.view_scores(rs, fail, ok)[vn])


def compact(v, systems):
    out = {}
    for s in systems:
        x = v["systems"][s]
        out[NAME.get(s, s)] = {k: x[k] for k in ("failures", "countable", "rate", "ci95")} | {
            "per_question": {q: (y["rate"], y["countable"]) for q, y in x["per_question"].items()}}
    for s in systems[1:]:
        w = v["vs_whu"][s]
        out[NAME.get(s, s)]["lean_vs"] = {"difference_lean_minus": w["difference_whu_minus"],
                                          "difference_ci95": w["difference_ci95"],
                                          "difference_ci_excludes_zero": w["difference_ci_excludes_zero"]}
    return out


def kinds(m1) -> dict:
    texts = {}
    for f in ("items.json", "uncited.json"):
        for it in json.loads((RUN / "m1" / f).read_text()):
            texts[it["item"]] = it["claim"]
    prot = {}
    for q, d in FOLDERS.items():
        b = json.loads((REPO / "issues" / d / "bindings.json").read_text())["bindings"]
        prot[q] = {PH.norm(r["sentence"]) for r in b.values() if r.get("protected") in ("question", "reading")}
    return {r["item"]: PH.kind(texts[r["item"]], prot[r["question"]]) for r in m1 if r["system"] == "WHU"}


def rate_of(rows, measure, vn, qs, system="WHU"):
    t = AR.tally([r for r in rows if r["system"] == system and r["question"] in qs], measure, vn)
    n = sum(t.get((q, system), [0, 0])[1] for q in qs)
    return A.r4(A.rate(t, system, qs)), n


def spend() -> dict:
    S = _load("spend_ledger_lean", REPO / "backend" / "scripts" / "spend_ledger.py")
    by = {}
    for e in S.entries():
        i = e.get("issue") or ""
        if i in LEAN_ISSUES or i == JUDGING:
            by[i] = by.get(i, 0.0) + float(e.get("usd") or 0)
    return {i: round(v, 2) for i, v in sorted(by.items())}


def main() -> int:
    l1, l2 = lean_rows()
    r1, r2 = round1_rows()
    m1, m2 = l1 + r1, l2 + r2
    out = {"written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "label": "Lean four-question test: AI judges only, not checked by people; in-sample; "
                    "needs confirming on new questions",
           "rules": "next_phase/analyse_lean.py docstring (round 1's code and rules)",
           "scored": SLUGS, "not_scored": NOT_READY, "freeze": "9863fb2", "seed": str(AR.SEED),
           "bootstrap_resamples": A.B}
    # counts
    out["M1_counts_lean"] = AR.counts([dict(r, system="WHU") for r in l1], "WHU")
    out["M2_items_lean"] = len(l2)
    A.SYSTEMS, A.QUESTIONS = ["WHU"], list(QS)
    out["M1_judges_lean"] = A.judge_stats(l1, A.M1_FAIL)
    out["M2_judges_lean"] = A.judge_stats(l2, A.M2_FAIL)
    # comparisons
    comp = {}
    for set_name, qs in SETS.items():
        comp[set_name] = {}
        for measure, (which, _, _) in AR.MEASURES.items():
            rows = m1 if which == "M1" else m2
            systems = [s for s in SYSTEMS if any(r["system"] == s and r["question"] in qs for r in rows)]
            comp[set_name][measure] = {vn: compact(view(rows, qs, systems, measure, vn), systems)
                                       for vn in AR.VIEWS}
    out["comparisons"] = comp
    # bar 3, second view: without readers'-list lines (a) and protected process sentences (b)
    k = kinds(m1)
    l1c = [r for r in l1 if k.get(r["item"]) == "c"]
    out["M1_kinds_lean"] = {x: sum(1 for v in k.values() if v == x) for x in "abc"}
    # bars
    cost = spend()
    per = [cost.get(SLUGS[q], 0.0) for q in QS]
    per4 = per + [cost.get("whu-lean-q1-04c", 0.0)]
    m1c, n1 = rate_of(l1, "M1_failure", "combined", QS)
    m1x, n1x = rate_of(l1c, "M1_failure", "combined", QS)
    m2 = {}
    ok4 = True
    for measure in ("M2_understates_omits", "M2_overstates_contradicts"):
        m2[measure] = {}
        for vn in ("claude_judge", "openai_judge"):
            lean, n = rate_of(l2, measure, vn, QS)
            full3, n3 = rate_of(r2, measure, vn, QS, "WHU-full")
            ref = R1[measure][vn]
            holds = lean is not None and lean <= ref
            ok4 = ok4 and holds
            m2[measure][vn] = {"lean": lean, "countable": n, "round1_whu_all_four": ref,
                               "round1_whu_same_three": full3, "round1_same_three_countable": n3,
                               "lean_no_higher_than_round1": holds}
    bars = {
        "1_cost": {"ledger_per_answer_scored": dict(zip(QS, per)), "median_scored": round(st.median(per), 2),
                   "with_Q1_04c": round(st.median(per4), 2), "none_over_10": max(per4) <= 10.0,
                   "holds": st.median(per) < 5.0 and max(per4) <= 10.0},
        "2_fred_time": {"minutes": 0, "holds": True},
        "3_M1": {"combined": m1c, "countable": n1, "bar": 0.15,
                 "excluding_process_and_declaration": m1x, "countable_excl": n1x, "bar_excl": 0.06,
                 "holds": m1c is not None and m1c <= 0.15 and m1x is not None and m1x <= 0.06},
        "4_M2": dict(m2, holds=ok4),
        "5_seeded_defect": "deferred, not dropped",
        "Q1_04": "Not Ready (whu-lean-q1-04c): recorded, not scored; fails bars 3 and 4 for that question",
    }
    met = all(bars[b]["holds"] for b in ("1_cost", "2_fred_time", "3_M1", "4_M2"))
    bars["verdict"] = ("does not pass §10: WHU-Q1-04 did not reach Ready" +
                       ("; on the three scored questions bars 1-4 hold" if met else
                        "; on the three scored questions not every bar holds"))
    out["pass_rule"] = bars
    sec = comp["three_scored"]["M1_failure"]["combined"]
    out["secondary"] = {
        "a_M1_within_10_points": {"lean": m1c, "bar": 0.22, "holds": m1c is not None and m1c <= 0.22},
        "b_lead_over_each_tool": {t: sec[t]["lean_vs"] for t in TOOLS if t in sec},
        "b_lead_without_Q1_02": {t: comp["without_Q1_02"]["M1_failure"]["combined"][t]["lean_vs"]
                                 for t in TOOLS if t in comp["without_Q1_02"]["M1_failure"]["combined"]},
        "c_cost_and_time": {"median_ledger": bars["1_cost"]["median_scored"], "human_minutes": 0},
    }
    out["spend"] = cost
    LOG.mkdir(parents=True, exist_ok=True)
    p = LOG / "lean_ai_only.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"pass_rule": bars, "secondary": out["secondary"]}, indent=1))
    print("wrote %s sha256 %s" % (p, hashlib.sha256(p.read_bytes()).hexdigest()[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
