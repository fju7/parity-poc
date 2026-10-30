#!/usr/bin/env python3
"""The check-an-answer pilot, v4 (docs/whu-check-an-answer-pilot.md §11, §11.1).

    run_pilot_v4.py prepare              free: v3's claims and v3's held copies (copied, never re-fetched),
                                         v4's passages, count_tokens; prints the worst-case estimate
    run_pilot_v4.py run --cap 10         PAID, ledger issue whu-check-pilot-v4
    run_pilot_v4.py compare              §10.7's bars for v3 and v4 side by side, claim by claim

Input (§11.1): v3's primary sample, the same 8 round-1 answers, not a fresh sample. Only what the judge
reads differs from v3. Private outputs: ~/Projects/whu-study-private/check_pilot_v4/. Committed: counts
only, check_pilot/pilot_v4_counts.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline as V1  # noqa: E402
import pipeline_v3 as V3  # noqa: E402
import pipeline_v4 as P  # noqa: E402
import run_pilot as R  # noqa: E402
import run_pilot_v3 as R3  # noqa: E402

J, S = V1.J, R3.S
ISSUE = "whu-check-pilot-v4"
SCRIPT = "study/whu-reliability/check_pilot/run_pilot_v4.py"
OUT = R.PRIVATE / "check_pilot_v4"
V3_OUT = R3.OUT / "primary"
COUNTS = HERE / "pilot_v4_counts.json"
V3_COUNTS = HERE / "pilot_v3_counts.json"
JUDGED = (P.BACKED, P.NOT_BACKED)


def sample() -> list[tuple[str, str]]:
    return R3.draw_primary()                           # §11.1: v3's 8, not a fresh draw


def work(q: str, s: str) -> Path:
    return OUT / ("%s-%s" % (q, s))


def v3_work(q: str, s: str) -> Path:
    return V3_OUT / ("%s-%s" % (q, s))


def held(q: str, s: str) -> dict:
    """v3's manifest for this answer, its source texts copied into v4's folder ({url: row})."""
    src, dst = v3_work(q, s) / "sources", work(q, s) / "sources"
    if not dst.exists():
        shutil.copytree(src, dst)
    return {m["url"]: m for m in json.loads((dst / "manifest.json").read_text())}


def prepare_held(text: str, q: str, s: str, fmt: str, count) -> dict:
    """v3's prepare with v3's held copies in place of snapshots_v3, and v4's plan (no model call)."""
    w = work(q, s)
    md, cited, fmt = V3.adapt_answer(text, fmt)
    rows, refs = V1.sentences(md, cited, w, s)
    claims, beyond, found = V3.claims_v3(rows, refs, None, V1.MAX_CLAIMS)
    man = held(q, s)
    missing = [ct["url"] for c in claims for ct in c["citations"] if ct.get("url") and ct["url"] not in man]
    if missing:
        raise P.Stop("%s/%s: %d cited address(es) not in v3's manifest, e.g. %s" % (q, s, len(missing), missing[0]))
    planned, log = P.plan_v4(claims, man, w, count)
    return {"format": fmt, "claims": claims, "beyond_limit": beyond, "found": found, "manifest": man,
            "planned": planned, "retrieval": log, "below_threshold": sum(1 for r in log if r["below_threshold"]),
            "worst_usd": round(sum(p.get("worst") or 0 for p in planned), 4),
            "calls": sum(1 for p in planned if p["label"] is None)}


def clients(role: str):
    import anthropic
    raw = anthropic.Anthropic(api_key=J.env_keys()["ANTHROPIC_API_KEY"])
    return raw, S.metered(raw, script=SCRIPT, issue=ISSUE, role=role)


def spent() -> float:
    return sum(e.get("usd") or 0 for e in S.entries() if e.get("issue") == ISSUE)


def do_prepare(_a) -> int:
    raw, _ = clients("check-pilot-v4-prepare")
    count = V1.count_tokens_fn(raw)
    total = 0.0
    rows = []
    for q, s in sample():
        text, fmt = R3.capture("primary", q, s)
        prep = prepare_held(text, q, s, fmt, count)
        v3_claims = [r["claim"] for r in json.loads((v3_work(q, s) / "results.json").read_text())["results"]]
        same = [c["claim"] for c in prep["claims"]] == v3_claims
        (work(q, s) / "prepared.json").write_text(json.dumps({
            "question": q, "system": s, "format": prep["format"], "at": R.now(), "found": prep["found"],
            "claims": R.strip(prep["planned"]), "retrieval": prep["retrieval"], "same_claims_as_v3": same,
            "worst_usd": prep["worst_usd"], "calls": prep["calls"]}, indent=1, ensure_ascii=False, default=str))
        total += prep["worst_usd"]
        rows.append({"answer": "%s/%s" % (q, s), "claims": len(prep["claims"]), "calls": prep["calls"],
                     "worst_usd": prep["worst_usd"], "below_threshold": prep["below_threshold"],
                     "same_claims_as_v3": same})
        print("  %s %-10s %2d claims (same as v3: %s), %2d calls, worst $%.2f, below threshold %d" % (
            q, s, len(prep["claims"]), same, prep["calls"], prep["worst_usd"], prep["below_threshold"]))
        if not same:
            print("STOP: the claims differ from v3's; the side-by-side would not be on identical input")
            return 4
    (OUT / "estimate.json").write_text(json.dumps({"at": R.now(), "worst_usd": round(total, 4), "rows": rows},
                                                  indent=1))
    print("ESTIMATE (worst case, judge_m1's formula): $%.2f" % total)
    return 0


def do_run(a) -> int:
    est = json.loads((OUT / "estimate.json").read_text())
    print("ESTIMATE: $%.2f (from %s); cap $%.2f on %s" % (est["worst_usd"], est["at"], a.cap, ISSUE))
    if est["worst_usd"] > a.cap:
        print("STOP: the estimate is over the cap; nothing was called")
        return 3
    V1.prompt_ok()
    base, reserved, lock = spent(), [0.0], threading.Lock()

    def before_call(worst: float) -> None:
        S.check_cap(ISSUE, worst)                      # caps.json: the $25 day cap and the issue cap
        with lock:
            if base + reserved[0] + worst > a.cap:
                raise P.Stop("%s: $%.3f spent before this run + $%.3f reserved; the next call could cost up to $%.3f"
                             " (cap $%.2f)" % (ISSUE, base, reserved[0], worst, a.cap))
            reserved[0] += worst

    raw, client = clients("check-pilot-v4")
    count = V1.count_tokens_fn(raw)
    for q, s in sample():
        res_f = work(q, s) / "results.json"
        if res_f.exists():
            print("  %s %-10s already run; kept" % (q, s))
            continue
        text, fmt = R3.capture("primary", q, s)
        t0 = time.time()
        try:
            prep = prepare_held(text, q, s, fmt, count)
            results = P.judge_v4(prep["planned"], prep["manifest"], work(q, s), client, before_call)
        except (S.OverCap, P.Stop) as e:
            print("STOP before a call on %s %s: %s" % (q, s, e))
            return 3
        secs = round(time.time() - t0, 1)
        res_f.write_text(json.dumps({"question": q, "system": s, "at": R.now(), "format": prep["format"],
                                     "found": prep["found"], "seconds": secs, "retrieval": prep["retrieval"],
                                     "summary": V3.summary(results, prep["found"]), "results": results,
                                     "totals": V1.totals(results)}, indent=1, ensure_ascii=False, default=str))
        print("  %s %-10s %5.0f s  %s" % (q, s, secs, V3.summary(results, prep["found"])))
    print("%s spent: $%.4f" % (ISSUE, spent()))
    return 0


def fetch_seconds(q: str, s: str) -> float:
    """v3's fetch wall time for one answer, reconstructed: per-copy seconds summed per host, slowest host."""
    by_host: Counter = Counter()
    for m in json.loads((v3_work(q, s) / "sources" / "manifest.json").read_text()):
        by_host[V3.V2.host(m["url"])] += m.get("seconds") or 0
    return round(max(by_host.values()) if by_host else 0.0, 1)


def side(version: int, q: str, s: str) -> dict[int, dict]:
    f = (work if version == 4 else v3_work)(q, s) / "results.json"
    return {r["idx"]: r for r in json.loads(f.read_text())["results"]}


def bars(c: dict, n: int, a: dict, passages: tuple[int, int], usd: float, secs: float) -> dict:
    share = c["n"] / c["of"] if c["of"] else None
    return {"couldnt_check_at_most_20": share is not None and share <= R3.PASS_COULDNT,
            "agreement_at_least_90": a["share"] is not None and a["share"] >= R3.PASS_AGREEMENT,
            "usd_per_answer_at_most_2": usd / n <= R3.PASS_USD,
            "seconds_per_answer_mean_at_most_120": secs <= R3.PASS_SECONDS,
            "passages_100": passages[0] > 0 and passages[1] == passages[0]}


def compare() -> dict:
    per_answer, pairs, transitions, delivery, reasons = [], [], Counter(), [], {3: Counter(), 4: Counter()}
    n_claims, passages = 0, {3: [0, 0], 4: [0, 0]}
    for q, s in sample():
        v3, v4 = side(3, q, s), side(4, q, s)
        assert [r["claim"] for r in v3.values()] == [r["claim"] for r in v4.values()], (q, s)
        study, texts = R3.study_labels_r1(q, s)
        res4 = json.loads((work(q, s) / "results.json").read_text())
        for ver, rows in ((3, v3), (4, v4)):
            for r in rows.values():
                if r["label"] == P.COULDNT:
                    reasons[ver][r.get("reason_kind") or "?"] += 1
                if r["label"] in JUDGED:
                    passages[ver][0] += 1
                    p = r.get("passage") or {}
                    passages[ver][1] += bool(p.get("quote")) and (p.get("words") or 99) < 60
        for idx, r3 in v3.items():
            r4 = v4[idx]
            transitions["%s -> %s" % (r3["label"], r4["label"])] += 1
            st = V1.study_label_to_check(study[idx]) if idx in study and texts.get(idx) == r3["claim"] else None
            if st is not None:
                pairs.append({"answer": "%s/%s" % (q, s), "idx": idx, "study": st, "v3": r3["label"],
                              "v4": r4["label"], "kind4": r4.get("kind"), "kind3": r3.get("kind")})
            if r3.get("reason_kind") == V3.R_DELIVERY:
                p = r4.get("passage") or {}
                delivery.append({"answer": "%s/%s" % (q, s), "idx": idx, "v4": r4["label"],
                                 "v4_reason": r4.get("reason_kind"), "study": st,
                                 "cleared": r4["label"] in JUDGED and bool(p.get("quote")),
                                 "agrees_with_study": (st == r4["label"]) if st in JUDGED and r4["label"] in JUDGED
                                 else None})
        n_claims += len(v3)
        ret = res4.get("retrieval") or []
        per_answer.append({"answer": "%s/%s" % (q, s), "claims": len(v3),
                           "v3": V1.totals(list(v3.values())), "v4": V1.totals(list(v4.values())),
                           "v4_seconds_measured": res4["seconds"], "v3_fetch_seconds_reconstructed": fetch_seconds(q, s),
                           "v3_seconds": json.loads((v3_work(q, s) / "results.json").read_text())["seconds"],
                           "v4_retrieval_below_threshold": sum(1 for x in ret if x["below_threshold"]),
                           "v4_topped_up": sum(len(x["topped_up"]) for x in ret)})
    n = len(per_answer)

    def agreement(ver: int) -> dict:
        both = [p for p in pairs if p["study"] in JUDGED and p["v%d" % ver] in JUDGED]
        agree = sum(p["study"] == p["v%d" % ver] for p in both)
        return {"n": len(both), "agree": agree, "share": round(agree / len(both), 4) if both else None}

    v3c = json.loads(V3_COUNTS.read_text())
    usd4 = spent()
    secs4 = sum(a["v4_seconds_measured"] for a in per_answer) / n
    secs4_bar = sum(a["v4_seconds_measured"] + a["v3_fetch_seconds_reconstructed"] for a in per_answer) / n
    cc = {ver: {"n": sum(reasons[ver].values()), "of": n_claims} for ver in (3, 4)}
    for ver in (3, 4):
        cc[ver]["share"] = round(cc[ver]["n"] / n_claims, 4)
        cc[ver]["reasons"] = dict(reasons[ver].most_common())
    ag = {3: agreement(3), 4: agreement(4)}
    out = {
        "written": R.now(), "by": SCRIPT + " compare",
        "label": "Counts only. Internal pilot, exploratory, outside H1/H2; judged by an AI model (Claude) only. "
                 "v4 on v3's 8 answers and v3's held copies: a side-by-side on identical input, not a fresh sample.",
        "design": "docs/whu-check-an-answer-pilot.md §11, §11.1", "ledger_issue": ISSUE,
        "sample": ["%s/%s" % x for x in sample()],
        "couldnt_check": {"v3": cc[3], "v4": cc[4]},
        "agreement": {"v3": ag[3], "v4": ag[4],
                      "rule": "sentences the study drew and the pilot checked, both BACKED or NOT BACKED "
                              "(study: round 1's Claude-judge first reads)"},
        "passages": {"v3": {"verdicts": passages[3][0], "with_passage": passages[3][1]},
                     "v4": {"verdicts": passages[4][0], "with_passage": passages[4][1]}},
        "usd": {"v3": v3c["usd"], "v4": {"total": round(usd4, 4), "per_answer": round(usd4 / n, 4)}},
        "seconds": {"v3": v3c["seconds"],
                    "v4_measured_no_fetch": {"mean": round(secs4, 1),
                                             "max": max(a["v4_seconds_measured"] for a in per_answer)},
                    "v4_plus_v3_fetch_reconstructed": {"mean": round(secs4_bar, 1), "estimate": True}},
        "v3_to_v4": dict(sorted(transitions.items())),
        "delivery_check_v3": {"n": len(delivery), "cleared_by_v4": sum(d["cleared"] for d in delivery),
                              "v4_labels": dict(Counter(d["v4"] for d in delivery)),
                              "cleared_agree_with_study": sum(d["agrees_with_study"] is True for d in delivery),
                              "cleared_with_study_label": sum(d["agrees_with_study"] is not None for d in delivery),
                              "claims": delivery},
        "per_answer": per_answer,
    }
    out["pass_bar"] = {
        "v3": v3c["pass_bar"],
        "v4": bars(cc[4], n, ag[4], tuple(passages[4]), usd4, secs4_bar)}
    out["pass"] = {"v3": v3c["pass"], "v4": all(out["pass_bar"]["v4"].values())}
    (OUT / "pairs.json").write_text(json.dumps(pairs, indent=1))
    COUNTS.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "run", "compare"])
    ap.add_argument("--cap", type=float, default=None)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "prepare":
        return do_prepare(a)
    if a.cmd == "run":
        if a.cap is None:
            print("STOP: run needs --cap")
            return 2
        return do_run(a)
    if all((work(q, s) / "results.json").exists() for q, s in sample()):
        print(json.dumps(compare(), indent=1))
        return 0
    print("not run (or not finished); no counts written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
