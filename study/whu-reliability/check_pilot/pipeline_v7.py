#!/usr/bin/env python3
"""Check an AI answer, v7: v6 with window reads on Sonnet, all of an answer's windows at once
(docs/whu-check-an-answer-pilot.md §14).

v1-v6 are imported unchanged. v7 differs from v6 in two places, both in the window stage only:
  * (a) a window call (v6's `kind: window` job) uses WINDOW_MODEL (claude-sonnet-5-5); stage 1, v5's whole-source
    re-reads and v6's whole-source call on a windowed claim's short sources stay on judge_m1.CLAUDE_MODEL (Opus).
    Same windows, overlap, batching and M1-derived batched prompt (same sha256).
  * (b) the window stage's workers = the number of calls in the wave (v6: 8), so every window's first call is in
    flight together; further batches over a window still go after its first call (they read the cache).
Every window call records its start and end (monotonic seconds from the stage's start). §13.5's verdict rules are
v6's `decide`, unchanged: a failed window -> COULDN'T CHECK, never NOT BACKED.
Not wired into the preview: routers/whu_check.py stays on v2.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pipeline_v5 as V5
import pipeline_v6 as V6
from pipeline import BACKED, COULDNT, NO_SOURCE, NOT_BACKED, Stop  # noqa: F401
from pipeline_v5 import NOT_FOUND  # noqa: F401
from pipeline_v6 import WINDOWED  # noqa: F401

J, S = V6.J, V6.S
VERSION = 7
WINDOW_MODEL = "claude-sonnet-5-5"            # §14.2; Models API max_input_tokens 1,000,000, read 2026-11-02
MODEL_MAX_INPUT = 1_000_000


def worst_cost(n_in: int) -> float:
    """v6's worst case (every call a cache write + MAX_OUT output) at WINDOW_MODEL's prices."""
    p = S.PRICES[WINDOW_MODEL]
    return (n_in * p["cache_write"] + V6.MAX_OUT * p["output"]) / 1e6


def call_batch(client, prefix: str, rest: str) -> tuple[str, dict, float, bool]:
    """v6's call_batch on WINDOW_MODEL."""
    r = client.messages.create(
        model=WINDOW_MODEL, max_tokens=V6.MAX_OUT,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": rest}]}])
    text = "".join(getattr(b, "text", "") for b in r.content)
    usd, counts = S.price(getattr(r, "model", WINDOW_MODEL), r.usage)
    return text, {**counts, "model": r.model, "stop": r.stop_reason}, usd or 0.0, r.stop_reason == "refusal"


def plan_windows(targets: list[dict], man: dict, work: Path, count) -> tuple[list[dict], dict]:
    """v6's jobs and layout; a window job's worst case priced at WINDOW_MODEL's rates."""
    jobs, layout = V6.plan_windows(targets, man, work, count)
    for j in jobs:
        if j["kind"] == "window":
            j["worst"] = worst_cost(j["n_in"])
            j["model"] = WINDOW_MODEL
    return jobs, layout


def _run_job(job: dict, man: dict, client, before_call, t0: float) -> dict:
    """v6's _run_job, with a window call on WINDOW_MODEL and its start and end recorded."""
    start = time.monotonic() - t0
    if job["kind"] == "whole":
        r = V6._run_job(job, man, client, before_call)
    else:
        try:
            if before_call:
                before_call(job["worst"])
            text, usage, usd, refused = call_batch(client, job["prefix"], job["rest"])
        except Exception as e:                                           # noqa: BLE001
            r = {"usd": 0.0, "verdicts": {i: {"failure": "%s: %s" % (type(e).__name__, e)} for i in job["idx"]}}
        else:
            parsed = ({n: {"failure": "the judge refused"} for n in range(1, len(job["idx"]) + 1)} if refused
                      else V6.parse_batch(text, len(job["idx"])))
            r = {"usd": usd, "usage": usage, "raw": text,
                 "verdicts": {i: parsed[n] for n, i in enumerate(job["idx"], 1)}}
    return {**r, "start": round(start, 2), "end": round(time.monotonic() - t0, 2)}


def windowed_read(targets: list[dict], man: dict, work: Path, client, count, before_call=None,
                  workers: int | None = None, planned: tuple[list[dict], dict] | None = None
                  ) -> tuple[list[dict], list[dict], dict, float]:
    """(decided rows in TARGETS' order, job log, layout, the calls' wall seconds). Every first call over a window
    in one wave, all in flight together (WORKERS defaults to the wave's size); further batches after. PLANNED:
    plan_windows' result, if already made (so the windows are not counted twice)."""
    jobs, layout = planned or plan_windows(targets, man, work, count)
    first, rest = V5.waves(jobs)
    done, t0 = {}, time.monotonic()
    for wave in (first, rest):
        if not wave:
            continue
        with ThreadPoolExecutor(max_workers=workers or len(wave)) as ex:
            for j, r in zip(wave, ex.map(lambda j: _run_job(j, man, client, before_call, t0), wave)):
                done[id(j)] = r
    secs = round(time.monotonic() - t0, 1)
    per = {t["idx"]: [] for t in targets}
    log = []
    for j in jobs:
        r = done[id(j)]
        share = (r["usd"] or 0) / len(j["idx"])
        for i in j["idx"]:
            v = dict(r["verdicts"][i])
            v.update(job=j["label"], usd_share=round(share, 6), span_found=None)
            per[i].append(v)
        log.append({"job": j["label"], "kind": j["kind"], "model": j.get("model") or J.CLAUDE_MODEL, "idx": j["idx"],
                    "range": j.get("range"), "n_in": j.get("n_in"), "worst": round(j["worst"], 6),
                    "usd": round(r["usd"] or 0, 6), "usage": r.get("usage"), "start": r["start"], "end": r["end"],
                    "failures": sum(1 for v in r["verdicts"].values() if v.get("failure"))})
    rows = []
    for t in targets:
        vs = per[t["idx"]]
        for v in vs:
            if v.get("span") is not None and "label" in v:
                v["span_found"] = V6.V3.passage(v["span"], t["full_docs"]) is not None
        rows.append(V6.decide(t, vs, man))
    return rows, log, {k: {**v, "windows": [list(w) for w in v["windows"]]} for k, v in layout.items()}, secs


plan_v7 = V6.plan_v6
public = V5.public
