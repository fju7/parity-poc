#!/usr/bin/env python3
"""WHU quarterly round 1: the pre-stated comparisons (round1_protocol.md §6),
AI judges only.

    analyse_round1.py

Writes quarterly/round1_scoring/round1_ai_only.json: numbers only, no answer,
key or source text. The human-review list (item ids and reasons) goes to the
private run directory. Free: no model is called.

RULES. analyse.py's, as analyse_eight.py applies them, through their own
functions: each judge's first-read label after the refusal rule; Uncited is
an M1 failure; Unreachable, INCOMPLETE_SOURCES and NOT_VERIFIABLE_ABSTRACT
are excluded, NOT_VERIFIABLE_ABSTRACT kept only when EVERY cited snapshot is
abstract only (cross_company.abstract_correct); two-judge combined = the mean
of the judges' failure indicators. Not quote-checked (protocol §5).

MEASURES (§6A). M1 failure rate (analyse.py's M1_FAIL over countable items);
M2 Overstates rate (fail: Overstates; countable: any M2 label); M2
Understates+Omits rate (fail: Understates or Omits). §6B also uses M2
Overstates+Contradicts. Views: two-judge combined, each judge, agreed only.

INTERVALS. analyse.analyse_view: whole questions resampled with replacement,
10,000 resamples, random.Random(int(round-1 freeze commit, 16)); WHU minus T
and WHU over T on the same resample. The half-rate flag is reported and
decides nothing. §6B: round 1's questions and the study's eight are
resampled separately on each resample (one generator, round 1 first), and
the difference round 1 minus study is taken on the same resample.

SETS. All four questions; without WHU-Q1-02 (its WHU answer is a page at a
STOP, deviations 2026-10-29); and, for Perplexity, Q1-03 and Q1-04 only (the
two report-card answers; ruling 2026-10-29). Gemini has no Q1-04 answer: its
rates are over its three questions, and WHU against Gemini is also given on
those three. ChatGPT: "no web search performed" (0 searches, all four).

STUDY (§6B). WHU's rows on WHU-S01 to S08 read by analyse_eight.py's own
setup (replies "" and "_ext", EVERY rule); its M1 and M2 two-judge rates are
checked against results/eight_ai_only.json before anything is written.
"""
from __future__ import annotations

import importlib.util
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
LOG = HERE / "round1_scoring"
RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "quarterly" / "round1"
FREEZE = "5f4a928b757d7f47c1ba8ed47600ced4a7a69f12"
SEED = int(FREEZE, 16)
QS = ["WHU-Q1-01", "WHU-Q1-02", "WHU-Q1-03", "WHU-Q1-04"]
SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini", "Perplexity"]
ISSUES_WHU = ("whu-quarterly-r1-01", "whu-quarterly-r1-02", "whu-quarterly-r1-03", "whu-quarterly-r1-04")
ISSUE_JUDGING = "whu-quarterly-r1-judging"
SETS = {"all_four": QS, "without_Q1_02": ["WHU-Q1-01", "WHU-Q1-03", "WHU-Q1-04"]}
MATCHED = {"Gemini": ["WHU-Q1-01", "WHU-Q1-02", "WHU-Q1-03"], "Perplexity": ["WHU-Q1-03", "WHU-Q1-04"]}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


E = _load("analyse_eight_r1", STUDY / "scripts" / "analyse_eight.py")
A, C = E.A, E.C

M2_ALL = A.M2_PASS | A.M2_FAIL
MEASURES = {
    "M1_failure": ("M1", A.M1_FAIL, A.M1_PASS),
    "M2_overstates": ("M2", {"Overstates"}, M2_ALL - {"Overstates"}),
    "M2_understates_omits": ("M2", {"Understates", "Omits"}, M2_ALL - {"Understates", "Omits"}),
    "M2_overstates_contradicts": ("M2", {"Overstates", "Contradicts"}, M2_ALL - {"Overstates", "Contradicts"}),
    "M2_any_failure": ("M2", A.M2_FAIL, A.M2_PASS),
}
VIEWS = ("combined", "claude_judge", "openai_judge", "agreed_only")


def round1_rows() -> tuple[list[dict], list[dict]]:
    A.PRIVATE, A.QUESTIONS, A.TAGS = RUN, list(QS), ("",)
    m1, m2 = A.items_m1(), A.items_m2()
    C.abstract_correct(m1)
    return m1, m2


def study_whu_rows() -> tuple[list[dict], list[dict], list[str]]:
    keep = A.PRIVATE
    A.PRIVATE = Path.home() / "Projects" / "whu-study-private" / "scoring"
    qs = E.SETS["all_eight"]
    E.configure(qs)
    try:
        m1 = [r for r in E.items_m1_every() if r["system"] == "WHU"]
        m2 = [r for r in A.items_m2() if r["system"] == "WHU"]
    finally:
        A.PRIVATE = keep
    return m1, m2, qs


def view(rows, qs, systems, measure, name):
    _, fail, ok = MEASURES[measure]
    A.QUESTIONS, A.SYSTEMS, A.SEED = list(qs), list(systems), SEED
    A.HEALTH, A.FRAME = {"WHU-Q1-01"} & set(qs), {q: q for q in qs}
    rs = [r for r in rows if r["question"] in qs and r["system"] in systems]
    return A.analyse_view(A.view_scores(rs, fail, ok)[name])


def compact(v, systems):
    out = {s: {k: v["systems"][s][k] for k in ("failures", "countable", "rate", "ci95")}
           | {"per_question": {q: (x["rate"], x["countable"]) for q, x in v["systems"][s]["per_question"].items()}}
           for s in systems}
    for s in systems[1:]:
        w = v["vs_whu"][s]
        out[s]["WHU_vs"] = {"difference_whu_minus": w["difference_whu_minus"], "difference_ci95": w["difference_ci95"],
                            "ratio_whu_over": w["ratio_whu_over"], "ratio_ci95": w["ratio_ci95"],
                            "whu_at_most_half (reported, decides nothing)": w["whu_at_most_half"],
                            "difference_ci_excludes_zero": w["difference_ci_excludes_zero"]}
    return out


def part_a(m1, m2) -> dict:
    out = {}
    for set_name, qs in SETS.items():
        res = {}
        for measure, (which, _, _) in MEASURES.items():
            rows = m1 if which == "M1" else m2
            res[measure] = {vn: compact(view(rows, qs, SYSTEMS, measure, vn), SYSTEMS) for vn in VIEWS}
            res[measure]["matched_questions"] = {
                s: {vn: compact(view(rows, [q for q in MATCHED[s] if q in qs], ["WHU", s], measure, vn), ["WHU", s])
                    for vn in VIEWS[:3]} for s in MATCHED if [q for q in MATCHED[s] if q in qs]}
        out[set_name] = res
    return out


def tally(rows, measure, name) -> dict:
    _, fail, ok = MEASURES[measure]
    return A.tallies(A.view_scores(rows, fail, ok)[name])


def part_b(m1, m2) -> dict:
    s1, s2, sq = study_whu_rows()
    check = json.loads((STUDY / "results" / "eight_ai_only.json").read_text())["sets"]["all_eight"]
    out = {"study_questions": sq, "study_source": "results/eight_ai_only.json (unchanged), WHU-S01 to WHU-S08",
           "label": "descriptive; 4 questions", "sets": {}}
    for set_name, qs in SETS.items():
        rng = random.Random(SEED)
        boots = [([rng.choice(qs) for _ in qs], [rng.choice(sq) for _ in sq]) for _ in range(A.B)]
        res = {}
        for measure, (which, _, _) in MEASURES.items():
            r1rows = [r for r in (m1 if which == "M1" else m2) if r["system"] == "WHU" and r["question"] in qs]
            strows = s1 if which == "M1" else s2
            res[measure] = {}
            for vn in VIEWS[:3]:
                t1, ts = tally(r1rows, measure, vn), tally(strows, measure, vn)
                a, b = A.rate(t1, "WHU", qs), A.rate(ts, "WHU", sq)
                diffs = [x - y for x, y in ((A.rate(t1, "WHU", bq), A.rate(ts, "WHU", bs)) for bq, bs in boots)
                         if x is not None and y is not None]
                n1 = sum(t1.get((q, "WHU"), [0, 0])[1] for q in qs)
                ns = sum(ts.get((q, "WHU"), [0, 0])[1] for q in sq)
                res[measure][vn] = {"round1": A.r4(a), "round1_countable": n1, "study": A.r4(b), "study_countable": ns,
                                    "difference_round1_minus_study": A.r4(None if a is None or b is None else a - b),
                                    "difference_ci95": [A.r4(A.pct(diffs, 0.025)), A.r4(A.pct(diffs, 0.975))]}
        c1 = all(res["M2_understates_omits"][v]["difference_round1_minus_study"] < 0 for v in ("claude_judge", "openai_judge"))
        c2 = all(res["M2_overstates_contradicts"][v]["difference_round1_minus_study"] <= 0 for v in ("claude_judge", "openai_judge"))
        c3 = res["M1_failure"]["combined"]["difference_round1_minus_study"] <= 0.05
        res["fixes_rule"] = {"label": "descriptive; 4 questions" if set_name == "all_four" else "descriptive; 3 questions",
                             "1_M2_understates_omits_below_study_both_judges": c1,
                             "2_M2_overstates_contradicts_not_above_study_either_judge": c2,
                             "3_M1_combined_at_most_5pp_above_study": c3,
                             "held_on_fresh_questions": c1 and c2 and c3}
        out["sets"][set_name] = res
    # The study's rates by this code must equal results/eight_ai_only.json's.
    got = {"M1": out["sets"]["all_four"]["M1_failure"]["combined"]["study"],
           "M2": out["sets"]["all_four"]["M2_any_failure"]["combined"]["study"]}
    want = {"M1": check["M1"]["views"]["combined"]["systems"]["WHU"]["rate"],
            "M2": check["M2"]["views"]["combined"]["systems"]["WHU"]["rate"]}
    out["check_against_eight_ai_only"] = {"computed": got, "eight_ai_only": want, "equal": got == want}
    if got != want:
        raise SystemExit("STOP: the study's WHU rates by this code %s differ from eight_ai_only.json %s" % (got, want))
    return out


def counts(m1, s) -> dict:
    rs = [r for r in m1 if r["system"] == s]
    lab = lambda r: {(r["raw"].get(j) or {}).get("label") for j in A.JUDGES}
    d = {"questions": sorted({r["question"] for r in rs}), "drawn": len(rs),
         "uncited": sum(r["uncited"] for r in rs), "cited": sum(not r["uncited"] for r in rs),
         "no_source_held": sum(not r["uncited"] and not r["raw"] for r in rs),
         "incomplete_sources_unreachable": sum(A.INCOMPLETE in lab(r) and not A.undelivered(r) for r in rs),
         "incomplete_sources_undelivered": sum(A.INCOMPLETE in lab(r) and A.undelivered(r) for r in rs),
         "judge_said_unreachable_any": sum("Unreachable" in lab(r) for r in rs),
         "not_verifiable_abstract_any": sum(A.NVA in lab(r) for r in rs)}
    d["uncited_share_of_drawn"] = A.r4(d["uncited"] / d["drawn"] if d["drawn"] else None)
    return d


def spend() -> dict:
    S = _load("spend_ledger_r1an", REPO / "backend" / "scripts" / "spend_ledger.py")
    by = {}
    for e in S.entries():
        i = e.get("issue") or ""
        if i in ISSUES_WHU or i == ISSUE_JUDGING:
            by.setdefault(i, {}).setdefault(e.get("role") or "?", 0.0)
            by[i][e.get("role") or "?"] += float(e.get("usd") or 0)
    tot = {i: round(sum(v.values()), 2) for i, v in by.items()}
    return {"by_issue": tot, "judging_by_role": {k: round(v, 2) for k, v in by.get(ISSUE_JUDGING, {}).items()},
            "whu_total": round(sum(tot.get(i, 0) for i in ISSUES_WHU), 2), "judging_total": tot.get(ISSUE_JUDGING, 0),
            "round_total": round(sum(tot.values()), 2), "round_cap": 275.0}


def main() -> int:
    m1, m2 = round1_rows()
    A.SYSTEMS, A.QUESTIONS = list(SYSTEMS), list(QS)
    review = A.review_list(m1, "M1") + A.review_list(m2, "M2")
    snap = json.loads((LOG / "snapshot_counts.json").read_text())
    res = {
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": "WHU quarterly round 1: AI judges only, not checked by people; nothing here is H1 or H2",
        "rules": "quarterly/analyse_round1.py docstring (analyse.py's rules via analyse_eight.py; EVERY abstract-only rule; not quote-checked)",
        "freeze": FREEZE, "seed": str(SEED), "bootstrap_resamples": A.B, "questions": QS,
        "notes": {"ChatGPT": "no web search performed (0 searches, 0 citations, all four questions)",
                  "Gemini": "3 questions (WHU-Q1-04: no result, two technical failures)",
                  "Perplexity": "Q1-03 and Q1-04 report cards; Q1-01 and Q1-02 inline answers, scored as captured",
                  "WHU-Q1-02": "WHU's answer is its page at a STOP, not Ready (deviations 2026-10-29)"},
        "M1_counts": {s: counts(m1, s) for s in SYSTEMS},
        "M2_items": {s: sum(r["system"] == s for r in m2) for s in SYSTEMS},
        "M1_judges": A.judge_stats(m1, A.M1_FAIL), "M2_judges": A.judge_stats(m2, A.M2_FAIL),
        "M1_label_counts_first_read": A.label_counts(m1), "M2_label_counts_first_read": A.label_counts(m2),
        "M1_direction_of_failures": A.directions(m1, ["Overstates", "Understates"]),
        "M2_direction_of_failures": A.directions(m2, ["Overstates", "Understates", "Omits", "Contradicts"]),
        "reachability": snap.get("reachability"), "sources": snap.get("sources"),
        "A_whu_against_each_tool": part_a(m1, m2),
        "B_whu_round1_against_study": part_b(m1, m2),
        "human_review_list": {"items": len(review), "by_reason": {}},
        "spend": spend(),
    }
    for x in review:
        for w in x["reasons"]:
            res["human_review_list"]["by_reason"][w] = res["human_review_list"]["by_reason"].get(w, 0) + 1
    (RUN / "human_review_round1.json").write_text(json.dumps(review, indent=1), encoding="utf-8")
    (LOG / "round1_ai_only.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"check": res["B_whu_round1_against_study"]["check_against_eight_ai_only"],
                      "fixes_rule": {k: v["fixes_rule"] for k, v in res["B_whu_round1_against_study"]["sets"].items()}},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
