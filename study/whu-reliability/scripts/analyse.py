#!/usr/bin/env python3
"""Stage 1 analysis (AI judges only), per the frozen protocol's analysis plan.

    analyse.py

Reads the private judge replies (PRIVATE/m1, PRIVATE/m2) and writes
study/whu-reliability/results/stage1_ai_only.json: numbers only, no answer,
key or source text. The human-review list (item ids and reasons only) goes to
PRIVATE/human_review.json. Free: no model is called.

Written and committed before any judge result was read (2026-10-23); the rules
below are fixed by that commit (deviations.md).

LABELS FOR STAGE 1. The protocol's primary result uses final labels after
human review. Stage 1 has no human labels, so each item is read as follows,
and every figure is "AI judges only, not yet checked by people":

  Per judge. The judge's first-read label. A label REFUSED (refused twice, the
  runner's refusal rule) takes the other judge's label; refused by both, or an
  unusable reply, the item has no label from that judge.
  M1 failure: Overstates, Understates, Absent, Wrong source, Contradicted, and
  Uncited (a drawn sentence with no citation, not sent to a judge). Not a
  failure: Supported. Excluded from the rate and reported: Unreachable (a
  cited source not held, INCOMPLETE_SOURCES, or a judge's "Unreachable") and
  NOT_VERIFIABLE_ABSTRACT. M2 failure: anything but Matches.
  Combined (the Stage 1 headline). Each item scores the mean of the two
  judges' failure indicators (0, 0.5 or 1) over the judges that gave it a
  countable label; an item neither counts is excluded.
  Agreed only. Items both judges labelled the same (and the same again on a
  second read where one was made), as the protocol defines agreement.

INTERVALS. A bootstrap that resamples whole questions (4 with replacement),
10,000 resamples, random.Random(int(freeze commit, 16)). A system's rate in a
resample is its failures over its countable items, pooled across the
resampled questions; the difference and the ratio with WHU are computed on
the same resample. 95% percentile intervals.

DECISION (H1 on M1, H2 on M2, WHU against Claude): holds when WHU's rate is
at most half Claude's AND the 95% interval for the difference excludes zero.
Stated for every view (combined, each judge, agreed only); the combined view
is the Stage 1 headline. ChatGPT and Gemini (H4): reported, no threshold.

HUMAN REVIEW LIST: every item the judges did not agree on (including a second
read that changed), every refused or unusable reply, every M1 item with a
source not held (INCOMPLETE_SOURCES), and a seeded random 20% of agreed items
drawn evenly across systems (random.Random("<SEED>/human-audit/<measure>/
<system>")). Also kept: every M2 item a judge labelled Contradicts, as a
possible key dispute (protocol, "When a system disputes the key").
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
PRIVATE = Path.home() / "Projects" / "whu-study-private" / "scoring"
OUT = STUDY / "results"
FREEZE = "5d83e9b8025312923f3fb8ea2d5de3b47c212362"
SEED = int(FREEZE, 16)
B = 10_000
SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini"]
QUESTIONS = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"]
FRAME = {"WHU-S01": "Cochrane (health)", "WHU-S02": "Campbell", "WHU-S03": "IPCC AR6", "WHU-S04": "IPCC AR6"}
HEALTH = {"WHU-S01"}
# Reply folders read, replies<tag>/ and replies<tag>_repeat/ ("" is Stage 1's).
# Rows are kept for QUESTIONS only. The eight-question analysis
# (scripts/analyse_eight.py) sets QUESTIONS, FRAME, HEALTH and TAGS; the
# defaults are Stage 1's, so this script's own output is unchanged.
TAGS = ("",)
JUDGES = ["claude", "openai"]
REFUSED, INCOMPLETE, NVA, UNCITED = "REFUSED", "INCOMPLETE_SOURCES", "NOT_VERIFIABLE_ABSTRACT", "UNCITED"
M1_PASS = {"Supported"}
M1_FAIL = {"Overstates", "Understates", "Absent", "Wrong source", "Contradicted", UNCITED}
M1_EXCL = {"Unreachable", INCOMPLETE, NVA}
M2_PASS = {"Matches"}
M2_FAIL = {"Overstates", "Understates", "Contradicts", "Omits"}


def load_replies(run: Path, tag: str = "") -> dict:
    out = {}
    for j in JUDGES:
        d = run / ("replies" + tag) / j
        for f in sorted(d.glob("*.json")) if d.exists() else []:
            r = json.loads(f.read_text(encoding="utf-8"))
            out.setdefault(r["item"], {})[j] = r
    return out


def load_tagged(run: Path, repeat: bool = False) -> dict:
    out = {}
    for t in TAGS:
        out.update(load_replies(run, t + ("_repeat" if repeat else "")))
    return out


def usable(label, valid: set) -> str | None:
    return label if label in valid else None


def per_judge_labels(raw: dict, valid: set) -> dict:
    """judge -> the label counted for that judge, after the refusal rule."""
    own = {j: (raw.get(j) or {}).get("label") for j in JUDGES}
    out = {}
    for j in JUDGES:
        o = [k for k in JUDGES if k != j][0]
        lab = own[j]
        if lab == REFUSED or usable(lab, valid) is None:
            lab = own[o] if usable(own[o], valid) else None
        out[j] = lab
    return out


def score(lab, fail: set, ok: set):
    if lab in fail:
        return 1.0
    if lab in ok:
        return 0.0
    return None


def items_m1() -> list[dict]:
    run = PRIVATE / "m1"
    items = json.loads((run / "items.json").read_text(encoding="utf-8"))
    unc = json.loads((run / "uncited.json").read_text(encoding="utf-8"))
    km = json.loads((run / "key_map.json").read_text(encoding="utf-8"))
    first, rep = load_tagged(run), load_tagged(run, True)
    valid = M1_PASS | M1_FAIL | M1_EXCL
    rows = []
    items = [it for it in items if km[it["item"]]["question"] in QUESTIONS]
    unc = [it for it in unc if km[it["item"]]["question"] in QUESTIONS]
    for it in items:
        raw = first.get(it["item"], {})
        rows.append({"item": it["item"], **km[it["item"]], "raw": raw, "repeat": rep.get(it["item"], {}),
                     "labels": per_judge_labels(raw, valid), "uncited": False})
    for it in unc:
        rows.append({"item": it["item"], **km[it["item"]], "raw": {}, "repeat": {},
                     "labels": {j: UNCITED for j in JUDGES}, "uncited": True})
    return rows


def items_m2() -> list[dict]:
    run = PRIVATE / "m2"
    m2 = json.loads((run / "items.json").read_text(encoding="utf-8"))
    km = json.loads((run / "key_map.json").read_text(encoding="utf-8"))
    first, rep = load_tagged(run), load_tagged(run, True)
    valid = M2_PASS | M2_FAIL
    return [{"item": it["item"], **km[it["answer"]], "raw": first.get(it["item"], {}),
             "repeat": rep.get(it["item"], {}), "labels": per_judge_labels(first.get(it["item"], {}), valid),
             "uncited": False} for it in m2["items"] if km[it["answer"]]["question"] in QUESTIONS]


def agreed(r: dict) -> bool:
    if r["uncited"]:
        return True
    a = [(r["raw"].get(j) or {}).get("label") for j in JUDGES]
    if a[0] is None or a[0] != a[1] or a[0] in (REFUSED, INCOMPLETE):
        return False
    for j in JUDGES:
        if j in r["repeat"] and r["repeat"][j].get("label") != a[0]:
            return False
    return True


def view_scores(rows, fail, ok) -> dict:
    """view -> list of (question, system, score or None) per item."""
    out = {"combined": [], "claude_judge": [], "openai_judge": [], "agreed_only": []}
    for r in rows:
        s = {j: score(r["labels"][j], fail, ok) for j in JUDGES}
        got = [v for v in s.values() if v is not None]
        out["combined"].append((r["question"], r["system"], sum(got) / len(got) if got else None))
        out["claude_judge"].append((r["question"], r["system"], s["claude"]))
        out["openai_judge"].append((r["question"], r["system"], s["openai"]))
        out["agreed_only"].append((r["question"], r["system"], s["claude"] if agreed(r) else None))
    return out


def tallies(scores) -> dict:
    """(question, system) -> [failures, countable]."""
    t = {}
    for q, s, v in scores:
        x = t.setdefault((q, s), [0.0, 0])
        if v is not None:
            x[0] += v
            x[1] += 1
    return t


def rate(t, system, qs) -> float | None:
    f = sum(t.get((q, system), [0, 0])[0] for q in qs)
    n = sum(t.get((q, system), [0, 0])[1] for q in qs)
    return f / n if n else None


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def r4(x):
    return None if x is None else round(x, 4)


def analyse_view(scores) -> dict:
    t = tallies(scores)
    rng = random.Random(SEED)
    boots = []
    for _ in range(B):
        boots.append([rng.choice(QUESTIONS) for _ in QUESTIONS])
    out = {"systems": {}, "vs_whu": {}}
    for s in SYSTEMS:
        f = sum(t.get((q, s), [0, 0])[0] for q in QUESTIONS)
        n = sum(t.get((q, s), [0, 0])[1] for q in QUESTIONS)
        br = [v for v in (rate(t, s, qs) for qs in boots) if v is not None]
        out["systems"][s] = {"failures": r4(f), "countable": n, "rate": r4(f / n if n else None),
                             "ci95": [r4(pct(br, 0.025)), r4(pct(br, 0.975))],
                             "per_question": {q: {"failures": r4(t.get((q, s), [0, 0])[0]),
                                                  "countable": t.get((q, s), [0, 0])[1],
                                                  "rate": r4(rate(t, s, [q]))} for q in QUESTIONS},
                             "health": r4(rate(t, s, sorted(HEALTH))),
                             "non_health": r4(rate(t, s, [q for q in QUESTIONS if q not in HEALTH]))}
    w = out["systems"]["WHU"]["rate"]
    for s in SYSTEMS[1:]:
        diffs, ratios = [], []
        for qs in boots:
            a, b = rate(t, "WHU", qs), rate(t, s, qs)
            if a is None or b is None:
                continue
            diffs.append(a - b)
            if b > 0:
                ratios.append(a / b)
        o = out["systems"][s]["rate"]
        d_ci = [r4(pct(diffs, 0.025)), r4(pct(diffs, 0.975))]
        half = (w is not None and o is not None and w <= 0.5 * o)
        excl = d_ci[0] is not None and (d_ci[1] < 0 or d_ci[0] > 0)
        out["vs_whu"][s] = {"difference_whu_minus": r4(None if w is None or o is None else w - o), "difference_ci95": d_ci,
                            "ratio_whu_over": r4(w / o if w is not None and o else None),
                            "ratio_ci95": [r4(pct(ratios, 0.025)), r4(pct(ratios, 0.975))],
                            "whu_at_most_half": half, "difference_ci_excludes_zero": excl,
                            "holds": bool(half and excl and d_ci[1] < 0)}
    return out


def kappa(pairs) -> float | None:
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    labs = {x for p in pairs for x in p}
    pe = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labs)
    return None if pe == 1 else (po - pe) / (1 - pe)


def judge_stats(rows, fail) -> dict:
    out = {}
    for s in SYSTEMS + ["all"]:
        rs = [r for r in rows if not r["uncited"] and (s == "all" or r["system"] == s)]
        judged = [r for r in rs if all((r["raw"].get(j) or {}).get("label") not in (None, INCOMPLETE) for j in JUDGES)]
        both = [r for r in judged if all((r["raw"][j]["label"] not in (REFUSED,)) for j in JUDGES)]
        pairs = [(r["raw"]["claude"]["label"], r["raw"]["openai"]["label"]) for r in both]
        st = {"items": len(rs), "judged_by_both": len(judged),
              "same_label": sum(a == b for a, b in pairs), "labelled_by_both": len(pairs),
              "same_label_share": r4(sum(a == b for a, b in pairs) / len(pairs) if pairs else None),
              "same_failure_or_pass_share": r4(sum((a in fail) == (b in fail) for a, b in pairs) / len(pairs)
                                               if pairs else None),
              "kappa": r4(kappa(pairs)),
              "agreed_by_protocol_rule": sum(agreed(r) for r in judged)}
        for j in JUDGES:
            rj = [r["raw"][j] for r in rs if j in r["raw"] and r["raw"][j].get("label") != INCOMPLETE]
            first_ref = sum(bool(x.get("attempts")) and x["attempts"][0].get("refused") for x in rj)
            st["refusal_" + j] = {"calls": len(rj), "refused_first_attempt": first_ref,
                                  "refused_after_retry": sum(x.get("label") == REFUSED for x in rj),
                                  "rate_after_retry": r4(sum(x.get("label") == REFUSED for x in rj) / len(rj) if rj else None),
                                  "unusable_reply": sum(x.get("label") not in (REFUSED,) and not x.get("judge_label")
                                                        for x in rj)}
            reps = [(r["raw"][j]["label"], r["repeat"][j]["label"]) for r in rs if j in r["repeat"] and j in r["raw"]]
            st["second_read_" + j] = {"pairs": len(reps), "same_label": sum(a == b for a, b in reps),
                                      "same_label_share": r4(sum(a == b for a, b in reps) / len(reps) if reps else None)}
        out[s] = st
    return out


def directions(rows, labels) -> dict:
    out = {}
    for s in SYSTEMS:
        for j in JUDGES:
            c = {}
            for r in rows:
                if r["system"] == s and r["labels"][j] in labels:
                    c[r["labels"][j]] = c.get(r["labels"][j], 0) + 1
            out.setdefault(s, {})[j] = {l: c.get(l, 0) for l in labels}
    return out


def label_counts(rows) -> dict:
    out = {}
    for s in SYSTEMS:
        for j in JUDGES:
            c = {}
            for r in rows:
                if r["system"] != s:
                    continue
                l = (r["raw"].get(j) or {}).get("label") or (UNCITED if r["uncited"] else "none")
                c[l] = c.get(l, 0) + 1
            out.setdefault(s, {})[j] = dict(sorted(c.items()))
    return out


def review_list(rows, measure: str) -> list[dict]:
    out = []
    for r in rows:
        if r["uncited"]:
            continue
        why = []
        labs = {j: (r["raw"].get(j) or {}).get("label") for j in JUDGES}
        if measure == "M1" and not r["raw"]:
            why.append("no cited source held (not sent to a judge)")
        elif INCOMPLETE in labs.values():
            why.append("source held but not delivered whole (INCOMPLETE_SOURCES)" if undelivered(r)
                       else "source not held (INCOMPLETE_SOURCES)")
        if REFUSED in labs.values():
            why.append("refused after one unchanged retry")
        if r["raw"] and any(l is None for l in labs.values()) or any(
                (r["raw"].get(j) or {}).get("label") not in (REFUSED, INCOMPLETE) and not (r["raw"].get(j) or {}).get("judge_label")
                for j in JUDGES if j in r["raw"]):
            why.append("missing or unusable reply")
        if not why and not agreed(r):
            why.append("judges disagree" if labs["claude"] != labs["openai"] else "second read changed")
        if measure == "M2" and "Contradicts" in labs.values():
            why.append("possible key dispute (a judge says Contradicts)")
        if why:
            out.append({"item": r["item"], "measure": measure, "reasons": why})
    flagged = {x["item"] for x in out}
    for s in SYSTEMS:
        pool = sorted(r["item"] for r in rows if r["system"] == s and not r["uncited"]
                      and r["item"] not in flagged and agreed(r))
        k = round(0.2 * len(pool))
        for i in sorted(random.Random("%d/human-audit/%s/%s" % (SEED, measure, s)).sample(pool, k)) if k else []:
            out.append({"item": i, "measure": measure, "reasons": ["random 20% audit of agreed items"]})
    return out


def spend() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("spend_ledger_an", STUDY.parents[1] / "backend" / "scripts" / "spend_ledger.py")
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    rows = [e for e in S.entries() if (e.get("issue") or "").startswith("whu-reliability-judging")]
    by = {}
    for e in rows:
        k = (e.get("role") or "?")
        by[k] = round(by.get(k, 0.0) + float(e.get("usd") or 0), 4)
    return {"usd": round(sum(float(e.get("usd") or 0) for e in rows), 2), "calls": len(rows), "by_role": by}


def undelivered(r: dict) -> bool:
    """INCOMPLETE_SOURCES because the runner could not pass a held source on
    whole (its delivery check), not because a cited source was not held."""
    return any((r["raw"].get(j) or {}).get("undelivered_sources")
               and not (r["raw"].get(j) or {}).get("unreachable_sources") for j in JUDGES)


def build() -> tuple[dict, list]:
    """The result and the human-review list for QUESTIONS (no file written)."""
    m1, m2 = items_m1(), items_m2()
    v1, v2 = view_scores(m1, M1_FAIL, M1_PASS), view_scores(m2, M2_FAIL, M2_PASS)
    cited_only = view_scores([r for r in m1 if not r["uncited"]], M1_FAIL, M1_PASS)
    counts_m1 = {}
    for s in SYSTEMS:
        rs = [r for r in m1 if r["system"] == s]
        lab = lambda r: {(r["raw"].get(j) or {}).get("label") for j in JUDGES}
        counts_m1[s] = {"drawn": len(rs), "uncited": sum(r["uncited"] for r in rs),
                        "cited": sum(not r["uncited"] for r in rs),
                        # No cited source held: the runner sends no judge and writes no reply.
                        "no_source_held": sum(not r["uncited"] and not r["raw"] for r in rs),
                        "incomplete_sources_unreachable": sum(INCOMPLETE in lab(r) and not undelivered(r) for r in rs),
                        # A source held but too long to pass on whole: the chunk sent would
                        # have left out a key word of the claim, so it was not judged.
                        "incomplete_sources_undelivered": sum(INCOMPLETE in lab(r) and undelivered(r) for r in rs),
                        "judge_said_unreachable_any": sum("Unreachable" in lab(r) for r in rs),
                        "not_verifiable_abstract_any": sum(NVA in lab(r) for r in rs)}
        d = counts_m1[s]
        d["unreachable_share_of_cited"] = r4((d["no_source_held"] + d["incomplete_sources_unreachable"]
                                              + d["judge_said_unreachable_any"])
                                             / d["cited"] if d["cited"] else None)
        d["flag_unreachable_over_20pct"] = bool(d["unreachable_share_of_cited"] and d["unreachable_share_of_cited"] > 0.2)
        d["not_verifiable_share_of_cited"] = r4(d["not_verifiable_abstract_any"] / d["cited"] if d["cited"] else None)
        d["flag_not_verifiable_over_20pct"] = bool(d["not_verifiable_share_of_cited"] and d["not_verifiable_share_of_cited"] > 0.2)
    reach = json.loads((STUDY / "scoring" / "snapshot_counts.json").read_text())["reachability"]
    review = review_list(m1, "M1") + review_list(m2, "M2")
    res = {
        "written": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": "Stage 1: AI judges only, not yet checked by people",
        "rules": "scripts/analyse.py docstring (committed before any result was read)",
        "seed": str(SEED), "bootstrap_resamples": B, "frames": FRAME, "health_questions": sorted(HEALTH),
        "M1_citation_support": {
            "counts": counts_m1,
            "views": {k: analyse_view(v) for k, v in v1.items()},
            "cited_items_only_combined": analyse_view(cited_only["combined"]),
            "uncited_rate": {s: r4(counts_m1[s]["uncited"] / counts_m1[s]["drawn"]) for s in SYSTEMS},
            "judges": judge_stats(m1, M1_FAIL),
            "label_counts_first_read": label_counts(m1),
            "direction_of_failures": directions(m1, ["Overstates", "Understates"]),
        },
        "M2_conclusion_calibration": {
            "items_per_system": {s: sum(r["system"] == s for r in m2) for s in SYSTEMS},
            "views": {k: analyse_view(v) for k, v in v2.items()},
            "judges": judge_stats(m2, M2_FAIL),
            "label_counts_first_read": label_counts(m2),
            "direction_of_failures": directions(m2, ["Overstates", "Understates"]),
            "possible_key_disputes": sum(1 for r in m2 if "Contradicts" in
                                         {(r["raw"].get(j) or {}).get("label") for j in JUDGES}),
        },
        "citation_reachability": reach,
        "human_review": {"items": len(review), "by_measure": {m: sum(x["measure"] == m for x in review) for m in ("M1", "M2")},
                         "by_reason": {}},
        "judging_spend": spend(),
    }
    for x in review:
        for w in x["reasons"]:
            res["human_review"]["by_reason"][w] = res["human_review"]["by_reason"].get(w, 0) + 1
    for m, key in (("H1", "M1_citation_support"), ("H2", "M2_conclusion_calibration")):
        res[m] = {view: res[key]["views"][view]["vs_whu"]["Claude"]["holds"] for view in res[key]["views"]}
    return res, review


def main() -> int:
    res, review = build()
    (PRIVATE / "human_review.json").write_text(json.dumps(review, indent=1), encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stage1_ai_only.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("H1", res["H1"], "H2", res["H2"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
