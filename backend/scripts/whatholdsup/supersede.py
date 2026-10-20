#!/usr/bin/env python3
"""Supersede a study issue's rulings and records, so no current tool reads them.

    supersede.py SLUG --reason "why" --by "Claude Code (session <id>)" [--only NAME ...]

WHY THIS EXISTS
---------------
For WHU-P02's clean re-run (2026-10-20) every earlier ruling and decision
record had to stop counting without being lost: each record was stamped
"superseded": {reason, on, by} and the files were moved where no current tool
reads them -- rulings/superseded/ and advocate/superseded/ -- by hand, because
no tool did it. This is that tool. It runs on a study issue only
(issue.json "study": true); a published issue's records are corrected, not
superseded.

WHAT IT DOES
------------
Each file in RECORDS that exists is stamped and moved to its folder as
"<UTC stamp>-<name>":

  a .jsonl file    every record gets "superseded": {reason, on, by}
  a .json object   it gets a top-level "superseded"
  a .json list     every object in it gets "superseded"
  a .md file       a first line says it is superseded, why, on, by

and the folder's README.txt gets a line. Nothing is deleted. Audit runs are
not touched: they are withdrawn with `audit_stage.py withdraw`. `--only` limits
the run to the named files (as RECORDS names them).

WHO. --by names whoever runs it. An agent writes its own name
(signers.AGENTS, optionally "(session <id>)"); a person's name needs
--signature <path>:<line> of a committed acceptance line, checked by
signers.check_source, as on a binding row (process doc section 8).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# (name as --only takes it, path pattern under the case directory, destination folder)
RECORDS = (
    ("rulings", "rulings/rulings.jsonl", "rulings/superseded"),
    ("applied_check", "rulings/applied_check.jsonl", "rulings/superseded"),
    ("change-reviews", "change-reviews.json", "rulings/superseded"),
    ("conclusion-review", "conclusion-review.json", "rulings/superseded"),
    ("gate-findings", "gate-findings.json", "rulings/superseded"),
    ("advocate-briefs", "advocate/*-briefs.json", "advocate/superseded"),
    ("advocate-adjudication", "advocate/*-adjudication.md", "advocate/superseded"),
)


def stamp_file(src: Path, dst: Path, mark: dict) -> None:
    """Write SRC to DST with every record stamped, then remove SRC."""
    text = src.read_text(encoding="utf-8")
    if src.suffix == ".jsonl":
        out = []
        for line in text.splitlines():
            if line.strip():
                out.append(json.dumps(dict(json.loads(line), superseded=mark), ensure_ascii=False))
        body = "\n".join(out) + ("\n" if out else "")
    elif src.suffix == ".json":
        d = json.loads(text)
        if isinstance(d, dict):
            d["superseded"] = mark
        elif isinstance(d, list):
            d = [dict(x, superseded=mark) if isinstance(x, dict) else x for x in d]
        body = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    else:
        body = ("SUPERSEDED on %s by %s: %s\n\n" % (mark["on"], mark["by"], mark["reason"])) + text
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise SystemExit("refusing to overwrite %s" % dst)
    dst.write_text(body, encoding="utf-8")
    src.unlink()


def check_by(by: str, signature: str | None) -> None:
    import signers
    if not (by or "").strip():
        raise SystemExit("--by is required")
    if signers.is_agent(by):
        return
    if not signature:
        raise SystemExit("%r is not an agent's name (signers.AGENTS). A person's name needs "
                         "--signature <path>:<line> of their committed acceptance line." % by)
    ok, why = signers.check_source(by, signature)
    if not ok:
        raise SystemExit("signature refused: %s" % why)


def supersede(case: Path, reason: str, by: str, *, only=None, on: str | None = None,
              now: datetime | None = None) -> list[tuple[str, str]]:
    """Stamp and move every record present; return [(from, to)] relative to CASE."""
    if not (reason or "").strip():
        raise ValueError("superseding needs a reason")
    now = now or datetime.now(timezone.utc)
    mark = {"reason": reason.strip(), "on": on or now.date().isoformat(), "by": by.strip()}
    prefix = now.strftime("%Y%m%dT%H%MZ")
    names = {n for n, _p, _d in RECORDS}
    if only:
        bad = set(only) - names
        if bad:
            raise ValueError("unknown record(s): %s (one of %s)" % (", ".join(sorted(bad)), ", ".join(sorted(names))))
    moved, folders = [], set()
    for name, pattern, folder in RECORDS:
        if only and name not in only:
            continue
        for src in sorted(case.glob(pattern)):
            dst = case / folder / ("%s-%s" % (prefix, src.name))
            stamp_file(src, dst, mark)
            moved.append((str(src.relative_to(case)), str(dst.relative_to(case))))
            folders.add(folder)
    for folder in sorted(folders):
        with open(case / folder / "README.txt", "a", encoding="utf-8") as f:
            f.write("Superseded %s by %s: %s. Files prefixed %s. No current tool reads this folder.\n"
                    % (mark["on"], mark["by"], mark["reason"], prefix))
    return moved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--reason", required=True)
    ap.add_argument("--by", required=True)
    ap.add_argument("--signature", help="<path>:<line> of a person's committed acceptance line")
    ap.add_argument("--only", nargs="*", help="limit to these records: %s"
                    % ", ".join(n for n, _p, _d in RECORDS))
    a = ap.parse_args(argv)
    import publish as P
    import source_store as store
    if not P.is_study(a.slug):
        raise SystemExit("%s is not a study issue (issue.json \"study\": true); a published "
                         "issue's records are corrected, not superseded" % a.slug)
    check_by(a.by, a.signature)
    moved = supersede(store.case_dir(a.slug), a.reason, a.by, only=a.only)
    for frm, to in moved:
        print("  superseded  %s  ->  %s" % (frm, to))
    print("\n  %d file(s) superseded\n" % len(moved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
