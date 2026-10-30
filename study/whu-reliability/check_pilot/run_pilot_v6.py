#!/usr/bin/env python3
"""The check-an-answer pilot, v6 (docs/whu-check-an-answer-pilot.md §13).

    run_pilot_v6.py prepare                    free: v4's recorded stage 1, v5's recorded verdicts, the long-source
                                               claims v6 re-reads, their windows and calls (count_tokens only);
                                               distinct long sources, windows each, the model, the worst case
    run_pilot_v6.py run --cap X --no-call-after ISO   PAID, ledger issue whu-check-pilot-v6; only after Fred's go-ahead
    run_pilot_v6.py compare                    §10.7's bars for v3 to v6 side by side

Input (§13.6): the same 8 answers; v4's stage 1 and v5's verdicts are read, not re-called; only the claims v5 sent
to its passages-checked path are read again. Private outputs: ~/Projects/whu-study-private/check_pilot_v6/.
Committed: counts only, check_pilot/pilot_v6_counts.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline as V1  # noqa: E402
import pipeline_v5 as V5  # noqa: E402
import pipeline_v6 as P  # noqa: E402
import run_pilot as R  # noqa: E402
import run_pilot_v3 as R3  # noqa: E402
import run_pilot_v4 as R4  # noqa: E402
import run_pilot_v5 as R5  # noqa: E402

J, S = V1.J, R3.S
ISSUE = "whu-check-pilot-v6"
ROLE = "check-pilot-v6"
SCRIPT = "study/whu-reliability/check_pilot/run_pilot_v6.py"
OUT = R.PRIVATE / "check_pilot_v6"
COUNTS = HERE / "pilot_v6_counts.json"
V5_COUNTS = HERE / "pilot_v5_counts.json"
RESERVED_DAYS = ("2026-10-31", "2026-11-01")          # §13.8: reserved for VP; no paid call on these UTC days
JUDGED = (P.BACKED, P.NOT_BACKED)


def reserved(now: datetime) -> bool:
    return now.strftime("%Y-%m-%d") in RESERVED_DAYS


def sample() -> list[tuple[str, str]]:
    return R4.sample()


def work(q: str, s: str) -> Path:
    return OUT / ("%s-%s" % (q, s))


def held(q: str, s: str) -> dict:
    src, dst = R4.v3_work(q, s) / "sources", work(q, s) / "sources"
    if not dst.exists():
        shutil.copytree(src, dst)
    return {m["url"]: m for m in json.loads((dst / "manifest.json").read_text())}


def clients(role: str = ROLE):
    import anthropic
    raw = anthropic.Anthropic(api_key=J.env_keys()["ANTHROPIC_API_KEY"])
    return raw, S.metered(raw, script=SCRIPT, issue=ISSUE, role=role)


def spent(entries=None) -> float:
    return sum(e.get("usd") or 0 for e in (S.entries() if entries is None else entries) if e.get("issue") == ISSUE)


def role_lines(entries=None, role: str = ROLE) -> list[dict]:
    return [e for e in (S.entries() if entries is None else entries) if e.get("role") == role]


def counter_blind(spent_usd: float, lines: list[dict]) -> str | None:
    """The v5 misfiling (§12.7) as a check: the run's own counter reads $0 while the ledger holds its role's lines."""
    paid = [e for e in lines if (e.get("usd") or 0) > 0]
    if spent_usd == 0 and paid:
        return ("the spend counter for %s reads $0 while the ledger holds %d priced line(s) for role %s (issue %r): "
                "the calls are metered somewhere the cap cannot see" % (ISSUE, len(paid), ROLE, paid[0].get("issue")))
    return None


class Budget(R5.Budget):
    """v5's budget on v6's issue, plus: stop if the counter is blind after a call has returned."""

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


def recorded(q: str, s: str) -> tuple[dict, dict]:
    return json.loads((R4.work(q, s) / "results.json").read_text()), json.loads((R5.work(q, s) / "results.json").read_text())


def plan_answer(q: str, s: str, count) -> dict:
    s1, v5 = recorded(q, s)
    man = held(q, s)
    planned = P.plan_v6(s1["results"], man, work(q, s), count)
    targets = [p for p in planned if p.get("windowed")]
    want = sorted(r["idx"] for r in v5["results"] if r.get("decided_by") == V5.EXPANDED)
    if sorted(t["idx"] for t in targets) != want:
        raise P.Stop("%s/%s: v6's long-source claims %s are not v5's passages-checked claims %s"
                     % (q, s, [t["idx"] for t in targets], want))
    jobs, layout = P.plan_windows(targets, man, work(q, s), count)
    return {"stage1": s1, "v5": v5, "manifest": man, "targets": targets, "jobs": jobs, "layout": layout,
            "worst_usd": round(sum(j["worst"] for j in jobs), 4)}


def do_prepare(_a) -> int:
    raw, _ = clients(ROLE + "-prepare")
    count = V1.count_tokens_fn(raw)
    total, rows, sources = 0.0, [], {}
    for q, s in sample():
        pa = plan_answer(q, s, count)
        for sid, lay in pa["layout"].items():
            sources[sid] = {"answer": "%s/%s" % (q, s), "tokens": lay["tokens"], "windows": len(lay["windows"]),
                            "claims": len(lay["claims"]),
                            "calls": sum(1 for j in pa["jobs"] if j.get("source_id") == sid)}
        calls = len(pa["jobs"])
        (work(q, s) / "prepared.json").write_text(json.dumps({
            "question": q, "system": s, "at": R.now(), "worst_usd": pa["worst_usd"], "layout": pa["layout"],
            "jobs": [{k: v for k, v in j.items() if k not in ("prefix", "rest", "planned")} for j in pa["jobs"]]},
            indent=1, default=str))
        total += pa["worst_usd"]
        rows.append({"answer": "%s/%s" % (q, s), "claims": len(pa["targets"]), "calls": calls,
                     "worst_usd": pa["worst_usd"]})
        print("  %s %-10s %2d long-source claims, %2d calls, worst $%.2f" % (q, s, len(pa["targets"]), calls,
                                                                             pa["worst_usd"]))
    print("DISTINCT LONG SOURCES: %d" % len(sources))
    for sid, v in sources.items():
        print("  %s %-22s %7d tokens  %d windows  %2d claims  %d calls" % (sid, v["answer"], v["tokens"], v["windows"],
                                                                         v["claims"], v["calls"]))
    print("MODEL: %s (max input %d tokens); window %d tokens, overlap >= %d, <= %d claims per call; batched prompt "
          "sha256 %s" % (J.CLAUDE_MODEL, P.MODEL_MAX_INPUT, P.WINDOW_TOKENS, P.OVERLAP_TOKENS, P.BATCH,
                         P.batched_prompt_sha()))
    print("ESTIMATE (worst case: every call a cache write + %d output tokens): $%.2f" % (P.MAX_OUT, total))
    (OUT / "estimate.json").write_text(json.dumps({
        "at": R.now(), "worst_usd": round(total, 4), "rows": rows, "sources": sources, "model": J.CLAUDE_MODEL,
        "window_tokens": P.WINDOW_TOKENS, "overlap_tokens": P.OVERLAP_TOKENS, "batch": P.BATCH,
        "batched_prompt_sha256": P.batched_prompt_sha()}, indent=1))
    return 0


def do_run(a) -> int:
    now = datetime.now(timezone.utc)
    if reserved(now):
        print("STOP: %s UTC is reserved for VP (§13.8); nothing was called" % now.strftime("%Y-%m-%d"))
        return 3
    est = json.loads((OUT / "estimate.json").read_text())
    # advisor's rule (2026-10-30): that day's ledger + VP's planned spend for the day + this run's cap, >= $10 left
    ok, why = R5.room(a.cap + a.vp_planned, R5.today_total(), float(S.caps()["default_per_day"]))
    why += " (this run's cap $%.2f + VP's planned $%.2f)" % (a.cap, a.vp_planned)
    print("ESTIMATE: $%.2f (from %s); cap $%.2f on %s\nROOM: %s" % (est["worst_usd"], est["at"], a.cap, ISSUE, why))
    if not ok:
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
        t0 = time.time()
        pa = plan_answer(q, s, count)
        win, log, layout = P.windowed_read(pa["targets"], pa["manifest"], work(q, s), client, count,
                                           budget.before_call)
        secs = round(time.time() - t0, 1)
        by = {r["idx"]: r for r in win}
        results = [{k: v for k, v in (by.get(r["idx"]) or r).items() if k not in V5._HIDDEN + ("windowed",)}
                   for r in pa["v5"]["results"]]
        res_f.write_text(json.dumps({
            "question": q, "system": s, "at": R.now(), "found": pa["stage1"]["found"], "seconds_windows": secs,
            "seconds_stage1_v4": pa["stage1"]["seconds"], "seconds_reread_v5": pa["v5"]["seconds_reread"],
            "layout": layout, "jobs": log, "summary": V5.summary(results, pa["stage1"]["found"]), "results": results,
            "totals": V5.totals(results)}, indent=1, ensure_ascii=False, default=str))
        print("  %s %-10s %5.0f s  %s" % (q, s, secs, V5.summary(results, pa["stage1"]["found"])))
        stopped = [j for j in log if j["failures"]]
        if stopped:
            print("    %d job(s) with failures (their claims are COULDN'T CHECK): %s" % (len(stopped), stopped[0]["job"]))
    why = counter_blind(spent(), role_lines())
    if why:
        print("STOP: " + why)
        return 4
    print("%s spent: $%.4f" % (ISSUE, spent()))
    return 0


def compare() -> dict:
    v5c = json.loads(V5_COUNTS.read_text())
    pairs, per_answer, reasons, by_path, nf_moves, win_moves = [], [], Counter(), Counter(), Counter(), Counter()
    n_claims, passages, nf, windows_per = 0, [0, 0], 0, {}
    for q, s in sample():
        v3, v4 = R4.side(3, q, s), R4.side(4, q, s)
        v5 = R5.side5(q, s)
        res6 = json.loads((work(q, s) / "results.json").read_text())
        v6 = {r["idx"]: r for r in res6["results"]}
        study, texts = R3.study_labels_r1(q, s)
        for sid, lay in res6["layout"].items():
            windows_per[sid] = {"answer": "%s/%s" % (q, s), "tokens": lay["tokens"], "windows": len(lay["windows"])}
        for idx, r in v6.items():
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
                win_moves["%s -> %s" % (v5[idx]["label"], r["label"])] += 1
            if v5[idx]["label"] == P.NOT_FOUND:
                nf_moves[r["label"]] += 1
        for idx, r3 in v3.items():
            st = V1.study_label_to_check(study[idx]) if idx in study and texts.get(idx) == r3["claim"] else None
            if st is not None:
                pairs.append({"answer": "%s/%s" % (q, s), "idx": idx, "study": st, "v3": r3["label"],
                              "v4": v4[idx]["label"], "v5": v5[idx]["label"], "v6": v6[idx]["label"],
                              "decided_by": v6[idx]["decided_by"]})
        n_claims += len(v6)
        usd = (sum(r.get("usd") or 0 for r in v4.values())
               + sum(r.get("usd_reread") or 0 for r in v5.values() if r.get("decided_by") == V5.WHOLE)
               + sum(j["usd"] for j in res6["jobs"]))
        per_answer.append({"answer": "%s/%s" % (q, s), "claims": len(v6), "v6": V5.totals(list(v6.values())),
                           "usd_v6": round(usd, 4), "usd_windows": round(sum(j["usd"] for j in res6["jobs"]), 4),
                           "seconds_stage1_v4": res6["seconds_stage1_v4"], "seconds_reread_v5": res6["seconds_reread_v5"],
                           "seconds_windows": res6["seconds_windows"],
                           "v3_fetch_seconds_reconstructed": R4.fetch_seconds(q, s)})
    n = len(per_answer)

    def agreement(rows: list[dict]) -> dict:
        both = [p for p in rows if p["study"] in JUDGED and p["v6"] in JUDGED]
        agree = sum(p["study"] == p["v6"] for p in both)
        return {"n": len(both), "agree": agree, "share": round(agree / len(both), 4) if both else None}

    usd_total = sum(a["usd_v6"] for a in per_answer)
    secs = [a["seconds_stage1_v4"] + a["seconds_reread_v5"] + a["seconds_windows"] for a in per_answer]
    secs_bar = sum(x + a["v3_fetch_seconds_reconstructed"] for x, a in zip(secs, per_answer)) / n
    cc_n = sum(reasons.values())
    cc = {"n": cc_n + nf, "of": n_claims, "share": round((cc_n + nf) / n_claims, 4), "couldnt_check": cc_n,
          "not_found_in_passages_checked": nf, "reasons": dict(reasons.most_common())}
    ag = agreement(pairs)
    out = {
        "written": R.now(), "by": SCRIPT + " compare",
        "label": "Counts only. Internal pilot, exploratory, outside H1/H2; judged by an AI model (Claude) only. v6 on "
                 "the same 8 answers, v3's held copies, v4's stage 1 and v5's verdicts: a side-by-side on identical "
                 "input, not a fresh sample. Development evidence only (§13.0).",
        "design": "docs/whu-check-an-answer-pilot.md §13", "ledger_issue": ISSUE, "sample": v5c["sample"],
        "window": {"tokens": P.WINDOW_TOKENS, "overlap_tokens": P.OVERLAP_TOKENS, "batch": P.BATCH,
                   "model": J.CLAUDE_MODEL, "batched_prompt_sha256": P.batched_prompt_sha(), "sources": windows_per},
        "couldnt_check": {**{k: v5c["couldnt_check"][k] for k in ("v3", "v4", "v5")}, "v6": cc},
        "agreement": {**{k: v5c["agreement"][k] for k in ("v3", "v4", "v5")}, "v6": ag,
                      "v6_windowed_claims": agreement([p for p in pairs if p["decided_by"] == P.WINDOWED]),
                      "v6_m1_claims": agreement([p for p in pairs if p["decided_by"] != P.WINDOWED]),
                      "rule": v5c["agreement"]["rule"]},
        "passages": {**v5c["passages"], "v6": {"verdicts": passages[0], "with_passage": passages[1]}},
        "usd": {**v5c["usd"], "v6": {"total": round(usd_total, 4), "per_answer": round(usd_total / n, 4),
                                     "windows": round(sum(a["usd_windows"] for a in per_answer), 4),
                                     "ledger_v6": round(spent(), 4)}},
        "seconds": {**v5c["seconds"], "v6_measured_no_fetch": {"mean": round(sum(secs) / n, 1), "max": max(secs),
                                                                "note": "includes v5's re-read seconds whole, "
                                                                        "though v6 does not make v5's passages-"
                                                                        "checked calls: an overstatement"},
                    "v6_plus_v3_fetch_reconstructed": {"mean": round(secs_bar, 1), "estimate": True}},
        "not_backed_by_path_v6": dict(by_path),
        "windowed_v5_to_v6": dict(sorted(win_moves.items())),
        "v5_not_found_to_v6": dict(nf_moves),
        "per_answer": per_answer,
    }
    out["pass_bar"] = {**{k: v5c["pass_bar"][k] for k in ("v3", "v4", "v5")},
                       "v6": R4.bars(cc, n, ag, tuple(passages), usd_total, secs_bar)}
    out["pass"] = {**v5c["pass"], "v6": all(out["pass_bar"]["v6"].values())}
    (OUT / "pairs.json").write_text(json.dumps(pairs, indent=1))
    COUNTS.write_text(json.dumps(out, indent=1) + "\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "run", "compare"])
    ap.add_argument("--cap", type=float, default=None)
    ap.add_argument("--no-call-after", default=None, help="ISO time (UTC); no call starts at or after it")
    ap.add_argument("--vp-planned", type=float, default=None, help="VP's planned spend for the day (USD), from VP")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == "prepare":
        return do_prepare(a)
    if a.cmd == "run":
        if a.cap is None or a.no_call_after is None or a.vp_planned is None:
            print("STOP: run needs --cap, --no-call-after and --vp-planned (ask VP first)")
            return 2
        return do_run(a)
    if all((work(q, s) / "results.json").exists() for q, s in sample()):
        print(json.dumps(compare(), indent=1))
        return 0
    print("not run (or not finished); no counts written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
