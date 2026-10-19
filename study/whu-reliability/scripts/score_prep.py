#!/usr/bin/env python3
"""Prep-round tables: agreement with the pilot's unanimous labels, confusion
tables, form checks, refusals, caching and measured cost per call. Free.

Usage: score_prep.py RUN_DIR [--replies replies] [--probe replies-cacheprobe2]

Reads replies written by judge_m1.py (v2 or v3 records). The span check is
re-done here with judge_m1.norm, so a fix to the checker applies to old
replies without touching them."""
import argparse
import glob
import importlib.util
import json
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("judge_m1", HERE / "judge_m1.py")
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)


def load(run: Path, folder: str, judge: str) -> list[dict]:
    return [json.load(open(f)) for f in sorted(glob.glob(str(run / folder / judge / "*.json")))]


def docs_text(run: Path, rec: dict) -> list[str]:
    return [(run / "sources" / (s["source_id"] + ".txt")).read_text(encoding="utf-8") for s in rec.get("sources", [])]


def summary(run: Path, rows: list[dict]) -> dict:
    conf: dict = {}
    for d in rows:
        got = d.get("label") or "(no label)"
        conf.setdefault(d["reference"], {}).setdefault(got, 0)
        conf[d["reference"]][got] += 1
    calls = [a for d in rows for a in d["attempts"]]
    labelled = [d for d in rows if d.get("label") != J.REFUSED]
    spans = 0
    for d in labelled:
        sp = (d.get("parsed") or {}).get("span") or ""
        spans += bool(sp) and any(J.norm(sp) in J.norm(t) for t in docs_text(run, d))
    hit = [a for a in calls if (a["usage"].get("cache_read") or 0) > 0]
    # Claude's "input" excludes cached tokens; OpenAI's "input" includes them.
    src_tokens = sum(((a["usage"].get("cache_read") or 0) + (a["usage"].get("cache_write") or 0)
                      if "cache_write" in a["usage"] else 0) + (a["usage"].get("input") or 0) for a in calls)
    read_tokens = sum(a["usage"].get("cache_read") or 0 for a in calls)
    usd = [a["usd"] for a in calls]
    return {
        "items": len(rows), "calls": len(calls),
        "agree_with_pilot": sum(d.get("label") == d["reference"] for d in rows),
        "refused_items": sum(d.get("label") == J.REFUSED for d in rows),
        "refused_calls": sum(a["refused"] for a in calls),
        "not_verifiable_abstract": sum(d.get("label") == J.NOT_VERIFIABLE_ABSTRACT for d in rows),
        "valid_json": sum(not d["form_problems"] for d in labelled), "labelled": len(labelled),
        "span_verbatim": spans,
        "per_reference": {r: "%d/%d" % (c.get(r, 0), sum(c.values())) for r, c in conf.items()},
        "confusion": conf,
        "calls_with_cache_hit": "%d/%d" % (len(hit), len(calls)),
        "input_tokens_read_from_cache": "%.1f%%" % (100.0 * read_tokens / max(src_tokens, 1)),
        "usd_total": round(sum(usd), 4), "usd_mean_per_call": round(st.mean(usd), 4),
        "usd_median_per_call": round(st.median(usd), 4),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--replies", default="replies")
    ap.add_argument("--probe")
    a = ap.parse_args()
    run = Path(a.run)
    out = {}
    for j in ("claude", "openai"):
        out[j] = summary(run, load(run, a.replies, j))
        if a.probe:
            out[j + "_cache_probe"] = summary(run, load(run, a.probe, j))
    c = {d["item"]: d for d in load(run, a.replies, "claude")}
    o = {d["item"]: d for d in load(run, a.replies, "openai")}
    both = [i for i in c if i in o]
    out["judge_vs_judge"] = "%d/%d" % (sum(c[i].get("label") == o[i].get("label") for i in both), len(both))
    out["human_review_items"] = sorted(i for i in both if c[i].get("label") != o[i].get("label")
                                       or c[i].get("human_review") or o[i].get("human_review"))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
