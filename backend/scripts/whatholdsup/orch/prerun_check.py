"""The full pre-run check before a paid orchestrated batch, in under 15 minutes of wall time (advisor's ruling 2 on the
replay gate, 2026-11-26), with every check's real exit code and its wall time.

    python3 orch/prerun_check.py [--out FILE]        exit 0 only if every check passed

What runs, all at once (each its own process; the rehearsals and replays each in their own Sandbox, state and temp
directory, so they share nothing but the machine-wide NCBI pacer):
  * suite               the default suite (pytest, no markers), ONCE;
  * rehearsal:<test>    each `-m rehearsal` test in its own pytest process -- these run the offline rehearsals none,
                        europepmc_down, only_crossref_answers, shapes_and_faults, registry_outage, model_outage (+
                        resume) and registries_down_at_confirm (+ resume), with more assertions than the standalone
                        `rehearse --offline` runs the old check made, which are therefore no longer run (the
                        duplicate; their one assertion each -- the result -- is asserted by these tests);
  * replay_gate         orch/replay_gate.py run (the four replays in parallel), then `check`.
Deselected: test_the_suite_passes_while_a_rehearsal_runs, which ran the whole suite a second time beside one
rehearsal; this check runs the suite beside the rehearsals and asserts that they overlapped (`overlap`), so its
assertion (the suite passes while a rehearsal runs) is kept here.

The record (--out, default ~/Projects/whu-study-private/prerun/<UTC stamp>.json) names each check's command, exit
code, start, end, seconds and the tail of its output.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
BACKEND = ROOT / "backend"
PY = str(BACKEND / "venv" / "bin" / "python")
PRIVATE = Path.home() / "Projects" / "whu-study-private" / "prerun"
REHEARSAL_FILES = ["tests/test_whu_orch_rehearsal.py", "tests/test_whu_orch_after_attempt24.py"]
DESELECT = "test_the_suite_passes_while_a_rehearsal_runs"


def rehearsal_tests() -> list[str]:
    """The node ids of the `-m rehearsal` tests, less DESELECT (collected, never typed)."""
    out = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--collect-only", "-m", "rehearsal"]
                         + REHEARSAL_FILES, cwd=str(BACKEND), capture_output=True, text=True)
    ids = [l.strip() for l in out.stdout.splitlines() if "::" in l and not l.startswith(" ")]
    if out.returncode != 0 or not ids:
        raise SystemExit("could not collect the rehearsal tests (exit %d): %s" % (out.returncode, out.stdout[-500:]))
    return [i for i in ids if not i.endswith("::" + DESELECT)]


def checks() -> list[dict]:
    env = {k: v for k, v in os.environ.items() if k != "TMPDIR" and not k.startswith("WHU_ORCH_")}
    out = [{"name": "suite", "argv": [PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], "cwd": BACKEND, "env": env}]
    for node in rehearsal_tests():
        out.append({"name": "rehearsal:" + node.split("::")[-1], "argv": [PY, "-m", "pytest", "-q", "-p",
                    "no:cacheprovider", "-m", "rehearsal", node], "cwd": BACKEND, "env": env})
    genv = dict(env, WHU_LEAN="1")
    out.append({"name": "replay_gate", "argv": [str(BACKEND / "venv" / "bin" / "python3"),
                str(HERE / "orch" / "replay_gate.py"), "run"], "cwd": ROOT, "env": genv,
                "then": [str(BACKEND / "venv" / "bin" / "python3"), str(HERE / "orch" / "replay_gate.py"), "check"]})
    return out


def _run(c: dict, logdir: Path) -> dict:
    log = logdir / (c["name"].replace(":", "_") + ".out")
    t0, start = time.monotonic(), datetime.now(timezone.utc)
    with log.open("w", encoding="utf-8") as fh:
        rc = subprocess.run(c["argv"], cwd=str(c["cwd"]), env=c["env"], stdout=fh, stderr=subprocess.STDOUT).returncode
        then_rc = None
        if c.get("then"):
            fh.write("\n--- %s\n" % " ".join(c["then"][-2:]))
            fh.flush()
            then_rc = subprocess.run(c["then"], cwd=str(c["cwd"]), env=c["env"], stdout=fh,
                                     stderr=subprocess.STDOUT).returncode
    end = datetime.now(timezone.utc)
    tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
    row = {"name": c["name"], "argv": c["argv"][1:], "exit": rc, "start": start.isoformat(timespec="seconds"),
           "end": end.isoformat(timespec="seconds"), "seconds": round(time.monotonic() - t0, 1), "tail": tail,
           "log": str(log)}
    if then_rc is not None:
        row["check_exit"] = then_rc
    row["passed"] = rc == 0 and then_rc in (None, 0)
    return row


def overlap(rows: list[dict]) -> bool:
    """Whether the suite ran while at least one rehearsal ran (DESELECT's assertion, kept here)."""
    s = next(r for r in rows if r["name"] == "suite")
    return any(r["name"].startswith("rehearsal:") and r["start"] < s["end"] and s["start"] < r["end"] for r in rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logdir = PRIVATE / stamp
    logdir.mkdir(parents=True, exist_ok=True)
    cs = checks()
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=len(cs)) as ex:
        rows = list(ex.map(lambda c: _run(c, logdir), cs))
    wall = round(time.monotonic() - t0, 1)
    ov = overlap(rows)
    rec = {"at": stamp, "head": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                                               capture_output=True, text=True).stdout.strip(),
           "wall_seconds": wall, "under_15_minutes": wall < 900, "suite_overlapped_a_rehearsal": ov,
           "checks": rows, "passed": all(r["passed"] for r in rows) and ov}
    out = Path(a.out) if a.out else logdir.with_suffix(".json")
    out.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    for r in sorted(rows, key=lambda r: -r["seconds"]):
        print("%-70s exit=%s%s %6.1f min  %s" % (r["name"], r["exit"], (" check_exit=%s" % r["check_exit"])
              if "check_exit" in r else "", r["seconds"] / 60, (r["tail"] or [""])[-1][:120]))
    print("wall %.1f min; suite overlapped a rehearsal: %s; passed: %s; record %s" % (wall / 60, ov, rec["passed"], out))
    return 0 if rec["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
