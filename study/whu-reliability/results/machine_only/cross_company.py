#!/usr/bin/env python3
"""Machine-only spec (b): the cross-company judge analysis. No model is called.

    cross_company.py

Spec (machine_only_plan.md, sha256 5c5059f3...): WHU and Claude Research are
scored by the OpenAI judge only (WHU runs on Claude); ChatGPT by the Claude
judge only; Gemini by both (analyse.py's combined score, the mean of the two
judges' failure indicators). M1 and M2 recomputed, and the WHU-vs-Claude
Research test, with the same bootstrap and the same seed.

Everything is analyse.py's: its item loaders, label rules, exclusions,
scores, bootstrap (analyse_view) and decision rule. One input correction is
applied before them, the abstract-only correction found by the independent
check (check/check_stage1.py): a stored NOT_VERIFIABLE_ABSTRACT stands only
when EVERY cited snapshot of the item is abstract only; where only some are,
the judge's own label (Absent) is restored. No other rule changes.

Writes the counts-only result cross_company.json next to this file. Reads the
private replies; no answer, source or quote text is written.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
_spec = importlib.util.spec_from_file_location("analyse", STUDY / "scripts" / "analyse.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

# Which judge's reading scores each system (spec (b)); "combined" = both.
ASSIGNMENT = {"WHU": "openai_judge", "Claude": "openai_judge", "ChatGPT": "claude_judge", "Gemini": "combined"}


def abstract_correct(rows: list[dict]) -> int:
    """NOT_VERIFIABLE_ABSTRACT only when every cited snapshot is abstract only.
    Rewrites the reply's label in memory and recomputes analyse.py's per-judge
    labels. Returns how many judge labels were restored to Absent."""
    n = 0
    for r in rows:
        for j, rep in list(r["raw"].items()):
            if rep.get("label") == A.NVA and rep.get("judge_label") == "Absent" \
                    and not all(s.get("abstract_only") for s in rep.get("sources") or []):
                r["raw"][j] = {**rep, "label": "Absent"}
                n += 1
        if r["raw"]:
            r["labels"] = A.per_judge_labels(r["raw"], A.M1_PASS | A.M1_FAIL | A.M1_EXCL)
    return n


def fallbacks(rows: list[dict], valid: set) -> int:
    """Items where analyse.py's refusal rule would hand one judge's label to
    the other (a REFUSED or unusable first read). Under spec (b) that would let
    the same-company judge in, so the run stops if there is any."""
    return sum(1 for r in rows if r["raw"] and any(
        (r["raw"].get(j) or {}).get("label") == A.REFUSED
        or ((r["raw"].get(j) or {}).get("label") not in valid
            and (r["raw"].get(j) or {}).get("label") != A.INCOMPLETE)
        for j in A.JUDGES))


def assigned(views: dict) -> list:
    out = []
    for name in set(ASSIGNMENT.values()):
        out += [x for x in views[name] if ASSIGNMENT[x[1]] == name]
    return out


def summary(view: dict) -> dict:
    return {"systems": {s: {k: view["systems"][s][k] for k in ("failures", "countable", "rate", "ci95")}
                        for s in A.SYSTEMS},
            "per_question": {s: view["systems"][s]["per_question"] for s in A.SYSTEMS},
            "vs_whu": view["vs_whu"]}


def run(rows, fail, ok) -> dict:
    v = A.view_scores(rows, fail, ok)
    return {"cross_company": summary(A.analyse_view(assigned(v))),
            "two_judge_combined": summary(A.analyse_view(v["combined"]))}


def main() -> int:
    m1, m2 = A.items_m1(), A.items_m2()
    restored = abstract_correct(m1)
    fb = {"M1": fallbacks(m1, A.M1_PASS | A.M1_FAIL | A.M1_EXCL), "M2": fallbacks(m2, A.M2_PASS | A.M2_FAIL)}
    if any(fb.values()):
        print("STOP: refused or unusable first reads would borrow the other judge's label: %s" % fb)
        return 2
    res = {"label": "Machine-only spec (b), cross-company judge: AI judges only, secondary to the two-judge result",
           "assignment": ASSIGNMENT, "seed": str(A.SEED), "bootstrap_resamples": A.B,
           "abstract_only_correction": {"rule": "NOT_VERIFIABLE_ABSTRACT only when every cited snapshot is abstract only",
                                        "judge_labels_restored_to_Absent": restored},
           "refusal_fallbacks_used": fb,
           "M1": run(m1, A.M1_FAIL, A.M1_PASS), "M2": run(m2, A.M2_FAIL, A.M2_PASS)}
    res["H1"] = {k: res["M1"][k]["vs_whu"]["Claude"]["holds"] for k in ("cross_company", "two_judge_combined")}
    res["H2"] = {k: res["M2"][k]["vs_whu"]["Claude"]["holds"] for k in ("cross_company", "two_judge_combined")}
    (HERE / "cross_company.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("H1", res["H1"], "H2", res["H2"], "restored", restored)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
