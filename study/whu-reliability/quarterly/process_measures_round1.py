#!/usr/bin/env python3
"""WHU quarterly round 1: the protocol §5 reports not in round1_ai_only.json:
cost and elapsed time per system (M4), and WHU's process measures for the
four runs (as the re-run plan lists them).

    process_measures_round1.py

Writes quarterly/round1_scoring/process_measures_round1.json: counts, times,
dollars and ids only. Free: no model is called; `publish.py check` is read
only.

SOURCES.
  WHU spend: backend/data/spend/ledger.jsonl, each round-1 issue, by the
    ledger's own "script" field; and per stage as each run's study_log.md
    table records it (stage number, metered spend).
  WHU elapsed: study_log.md stage rows, first start to the `Ready.` row (or,
    for WHU-Q1-02, its last row), and the sum of the stage rows' own spans.
  New preflight rows (CLAUDE.md, fixes 1-3): `publish.py check <slug>` now.
  ADDs, declarations, judgement candidates: those rows' own counts.
  Items sent to a person: rulings/for_person.jsonl rows; person reads in the
    final audit run (audit/<run>/human_reads.jsonl).
  Ruling-model consistency: rulings/consistency.jsonl summary rows.
  Tools: run_record.md (private), minutes as Fred recorded them. The tools
    are flat-rate subscriptions; no per-run cost is metered.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = HERE / "round1_scoring" / "process_measures_round1.json"
SLUGS = {"WHU-Q1-01": "whu-quarterly-r1-01", "WHU-Q1-02": "whu-quarterly-r1-02",
         "WHU-Q1-03": "whu-quarterly-r1-03", "WHU-Q1-04": "whu-quarterly-r1-04"}
NEW_ROWS = ["protected sentences kept", "omission objections ruled", "headline conclusions accounted for",
            "declared findings shown to readers", "assessment judgements stated", "scope declared",
            "evidence standard declared"]
TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d)?Z)$")
# Tool minutes from run_record.md ("Took"), as Fred recorded them; None where not observed.
TOOL_MINUTES = {
    "Claude": {"WHU-Q1-01": 7, "WHU-Q1-02": 6, "WHU-Q1-03": None, "WHU-Q1-04": 5},
    "ChatGPT": {"WHU-Q1-01": 8, "WHU-Q1-02": 10, "WHU-Q1-03": 8, "WHU-Q1-04": 7},
    "Gemini": {"WHU-Q1-01": 12, "WHU-Q1-02": 6, "WHU-Q1-03": 28, "WHU-Q1-04": "no result (two technical failures)"},
    "Perplexity": {"WHU-Q1-01": "at most 11", "WHU-Q1-02": 11, "WHU-Q1-03": None, "WHU-Q1-04": 9},
}


def ts(s: str) -> datetime | None:
    s = s.strip()
    if not TS.match(s):
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def stage_rows(log: str) -> list[dict]:
    out = []
    for line in log.splitlines():
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 6:
            continue
        a, b = ts(c[1]), ts(c[2])
        m = re.match(r"\$?(\d+(?:\.\d+)?)", c[3].replace("$", "")) if c[3] else None
        if not a or not b:
            continue
        out.append({"stage": c[0].split()[0], "start": a, "end": b,
                    "usd": float(m.group(1)) if m else None, "ready": c[-1].lstrip("*").startswith("Ready.")
                    or "**Ready.**" in c[-1]})
    return out


def ledger() -> list[dict]:
    rows = []
    for line in (REPO / "backend" / "data" / "spend" / "ledger.jsonl").read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def check_rows(slug: str) -> dict:
    p = subprocess.run([str(REPO / "backend" / "venv" / "bin" / "python3"),
                        str(REPO / "backend" / "scripts" / "whatholdsup" / "publish.py"), "check", slug],
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    out, verdict = {}, None
    for line in p.stdout.splitlines():
        s = line.strip()
        if s.startswith(("Ready.", "BLOCKED")):
            verdict = s.split("—")[0].strip()
        for name in NEW_ROWS:
            m = re.match(r"^(ok|warn|STOP)\s+" + re.escape(name) + r"\s+(.*)$", s)
            if m:
                out[name] = {"outcome": m.group(1), "detail": m.group(2)[:200]}
    return {"rows": out, "verdict": verdict}


def counts_from(rows: dict) -> dict:
    g = lambda name: (rows.get(name) or {}).get("detail", "")
    om = dict((k, int(v)) for v, k in re.findall(r"(\d+) (ADD|NOT_IN_SOURCE|NOT_MATERIAL|TO_PERSON)", g("omission objections ruled")))
    dec = re.search(r"(\d+) declared finding\(s\).*?(\d+) counted against the budget of (\d+)", g("declared findings shown to readers"))
    j = g("assessment judgements stated")
    jm = {k: int(v) for v, k in re.findall(r"(\d+) (held assessment judgement|relevant|stated|declared)", j)}
    return {"omission_decisions": om, "ADD_sentences": om.get("ADD", 0),
            "declared_findings": int(dec.group(1)) if dec else None,
            "declarations_budget": int(dec.group(3)) if dec else None,
            "declarations_over_budget": (int(dec.group(2)) > int(dec.group(3))) if dec else None,
            "judgement_candidates": jm.get("held assessment judgement"), "judgements_relevant": jm.get("relevant"),
            "judgements_stated": jm.get("stated", 0), "judgements_declared": jm.get("declared", 0)}


def consistency(d: Path) -> list[dict]:
    out = []
    for line in (d / "rulings" / "consistency.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("type") == "pair":
            continue
        out.append({"step": r.get("step"), "kind": r.get("kind"), "rulings": r.get("rulings"),
                    "sampled": r.get("sampled"), "pairs": r.get("pairs"), "agreement": r.get("agreement"),
                    "decision_agreement": r.get("decision_agreement")})
    return out


def main() -> int:
    led = ledger()
    whu = {}
    for q, slug in SLUGS.items():
        d = next((REPO / "issues").glob(q + "-*"))
        rows = stage_rows((d / "study_log.md").read_text())
        ready = [r for r in rows if r["ready"]]
        end = (ready[-1] if ready else rows[-1])["end"]
        by_stage = {}
        for r in rows:
            if r["usd"] is not None:
                by_stage[r["stage"]] = round(by_stage.get(r["stage"], 0.0) + r["usd"], 4)
        by_script = {}
        for e in led:
            if e.get("issue") == slug:
                k = Path(e.get("script") or "?").name
                by_script[k] = round(by_script.get(k, 0.0) + float(e.get("usd") or 0), 4)
        chk = check_rows(slug)
        audits = sorted((d / "audit").glob("*/human_reads.jsonl"))
        fp = d / "rulings" / "for_person.jsonl"
        whu[q] = {
            "spend_usd": round(sum(by_script.values()), 2), "spend_by_script": by_script,
            "spend_by_stage_from_study_log": by_stage,
            "elapsed": {"first_start": rows[0]["start"].isoformat(), "answer_at": end.isoformat(),
                        "wall_clock_minutes": round((end - rows[0]["start"]).total_seconds() / 60, 1),
                        "stage_rows_minutes": round(sum((r["end"] - r["start"]).total_seconds() for r in rows) / 60, 1),
                        "reached": "Ready." if ready else "STOP (corrections not yet read; advisor ruling)"},
            "publish_check_now": chk["verdict"], "new_preflight_rows": chk["rows"],
            **counts_from(chk["rows"]),
            "sent_to_a_person": {"for_person_rows": sum(1 for l in fp.read_text().splitlines() if l.strip()) if fp.exists() else 0,
                                 "person_reads_final_audit_run": sum(1 for l in audits[-1].read_text().splitlines() if l.strip()) if audits else 0,
                                 "audit_runs": len(list((d / "audit").glob("*/")))},
            "ruling_model_consistency": consistency(d),
        }
    res = {"label": "WHU quarterly round 1: cost, elapsed time (M4) and WHU's process measures",
           "rules": "quarterly/process_measures_round1.py docstring",
           "M4": {"WHU": {q: {"usd": v["spend_usd"], "wall_clock_minutes": v["elapsed"]["wall_clock_minutes"],
                              "stage_rows_minutes": v["elapsed"]["stage_rows_minutes"]} for q, v in whu.items()},
                  "tools_minutes": TOOL_MINUTES,
                  "tools_cost": "flat-rate subscriptions; no per-run cost metered (round1_capture.md)"},
           "WHU_process": whu}
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    for q, v in whu.items():
        print(q, v["spend_usd"], v["elapsed"], v["publish_check_now"], {k: v[k] for k in ("ADD_sentences", "declared_findings", "declarations_budget", "judgement_candidates", "judgements_relevant", "judgements_stated", "judgements_declared")},
              v["sent_to_a_person"], {k: x["outcome"] for k, x in v["new_preflight_rows"].items()})
        print("   stages", v["spend_by_stage_from_study_log"])
        print("   consistency", [(c["step"][:22] if c["step"] else None, c["pairs"], c["agreement"], c["decision_agreement"]) for c in v["ruling_model_consistency"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
