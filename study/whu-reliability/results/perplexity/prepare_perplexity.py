#!/usr/bin/env python3
"""Perplexity add-on (exploratory, outside H1 and H2): blind, sample and snapshot
Perplexity's WHU-S01 to WHU-S04 answers by the S01-S04 rules.

    prepare_perplexity.py blind | sample | snapshot | routes | ingest ARGS... | report

Plan: study/whu-reliability/perplexity_plan.md (frozen at 078ab4e).

The study's own code runs unchanged. scripts/prepare_scoring.py,
scripts/retrieve_sources.py and scripts/ingest_operator.py are loaded and their
path constants pointed at Perplexity's own private run directory,
~/Projects/whu-study-private/scoring/perplexity/ (SCORING; m1/ is RUN), and
at study/whu-reliability/results/perplexity/ (LOG: hashes and counts only).
So the study's existing items, samples, snapshots, replies and manifests are
never written. prepare_scoring.SYSTEMS is ["Perplexity"], so the M1 draw is
random.Random("<SEED>/<question>/Perplexity/M1") and item ids are
opaque("M1", "<question>/Perplexity/<idx>"), as for every other answer.

The answer is taken from the capture by blinding/adapt.perplexity_sources
(the report up to its References; [^n] written [n]; entry n of the
References is [n]), then blind.py as for every tool.

SNAPSHOTS. Before any fetch, every cited address that already has a row in
the study's snapshot manifest (scoring/m1/sources/manifest.json) gets that
row and its stored files, unchanged: one snapshot per address, the same
evidence for every system. Only addresses with no row go through
snapshot.py ("snapshot"), then routes (a) to (c) ("routes", the new
unreachable rows only), then route (d) in Fred's Chrome ("ingest", via
ingest_operator.py's size and sha256 check). No model is called.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
SCRIPTS = STUDY / "scripts"
PRIVATE = Path.home() / "Projects" / "whu-study-private"
MAIN_RUN = PRIVATE / "scoring" / "m1"
PPLX = PRIVATE / "scoring" / "perplexity"
RUN = PPLX / "m1"
QUESTIONS = ["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"]
# PPLX_QUESTIONS narrows a run while an answer is not yet captured; the draw for an
# answer depends on its own seed string only, so adding one later changes no other.
QUESTIONS = [q for q in QUESTIONS if q in os.environ.get("PPLX_QUESTIONS", ",".join(QUESTIONS)).split(",")]
SYSTEM = "Perplexity"
sys.path.insert(0, str(SCRIPTS))          # as when prepare_scoring.py runs as a script (snapshot, find_access)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def prep():
    ps = _load("prepare_scoring_pplx", SCRIPTS / "prepare_scoring.py")
    ps.SCORING, ps.LOG = PPLX, HERE
    ps.SYSTEMS = [SYSTEM]
    ps.TOOL_FILE = dict(ps.TOOL_FILE, **{SYSTEM: "perplexity"})
    original = ps.tool_answer

    def tool_answer(q, system):
        if system != SYSTEM:
            return original(q, system)
        import adapt
        rec = PRIVATE / "answers" / q / "perplexity.md"
        body, cited = adapt.perplexity_sources(rec.read_text(encoding="utf-8"))
        return body, cited, rec.name
    ps.tool_answer = tool_answer
    return ps


class A:
    questions = ",".join(QUESTIONS)


def do_blind() -> int:
    ps = prep()
    rows = [ps.blind_one(q, SYSTEM) for q in QUESTIONS]
    lines = ["# Perplexity add-on: blinded answers, sha256 manifest (prepare_perplexity.py blind)",
             "# The blinded texts are held at ~/Projects/whu-study-private/scoring/perplexity/blinded/<question>/perplexity.blind.txt.",
             "#", "# sha256  question  system  record  chars  sentences  samplable  with-marker  references  markers-beyond-list"]
    for r in rows:
        lines.append("%s  %s  %s  %s  %6d  %4d  %4d  %4d  %3d  %d" % (
            r["blinded_sha256"], r["question"], r["system"], r["record"], r["blinded_chars"], r["sentences"],
            r["samplable"], r["with_marker"], r["references"], r["markers_outside_reference_list"]))
        print(lines[-1][66:])
    (HERE / "blinded_manifest.txt").write_text("\n".join(lines) + "\n")
    return 1 if any(r["markers_outside_reference_list"] for r in rows) else 0


def do_sample() -> int:
    return prep().do_sample(A())


# Earlier snapshot runs whose rows may be reused (advisor's ruling, 2026-10-27:
# "Reuse existing snapshots wherever the DOI, PMID or URL matches"): the study's
# own, then the set-aside first Perplexity run's (personalisation left on).
REUSE_RUNS = [MAIN_RUN, PRIVATE / "scoring" / "perplexity_personalised_set_aside" / "m1"]
DOI = re.compile(r"\b(10\.\d{4,9}/[^\s?#&]+)", re.I)
PMID = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)|ncbi\.nlm\.nih\.gov/pubmed/(\d+)")
PMCID = re.compile(r"(PMC\d+)", re.I)


def ident(url: str) -> str | None:
    """A work's identifier from its address alone: DOI, PMID or PMCID."""
    m = DOI.search(url)
    if m:
        return "doi:" + m.group(1).rstrip(".,;)/").lower()
    m = PMID.search(url)
    if m:
        return "pmid:" + (m.group(1) or m.group(2))
    m = PMCID.search(url)
    return "pmcid:" + m.group(1).upper() if m else None


def seed_from_study() -> tuple[int, int]:
    """Copy an earlier run's manifest row and stored files for every cited
    address that one already covers; return (copied, already here). The same
    address: its row, held or not (its retrieval record is kept, as in Stage
    1). Another address of the same work (DOI, PMID or PMCID): only a row
    that holds text, re-keyed to the cited address; an unreachable work at a
    new address is fetched like any other."""
    items = json.loads((RUN / "items.json").read_text(encoding="utf-8"))
    urls = {c["url"] for it in items for c in it["citations"] if c.get("url")}
    by_url, by_id = {}, {}
    for run in REUSE_RUNS:
        mfp = run / "sources" / "manifest.json"
        for r in json.loads(mfp.read_text()) if mfp.exists() else []:
            if r.get("reused_from"):
                continue                                  # a copy: take the original
            by_url.setdefault(r["url"], (run, r))
            i = ident(r["url"])
            if i and r["extent"] != "unreachable":
                by_id.setdefault(i, (run, r))
    mf = RUN / "sources" / "manifest.json"
    mine = json.loads(mf.read_text()) if mf.exists() else []
    have = {r["url"] for r in mine}
    copied = 0
    (RUN / "sources").mkdir(parents=True, exist_ok=True)
    for u in sorted(urls - have):
        how = "url" if u in by_url else None
        hit = by_url.get(u)
        if not hit and ident(u) in by_id:
            hit, how = by_id[ident(u)], ident(u).split(":")[0]
        if not hit:
            continue
        run, r = hit
        for ext in (".raw", ".txt"):
            src = run / "sources" / (r["source_id"] + ext)
            if src.exists():
                shutil.copy2(src, RUN / "sources" / src.name)
        mine.append(dict(r, url=u, reused_from={"run": str(run.relative_to(PRIVATE)), "matched_by": how,
                                                "url": r["url"]}))
        copied += 1
    mf.write_text(json.dumps(mine, indent=1, ensure_ascii=False), encoding="utf-8")
    return copied, len(have)


def do_snapshot() -> int:
    copied, before = seed_from_study()
    print("  reused from earlier snapshot runs (URL, DOI or PMID): %d address(es) (%d already here)" % (copied, before))
    return prep().do_snapshot(A())


def do_routes(only: str | None) -> int:
    rs = _load("retrieve_sources_pplx", SCRIPTS / "retrieve_sources.py")
    rs.RUN = RUN
    rows = json.loads((RUN / "sources" / "manifest.json").read_text())
    new = [r["source_id"] for r in rows if r["extent"] == "unreachable" and not r.get("reused_from")]
    ids = only or ",".join(new)
    if not ids:
        print("  no new unreachable source")
        return 0
    sys.argv = ["retrieve_sources.py", "--only", ids]
    return rs.main()


def do_ingest(args: list[str]) -> int:
    io = _load("ingest_operator_pplx", SCRIPTS / "ingest_operator.py")
    io.RUN = RUN
    sys.argv = ["ingest_operator.py", "--incoming", str(RUN / "operator_incoming_ext")] + args
    return io.main()


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "blind":
        return do_blind()
    if cmd == "sample":
        return do_sample()
    if cmd == "snapshot":
        return do_snapshot()
    if cmd == "routes":
        return do_routes(sys.argv[2] if len(sys.argv) > 2 else None)
    if cmd == "ingest":
        return do_ingest(sys.argv[2:])
    if cmd == "report":
        return prep().snapshot_report()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
