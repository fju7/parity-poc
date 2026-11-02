#!/usr/bin/env python3
"""The check-an-answer pilot, v7 (docs/whu-check-an-answer-pilot.md §14).

    run_pilot_v7.py prepare                    free: the claims v6 read in windows, their window calls (count_tokens
                                               only), likely (v6's measured window cost at Sonnet's prices) and worst
    run_pilot_v7.py run --cap X --no-call-after ISO --vp-planned Y   PAID, ledger issue whu-check-pilot-v7
    run_pilot_v7.py compare                    §10.7's bars for v3 to v7, with per-answer cost and time distributions

Input (§14.4): the same 8 answers; v4's stage 1, v5's verdicts and v6's verdicts are read, not re-called; only the
claims v6 read in windows are read again, on WINDOW_MODEL. Private outputs: ~/Projects/whu-study-private/check_pilot_v7/.
Committed: counts only, check_pilot/pilot_v7_counts.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline as V1  # noqa: E402
import pipeline_v5 as V5  # noqa: E402
import pipeline_v6 as V6  # noqa: E402
import pipeline_v7 as P  # noqa: E402
import run_pilot as R  # noqa: E402
import run_pilot_v3 as R3  # noqa: E402
import run_pilot_v4 as R4  # noqa: E402
import run_pilot_v5 as R5  # noqa: E402
import run_pilot_v6 as R6  # noqa: E402

J, S = V1.J, R3.S
ISSUE = "whu-check-pilot-v7"
ROLE = "check-pilot-v7"
SCRIPT = "study/whu-reliability/check_pilot/run_pilot_v7.py"
OUT = R.PRIVATE / "check_pilot_v7"
COUNTS = HERE / "pilot_v7_counts.json"
V6_COUNTS = HERE / "pilot_v6_counts.json"
JUDGED = (P.BACKED, P.NOT_BACKED)
# §14.2: Sonnet's prices are half of Opus's on every line, so v6's measured window cost x this is v7's likely figure
PRICE_RATIO = S.PRICES[P.WINDOW_MODEL]["input"] / S.PRICES[J.CLAUDE_MODEL]["input"]


def sample() -> list[tuple[str, str]]:
    return R4.sample()


def work(q: str, s: str) -> Path:
    return OUT / ("%s-%s" % (q, s))


def v6_result(q: str, s: str) -> dict:
    return json.loads((R6.work(q, s) / "results.json").read_text())


def clients(role: str = ROLE):
    import anthropic
    raw = anthropic.Anthropic(api_key=J.env_keys()["ANTHROPIC_API_KEY"])
    return raw, S.metered(raw, script=SCRIPT, issue=ISSUE, role=role)


def spent(entries=None) -> float:
    return sum(e.get("usd") or 0 for e in (S.entries() if entries is None else entries) if e.get("issue") == ISSUE)


def role_lines(entries=None) -> list[dict]:
    return [e for e in (S.entries() if entries is None else entries) if e.get("role") == ROLE]


def counter_blind(spent_usd: float, lines: list[dict]) -> str | None:
    paid = [e for e in lines if (e.get("usd") or 0) > 0]
    if spent_usd == 0 and paid:
        return ("the spend counter for %s reads $0 while the ledger holds %d priced line(s) for role %s (issue %r): "
                "the calls are metered somewhere the cap cannot see" % (ISSUE, len(paid), ROLE, paid[0].get("issue")))
    return None


class Budget(R5.Budget):
    """v5's budget on v7's issue, plus v6's stop if the counter is blind after a call has returned."""

    def __init__(self, cap, spent_fn, lines_fn, check_cap=None, no_call_after=None, clock=None):
        super().__init__(cap, spent_fn, check_cap, no_call_after, clock, issue=ISSUE)
        self.lines_fn, self.returned_n = lines_fn, 0

    def before_call(self, worst: float) -> None:
        if self.returned_n:
            why = counter_blind(self.spent_fn(), self.lines_fn())
            if why:
                raise P.Stop(why)
        super().before_call(worst)

    def returned(self) -> None:
        super().returned()
        with self.lock:
            self.returned_n += 1


def plan_answer(q: str, s: str, count) -> dict:
    """v6's targets for this answer (v6's own planning, as run_pilot_v6.plan_answer, windows planned once, on v7's
    model), checked against v6's recorded windowed rows (§14.4)."""
    s1, _v5 = R6.recorded(q, s)
    man = R6.held(q, s)
    targets = [p for p in V6.plan_v6(s1["results"], man, R6.work(q, s), count) if p.get("windowed")]
    res6 = v6_result(q, s)
    want = sorted(r["idx"] for r in res6["results"] if r.get("decided_by") == V6.WINDOWED)
    if sorted(t["idx"] for t in targets) != want:
        raise P.Stop("%s/%s: the long-source claims %s are not v6's windowed rows %s"
                     % (q, s, [t["idx"] for t in targets], want))
    jobs, layout = P.plan_windows(targets, man, R6.work(q, s), count)
    pa = {"stage1": s1, "manifest": man, "targets": targets}
    likely = sum(j["usd"] for j in res6["jobs"] if j["kind"] == "window") * PRICE_RATIO \
        + sum(j["usd"] for j in res6["jobs"] if j["kind"] == "whole")
    return {**pa, "res6": res6, "jobs": jobs, "layout": layout, "likely_usd": round(likely, 4),
            "worst_usd": round(sum(j["worst"] for j in jobs), 4)}


def gate(likely: float, spent_usd: float, cap: float) -> tuple[bool, str]:
    """Advisor rule 2026-11-01: stop before any call only if the issue's spend + the LIKELY figure exceeds the cap."""
    return spent_usd + likely <= cap, ("%s has spent $%.2f; + likely $%.2f = $%.2f; cap $%.2f"
                                       % (ISSUE, spent_usd, likely, spent_usd + likely, cap))


def do_prepare(_a) -> int:
    raw, _ = clients(ROLE + "-prepare")
    count = V1.count_tokens_fn(raw)
    likely = worst = 0.0
    rows = []
    for q, s in sample():
        pa = plan_answer(q, s, count)
        likely, worst = likely + pa["likely_usd"], worst + pa["worst_usd"]
        win = [j for j in pa["jobs"] if j["kind"] == "window"]
        rows.append({"answer": "%s/%s" % (q, s), "claims": len(pa["targets"]), "window_calls": len(win),
                     "whole_calls": len(pa["jobs"]) - len(win), "likely_usd": pa["likely_usd"],
                     "worst_usd": pa["worst_usd"]})
        print("  %s %-10s %2d claims, %2d window calls (%s), %d whole; likely $%.2f, worst $%.2f"
              % (q, s, len(pa["targets"]), len(win), P.WINDOW_MODEL, len(pa["jobs"]) - len(win), pa["likely_usd"],
                 pa["worst_usd"]))
    print("ESTIMATE: likely $%.2f (v6's measured window cost on whu-check-pilot-v6 x %.2f, Sonnet/Opus prices; "
          "whole-source calls at v6's cost); worst $%.2f (every call a cache write + %d output tokens)"
          % (likely, PRICE_RATIO, worst, V6.MAX_OUT))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "estimate.json").write_text(json.dumps({
        "at": R.now(), "likely_usd": round(likely, 4), "worst_usd": round(worst, 4), "rows": rows,
        "window_model": P.WINDOW_MODEL, "batched_prompt_sha256": V6.batched_prompt_sha()}, indent=1))
    return 0


def do_run(a) -> int:
    est = json.loads((OUT / "estimate.json").read_text())
    ok, why = gate(est["likely_usd"], spent(), a.cap)
    print("ESTIMATE: likely $%.2f, worst $%.2f (from %s)\nGATE: %s" % (est["likely_usd"], est["worst_usd"], est["at"],
                                                                       why))
    if not ok:
        print("STOP: likely over the cap; nothing was called")
        return 5
    room_ok, rwhy = R5.room(a.cap + a.vp_planned, R5.today_total(), float(S.caps()["default_per_day"]))
    print("ROOM: %s (this run's cap $%.2f + VP's planned $%.2f)" % (rwhy, a.cap, a.vp_planned))
    if not room_ok:
        print("STOP: no room under the day cap; nothing was called. Check again later; no cap is raised.")
        return 3
    V1.prompt_ok()
    cutoff = datetime.fromisoformat(a.no_call_after) if a.no_call_after else None
    budget = Budget(a.cap, spent, role_lines, S.check_cap, cutoff)
    raw, metered = clients()
    client = budget.wrap(metered)
    count = V1.count_tokens_fn(raw)
    for q, s in sample():
        res_f = work(q, s) / "results.json"
        if res_f.exists():
            print("  %s %-10s already run; kept" % (q, s))
            continue
        t0 = time.time()                    # as v6 (§13.11): planning (token counts) + the window calls
        pa = plan_answer(q, s, count)
        win, log, layout, call_secs = P.windowed_read(pa["targets"], pa["manifest"], R6.work(q, s), client, count,
                                                      budget.before_call, planned=(pa["jobs"], pa["layout"]))
        secs = round(time.time() - t0, 1)
        by = {r["idx"]: r for r in win}
        results = [{k: v for k, v in (by.get(r["idx"]) or r).items() if k not in V5._HIDDEN + ("windowed",)}
                   for r in pa["res6"]["results"]]
        work(q, s).mkdir(parents=True, exist_ok=True)
        res_f.write_text(json.dumps({
            "question": q, "system": s, "at": R.now(), "found": pa["stage1"]["found"], "seconds_windows": secs,
            "seconds_window_calls": call_secs, "window_model": P.WINDOW_MODEL, "layout": layout, "jobs": log,
            "summary": V5.summary(results, pa["stage1"]["found"]), "results": results,
            "totals": V5.totals(results)}, indent=1, ensure_ascii=False, default=str))
        print("  %s %-10s %5.1f s  %s" % (q, s, secs, V5.summary(results, pa["stage1"]["found"])))
        stopped = [j for j in log if j["failures"]]
        if stopped:
            print("    %d job(s) with failures (their claims are COULDN'T CHECK): %s" % (len(stopped), stopped[0]["job"]))
    why = counter_blind(spent(), role_lines())
    if why:
        print("STOP: " + why)
        return 4
    print("%s spent: $%.4f" % (ISSUE, spent()))
    return 0


def dist(xs: list[float]) -> dict:
    ys = sorted(xs)
    mid = len(ys) // 2
    return {"mean": round(sum(ys) / len(ys), 2), "median": round((ys[mid] + ys[~mid]) / 2, 2), "min": round(ys[0], 2),
            "max": round(ys[-1], 2), "each": [round(x, 2) for x in xs]}


def earlier_distributions() -> dict:
    """Per-answer dollars and seconds (with v3's reconstructed fetch time) for v3-v6, from their committed counts."""
    c3, c4, c5, c6 = (json.loads((HERE / ("pilot_v%d_counts.json" % v)).read_text()) for v in (3, 4, 5, 6))
    fetch = [a["v3_fetch_seconds_reconstructed"] for a in c4["per_answer"]]
    return {
        "answers": [a["answer"] for a in c6["per_answer"]],
        "usd": {"v3": dist([a["usd"] for a in c3["per_answer"]]),
                "v4": dist([a["v4"]["usd"] for a in c4["per_answer"]]),
                "v5": dist([a["usd_v5"] for a in c5["per_answer"]]),
                "v6": dist([a["usd_v6"] for a in c6["per_answer"]])},
        "seconds_with_fetch": {
            "v3": dist([a["seconds"] for a in c3["per_answer"]]),
            "v4": dist([a["v4_seconds_measured"] + f for a, f in zip(c4["per_answer"], fetch)]),
            "v5": dist([a["seconds_stage1_v4"] + a["seconds_reread_v5"] + a["v3_fetch_seconds_reconstructed"]
                        for a in c5["per_answer"]]),
            "v6_low": dist([a["seconds_v6_low"] + a["v3_fetch_seconds_reconstructed"] for a in c6["per_answer"]]),
            "v6_high": dist([a["seconds_v6_high"] + a["v3_fetch_seconds_reconstructed"] for a in c6["per_answer"]])}}


def compare() -> dict:
    c6 = json.loads(V6_COUNTS.read_text())
    pa6 = {a["answer"]: a for a in c6["per_answer"]}
    pairs, per_answer, reasons, by_path, moves = [], [], Counter(), Counter(), Counter()
    n_claims, passages, nf = 0, [0, 0], 0
    for q, s in sample():
        name = "%s/%s" % (q, s)
        res6, res7 = v6_result(q, s), json.loads((work(q, s) / "results.json").read_text())
        v6 = {r["idx"]: r for r in res6["results"]}
        v7 = {r["idx"]: r for r in res7["results"]}
        v3 = R4.side(3, q, s)
        study, texts = R3.study_labels_r1(q, s)
        for idx, r in v7.items():
            if r["label"] == P.COULDNT:
                reasons[r.get("reason_kind") or "?"] += 1
            nf += r["label"] == P.NOT_FOUND
            if r["label"] in JUDGED:
                passages[0] += 1
                p = r.get("passage") or {}
                passages[1] += bool(p.get("quote")) and (p.get("words") or 99) < 60
            if r["label"] == P.NOT_BACKED:
                by_path[r["decided_by"]] += 1
            if r.get("decided_by") == P.WINDOWED:
                moves["%s -> %s" % (v6[idx]["label"], r["label"])] += 1
        for idx, r3 in v3.items():
            st = V1.study_label_to_check(study[idx]) if idx in study and texts.get(idx) == r3["claim"] else None
            if st is not None:
                pairs.append({"answer": name, "idx": idx, "study": st, "v6": v6[idx]["label"],
                              "v7": v7[idx]["label"], "decided_by": v7[idx]["decided_by"]})
        n_claims += len(v7)
        a6 = pa6[name]
        win6 = sum(j["usd"] for j in res6["jobs"])
        win7 = sum(j["usd"] for j in res7["jobs"])
        base = a6["seconds_stage1_v4"]
        reread = a6["seconds_v6_high"] - a6["seconds_v6_low"]             # v5's whole-source share, bounded (§14.5)
        low = base + res7["seconds_windows"] + (a6["seconds_v6_low"] - base - a6["seconds_windows"])
        per_answer.append({"answer": name, "claims": len(v7), "v7": V5.totals(list(v7.values())),
                           "usd_v7": round(a6["usd_v6"] - win6 + win7, 4), "usd_windows_v6": round(win6, 4),
                           "usd_windows_v7": round(win7, 4), "seconds_windows_v6": a6["seconds_windows"],
                           "seconds_windows_v7": res7["seconds_windows"], "seconds_v7_low": round(low, 1),
                           "seconds_v7_high": round(low + reread, 1), "seconds_v7_exact": a6["seconds_v6_exact"],
                           "v3_fetch_seconds_reconstructed": a6["v3_fetch_seconds_reconstructed"],
                           "window_calls": [{"job": j["job"], "model": j["model"], "start": j["start"],
                                             "end": j["end"], "usd": j["usd"]} for j in res7["jobs"]]})
    n = len(per_answer)

    def agreement(rows: list[dict], key: str = "v7") -> dict:
        both = [p for p in rows if p["study"] in JUDGED and p[key] in JUDGED]
        agree = sum(p["study"] == p[key] for p in both)
        return {"n": len(both), "agree": agree, "share": round(agree / len(both), 4) if both else None}

    usd_total = sum(a["usd_v7"] for a in per_answer)
    secs = {k: [a["seconds_v7_" + k] + a["v3_fetch_seconds_reconstructed"] for a in per_answer] for k in ("low", "high")}
    cc_n = sum(reasons.values())
    cc = {"n": cc_n + nf, "of": n_claims, "share": round((cc_n + nf) / n_claims, 4), "couldnt_check": cc_n,
          "not_found_in_passages_checked": nf, "reasons": dict(reasons.most_common())}
    ag = agreement(pairs)
    windowed = [p for p in pairs if p["decided_by"] == P.WINDOWED]
    earlier = earlier_distributions()
    out = {
        "written": R.now(), "by": SCRIPT + " compare",
        "label": "Counts only. Internal pilot, exploratory, outside H1/H2; judged by AI models (Claude Opus; Sonnet for "
                 "v7's window reads) only. v7 on the same 8 answers and held copies, v4's stage 1, v5's and v6's "
                 "verdicts: a side-by-side on identical input, not a fresh sample. Development evidence only (§13.0).",
        "design": "docs/whu-check-an-answer-pilot.md §14", "ledger_issue": ISSUE, "sample": c6["sample"],
        "window_model": P.WINDOW_MODEL, "batched_prompt_sha256": V6.batched_prompt_sha(),
        "couldnt_check": {**c6["couldnt_check"], "v7": cc},
        "agreement": {**{k: c6["agreement"][k] for k in ("v3", "v4", "v5", "v6")}, "v7": ag,
                      "v7_windowed_claims": agreement(windowed),
                      "v6_windowed_claims_same_items": agreement(windowed, "v6"),
                      "v7_m1_claims": agreement([p for p in pairs if p["decided_by"] != P.WINDOWED]),
                      "rule": c6["agreement"]["rule"]},
        "windowed_v6_to_v7": dict(sorted(moves.items())),
        "passages": {**c6["passages"], "v7": {"verdicts": passages[0], "with_passage": passages[1]}},
        "usd": {**c6["usd"], "v7": {"total": round(usd_total, 4), "per_answer": round(usd_total / n, 4),
                                    "windows": round(sum(a["usd_windows_v7"] for a in per_answer), 4),
                                    "ledger_v7": round(spent(), 4)}},
        "distributions": {"answers": earlier["answers"],
                          "usd": {**earlier["usd"], "v7": dist([a["usd_v7"] for a in per_answer])},
                          "seconds_with_fetch": {**earlier["seconds_with_fetch"], "v7_low": dist(secs["low"]),
                                                 "v7_high": dist(secs["high"])},
                          "note": "v6 and v7 time: low/high bound on v5's whole-source re-read share (§13.11, §14.5)"},
        "not_backed_by_path_v7": dict(by_path),
        "per_answer": per_answer,
    }
    out["pass_bar"] = {**c6["pass_bar"], "v6_time_low": c6["pass_bar_v6_corrected_time"]["low"],
                       "v6_time_high": c6["pass_bar_v6_corrected_time"]["high"],
                       **{"v7_time_" + k: R4.bars(cc, n, ag, tuple(passages), usd_total, sum(v) / n)
                          for k, v in secs.items()}}
    lo, hi = all(out["pass_bar"]["v7_time_low"].values()), all(out["pass_bar"]["v7_time_high"].values())
    out["pass"] = {**c6["pass"], "v6": False, "v7": lo if lo == hi else "unsettled (time bound)"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pairs.json").write_text(json.dumps(pairs, indent=1))
    COUNTS.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "run", "compare"])
    ap.add_argument("--cap", type=float, default=None)
    ap.add_argument("--no-call-after", default=None, help="ISO time (UTC); no call starts at or after it")
    ap.add_argument("--vp-planned", type=float, default=None, help="VP's remaining planned spend for the day (USD)")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "prepare":
        return do_prepare(a)
    if a.cmd == "run":
        if a.cap is None or a.no_call_after is None or a.vp_planned is None:
            print("STOP: run needs --cap, --no-call-after and --vp-planned")
            return 2
        return do_run(a)
    if all((work(q, s) / "results.json").exists() for q, s in sample()):
        print(json.dumps(compare(), indent=1))
        return 0
    print("not run (or not finished); no counts written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
