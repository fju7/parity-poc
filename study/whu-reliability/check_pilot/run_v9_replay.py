#!/usr/bin/env python3
"""v9's second read replayed on the fresh set's stored v8 passages (docs/whu-check-an-answer-pilot.md §17.5).
PARKED (advisor, 2026-11-05; §18): not to be run. The ledger issue has no budget line, so `run` stops before any call.
Development evidence, in sample: v9 was designed after the fresh set's results were seen. Nothing is fetched and no
source is re-read; the second read sees only the claim and passage.quote, so the replay is what v9 would have done
given v8's verdicts.

    run_v9_replay.py estimate                   free: likely and worst for every stored BACKED verdict
    run_v9_replay.py run --today X [--vp-planned Y]
                                                paid; stops before any call unless caps.json has a line for ISSUE
    run_v9_replay.py report                     free; refuses a partial set; writes check_pilot/v9_replay_counts.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fresh_judge as G  # noqa: E402
import pipeline_v9 as V9  # noqa: E402

F, R5, S = G.F, G.R5, G.S
ISSUE = "whu-check-v9-replay"
OUT = F.OUT / "v9_replay"
REPLIES = OUT / "replies"
COUNTS = HERE / "v9_replay_counts.json"
LIKELY_OUT = 250                       # the OpenAI judge's visible replies on the fresh set ran 64-263 output tokens
LABEL = ("Development evidence, in sample: v9 was designed after these results were seen; not a test. v9's second "
         "read replayed on v8's stored passages (no source re-read). Judged by AI models only; no human has checked "
         "the judgements. Blinding was partial: writing style allowed a model to identify systems, and WHU's scope "
         "notes were left in.")


def backed_rows() -> list[tuple[str, str, dict]]:
    """(question, system, row) for every BACKED verdict in the 18 stored v8 runs, in answer order."""
    out = []
    for q, s in F.sample():
        for r in json.loads((F.work(q, s) / "results.json").read_text())["results"]:
            if r.get("label") == V9.BACKED:
                out.append((q, s, r))
    return out


def reply_file(q: str, s: str, idx) -> Path:
    return REPLIES / ("%s-%s-%s.json" % (q, s, idx))


def call_usd(text: str, out_tokens: int) -> float:
    n_in = math.ceil(len(text) / F.P.CHARS_PER_TOKEN)
    return (n_in * V9.J.OPENAI_PRICE["input"] + out_tokens * V9.J.OPENAI_PRICE["output"]) / 1e6


def estimate(rows=None) -> dict:
    rows = backed_rows() if rows is None else rows
    likely = worst = 0.0
    for _, _, r in rows:
        t = V9.second_read_input(r["claim"], (r.get("passage") or {}).get("quote") or "")
        likely += call_usd(t, LIKELY_OUT)
        worst += V9.SECOND_READ_TRIES * call_usd(t, V9.SECOND_READ_MAX_OUT)
    return {"at": G.R.now(), "calls": len(rows), "likely_usd": round(likely, 4), "worst_usd": round(worst, 4),
            "worst_per_call_usd": round(worst / max(1, len(rows)) / V9.SECOND_READ_TRIES, 4),
            "basis": "chars/%.1f estimated input tokens; likely %d output tokens a call; worst %d output tokens on "
                     "every try (%d tries)" % (F.P.CHARS_PER_TOKEN, LIKELY_OUT, V9.SECOND_READ_MAX_OUT,
                                               V9.SECOND_READ_TRIES)}


def do_estimate(_a) -> int:
    est = estimate()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "estimate.json").write_text(json.dumps(est, indent=1))
    print("ESTIMATE: %d BACKED verdicts; likely $%.2f, worst $%.2f (%s)" % (est["calls"], est["likely_usd"],
                                                                         est["worst_usd"], est["basis"]))
    return 0


def spent(entries=None) -> float:
    return sum(e.get("usd") or 0 for e in (S.entries() if entries is None else entries) if e.get("issue") == ISSUE)


def do_run(a, call=None) -> int:
    cap = (S.caps().get("per_issue") or {}).get(ISSUE)
    if cap is None:
        print("STOP: no budget line for %s in caps.json; the replay is paid and needs its own approved line "
              "(§17.5); nothing was called" % ISSUE)
        return 5
    est_f = OUT / "estimate.json"
    if not est_f.exists():
        print("STOP: no estimate; run run_v9_replay.py estimate first; nothing was called")
        return 4
    est = json.loads(est_f.read_text())
    rows = [x for x in backed_rows() if not reply_file(x[0], x[1], x[2]["idx"]).exists()]
    likely_left = est["likely_usd"] * len(rows) / max(1, est["calls"])
    print("ESTIMATE: likely $%.2f, worst $%.2f (%s); %d left, likely $%.2f" % (
        est["likely_usd"], est["worst_usd"], est["at"], len(rows), likely_left))
    if spent() + likely_left > cap:
        print("STOP: spent $%.2f + likely $%.2f passes the $%.2f line; nothing was called" % (spent(), likely_left,
                                                                                          cap))
        return 5
    ok, why = R5.room(a.today + a.vp_planned, R5.today_total(), float(S.caps()["default_per_day"]))
    print("ROOM: %s" % why)
    if not ok:
        print("STOP: no room under the day cap; nothing was called")
        return 3
    stop_at = min(float(cap), spent() + a.today)
    call = call or V9.openai_call(V9.J.env_keys()["OPENAI_API_KEY"], ISSUE)
    REPLIES.mkdir(parents=True, exist_ok=True)
    for q, s, r in rows:
        if spent() + V9.SECOND_READ_TRIES * est["worst_per_call_usd"] > stop_at:
            print("STOP: the next read could pass $%.2f (spent $%.4f); replies kept, rerun to resume" % (stop_at,
                                                                                                   spent()))
            return 6
        sr = V9.second_read(r["claim"], (r.get("passage") or {}).get("quote") or "", call)
        reply_file(q, s, r["idx"]).write_text(json.dumps({"question": q, "system": s, "idx": r["idx"],
                                                          "second_read": sr}, indent=1))
        print("%s/%s %-4s %-40s $%.4f" % (q, s, r["idx"], V9.shown({**r, "second_read": sr}), sr["usd"]))
    print("%s spent: $%.4f" % (ISSUE, spent()))
    return 0


def report() -> dict:
    rows = backed_rows()
    missing = [x for x in rows if not reply_file(x[0], x[1], x[2]["idx"]).exists()]
    if missing:
        raise F.P.Stop("%d of %d BACKED verdicts have no second read: a partial set is not analysed"
                       % (len(missing), len(rows)))
    read = {}
    for q, s, r in rows:
        read["%s/%s" % (q, s), r["idx"]] = json.loads(reply_file(q, s, r["idx"]).read_text())["second_read"]
    shown = {k: V9.shown({"label": V9.BACKED, "second_read": v}) for k, v in read.items()}
    _, pairs = G.agree()
    v9 = []
    for p in pairs:
        sr = read.get((p["answer"], p["idx"]))
        lab = V9.score_label({"label": p["v8"], "second_read": sr}) if p["v8"] == V9.BACKED else p["v8"]
        v9.append({**p, "v8_label": p["v8"], "v8": lab,
                   "v9_shown": V9.shown({"label": p["v8"], "second_read": sr}) if sr else p["v8"]})
    keep = [p for p in v9 if p["v9_shown"] != V9.MAY_OVERSTATE]
    figs = {}
    for name, ps in (("v9_scored", v9), ("may_overstate_excluded", keep), ("v8_as_reported", pairs)):
        figs[name] = {k: {**G.share(ps, key), "ci95_over_answers": G.interval(ps, key),
                          "disagreement_counts": {d: len(x) for d, x in G.directions(ps, key).items()}}
                      for key, k in (("claude", "vs_claude_judge"), ("openai", "vs_openai_judge"),
                                     ("two_judges", "two_judge_agreed"))}
    both_supported = [p for p in v9 if p["v8_label"] == V9.BACKED and p["claude_raw"] == "Supported"
                      and p["openai_raw"] == "Supported"]
    flags = {}
    for v in shown.values():
        flags[v] = flags.get(v, 0) + 1
    return {
        "written": G.R.now(), "by": "study/whu-reliability/check_pilot/run_v9_replay.py report", "label": LABEL,
        "ledger_issue": ISSUE, "usd": round(spent(), 4), "prompt_sha256": V9.PROMPT_SHA256,
        "model": V9.SECOND_READ_MODEL,
        "second_read_on_all_backed": {"verdicts": len(rows), "shown": flags,
                                      "how": {h: sum(1 for v in read.values() if v.get("how") == h)
                                              for h in V9.HOW if h != "none"}},
        "agreement_on_stage2_sentences": figs,
        "flagged_where_both_judges_said_supported": {
            "items": len(both_supported), "flagged": sum(p["v9_shown"] == V9.MAY_OVERSTATE for p in both_supported)},
        "contested": {"items": sum(1 for p in pairs if p["claude"] in F.JUDGED and p["openai"] in F.JUDGED
                                   and p["claude"] != p["openai"]), "status": G.CONTESTED},
        "scoring": "§17.3: 'BACKED, but may overstate' counts as NOT BACKED; a read not done counts as COULDN'T CHECK",
        "ready": False,
        "ready_rule": "not applicable: in-sample development evidence. A v9 needs a new fresh set (§17.8)."}


def do_report(_a) -> int:
    out = report()
    COUNTS.write_text(json.dumps(out, indent=1) + "\n")
    for name, f in out["agreement_on_stage2_sentences"].items():
        for k, v in f.items():
            print("%-24s %-18s %3d of %3d = %s  CI %s  %s" % (name, k, v["agree"], v["n"], v["share"],
                                                            v["ci95_over_answers"], v["disagreement_counts"]))
    print(out["label"])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("estimate")
    sub.add_parser("report")
    r = sub.add_parser("run")
    r.add_argument("--today", type=float, required=True)
    r.add_argument("--vp-planned", type=float, default=0.0)
    a = ap.parse_args()
    return {"estimate": do_estimate, "run": do_run, "report": do_report}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
