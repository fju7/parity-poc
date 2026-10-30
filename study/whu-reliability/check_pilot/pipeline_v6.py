#!/usr/bin/env python3
"""Check an AI answer, v6: a windowed whole-source read for long sources (docs/whu-check-an-answer-pilot.md §13).

v1, v3, v4 and v5 are imported unchanged. v6 differs from v5 in one place: a claim v5 would send to its
passages-checked path (a stage-1 NOT BACKED citing a source over judge_m1.MAX_SOURCE_TOKENS) is read against the
whole source in overlapping windows instead.

  * Windows: WINDOW_TOKENS (= judge_m1.MAX_SOURCE_TOKENS) each, overlapping by at least OVERLAP_TOKENS, on
    passage_index boundaries, every one measured with count_tokens. Every window is read.
  * Batching: the claims citing one long source go into each window's call, at most BATCH per call; further calls
    over the same window read it from the prompt cache (the first runs alone, the rest after it).
  * The batched prompt is DERIVED from the frozen M1 file (sha256 checked) by the edits in M1_EDITS, each of which
    must match exactly once; no prompt text lives here.
  * BACKED if any window backs the claim; NOT BACKED only if every window was read and none backs it; a window that
    failed or was skipped -> COULDN'T CHECK, never NOT BACKED.
Not wired into the preview: routers/whu_check.py stays on v2.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pipeline as V1
import pipeline_v3 as V3
import pipeline_v4 as V4
import pipeline_v5 as V5
from pipeline import BACKED, COULDNT, NO_SOURCE, NOT_BACKED, Stop  # noqa: F401
from pipeline_v5 import NOT_FOUND  # noqa: F401

J, S, PI = V1.J, V1.S, V4.PI
VERSION = 6
WINDOW_TOKENS = J.MAX_SOURCE_TOKENS          # §13.3: 150,000, the most the study's judge read in one call
OVERLAP_TOKENS = 2_000                        # §13.3: at least this much between consecutive windows
MODEL_MAX_INPUT = 1_000_000                   # Models API max_input_tokens for claude-opus-5-5, read 2026-10-30
BATCH = 20                                    # §13.4: at most 20 claims per call
MAX_OUT = 300 * BATCH                         # one span (<= 300 chars) and one sentence per claim, with room
WINDOWED = "windowed whole source"
R_WINDOW = "a window of the source was not read"
ORDER = ("Contradicted", "Wrong source", "Overstates", "Understates", "Absent")     # M1's own order

# The batched prompt: M1 with these edits only (old text, new text). Each must occur exactly once in M1.
M1_EDITS = (
    ("The documents below are the sources one sentence cites. After them come the sentence and your instructions.",
     "The document below is one part of a long source that each of the numbered sentences after it cites. After it "
     "come the sentences and your instructions."),
    ("THE SENTENCE (the claim to check):\n<<<CLAIM\n{claim}\nCLAIM>>>\n\nTEXT JUST BEFORE THE SENTENCE, for context "
     "only (it is not being checked; use it only to understand what the sentence refers to):\n<<<CONTEXT\n{context}\n"
     "CONTEXT>>>",
     "THE SENTENCES (each a claim to check, numbered; each is followed by the text just before it, for context only: "
     "the context is not being checked; use it only to understand what the sentence refers to):\n{claims}"),
    ("You are checking this one sentence against the document or documents above.",
     "You are checking each numbered sentence, separately and on its own, against the document above."),
    ("Give exactly one label:", "Give exactly one label for each sentence:"),
    ('Reply with ONE JSON object and nothing else, no code fence, in exactly this form:\n{"label": "<one of the seven '
     'labels, spelled as above>", "span": "<an exact quotation, copied character for character from one of the '
     'documents, of at most 300 characters, that your label rests on>", "reason": "<one sentence>"}',
     'Reply with ONE JSON object and nothing else, no code fence, with one entry for every numbered sentence, keyed '
     'by its number, in exactly this form:\n{"1": {"label": "<one of the seven labels, spelled as above>", "span": '
     '"<an exact quotation, copied character for character from the document, of at most 300 characters, that your '
     'label rests on>", "reason": "<one sentence>"}, "2": {...}}'),
)


def batched_prompt() -> str:
    """M1, sha256 checked, with M1_EDITS applied; stops if an edit does not match exactly once."""
    V1.prompt_ok()
    t = J.PROMPT.read_text(encoding="utf-8")
    for old, new in M1_EDITS:
        n = t.count(old)
        if n != 1:
            raise Stop("M1 edit matches %d times, not once: %r" % (n, old[:60]))
        t = t.replace(old, new)
    return t


def batched_prompt_sha() -> str:
    return hashlib.sha256(batched_prompt().encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Windows
# --------------------------------------------------------------------------

def windows(text: str, count, size: int | None = None, overlap: int | None = None) -> list[tuple[int, int]]:
    """Character ranges covering TEXT, on passage boundaries, each <= SIZE tokens, consecutive ones sharing
    >= OVERLAP tokens. Sizes are estimated from the text's own token/character ratio, then measured."""
    size, overlap = size or WINDOW_TOKENS, overlap or OVERLAP_TOKENS
    ps = PI.index_of(text).passages
    if not ps:
        return []
    ratio = count(text) / max(len(text), 1)
    est = lambda a, b: (b - a) * ratio                                   # noqa: E731
    out, i = [], 0
    while True:
        j = i
        while j + 1 < len(ps) and est(ps[i].start, ps[j + 1].end) <= size:
            j += 1
        while j > i and count(text[ps[i].start:ps[j].end]) > size:      # measured: shrink until it fits
            j -= 1
        out.append((ps[i].start, ps[j].end))
        if j == len(ps) - 1:
            return out
        k = j
        while k > i + 1 and count(text[ps[k].start:ps[j].end]) < overlap:
            k -= 1                                                       # back until the overlap is enough
        if count(text[ps[k].start:ps[j].end]) < overlap:
            raise Stop("window size %d cannot hold an overlap of %d tokens" % (size, overlap))
        i = k


def window_doc(d: dict, text: str, w: tuple[int, int], i: int, n: int, count) -> dict:
    a, b = w
    part = text[a:b]
    return {"source_id": d["source_id"], "url": d["url"], "abstract_only": False, "chunked": False,
            "extent": "%s; part %d of %d of a long document (characters %d-%d)" % (d["extent"], i, n, a, b),
            "text": part, "tokens": count(part), "window": [a, b]}


# --------------------------------------------------------------------------
# One batched call
# --------------------------------------------------------------------------

def claims_block(claims: list[dict]) -> str:
    out = []
    for n, c in enumerate(claims, 1):
        ctx = c.get("context") or ""
        if len(ctx) > J.CONTEXT_CHARS:
            ctx = "…" + ctx[-J.CONTEXT_CHARS:].lstrip()
        out.append("<<<CLAIM %d\n%s\nCLAIM %d>>>\n<<<CONTEXT %d\n%s\nCONTEXT %d>>>" % (n, c["claim"], n, n, ctx, n))
    return "\n\n".join(out)


def build_batch(doc: dict, claims: list[dict]) -> tuple[str, str]:
    """(cacheable prefix: the prompt up to and including the window, rest: the numbered claims and instructions)."""
    head, tail = batched_prompt().split("{documents}", 1)
    return head + J.documents_block([doc]), tail.replace("{claims}", claims_block(claims))


def worst_cost(n_in: int) -> float:
    p = S.PRICES[J.CLAUDE_MODEL]
    return (n_in * p["cache_write"] + MAX_OUT * p["output"]) / 1e6


def call_batch(client, prefix: str, rest: str) -> tuple[str, dict, float, bool]:
    """judge_m1.call_claude's request, with room for one reply per claim."""
    r = client.messages.create(
        model=J.CLAUDE_MODEL, max_tokens=MAX_OUT,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": rest}]}])
    text = "".join(getattr(b, "text", "") for b in r.content)
    usd, counts = S.price(getattr(r, "model", J.CLAUDE_MODEL), r.usage)
    return text, {**counts, "model": r.model, "stop": r.stop_reason}, usd or 0.0, r.stop_reason == "refusal"


def parse_batch(text: str, n: int) -> dict[int, dict]:
    """{claim number: {label, span, reason} or {failure}} for 1..n."""
    s = re.sub(r"^```(json)?\s*|\s*```$", "", text.strip())
    try:
        obj = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        try:
            obj = json.loads(m.group(0)) if m else None
        except Exception:
            obj = None
    out = {}
    for i in range(1, n + 1):
        e = obj.get(str(i)) if isinstance(obj, dict) else None
        if not isinstance(e, dict):
            out[i] = {"failure": "no reply for this claim" if isinstance(obj, dict) else "reply did not parse"}
        elif e.get("label") not in J.LABELS:
            out[i] = {"failure": "label %r not in the label set" % e.get("label")}
        elif e["label"] == "Unreachable":
            out[i] = {"failure": "the judge read the window as Unreachable"}
        else:
            out[i] = {"label": e["label"], "span": e.get("span") or "", "reason": e.get("reason") or ""}
    return out


# --------------------------------------------------------------------------
# Plan, run, decide
# --------------------------------------------------------------------------

def is_target(p: dict) -> bool:
    """A planned v5 row that v5 sends to its passages-checked path (§13.2)."""
    return p.get("path") == V5.EXPANDED


def plan_windows(targets: list[dict], man: dict, work: Path, count) -> tuple[list[dict], dict]:
    """(jobs, layout): one job per (long source, window, batch of <= BATCH claims); plus, for a claim that also
    cites sources within the limit, one v5 whole-source call on those (§13.5)."""
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
        ws = windows(d["text"], count)
        layout[sid] = {"tokens": d.get("tokens") or count(d["text"]), "windows": ws, "claims": [t["idx"] for t in ts]}
        for i, w in enumerate(ws, 1):
            doc = window_doc(d, d["text"], w, i, len(ws), count)
            for b in range(0, len(ts), BATCH):
                batch = ts[b:b + BATCH]
                prefix, rest = build_batch(doc, batch)
                n_in = count(prefix + rest)
                jobs.append({"kind": "window", "source_id": sid, "window": i, "of": len(ws), "range": list(w),
                             "idx": [t["idx"] for t in batch], "prefix": prefix, "rest": rest, "n_in": n_in,
                             "worst": worst_cost(n_in), "label": "window %d of %d of %s" % (i, len(ws), sid)})
    return jobs, layout


def _run_job(job: dict, man: dict, client, before_call) -> dict:
    """{idx: verdict} for one job; any exception is a failure for every claim in it (never a verdict)."""
    if job["kind"] == "whole":
        try:
            r = V5._one(job["planned"], man, client, before_call)
        except Exception as e:                                           # noqa: BLE001
            return {"usd": 0.0, "verdicts": {job["idx"][0]: {"failure": "%s: %s" % (type(e).__name__, e)}}}
        m1 = r.get("study_label")
        v = ({"label": m1, "span": r.get("span") or "", "reason": r.get("reason") or ""}
             if m1 == "Supported" or m1 in V1.STUDY_CITED_FAIL else {"failure": r.get("reason") or "not judged"})
        return {"usd": r.get("usd_reread") or 0.0, "verdicts": {job["idx"][0]: v}}
    try:
        if before_call:
            before_call(job["worst"])
        text, usage, usd, refused = call_batch(client, job["prefix"], job["rest"])
    except Exception as e:                                               # noqa: BLE001
        return {"usd": 0.0, "verdicts": {i: {"failure": "%s: %s" % (type(e).__name__, e)} for i in job["idx"]}}
    if refused:
        parsed = {n: {"failure": "the judge refused"} for n in range(1, len(job["idx"]) + 1)}
    else:
        parsed = parse_batch(text, len(job["idx"]))
    return {"usd": usd, "usage": usage, "raw": text,
            "verdicts": {i: parsed[n] for n, i in enumerate(job["idx"], 1)}}


def decide(t: dict, verdicts: list[dict], man: dict) -> dict:
    """§13.5 on one claim's window verdicts."""
    full = t["full_docs"]
    for d in full:
        d.setdefault("retrieved_from", (man.get(d["url"]) or {}).get("retrieved_from"))
    base = {k: v for k, v in t.items() if k not in V5._HIDDEN + ("path", "expanded", "label", "reason")}
    row = {**base, "decided_by": WINDOWED, "windows": verdicts, "stage1": t["stage1"],
           "usd_reread": round(sum(v.get("usd_share") or 0 for v in verdicts), 6)}
    row["usd"] = round((t["stage1"].get("usd") or 0) + row["usd_reread"], 6)
    backs = [v for v in verdicts if v.get("label") == "Supported"]
    for v in backs:
        p = V3.passage(v["span"], full)
        if p:
            return {**row, "label": BACKED, "reason": "Supported: %s" % v["reason"], "study_label": "Supported",
                    "span": v["span"], "passage": p, "reason_kind": None}
    if backs:
        return {**row, "label": COULDNT, "reason": "no passage to show: a window backs it but its quotation was not "
                "found in the text", "study_label": "Supported", "reason_kind": V3.R_NOPASSAGE}
    failed = [v for v in verdicts if v.get("failure")]
    if failed:
        return {**row, "label": COULDNT, "reason": "%s (%s)" % (R_WINDOW, failed[0]["failure"]),
                "study_label": None, "reason_kind": R_WINDOW}
    for lab in ORDER:
        for v in verdicts:
            if v.get("label") == lab:
                p = V3.passage(v["span"], full)
                if p:
                    return {**row, "label": NOT_BACKED, "reason": "%s: %s" % (lab, v["reason"]), "study_label": lab,
                            "span": v["span"], "passage": p, "reason_kind": None}
    return {**row, "label": COULDNT, "reason": "no passage to show: no window's quotation was found in the text",
            "study_label": verdicts[0].get("label") if verdicts else None, "reason_kind": V3.R_NOPASSAGE}


def windowed_read(targets: list[dict], man: dict, work: Path, client, count, before_call=None,
                  workers: int = 8) -> tuple[list[dict], list[dict], dict]:
    """(decided rows in TARGETS' order, job log, layout). Jobs over one window: the first alone, the rest after."""
    jobs, layout = plan_windows(targets, man, work, count)
    first, rest = V5.waves(jobs)
    done = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for wave in (first, rest):
            for j, r in zip(wave, ex.map(lambda j: _run_job(j, man, client, before_call), wave)):
                done[id(j)] = r
    per = {t["idx"]: [] for t in targets}
    log = []
    for j in jobs:
        r = done[id(j)]
        share = (r["usd"] or 0) / len(j["idx"])
        for i in j["idx"]:
            v = dict(r["verdicts"][i])
            v.update(job=j["label"], usd_share=round(share, 6), span_found=None)
            per[i].append(v)
        log.append({"job": j["label"], "kind": j["kind"], "idx": j["idx"], "range": j.get("range"),
                    "n_in": j.get("n_in"), "worst": round(j["worst"], 6), "usd": round(r["usd"] or 0, 6),
                    "usage": r.get("usage"), "failures": sum(1 for v in r["verdicts"].values() if v.get("failure"))})
    rows = []
    for t in targets:
        vs = per[t["idx"]]
        for v in vs:
            if v.get("span") is not None and "label" in v:
                v["span_found"] = V3.passage(v["span"], t["full_docs"]) is not None
        rows.append(decide(t, vs, man))
    return rows, log, {k: {**v, "windows": [list(w) for w in v["windows"]]} for k, v in layout.items()}


def plan_v6(stage1: list[dict], man: dict, work: Path, count) -> list[dict]:
    """v5's plan; rows v5 would read on its passages-checked path are marked for the windowed read."""
    return [{**p, "windowed": True} if is_target(p) else p for p in V5.plan_v5(stage1, man, work, count)]


def worst_usd(planned: list[dict], man: dict, work: Path, count) -> tuple[float, list[dict], dict]:
    """(worst case of every call v6 would make, the window jobs, the layout): v5's re-reads plus the window jobs."""
    plain = [p for p in planned if p.get("label") is None and p.get("path") and not p.get("windowed")]
    jobs, layout = plan_windows([p for p in planned if p.get("windowed")], man, work, count)
    return round(V5.worst_usd(plain) + sum(j["worst"] for j in jobs), 4), jobs, layout


def check(text: str, work: Path, client, count, fmt: str | None = None, system: str = "answer",
          net: dict | None = None, selected: list[int] | None = None, before_call=None) -> dict:
    """v4's stage 1, v5's whole-source re-reads, and the windowed read for long sources."""
    t0 = time.time()
    prep = V4.prepare(text, work, fmt, count, system, net, selected)
    stage1 = V4.judge_v4(prep["planned"], prep["manifest"], work, client, before_call)
    planned = plan_v6(stage1, prep["manifest"], work, count)
    plain = V5.fuller_read([p for p in planned if not p.get("windowed")], prep["manifest"], client, before_call)
    win, log, layout = windowed_read([p for p in planned if p.get("windowed")], prep["manifest"], work, client,
                                     count, before_call)
    by = {r["idx"]: r for r in plain + win}
    results = [{k: v for k, v in by[p["idx"]].items() if k not in V5._HIDDEN + ("windowed",)} for p in planned]
    return {**{k: v for k, v in prep.items() if k != "planned"}, "version": VERSION, "results": results,
            "windows": layout, "jobs": log, "summary": V5.summary(results, prep["found"]),
            "seconds": round(time.time() - t0, 1)}


public = V5.public
