"""The replay gate (advisor's ruling 2 on the design review of 2026-11-26): before any paid orchestrated run, the replay
rehearsal (orch/replay_rehearsal.py) of every recorded run in RUNS must pass on the code as it stands.

    python3 orch/replay_gate.py run [--offline]   replay each run; write the gate record; exit 0 only if all pass
    python3 orch/replay_gate.py check             exit 0 only if a passing record exists for the current code

A replay PASSES when it ends
  * Ready., or
  * with the honest outcome "Insufficient sources: ..." (thin_sources.py), or
  * Not Ready by design at the recorded run's last step or later, with no STOP row the recorded run did not have;
and FAILS when it ends on an exception (a plumbing fault: "Not Ready: <Name>Error: ..."), when a prompt no
generator recognises was met, or Not Ready by design EARLIER than the recorded run without an outcome to explain it.
An outage ("registry unavailable" / "model unavailable") is INCONCLUSIVE, which fails the gate: run it again later.

The gate record (private: it names documents) is ~/Projects/whu-study-private/replay_gate/<code sha>.json, where the
code sha is replay_rehearsal.code_sha(); `orchestrator.py run --mode paid` refuses without a passing one.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from orch import replay_rehearsal as RR  # noqa: E402

RUNS = ["whu-lean-orch-t1-q1-02z", "whu-lean-orch-t1-q1-02za", "whu-lean-orch-t1-q1-02zc",
        "whu-lean-orch-t1-q1-02zd"]
GATE_DIR = RR.PRIVATE / "replay_gate"
EXCEPTION = re.compile(r"^Not Ready: [A-Z][A-Za-z]*(Error|Exception|Exit)\b")
OUTAGE = re.compile(r"(registry|model) unavailable; run again later")


def _order() -> list[str]:
    from orch import steps as ST
    return [s.name for s in ST.STEPS]


def _recorded(slug: str) -> dict:
    case = next((ROOT / "issues").glob("WHU-*-%s" % slug))
    d = json.loads((case / "orchestrator" / "run_paid.json").read_text(encoding="utf-8"))
    steps = [s.get("step") for s in d.get("steps") or []]
    return {"case": case, "result": d.get("result"), "last": steps[-1] if steps else None,
            "stops": _stop_rows(case)}


def _key(line: str) -> str:
    """A STOP row's identity: the first words of its label (code_preflight keeps each row whitespace-collapsed)."""
    w = str(line).split()
    return " ".join(w[1:4]) if w and w[0] == "STOP" else " ".join(w[:3])


def _stop_rows(case: Path, record: str = "run_paid.json") -> set:
    """STOP rows of a run's last preflight, when it reached one (code_preflight's `stops`)."""
    p = case / "orchestrator" / record
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    out = set()
    for s in d.get("steps") or []:
        if s.get("step") == "preflight":
            out = {_key(x) for x in (s.get("code") or {}).get("stops") or []}
    return out


def judge(rec: dict, rep: dict, unknown: int) -> tuple[str, str]:
    result = str(rep.get("result") or "")
    if unknown:
        return "FAIL", "%d prompt(s) no generator recognises" % unknown
    if result == "Ready.":
        return "PASS", "Ready."
    if result.startswith("Insufficient sources:"):
        return "PASS", result
    if OUTAGE.search(result):
        return "INCONCLUSIVE", result[:200]
    if EXCEPTION.search(result) or "Traceback" in result:
        return "FAIL", "plumbing: %s" % result[:300]
    order = _order()
    steps = [s.get("step") for s in rep.get("steps") or []]
    last = steps[-1] if steps else None
    ri = order.index(rec["last"]) if rec["last"] in order else -1
    li = order.index(last) if last in order else -1
    if li < ri:
        return "FAIL", "ended at %s, earlier than the recorded run's %s: %s" % (last, rec["last"], result[:200])
    new = rep.get("_stops", set()) - rec["stops"]
    if new:
        return "FAIL", "new STOP row(s): %s" % ", ".join(sorted(new))
    return "PASS", "Not Ready at %s (the recorded run ended at %s): %s" % (last, rec["last"], result[:160])


def replay_one(slug: str, offline: bool, out_dir: Path) -> dict:
    state = out_dir / slug
    state.mkdir(parents=True, exist_ok=True)
    summary = state / "summary.json"
    plan = HERE / "orch" / "rehearsal_plans" / "none.json"
    argv = [str(ROOT / "backend" / "venv" / "bin" / "python3"), str(HERE / "orchestrator.py"), "rehearse", slug,
            "--slug", "whu-replay-" + slug.rsplit("-", 1)[-1], "--replay", "--plan", str(plan),
            "--state", str(state), "--out", str(summary)] + (["--offline"] if offline else [])
    env = {k: v for k, v in os.environ.items() if not k.startswith("WHU_ORCH_")}
    env["WHU_LEAN"] = "1"
    with (state / "gate.log").open("w", encoding="utf-8") as fh:
        rc = subprocess.run(argv, cwd=str(ROOT), env=env, stdout=fh, stderr=subprocess.STDOUT).returncode
    rep = json.loads(summary.read_text(encoding="utf-8")) if summary.exists() else {"result": "no summary (rc %d)" % rc}
    unknown = len(list((state / "unknown").glob("*.txt"))) if (state / "unknown").exists() else 0
    sources = _sources(state / "events.jsonl")
    rec = _recorded(slug)
    rep["_stops"] = _stop_rows(state / "case", "run_rehearse.json")
    verdict, why = judge(rec, rep, unknown)
    return {"slug": slug, "verdict": verdict, "why": why, "rc": rc, "result": rep.get("result"),
            "steps": [s.get("step") for s in rep.get("steps") or []], "recorded_result": rec["result"],
            "recorded_last_step": rec["last"], "replies": sources, "unknown_prompts": unknown,
            "stops": sorted(rep["_stops"]), "recorded_stops": sorted(rec["stops"]),
            "seeded": _seeded(state)}


def _sources(events: Path) -> dict:
    out = {}
    try:
        for line in events.read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            if e.get("event") == "replayed":
                k = "%s:%s" % (e.get("source"), e.get("generator"))
                out[k] = out.get(k, 0) + 1
    except (OSError, ValueError):
        pass
    return out


def _seeded(state: Path) -> int:
    try:
        return sum(1 for r in json.loads((state / "seeded.json").read_text()) if r.get("seeded"))
    except (OSError, ValueError):
        return 0


def record_path(sha: str | None = None) -> Path:
    return GATE_DIR / ("%s.json" % (sha or RR.code_sha()))


def run(offline: bool = False) -> dict:
    sha = RR.code_sha()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = GATE_DIR / "runs" / stamp
    rows = [replay_one(s, offline, out_dir) for s in RUNS]
    rec = {"code_sha": sha, "at": stamp, "offline": offline, "runs": rows,
           "passed": all(r["verdict"] == "PASS" for r in rows)}
    GATE_DIR.mkdir(parents=True, exist_ok=True)
    record_path(sha).write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return rec


def check() -> tuple[bool, str]:
    sha = RR.code_sha()
    p = record_path(sha)
    if not p.exists():
        return False, "no replay gate record for this code (%s): run orch/replay_gate.py run" % sha[:12]
    d = json.loads(p.read_text(encoding="utf-8"))
    if not d.get("passed"):
        bad = ["%s %s" % (r["slug"], r["verdict"]) for r in d.get("runs") or [] if r.get("verdict") != "PASS"]
        return False, "the replay gate did not pass for this code (%s): %s" % (sha[:12], "; ".join(bad))
    return True, "the replay gate passed for this code (%s, %s)" % (sha[:12], d.get("at"))


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--offline", action="store_true")
    sub.add_parser("check")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        ok, why = check()
        print(why)
        return 0 if ok else 1
    rec = run(offline=a.offline)
    print(json.dumps({"passed": rec["passed"], "code_sha": rec["code_sha"][:12],
                      "runs": [{k: r[k] for k in ("slug", "verdict", "why", "replies", "seeded")}
                               for r in rec["runs"]]}, indent=1))
    return 0 if rec["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
