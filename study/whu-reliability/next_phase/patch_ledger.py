#!/usr/bin/env python3
"""The patch ledger (post-test item 1; advisor's ruling after Q1-04c, following arXiv:2611.04338 §5).

Every deviations.md row from the start of the next phase (the row "the lean four-question test is CLOSED as
reported" onward) has an entry in patches.jsonl with fixed fields:

  id                    P001, P002, ...
  deviation             the opening words of the row's bold title (how the row is found)
  date                  the row's date
  kind                  "patch" | "check_defect" (a defect found in a non-impact check is logged as a patch)
  trigger               what caused the change
  timing                "before any data" | "during data collection" | "after data seen"
  components            the files or stages changed
  data_exposure         what data, if any, the person making the change had seen
  decision_rule_change  true | false: does it change how a result is decided?
  non_impact_check      {"script": "nonimpact/<name>.py", "args": [...], "expected_sha256": "<stdout sha256>"}
                        or {"none": "<why no check applies>"}

A non-impact check is a small committed script anyone can rerun; `verify` reruns each one and compares the
sha256 of its standard output with the expected value. Rows before the phase are listed as legacy: their fields
are not back-filled.

    py study/whu-reliability/next_phase/patch_ledger.py validate
    py study/whu-reliability/next_phase/patch_ledger.py verify [--id P003]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEVIATIONS = HERE / "deviations.md"
PATCHES = HERE / "patches.jsonl"
PHASE_START = "the lean four-question test is CLOSED as reported"
FIELDS = ("id", "deviation", "date", "kind", "trigger", "timing", "components", "data_exposure",
          "decision_rule_change", "non_impact_check")
TIMINGS = ("before any data", "during data collection", "after data seen")
KINDS = ("patch", "check_defect")
ROW = re.compile(r"^\| (\d{4}-\d{2}-\d{2}) \| \*\*(.+?)\*\*")


def deviation_rows(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            out.append({"date": m.group(1), "title": m.group(2)})
    return out


def phase_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """(legacy rows, rows that need an entry)."""
    for i, r in enumerate(rows):
        if PHASE_START in r["title"]:
            return rows[:i], rows[i:]
    return rows, []


def load(path: Path = PATCHES) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def problems_of(entry: dict) -> list[str]:
    bad = ["missing field %r" % f for f in FIELDS if f not in entry]
    if bad:
        return bad
    if not re.fullmatch(r"P\d{3}", str(entry["id"])):
        bad.append("id must be P###")
    if entry["kind"] not in KINDS:
        bad.append("kind must be one of %s" % (KINDS,))
    if entry["timing"] not in TIMINGS:
        bad.append("timing must be one of %s" % (TIMINGS,))
    if not isinstance(entry["decision_rule_change"], bool):
        bad.append("decision_rule_change must be true or false")
    if not isinstance(entry["components"], list) or not entry["components"]:
        bad.append("components must be a non-empty list")
    for f in ("trigger", "data_exposure", "deviation"):
        if not str(entry.get(f) or "").strip():
            bad.append("%s is empty" % f)
    c = entry["non_impact_check"]
    if not isinstance(c, dict) or not (("none" in c and str(c["none"]).strip()) or
                                       (c.get("script") and re.fullmatch(r"[0-9a-f]{64}",
                                                                          str(c.get("expected_sha256", ""))))):
        bad.append("non_impact_check must be {script, args, expected_sha256} or {none: why}")
    elif c.get("script") and not (HERE / c["script"]).exists():
        bad.append("non-impact check script %s does not exist" % c["script"])
    return bad


def validate(dev_text: str, entries: list[dict]) -> dict:
    legacy, need = phase_rows(deviation_rows(dev_text))
    out = {"legacy_rows": len(legacy), "phase_rows": len(need), "problems": []}
    ids = [e.get("id") for e in entries]
    if len(set(ids)) != len(ids):
        out["problems"].append("duplicate ids")
    for e in entries:
        out["problems"] += ["%s: %s" % (e.get("id"), p) for p in problems_of(e)]
    for r in need:
        hits = [e for e in entries if e.get("date") == r["date"] and r["title"].startswith(str(e.get("deviation")))]
        if not hits:
            out["problems"].append("deviations row %s %r has no patch entry" % (r["date"], r["title"][:70]))
    return out


def run_check(entry: dict) -> dict:
    c = entry["non_impact_check"]
    if "none" in c:
        return {"id": entry["id"], "ran": False, "why": c["none"]}
    r = subprocess.run([sys.executable, str(HERE / c["script"]), *c.get("args", [])], cwd=str(ROOT),
                       capture_output=True, text=True)
    got = hashlib.sha256(r.stdout.encode("utf-8")).hexdigest()
    return {"id": entry["id"], "ran": True, "rc": r.returncode, "sha256": got,
            "matches": got == c["expected_sha256"] and r.returncode == 0}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("validate", "verify"))
    ap.add_argument("--id")
    a = ap.parse_args(argv)
    entries = load()
    if a.cmd == "validate":
        res = validate(DEVIATIONS.read_text(encoding="utf-8"), entries)
        print(json.dumps(res, indent=1))
        return 1 if res["problems"] else 0
    rc = 0
    for e in entries:
        if a.id and e["id"] != a.id:
            continue
        r = run_check(e)
        print(json.dumps(r))
        rc = rc or (0 if (not r["ran"] or r["matches"]) else 1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
