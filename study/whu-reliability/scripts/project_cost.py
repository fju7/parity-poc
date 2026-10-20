#!/usr/bin/env python3
"""Project full-study judging cost with prompt caching, from measured M1 calls.

Usage: project_cost.py RUN_DIR

Run 1 of each item is priced as measured (Claude writes the source block to
the cache; OpenAI reads whatever it already had). Run 2 is priced from the
same call's measured token counts with the source block read from cache, at
each API's cached rate. The cache probe (replies-cacheprobe2) is the check on
that estimate. Source size enters only through the source block, so "2x"
doubles the cached and cache-written tokens and leaves the rest alone.

M2 is an estimate (no M2 call has been made): the answer is cached once per
answer and read by its other nine calls (5 conclusions x 2 runs).

"as ruled" (budget ruling, protocol rev 26, 20 October 2026): four questions,
the same number of items judged (320 M1 claims; M2's 160 conclusions as 16
answers x 10), each judge reading each item once, and a seeded 20% read a
second time straight after the first (judge_m1.py), so a second read is an
identical prompt with its source block in cache: priced as run 2 above, which
the cache probe measured. OpenAI caches only an identical prompt (prep round 3
bias test: 16 of 64 calls hit, all of them the identical repeat), so an M2
answer's ten conclusions are each priced uncached on OpenAI, and only the
repeat of a conclusion is cached."""
import glob, importlib.util, json, statistics as st, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("judge_m1", HERE / "judge_m1.py"); J = importlib.util.module_from_spec(spec); spec.loader.exec_module(J)
run = Path(sys.argv[1])
P = J.S.PRICES[J.CLAUDE_MODEL]; O = J.OPENAI_PRICE
M1_ITEMS, M2_ANSWERS, M2_CALLS_PER_ANSWER = 320, 32, 10
RULED_M2_ANSWERS, RULED_M2_CONCLUSIONS, REPEAT_SHARE = 16, 10, 0.20


def claude_runs(u, scale):
    src = (u.get("cache_write") or 0) + (u.get("cache_read") or 0)
    rest, out = u.get("input") or 0, u.get("output") or 0
    r1 = (src * scale * P["cache_write"] + rest * P["input"] + out * P["output"]) / 1e6
    r2 = (src * scale * P["cache_read"] + rest * P["input"] + out * P["output"]) / 1e6
    return r1, r2


def openai_runs(u, scale):
    inp, out = u.get("input") or 0, u.get("output") or 0
    rest = 1500                      # the part after the documents, which is never cached
    src = max(inp - rest, 0)
    r1 = (src * scale * O["input"] + rest * O["input"] + out * O["output"]) / 1e6
    r2 = (src * scale * O["cached_input"] + rest * O["input"] + out * O["output"]) / 1e6
    return r1, r2


def m1(judge, scale):
    per = []
    for f in sorted(glob.glob(str(run / "replies" / judge / "*.json"))):
        d = json.load(open(f))
        u = d["attempts"][0]["usage"]
        r1, r2 = (claude_runs if judge == "claude" else openai_runs)(u, scale)
        extra = sum(a["usd"] for a in d["attempts"][1:])     # a refusal's retry, as measured
        per.append(r1 + r2 + extra)
    return M1_ITEMS * st.mean(per), st.mean(per) / 2


def m1_ruled(judge, scale):
    per = []
    for f in sorted(glob.glob(str(run / "replies" / judge / "*.json"))):
        d = json.load(open(f))
        r1, _r2 = (claude_runs if judge == "claude" else openai_runs)(d["attempts"][0]["usage"], scale)
        per.append((r1, _r2, sum(a["usd"] for a in d["attempts"][1:])))
    first = st.mean(r1 + extra for r1, _r2, extra in per)
    again = st.mean(r2 for _r1, r2, _e in per)
    return M1_ITEMS * (first + REPEAT_SHARE * again), first


def m2_parts(judge):
    ans_chars, rest_chars, out = 18000 + 400, 4200, (300 if judge == "claude" else 400)
    c = 2.5 if judge == "claude" else 4.0
    a, r = ans_chars / c, rest_chars / c
    if judge == "claude":
        first = (a * P["cache_write"] + r * P["input"] + out * P["output"]) / 1e6
        later = (a * P["cache_read"] + r * P["input"] + out * P["output"]) / 1e6
    else:
        first = (a * O["input"] + r * O["input"] + out * O["output"]) / 1e6
        later = first                  # a different conclusion is not an identical prompt
    return first, later


def m2_repeat(judge):
    """The second read of one conclusion, straight after the first: identical."""
    ans_chars, rest_chars, out = 18000 + 400, 4200, (300 if judge == "claude" else 400)
    if judge == "claude":
        a, r = ans_chars / 2.5, rest_chars / 2.5
        return (a * P["cache_read"] + r * P["input"] + out * P["output"]) / 1e6
    return ((ans_chars + rest_chars) / 4.0 * O["cached_input"] + out * O["output"]) / 1e6


def m2_ruled(judge):
    first, later = m2_parts(judge)
    main = RULED_M2_ANSWERS * (first + (RULED_M2_CONCLUSIONS - 1) * later)
    repeats = REPEAT_SHARE * RULED_M2_ANSWERS * RULED_M2_CONCLUSIONS * m2_repeat(judge)
    return main + repeats


def m2(judge):
    ans_chars, rest_chars, out = 18000 + 400, 4200, (300 if judge == "claude" else 400)
    if judge == "claude":
        a, r = ans_chars / 2.5, rest_chars / 2.5
        first = (a * P["cache_write"] + r * P["input"] + out * P["output"]) / 1e6
        later = (a * P["cache_read"] + r * P["input"] + out * P["output"]) / 1e6
    else:
        a, r = ans_chars / 4.0, rest_chars / 4.0
        first = (a * O["input"] + r * O["input"] + out * O["output"]) / 1e6
        later = (a * O["cached_input"] + r * O["input"] + out * O["output"]) / 1e6
    return M2_ANSWERS * (first + (M2_CALLS_PER_ANSWER - 1) * later)


out = {}
for scale in (1, 2):
    row = {}
    for j in ("claude", "openai"):
        tot, per_call = m1(j, scale)
        row[j] = {"m1": round(tot, 2), "m1_per_call_avg": round(per_call, 4), "m2": round(m2(j), 2)}
    row["total"] = round(sum(row[j]["m1"] + row[j]["m2"] for j in ("claude", "openai")), 2)
    out["pilot-sized sources" if scale == 1 else "sources 2x pilot"] = row
for scale in (1, 2):
    row = {}
    for j in ("claude", "openai"):
        tot, per_call = m1_ruled(j, scale)
        row[j] = {"m1": round(tot, 2), "m1_first_read_per_item": round(per_call, 4), "m2": round(m2_ruled(j), 2),
                  "m1_repeat_per_item": round((m1_ruled(j, scale)[0] / M1_ITEMS - per_call) / REPEAT_SHARE, 4),
                  "m2_first_call": round(m2_parts(j)[0], 4), "m2_later_conclusion": round(m2_parts(j)[1], 4),
                  "m2_repeat": round(m2_repeat(j), 4)}
    row["total"] = round(sum(row[j]["m1"] + row[j]["m2"] for j in ("claude", "openai")), 2)
    out["as ruled, " + ("pilot-sized sources" if scale == 1 else "sources 2x pilot")] = row
print(json.dumps(out, indent=1))
