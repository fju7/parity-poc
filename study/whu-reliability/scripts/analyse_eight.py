#!/usr/bin/env python3
"""The analysis on all eight questions (protocol, extension rule), AI judges only.

    analyse_eight.py

The extension rule: "four more questions are drawn the same way, one per
frame, and the analysis is rerun on all eight", used at most once. This runs
analyse.py's rules (labels, exclusions, scores, bootstrap over whole
questions with the freeze seed, decision rule) unchanged, through its own
functions, on three question sets: WHU-S01 to S04 (Stage 1), WHU-S05 to S08,
and all eight. The all-eight two-judge result is the extension's outcome; the
rule is not applied again. For each set:

  - two-judge views (combined, each judge, agreed only), counts, judge
    agreement and kappa, refusals, second reads, label counts, directions:
    analyse.build();
  - cross-company (spec (b)): cross_company.py's assignment and its
    abstract-only correction;
  - quote-checked (spec (a), WHU's items only, Option B): quotecheck_m1.py's
    quote check on the re-judge replies (S01-S04: replies/, S05-S08:
    replies_ext/), WHU quote-checked against Claude Research as labelled,
    two-judge combined and cross-company (OpenAI judge);
  - sensitivity (advisor's ruling, 2026-10-27): all excluded WHU items
    counted as failures (every WHU cited item without a countable label:
    unreachable, abstract-only, too long to send, or no usable reply); and
    WHU-S05's 10 items citing its two Lancet DOIs (not free to read) counted
    as failures, a subset of the first;
  - citation reachability per system (prepare_scoring.reachability).

ChatGPT performed no web search on WHU-S05 to S08 (deviations 2026-10-26): its
figures are given for all eight and for S01-S04 only, so labelled; it is
outside H1 and H2. Replies: Stage 1 in replies/, the extension in
replies_ext/ (deviations 2026-10-27). Writes results/eight_ai_only.json,
counts only; the human-review list for all eight (ids and reasons) goes to
PRIVATE/human_review_eight.json. Free: no model is called.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


Q = _load("quotecheck_m1", STUDY / "results" / "machine_only" / "quotecheck_m1.py")
C, A = Q.C, Q.A
PS = _load("prepare_scoring_an", HERE / "prepare_scoring.py")

S1 = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"]
EXT = ["WHU-S05", "WHU-S06", "WHU-S07", "WHU-S08"]
SETS = {"S01-S04": S1, "S05-S08": EXT, "all_eight": S1 + EXT}
FRAME = {"WHU-S01": "Cochrane (health)", "WHU-S02": "Campbell", "WHU-S03": "IPCC AR6", "WHU-S04": "IPCC AR6",
         "WHU-S05": "Cochrane (health)", "WHU-S06": "Campbell", "WHU-S07": "IPCC AR6", "WHU-S08": "IPCC AR6"}
HEALTH = {"WHU-S01", "WHU-S05"}
TAGS = ("", "_ext")
# WHU-S05's two Lancet DOIs: not free to read, so unreachable (advisor's ruling, 2026-10-27).
LANCET = ("https://doi.org/10.1016/S0140-6736(23)01231-X", "https://doi.org/10.1016/S0140-6736(24)01500-9")
QC_DIRS = ("replies", "replies_ext")
SND = Q.SND


def configure(qs: list[str]) -> None:
    A.QUESTIONS, A.HEALTH, A.TAGS = list(qs), HEALTH & set(qs), TAGS
    A.FRAME = {q: FRAME[q] for q in qs}


def short(view: dict) -> dict:
    return {"systems": {s: {k: view["systems"][s][k] for k in ("failures", "countable", "rate", "ci95")}
                        for s in A.SYSTEMS},
            "per_question": {s: {q: v["rate"] for q, v in view["systems"][s]["per_question"].items()}
                             for s in A.SYSTEMS},
            "WHU_vs_Claude": view["vs_whu"]["Claude"]}


def cross_company() -> dict:
    m1, m2 = A.items_m1(), A.items_m2()
    restored = C.abstract_correct(m1)
    fb = {"M1": C.fallbacks(m1, A.M1_PASS | A.M1_FAIL | A.M1_EXCL), "M2": C.fallbacks(m2, A.M2_PASS | A.M2_FAIL)}
    out = {"abstract_only_labels_restored_to_Absent": restored, "refusal_fallbacks": fb}
    for name, rows, fail, ok in (("M1", m1, A.M1_FAIL, A.M1_PASS), ("M2", m2, A.M2_FAIL, A.M2_PASS)):
        v = A.view_scores(rows, fail, ok)
        out[name] = {"cross_company": short(A.analyse_view(C.assigned(v))),
                     "two_judge_combined_abstract_corrected": short(A.analyse_view(v["combined"]))}
    return out


def quote_checked() -> dict:
    """WHU's M1 items with a quote-check re-judge from both judges, quote-checked;
    every other item as labelled (Stage 1 rules, abstract-only correction)."""
    replies = {}
    for d in QC_DIRS:
        for j in A.JUDGES:
            for f in sorted((Q.OUTDIR / d / j).glob("*.json")) if (Q.OUTDIR / d / j).exists() else []:
                r = json.loads(f.read_text(encoding="utf-8"))
                replies.setdefault(r["item"], {})[j] = r
    rows = A.items_m1()
    C.abstract_correct(rows)
    valid = A.M1_PASS | A.M1_FAIL | A.M1_EXCL | {SND}
    texts, used, down = {}, 0, {j: 0 for j in A.JUDGES}
    whu_judged = [r for r in rows if r["system"] == "WHU" and r["raw"]
                  and all((r["raw"].get(j) or {}).get("attempts") for j in A.JUDGES)]
    missing = [r["item"] for r in whu_judged if set(replies.get(r["item"], {})) != set(A.JUDGES)]
    for r in whu_judged:
        if r["item"] in missing:
            continue
        used += 1
        raw = {}
        for j in A.JUDGES:
            rep = replies[r["item"]][j]
            for s in rep["sources"]:
                if s["source_id"] not in texts:
                    texts[s["source_id"]] = (Q.RUN / "sources" / (s["source_id"] + ".txt")).read_text(encoding="utf-8")
            lab = Q.checked_label(rep["label"], Q.check_reply(rep, texts))
            down[j] += lab == SND
            raw[j] = {**rep, "label": lab}
        r["raw"], r["repeat"] = raw, {}
        C.abstract_correct([r])
        r["labels"] = A.per_judge_labels(r["raw"], valid)
    v = A.view_scores(rows, A.M1_FAIL | {SND}, A.M1_PASS)
    return {"whu_items_quote_checked": used, "whu_items_without_a_rejudge": len(missing),
            "downgraded_to_support_not_demonstrated": down,
            "two_judge_combined": short(A.analyse_view(v["combined"])),
            "cross_company_openai_judge": short(A.analyse_view(
                [x for x in v["openai_judge"] if x[1] in ("WHU", "Claude")]))}


def sensitivity() -> dict:
    rows = A.items_m1()
    km_items = {it["item"]: it for it in json.loads((Q.RUN / "items.json").read_text(encoding="utf-8"))}
    v = A.view_scores(rows, A.M1_FAIL, A.M1_PASS)
    excluded = {r["item"] for r, (_, _, sc) in zip(rows, v["combined"]) if not r["uncited"] and sc is None}
    lancet = {r["item"] for r in rows if r["system"] == "WHU" and r["question"] == "WHU-S05"
              and any(c.get("url") in LANCET for c in km_items[r["item"]]["citations"])}
    out = {"excluded_cited_items": {s: sum(1 for r in rows if r["item"] in excluded and r["system"] == s)
                                    for s in A.SYSTEMS},
           "whu_lancet_items_subset_of_excluded": lancet <= excluded}
    for name, worst in (("whu_all_excluded_items_as_failures", {r["item"] for r in rows if r["system"] == "WHU"} & excluded),
                        ("whu_s05_lancet_items_as_failures", lancet)):
        sc = [(q, s, 1.0 if r["item"] in worst else x) for r, (q, s, x) in zip(rows, v["combined"])]
        av = A.analyse_view(sc)
        out[name] = {"items_counted_as_failures": len(worst),
                     "WHU": {k: av["systems"]["WHU"][k] for k in ("failures", "countable", "rate", "ci95")},
                     "Claude": {k: av["systems"]["Claude"][k] for k in ("failures", "countable", "rate", "ci95")},
                     "H1_WHU_vs_Claude": av["vs_whu"]["Claude"]}
    return out


def reachability(qs: list[str]) -> dict:
    items = json.loads((Q.RUN / "items.json").read_text(encoding="utf-8"))
    km = json.loads((Q.RUN / "key_map.json").read_text(encoding="utf-8"))
    man = {r["url"]: r for r in json.loads((Q.RUN / "sources" / "manifest.json").read_text())}
    return PS.reachability([it for it in items if km[it["item"]]["question"] in qs], km, man)


def one_set(qs: list[str]) -> tuple[dict, list]:
    configure(qs)
    res, review = A.build()
    m1, m2 = res["M1_citation_support"], res["M2_conclusion_calibration"]
    out = {
        "questions": qs, "frames": A.FRAME, "health_questions": sorted(A.HEALTH),
        "H1_two_judge": res["H1"], "H2_two_judge": res["H2"],
        "M1": {"counts": m1["counts"], "uncited_rate": m1["uncited_rate"],
               "views": {k: short(v) for k, v in m1["views"].items()},
               "cited_items_only_combined": short(m1["cited_items_only_combined"]),
               "judges": m1["judges"], "label_counts_first_read": m1["label_counts_first_read"],
               "direction_of_failures": m1["direction_of_failures"]},
        "M2": {"items_per_system": m2["items_per_system"], "views": {k: short(v) for k, v in m2["views"].items()},
               "judges": m2["judges"], "label_counts_first_read": m2["label_counts_first_read"],
               "direction_of_failures": m2["direction_of_failures"],
               "possible_key_disputes": m2["possible_key_disputes"]},
        "cross_company": cross_company(),
        "quote_checked_M1": quote_checked(),
        "sensitivity_M1": sensitivity(),
        "citation_reachability": reachability(qs),
        "human_review_list": {"items": len(review), "by_reason": {}},
    }
    for x in review:
        for w in x["reasons"]:
            out["human_review_list"]["by_reason"][w] = out["human_review_list"]["by_reason"].get(w, 0) + 1
    return out, review


def spend() -> dict:
    S = Q.S
    whu = {i: 0.0 for i in Q.WHU_ISSUES}
    judging = {}
    for e in S.entries():
        i = e.get("issue") or ""
        if i in whu:
            whu[i] += float(e.get("usd") or 0)
        elif i.startswith("whu-reliability-judging"):
            judging[i] = judging.get(i, 0.0) + float(e.get("usd") or 0)
    tw, tj = sum(whu.values()), sum(judging.values())
    return {"whu_by_issue": {k: round(v, 2) for k, v in whu.items()}, "whu_total": round(tw, 2),
            "judging_by_issue": {k: round(v, 2) for k, v in sorted(judging.items())}, "judging_total": round(tj, 2),
            "study_total": round(tw + tj, 2), "study_total_check": Q.STUDY_TOTAL}


def main() -> int:
    res = {"written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "label": "All eight questions: AI judges only, not checked by people",
           "rules": "scripts/analyse.py (Stage 1 rules, unchanged), via scripts/analyse_eight.py",
           "seed": str(A.SEED), "bootstrap_resamples": A.B,
           "chatgpt_note": "ChatGPT: no web search performed on S05-S08 (0 searches, 0 citations); "
                           "its S05-S08 sentences are all uncited. Outside H1 and H2.",
           "extension_rule": "applied once (Stage 1, deviations 2026-10-24); the all-eight two-judge "
                             "result is the outcome and the rule is not applied again",
           "sets": {}}
    review_all = []
    for name, qs in SETS.items():
        res["sets"][name], review = one_set(qs)
        if name == "all_eight":
            review_all = review
    res["outcome_all_eight"] = {"H1": res["sets"]["all_eight"]["H1_two_judge"],
                                "H2": res["sets"]["all_eight"]["H2_two_judge"]}
    res["spend"] = spend()
    (A.PRIVATE / "human_review_eight.json").write_text(json.dumps(review_all, indent=1), encoding="utf-8")
    (A.OUT / "eight_ai_only.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["outcome_all_eight"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
