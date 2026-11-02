#!/usr/bin/env python3
"""Check an AI answer, v8: v6's Opus window reads, read at once, planned without API token counts
(docs/whu-check-an-answer-pilot.md §15).

v1-v7 are imported unchanged. v8 reads and decides exactly as v6 (stage 1 = v4, re-reads = v5, the windowed
whole-source read and §13.5's verdict rules = v6, the same M1-derived batched prompt), with three changes:
  * window reads on judge_m1.CLAUDE_MODEL (Opus), as v6; v7's Sonnet is set aside (§14.10);
  * v7's concurrency: every first call over a window in flight together, per-call start and end recorded;
  * no count_tokens call anywhere: LocalCount estimates ceil(chars / CHARS_PER_TOKEN), cached by sha256; windows
    are at most WINDOW_EST estimated tokens. Nothing is cut on the estimate: every call's true input size is taken
    from the response's usage and a call over the study's read size is flagged over_limit, its verdict kept.
Not wired into the preview: routers/whu_check.py stays on v2.
"""
from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pipeline_v4 as V4
import pipeline_v5 as V5
import pipeline_v6 as V6
from pipeline import BACKED, COULDNT, NO_SOURCE, NOT_BACKED, Stop  # noqa: F401
from pipeline_v5 import NOT_FOUND  # noqa: F401
from pipeline_v6 import WINDOWED  # noqa: F401

J, S, PI = V6.J, V6.S, V6.PI
VERSION = 8
CHARS_PER_TOKEN = 1.9            # §15.3: below every ratio measured on the pilot (1.99-2.80); fixed before the fresh set
ESTIMATOR = "chars/1.9 v1"
WINDOW_EST = 140_000             # §15.4: estimated tokens per window, a margin under judge_m1.MAX_SOURCE_TOKENS
PROMPT_ALLOWANCE = 10_000        # §15.5: prompt, claims and context on top of the source text, for over_limit


class LocalCount:
    """count(text) -> estimated tokens, no API call. Cached by sha256 of the text (and ESTIMATOR) in memory and, if
    PATH is given, in a JSON file, so a text is measured once and the figure used is the figure recorded."""

    def __init__(self, path: Path | None = None):
        self.path, self.lock, self.computed = path, threading.Lock(), 0
        self.cache: dict[str, int] = {}
        if path and path.exists():
            self.cache = json.loads(path.read_text())

    @staticmethod
    def estimate(text: str) -> int:
        return math.ceil(len(text) / CHARS_PER_TOKEN)

    def __call__(self, text: str) -> int:
        key = "%s:%s" % (ESTIMATOR, hashlib.sha256(text.encode("utf-8")).hexdigest())
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        n = self.estimate(text)
        with self.lock:
            self.cache[key] = n
            self.computed += 1
        return n

    def save(self) -> None:
        if self.path:
            with self.lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.cache, sort_keys=True))


class SizeLog:
    """A client wrapper recording each call's estimated and true input size (usage: input + cache write + cache read);
    over_limit when the true size passes judge_m1.MAX_SOURCE_TOKENS + PROMPT_ALLOWANCE (§15.5)."""

    def __init__(self, client, count):
        self.client, self.count, self.calls, self.lock = client, count, [], threading.Lock()
        self.messages = self

    def __getattr__(self, name):
        return getattr(self.client, name)

    def create(self, **kw):
        text = "".join(b.get("text", "") if isinstance(b, dict) else str(b)
                       for m in kw.get("messages", []) for b in (m["content"] if isinstance(m["content"], list)
                                                                 else [{"text": m["content"]}]))
        r = self.client.messages.create(**kw)
        u = getattr(r, "usage", None)
        true = sum(int(getattr(u, k, 0) or 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                       "cache_read_input_tokens"))
        with self.lock:
            self.calls.append({"model": kw.get("model"), "est_input": self.count(text), "true_input": true,
                               "over_limit": true > J.MAX_SOURCE_TOKENS + PROMPT_ALLOWANCE})
        return r


def plan_windows(targets: list[dict], man: dict, work: Path, count) -> tuple[list[dict], dict]:
    """v6's plan_windows with windows of at most WINDOW_EST estimated tokens (the only difference)."""
    long_of, jobs, layout = {}, [], {}
    for t in targets:
        short = []
        for d in t["full_docs"]:
            if (d.get("tokens") or count(d["text"])) > J.MAX_SOURCE_TOKENS:
                long_of.setdefault(d["source_id"], (d, []))[1].append(t)
            else:
                short.append(d["url"])
        if short:
            sub = {**{k: v for k, v in t.items() if k not in V5._HIDDEN + ("path", "expanded", "stage1")},
                   "citations": [ct for ct in t["citations"] if ct.get("url") in short]}
            p = V5.plan_reread({**sub, "study_label": t["stage1"]["study_label"]}, man, work, count)
            jobs.append({"kind": "whole", "idx": [t["idx"]], "planned": p, "prefix": p["prefix"], "worst": p["worst"],
                         "label": "whole: %d source(s) within the limit" % len(short)})
    for sid, (d, ts) in long_of.items():
        ws = V6.windows(d["text"], count, size=WINDOW_EST)
        layout[sid] = {"tokens_est": d.get("tokens") or count(d["text"]), "windows": ws,
                       "claims": [t["idx"] for t in ts]}
        for i, w in enumerate(ws, 1):
            doc = V6.window_doc(d, d["text"], w, i, len(ws), count)
            for b in range(0, len(ts), V6.BATCH):
                batch = ts[b:b + V6.BATCH]
                prefix, rest = V6.build_batch(doc, batch)
                n_in = count(prefix + rest)
                jobs.append({"kind": "window", "source_id": sid, "window": i, "of": len(ws), "range": list(w),
                             "idx": [t["idx"] for t in batch], "prefix": prefix, "rest": rest, "n_in": n_in,
                             "worst": V6.worst_cost(n_in), "label": "window %d of %d of %s" % (i, len(ws), sid)})
    return jobs, layout


def _run_job(job: dict, man: dict, client, before_call, t0: float) -> dict:
    start = time.monotonic() - t0
    r = V6._run_job(job, man, client, before_call)              # v6's call: judge_m1.CLAUDE_MODEL, v6's parsing
    return {**r, "start": round(start, 2), "end": round(time.monotonic() - t0, 2)}


def windowed_read(targets: list[dict], man: dict, work: Path, client, count, before_call=None,
                  workers: int | None = None, planned: tuple[list[dict], dict] | None = None
                  ) -> tuple[list[dict], list[dict], dict, float]:
    """(decided rows in TARGETS' order, job log, layout, the calls' wall seconds). Every first call over a window in
    one wave, all in flight together; further batches after (they read the cache)."""
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
        u = r.get("usage") or {}
        true = sum(u.get(k) or 0 for k in ("input", "cache_write", "cache_read")) if u else None
        log.append({"job": j["label"], "kind": j["kind"], "model": J.CLAUDE_MODEL, "idx": j["idx"],
                    "range": j.get("range"), "n_in_est": j.get("n_in"), "n_in_true": true,
                    "over_limit": bool(true and true > J.MAX_SOURCE_TOKENS + PROMPT_ALLOWANCE),
                    "worst": round(j["worst"], 6), "usd": round(r["usd"] or 0, 6), "usage": r.get("usage"),
                    "start": r["start"], "end": r["end"],
                    "failures": sum(1 for v in r["verdicts"].values() if v.get("failure"))})
    rows = []
    for t in targets:
        vs = per[t["idx"]]
        for v in vs:
            if v.get("span") is not None and "label" in v:
                v["span_found"] = V6.V3.passage(v["span"], t["full_docs"]) is not None
        rows.append(V6.decide(t, vs, man))
    return rows, log, {k: {**v, "windows": [list(w) for w in v["windows"]]} for k, v in layout.items()}, secs


def check(text: str, work: Path, client, fmt: str | None = None, system: str = "answer", net: dict | None = None,
          selected: list[int] | None = None, before_call=None, count: LocalCount | None = None) -> dict:
    """v6's check with v8's planning and window stage; wall time for the whole answer, measured (§15.7)."""
    t0 = time.time()
    count = count or LocalCount(work / "token_counts.json")
    sized = SizeLog(client, count)
    prep = V4.prepare(text, work, fmt, count, system, net, selected)
    stage1 = V4.judge_v4(prep["planned"], prep["manifest"], work, sized, before_call)
    planned = V6.plan_v6(stage1, prep["manifest"], work, count)
    plain = V5.fuller_read([p for p in planned if not p.get("windowed")], prep["manifest"], sized, before_call)
    win, log, layout, win_secs = windowed_read([p for p in planned if p.get("windowed")], prep["manifest"], work,
                                               sized, count, before_call)
    count.save()
    by = {r["idx"]: r for r in plain + win}
    results = [{k: v for k, v in by[p["idx"]].items() if k not in V5._HIDDEN + ("windowed",)} for p in planned]
    return {**{k: v for k, v in prep.items() if k != "planned"}, "version": VERSION, "results": results,
            "windows": layout, "jobs": log, "calls": sized.calls,
            "over_limit": [c for c in sized.calls if c["over_limit"]], "summary": V5.summary(results, prep["found"]),
            "seconds_windows": win_secs, "seconds": round(time.time() - t0, 1), "estimator": ESTIMATOR}


public = V5.public
