#!/usr/bin/env python3
"""Does the ruling model rule the same way twice? A seeded sample, re-run.

    consistency.py report SLUG                     agreement per step and for the issue
    consistency.py audit SLUG RUN_STAMP [--cap USD] sample an audit run's rulings

WHY THIS EXISTS
---------------
Every ruling on a study issue is the ruling model's (protocol rev 27), and
each is made once. Whether a second call on the identical payload would have
decided the same is a property of the process the study measures, and nothing
recorded it. This samples it, on study issues only.

WHAT IT DOES
------------
After each ruling step -- each `ruling.py` mode run (gate, conclusions,
changecheck, advocate, dangling), which calls sample_step itself, and each
audit run (`consistency.py audit`, after RUN.md steps 7 and 7c) -- it re-runs a seeded random
RATE (20%) of that step's rulings, at least 1: k = max(1, ceil(0.2 * n)),
chosen by random.Random(seed).sample. The seed is derived from the step's id
(sha256, first 12 hex digits) unless one is given, and both are logged.

Each sampled ruling is asked again with its IDENTICAL payload: the logged
inputs, through the same prompt file, whose sha256 must still equal the one
on the ruling (otherwise the sample refuses: it would not be the same
question). The pair -- the first decision and text, the second decision and
text -- is logged in rulings/consistency.jsonl (never committed: rulings/ is
excluded for WHU-P* and WHU-S*). THE SECOND RULING IS NEVER APPLIED: nothing
reads consistency.jsonl but this module's report.

Agreement: the same decision (accept / amend / reject) and the same text,
whitespace collapsed (two rejects, both with no text, agree). A second reply
that is not usable is logged as such and counted apart, not as a
disagreement. The report gives, per step and for the issue, how many pairs
agree on decision and text, and on decision alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

RATE = 0.2


def sample_size(n: int, rate: float = RATE) -> int:
    return 0 if n <= 0 else max(1, math.ceil(rate * n))


def seed_for(step: str) -> int:
    return int(hashlib.sha256(step.encode("utf-8")).hexdigest()[:12], 16)


def choose(n: int, seed: int, rate: float = RATE) -> list[int]:
    return sorted(random.Random(seed).sample(range(n), sample_size(n, rate)))


def _norm(t) -> str | None:
    return None if t is None else " ".join(str(t).split())


def _pair(first: dict, second: dict | None) -> dict:
    a = {"ruling": first.get("ruling"), "text": first.get("text")}
    if second is None:
        return {"first": a, "second": None, "usable": False}
    b = {"ruling": second.get("ruling"), "text": second.get("text")}
    same_decision = a["ruling"] == b["ruling"]
    return {"first": a, "second": b, "usable": True, "agree_decision": same_decision,
            "agree": same_decision and _norm(a["text"]) == _norm(b["text"])}


def sample_step(step: str, issue: str, kind: str, records: list[dict], reask, log: Path,
                seed: int | None = None, rate: float = RATE) -> dict:
    """Re-run a seeded sample of RECORDS (one ruling step) with `reask(record)`,
    which returns (second ruling dict or None if unusable, usage, note).
    Logs every pair and a step line; returns the step line."""
    seed = seed_for(step) if seed is None else seed
    idx = choose(len(records), seed, rate)
    ids = [records[i].get("id") for i in idx]
    log.parent.mkdir(parents=True, exist_ok=True)
    pairs = []
    for i in idx:
        r = records[i]
        second, usage, note = reask(r)
        p = dict({"type": "pair", "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "step": step, "issue": issue, "kind": kind, "seed": seed, "ruling_id": r.get("id"),
                  "prompt_sha256": r.get("prompt_sha256"), "inputs_sha256": r.get("inputs_sha256")
                  or r.get("payload_sha256"), **_pair(r, second), "usage": usage, "applied": False},
                 **({"note": note} if note else {}))
        pairs.append(p)
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    line = {"type": "step", "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "step": step, "issue": issue, "kind": kind, "seed": seed, "rate": rate,
            "rulings": len(records), "sampled": len(idx), "sampled_ids": ids, **_rates(pairs)}
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def _rates(pairs: list[dict]) -> dict:
    usable = [p for p in pairs if p.get("usable")]
    agree = sum(1 for p in usable if p.get("agree"))
    dec = sum(1 for p in usable if p.get("agree_decision"))
    return {"pairs": len(pairs), "usable": len(usable), "agree": agree, "agree_decision": dec,
            "agreement": round(agree / len(usable), 4) if usable else None,
            "decision_agreement": round(dec / len(usable), 4) if usable else None}


def load(log: Path) -> list[dict]:
    if not log.exists():
        return []
    return [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]


def report(log: Path) -> dict:
    """{"steps": {step: rates}, "issue": rates}, from the pairs logged."""
    pairs = [r for r in load(log) if r.get("type") == "pair"]
    steps: dict = {}
    for p in pairs:
        steps.setdefault(p["step"], []).append(p)
    return {"steps": {s: dict(_rates(ps), kind=ps[0].get("kind"), seed=ps[0].get("seed"))
                      for s, ps in steps.items()},
            "issue": _rates(pairs)}


def _pct(x) -> str:
    return "n/a" if x is None else "%.0f%%" % (100 * x)


def print_report(slug: str, log: Path) -> None:
    rep = report(log)
    print("\n  Ruling-model consistency, %s (%s)\n" % (slug, log))
    for s, r in rep["steps"].items():
        print("  %-40s %d pair(s), %d usable: %d agree (%s); decision alone %d (%s); seed %s"
              % (s, r["pairs"], r["usable"], r["agree"], _pct(r["agreement"]), r["agree_decision"],
                 _pct(r["decision_agreement"]), r["seed"]))
    i = rep["issue"]
    print("\n  issue: %d pair(s), %d usable: %d agree (%s); decision alone %d (%s)\n"
          % (i["pairs"], i["usable"], i["agree"], _pct(i["agreement"]), i["agree_decision"],
             _pct(i["decision_agreement"])))


# ---------------------------------------------------------------------------
# the two kinds of ruling log
# ---------------------------------------------------------------------------

def ruling_reask(call):
    """reask for a ruling.py record: the same prompt file, the logged inputs."""
    import ruling as R

    def reask(r: dict):
        kind = r["ruling_kind"]
        grouped = tuple(r["inputs"]) == R.GROUP_FIELDS
        if R.prompt_sha(kind, grouped) != r.get("prompt_sha256"):
            raise SystemExit("consistency sample refused: the %s prompt changed since ruling %s"
                             % (kind, r.get("id")))
        n_quotes = len(re.findall(r"(?m)^Quotation \d+:", r["inputs"].get("quoted_source_text") or ""))
        text, usage = call(R.build_prompt(kind, r["inputs"], grouped), R.MAX_OUT, "rule-%s-repeat" % kind)
        try:
            return R.parse(kind, text, n_quotes), usage, None
        except R.RulingError as e:
            return None, usage, "second reply not usable: %s" % e
    return reask


def audit_reask(call):
    """reask for an audit-stage ruling: audit_stage's prompt, the logged payload."""
    import audit_stage as A

    def reask(r: dict):
        if A.sha(A.RULE_PROMPT.read_text(encoding="utf-8")) != r.get("prompt_sha256"):
            raise SystemExit("consistency sample refused: the audit ruling prompt changed since %s"
                             % r.get("id"))
        text, usage = call(A.build_rule_prompt(r["inputs"]), A.RULE_MAX_OUT, "rule-repeat")
        try:
            return A.check_ruling(A.parse_json(text)), usage, None
        except Exception as e:
            return None, usage, "second reply not usable: %s" % e
    return reask


def record_id(r: dict) -> str:
    """A ruling's id: its own "id", else (an audit ruling, or one logged before
    ids) sha256 of its time, unit or kind, round and inputs, 16 hex digits."""
    if r.get("id"):
        return r["id"]
    key = json.dumps([r.get("at"), r.get("unit") or r.get("ruling_kind"), r.get("round"),
                      r.get("inputs")], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def log_path(slug: str) -> Path:
    import source_store as store
    return store.case_dir(slug) / "rulings" / "consistency.jsonl"


def _require_study(slug: str) -> None:
    import publish as P
    if not P.is_study(slug):
        raise SystemExit("%s is not a study issue (issue.json \"study\": true)" % slug)


def cmd_audit(a) -> int:
    import audit_stage as A
    import source_store as store
    _require_study(a.slug)
    run = store.case_dir(a.slug) / "audit" / a.run
    import applied_check as AC
    if AC._withdrawn(run):
        raise SystemExit("audit run %s is withdrawn; its rulings are not sampled" % a.run)
    recs = [dict(r, id=record_id(r)) for r in load(run / "rulings.jsonl")]
    if not recs:
        raise SystemExit("no rulings in %s" % run)
    step = "audit-%s" % a.run
    if any(r.get("step") == step for r in load(log_path(a.slug))):
        raise SystemExit("audit run %s has been sampled already" % a.run)
    import stage_cap
    stage_cap.guard("rulings", a.slug, sample_size(len(recs)))
    call = A.Caller(cap=a.cap, ledger_issue=a.slug)
    line = sample_step(step, a.slug, "audit", recs, audit_reask(call), log_path(a.slug), seed=a.seed)
    print("  sampled %d of %d audit ruling(s), seed %d: %d of %d usable pair(s) agree"
          % (line["sampled"], line["rulings"], line["seed"], line["agree"], line["usable"]))
    print_report(a.slug, log_path(a.slug))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("report")
    r.add_argument("slug")
    au = sub.add_parser("audit")
    au.add_argument("slug")
    au.add_argument("run", help="the audit run's UTC stamp (audit/<stamp>/)")
    au.add_argument("--cap", type=float, default=5.0)
    au.add_argument("--seed", type=int, help="default: derived from the step id, and logged")
    a = ap.parse_args(argv)
    if a.cmd == "report":
        _require_study(a.slug)
        print_report(a.slug, log_path(a.slug))
        return 0
    return cmd_audit(a)


if __name__ == "__main__":
    raise SystemExit(main())
