#!/usr/bin/env python3
"""Check an AI answer, v5: a NOT BACKED verdict needs a fuller read (docs/whu-check-an-answer-pilot.md §12).

v1, v3 and v4 are imported unchanged; no prompt is copied (the judge only through judge_m1, by v1's judge).

  * Stage 1 is v4: the judge reads the retrieved passages. A BACKED verdict from them stands; so do
    COULDN'T CHECK and NO SOURCE.
  * A stage-1 NOT BACKED label (Overstates, Understates, Absent, Wrong source, Contradicted -- including one
    withheld as "no passage to show") is judged again, and that reading is the verdict:
      - every cited source within judge_m1.MAX_SOURCE_TOKENS: against the whole held source(s), v3's
        documents and prompt exactly (pipeline._docs, judge_m1.build; the prefix prompt-cached);
      - a source over it: its top EXPAND_K passages for the claim plus each one's neighbours (sources under
        the limit whole). Supported -> BACKED; a NOT BACKED label -> NOT FOUND IN THE PASSAGES CHECKED, never
        counted as NOT BACKED.
  * Every row records `decided_by` and, when re-judged, stage 1's verdict (`stage1`).
  * Re-reads sharing a cached prefix are ordered: the first alone, the rest after it.
Not wired into the preview: routers/whu_check.py stays on v2.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pipeline as V1
import pipeline_v3 as V3
import pipeline_v4 as V4
from pipeline import BACKED, COULDNT, LABELS, NO_SOURCE, NOT_BACKED, Stop  # noqa: F401

J, PI = V1.J, V4.PI
VERSION = 5
EXPAND_K = 20
NOT_FOUND = "NOT FOUND IN THE PASSAGES CHECKED"
LABELS_V5 = LABELS + (NOT_FOUND,)
NOT_FOUND_NOTE = ("We did not find this in the passages we checked; the source is too long to read whole, so this "
                  "is not a finding that the source does not say it.")
PASSAGES, WHOLE, EXPANDED, NOT_JUDGED = "passages", "whole source", "top 20 passages + neighbours", "not judged"
_HIDDEN = ("docs", "full_docs", "prefix", "rest")
_VERDICT = ("attempts", "label", "reason", "reason_kind", "study_label", "span", "span_verbatim", "form_problems",
            "passage", "verdict_withheld", "kind", "usd")        # stage 1's; the second reading sets its own


def needs_fuller_read(r: dict) -> bool:
    """Stage 1's judge gave one of NOT BACKED's labels (shown, or withheld for no passage to show)."""
    return r.get("study_label") in V1.STUDY_CITED_FAIL


def expanded_text(text: str, claim: str, k: int = EXPAND_K) -> tuple[str, dict]:
    """The top K passages for the claim and each one's neighbours, merged, in document order."""
    ix = PI.index_of(text)
    got = ix.top(claim, k)
    idxs = sorted({j for p, _s in got for j in (p.idx - 1, p.idx, p.idx + 1) if 0 <= j < ix.n})
    ps = [ix.passages[j] for j in idxs]
    rec = {"top": [[p.start, p.end, round(s, 3)] for p, s in got], "sent": [[p.start, p.end] for p in ps]}
    return PI.deliver(text, [(p.start, p.end) for p in ps]), rec


def plan_reread(r: dict, man: dict, work: Path, count) -> dict:
    """One stage-1 NOT BACKED row -> the second reading's planned call (path, docs, prompt, worst case)."""
    docs, _why = V1._docs(r, man, work, count)                # v3's documents; chunked = over the one-call limit
    full = [dict(d, text=(work / "sources" / (d["source_id"] + ".txt")).read_text(encoding="utf-8")) for d in docs]
    path, rec = (EXPANDED, []) if any(d["chunked"] for d in docs) else (WHOLE, [])
    if path == EXPANDED:
        sent = []
        for d, f in zip(docs, full):
            if d["chunked"]:
                text, x = expanded_text(f["text"], r["claim"])
                rec.append({"source_id": d["source_id"], **x})
                d = {k: v for k, v in d.items() if k != "chunk"}
                d.update(text=text, tokens=count(text), chunked=False, passages=True)
            sent.append(d)
        docs = sent
    prefix, rest = J.build(r, docs)
    n_in = count(prefix + rest)
    return {**{k: v for k, v in r.items() if k not in _VERDICT}, "label": None, "docs": docs,
            "full_docs": full, "prefix": prefix, "rest": rest, "n_in": n_in, "worst": V1.worst_cost(n_in),
            "path": path, "expanded": rec, "stage1": stage1_of(r)}


def stage1_of(r: dict) -> dict:
    return {k: r.get(k) for k in ("label", "reason", "reason_kind", "study_label", "passage", "usd")}


def waves(planned: list[dict]) -> tuple[list[dict], list[dict]]:
    """(the first call for each distinct prefix, the rest): the rest go after, so the cache is read, not rewritten."""
    seen, first, rest = set(), [], []
    for p in planned:
        (rest if p["prefix"] in seen else first).append(p)
        seen.add(p["prefix"])
    return first, rest


def _one(p: dict, man: dict, client, before_call) -> dict:
    r = V1.judge([{k: v for k, v in p.items() if k != "full_docs"}], client, before_call)[0]
    m1 = r.get("study_label")
    if p["path"] == EXPANDED and m1 in V1.STUDY_CITED_FAIL:
        r = {**r, "label": NOT_FOUND, "reason": "%s (%s)" % (NOT_FOUND_NOTE, r.get("reason") or ""),
             "reason_kind": NOT_FOUND}
    else:
        r = V3.finish(r, p["full_docs"], man)                # the passage is found in the full held text
    s1 = p["stage1"]
    return {**r, "decided_by": p["path"], "stage1": s1, "usd_reread": r.get("usd") or 0.0,
            "usd": round((s1.get("usd") or 0.0) + (r.get("usd") or 0.0), 6)}


def plan_v5(stage1: list[dict], man: dict, work: Path, count) -> list[dict]:
    """Stage-1 rows in order; a row needing a fuller read is replaced by its planned re-read."""
    return [plan_reread(r, man, work, count) if needs_fuller_read(r) else r for r in stage1]


def fuller_read(planned: list[dict], man: dict, client, before_call=None, workers: int = 8) -> list[dict]:
    """The second readings (in two waves), and decided_by on every row; order kept."""
    todo = [p for p in planned if p.get("label") is None and p.get("path")]
    first, rest = waves(todo)
    done = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for wave in (first, rest):
            for p, r in zip(wave, ex.map(lambda p: _one(p, man, client, before_call), wave)):
                done[id(p)] = r
    out = []
    for p in planned:
        if id(p) in done:
            out.append(done[id(p)])
        else:
            out.append({**p, "decided_by": PASSAGES if p.get("attempts") else NOT_JUDGED})
    return out


def totals(results: list[dict]) -> dict:
    t = {k: sum(r["label"] == k for r in results) for k in LABELS_V5}
    t["usd"] = round(sum(r.get("usd") or 0 for r in results), 6)
    t["claims"] = len(results)
    return t


def summary(results: list[dict], found: int) -> str:
    """v3's summary line, with NOT FOUND IN THE PASSAGES CHECKED counted apart."""
    t = totals(results)
    abs_ = sum(r.get("kind") == V3.ABSTRACT_ONLY for r in results)
    return ("%d of %d claims checked: %d BACKED, %d NOT BACKED, %d NO SOURCE, %d COULDN'T CHECK, %d %s%s."
            % (len(results), found, t[BACKED], t[NOT_BACKED], t[NO_SOURCE], t[COULDNT], t[NOT_FOUND], NOT_FOUND,
               ("; %d %s" % (abs_, V3.ABSTRACT_ONLY)) if abs_ else ""))


def worst_usd(planned: list[dict]) -> float:
    return round(sum(p.get("worst") or 0 for p in planned if p.get("label") is None), 4)


def check(text: str, work: Path, client, count, fmt: str | None = None, system: str = "answer",
          net: dict | None = None, selected: list[int] | None = None, before_call=None) -> dict:
    """v4's check (stage 1), then the fuller read of every NOT BACKED."""
    t0 = time.time()
    prep = V4.prepare(text, work, fmt, count, system, net, selected)
    stage1 = V4.judge_v4(prep["planned"], prep["manifest"], work, client, before_call)
    planned = plan_v5(stage1, prep["manifest"], work, count)
    results = [{k: v for k, v in r.items() if k not in _HIDDEN} for r in
               fuller_read(planned, prep["manifest"], client, before_call)]
    return {**{k: v for k, v in prep.items() if k != "planned"}, "version": VERSION, "results": results,
            "summary": summary(results, prep["found"]), "seconds": round(time.time() - t0, 1)}


def public(results: list[dict], man: dict) -> list[dict]:
    """v3's reader view, with the deciding path."""
    return [{**p, "decided_by": r.get("decided_by")} for p, r in zip(V3.public(results, man), results)]
