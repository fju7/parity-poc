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
  advocate       per source: the higher of the mean of the ledger's per-
                 source totals (advocate, advocate-questions and advocate-
                 requote calls for one source on one day) and the cost per
                 objection times the most objections per source of any run
                 (2026-10-22; _advocate_per_source).
  audit          per sentence unit: the HIGHEST per-unit cost (usd / units) of
                 any audit manifest in issues/*/audit/ whose lean_config equals
                 this run's (audit_config(); None for a non-lean audit), times
                 AUDIT_MARGIN (2). An upper bound from runs of the same kind,
                 not a mean (advisor's ruling 3 on P112, 2026-11-25: the pooled
                 mean over all 69 runs, $0.0243, was dominated by non-lean
                 audits that read whole texts and refused 02za's lean audit).
  changecheck    per run: the mean changecheck call in the ledger (one call).
  rulings        per ruling: the mean usage.usd of every logged ruling in
                 issues/*/rulings/ and issues/*/audit/*/rulings.jsonl.

A stage with no measurement yet falls back to FALLBACK, each figure with the
record it came from. The per-call check remains the hard backstop for every
stage, and stops a run that costs more than estimated.

SAME-CONFIG UPPER BOUNDS, NOT MEANS (advisor's rulings 1 and 2 on P140,
2026-11-26). Every estimate above that says "mean" is now the HIGHEST measured
per-unit figure among records of the same configuration (current_config: the
stage's model and whether the call is in an orchestrated run; the reply-limits
table, WHU_ORCH_LIMITS_SHA, is recorded on each ledger row and ruling since that
date but not matched -- see same_config), x MARGIN (2). With no same-config record yet: the higher of
FALLBACK and the highest of any config, x MARGIN. The gate's own check is
gate_bound(): max(its dry-run estimate, the highest same-config gate run in the
gate reports) x MARGIN, replacing a fixed $3.00 that refused 02-batch run 1.

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

STAGES = ("gate-narrow", "gate-full", "conclusions", "advocate", "audit", "changecheck", "rulings", "omissions", "judgements")
NAMES = {"gate-narrow": "the machine gate (narrow)", "gate-full": "the machine gate (full)",
         "conclusions": "the conclusion judge", "advocate": "the source advocate",
         "audit": "the audit stage", "changecheck": "changecheck", "rulings": "the ruling model",
         "omissions": "the omission ruling", "judgements": "the relevance ruling"}
UNIT = {"gate-narrow": "call", "gate-full": "run", "conclusions": "sentence", "advocate": "source",
        "audit": "sentence unit", "changecheck": "run", "rulings": "ruling", "omissions": "omission unit", "judgements": "candidate"}
# Used only where nothing has been measured yet.
FALLBACK = {
    "gate-narrow": (0.75, "factcheck_draft.EST_PER_CALL"),
    "gate-full": (4.63, "Phase B's full run (RUN.md step 4)"),
    "conclusions": (0.0040, "RUN.md step 6"),
    "advocate": (0.30, "RUN.md step 4b, upper figure"),
    "audit": (0.40, "RUN.md step 7, $31 projected over 78 units"),
    "changecheck": (0.08, "RUN.md step 9, upper figure"),
    "rulings": (0.02, "README: $1.98 for 94 rulings"),
    # Post-study fix 2, step 8: docs/whu-fix2-omission-rulings-design.md s5.
    "omissions": (0.03, "fix 2 design s5: an omission ruling carries question, scope and context"),
    # Post-study fix 3, step 2: one short relevance call per candidate judgement.
    "judgements": (0.02, "fix 3 design s3.2 (R1): about a ruling's cost per candidate"),
}
FULL_GATE_ROLES = ("extract", "advocate", "inference", "coverage", "recency", "counterexample")


AUDIT_MARGIN = 2.0          # the audit estimate: highest measured per-unit cost in its pool x this
_CURRENT = object()          # per_unit's default config: this run's own (audit_config())


def audit_config() -> dict | None:
    """The audit's lean_config exactly as audit_stage.py writes it into its manifest (the one
    definition both use), or None when lean is off (a non-lean audit's manifest has none)."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import lean
    if not lean.enabled():
        return None
    import passage_index as PI
    return {"models": {k: lean.model_for(k) for k in
                       ("audit_first", "audit_escalate", "audit_rule", "audit_second")},
            "k": PI.K, "min_score": PI.MIN_SCORE, "min_terms": PI.MIN_TERMS,
            "passage_chars": PI.PASSAGE_CHARS}


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


MARGIN = 2.0                # every measured stage estimate: the highest measured cost in its same-config pool x this


def current_config(model: str | None = None) -> dict:
    """The configuration a stage's pool is matched on (advisor's ruling 2 on P140, 2026-11-26): the model (None:
    any), whether the call is inside an orchestrated run, and the reply-limits table it runs under (the
    orchestrator's WHU_ORCH_LIMITS_SHA; None outside one, where the callers' own limits apply as before)."""
    return {"model": model, "orchestrated": bool(os.environ.get("WHU_ORCH_STEP")),
            "limits": os.environ.get("WHU_ORCH_LIMITS_SHA") or None}


def row_config(e: dict) -> dict:
    """A ledger row's configuration: its model, whether it was spent in an orchestrator step (`step`), and the
    limits table recorded with it (`limits_sha`; rows written before 2026-11-26 carry none)."""
    return {"model": e.get("model"), "orchestrated": bool(e.get("step")), "limits": e.get("limits_sha")}


def same_config(want: dict, got: dict) -> bool:
    """Same model (when the caller names one) and same kind of run (orchestrated or not). The limits table is
    recorded on every row but NOT matched: a limit is a ceiling, and a reply that was not cut off costs the same
    under a raised one; matching it would leave every pool empty after P130 and fall back to non-lean runs that
    read whole texts ($2.15 a source for the advocate, against $0.96 for all of 02za's). A reply cut off under an
    old limit is measured at that limit, an under-count the x2 margin and the per-call backstop cover."""
    return ((want.get("model") is None or got.get("model") == want.get("model"))
            and bool(got.get("orchestrated")) == bool(want.get("orchestrated")))


def bound(stage: str, pairs: list[tuple[float, dict]], want: dict, what: str) -> tuple[float, str]:
    """(dollars per unit, how): the highest measured per-unit cost among PAIRS (value, config) whose config equals
    WANT, x MARGIN -- an upper bound from runs of the same kind, never a mean. With none of the same config yet:
    the higher of the stage's FALLBACK and the highest of any config, x MARGIN, and it says so."""
    same = [v for v, c in pairs if v and same_config(want, c)]
    if same:
        top = max(same)
        return top * MARGIN, "the highest of %d same-config %s ($%.4f) x %g" % (len(same), what, top, MARGIN)
    f, src = FALLBACK[stage]
    anyc = [v for v, _c in pairs if v]
    if not anyc:
        return f * MARGIN, "nothing measured yet; %s ($%.4f) x %g" % (src, f, MARGIN)
    top = max([f] + anyc)
    return top * MARGIN, ("no same-config %s measured yet: the higher of the fallback ($%.4f, %s) and the highest "
                          "of %d of any config ($%.4f), x %g" % (what, f, src, len(anyc), max(anyc) if anyc else 0.0,
                                                                  MARGIN))


def per_unit(stage: str, entries: list[dict] | None = None, issues_dir: Path | None = None,
             config=_CURRENT, model: str | None = None) -> tuple[float, str]:
    """(dollars per unit, how it was measured). CONFIG (audit only): the lean_config whose runs
    form the pool; by default this run's own (audit_config()). MODEL (every other stage): the model the
    stage will call, matched with the run's orchestrated flag and limits table (current_config)."""
    es = S.entries() if entries is None else entries
    idir = issues_dir or (ROOT / "issues")
    fd = _gate_calls(es)
    want = current_config(model)
    if stage == "gate-narrow":
        pairs = [(e.get("usd") or 0, row_config(e)) for e in fd
                 if (e.get("role") or "").startswith("source:") or e.get("role") == "recency"]
        return bound(stage, pairs, want, "metered gate call(s) (source, recency)")
    if stage == "gate-full":
        pairs = []
        fds = sorted(fd, key=lambda e: e.get("at") or "")
        starts = [i for i, e in enumerate(fds) if e.get("role") == "extract"]
        for j, i in enumerate(starts):
            end = starts[j + 1] if j + 1 < len(starts) else len(fds)
            iss = fds[i].get("issue")
            tot = sum(e.get("usd") or 0 for e in fds[i:end] if e.get("issue") == iss and
                      (e.get("role") in FULL_GATE_ROLES or (e.get("role") or "").startswith("source:")))
            if tot >= 1.0:
                pairs.append((tot, row_config(fds[i])))
        return bound(stage, pairs, want, "measured full gate run(s)")
    if stage == "conclusions":
        pairs = [(e.get("usd") or 0, row_config(e)) for e in fd
                 if (e.get("role") or "").startswith("conclusion_judge/")]
        return bound(stage, pairs, want, "metered conclusion-judge call(s)")
    if stage == "advocate":
        return _advocate_per_source(fd, idir, want)
    if stage == "audit":
        want_a = audit_config() if config is _CURRENT else config
        pool = []
        for f in sorted(glob.glob(str(idir / "*" / "audit" / "*" / "manifest.json"))):
            try:
                m = json.loads(Path(f).read_text(encoding="utf-8"))
            except Exception:
                continue
            if m.get("usd") and m.get("units") and m.get("lean_config") == want_a:
                pool.append((m["usd"] / m["units"], Path(f).parent))
        if pool:
            top, where = max(pool, key=lambda r: r[0])
            return top * AUDIT_MARGIN, ("the highest per-unit cost of %d audit run(s) with this run's lean_config "
                                        "($%.4f, %s/%s) x %g" % (len(pool), top, where.parent.parent.name,
                                                                 where.name, AUDIT_MARGIN))
        f, src = FALLBACK[stage]
        return f, "nothing measured yet; %s" % src
    if stage == "changecheck":
        pairs = [(e.get("usd") or 0, row_config(e)) for e in fd if e.get("role") == "changecheck"]
        return bound(stage, pairs, want, "metered changecheck call(s)")
    if stage in ("rulings", "omissions", "judgements"):
        # "omissions": the omission rulings alone (ruling_kind "omission"); one
        # unit is one ruling, and ruling.omission_units counts a re-ask as two.
        files = glob.glob(str(idir / "*" / "rulings" / "**" / "*rulings.jsonl"), recursive=True) + \
            ([] if stage in ("omissions", "judgements") else glob.glob(str(idir / "*" / "audit" / "*" / "rulings.jsonl")))
        pairs = []
        for f in files:
            orch = Path(f).relative_to(idir).parts[0].startswith("WHU-OT")   # an orchestrated run's own rulings
            for line in Path(f).read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line) if line.strip() else {}
                except Exception:
                    rec = {}
                if stage == "omissions" and rec.get("ruling_kind") != "omission":
                    continue
                if stage == "judgements" and rec.get("ruling_kind") != "relevance":
                    continue
                usd = (rec.get("usage") or {}).get("usd")
                if usd:
                    pairs.append((float(usd), {"model": rec.get("model"), "orchestrated": orch,
                                               "limits": rec.get("limits_sha")}))
        what = {"rulings": "logged ruling(s)", "omissions": "logged omission ruling(s)",
                "judgements": "logged relevance ruling(s)"}[stage]
        return bound(stage, pairs, want, what)
    raise ValueError("unknown stage %r (one of %s)" % (stage, ", ".join(STAGES)))


def _advocate_per_source(fd: list[dict], idir: Path, want: dict | None = None) -> tuple[float, str]:
    """The source advocate's cost per source: the HIGHER of two measures
    (2026-10-22), from the study and practice issues' runs (WHU-P*, WHU-S*:
    P02, P04, S01, S02 when this was written; every issue's, where none has
    run).

      per source     the mean of the ledger's per-source totals (advocate,
                     advocate-questions and advocate-requote calls for one
                     source on one day)
      per objection  the issues' advocate spend over the objections in their
                     briefs (superseded runs included: their spend is in the
                     ledger), times the most objections per source any one
                     run's briefs hold

    The per-source mean alone was $0.46 over these issues' 62 sources (2026-10-22)
    against WHU-S02's $0.72 per source and $0.89 by the per-objection measure:
    the cost follows the objections (each is checked, and re-asked when its
    quotation is not in the held text), and a question that draws many
    objections per source costs more than the mean source did."""
    per = defaultdict(float)
    cfg = {}
    for e in fd:
        m = re.match(r"advocate(?:-requote|-questions)?:(\S+)$", e.get("role") or "")
        if m:
            k = (e.get("issue"), (e.get("at") or "")[:10], m.group(1))
            per[k] += e.get("usd") or 0
            cfg.setdefault(k, row_config(e))
    # Advisor's ruling 2 on P140: the same-config per-source totals, when any exist, and the HIGHEST of them (x
    # MARGIN at the end), not the mean.
    want = want or current_config()
    if any(same_config(want, c) for c in cfg.values()):
        per = {k: v for k, v in per.items() if same_config(want, cfg[k])}
    cases = {p.name.split("-", 2)[2]: p for p in idir.glob("WHU-[PS][0-9]*-*") if p.is_dir()
             and len(p.name.split("-", 2)) == 3}
    if any(k[0] in cases for k in per):
        per = {k: v for k, v in per.items() if k[0] in cases}
    if not per:
        f, src = FALLBACK["advocate"]
        return f * MARGIN, "nothing measured yet; %s, x %g" % (src, MARGIN)
    a = max(per.values())
    spend = defaultdict(float)
    for (iss, _d, _s), v in per.items():
        spend[iss] += v
    objections, rates, per_issue_obj = 0, [], defaultdict(int)
    for iss in spend:
        case = cases.get(iss)
        for bf in sorted(case.glob("advocate/**/*-briefs.json")) if case else []:
            if "TEST" in bf.name:
                continue
            try:
                briefs = json.loads(bf.read_text(encoding="utf-8"))
            except Exception:
                continue
            n = sum(len(b.get("objections") or []) for b in briefs
                    if b.get("mode", "objections") == "objections")
            objections += n
            per_issue_obj[iss] += n
            if briefs:
                rates.append((n / len(briefs), "%s %s" % (case.name, bf.name)))
    how_a = "$%.4f the highest of %d measured source(s) in %d issue(s)" % (a, len(per), len(spend))
    if not objections or not rates:
        return a * MARGIN, how_a + ", x %g" % MARGIN
    # the HIGHEST issue's cost per objection (was the pooled rate over every issue's objections)
    each, worst = max((spend[i] / per_issue_obj[i], i) for i in per_issue_obj if per_issue_obj[i])
    top, where = max(rates)
    b = each * top
    how_b = ("$%.4f per objection (the highest of %d issue(s): %s; %d objection(s) in all) x %.2f objections per "
             "source (the most of any run: %s) = $%.4f" % (each, len([i for i in per_issue_obj if per_issue_obj[i]]),
                                                         worst, objections, top, where, b))
    if b > a:
        return b * MARGIN, "the higher of: %s; %s; x %g" % (how_b, how_a, MARGIN)
    return a * MARGIN, "the higher of: %s; %s; x %g" % (how_a, how_b, MARGIN)


def default_cap(issue: str) -> float:
    """A stage's --cap when none is given: what is left of the issue's cap
    (spend_ledger.cap_for, which honours issue.json's run_cap_usd), never more
    and never uncapped (advisor's ruling after Q1-01b). With no cap at all on
    the issue, the day's remaining room."""
    lim = S.cap_for(issue)
    if lim:
        return max(0.0, round(float(lim) - S.spent(issue=issue), 4))
    day = (S.caps() or {}).get("default_per_day") or 0
    return max(0.0, float(day))


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


def gate_bound(gate_config: dict, dry_estimate: float, issues_dir: Path | None = None,
               entries: list[dict] | None = None) -> tuple[float, str]:
    """The gate's pre-spend bound (advisor's ruling 1 on P140): max(the gate's own dry-run estimate, the highest
    measured gate run among the gate reports whose cost.lean_config equals GATE_CONFIG) x MARGIN. Each report
    (factcheck_draft.py's <draft>.gate*.json) records its run's config and measured spend since 2026-11-26."""
    idir = issues_dir or (ROOT / "issues")
    pool = []
    # the orchestrated gate runs in the ledger (one run = one issue's rows in one gate step), same model, when the
    # configuration is an orchestrated one; their reports predate cost.lean_config
    if gate_config.get("orchestrated"):
        runs: dict = defaultdict(float)
        for e in (S.entries() if entries is None else entries):
            if e.get("script") == "factcheck_draft.py" and e.get("step") in ("gate", "final_gate") and \
                    e.get("model") == gate_config.get("model"):
                runs[(e.get("issue"), e.get("step"))] += e.get("usd") or 0
        pool += [(v, Path(str(k[0])) / "draft" / str(k[1])) for k, v in runs.items() if v]
    for f in sorted(glob.glob(str(idir / "*" / "draft" / "*.gate*.json"))):
        try:
            c = (json.loads(Path(f).read_text(encoding="utf-8")).get("cost") or {})
        except Exception:
            continue
        lc = dict(c.get("lean_config") or {})
        if c.get("usd") and lc and {k: v for k, v in lc.items() if k != "limits"} == \
                {k: v for k, v in gate_config.items() if k != "limits"}:        # limits not matched (same_config)
            pool.append((float(c["usd"]), Path(f)))
    top, where = max(pool, key=lambda r: r[0]) if pool else (0.0, None)
    base = max(dry_estimate, top)
    how = ("max(the dry-run estimate $%.4f, the highest of %d same-config gate run(s) $%.4f%s) x %g"
           % (dry_estimate, len(pool), top, (" (%s)" % where.parent.parent.name) if where else "", MARGIN))
    return round(base * MARGIN, 4), how


def guard_amount(name: str, issue: str, amount: float, how: str) -> None:
    """guard() for a stage whose estimate is an amount already computed (the gate): the frozen-file check, then
    spend_ledger.check_cap with AMOUNT (the day, issue and line caps); a refusal prints and exits 3."""
    frozen = _frozen()
    if frozen.is_study(issue):
        try:
            frozen.verify_all()
        except frozen.FrozenFileChanged as e:
            print("\n  NOT STARTED: %s.\n  %s\n" % (name, e), file=sys.stderr)
            raise SystemExit(6)
    try:
        S.check_cap(issue, about_to_spend=amount)
    except S.OverCap as e:
        print("\n  NOT STARTED: %s is bounded at $%.2f (%s).\n  " % (name, amount, how)
              + str(e).replace("\n", "\n  ") + "\n", file=sys.stderr)
        raise SystemExit(3)
    left = remaining(issue)
    print("  stage cap: %s bounded at $%.2f (%s); $%s left today, $%s left on %s"
          % (name, amount, how, _d(left["day_left"]), _d(left["issue_left"]), issue))


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


def guard(stage: str, issue: str, units: int, model: str | None = None) -> None:
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
        r = check(stage, issue, units, **({"model": model} if model else {}))
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
