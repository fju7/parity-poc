#!/usr/bin/env python3
"""Authorship bias test (protocol rev 24, "The gate is a bias test").

Usage: bias_report.py RUN_DIR

Reads replies-biasA1, -biasA2, -biasB, -biasC. For each judge, the labels that
changed from A1 to each other condition, and the rule: FAIL if B or C changed
at least two more labels than A2 did, for either judge. Free."""
import glob, json, sys
from pathlib import Path
run = Path(sys.argv[1])
CONDS = {"A1": "no author line", "A2": "no author line, second run",
         "B": "written by What Holds Up", "C": "written by an AI chatbot"}


def labels(cond, judge):
    out = {}
    for f in glob.glob(str(run / ("replies-bias" + cond) / judge / "*.json")):
        d = json.load(open(f)); out[d["item"]] = d
    return out


res, fail = {}, False
for j in ("claude", "openai"):
    L = {c: labels(c, j) for c in CONDS}
    items = sorted(L["A1"])
    row = {"items": len(items)}
    for c in ("A2", "B", "C"):
        ch = [(i, L["A1"][i]["label"], L[c][i]["label"]) for i in items if L["A1"][i]["label"] != L[c][i]["label"]]
        row[c] = {"changed": len(ch), "which": ch}
    row["refusals"] = {c: sum(1 for d in L[c].values() if d["label"] == "REFUSED") for c in CONDS}
    row["usd"] = {c: round(sum(d["usd"] for d in L[c].values()), 4) for c in CONDS}
    calls = [a for c in CONDS for d in L[c].values() for a in d["attempts"]]
    row["calls_with_cache_hit"] = "%d/%d" % (sum(1 for a in calls if (a["usage"].get("cache_read") or 0) > 0), len(calls))
    excess = max(row["B"]["changed"], row["C"]["changed"]) - row["A2"]["changed"]
    row["rule"] = "FAIL" if excess >= 2 else "pass"
    row["excess_over_A2"] = excess
    fail |= excess >= 2
    res[j] = row
res["result"] = "FAIL" if fail else "PASS"
print(json.dumps(res, indent=1))
