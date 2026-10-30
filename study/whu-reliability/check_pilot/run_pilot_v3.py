#!/usr/bin/env python3
"""The check-an-answer pilot, v3 (docs/whu-check-an-answer-pilot.md §10).

    run_pilot_v3.py draw                 the primary sample (round 1) and the secondary (v2's 8)
    run_pilot_v3.py prepare              free: copies, plans, count_tokens; prints the worst-case
                                         estimate for each sample
    run_pilot_v3.py run --cap 35         PAID, ledger issue whu-check-pilot-v3: the primary, then the
                                         secondary only if both estimates together fit the cap
    run_pilot_v3.py compare              counts against §10.7's bars (primary) and v2 against v3 on
                                         the same input (secondary)

Private outputs: ~/Projects/whu-study-private/check_pilot_v3/{primary,secondary}/. Committed: counts only,
check_pilot/pilot_v3_counts.json and pilot_v3_secondary_counts.json.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import threading
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline as V1  # noqa: E402
import pipeline_v3 as P  # noqa: E402
import run_pilot as R  # noqa: E402
import run_pilot_v2 as R2  # noqa: E402  (sets R's v2 globals; only R.capture / R.study_labels are used)

J, S = P.J, P.S
ISSUE = "whu-check-pilot-v3"
SCRIPT = "study/whu-reliability/check_pilot/run_pilot_v3.py"
OUT = R.PRIVATE / "check_pilot_v3"
V2_OUT = R.PRIVATE / "check_pilot_v2"
R1_ANSWERS = R.PRIVATE / "answers" / "quarterly" / "round1"
R1_SCORING = R.PRIVATE / "scoring" / "quarterly" / "round1"
R1_FREEZE = "5f4a928b757d7f47c1ba8ed47600ced4a7a69f12"
R1_QUESTIONS = ["WHU-Q1-01", "WHU-Q1-02", "WHU-Q1-03", "WHU-Q1-04"]
R1_NO_ANSWER = {("WHU-Q1-04", "Gemini")}
R1_PPLX_REPORT = {"WHU-Q1-03", "WHU-Q1-04"}
PRIMARY_K = (("Claude", 3), ("Perplexity", 3), ("Gemini", 2))
PASS_COULDNT, PASS_AGREEMENT, PASS_USD, PASS_SECONDS, PASS_PASSAGES = 0.20, 0.90, 2.00, 120.0, 1.0
COUNTS = {"primary": HERE / "pilot_v3_counts.json", "secondary": HERE / "pilot_v3_secondary_counts.json"}


def draw_primary() -> list[tuple[str, str]]:
    """§10.8: 3 Claude, 3 Perplexity, 2 Gemini from round 1; one generator, systems in that order."""
    rng = random.Random("%d/check-pilot-v3" % int(R1_FREEZE, 16))
    out = []
    for s, k in PRIMARY_K:
        qs = [q for q in R1_QUESTIONS if (q, s) not in R1_NO_ANSWER]
        out += [(q, s) for q in sorted(rng.sample(qs, k))]
    return out


def draw_secondary() -> list[tuple[str, str]]:
    return R2.draw()


SAMPLES = {"primary": draw_primary, "secondary": draw_secondary}


def capture(sample: str, q: str, s: str) -> tuple[str, str]:
    if sample == "secondary":
        return R.capture(q, s)
    md = (R1_ANSWERS / q / (s.lower() + ".md")).read_text(encoding="utf-8")
    fmt = {"Claude": "claude_sources_r1", "Gemini": "gemini_works_cited",
           "Perplexity": "perplexity_sources" if q in R1_PPLX_REPORT else "perplexity_footnotes"}[s]
    return md, fmt


def work(sample: str, q: str, s: str) -> Path:
    return OUT / sample / ("%s-%s" % (q, s))


def clients(role: str):
    import anthropic
    raw = anthropic.Anthropic(api_key=J.env_keys()["ANTHROPIC_API_KEY"])
    return raw, S.metered(raw, script=SCRIPT, issue=ISSUE, role=role)


def spent(role: str | None = None) -> float:
    return sum(e.get("usd") or 0 for e in S.entries()
               if e.get("issue") == ISSUE and (role is None or e.get("role") == role))


def do_prepare(_a) -> int:
    raw, _ = clients("check-pilot-v3-prepare")
    count = V1.count_tokens_fn(raw)
    est = {"at": R.now()}
    for sample, dr in SAMPLES.items():
        total, rows = 0.0, []
        for q, s in dr():
            text, fmt = capture(sample, q, s)
            w = work(sample, q, s)
            prep = P.prepare(text, w, fmt=fmt, count=count, system=s)
            (w / "prepared.json").write_text(json.dumps({
                "question": q, "system": s, "format": prep["format"], "at": R.now(), "found": prep["found"],
                "claims": R.strip(prep["planned"]), "beyond_limit": [c["idx"] for c in prep["beyond_limit"]],
                "worst_usd": prep["worst_usd"], "calls": prep["calls"]}, indent=1, ensure_ascii=False, default=str))
            why = Counter(P._reason_kind(p, prep["manifest"]) for p in prep["planned"] if p["label"] == P.COULDNT)
            rules = Counter(m.get("rule") or m.get("why_kind") for m in prep["manifest"].values())
            total += prep["worst_usd"]
            rows.append({"answer": "%s/%s" % (q, s), "claims": len(prep["claims"]), "found": prep["found"],
                         "calls": prep["calls"], "worst_usd": prep["worst_usd"], "couldnt": dict(why),
                         "sources": dict(rules)})
            print("  %-9s %s %-10s %2d of %2d claims, %2d calls, worst $%.2f  COULDN'T %s" % (
                sample, q, s, len(prep["claims"]), prep["found"], prep["calls"], prep["worst_usd"], dict(why)))
        est[sample] = {"worst_usd": round(total, 4), "rows": rows}
        print("ESTIMATE %s (worst case, judge_m1's formula): $%.2f" % (sample, total))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "estimate.json").write_text(json.dumps(est, indent=1))
    return 0


def do_run(a) -> int:
    est = json.loads((OUT / "estimate.json").read_text())
    p_, s_ = est["primary"]["worst_usd"], est["secondary"]["worst_usd"]
    print("ESTIMATE: primary $%.2f, secondary $%.2f (from %s); cap $%.2f on %s" % (p_, s_, est["at"], a.cap, ISSUE))
    if p_ > a.cap:
        print("STOP: the primary's estimate is over the cap; nothing was called")
        return 3
    samples = ["primary"] + (["secondary"] if p_ + s_ <= a.cap else [])
    if len(samples) == 1:
        print("primary only: primary + secondary ($%.2f) is over the cap" % (p_ + s_))
    V1.prompt_ok()
    base, reserved, lock = spent(), [0.0], threading.Lock()

    def before_call(worst: float) -> None:
        S.check_cap(ISSUE, worst)                      # caps.json: the $25 day cap and the issue cap
        with lock:
            if base + reserved[0] + worst > a.cap:
                raise P.Stop("%s: $%.3f spent before this run + $%.3f reserved; the next call could cost up to $%.3f"
                             " (cap $%.2f)" % (ISSUE, base, reserved[0], worst, a.cap))
            reserved[0] += worst

    for sample in samples:
        raw, client = clients("check-pilot-v3-" + sample)
        count = V1.count_tokens_fn(raw)
        for q, s in SAMPLES[sample]():
            w = work(sample, q, s)
            res_f = w / "results.json"
            if res_f.exists():
                print("  %s %s %-10s already run; kept" % (sample, q, s))
                continue
            text, fmt = capture(sample, q, s)
            try:
                out = P.check(text, w, client, count, fmt=fmt, system=s, before_call=before_call)
            except (S.OverCap, P.Stop) as e:
                print("STOP before a call on %s %s %s: %s" % (sample, q, s, e))
                return 3
            res_f.write_text(json.dumps({"question": q, "system": s, "at": R.now(), "format": out["format"],
                                         "found": out["found"], "seconds": out["seconds"], "summary": out["summary"],
                                         "results": out["results"], "totals": V1.totals(out["results"])},
                                        indent=1, ensure_ascii=False, default=str))
            print("  %s %s %-10s %5.0f s  %s" % (sample, q, s, out["seconds"], out["summary"]))
    print("%s spent: $%.4f (primary $%.4f, secondary $%.4f)" % (ISSUE, spent(), spent("check-pilot-v3-primary"),
                                                                spent("check-pilot-v3-secondary")))
    return 0


def study_labels_r1(q: str, s: str) -> tuple[dict[int, str], dict[int, str]]:
    """Round 1's Claude-judge first reads (replies/claude, not replies_repeat), as R.study_labels reads the study's."""
    base = R1_SCORING / "m1"
    km = json.loads((base / "key_map.json").read_text())
    uncited = {r["item"] for r in json.loads((base / "uncited.json").read_text())}
    out = {}
    for item, k in km.items():
        if k["question"] != q or k["system"] != s:
            continue
        idx = int(k["sentence"].rsplit("/", 1)[1])
        f = base / "replies" / "claude" / (item + ".json")
        out[idx] = ("UNCITED" if item in uncited else json.loads(f.read_text())["label"] if f.exists()
                    else "NO_SOURCE_HELD")
    texts = {}
    for line in (R1_SCORING / "blinded" / q / ("%s.sentences.jsonl" % s.lower())).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        texts[r["idx"]] = r["text"]
    return out, texts


def compare(sample: str) -> dict:
    judged = (P.BACKED, P.NOT_BACKED)
    pairs, reasons, per_answer, mismatch, rules = [], Counter(), [], [], Counter()
    v2_table, n_claims = Counter(), 0
    for q, s in SAMPLES[sample]():
        w = work(sample, q, s)
        res = json.loads((w / "results.json").read_text())
        man = {m["url"]: m for m in json.loads((w / "sources" / "manifest.json").read_text())}
        rules.update(m.get("rule") or ("refused: " + (m.get("why_kind") or "?")) for m in man.values())
        study, texts = (study_labels_r1 if sample == "primary" else R.study_labels)(q, s)
        mine = {r["idx"]: r for r in res["results"]}
        for r in res["results"]:
            if r["idx"] in texts and texts[r["idx"]] != r["claim"]:
                mismatch.append("%s/%s/%d" % (q, s, r["idx"]))
            if r["label"] == P.COULDNT:
                reasons[r.get("reason_kind") or "?"] += 1
        n_claims += len(res["results"])
        by_text = {r["claim"]: r for r in res["results"]}
        for idx, lab in study.items():
            r = mine.get(idx) if mine.get(idx, {}).get("claim") == texts.get(idx) else by_text.get(texts.get(idx))
            if r is not None:
                pairs.append({"answer": "%s/%s" % (q, s), "idx": idx, "study": V1.study_label_to_check(lab),
                              "study_raw": lab, "pilot": r["label"], "kind": r.get("kind")})
        if sample == "secondary":
            v2 = {r["idx"]: r["label"] for r in json.loads((V2_OUT / ("%s-%s" % (q, s)) / "results.json").read_text())["results"]}
            v2_table.update("%s -> %s" % (v2[i], mine[i]["label"]) for i in mine if i in v2)
        rs = res["results"]
        per_answer.append({"answer": "%s/%s" % (q, s), "found": res["found"], **V1.totals(rs),
                           "abstract_only": sum(r.get("kind") == P.ABSTRACT_ONLY for r in rs),
                           "seconds": res["seconds"]})
    both = [p for p in pairs if p["study"] in judged and p["pilot"] in judged]
    agree = sum(p["study"] == p["pilot"] for p in both)
    v1style = [p for p in pairs if P.COULDNT not in (p["study"], p["pilot"])]
    verdicts = sum(a[P.BACKED] + a[P.NOT_BACKED] for a in per_answer)
    with_passage = 0
    for q, s in SAMPLES[sample]():
        for r in json.loads((work(sample, q, s) / "results.json").read_text())["results"]:
            if r["label"] in judged and (r.get("passage") or {}).get("quote") and (r["passage"]["words"] < 60):
                with_passage += 1
    cc = sum(a[P.COULDNT] for a in per_answer)
    secs = [a["seconds"] for a in per_answer]
    usd = spent("check-pilot-v3-" + sample)
    out = {
        "written": R.now(), "by": SCRIPT + " compare",
        "label": "Counts only. Internal pilot, exploratory, outside H1/H2; judged by an AI model (Claude) only.",
        "design": "docs/whu-check-an-answer-pilot.md §10", "ledger_issue": ISSUE, "sample_kind": sample,
        "sample": ["%s/%s" % x for x in SAMPLES[sample]()],
        "sentence_text_mismatches": mismatch,
        "agreement": {"n": len(both), "agree": agree, "share": round(agree / len(both), 4) if both else None,
                      "rule": "sentences the study drew and the pilot checked, both BACKED or NOT BACKED"},
        "agreement_v1_rule": {"n": len(v1style), "agree": sum(p["study"] == p["pilot"] for p in v1style)},
        "agreement_abstract_only": {"n": sum(p["kind"] == P.ABSTRACT_ONLY for p in both),
                                    "agree": sum(p["kind"] == P.ABSTRACT_ONLY and p["study"] == p["pilot"] for p in both)},
        "study_vs_pilot": {"%s -> %s" % k: v for k, v in sorted(Counter((p["study"], p["pilot"]) for p in pairs).items())},
        "couldnt_check": {"n": cc, "of": n_claims, "share": round(cc / n_claims, 4) if n_claims else None,
                          "reasons": dict(reasons.most_common())},
        "abstract_only": {"n": sum(a["abstract_only"] for a in per_answer), "of": n_claims},
        "passages": {"verdicts": verdicts, "with_passage": with_passage,
                     "share": round(with_passage / verdicts, 4) if verdicts else None},
        "sources_by_rule": dict(rules.most_common()),
        "usd": {"total": round(usd, 4), "per_answer": round(usd / len(per_answer), 4)},
        "seconds": {"mean": round(sum(secs) / len(secs), 1), "max": max(secs)},
        "per_answer": per_answer,
    }
    if sample == "primary":
        a1, c1 = out["agreement"]["share"], out["couldnt_check"]["share"]
        out["pass_bar"] = {
            "couldnt_check_at_most_20": c1 is not None and c1 <= PASS_COULDNT,
            "agreement_at_least_90": a1 is not None and a1 >= PASS_AGREEMENT,
            "usd_per_answer_at_most_2": out["usd"]["per_answer"] <= PASS_USD,
            "seconds_per_answer_mean_at_most_120": out["seconds"]["mean"] <= PASS_SECONDS,
            "passages_100": out["passages"]["share"] in (None, PASS_PASSAGES) and out["passages"]["share"] is not None}
        out["pass"] = all(out["pass_bar"].values())
    else:
        out["v2_vs_v3_same_sentence"] = dict(sorted(v2_table.items()))
        out["v2_counts"] = "pilot_v2_counts.json"
    (OUT / sample / "pairs.json").write_text(json.dumps(pairs, indent=1))
    COUNTS[sample].write_text(json.dumps(out, indent=1) + "\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["draw", "prepare", "run", "compare"])
    ap.add_argument("--cap", type=float, default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "draw":
        for sample, dr in SAMPLES.items():
            for x in dr():
                print("%-9s %s %s" % (sample, *x))
        return 0
    if a.cmd == "prepare":
        return do_prepare(a)
    if a.cmd == "run":
        if a.cap is None:
            print("STOP: run needs --cap")
            return 2
        return do_run(a)
    for sample in SAMPLES:
        if all((work(sample, q, s) / "results.json").exists() for q, s in SAMPLES[sample]()):
            print(json.dumps(compare(sample), indent=1))
        else:
            print("%s: not run (or not finished); no counts written" % sample)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
