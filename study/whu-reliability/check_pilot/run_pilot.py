#!/usr/bin/env python3
"""The check-an-answer pilot: sample, estimate, run, compare.

    run_pilot.py draw                 the 8 answers (free)
    run_pilot.py prepare              adapt, claims, licences, snapshots, count_tokens; prints
                                      the worst-case estimate (free; no model call)
    run_pilot.py run --cap 35         PAID: Claude judge, first read, on ledger issue
                                      whu-check-pilot; STOPs if the estimate is over the cap,
                                      and before any call that would pass the cap or caps.json
    run_pilot.py compare              agreement with the study's Claude first-read labels,
                                      COULDN'T CHECK share, dollars per answer (free)

Design and the pass bar: docs/whu-check-an-answer-pilot.md (fixed before this code).
Private outputs (answer text): ~/Projects/whu-study-private/check_pilot/. Committed: counts
only, study/whu-reliability/check_pilot/pilot_counts.json.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline as P  # noqa: E402

J, S = P.J, P.S
PRIVATE = Path.home() / "Projects" / "whu-study-private"
SCORING = PRIVATE / "scoring"
OUT = PRIVATE / "check_pilot"
COUNTS = HERE / "pilot_counts.json"
ISSUE = "whu-check-pilot"
SEED = int(J.FREEZE_COMMIT, 16)
QUESTIONS = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"]
SYSTEMS = ["Claude", "ChatGPT", "Gemini", "Perplexity"]
PASS_AGREEMENT, PASS_COULDNT, PASS_USD = 0.90, 0.20, 5.00


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def draw() -> list[tuple[str, str]]:
    rng = random.Random("%d/check-pilot" % SEED)
    return [(q, s) for s in SYSTEMS for q in sorted(rng.sample(QUESTIONS, 2))]


def capture(q: str, s: str) -> tuple[str, str]:
    """(the answer as captured, its format), as prepare_scoring.tool_answer read it."""
    d = PRIVATE / "answers" / q
    if s == "Gemini" and q in ("WHU-S03", "WHU-S04"):
        return (d / "gemini.raw.html").read_text(encoding="utf-8"), "gemini_html"
    md = (d / (s.lower() + ".md")).read_text(encoding="utf-8")
    fmt = {"Claude": "report_section", "Perplexity": "perplexity_sources",
           "ChatGPT": "chatgpt_lenticular" if q in ("WHU-S01", "WHU-S02") else "chatgpt_bracketed",
           "Gemini": "gemini_works_cited"}[s]
    return md, fmt


def work(q: str, s: str) -> Path:
    return OUT / ("%s-%s" % (q, s))


def clients():
    import anthropic
    keys = J.env_keys()
    raw = anthropic.Anthropic(api_key=keys["ANTHROPIC_API_KEY"])
    return raw, S.metered(raw, script="study/whu-reliability/check_pilot/run_pilot.py", issue=ISSUE,
                          role="check-pilot-claude")


def strip(planned: list[dict]) -> list[dict]:
    return [{k: v for k, v in p.items() if k not in ("docs", "prefix", "rest")} for p in planned]


def do_prepare(_a) -> int:
    raw, _ = clients()
    count = P.count_tokens_fn(raw)
    total, rows = 0.0, []
    for q, s in draw():
        text, fmt = capture(q, s)
        w = work(q, s)
        prep = P.prepare(text, w, fmt=fmt, count=count, system=s)
        (w / "prepared.json").write_text(json.dumps({
            "question": q, "system": s, "format": prep["format"], "at": now(),
            "claims": strip(prep["planned"]), "beyond_limit": [c["idx"] for c in prep["beyond_limit"]],
            "worst_usd": prep["worst_usd"], "calls": prep["calls"]}, indent=1, ensure_ascii=False, default=str))
        lab = Counter(p["label"] or "to judge" for p in prep["planned"])
        total += prep["worst_usd"]
        rows.append((q, s, len(prep["claims"]), len(prep["beyond_limit"]), dict(lab), prep["worst_usd"]))
        print("  %s %-10s %2d claims (+%d beyond 40)  %s  worst $%.2f" % (q, s, *rows[-1][2:4], dict(lab), prep["worst_usd"]))
    (OUT / "estimate.json").write_text(json.dumps({"at": now(), "worst_usd": round(total, 4), "rows": rows}, indent=1))
    print("ESTIMATE (worst case, judge_m1's formula): $%.2f for %d answers" % (total, len(rows)))
    return 0


def do_run(a) -> int:
    est = json.loads((OUT / "estimate.json").read_text())
    print("ESTIMATE: $%.2f (from %s); cap $%.2f on %s" % (est["worst_usd"], est["at"], a.cap, ISSUE))
    if est["worst_usd"] > a.cap:
        print("STOP: the estimate is over the cap; nothing was called")
        return 3
    P.prompt_ok()
    raw, client = clients()
    count = P.count_tokens_fn(raw)

    def before_call(worst: float) -> None:
        S.check_cap(ISSUE, worst)                      # caps.json: the day cap and the issue cap
        so_far = S.spent(issue=ISSUE)
        if so_far + worst > a.cap:
            raise P.Stop("%s has spent $%.3f of $%.2f; the next call could cost up to $%.3f"
                         % (ISSUE, so_far, a.cap, worst))

    for q, s in draw():
        w = work(q, s)
        res_f = w / "results.json"
        if res_f.exists():
            print("  %s %-10s already run; kept" % (q, s))
            continue
        text, fmt = capture(q, s)
        prep = P.prepare(text, w, fmt=fmt, count=count, system=s)
        try:
            results = P.judge(prep["planned"], client, before_call)
        except (S.OverCap, P.Stop) as e:
            print("STOP before a call on %s %s: %s" % (q, s, e))
            return 3
        res_f.write_text(json.dumps({"question": q, "system": s, "at": now(), "format": prep["format"],
                                     "results": results, "totals": P.totals(results)},
                                    indent=1, ensure_ascii=False, default=str))
        print("  %s %-10s %s" % (q, s, P.totals(results)))
    print("%s spent: $%.4f" % (ISSUE, S.spent(issue=ISSUE)))
    return 0


def study_labels(q: str, s: str) -> tuple[dict[int, str], dict[int, str]]:
    """({sentence idx: the study's Claude first-read label or UNCITED / NO_SOURCE_HELD},
    {idx: the study's sentence text})."""
    base = SCORING / ("perplexity" if s == "Perplexity" else "") / "m1"
    blinded = SCORING / ("perplexity" if s == "Perplexity" else "") / "blinded" / q
    km = json.loads((base / "key_map.json").read_text())
    uncited = {r["item"] for r in json.loads((base / "uncited.json").read_text())}
    out = {}
    for item, k in km.items():
        if k["question"] != q or k["system"] != s:
            continue
        idx = int(k["sentence"].rsplit("/", 1)[1])
        f = base / "replies" / "claude" / (item + ".json")
        out[idx] = ("UNCITED" if item in uncited else
                    json.loads(f.read_text())["label"] if f.exists() else "NO_SOURCE_HELD")
    texts = {}
    for line in (blinded / ("%s.sentences.jsonl" % s.lower())).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        texts[r["idx"]] = r["text"]
    return out, texts


def do_compare(_a) -> int:
    pairs, cc_reasons, per_answer, sentence_mismatch = [], Counter(), [], []
    all_claims = 0
    for q, s in draw():
        res = json.loads((work(q, s) / "results.json").read_text())
        study, texts = study_labels(q, s)
        mine = {r["idx"]: r for r in res["results"]}
        by_text = {t: i for i, t in texts.items()}
        for r in res["results"]:
            if texts.get(r["idx"]) != r["claim"]:
                sentence_mismatch.append("%s/%s/%d" % (q, s, r["idx"]))
            if r["label"] == P.COULDNT:
                why = r["reason"]
                cc_reasons[("no open licence" if "no open-licence copy" in why else
                            "abstract only" if "abstract" in why else
                            "delivery check" if "key word" in why or "delivered" in why else
                            "refused" if "refused" in why else "unparsed" if "did not parse" in why else
                            "not retrieved")] += 1
        all_claims += len(res["results"])
        for idx, lab in study.items():
            t = texts.get(idx)
            r = mine.get(idx) if mine.get(idx, {}).get("claim") == t else mine.get(by_text.get(t, -1))
            if r is None:
                r = next((x for x in res["results"] if x["claim"] == t), None)
            if r is None:
                continue                      # drawn by the study, beyond the pilot's 40 claims
            pairs.append({"answer": "%s/%s" % (q, s), "idx": idx, "study": P.study_label_to_check(lab),
                          "study_raw": lab, "pilot": r["label"]})
        per_answer.append({"answer": "%s/%s" % (q, s), "claims": len(res["results"]), **res["totals"]})
    both = [p for p in pairs if P.COULDNT not in (p["study"], p["pilot"])]
    agree = sum(p["study"] == p["pilot"] for p in both)
    cited = [p for p in both if P.NO_SOURCE not in (p["study"], p["pilot"])]
    table = Counter((p["study"], p["pilot"]) for p in pairs)
    cc = sum(a[P.COULDNT] for a in per_answer)
    usd = S.spent(issue=ISSUE)
    out = {
        "written": now(), "by": "study/whu-reliability/check_pilot/run_pilot.py compare",
        "label": "Counts only. Internal pilot, exploratory, outside H1/H2; judged by an AI model (Claude) only.",
        "design": "docs/whu-check-an-answer-pilot.md", "ledger_issue": ISSUE,
        "sample": ["%s/%s" % x for x in draw()],
        "sentence_text_mismatches": sentence_mismatch,
        "agreement": {"n": len(both), "agree": agree, "share": round(agree / len(both), 4) if both else None,
                      "rule": "sentences the study drew and the pilot checked, neither COULDN'T CHECK"},
        "agreement_counting_couldnt_check": {"n": len(pairs), "agree": sum(p["study"] == p["pilot"] for p in pairs)},
        "agreement_cited_only": {"n": len(cited), "agree": sum(p["study"] == p["pilot"] for p in cited)},
        "study_vs_pilot": {"%s -> %s" % k: v for k, v in sorted(table.items())},
        "couldnt_check": {"n": cc, "of": all_claims, "share": round(cc / all_claims, 4) if all_claims else None,
                          "reasons": dict(cc_reasons)},
        "usd": {"total": round(usd, 4), "per_answer": round(usd / len(per_answer), 4)},
        "per_answer": per_answer,
    }
    a1 = out["agreement"]["share"]
    out["pass_bar"] = {
        "agreement_at_least_90": a1 is not None and a1 >= PASS_AGREEMENT,
        "couldnt_check_at_most_20": out["couldnt_check"]["share"] is not None and out["couldnt_check"]["share"] <= PASS_COULDNT,
        "usd_per_answer_at_most_5": out["usd"]["per_answer"] <= PASS_USD}
    out["pass"] = all(out["pass_bar"].values())
    (OUT / "pairs.json").write_text(json.dumps(pairs, indent=1))
    COUNTS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draw", "prepare", "run", "compare"])
    ap.add_argument("--cap", type=float, default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "draw":
        for x in draw():
            print("%s %s" % x)
        return 0
    if a.cmd == "prepare":
        return do_prepare(a)
    if a.cmd == "run":
        if a.cap is None:
            print("STOP: run needs --cap")
            return 2
        return do_run(a)
    return do_compare(a)


if __name__ == "__main__":
    raise SystemExit(main())
