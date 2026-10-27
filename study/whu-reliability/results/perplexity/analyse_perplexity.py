#!/usr/bin/env python3
"""Perplexity add-on (exploratory, outside H1 and H2): Perplexity's M1 and M2
rates on WHU-S01 to WHU-S04, and WHU minus Perplexity.

    analyse_perplexity.py

Plan: study/whu-reliability/perplexity_plan.md (frozen at 078ab4e). Writes
results/perplexity/perplexity_ai_only.json: numbers only, no answer, key or
source text. Free: no model is called.

RULES. analyse.py's, as analyse_eight.py applies them on S01-S04: each
judge's first-read label after the refusal rule; Uncited is an M1 failure;
Unreachable, INCOMPLETE_SOURCES and NOT_VERIFIABLE_ABSTRACT are excluded,
with NOT_VERIFIABLE_ABSTRACT kept only when EVERY cited snapshot is abstract
only (cross_company.abstract_correct). Views: two-judge combined, each judge,
agreed only, and M1 on cited items only.

ROWS. WHU's are analyse.py's own S01-S04 rows from the study's private m1/
and m2/ (replies "" and "_repeat"), unchanged. Perplexity's are read the same
way from ~/Projects/whu-study-private/scoring/perplexity/m1 and m2.

INTERVALS. analyse.analyse_view: whole questions resampled (4 with
replacement), 10,000 resamples, random.Random(int(freeze commit, 16));
WHU minus Perplexity and WHU over Perplexity on the same resample. The
"holds" flag analyse_view prints is the H1/H2 rule's arithmetic only: this
comparison is exploratory and outside H1 and H2.
"""
from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
PRIVATE = Path.home() / "Projects" / "whu-study-private" / "scoring"
PPLX = PRIVATE / "perplexity"
QUESTIONS = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"]
ISSUES = ("whu-reliability-judging-perplexity",)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


C = _load("cross_company_pplx", STUDY / "results" / "machine_only" / "cross_company.py")
A = C.A


def rows_from(base: Path, system: str) -> tuple[list[dict], list[dict]]:
    keep = A.PRIVATE
    A.PRIVATE = base
    try:
        m1 = [r for r in A.items_m1() if r["system"] == system]
        m2 = [r for r in A.items_m2() if r["system"] == system]
    finally:
        A.PRIVATE = keep
    C.abstract_correct(m1)
    return m1, m2


def counts(m1: list[dict], s: str) -> dict:
    rs = [r for r in m1 if r["system"] == s]
    lab = lambda r: {(r["raw"].get(j) or {}).get("label") for j in A.JUDGES}
    d = {"drawn": len(rs), "uncited": sum(r["uncited"] for r in rs), "cited": sum(not r["uncited"] for r in rs),
         "no_source_held": sum(not r["uncited"] and not r["raw"] for r in rs),
         "incomplete_sources_unreachable": sum(A.INCOMPLETE in lab(r) and not A.undelivered(r) for r in rs),
         "incomplete_sources_undelivered": sum(A.INCOMPLETE in lab(r) and A.undelivered(r) for r in rs),
         "judge_said_unreachable_any": sum("Unreachable" in lab(r) for r in rs),
         "not_verifiable_abstract_any": sum(A.NVA in lab(r) for r in rs)}
    d["uncited_share_of_drawn"] = A.r4(d["uncited"] / d["drawn"] if d["drawn"] else None)
    d["unreachable_share_of_cited"] = A.r4((d["no_source_held"] + d["incomplete_sources_unreachable"]
                                            + d["judge_said_unreachable_any"]) / d["cited"] if d["cited"] else None)
    d["flag_unreachable_over_20pct"] = bool(d["unreachable_share_of_cited"] and d["unreachable_share_of_cited"] > 0.2)
    return d


def spend() -> dict:
    S = _load("spend_ledger_pplx", STUDY.parents[1] / "backend" / "scripts" / "spend_ledger.py")
    rows = [e for e in S.entries() if e.get("issue") in ISSUES]
    by = {}
    for e in rows:
        by[e.get("role") or "?"] = round(by.get(e.get("role") or "?", 0.0) + float(e.get("usd") or 0), 4)
    return {"issues": list(ISSUES), "usd": round(sum(float(e.get("usd") or 0) for e in rows), 4),
            "calls": len(rows), "by_role": by}


def main() -> int:
    A.QUESTIONS, A.HEALTH, A.TAGS = list(QUESTIONS), {"WHU-S01"}, ("",)
    A.FRAME = {q: A.FRAME[q] for q in QUESTIONS}
    w1, w2 = rows_from(PRIVATE, "WHU")
    p1, p2 = rows_from(PPLX, "Perplexity")
    A.SYSTEMS = ["WHU", "Perplexity"]
    m1, m2 = w1 + p1, w2 + p2
    v1, v2 = A.view_scores(m1, A.M1_FAIL, A.M1_PASS), A.view_scores(m2, A.M2_FAIL, A.M2_PASS)
    cited = A.view_scores([r for r in m1 if not r["uncited"]], A.M1_FAIL, A.M1_PASS)
    snap = json.loads((HERE / "snapshot_counts.json").read_text())
    res = {
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": "Exploratory add-on, outside H1 and H2: AI judges only, not checked by people",
        "plan": "study/whu-reliability/perplexity_plan.md",
        "rules": "results/perplexity/analyse_perplexity.py docstring (analyse.py's rules, EVERY abstract-only rule)",
        "questions": QUESTIONS, "seed": str(A.SEED), "bootstrap_resamples": A.B,
        "M1_citation_support": {
            "counts": {s: counts(m1, s) for s in A.SYSTEMS},
            "views": {k: A.analyse_view(v) for k, v in v1.items()},
            "cited_items_only_combined": A.analyse_view(cited["combined"]),
            "judges": A.judge_stats(m1, A.M1_FAIL),
            "label_counts_first_read": A.label_counts(m1),
            "direction_of_failures": A.directions(m1, ["Overstates", "Understates"]),
        },
        "M2_conclusion_calibration": {
            "items_per_system": {s: sum(r["system"] == s for r in m2) for s in A.SYSTEMS},
            "views": {k: A.analyse_view(v) for k, v in v2.items()},
            "judges": A.judge_stats(m2, A.M2_FAIL),
            "label_counts_first_read": A.label_counts(m2),
            "direction_of_failures": A.directions(m2, ["Overstates", "Understates"]),
            "possible_key_disputes_perplexity": sum(1 for r in p2 if "Contradicts" in
                                                    {(r["raw"].get(j) or {}).get("label") for j in A.JUDGES}),
        },
        "perplexity_citation_reachability": snap.get("reachability"),
        "perplexity_sources": snap.get("sources"),
        "judging_spend": spend(),
    }
    (HERE / "perplexity_ai_only.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k in ("M1_citation_support", "M2_conclusion_calibration"):
        v = res[k]["views"]["combined"]
        print(k, {s: (v["systems"][s]["rate"], v["systems"][s]["countable"]) for s in A.SYSTEMS},
              "WHU-Perplexity", v["vs_whu"]["Perplexity"]["difference_whu_minus"], v["vs_whu"]["Perplexity"]["difference_ci95"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
