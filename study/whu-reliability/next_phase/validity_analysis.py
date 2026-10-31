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
import re
import sys
from datetime import datetime, timezone
from collections import Counter
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


# ---------------------------------------------------------------------------------------------------------------
# checks 1 and 2: the Google judge; the non-Anthropic view (plan §1, §2)
# ---------------------------------------------------------------------------------------------------------------

def google_labels(rows: list[dict], measure: str, tag: str = "", run: Path | None = None) -> int:
    """r["labels"]["google"]: Google's own first-read label (no fill from another judge: three judges, no refusal
    fill), with the EVERY abstract-only rule applied as cross_company.abstract_correct applies it."""
    run = run or (AR.RUN / measure.lower())
    valid = (A.M1_PASS | A.M1_FAIL | A.M1_EXCL) if measure == "M1" else (A.M2_PASS | A.M2_FAIL)
    n = 0
    for r in rows:
        if r["uncited"]:
            r["labels"]["google"] = A.UNCITED
            continue
        f = run / ("replies" + tag) / "google" / (r["item"] + ".json")
        rep = json.loads(f.read_text()) if f.exists() else {}
        lab = rep.get("label")
        if lab == A.NVA and rep.get("judge_label") == "Absent" and not all(
                x.get("abstract_only") for x in rep.get("sources") or []):
            lab = "Absent"
        r["labels"]["google"] = lab if lab in valid else None
        n += bool(rep)
    return n


def three(r):
    return [r["labels"][j] for j in ("claude", "openai", "google")]


def non_anthropic(r):
    return [r["labels"][j] for j in ("openai", "google")]


def by_judge(rows, measure, qs, fn) -> dict:
    return seven(view_of(scores(rows, measure, fn), qs), measure)


def check1() -> dict:
    m1, m2 = AR.round1_rows()
    got = {"M1": google_labels(m1, "M1"), "M2": google_labels(m2, "M2")}
    res = {"google_replies": got, "model": "gemini-4-argon", "sets": {}}
    for set_name, qs in SETS.items():
        out = {}
        for measure in ("M1_failure", "M2_overstates", "M2_understates_omits"):
            rows = m1 if measure.startswith("M1") else m2
            v = {name: by_judge(rows, measure, qs, fn) for name, fn in (
                ("claude", lambda r: [r["labels"]["claude"]]), ("openai", lambda r: [r["labels"]["openai"]]),
                ("google", lambda r: [r["labels"]["google"]]), ("two_judge", combined), ("three_judge", three),
                ("openai_google", non_anthropic))}
            for s, g in v["google"].items():
                c, o = v["claude"][s]["difference"], v["openai"][s]["difference"]
                hi = max(c, o)
                g["test"] = {
                    "outside_range_narrowing_by_more_than_5_points": g["difference"] is not None and g["difference"] > hi + 0.05,
                    "outside_range_widening_reported": g["difference"] is not None and g["difference"] < min(c, o) - 0.05,
                    "ci_includes_zero_or_reverses": g["ci95"][0] is None or g["ci95"][1] >= 0,
                    "gemini_self_preference_flag": s == "Gemini"}
            out[measure] = v
        flags = [(m, s) for m, s in SEVEN for x in [out[m]["google"][s]["test"]]
                 if x["outside_range_narrowing_by_more_than_5_points"] or x["ci_includes_zero_or_reverses"]]
        out["changed"] = flags
        out["conclusion_changes"] = bool(flags)
        res["sets"][set_name] = out
    res["conclusion_changes"] = res["sets"]["all_four"]["conclusion_changes"]
    res["agreement_with_google"] = agreement(m1, m2)
    return write("check1", res)


def agreement(m1, m2) -> dict:
    out = {}
    for name, rows in (("M1", m1), ("M2", m2)):
        for j in ("claude", "openai"):
            pairs = [(r["labels"][j], r["labels"]["google"]) for r in rows if not r["uncited"]
                     and r["labels"][j] is not None and r["labels"]["google"] is not None]
            out["%s_%s_vs_google" % (name, j)] = {"n": len(pairs), "same_label": sum(a == b for a, b in pairs)}
    return out


def check2() -> dict:
    m1, m2 = AR.round1_rows()
    google_labels(m1, "M1")
    google_labels(m2, "M2")
    res = {"sets": {}}
    for set_name, qs in SETS.items():
        out = {}
        for measure in ("M1_failure", "M2_overstates", "M2_understates_omits", "M2_overstates_contradicts"):
            rows = m1 if measure.startswith("M1") else m2
            two = view_of(scores(rows, measure, combined), qs)
            na = view_of(scores(rows, measure, non_anthropic), qs)
            cj = view_of(scores(rows, measure, lambda r: [r["labels"]["claude"]]), qs)
            tests = {}
            for s in SYSTEMS[1:]:
                d2, dn = two[s]["WHU_vs"]["difference_whu_minus"], na[s]["WHU_vs"]["difference_whu_minus"]
                ci = na[s]["WHU_vs"]["difference_ci95"]
                tests[s] = {"two_judge_difference": d2, "non_anthropic_difference": dn, "non_anthropic_ci95": ci,
                            "in_seven": (measure, s) in SEVEN,
                            "ci_includes_zero": ci[0] is None or ci[0] <= 0 <= ci[1],
                            "lead_under_half": d2 is not None and dn is not None and d2 < 0 and dn > 0.5 * d2}
            bias = {s: None if cj[s]["rate"] is None or na[s]["rate"] is None else round(cj[s]["rate"] - na[s]["rate"], 4)
                    for s in SYSTEMS}
            others = [bias[s] for s in ("ChatGPT", "Gemini", "Perplexity") if bias[s] is not None]
            base = sum(others) / len(others) if others else 0.0
            out[measure] = {"tests": tests, "rates": {s: {"two_judge": two[s]["rate"], "non_anthropic": na[s]["rate"],
                                                          "claude_judge": cj[s]["rate"], "n": na[s]["countable"]}
                                                      for s in SYSTEMS},
                            "self_preference": {"claude_minus_non_anthropic": bias,
                                                "non_claude_tools_mean": round(base, 4),
                                                "flag_WHU": bias["WHU"] is not None and bias["WHU"] - base < -0.05,
                                                "flag_Claude": bias["Claude"] is not None and bias["Claude"] - base < -0.05}}
        flags = [(m, s) for m, s in SEVEN if out[m]["tests"][s]["ci_includes_zero"] or out[m]["tests"][s]["lead_under_half"]]
        out["changed"] = flags
        out["conclusion_changes"] = bool(flags)
        res["sets"][set_name] = out
    res["conclusion_changes"] = res["sets"]["all_four"]["conclusion_changes"]
    return write("check2", res)


# ---------------------------------------------------------------------------------------------------------------
# check 10: prompt wording (plan §8)
# ---------------------------------------------------------------------------------------------------------------

C10_TAG = "_c10alt"
PRIV = Path.home() / "Projects" / "whu-study-private"


def check10() -> dict:
    smp = json.loads((PRIV / "validity" / "check10" / "sample.json").read_text())
    m1, m2 = AR.round1_rows()
    res = {"tag": C10_TAG, "flips": {}, "shifts": {}, "sets": {}}
    for measure_kind, rows, ids in (("M1", m1, set(smp["items"]["M1"])), ("M2", m2, set(smp["items"]["M2"]))):
        run = AR.RUN / measure_kind.lower()
        alt = A.load_replies(run, C10_TAG)
        valid = (A.M1_PASS | A.M1_FAIL | A.M1_EXCL) if measure_kind == "M1" else (A.M2_PASS | A.M2_FAIL)
        sub = [r for r in rows if r["item"] in ids]
        for r in sub:
            r["alt"] = A.per_judge_labels(alt.get(r["item"], {}), valid)
        for j in A.JUDGES:
            pf = [(r["labels"][j], r["alt"][j]) for r in sub if r["labels"][j] and r["alt"][j]]
            fail = A.M1_FAIL if measure_kind == "M1" else A.M2_FAIL
            res["flips"]["%s_%s" % (measure_kind, j)] = {
                "n": len(pf), "exact_label_changed": sum(a != b for a, b in pf),
                "pass_fail_changed": sum((a in fail) != (b in fail) for a, b in pf if a not in A.M1_EXCL and b not in A.M1_EXCL),
                "replies_missing": len(sub) - len(pf)}
            n = res["flips"]["%s_%s" % (measure_kind, j)]
            n["flip_rate_pass_fail"] = round(n["pass_fail_changed"] / n["n"], 4) if n["n"] else None
            n["instability_flag_over_15pct"] = bool(n["flip_rate_pass_fail"] and n["flip_rate_pass_fail"] > 0.15)
        res["_rows_" + measure_kind] = (rows, sub)
    for set_name, qs in SETS.items():
        out = {}
        for measure in ("M1_failure", "M2_overstates", "M2_understates_omits"):
            rows, sub = res["_rows_M1" if measure.startswith("M1") else "_rows_M2"]
            _, fail, ok = AR.MEASURES[measure]
            base = view_of(scores(rows, measure, combined), qs)
            shift = {}
            for sy in SYSTEMS:
                ss = [r for r in sub if r["system"] == sy and r["question"] in qs]
                def rate(fn):
                    v = [x for x in (sum(g) / len(g) if g else None for g in (
                        [y for y in (A.score(l, fail, ok) for l in fn(r)) if y is not None] for r in ss)) if x is not None]
                    return (sum(v) / len(v), len(v)) if v else (None, 0)
                o, n_o = rate(combined)
                al, n_a = rate(lambda r: [r["alt"][j] for j in A.JUDGES])
                judged = sum(1 for r in rows if r["system"] == sy and r["question"] in qs and not r["uncited"]
                             and any(A.score(l, fail, ok) is not None for l in combined(r)))
                share = judged / base[sy]["countable"] if base[sy]["countable"] else 0
                d = (al - o) if o is not None and al is not None else 0.0
                shift[sy] = {"subsample_n": n_o, "original": None if o is None else round(o, 4),
                             "alternative": None if al is None else round(al, 4), "shift_on_judged": round(d, 4),
                             "judged_share_of_countable": round(share, 4), "applied_shift": round(d * share, 4)}
            tests = {}
            for m, sy in SEVEN:
                if m != measure:
                    continue
                d0 = base[sy]["WHU_vs"]["difference_whu_minus"]
                d1 = (base["WHU"]["rate"] + shift["WHU"]["applied_shift"]) - (base[sy]["rate"] + shift[sy]["applied_shift"])
                tests[sy] = {"difference": d0, "shifted_difference": round(d1, 4), "sign_changes": (d1 > 0) != (d0 > 0)}
            out[measure] = {"shift": shift, "seven": tests}
        out["changed"] = [(m, sy) for m in out for sy, t in (out[m]["seven"].items() if isinstance(out[m], dict) and "seven" in out[m] else []) if t["sign_changes"]]
        out["conclusion_changes"] = bool(out["changed"])
        res["sets"][set_name] = out
    for k in [k for k in res if k.startswith("_rows_")]:
        res.pop(k)
    res["instability_flags"] = [k for k, v in res["flips"].items() if v["instability_flag_over_15pct"]]
    res["conclusion_changes"] = res["sets"]["all_four"]["conclusion_changes"]
    return write("check10", res)


# ---------------------------------------------------------------------------------------------------------------
# check 4: second keys (plan §4)
# ---------------------------------------------------------------------------------------------------------------

def k2_rows(run: Path) -> list[dict]:
    spec = json.loads((run / "items.json").read_text())
    km = json.loads((run / "key_map.json").read_text())
    valid = A.M2_PASS | A.M2_FAIL
    rows = []
    for it in spec["items"]:
        raw = {}
        for j in ("claude", "openai", "google"):
            f = run / "replies" / j / (it["item"] + ".json")
            if f.exists():
                raw[j] = json.loads(f.read_text())
        labels = A.per_judge_labels({j: raw[j] for j in A.JUDGES if j in raw}, valid)
        g = (raw.get("google") or {}).get("label")
        labels["google"] = g if g in valid else None
        rows.append({"item": it["item"], **km[it["answer"]], "conclusion": it["conclusion"], "raw": raw,
                     "labels": labels, "uncited": False, "repeat": {}})
    return rows


def norm_offsets(text: str, quote: str) -> tuple[int, int] | None:
    h, q = CL_norm(text), CL_norm(quote)
    i = h.find(q)
    return (i, i + len(q)) if q and i >= 0 else None


def CL_norm(s: str) -> str:
    import judge_m1 as J1
    return J1.norm(s)


def matching(q: str) -> dict:
    """Second-key conclusion -> matched first-key conclusion (quoted passages overlap >= half the shorter quote)."""
    sys.path.insert(0, str(STUDY / "scripts"))
    k1dir = (PRIV / "keys" / "quarterly" / "round1" / q) if q.startswith("WHU-Q1") else (PRIV / "keys" / q)
    k1 = json.loads((k1dir / "key.json").read_text())
    k2 = json.loads((PRIV / "keys2" / q / "key.json").read_text())
    full = "\n\n".join(f.read_text(encoding="utf-8") for f in sorted(k1dir.joinpath("source").rglob("*.txt")))
    def spans(c):
        return [x for x in (norm_offsets(full, y["text"]) for y in c.get("quotes") or []) if x]
    out = {}
    for c2 in k2["conclusions"]:
        best = None
        for c1 in k1["conclusions"]:
            for a in spans(c2):
                for b in spans(c1):
                    ov = max(0, min(a[1], b[1]) - max(a[0], b[0]))
                    if ov >= 0.5 * min(a[1] - a[0], b[1] - b[0]):
                        best = c1["n"]
        out["%s-K2C%d" % (q, c2["n"])] = best
    return out


def check4() -> dict:
    c4 = PRIV / "validity" / "check4"
    r1 = k2_rows(c4 / "m2_round1")
    st = k2_rows(c4 / "m2_study")
    match = {}
    for q in QS + ["WHU-S01", "WHU-S02"]:
        match.update(matching(q))
    _, m2_first = AR.round1_rows()
    q4_run = (PRIV / "keys2" / "WHU-Q1-04" / "key.json").exists()
    q4_not_run = PRIV / "keys2" / "WHU-Q1-04" / "not_run.json"
    res = {"conclusions": {"total": len(match), "matched": sum(v is not None for v in match.values()),
                           "by_conclusion": match},
           "WHU_Q1_04": ("FLAG: read in one ~832k-token call, far beyond any read length tested in this study; lower "
                         "confidence than the other keys (advisor, 2026-10-30)") if q4_run else
                        ("NOT RUN: " + json.loads(q4_not_run.read_text())["reason"]) if q4_not_run.exists() else
                        "no second key", "sets": {}}
    measures = ("M2_overstates", "M2_understates_omits", "M2_overstates_contradicts")
    qsets = {"with_Q1_04": QS, "without_Q1_04": [q for q in QS if q != "WHU-Q1-04"]} if q4_run else \
        {"without_Q1_04": [q for q in QS if q != "WHU-Q1-04"]}
    for qname, qs in qsets.items():
        for label, rows_fn in (("all_conclusions", lambda rs: rs),
                               ("unmatched_only", lambda rs: [r for r in rs if match.get(r["conclusion"]) is None])):
            rows = [r for r in rows_fn(r1) if r["question"] in qs]
            out = {}
            for measure in measures + ("M2_any_failure",):
                v = {name: view_of(scores(rows, measure, fn), qs) for name, fn in (
                    ("two_judge", combined), ("claude", lambda r: [r["labels"]["claude"]]),
                    ("openai", lambda r: [r["labels"]["openai"]]), ("google", lambda r: [r["labels"]["google"]]))}
                f1 = view_of(scores(m2_first, measure, combined), qs)
                out[measure] = {"second_key": {s: {"rate": v["two_judge"][s]["rate"], "n": v["two_judge"][s]["countable"]}
                                               for s in SYSTEMS},
                                "per_judge_WHU": {j: v[j]["WHU"]["rate"] for j in ("claude", "openai", "google")},
                                "first_key_WHU": f1["WHU"]["rate"],
                                "vs_tools": {s: {"first_key_difference": f1[s]["WHU_vs"]["difference_whu_minus"],
                                                 "first_key_ci95": f1[s]["WHU_vs"]["difference_ci95"],
                                                 "second_key_difference": v["two_judge"][s]["WHU_vs"]["difference_whu_minus"],
                                                 "second_key_ci95": v["two_judge"][s]["WHU_vs"]["difference_ci95"]}
                                             for s in SYSTEMS[1:]}}
            t = []
            for measure in ("M2_overstates_contradicts", "M2_understates_omits"):
                a, b = out[measure]["first_key_WHU"], out[measure]["second_key"]["WHU"]["rate"]
                if a is not None and b is not None and b - a >= 0.10:
                    t.append("WHU %s rises %.3f -> %.3f" % (measure, a, b))
            for m, sy in SEVEN:
                if m.startswith("M2") and m in out:
                    x = out[m]["vs_tools"][sy]
                    ci0, ci = x["first_key_ci95"], x["second_key_ci95"]
                    excl0 = ci0[0] is not None and not (ci0[0] <= 0 <= ci0[1])
                    if excl0 and (ci[0] is None or ci[0] <= 0 <= ci[1]):
                        t.append("%s vs %s: interval %s includes zero" % (m, sy, ci))
            for m in measures:
                for sy, x in out[m]["vs_tools"].items():
                    d0, d1 = x["first_key_difference"], x["second_key_difference"]
                    if d0 is not None and d1 is not None and ((d0 <= 0 and d1 > 0.05) or (d0 >= 0 and d1 < -0.05)):
                        t.append("%s vs %s reverses: %.3f -> %.3f" % (m, sy, d0, d1))
            out["changed"] = t
            res["sets"]["round1_%s_%s" % (qname, label)] = out
    # study S01-S02: WHU's second-key rates against the study's own (first-key) rates on the same two questions
    keep = A.PRIVATE, A.QUESTIONS, A.TAGS
    sm = {}
    try:
        for base in (PRIV / "scoring", PRIV / "scoring" / "perplexity"):
            A.PRIVATE, A.QUESTIONS, A.TAGS = base, ["WHU-S01", "WHU-S02"], ("", "_ext")
            sm[str(base)] = A.items_m2()
    finally:
        A.PRIVATE, A.QUESTIONS, A.TAGS = keep
    study_first = [r for rs in sm.values() for r in rs]
    stud = {}
    for measure in ("M2_overstates_contradicts", "M2_understates_omits"):
        _, fail, ok = AR.MEASURES[measure]
        def rate(rows, sy):
            v = [x for x in (sum(g) / len(g) if g else None for g in (
                [y for y in (A.score(l, fail, ok) for l in [r["labels"]["claude"], r["labels"]["openai"]]) if y is not None]
                for r in rows if r["system"] == sy)) if x is not None]
            return (round(sum(v) / len(v), 4) if v else None, len(v))
        stud[measure] = {sy: {"first_key": rate(study_first, sy), "second_key": rate(st, sy)} for sy in SYSTEMS}
    t = ["study WHU %s rises %s -> %s" % (m, x["WHU"]["first_key"][0], x["WHU"]["second_key"][0])
         for m, x in stud.items() if x["WHU"]["first_key"][0] is not None and x["WHU"]["second_key"][0] is not None
         and x["WHU"]["second_key"][0] - x["WHU"]["first_key"][0] >= 0.10]
    res["sets"]["study_S01_S02"] = {"rates_two_judge": stud, "changed": t,
                                    "note": "two questions: point rates only, no interval"}
    main_set = "round1_with_Q1_04_all_conclusions" if q4_run else "round1_without_Q1_04_all_conclusions"
    res["conclusion_changes"] = bool(res["sets"][main_set]["changed"] or t)
    res["conclusion_changes_without_Q1_04"] = bool(res["sets"]["round1_without_Q1_04_all_conclusions"]["changed"] or t)
    return write("check4", res)


# ---------------------------------------------------------------------------------------------------------------
# check 5: the human probability sample, judge error correction (plan §5)
# ---------------------------------------------------------------------------------------------------------------

def _corrected(items, frame_rows, judge, fail) -> dict:
    """One judge, one system: Se/Sp from the labelled items (weights N_h/n_h, Jeffreys +0.5), the corrected judged
    failure rate, and the direct stratified human estimate."""
    w = {}
    for it in items:
        w.setdefault(it["stratum"], []).append(it)
    N = {}
    for r in frame_rows:
        N[r["stratum"]] = N.get(r["stratum"], 0) + 1
    tp = fn = tn = fp = 0.0
    direct_num = direct_den = 0.0
    for h, its in w.items():
        wt = N.get(h, 0) / len(its)
        for it in its:
            hf, jf = it["human_fail"], it[judge] in fail
            tp += wt * (hf and jf); fn += wt * (hf and not jf); tn += wt * ((not hf) and not jf); fp += wt * ((not hf) and jf)
        direct_num += N.get(h, 0) * sum(i["human_fail"] for i in its) / len(its)
        direct_den += N.get(h, 0)
    se = (tp + 0.5) / (tp + fn + 1.0)
    sp = (tn + 0.5) / (tn + fp + 1.0)
    obs = sum(r[judge] in fail for r in frame_rows) / len(frame_rows) if frame_rows else None
    direct = direct_num / direct_den if direct_den else None
    if obs is None:
        return {"se": se, "sp": sp, "observed": None, "corrected": None, "direct": direct, "identifiable": False}
    j = se + sp - 1
    ok = j >= 0.5
    theta = min(1.0, max(0.0, (obs + sp - 1) / j)) if ok else direct
    return {"se": round(se, 4), "sp": round(sp, 4), "observed": round(obs, 4),
            "corrected": None if theta is None else round(theta, 4), "direct": None if direct is None else round(direct, 4),
            "identifiable": ok}


def check5(boot: int = 10_000) -> dict:
    import random as _r
    smp = json.loads((PRIV / "validity" / "check5" / "sample.json").read_text())
    lab = {}
    lf = PRIV / "validity" / "check5" / "fred.jsonl"
    for line in lf.read_text().splitlines() if lf.exists() else []:
        if line.strip():
            x = json.loads(line)
            lab[x["n"]] = x
    m1, m2 = AR.round1_rows()
    rows = {"M1": m1, "M2": m2}
    fails = {"M1": {"Not supported"}, "M2": {"Overstates", "Understates", "Omits", "Contradicts"}}
    jfail = {"M1": A.M1_FAIL, "M2": A.M2_FAIL}
    labelled = []
    cant = 0
    for it in smp["items"]:
        x = lab.get(it["n"])
        if not x:
            continue
        if x["label"] == "Can't tell":
            cant += 1
            continue
        labelled.append({**it, "human": x["label"], "human_fail": x["label"] in fails[it["measure"]],
                         "think_i_know": x.get("think_i_know")})
    res = {"labelled": len(labelled), "cant_tell": cant, "of": len(smp["items"]),
           "by": "Fred (built WHU; his labels reported as his)", "systems": {}}
    if not labelled:
        res["note"] = "no labels yet"
        return write("check5", res)
    # the frame each item came from (both judges' own labels countable), with its stratum
    frame = {}
    for m in ("M1", "M2"):
        valid = (A.M1_PASS | A.M1_FAIL) if m == "M1" else (A.M2_PASS | A.M2_FAIL)
        for r in rows[m]:
            l = {j: (r["raw"].get(j) or {}).get("label") for j in A.JUDGES}
            if not r["uncited"] and all(l[j] in valid for j in A.JUDGES):
                frame.setdefault((m, r["system"]), []).append(
                    {"item": r["item"], "question": r["question"], "claude": l["claude"], "openai": l["openai"],
                     "stratum": "agree" if l["claude"] == l["openai"] else "disagree"})
    def system_rates(m, sy, items, fr):
        out = {}
        for j in A.JUDGES:
            out[j] = _corrected([i for i in items if i["system"] == sy and i["measure"] == m], fr, j, jfail[m])
        cs = [out[j]["corrected"] for j in A.JUDGES if out[j]["corrected"] is not None]
        out["two_judge_corrected_judged"] = sum(cs) / len(cs) if cs else None
        return out
    m1_unc = {}
    m1_cnt = {}
    for r in m1:
        m1_unc[r["system"]] = m1_unc.get(r["system"], 0) + r["uncited"]
    for sy in SYSTEMS:
        res["systems"][sy] = {}
        for m in ("M1", "M2"):
            fr = frame.get((m, sy), [])
            rr = system_rates(m, sy, labelled, fr)
            if m == "M1":
                unc = m1_unc.get(sy, 0)
                cnt = unc + len(fr)
                t = rr["two_judge_corrected_judged"]
                # no judged items (ChatGPT: all UNCITED, by code) -> the rate is UNCITED / countable, no judge error
                rr["corrected_M1_rate"] = None if not cnt else round(unc / cnt, 4) if not fr else \
                    None if t is None else round((unc + t * len(fr)) / cnt, 4)
                rr["countable"] = cnt
            res["systems"][sy][m] = rr
    # bootstrap: questions with replacement, then labelled items within stratum
    rng = _r.Random("%d/check5/boot" % SEED)
    qs = list(QS)
    diffs = {sy: [] for sy in SYSTEMS[1:]}
    for _ in range(boot):
        qb = [rng.choice(qs) for _ in qs]
        lab_b, fr_b = [], {}
        for q in qb:
            for key, fr in frame.items():
                fr_b.setdefault(key, []).extend([x for x in fr if x["question"] == q])
            byh = {}
            for i in labelled:
                if i["question"] == q:
                    byh.setdefault((i["measure"], i["system"], i["stratum"]), []).append(i)
            for its in byh.values():
                lab_b += [rng.choice(its) for _ in its]
        def m1rate(sy):
            fr = fr_b.get(("M1", sy), [])
            unc = sum(1 for q in qb for r in m1 if r["system"] == sy and r["question"] == q and r["uncited"])
            t = system_rates("M1", sy, lab_b, fr)["two_judge_corrected_judged"] if fr else None
            cnt = unc + len(fr)
            if not cnt:
                return None
            return unc / cnt if not fr else None if t is None else (unc + t * len(fr)) / cnt
        w = m1rate("WHU")
        for sy in SYSTEMS[1:]:
            o = m1rate(sy)
            if w is not None and o is not None:
                diffs[sy].append(w - o)
    out = {}
    for sy, d in diffs.items():
        d.sort()
        ci = [round(d[int(0.025 * (len(d) - 1))], 4), round(d[int(0.975 * (len(d) - 1))], 4)] if d else [None, None]
        w, o = res["systems"]["WHU"]["M1"]["corrected_M1_rate"], res["systems"][sy]["M1"]["corrected_M1_rate"]
        out[sy] = {"corrected_difference": None if w is None or o is None else round(w - o, 4), "ci95": ci, "resamples": len(d)}
    res["M1_corrected_vs_whu"] = out
    first = json.loads((STUDY / "quarterly" / "round1_scoring" / "round1_ai_only.json").read_text())
    base = first["A_whu_against_each_tool"]["all_four"]["M1_failure"]["combined"]
    flags = []
    for m, sy in SEVEN:
        if m != "M1_failure":
            continue
        x, d0 = out[sy], base[sy]["WHU_vs"]["difference_whu_minus"]
        if x["ci95"][0] is None or x["ci95"][0] <= 0 <= x["ci95"][1] or (x["corrected_difference"] is not None and x["corrected_difference"] > 0.5 * d0):
            flags.append((m, sy))
    res["changed"] = flags
    res["M2_note"] = "M2 is diagnostic only (1 agreed item drawn per system): per-judge Se/Sp and corrected rates above"
    res["conclusion_changes"] = bool(flags)
    return write("check5", res)


# ---------------------------------------------------------------------------------------------------------------
# check 5b: the mechanical figure check (plan §5b, amendment of 2026-10-30)
# ---------------------------------------------------------------------------------------------------------------

LABEL_5B = "mechanical figure check, figure claims only; not a human review. No human has checked the judgements."


def wilson(k: int, n: int) -> list:
    if not n:
        return [None, None]
    z, p = 1.959964, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def _fig_rates(rows, cls, judge) -> dict:
    """One judge over one system's figure items: agreement, Se, Sp on decidable items; corrected figure-claim rate."""
    ok_set = A.M1_PASS | A.M1_FAIL
    judged = [r for r in rows if not r["uncited"] and r["labels"].get(judge) in ok_set]
    unc = sum(1 for r in rows if r["uncited"])
    dec = [r for r in judged if cls[r["item"]]["class"] in ("FIGURE_ABSENT", "FIGURE_NEAR")]
    pos = [r for r in dec if cls[r["item"]]["class"] == "FIGURE_ABSENT"]
    neg = [r for r in dec if cls[r["item"]]["class"] == "FIGURE_NEAR"]
    tp = sum(r["labels"][judge] in A.M1_FAIL for r in pos)
    tn = sum(r["labels"][judge] in A.M1_PASS for r in neg)
    se, sp = (tp + 0.5) / (len(pos) + 1.0), (tn + 0.5) / (len(neg) + 1.0)
    obs = sum(r["labels"][judge] in A.M1_FAIL for r in judged) / len(judged) if judged else None
    ref = len(pos) / len(dec) if dec else None
    jy = se + sp - 1
    if obs is None:
        theta, how = None, "no judged figure item"
    elif jy >= 0.5:
        theta, how = min(1.0, max(0.0, (obs + sp - 1) / jy)), "corrected (Se + Sp - 1 >= 0.5)"
    else:
        theta, how = ref, "unidentifiable (Se + Sp - 1 < 0.5): the reference share on decidable items"
    cnt = unc + len(judged)
    return {"uncited": unc, "judged": len(judged), "decidable": len(dec), "reference_absent": len(pos),
            "reference_near": len(neg), "agree": tp + tn, "agreement": round((tp + tn) / len(dec), 4) if dec else None,
            "sensitivity": {"k": tp, "n": len(pos), "raw": round(tp / len(pos), 4) if pos else None, "ci95": wilson(tp, len(pos))},
            "specificity": {"k": tn, "n": len(neg), "raw": round(tn / len(neg), 4) if neg else None, "ci95": wilson(tn, len(neg))},
            "se_smoothed": round(se, 4), "sp_smoothed": round(sp, 4), "observed_judged_failure": None if obs is None else round(obs, 4),
            "theta": None if theta is None else round(theta, 4), "theta_how": how,
            "corrected_figure_rate": None if not cnt else round(unc / cnt, 4) if not judged else
            None if theta is None else round((unc + theta * len(judged)) / cnt, 4),
            "ai_only_figure_rate": None if not cnt else round((unc + (obs or 0) * len(judged)) / cnt, 4)}


def check5b(boot: int = 10_000) -> dict:
    import random as _r
    cls = json.loads((HERE / "results" / "check5b_classes.json").read_text())["items"]
    m1, _ = AR.round1_rows()
    has_google = google_labels(m1, "M1") > 0
    judges = ["claude", "openai"] + (["google"] if has_google else [])
    fig = [r for r in m1 if r["item"] in cls]
    res = {"label": LABEL_5B, "judges": judges, "figure_items": len(fig),
           "classes": dict(Counter(v["class"] or v["why"] for v in cls.values())), "systems": {}}
    for sy in SYSTEMS:
        rs = [r for r in fig if r["system"] == sy]
        res["systems"][sy] = {j: _fig_rates(rs, cls, j) for j in judges}
        two = [res["systems"][sy][j]["corrected_figure_rate"] for j in ("claude", "openai")]
        res["systems"][sy]["two_judge_corrected_figure_rate"] = None if None in two else round(sum(two) / 2, 4)
        ai = [res["systems"][sy][j]["ai_only_figure_rate"] for j in ("claude", "openai")]
        res["systems"][sy]["two_judge_ai_only_figure_rate"] = None if None in ai else round(sum(ai) / 2, 4)
    rng = _r.Random("%d/check5b/boot" % SEED)
    diffs = {sy: [] for sy in SYSTEMS[1:]}
    for _ in range(boot):
        qb = [rng.choice(QS) for _ in QS]
        sample = []
        for q in qb:
            pool = [r for r in fig if r["question"] == q]
            sample += [rng.choice(pool) for _ in pool] if pool else []
        def rate(sy):
            rs = [r for r in sample if r["system"] == sy]
            v = [_fig_rates(rs, cls, j)["corrected_figure_rate"] for j in ("claude", "openai")]
            return None if None in v else sum(v) / 2
        w = rate("WHU")
        for sy in SYSTEMS[1:]:
            o = rate(sy)
            if w is not None and o is not None:
                diffs[sy].append(w - o)
    tests = {}
    for m, sy in SEVEN:
        if m != "M1_failure":
            continue
        d = sorted(diffs[sy])
        ci = [round(d[int(0.025 * (len(d) - 1))], 4), round(d[int(0.975 * (len(d) - 1))], 4)] if d else [None, None]
        w, o = res["systems"]["WHU"]["two_judge_corrected_figure_rate"], res["systems"][sy]["two_judge_corrected_figure_rate"]
        wa, oa = res["systems"]["WHU"]["two_judge_ai_only_figure_rate"], res["systems"][sy]["two_judge_ai_only_figure_rate"]
        dc = None if w is None or o is None else round(w - o, 4)
        da = None if wa is None or oa is None else round(wa - oa, 4)
        tests[sy] = {"corrected_difference": dc, "ci95": ci, "resamples": len(d), "ai_only_figure_difference": da,
                     "n_whu": res["systems"]["WHU"]["claude"]["uncited"] + res["systems"]["WHU"]["claude"]["judged"],
                     "n_tool": res["systems"][sy]["claude"]["uncited"] + res["systems"][sy]["claude"]["judged"],
                     "ci_includes_zero": ci[0] is None or ci[0] <= 0 <= ci[1],
                     "lead_halves": dc is not None and da is not None and da < 0 and dc > 0.5 * da}
    res["M1_figure_comparisons"] = tests
    res["rule_would_have_flagged"] = [sy for sy, t in tests.items() if t["ci_includes_zero"] or t["lead_halves"]]
    res["status"] = WITHDRAWN_5B
    res["description"] = DESCRIPTION_5B
    res["conclusion_changes"] = None          # withdrawn: the conclusion-change rule does not apply
    return write("check5b", res)


WITHDRAWN_5B = ("WITHDRAWN as a correction instrument; decides nothing (advisor ruling 2026-10-30, the advisor's error, "
                "next_phase/deviations.md). FIGURE_NEAR was used as a 'supported' reference, but the judges' fails on "
                "those items are framing labels (Overstates, Wrong source, Absent) a figure check cannot see, so the "
                "reference was invalid by construction; with 1 FIGURE_ABSENT item in 177, sensitivity cannot be "
                "estimated and the correction degenerates. The figures below are kept as computed, not as findings.")
LINE_5B = "113 of 177 figure claims (64%) carry no citation."   # advisor, 2026-10-30
DESCRIPTION_5B = ("Mechanical figure check; not a human review; not a correction. %s Of 177 round-1 M1 items with a figure, " % LINE_5B +
                  "113 are uncited and 1 has no cited source held. Of the other 63, every claimed figure appears in the "
                  "cited source for 57, some for 5, none for 1. On the 52 items where each figure appears near the "
                  "sentence's content words, the two judges' 20 fail labels are Absent 8, Overstates 7, Wrong source 4, "
                  "Contradicted 1: failures of what the sentence says beyond the figure, not invented numbers. "
                  "No human has checked the judgements.")


# ---------------------------------------------------------------------------------------------------------------
# check 3: identifiability (plan §3)
# ---------------------------------------------------------------------------------------------------------------

def _guesses(raw: str, array: bool):
    m = re.search(r"\[.*\]" if array else r"\{.*\}", raw or "", re.S)
    try:
        return json.loads(m.group(0)) if m else ([] if array else {})
    except json.JSONDecodeError:
        return [] if array else {}


def check3() -> dict:
    """Confusion table per guesser (sentences and whole answers), each system's rate against 1/5, and, for WHU's
    sentences, WHU's M1 failure rate (the guesser's own judge labels) on identified vs not identified items."""
    ID = _load("identify_v", HERE / "identify.py")
    smp = json.loads((ID.OUT / "sample.json").read_text(encoding="utf-8"))
    ans = ID.answers()
    m1, _ = AR.round1_rows()
    if any((AR.RUN / "m1" / "replies" / "google").glob("*.json")):
        google_labels(m1, "M1")
    by_item = {r["item"]: r for r in m1}
    _, fail, ok = AR.MEASURES["M1_failure"]
    res = {"chance": 0.2, "guessers": {}}
    for who in ID.GUESSERS:
        d = ID.OUT / "replies" / who
        g = {}
        for f in sorted(d.glob("batch*.json")):
            for x in _guesses(json.loads(f.read_text())["raw"], True):
                g[x.get("id")] = x
        g_ans = {a["answer"]: _guesses(json.loads((d / ("answer-%s.json" % a["answer"])).read_text())["raw"], False)
                 for a in ans}
        sent = ID.tally(smp, g)
        whole = ID.tally([{"id": a["answer"], "system": a["system"]} for a in ans], g_ans)
        for t in (sent, whole):
            t.pop("whu_above_half", None), t.pop("gate", None), t.pop("note", None)
        whu = [r for r in smp if r["system"] == "WHU"]
        k = sum(g.get(r["id"], {}).get("guess") == "WHU" for r in whu)
        judge = {"claude": "claude", "openai": "openai", "google": "google"}[who]
        split = {}
        for name, keep in (("identified", True), ("not_identified", False)):
            sc = [A.score(by_item[r["item"]]["labels"].get(judge), fail, ok) for r in whu
                  if (g.get(r["id"], {}).get("guess") == "WHU") == keep]
            sc = [x for x in sc if x is not None]
            split[name] = {"n_items": sum((g.get(r["id"], {}).get("guess") == "WHU") == keep for r in whu),
                           "countable": len(sc), "failure_rate": round(sum(sc) / len(sc), 4) if sc else None}
        a, b = split["identified"]["failure_rate"], split["not_identified"]["failure_rate"]
        gap = round(a - b, 4) if a is not None and b is not None else None
        first = k >= 9 and ID.binom_tail(k, len(whu)) <= 0.01
        res["guessers"][who] = {
            "sentences": sent, "whole_answers": whole,
            "whu_identified": "%d/%d" % (k, len(whu)), "whu_p_by_chance": float("%.3g" % ID.binom_tail(k, len(whu))),
            "whu_m1_failure_by_identification (judge %s's own labels; descriptive, n small)" % judge: split,
            "gap_points": None if gap is None else round(100 * gap, 1),
            "test": {"identified_at_least_9_of_20_p_le_0.01": first,
                     "failure_gap_at_least_15_points": gap is not None and abs(gap) >= 0.15,
                     "goes_to_advisor": first and gap is not None and abs(gap) >= 0.15}}
    res["conclusion_changes"] = "not automatic: goes to the advisor" if any(
        v["test"]["goes_to_advisor"] for v in res["guessers"].values()) else False
    return write("check3", res)


# ---------------------------------------------------------------------------------------------------------------
# check 3b: recognition bias (advisor ruling 2026-10-31, after check 3), $0, round-1 labels only
# ---------------------------------------------------------------------------------------------------------------
# RULE, written before computing:
#   Items: round-1 M1 items that were judged (cited; uncited items carry the same UNCITED label for every judge
#   and say nothing about a judge). Each judge's own first-read label, scored by M1_failure (fail 1, pass 0,
#   anything else not countable).
#   d(s) = OpenAI's M1 failure rate on system s minus Claude's (pooled over the questions in the set).
#   Contrast for WHU against each other system o: c(o) = d(WHU) - d(o). A negative c means OpenAI (the judge that
#   recognised WHU, 18/20 in check 3) is more favourable to WHU, relative to Claude (1/20), than to o.
#   Primary contrast: c(others) = d(WHU) - mean of d(o) over the four other systems.
#   95% CI: 10,000 bootstrap resamples of questions with replacement (random.Random("%d/check3b/boot" % SEED)).
#   BIAS INDICATED if c(others) <= -0.10 and its 95% CI excludes zero (upper bound < 0). Pairwise c(o) are
#   reported with their CIs; they decide nothing. With four questions the bootstrap has few distinct resamples;
#   reported as is. Repeated with Google in place of OpenAI once check 1's labels exist (Google named WHU 5/20).

def check3b(boot: int = 10_000) -> dict:
    import random as _r
    m1, _ = AR.round1_rows()
    have_google = any((AR.RUN / "m1" / "replies" / "google").glob("*.json"))
    if have_google:
        google_labels(m1, "M1")
    _, fail, ok = AR.MEASURES["M1_failure"]
    rows = [r for r in m1 if not r["uncited"]]

    def counts(judge):
        c = {}
        for r in rows:
            x = A.score(r["labels"].get(judge), fail, ok)
            if x is not None:
                f, n = c.get((r["question"], r["system"]), (0, 0))
                c[(r["question"], r["system"])] = (f + x, n + 1)
        return c

    def diffs(cj, cc, qs):
        out = {}
        for s in SYSTEMS:
            fj = sum(cj.get((q, s), (0, 0))[0] for q in qs); nj = sum(cj.get((q, s), (0, 0))[1] for q in qs)
            fc = sum(cc.get((q, s), (0, 0))[0] for q in qs); nc = sum(cc.get((q, s), (0, 0))[1] for q in qs)
            out[s] = (fj / nj - fc / nc) if nj and nc else None
        return out

    def contrasts(d):
        oth = [s for s in SYSTEMS if s != "WHU" and d[s] is not None]
        if d["WHU"] is None or not oth:
            return None
        c = {o: d["WHU"] - d[o] for o in oth}
        c["others"] = d["WHU"] - sum(d[o] for o in oth) / len(oth)
        return c

    cc = counts("claude")
    res = {"rule": "validity_analysis.py check3b comment block", "items": "judged (cited) round-1 M1 items",
           "sets": {}}
    for jname in ("openai",) + (("google",) if have_google else ()):
        cj = counts(jname)
        for set_name, qs in SETS.items():
            d = diffs(cj, cc, qs)
            c = contrasts(d)
            rng = _r.Random("%d/check3b/boot/%s/%s" % (SEED, jname, set_name))
            bs = {k: [] for k in (c or {})}
            for _ in range(boot):
                x = contrasts(diffs(cj, cc, [rng.choice(qs) for _q in qs]))
                if x:
                    for k in bs:
                        if k in x:
                            bs[k].append(x[k])

            def ci(v):
                v = sorted(v)
                return [round(v[int(0.025 * len(v))], 4), round(v[int(0.975 * len(v)) - 1], 4)] if v else [None, None]
            n = {s: (sum(cj.get((q, s), (0, 0))[1] for q in qs), sum(cc.get((q, s), (0, 0))[1] for q in qs))
                 for s in SYSTEMS}
            prim = c["others"] if c else None
            pci = ci(bs.get("others", []))
            res["sets"]["%s_vs_claude/%s" % (jname, set_name)] = {
                "difference_judge_minus_claude": {s: None if v is None else round(v, 4) for s, v in d.items()},
                "countable_judge_claude": n,
                "contrast_whu_minus_other": {k: {"value": round(v, 4), "ci95": ci(bs[k])} for k, v in (c or {}).items()},
                "bias_indicated": prim is not None and prim <= -0.10 and pci[1] is not None and pci[1] < 0}
    if not have_google:
        res["google"] = "not run: check 1's labels do not exist yet"
    return write("check3b", res)


# ---------------------------------------------------------------------------------------------------------------
# check 3c: sensitivity to the blinding leak (advisor ruling 2026-10-31), $0
# ---------------------------------------------------------------------------------------------------------------
# RULE, written before computing: the seven round-1 comparisons, as scored, in both sets, recomputed with the WHU M1
# items whose sentence or context carries WHU page furniture (FURNITURE below, the phrases searched for in the leak
# report, deviations.md 2026-10-31) removed. M2 has no exclusion: the M1 exclusion does not touch M2, and every WHU
# M2 answer carries the furniture (listed). CONCLUSION CHANGES if any comparison reverses sign or WHU's lead falls
# under half its as-scored size (changes()["reverses"] or ["lead_under_half"]); ["ci_includes_zero"] is reported
# and decides nothing here.
FURNITURE = [r"judged not material", r"judged outside this question", r"outside this question",
             r"findings in our sources", r"we did not search", r"we did not read", r"this answer draws on"]


def furniture_in(text: str) -> list[str]:
    return [p for p in FURNITURE if re.search(p, text or "", re.I)]


def furniture_items() -> list[str]:
    run = AR.RUN / "m1"
    km = json.loads((run / "key_map.json").read_text(encoding="utf-8"))
    rows = json.loads((run / "items.json").read_text(encoding="utf-8")) + \
        json.loads((run / "uncited.json").read_text(encoding="utf-8"))
    return sorted(r["item"] for r in rows if km[r["item"]]["system"] == "WHU"
                  and furniture_in(r["claim"] + " " + (r.get("context") or "")))


def check3c() -> dict:
    m1, m2 = AR.round1_rows()
    drop = set(furniture_items())
    km2 = json.loads((AR.RUN / "m2" / "key_map.json").read_text(encoding="utf-8"))
    m2_files = sorted(a for a, k in km2.items() if k["system"] == "WHU"
                      and furniture_in((AR.RUN / "m2" / "answers" / (a + ".txt")).read_text(encoding="utf-8")))
    kept = [r for r in m1 if r["item"] not in drop]
    res = {"rule": "validity_analysis.py check3c comment block", "furniture": FURNITURE,
           "excluded_m1_items": sorted(drop), "n_excluded": len(drop),
           "whu_m2_answers_with_furniture": m2_files,
           "whu_m2_answers": sorted(a for a, k in km2.items() if k["system"] == "WHU"), "sets": {}}
    for set_name, qs in SETS.items():
        out = {}
        for measure in ("M1_failure", "M2_overstates", "M2_understates_omits"):
            rows = m1 if measure.startswith("M1") else m2
            base = seven(view_of(scores(rows, measure, combined), qs), measure)
            if measure.startswith("M1"):
                alt = seven(view_of(scores(kept, measure, combined), qs), measure)
                out[measure] = {s: {"as_scored": base[s], "excluding_furniture": alt[s],
                                    "test": changes(base[s], alt[s])} for s in base}
            else:
                out[measure] = {s: {"as_scored": base[s], "excluding_furniture": "no M2 exclusion (see rule)"}
                                for s in base}
        out["changed"] = [(m, s) for m in out for s, x in out[m].items()
                          if isinstance(x.get("test"), dict) and (x["test"]["reverses"] or x["test"]["lead_under_half"])]
        out["conclusion_changes"] = bool(out["changed"])
        res["sets"][set_name] = out
    res["conclusion_changes"] = any(v["conclusion_changes"] for v in res["sets"].values())
    return write("check3c", res)


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"check9": check9, "check6": check6, "check1": check1, "check2": check2, "check10": check10, "check3": check3, "check3b": check3b, "check3c": check3c,
          "check4": check4, "check5": check5,
          "check5b": check5b}.get(which)
    if not fn:
        print(__doc__)
        return 2
    r = fn()
    print(json.dumps({k: v for k, v in r.items() if k not in ("non_claim_items",)}, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
