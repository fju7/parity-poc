"""Recover what git still knows about gate-run spend, into the ledger.

The ledger starts empty, and an empty ledger is a wrong answer to "what has
this issue cost". Every committed version of a *.gate.json carries its own
usage, so the runs that survived into git can be recovered. What cannot: runs
whose report was overwritten before being committed, melanoma's run (its report
predates usage accounting), and every priced call from the fourteen other
scripts that record nothing. The recovered figure is a FLOOR, and the ledger
says so.

Idempotent. Each entry is keyed on the commit it came from and the role, so
running this twice does not double the history -- which the first version did,
turning $20.66 into $41.32 and reporting it without blinking.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spend_ledger as sl

REPORTS = ["site/whatholdsup/cdk46.html.gate.json",
           "site/whatholdsup/melanoma.html.gate.json",
           "site/whatholdsup/deskilling.html.gate.json"]


def git(*a) -> str:
    r = subprocess.run(["git", "-C", str(sl.ROOT)] + list(a), capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def main() -> int:
    have = {(e.get("note"), e.get("role")) for e in sl.entries()}
    added = 0
    seen_runs = set()
    for f in REPORTS:
        issue = f.split("/")[-1].replace(".html.gate.json", "")
        for line in git("log", "--format=%H %ad", "--date=short", "--", f).strip().splitlines():
            sha, date = line.split()[0], line.split()[1]
            blob = git("show", f"{sha}:{f}")
            if not blob:
                continue
            try:
                r = json.loads(blob)
            except Exception:
                continue
            usage = r.get("usage") or {}
            by, tot = usage.get("by_role") or {}, usage.get("total") or {}
            if not tot.get("usd"):
                continue
            run_key = (issue, round(tot["usd"], 4))
            if run_key in seen_runs:          # same report content, committed twice
                continue
            seen_runs.add(run_key)
            note = "backfilled from git %s" % sha[:8]
            when = (r.get("checked_at") or date) + "T12:00:00+00:00"
            for role, u in by.items():
                if (note, role) in have:
                    continue
                sl.record(script="factcheck_draft.py", role=role, issue=issue,
                          usd=u.get("usd") or 0, input_tokens=u.get("input") or 0,
                          output_tokens=u.get("output") or 0,
                          web_searches=u.get("web_searches") or 0,
                          at=when, note=note)
                added += 1
    print(f"added {added} entr{'y' if added == 1 else 'ies'} from {len(seen_runs)} gate run(s)")
    print("This is a FLOOR. Overwritten reports, melanoma's un-instrumented run,")
    print("and every call from the other fourteen priced scripts are not recoverable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
