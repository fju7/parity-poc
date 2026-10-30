#!/usr/bin/env python3
"""Check 10, prompt wording (validity plan §8): the two existing judges re-read a seeded 20% of round-1 items with the
alternative wording.

    check10.py sample                 the items (free; written once to the private run record)
    check10.py run --cap 30           M1 then M2, through judge_m1.py / judge_m2.py, replies tag "_c10alt"

THE SWAP (advisor's terms, 2026-10-30). Before every stage this wrapper: checks the alternative prompt's sha256
against the value frozen in the plan; checks the frozen prompt's sha256 is unchanged (it is only read, never
written); calls spend_ledger.check_day_cap with the stage's worst case; then points the runner's module globals
PROMPT / PROMPT_SHA256 / PROMPT_VERSION at the alternative, in memory, and calls the runner's own main(). Each swap
is appended to the run record (~/Projects/whu-study-private/validity/check10/run_record.jsonl): paths, both hashes,
time. The runners' frozen-prompt check then passes for the alternative's own hash; nothing else in them changes.

SAMPLE. 20% within system (round(0.2 * n)) of round 1's judged items: M1 items with a first-read Claude reply that
is not INCOMPLETE_SOURCES (217), M2 items (91); random.Random("%d/check10/%s/%s" % (SEED, measure, system)).
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import judge_m1 as J1  # noqa: E402
import judge_m2 as J2  # noqa: E402

S = J1.S
PLAN_FREEZE = "b4cf31ad19046a63073461fc5195415bc496594b"
SEED = int(PLAN_FREEZE, 16)
RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "quarterly" / "round1"
REC = Path.home() / "Projects" / "whu-study-private" / "validity" / "check10"
ISSUE = "whu-reliability-judging-validity-c10"
TAG = "_c10alt"
ALT = {"M1": (HERE / "prompts" / "m1_citation_support_alt.md",
              "589f8dd8f522cf1186aac6a9f2229ed59e6b31dabb76423c7070df74e564dfa9", "v3-alt-c10"),
       "M2": (HERE / "prompts" / "m2_conclusion_calibration_alt.md",
              "1f74129bc7960ed511b871735d84ecc2124a3253ddac464db5dafb3b91597601", "v2-alt-c10")}
FROZEN = {"M1": (J1.PROMPT, J1.PROMPT_SHA256), "M2": (J2.PROMPT, J2.PROMPT_SHA256)}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sample() -> dict:
    f = REC / "sample.json"
    if f.exists():
        return json.loads(f.read_text())
    km1 = json.loads((RUN / "m1" / "key_map.json").read_text())
    by: dict = {"M1": {}, "M2": {}}
    for p in sorted((RUN / "m1" / "replies" / "claude").glob("*.json")):
        r = json.loads(p.read_text())
        if r.get("label") != J1.INCOMPLETE_SOURCES:
            by["M1"].setdefault(km1[r["item"]]["system"], []).append(r["item"])
    spec = json.loads((RUN / "m2" / "items.json").read_text())
    km2 = json.loads((RUN / "m2" / "key_map.json").read_text())
    for it in spec["items"]:
        by["M2"].setdefault(km2[it["answer"]]["system"], []).append(it["item"])
    out = {"seed": "SEED=%s" % PLAN_FREEZE, "pools": {}, "items": {}}
    for m in ("M1", "M2"):
        out["items"][m] = []
        for s in sorted(by[m]):
            pool = sorted(by[m][s])
            k = round(0.2 * len(pool))
            out["pools"]["%s/%s" % (m, s)] = {"N": len(pool), "n": k}
            out["items"][m] += sorted(random.Random("%d/check10/%s/%s" % (SEED, m, s)).sample(pool, k))
    REC.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out, indent=1))
    return out


def swap(measure: str, mod) -> None:
    path, want, version = ALT[measure]
    got = sha(path)
    if got != want:
        raise SystemExit("STOP: %s has sha256 %s, not the frozen %s" % (path, got, want))
    fp, fs = FROZEN[measure]
    if sha(fp) != fs:
        raise SystemExit("STOP: the frozen %s prompt %s has changed (sha256 %s)" % (measure, fp, sha(fp)))
    mod.PROMPT, mod.PROMPT_SHA256, mod.PROMPT_VERSION = path, want, version
    with (REC / "run_record.jsonl").open("a") as f:
        f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "measure": measure,
                            "frozen_prompt": str(fp), "frozen_sha256": fs, "alternative_prompt": str(path),
                            "alternative_sha256": want, "version_recorded": version, "tag": TAG}) + "\n")


def stage_estimate(run_dir: Path, items: list[str]) -> float:
    """Round 1's recorded first-read cost of these items, both judges. Those first reads already paid the cache
    write (Claude) and uncached input (OpenAI) a new prompt pays, so no margin is added; the runners hold --cap per
    call."""
    usd = 0.0
    for j in ("claude", "openai"):
        for i in items:
            f = run_dir / "replies" / j / (i + ".json")
            if f.exists():
                usd += float(json.loads(f.read_text()).get("usd") or 0)
    return round(usd, 4)


def run(cap: float) -> int:
    smp = sample()
    est = {m: stage_estimate(RUN / m.lower(), smp["items"][m]) for m in ("M1", "M2")}
    print("ESTIMATE (round 1's recorded first-read cost of these items, both judges): M1 $%.2f, M2 $%.2f, total $%.2f;"
          " cap $%.2f; %s spent so far $%.2f" % (est["M1"], est["M2"], est["M1"] + est["M2"], cap, ISSUE, J1.spent(ISSUE)))
    if est["M1"] + est["M2"] > cap:
        print("STOP: the estimate is over the cap; nothing was called")
        return 3
    for measure, mod, run_dir in (("M1", J1, RUN / "m1"), ("M2", J2, RUN / "m2")):
        items = smp["items"][measure]
        swap(measure, mod)
        try:
            S.check_day_cap(est[measure])   # the all-spend day cap, for the whole stage, before it starts
        except S.OverCap as e:
            print("STOP before %s: %s" % (measure, e))
            return 3
        argv = [str(run_dir), "--only", ",".join(items), "--judges", "claude,openai", "--tag", TAG,
                "--ledger-issue", ISSUE, "--cap", str(cap), "--consistency-share", "0"]
        print("== %s: %d items, prompt %s (sha256 %s…)" % (measure, len(items), ALT[measure][0].name, ALT[measure][1][:8]),
              flush=True)
        sys.argv = [mod.__file__] + argv
        rc = mod.main()
        if rc:
            print("STOP: %s runner exited %s" % (measure, rc))
            return rc
    print("%s spent: $%.4f" % (ISSUE, J1.spent(ISSUE)))
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "sample":
        print(json.dumps(sample()["pools"], indent=1))
        raise SystemExit(0)
    if cmd == "run" and "--cap" in sys.argv:
        raise SystemExit(run(float(sys.argv[sys.argv.index("--cap") + 1])))
    print(__doc__)
    raise SystemExit(2)
