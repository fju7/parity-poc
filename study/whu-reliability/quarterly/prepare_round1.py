#!/usr/bin/env python3
"""WHU quarterly round 1: verify, blind, sample, snapshot and cost the round's
answers by the study's rules (round1_protocol.md §5, frozen at 5f4a928).

    prepare_round1.py verify | blind | sample | snapshot | routes [IDS] | ingest ARGS... | report | cost

The study's code runs unchanged, as the re-runs and the Perplexity add-on ran
it (results/perplexity/prepare_perplexity.py): scripts/prepare_scoring.py,
scripts/retrieve_sources.py and scripts/ingest_operator.py are loaded and
their constants pointed at round 1:

  FREEZE / SEED   the round's freeze commit 5f4a928b..., read as a hexadecimal
                  integer (protocol §1, §5): the M1 draw is
                  random.Random("<SEED>/<question>/<system>/M1"), item ids
                  opaque("M1", ...) and the M1/M2 orders with this SEED.
  QUESTIONS       WHU-Q1-01..04 -> whu-quarterly-r1-01..04 (the WHU issues).
  SYSTEMS         WHU, Claude, ChatGPT, Gemini, Perplexity, per question: the
                  answers that exist. Gemini has no WHU-Q1-04 answer (two
                  technical failures; answers manifest). prepare_scoring loops
                  `for q in qs(a): for s in SYSTEMS`, so qs() is replaced by a
                  generator that sets SYSTEMS for each question as it yields
                  it and restores the full list when done. Each answer's draw
                  depends on its own seed string only, so no other answer's
                  draw changes.
  PRIVATE         a run root whose answers/ and keys/ are links to
                  answers/quarterly/round1/ and keys/quarterly/round1/.
  SCORING         ~/Projects/whu-study-private/scoring/quarterly/round1/
                  (blinded/, m1/, m2/): everything with answer, key or source
                  text.
  LOG             quarterly/round1_scoring/ in the repository: hashes and
                  counts only.

Tool answers are taken from their capture files by blinding/adapt.py: Claude
by claude_sources_r1 (deviations 2026-10-29, ruling 2); Perplexity WHU-Q1-03
and WHU-Q1-04 by the study's perplexity_sources (the re-captured Deep research
reports) and WHU-Q1-01 and WHU-Q1-02 by perplexity_footnotes (the inline
answers, no report card produced; ruling 1 and the ruling of 2026-10-29);
ChatGPT by chatgpt_bracketed, Gemini by report_section and works_cited, as in
the study. WHU by prepare_scoring's own
WHU branch (export_whu.py, then blind.py).

VERIFY replaces prepare_scoring.verify, whose manifests are the study's: the
15 tool answers against answers_manifest_round1.txt, every key file against
keys_manifest_round1.txt, every key source against its sources.sha256, and
each WHU page against whu_answers_manifest_round1.txt and clean against git.
Any mismatch stops with exit 2.

SNAPSHOTS. snapshot.py on every distinct cited address, then routes (a) to (c)
("routes"), then route (d) in Fred's Chrome ("ingest", via ingest_operator.py's
size and sha256 check). Nothing is reused from earlier runs: the protocol asks
for one snapshot per address for this round. No model is called.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
SCRIPTS = STUDY / "scripts"
PRIV = Path.home() / "Projects" / "whu-study-private"
RUN_ROOT = PRIV / "scoring" / "quarterly" / "round1"
ROOT_LINKS = RUN_ROOT / "root"                       # answers -> round 1's answers, keys -> round 1's keys
LOG = HERE / "round1_scoring"
FREEZE = "5f4a928b757d7f47c1ba8ed47600ced4a7a69f12"
QUESTIONS = {"WHU-Q1-01": "whu-quarterly-r1-01", "WHU-Q1-02": "whu-quarterly-r1-02",
             "WHU-Q1-03": "whu-quarterly-r1-03", "WHU-Q1-04": "whu-quarterly-r1-04"}
ALL_SYSTEMS = ["WHU", "Claude", "ChatGPT", "Gemini", "Perplexity"]
NO_ANSWER = {("WHU-Q1-04", "Gemini")}                 # answers_manifest_round1.txt: no result
PPLX_REPORT = {"WHU-Q1-03", "WHU-Q1-04"}               # Deep research report card; Q1-01/Q1-02 answered inline
sys.path.insert(0, str(SCRIPTS))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def systems_for(q: str) -> list[str]:
    return [s for s in ALL_SYSTEMS if (q, s) not in NO_ANSWER]


def links() -> None:
    ROOT_LINKS.mkdir(parents=True, exist_ok=True)
    for name, target in (("answers", PRIV / "answers" / "quarterly" / "round1"),
                         ("keys", PRIV / "keys" / "quarterly" / "round1")):
        p = ROOT_LINKS / name
        if not p.exists():
            p.symlink_to(target)
        if p.resolve() != target.resolve():
            raise SystemExit("%s does not point at %s" % (p, target))


def prep():
    links()
    ps = _load("prepare_scoring_r1", SCRIPTS / "prepare_scoring.py")
    ps.FREEZE, ps.SEED = FREEZE, int(FREEZE, 16)
    ps.QUESTIONS = dict(QUESTIONS)
    ps.PRIVATE, ps.SCORING, ps.LOG = ROOT_LINKS, RUN_ROOT, LOG
    ps.SYSTEMS = list(ALL_SYSTEMS)
    ps.TOOL_FILE = dict(ps.TOOL_FILE, Perplexity="perplexity")

    def qs(_a):
        try:
            for q in QUESTIONS:
                ps.SYSTEMS = systems_for(q)
                yield q
        finally:
            ps.SYSTEMS = list(ALL_SYSTEMS)
    ps.qs = qs

    def tool_answer(q, system):
        import adapt
        rec = ROOT_LINKS / "answers" / q / (ps.TOOL_FILE[system] + ".md")
        md = rec.read_text(encoding="utf-8")
        if system == "Claude":
            body, cited = adapt.claude_sources_r1(md)
            return body, cited, rec.name
        if system == "Perplexity":
            body, cited = (adapt.perplexity_sources if q in PPLX_REPORT else adapt.perplexity_footnotes)(md)
            return body, cited, rec.name
        if system == "ChatGPT":
            return adapt.chatgpt_bracketed(md), None, rec.name
        if system == "Gemini":
            return adapt.report_section(md), adapt.works_cited(md), rec.name
        raise SystemExit("no tool %s" % system)
    ps.tool_answer = tool_answer
    return ps


class A:
    questions = ",".join(QUESTIONS)


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def do_verify() -> int:
    ps = prep()
    bad, n = [], {"answers": 0, "keys": 0, "key sources": 0, "WHU pages": 0}
    for line in (HERE / "answers_manifest_round1.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip() or line.startswith("no result"):
            continue
        want, rel = line.split(None, 1)
        p = ROOT_LINKS / "answers" / rel.strip()
        if not p.exists() or sha_file(p) != want:
            bad.append("answer %s" % rel)
        n["answers"] += 1
    for line in (HERE / "keys_manifest_round1.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        want, q, rel = line.split(None, 2)
        p = ROOT_LINKS / "keys" / q / rel.strip()
        if not p.exists() or sha_file(p) != want:
            bad.append("key file %s/%s" % (q, rel))
        n["keys"] += 1
    for q in QUESTIONS:
        k, b = ps.check_manifest(ROOT_LINKS / "keys" / q / "sources.sha256", ROOT_LINKS / "keys" / q)
        n["key sources"] += k; bad += b
    for line in (HERE / "whu_answers_manifest_round1.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        want, q, rel = line.split()[:3]
        page = REPO / rel
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO).returncode != 0
        if dirty or sha_file(page) != want or page != ps.whu_page(QUESTIONS[q]):
            bad.append("WHU page %s" % q)
        n["WHU pages"] += 1
    for k, v in n.items():
        print("  %-12s %3d checked" % (k, v))
    if bad or n["answers"] != 15 or n["WHU pages"] != 4:
        print("  STOP: %s" % (bad or "wrong counts"))
        return 2
    print("  all match")
    return 0


def do_blind() -> int:
    ps = prep()
    rows = [ps.blind_one(q, s) for q in ps.qs(A()) for s in ps.SYSTEMS]
    lines = ["# WHU quarterly round 1: blinded answers, sha256 manifest (prepare_round1.py blind)",
             "# The blinded texts are held at ~/Projects/whu-study-private/scoring/quarterly/round1/blinded/<question>/<system>.blind.txt.",
             "#", "# sha256  question  system  record  chars  sentences  samplable  with-marker  references  markers-beyond-list"]
    for r in rows:
        lines.append("%s  %s  %-10s  %-14s %6d  %4d  %4d  %4d  %3d  %d" % (
            r["blinded_sha256"], r["question"], r["system"], r["record"], r["blinded_chars"], r["sentences"],
            r["samplable"], r["with_marker"], r["references"], r["markers_outside_reference_list"]))
        print(lines[-1][66:])
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "blinded_manifest.txt").write_text("\n".join(lines) + "\n")
    return 1 if any(r["markers_outside_reference_list"] for r in rows) else 0


def do_routes(only: str | None) -> int:
    rs = _load("retrieve_sources_r1", SCRIPTS / "retrieve_sources.py")
    rs.RUN = RUN_ROOT / "m1"
    rows = json.loads((rs.RUN / "sources" / "manifest.json").read_text())
    ids = only or ",".join(r["source_id"] for r in rows if r["extent"] == "unreachable")
    if not ids:
        print("  no unreachable source")
        return 0
    sys.argv = ["retrieve_sources.py", "--only", ids]
    return rs.main()


def do_ingest(args: list[str]) -> int:
    io = _load("ingest_operator_r1", SCRIPTS / "ingest_operator.py")
    io.RUN = RUN_ROOT / "m1"
    sys.argv = ["ingest_operator.py", "--incoming", str(RUN_ROOT / "m1" / "operator_incoming")] + args
    return io.main()


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "verify":
        return do_verify()
    if cmd in ("blind", "sample", "snapshot", "report", "cost"):
        rc = do_verify()
        if rc:
            return rc
        ps = prep()
        return {"blind": do_blind, "sample": lambda: ps.do_sample(A()), "snapshot": lambda: ps.do_snapshot(A()),
                "report": ps.snapshot_report, "cost": lambda: ps.do_cost(A())}[cmd]()
    if cmd == "routes":
        return do_routes(sys.argv[2] if len(sys.argv) > 2 else None)
    if cmd == "ingest":
        return do_ingest(sys.argv[2:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
