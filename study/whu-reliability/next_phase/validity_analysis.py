#!/usr/bin/env python3
"""The validity checks' analyses (validity_plan.md, frozen at b4cf31a). Free: no model is called.

    validity_analysis.py check9 | check6 | check1 | check10 | check4 | check5

Each writes next_phase/results/<check>.json: numbers and item ids only, no answer, key or source text.

RULES. analyse.py's, through quarterly/analyse_round1.py's setup (round1_rows: replies "", the EVERY abstract-only
rule): scores per item with analyse.score, intervals with analyse.analyse_view (whole questions resampled, 10,000,
seeded by round 1's freeze). A check changes WHICH label an item counts with, or WHICH items count; never the rule
that turns labels into rates.

THE SEVEN (plan §0): the §6A comparisons whose interval excludes zero under both judges alone, two-judge combined,
all four questions. Each check tests them against its own "conclusion changes if" rule.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
OUT = HERE / "results"
PLAN_FREEZE = "b4cf31ad19046a63073461fc5195415bc496594b"
SEED = int(PLAN_FREEZE, 16)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


AR = _load("analyse_round1_v", STUDY / "quarterly" / "analyse_round1.py")
A = AR.A
PS = _load("prepare_scoring_v", STUDY / "scripts" / "prepare_scoring.py")
CL = _load("claims_v", HERE / "claims.py")
QS, SYSTEMS, SETS = AR.QS, AR.SYSTEMS, AR.SETS
SEVEN = [("M1_failure", "Claude"), ("M1_failure", "ChatGPT"), ("M1_failure", "Gemini"), ("M1_failure", "Perplexity"),
         ("M2_overstates", "ChatGPT"), ("M2_overstates", "Gemini"), ("M2_understates_omits", "ChatGPT")]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def view_of(scores: list[tuple], qs: list[str]) -> dict:
    """analyse.analyse_view over (question, system, score) tuples, configured as analyse_round1.view is."""
    A.QUESTIONS, A.SYSTEMS, A.SEED = list(qs), list(SYSTEMS), AR.SEED
    A.HEALTH, A.FRAME = {"WHU-Q1-01"} & set(qs), {q: q for q in qs}
    return AR.compact(A.analyse_view([x for x in scores if x[0] in qs]), SYSTEMS)


def scores(rows: list[dict], measure: str, label_of) -> list[tuple]:
    """(question, system, score) with LABEL_OF(row) -> list of labels counted (the mean of their scores)."""
    _, fail, ok = AR.MEASURES[measure]
    out = []
    for r in rows:
        got = [s for s in (A.score(l, fail, ok) for l in label_of(r)) if s is not None]
        out.append((r["question"], r["system"], sum(got) / len(got) if got else None))
    return out


def combined(r):
    return [r["labels"][j] for j in A.JUDGES]


def seven(v: dict, measure: str) -> dict:
    return {s: {"whu": v["WHU"]["rate"], "tool": v[s]["rate"], "difference": v[s]["WHU_vs"]["difference_whu_minus"],
                "ci95": v[s]["WHU_vs"]["difference_ci95"], "n_whu": v["WHU"]["countable"], "n_tool": v[s]["countable"]}
            for m, s in SEVEN if m == measure}


def changes(base: dict, alt: dict) -> dict:
    """Plan's common test: direction reverses, the interval includes zero, or the lead is under half."""
    d0, d1, ci, ci0 = base["difference"], alt["difference"], alt["ci95"], base["ci95"]
    base_excludes = ci0[0] is not None and not (ci0[0] <= 0 <= ci0[1])
    return {"reverses": d1 is not None and d0 is not None and (d1 > 0) != (d0 > 0) and d1 != 0,
            # a crossing counts only where the as-scored interval excluded zero in the same set
            "ci_includes_zero": base_excludes and (ci[0] is None or (ci[0] <= 0 <= ci[1])),
            "lead_under_half": d1 is not None and abs(d1) < 0.5 * abs(d0) if d0 < 0 else False}


def write(name: str, obj: dict) -> dict:
    OUT.mkdir(exist_ok=True)
    obj = {"written": now(), "plan": "next_phase/validity_plan.md @ %s" % PLAN_FREEZE[:7],
           "label": "Judged by AI models; not checked by people (check 5 aside).", **obj}
    (OUT / (name + ".json")).write_text(json.dumps(obj, indent=1) + "\n")
    return obj


# ---------------------------------------------------------------------------------------------------------------
# check 9: reachability both ways (plan §7)
# ---------------------------------------------------------------------------------------------------------------

def held_routes() -> dict:
    run = AR.RUN / "m1"
    items = json.loads((run / "items.json").read_text(encoding="utf-8"))
    man = {r["url"]: r for r in json.loads((run / "sources" / "manifest.json").read_text())}
    return {it["item"]: [PS.how_held(man.get(c["url"])) if c.get("url") else "unreachable" for c in it["citations"]]
            for it in items}


def check9() -> dict:
    m1, _ = AR.round1_rows()
    routes = held_routes()
    excl = A.M1_EXCL

    def route(r):
        hs = routes.get(r["item"], [])
        return "uncited" if r["uncited"] else "unreachable" if "unreachable" in hs else \
            "operator" if "operator" in hs else "script"

    def no_judge(r):                      # cited, nothing held: no judge was called (raw empty)
        return not r["uncited"] and not r["raw"]

    def as_scored(r):
        return combined(r)

    def count_a(r):                       # (a) unreachable, undelivered and not-held items count as failures
        if no_judge(r) or any(l in excl for l in combined(r) if l) or (
                not r["uncited"] and all(l is None for l in combined(r))):
            return ["UNCITED"]            # an M1 failure label, standing for "counted as a failure"
        return combined(r)

    def count_b(r):                       # (b) those items excluded
        if no_judge(r) or any(l in excl for l in combined(r) if l):
            return []
        return combined(r)

    def count_c(r):                       # (c) script-reachable only
        return [] if route(r) in ("operator", "unreachable") else count_b(r)

    table = {}
    for r in m1:
        t = table.setdefault(r["system"], {"drawn": 0, "uncited": 0, "cited": 0, "by_script": 0, "by_operator_fetch": 0,
                                           "unreachable": 0, "no_judge_called": 0, "excluded_label_any": 0})
        t["drawn"] += 1
        k = route(r)
        t["uncited" if k == "uncited" else "cited"] += 1
        if k != "uncited":
            t[{"script": "by_script", "operator": "by_operator_fetch", "unreachable": "unreachable"}[k]] += 1
        t["no_judge_called"] += no_judge(r)
        t["excluded_label_any"] += any(l in excl for l in combined(r) if l)
    res = {"rules": {"a": "unreachable, undelivered (INCOMPLETE_SOURCES), NOT_VERIFIABLE_ABSTRACT and no-judge items "
                          "count as failures", "b": "those items excluded",
                     "c": "(b), and items needing an operator fetch (route d) also excluded"},
           "table": table, "sets": {}}
    for set_name, qs in SETS.items():
        base = view_of(scores(m1, "M1_failure", as_scored), qs)
        out = {"as_scored": seven(base, "M1_failure")}
        for k, fn in (("a", count_a), ("b", count_b), ("c", count_c)):
            v = seven(view_of(scores(m1, "M1_failure", fn), qs), "M1_failure")
            out[k] = {s: {**x, "test": changes(out["as_scored"][s], x)} for s, x in v.items()}
        out["conclusion_changes"] = any(any(t["test"].values()) for k in "abc" for t in out[k].values())
        res["sets"][set_name] = out
    res["conclusion_changes"] = res["sets"]["all_four"]["conclusion_changes"]
    return write("check9", res)


# ---------------------------------------------------------------------------------------------------------------
# check 6: the claim definition (plan §6)
# ---------------------------------------------------------------------------------------------------------------

def protected_by_question() -> dict:
    out = {}
    for q in QS:
        d = next((REPO / "issues").glob(q + "-*"))
        out[q] = CL.protected_map(d / "bindings.json")
    return out


def item_kinds() -> dict:
    run = AR.RUN / "m1"
    km = json.loads((run / "key_map.json").read_text(encoding="utf-8"))
    prot = protected_by_question()
    out = {}
    for f in ("items.json", "uncited.json"):
        for it in json.loads((run / f).read_text(encoding="utf-8")):
            k = km[it["item"]]
            p = prot.get(k["question"], {}).get(CL._norm(it["claim"])) if k["system"] == "WHU" else None
            out[it["item"]] = CL.kind(it["claim"], it.get("context") or "", p)
    return out


def check6() -> dict:
    m1, _ = AR.round1_rows()
    kinds = item_kinds()
    from collections import Counter
    tally = {}
    for r in m1:
        tally.setdefault(r["system"], Counter())[kinds[r["item"]]] += 1
    res = {"rule": "claims.py (frozen with the plan); round 1 classified after the fact, a labelled sensitivity; "
                   "round 1's pre-stated results stand", "kinds_by_system": {s: dict(c) for s, c in tally.items()},
           "sets": {}}
    for set_name, qs in SETS.items():
        base = seven(view_of(scores(m1, "M1_failure", combined), qs), "M1_failure")
        new = seven(view_of(scores(m1, "M1_failure", lambda r: combined(r) if kinds[r["item"]] == "claim" else []),
                            qs), "M1_failure")
        res["sets"][set_name] = {"old_definition": base, "new_definition": {
            s: {**x, "test": {"reverses": changes(base[s], x)["reverses"],
                              "ci_includes_zero": changes(base[s], x)["ci_includes_zero"]}} for s, x in new.items()}}
        res["sets"][set_name]["conclusion_changes"] = any(
            any(x["test"].values()) for x in res["sets"][set_name]["new_definition"].values())
    res["non_claim_items"] = sorted(i for i, k in kinds.items() if k != "claim")
    res["conclusion_changes"] = res["sets"]["all_four"]["conclusion_changes"]
    return write("check6", res)


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"check9": check9, "check6": check6}.get(which)
    if not fn:
        print(__doc__)
        return 2
    r = fn()
    print(json.dumps({k: v for k, v in r.items() if k not in ("non_claim_items",)}, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
