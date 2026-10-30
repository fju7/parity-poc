#!/usr/bin/env python3
"""WHU quarterly round 1: WHU's M1 failures, per judge, by question, by reason
and by the failing sentence's origin on the page.

    whu_m1_failures_round1.py

Writes quarterly/round1_scoring/whu_m1_failures_round1.json: item ids and
counts only, no sentence, key or source text. Free: no model is called.

FAILURE. analyse_round1.py's M1 rows (analyse.py's rules, EVERY abstract-only
rule): a judge's counted label (after the refusal rule) in analyse.py's
M1_FAIL.

REASON. "uncited" (a drawn sentence with no citation marker); "abstract-only
under the EVERY rule" (the judge's stored label was NOT_VERIFIABLE_ABSTRACT
with its own label Absent, restored to Absent because not every cited
snapshot is abstract only); "cited but not supported" (Overstates,
Understates, Absent, Wrong source, Contradicted as judged); nothing else
fails under M1_FAIL, and any other case would be listed as "other".

ORIGIN. The drawn sentence (items.json / uncited.json "claim", the blinded
text) is matched to the WHU page's own records, after both are reduced to
lower-case words with citation markers removed: "omission ADD" if it matches
a bindings.json row with origin omission_add; "audit rewording" if it
matches the text an audit ruling applied (rulings.jsonl, ruling accept or
amend: its "text", else the proposed text); otherwise "first-draft text".
A sentence that matches neither a binding nor a ruling is still first-draft
text by this rule; how many matched a binding row is reported.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("analyse_round1_f", HERE / "analyse_round1.py")
AR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AR)
A = AR.A
OUT = AR.LOG / "whu_m1_failures_round1.json"


def norm(t: str) -> str:
    t = re.sub(r"\[\d+(?:[,–-]\s*\d+)*\]", " ", t or "")
    return " ".join(re.findall(r"[a-z0-9]+", t.lower()))


def page_records(q: str) -> tuple[set, set]:
    d = next((REPO / "issues").glob(q + "-*"))
    b = json.loads((d / "bindings.json").read_text())["bindings"]
    adds = {norm(r["sentence"]) for r in b.values() if r.get("origin") == "omission_add"}
    bound = {norm(r["sentence"]) for r in b.values()}
    rew = set()
    for f in sorted(d.glob("audit/*/rulings.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("ruling") in ("accept", "amend"):
                t = r.get("text") or (r.get("inputs") or {}).get("proposed_text")
                if t:
                    rew.add(norm(t))
    return adds, rew, bound


def match(s: str, pool: set) -> bool:
    return bool(s) and any(s == p or (len(s) >= 30 and (s in p or p in s)) for p in pool)


def main() -> int:
    rows, _ = AR.round1_rows()
    # Labels as stored, before the EVERY correction, for the abstract-only reason.
    A.PRIVATE, A.QUESTIONS, A.TAGS = AR.RUN, list(AR.QS), ("",)
    stored = {r["item"]: {j: ((r["raw"].get(j) or {}).get("label"), (r["raw"].get(j) or {}).get("judge_label"))
                          for j in A.JUDGES} for r in A.items_m1()}
    texts = {}
    for f in ("items.json", "uncited.json"):
        for it in json.loads((AR.RUN / "m1" / f).read_text()):
            texts[it["item"]] = it["claim"]
    recs = {q: page_records(q) for q in AR.QS}
    whu = [r for r in rows if r["system"] == "WHU"]
    origin, bound_hit = {}, 0
    for r in whu:
        s = norm(texts[r["item"]])
        adds, rew, bound = recs[r["question"]]
        bound_hit += match(s, bound)
        origin[r["item"]] = ("omission ADD" if match(s, adds) else
                             "audit rewording" if match(s, rew) else "first-draft text")
    out = {"label": "WHU quarterly round 1, WHU's M1 failures: AI judges only; item ids and counts only",
           "rules": "quarterly/whu_m1_failures_round1.py docstring",
           "whu_items": len(whu), "whu_items_matched_to_a_binding_row": bound_hit,
           "origin_of_all_whu_items": {}, "judges": {}}
    for o in origin.values():
        out["origin_of_all_whu_items"][o] = out["origin_of_all_whu_items"].get(o, 0) + 1
    for j in A.JUDGES:
        fails = []
        for r in whu:
            lab = r["labels"][j]
            if lab not in A.M1_FAIL:
                continue
            st, own = stored[r["item"]][j]
            if r["uncited"]:
                why = "uncited"
            elif st == A.NVA and own == "Absent" and lab == "Absent":
                why = "abstract-only under the EVERY rule"
            elif lab in A.M1_FAIL:
                why = "cited but not supported (%s)" % lab
            else:
                why = "other"
            fails.append({"item": r["item"], "question": r["question"], "reason": why, "origin": origin[r["item"]]})
        by = lambda k: {v: sum(1 for f in fails if f[k] == v) for v in sorted({f[k] for f in fails})}
        countable = sum(1 for r in whu if r["labels"][j] in A.M1_FAIL | A.M1_PASS)
        out["judges"][j] = {"failures": len(fails), "countable": countable,
                            "by_question": {q: {"failures": sum(1 for f in fails if f["question"] == q),
                                                "countable": sum(1 for r in whu if r["question"] == q
                                                                 and r["labels"][j] in A.M1_FAIL | A.M1_PASS)}
                                            for q in AR.QS},
                            "by_reason": by("reason"), "by_origin": by("origin"), "items": fails}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    for j, v in out["judges"].items():
        print(j, v["failures"], "/", v["countable"], v["by_question"], v["by_reason"], v["by_origin"])
    print("origin of all WHU items", out["origin_of_all_whu_items"], "matched to a binding", bound_hit, "of", len(whu))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
