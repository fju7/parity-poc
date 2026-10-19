#!/usr/bin/env python3
"""Prep-round tables: per-label agreement with the pilot's unanimous labels,
confusion tables, form checks, and measured cost per M1 call. Free."""
import json, glob, sys, statistics as st
from pathlib import Path
run = Path(sys.argv[1])
LAB = ["Supported", "Overstates", "Understates", "Absent", "Wrong source", "Contradicted", "Unreachable", "(no label)"]
out = {}
for j in ("claude", "openai"):
    rows = [json.load(open(f)) for f in sorted(glob.glob(str(run / "replies" / j / "*.json")))]
    conf = {}
    for d in rows:
        got = (d["parsed"] or {}).get("label") or "(no label)"
        conf.setdefault(d["reference"], {}).setdefault(got, 0)
        conf[d["reference"]][got] += 1
    per = {r: "%d/%d" % (c.get(r, 0), sum(c.values())) for r, c in conf.items()}
    usd = [d["usd"] for d in rows]
    out[j] = {"n": len(rows), "agree": sum(((d["parsed"] or {}).get("label") == d["reference"]) for d in rows),
              "refusals": sum(d["usage"].get("stop") == "refusal" for d in rows),
              "valid_json": sum(not d["form_problems"] for d in rows),
              "span_verbatim": sum(bool(d["span_verbatim_in_document"]) for d in rows),
              "per_label": per, "confusion": conf,
              "usd_total": round(sum(usd), 4), "usd_mean": round(st.mean(usd), 4), "usd_median": round(st.median(usd), 4),
              "in_mean": round(st.mean(d["usage"]["input"] for d in rows)), "out_mean": round(st.mean(d["usage"]["output"] for d in rows)),
              "seconds_mean": round(st.mean(d["seconds"] for d in rows), 1)}
c = {Path(f).stem: json.load(open(f)) for f in glob.glob(str(run / "replies/claude/*.json"))}
o = {Path(f).stem: json.load(open(f)) for f in glob.glob(str(run / "replies/openai/*.json"))}
both = [i for i in c if i in o]
out["judge_vs_judge"] = "%d/%d" % (sum((c[i]["parsed"] or {}).get("label") == (o[i]["parsed"] or {}).get("label") for i in both), len(both))
print(json.dumps(out, indent=1))
