#!/usr/bin/env python3
"""The check-an-answer pilot, v5 (docs/whu-check-an-answer-pilot.md §12).

    run_pilot_v5.py prepare              free: v4's recorded stage 1, v3's held copies (never re-fetched), the
                                         re-reads and their paths, count_tokens; the worst case and the room check
    run_pilot_v5.py run --cap 8          PAID, ledger issue whu-check-pilot-v5; only with room under the day cap
    run_pilot_v5.py compare              §10.7's bars for v3, v4 and v5 side by side

Input (§12.2): the same 8 round-1 answers as v3 and v4, not a fresh sample; stage 1 is v4's results.json, read,
not re-called. Private outputs: ~/Projects/whu-study-private/check_pilot_v5/. Committed: counts only,
check_pilot/pilot_v5_counts.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pipeline as V1  # noqa: E402
import pipeline_v3 as V3  # noqa: E402
import pipeline_v5 as P  # noqa: E402
import run_pilot as R  # noqa: E402
import run_pilot_v3 as R3  # noqa: E402
import run_pilot_v4 as R4  # noqa: E402

J, S = V1.J, R3.S
ISSUE = "whu-check-pilot-v5"
SCRIPT = "study/whu-reliability/check_pilot/run_pilot_v5.py"
OUT = R.PRIVATE / "check_pilot_v5"
COUNTS = HERE / "pilot_v5_counts.json"
V4_COUNTS = HERE / "pilot_v4_counts.json"
ROOM = 10.0                                   # §12.4: at least $10 left under the day cap after the worst case
JUDGED = (P.BACKED, P.NOT_BACKED)


def sample() -> list[tuple[str, str]]:
    return R4.sample()                                    # §12.2: v3's and v4's 8


def work(q: str, s: str) -> Path:
    return OUT / ("%s-%s" % (q, s))


def held(q: str, s: str) -> dict:
    """v3's held copies, copied into v5's folder ({url: row}); never re-fetched."""
    src, dst = R4.v3_work(q, s) / "sources", work(q, s) / "sources"
    if not dst.exists():
        shutil.copytree(src, dst)
    return {m["url"]: m for m in json.loads((dst / "manifest.json").read_text())}


def stage1(q: str, s: str) -> dict:
    return json.loads((R4.work(q, s) / "results.json").read_text())


def today_total(now: datetime | None = None) -> float:
    day = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return round(sum(e.get("usd") or 0 for e in S.entries() if (e.get("at") or "").startswith(day)), 4)


def room(worst: float, today: float, day_cap: float) -> tuple[bool, str]:
    """§12.4: run only if today's total + the worst case leaves at least $10 under the day cap."""
    left = day_cap - (today + worst)
    return left >= ROOM, ("today $%.2f + worst case $%.2f = $%.2f; day cap $%.2f leaves $%.2f (need >= $%.2f)"
                          % (today, worst, today + worst, day_cap, left, ROOM))


class Budget:
    """The run's cap: spent on the issue + the worst case of every call in flight + the next call's <= cap.
    A call's reservation is dropped when it returns; its actual cost is then in the ledger."""

    def __init__(self, cap: float, spent_fn, check_cap=None):
        self.cap, self.spent_fn, self.check_cap = cap, spent_fn, check_cap
        self.lock, self.in_flight, self.local = threading.Lock(), 0.0, threading.local()

    def before_call(self, worst: float) -> None:
        with self.lock:
            if self.check_cap:
                self.check_cap(ISSUE, worst)                # caps.json: the day cap and the issue cap
            spent = self.spent_fn()
            if spent + self.in_flight + worst > self.cap:
                raise P.Stop("%s: $%.3f spent + $%.3f in flight; the next call could cost up to $%.3f (cap $%.2f)"
                             % (ISSUE, spent, self.in_flight, worst, self.cap))
            self.in_flight += worst
            self.local.held = getattr(self.local, "held", 0.0) + worst

    def returned(self) -> None:
        with self.lock:
            self.in_flight -= getattr(self.local, "held", 0.0)
            self.local.held = 0.0

    def wrap(self, client):
        budget = self

        class Messages:
            def create(self, **kw):
                try:
                    return client.messages.create(**kw)
                finally:
                    budget.returned()
        return SimpleNamespace(messages=Messages())


def spent() -> float:
    return sum(e.get("usd") or 0 for e in S.entries() if e.get("issue") == ISSUE)


def plan_answer(q: str, s: str, count) -> dict:
    s1 = stage1(q, s)
    man = held(q, s)
    planned = P.plan_v5(s1["results"], man, work(q, s), count)
    return {"stage1": s1, "manifest": man, "planned": planned, "worst_usd": P.worst_usd(planned),
            "paths": dict(Counter(p["path"] for p in planned if p.get("path")))}


def do_prepare(_a) -> int:
    raw, _ = R4.clients("check-pilot-v5-prepare")
    count = V1.count_tokens_fn(raw)
    total, rows = 0.0, []
    for q, s in sample():
        pa = plan_answer(q, s, count)
        (work(q, s) / "prepared.json").write_text(json.dumps({
            "question": q, "system": s, "at": R.now(), "worst_usd": pa["worst_usd"], "paths": pa["paths"],
            "rereads": [{"idx": p["idx"], "path": p["path"], "n_in": p["n_in"], "worst": p["worst"],
                         "stage1": p["stage1"]["study_label"], "expanded": p["expanded"]}
                        for p in pa["planned"] if p.get("path")]}, indent=1, default=str))
        total += pa["worst_usd"]
        rows.append({"answer": "%s/%s" % (q, s), "worst_usd": pa["worst_usd"], "paths": pa["paths"]})
        print("  %s %-10s re-reads %s, worst $%.2f" % (q, s, pa["paths"] or "none", pa["worst_usd"]))
    ok, why = room(total, today_total(), float(S.caps()["default_per_day"]))
    (OUT / "estimate.json").write_text(json.dumps({"at": R.now(), "worst_usd": round(total, 4), "rows": rows,
                                                   "room": ok, "room_check": why}, indent=1))
    print("ESTIMATE (worst case, judge_m1's formula): $%.2f" % total)
    print("ROOM: %s -> %s" % (why, "room" if ok else "NO ROOM: do not run; check again later"))
    return 0


def do_run(a) -> int:
    est = json.loads((OUT / "estimate.json").read_text())
    ok, why = room(est["worst_usd"], today_total(), float(S.caps()["default_per_day"]))
    print("ESTIMATE: $%.2f (from %s); cap $%.2f on %s\nROOM: %s" % (est["worst_usd"], est["at"], a.cap, ISSUE, why))
    if not ok:
        print("STOP: no room under the day cap; nothing was called. Check again later; no cap is raised.")
        return 3
    V1.prompt_ok()
    budget = Budget(a.cap, spent, S.check_cap)
    raw, metered = R4.clients("check-pilot-v5")
    client = budget.wrap(metered)
    count = V1.count_tokens_fn(raw)
    for q, s in sample():
        res_f = work(q, s) / "results.json"
        if res_f.exists():
            print("  %s %-10s already run; kept" % (q, s))
            continue
        t0 = time.time()
        try:
            pa = plan_answer(q, s, count)
            results = P.fuller_read(pa["planned"], pa["manifest"], client, budget.before_call)
        except (S.OverCap, P.Stop) as e:
            print("STOP on %s %s: %s (finished answers kept; the result is partial)" % (q, s, e))
            return 3
        secs = round(time.time() - t0, 1)
        results = [{k: v for k, v in r.items() if k not in P._HIDDEN} for r in results]
        s1 = pa["stage1"]
        res_f.write_text(json.dumps({"question": q, "system": s, "at": R.now(), "found": s1["found"],
                                     "seconds_reread": secs, "seconds_stage1_v4": s1["seconds"],
                                     "summary": P.summary(results, s1["found"]), "results": results,
                                     "totals": P.totals(results)}, indent=1, ensure_ascii=False, default=str))
        print("  %s %-10s %5.0f s  %s" % (q, s, secs, P.summary(results, s1["found"])))
    print("%s spent: $%.4f" % (ISSUE, spent()))
    return 0


def side5(q: str, s: str) -> dict[int, dict]:
    return {r["idx"]: r for r in json.loads((work(q, s) / "results.json").read_text())["results"]}


def compare() -> dict:
    v4c = json.loads(V4_COUNTS.read_text())
    pairs, per_answer, reasons, by_path, rereads = [], [], Counter(), Counter(), Counter()
    n_claims, passages, nf = 0, [0, 0], 0
    for q, s in sample():
        v3, v4, v5 = R4.side(3, q, s), R4.side(4, q, s), side5(q, s)
        assert [r["claim"] for r in v4.values()] == [r["claim"] for r in v5.values()], (q, s)
        study, texts = R3.study_labels_r1(q, s)
        res5 = json.loads((work(q, s) / "results.json").read_text())
        for r in v5.values():
            if r["label"] == P.COULDNT:
                reasons[r.get("reason_kind") or "?"] += 1
            nf += r["label"] == P.NOT_FOUND
            if r["label"] in JUDGED:
                passages[0] += 1
                p = r.get("passage") or {}
                passages[1] += bool(p.get("quote")) and (p.get("words") or 99) < 60
            if r["label"] == P.NOT_BACKED:
                by_path[r["decided_by"]] += 1
            if r.get("stage1"):
                rereads["%s: %s -> %s" % (r["decided_by"], r["stage1"]["label"], r["label"])] += 1
        for idx, r3 in v3.items():
            st = V1.study_label_to_check(study[idx]) if idx in study and texts.get(idx) == r3["claim"] else None
            if st is not None:
                pairs.append({"answer": "%s/%s" % (q, s), "idx": idx, "study": st, "v3": r3["label"],
                              "v4": v4[idx]["label"], "v5": v5[idx]["label"], "decided_by": v5[idx]["decided_by"]})
        n_claims += len(v5)
        usd5 = sum(r.get("usd_reread") or 0 for r in v5.values())
        usd4 = sum(r.get("usd") or 0 for r in v4.values())
        per_answer.append({"answer": "%s/%s" % (q, s), "claims": len(v5), "v5": P.totals(list(v5.values())),
                           "usd_stage1_v4": round(usd4, 4), "usd_reread_v5": round(usd5, 4),
                           "usd_v5": round(usd4 + usd5, 4),
                           "seconds_stage1_v4": res5["seconds_stage1_v4"], "seconds_reread_v5": res5["seconds_reread"],
                           "v3_fetch_seconds_reconstructed": R4.fetch_seconds(q, s)})
    n = len(per_answer)

    def agreement(ver: str) -> dict:
        both = [p for p in pairs if p["study"] in JUDGED and p[ver] in JUDGED]
        agree = sum(p["study"] == p[ver] for p in both)
        return {"n": len(both), "agree": agree, "share": round(agree / len(both), 4) if both else None}

    dis4 = [p for p in pairs if p["study"] in JUDGED and p["v4"] in JUDGED and p["study"] != p["v4"]]
    usd_total = sum(a["usd_v5"] for a in per_answer)
    secs = sum(a["seconds_stage1_v4"] + a["seconds_reread_v5"] for a in per_answer) / n
    secs_bar = sum(a["seconds_stage1_v4"] + a["seconds_reread_v5"] + a["v3_fetch_seconds_reconstructed"]
                   for a in per_answer) / n
    cc_n = sum(reasons.values())
    cc = {"n": cc_n + nf, "of": n_claims, "share": round((cc_n + nf) / n_claims, 4),
          "couldnt_check": cc_n, "not_found_in_passages_checked": nf, "reasons": dict(reasons.most_common())}
    ag = agreement("v5")
    out = {
        "written": R.now(), "by": SCRIPT + " compare",
        "label": "Counts only. Internal pilot, exploratory, outside H1/H2; judged by an AI model (Claude) only. v5 on "
                 "v3's and v4's 8 answers, v3's held copies and v4's recorded stage 1: a side-by-side on identical "
                 "input, not a fresh sample.",
        "design": "docs/whu-check-an-answer-pilot.md §12", "ledger_issue": ISSUE, "sample": v4c["sample"],
        "couldnt_check": {"v3": v4c["couldnt_check"]["v3"], "v4": v4c["couldnt_check"]["v4"], "v5": cc,
                          "rule_v5": "NOT FOUND IN THE PASSAGES CHECKED counted with COULDN'T CHECK for the bar; "
                                     "reported separately"},
        "agreement": {"v3": v4c["agreement"]["v3"], "v4": v4c["agreement"]["v4"], "v5": ag,
                      "rule": v4c["agreement"]["rule"]},
        "passages": {**v4c["passages"], "v5": {"verdicts": passages[0], "with_passage": passages[1]}},
        "usd": {**v4c["usd"], "v5": {"total": round(usd_total, 4), "per_answer": round(usd_total / n, 4),
                                     "stage1_v4": round(sum(a["usd_stage1_v4"] for a in per_answer), 4),
                                     "reread_v5": round(sum(a["usd_reread_v5"] for a in per_answer), 4),
                                     "ledger_v5": round(spent(), 4)}},
        "seconds": {**v4c["seconds"], "v5_measured_no_fetch": {"mean": round(secs, 1), "max": max(
            a["seconds_stage1_v4"] + a["seconds_reread_v5"] for a in per_answer)},
            "v5_plus_v3_fetch_reconstructed": {"mean": round(secs_bar, 1), "estimate": True}},
        "not_backed_by_path_v5": dict(by_path),
        "rereads_v5": dict(sorted(rereads.items())),
        "v4_disagreements": {"n": len(dis4), "resolved_by_v5": sum(p["v5"] == p["study"] for p in dis4),
                             "v5_labels": dict(Counter(p["v5"] for p in dis4)), "claims": dis4},
        "per_answer": per_answer,
    }
    out["pass_bar"] = {"v3": v4c["pass_bar"]["v3"], "v4": v4c["pass_bar"]["v4"],
                       "v5": R4.bars(cc, n, ag, tuple(passages), usd_total, secs_bar)}
    out["pass"] = {**v4c["pass"], "v5": all(out["pass_bar"]["v5"].values())}
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
