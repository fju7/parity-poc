#!/usr/bin/env python3
"""Will this paid stage fit in what is left? Asked before the stage starts.

    stage_cap.py SLUG STAGE UNITS       print the estimate and both remainders

WHY THIS EXISTS
---------------
Every paid call already checks the day cap and the issue cap (spend_ledger.
check_cap) -- per CALL. On 2026-10-20 the WHU-P02 source advocate read 17
sources and drafted 27 objections, spent $4.28, and was stopped by the day cap
in the middle of its quotation check, before it had written anything a later
step could use. A per-call check stops a run that crosses the cap in the
middle; it does not stop a run that could never have finished. This does: before
a paid stage starts, its cost is estimated from what such stages have actually
cost, and the stage does not start if the estimate exceeds the cap remaining
today or on the issue.

THE ESTIMATES -- MEASURED, NOT ASSUMED
--------------------------------------
Each stage's cost is (units) x (measured cost per unit), the per-unit figure
computed when the check runs, from the records of what was spent:

  gate (narrow)  per call: the mean of every metered gate call of the roles a
                 narrow run makes (source:*, recency) in the spend ledger.
                 Units: the calls the run will make (one per attributed source
                 group, plus recency).
  gate (full)    per run: the mean of the measured full gate runs that reached
                 the source role (an extract call starts a run; runs under
                 $1.00 were aborted and are not counted). Units: 1.
  conclusions    per sentence: the mean conclusion-judge call in the ledger.
  advocate       per source: the mean of the ledger's per-source totals
                 (advocate, advocate-questions and advocate-requote calls for
                 one source on one day).
  audit          per sentence unit: total usd / total units over every audit
                 manifest in issues/*/audit/.
  changecheck    per run: the mean changecheck call in the ledger (one call).
  rulings        per ruling: the mean usage.usd of every logged ruling in
                 issues/*/rulings/ and issues/*/audit/*/rulings.jsonl.

A stage with no measurement yet falls back to FALLBACK, each figure with the
record it came from. The estimate is a mean, so a run can still cost more than
estimated; the per-call check remains, and stops it then.

NO OVERRIDE ON A STUDY ISSUE. A study issue's cap is set before the freeze and
never raised for a run (caps.json). On a published issue, WHU_SPEND_OVERRIDE
works here as in spend_ledger.check_cap: the run goes ahead and the override is
recorded in the ledger.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location("spend_ledger_stage", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

STAGES = ("gate-narrow", "gate-full", "conclusions", "advocate", "audit", "changecheck", "rulings")
NAMES = {"gate-narrow": "the machine gate (narrow)", "gate-full": "the machine gate (full)",
         "conclusions": "the conclusion judge", "advocate": "the source advocate",
         "audit": "the audit stage", "changecheck": "changecheck", "rulings": "the ruling model"}
UNIT = {"gate-narrow": "call", "gate-full": "run", "conclusions": "sentence", "advocate": "source",
        "audit": "sentence unit", "changecheck": "run", "rulings": "ruling"}
# Used only where nothing has been measured yet.
FALLBACK = {
    "gate-narrow": (0.75, "factcheck_draft.EST_PER_CALL"),
    "gate-full": (4.63, "Phase B's full run (RUN.md step 4)"),
    "conclusions": (0.0040, "RUN.md step 6"),
    "advocate": (0.30, "RUN.md step 4b, upper figure"),
    "audit": (0.40, "RUN.md step 7, $31 projected over 78 units"),
    "changecheck": (0.08, "RUN.md step 9, upper figure"),
    "rulings": (0.02, "README: $1.98 for 94 rulings"),
}
FULL_GATE_ROLES = ("extract", "advocate", "inference", "coverage", "recency", "counterexample")


class StageOverCap(Exception):
    """A stage whose estimate exceeds the cap remaining today or on the issue."""



def _load_frozen():
    """frozen.py, by its path beside this file (callers load this module by path)."""
    import importlib.util as _u
    m = sys.modules.get("frozen")
    if m is None:
        sp = _u.spec_from_file_location("frozen", Path(__file__).resolve().parent / "frozen.py")
        m = _u.module_from_spec(sp)
        sys.modules["frozen"] = m
        sp.loader.exec_module(m)
    return m


_frozen = _load_frozen

def _gate_calls(es):
    return [e for e in es if e.get("script") == "factcheck_draft.py"]


def per_unit(stage: str, entries: list[dict] | None = None, issues_dir: Path | None = None) -> tuple[float, str]:
    """(dollars per unit, how it was measured)."""
    es = S.entries() if entries is None else entries
    idir = issues_dir or (ROOT / "issues")
    fd = _gate_calls(es)
    vals: list[float] = []
    if stage == "gate-narrow":
        vals = [e.get("usd") or 0 for e in fd
                if (e.get("role") or "").startswith("source:") or e.get("role") == "recency"]
        how = "mean of %d metered gate call(s) (source, recency)"
    elif stage == "gate-full":
        fds = sorted(fd, key=lambda e: e.get("at") or "")
        starts = [i for i, e in enumerate(fds) if e.get("role") == "extract"]
        for j, i in enumerate(starts):
            end = starts[j + 1] if j + 1 < len(starts) else len(fds)
            iss = fds[i].get("issue")
            tot = sum(e.get("usd") or 0 for e in fds[i:end] if e.get("issue") == iss and
                      (e.get("role") in FULL_GATE_ROLES or (e.get("role") or "").startswith("source:")))
            if tot >= 1.0:
                vals.append(tot)
        how = "mean of %d measured full gate run(s)"
    elif stage == "conclusions":
        vals = [e.get("usd") or 0 for e in fd if (e.get("role") or "").startswith("conclusion_judge/")]
        how = "mean of %d metered conclusion-judge call(s)"
    elif stage == "advocate":
        per = defaultdict(float)
        for e in fd:
            m = re.match(r"advocate(?:-requote|-questions)?:(\S+)$", e.get("role") or "")
            if m:
                per[(e.get("issue"), (e.get("at") or "")[:10], m.group(1))] += e.get("usd") or 0
        vals = list(per.values())
        how = "mean over %d measured source(s)"
    elif stage == "audit":
        u = usd = 0.0
        n = 0
        for f in glob.glob(str(idir / "*" / "audit" / "*" / "manifest.json")):
            try:
                m = json.loads(Path(f).read_text(encoding="utf-8"))
            except Exception:
                continue
            if m.get("usd") and m.get("units"):
                u, usd, n = u + m["units"], usd + m["usd"], n + 1
        if u:
            return usd / u, "$%.2f over %d sentence unit(s) in %d audit run(s)" % (usd, u, n)
    elif stage == "changecheck":
        vals = [e.get("usd") or 0 for e in fd if e.get("role") == "changecheck"]
        how = "mean of %d metered changecheck call(s)"
    elif stage == "rulings":
        files = glob.glob(str(idir / "*" / "rulings" / "**" / "*rulings.jsonl"), recursive=True) + \
            glob.glob(str(idir / "*" / "audit" / "*" / "rulings.jsonl"))
        for f in files:
            for line in Path(f).read_text(encoding="utf-8").splitlines():
                try:
                    usd = ((json.loads(line) if line.strip() else {}).get("usage") or {}).get("usd")
                except Exception:
                    usd = None
                if usd:
                    vals.append(float(usd))
        how = "mean of %d logged ruling(s)"
    else:
        raise ValueError("unknown stage %r (one of %s)" % (stage, ", ".join(STAGES)))
    if vals:
        return sum(vals) / len(vals), how % len(vals)
    f, src = FALLBACK[stage]
    return f, "nothing measured yet; %s" % src


def remaining(issue: str) -> dict:
    """{day_left, day_cap, issue_left, issue_cap}; a cap that is not set is None."""
    c = S.caps()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day = c.get("default_per_day")
    spent_today = sum(e.get("usd") or 0 for e in S.entries() if (e.get("at") or "").startswith(today))
    cap = S.cap_for(issue)
    return {"day_cap": float(day) if day else None,
            "day_left": round(float(day) - spent_today, 4) if day else None,
            "issue_cap": float(cap) if cap else None,
            "issue_left": round(float(cap) - S.spent(issue=issue), 4) if cap else None}


def estimate(stage: str, units: int, **kw) -> tuple[float, str]:
    each, how = per_unit(stage, **kw)
    return round(units * each, 4), "%d %s(s) x $%.4f per %s (%s)" % (
        units, UNIT[stage], each, UNIT[stage], how)


def check(stage: str, issue: str, units: int, **kw) -> dict:
    """Refuse to start STAGE on ISSUE if its estimate exceeds the cap remaining
    today or on the issue. Returns what was checked; raises StageOverCap."""
    S.check_cap(issue, 0.0)                    # an unpriced ledger line stops everything first
    est, how = estimate(stage, units, **kw)
    left = remaining(issue)
    over = []
    if left["day_left"] is not None and est > left["day_left"]:
        over.append("today")
    if left["issue_left"] is not None and est > left["issue_left"]:
        over.append("the issue")
    out = {"stage": stage, "units": units, "estimate": est, "how": how, **left, "over": over}
    if not over:
        return out
    msg = ("NOT STARTED: %s is estimated at $%.2f (%s).\n"
           "Remaining today: $%s of the $%s day cap.\n"
           "Remaining on %s: $%s of its $%s cap.\n"
           "The estimate exceeds what is left %s."
           % (NAMES[stage], est, how,
              _d(left["day_left"]), _d(left["day_cap"]), issue,
              _d(left["issue_left"]), _d(left["issue_cap"]), " and ".join(over)))
    why = os.environ.get("WHU_SPEND_OVERRIDE", "").strip()
    if why and not S.is_study_issue(issue):
        S.record(script="stage_cap", role="override", issue=issue, usd=0.0,
                 note="%s estimated $%.2f over %s -- %s" % (stage, est, " and ".join(over), why))
        return dict(out, override=why)
    raise StageOverCap(msg)


def _d(x) -> str:
    return "%.2f" % x if x is not None else "(no cap)"


def guard(stage: str, issue: str, units: int) -> None:
    """check(), printing the refusal and exiting 3 (the gate's 'stopped before
    spending' code) instead of raising: for a script's entry point."""
    # THE FROZEN FILES (protocol rev 38): no paid stage of a study issue starts
    # if RUN.md or a frozen prompt is not the one recorded in frozen.py.
    frozen = _frozen()
    if frozen.is_study(issue):
        try:
            frozen.verify_all()
        except frozen.FrozenFileChanged as e:
            print("\n  NOT STARTED: %s.\n  %s\n" % (NAMES[stage], e), file=sys.stderr)
            raise SystemExit(6)
    try:
        r = check(stage, issue, units)
    except (StageOverCap, S.OverCap) as e:                 # S.OverCap: already past a cap
        print("\n  NOT STARTED: %s.\n  " % NAMES[stage] + str(e).replace("\n", "\n  ") + "\n",
              file=sys.stderr)
        raise SystemExit(3)
    print("  stage cap: %s estimated $%.2f (%s); $%s left today, $%s left on %s"
          % (NAMES[stage], r["estimate"], r["how"], _d(r["day_left"]), _d(r["issue_left"]), issue))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("stage", choices=STAGES)
    ap.add_argument("units", type=int)
    a = ap.parse_args(argv)
    try:
        r = check(a.stage, a.slug, a.units)
    except (StageOverCap, S.OverCap) as e:
        print(e)
        return 3
    print(json.dumps(r, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
