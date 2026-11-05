#!/usr/bin/env python3
"""Lean four-question test: verify, blind, sample, snapshot and cost the lean
answers by round 1's rules (lean_test_rule.md §2; validity_plan.md §10).

    prepare_lean.py verify | blind | sample | snapshot | routes [IDS] | ingest ARGS... | report | cost
                    [--questions WHU-Q1-01,WHU-Q1-03]   (default: every lean question whose page is committed)

Round 1's code runs unchanged (scripts/prepare_scoring.py, loaded as
quarterly/prepare_round1.py loads it), pointed at the lean run:

  SEED        R1SEED (round 1's freeze 5f4a928b..., as an integer): item ids and orders.
  SYSTEM      blinding runs prepare_scoring's own WHU branch (export_whu.py, then blind.py)
              on the lean page; its blinded files are then copied to the system name
              "WHU-lean", and the draw runs on that name, so the M1 draw is exactly
              random.Random("%d/%s/WHU-lean/M1" % (R1SEED, q)) (plan §10).
  KEYS        round 1's frozen keys (keys_manifest_round1.txt), checked before every stage.
  SCORING     ~/Projects/whu-study-private/scoring/lean/ (everything with answer, key or source text).
  LOG         next_phase/results/lean/ (hashes and counts only).

SNAPSHOTS. A cited address round 1's run already holds (the same address, or
the same work by DOI, PMID or PMCID: the identifier rule of round 1's snapshot
ruling) takes round 1's row and files, so the judges read the same text as for
full WHU. Every other address goes through snapshot.py and routes (a) to (c).
Route (d), Fred's Chrome, is not run here: such an address stops for a ruling.
No model is called.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = STUDY.parents[1]
SCRIPTS = STUDY / "scripts"
PRIV = Path.home() / "Projects" / "whu-study-private"
R1_RUN = PRIV / "scoring" / "quarterly" / "round1"
RUN_ROOT = PRIV / "scoring" / "lean"
ROOT_LINKS = RUN_ROOT / "root"
LOG = HERE / "results" / "lean"
R1SEED_HEX = "5f4a928b757d7f47c1ba8ed47600ced4a7a69f12"
ALL = {"WHU-Q1-01": "whu-lean-q1-01", "WHU-Q1-02": "whu-lean-q1-02r",
       "WHU-Q1-03": "whu-lean-q1-03", "WHU-Q1-04": "whu-lean-q1-04"}
SYSTEM = "WHU-lean"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(STUDY / "blinding"))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def questions(argv: list[str]) -> dict[str, str]:
    if "--questions" in argv:
        want = argv[argv.index("--questions") + 1].split(",")
        return {q: ALL[q] for q in want}
    import publish as P
    out = {}
    for q, slug in ALL.items():
        try:
            page = P.ROOT / P.issue_cfg(slug)["page"]
        except (Exception, SystemExit):
            continue
        rel = str(page.relative_to(REPO))
        if page.exists() and subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=REPO,
                                            capture_output=True, text=True).stdout.strip():
            out[q] = slug
    return out


def links() -> None:
    ROOT_LINKS.mkdir(parents=True, exist_ok=True)
    for name, target in (("keys", PRIV / "keys" / "quarterly" / "round1"),
                         ("answers", PRIV / "answers" / "quarterly" / "round1")):
        p = ROOT_LINKS / name
        if not p.exists():
            p.symlink_to(target)
        if p.resolve() != target.resolve():
            raise SystemExit("%s does not point at %s" % (p, target))


def prep(qs_map: dict[str, str], system: str):
    links()
    ps = _load("prepare_scoring_lean", SCRIPTS / "prepare_scoring.py")
    ps.FREEZE, ps.SEED = R1SEED_HEX, int(R1SEED_HEX, 16)
    ps.QUESTIONS = dict(qs_map)
    ps.PRIVATE, ps.SCORING, ps.LOG = ROOT_LINKS, RUN_ROOT, LOG
    ps.SYSTEMS = [system]
    ps.qs = lambda _a: list(qs_map)
    return ps


class A:
    pass


def do_verify(qs_map: dict[str, str]) -> int:
    ps = prep(qs_map, "WHU")
    bad, n = [], {"keys": 0, "key sources": 0, "lean pages": 0}
    for line in (STUDY / "quarterly" / "keys_manifest_round1.txt").read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        want, q, rel = line.split(None, 2)
        if q not in qs_map:
            continue
        p = ROOT_LINKS / "keys" / q / rel.strip()
        if not p.exists() or sha_file(p) != want:
            bad.append("key file %s/%s" % (q, rel))
        n["keys"] += 1
    for q in qs_map:
        k, b = ps.check_manifest(ROOT_LINKS / "keys" / q / "sources.sha256", ROOT_LINKS / "keys" / q)
        n["key sources"] += k
        bad += b
    lines = ["# Lean four-question test: lean WHU answers, sha256 manifest (prepare_lean.py verify)",
             "# sha256  question  page  (last commit touching the page)"]
    for q, slug in qs_map.items():
        page = ps.whu_page(slug)
        rel = str(page.relative_to(REPO))
        commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=REPO,
                                capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=REPO).returncode != 0
        if dirty or not commit:
            bad.append("lean page %s %s" % (q, "differs from its last commit" if dirty else "is not committed"))
        lines.append("%s  %s  %s  (commit %s)" % (sha_file(page), q, rel, commit))
        n["lean pages"] += 1
    for k, v in n.items():
        print("  %-12s %3d checked" % (k, v))
    if bad:
        print("  STOP: %s" % bad)
        return 2
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "whu_lean_answers_manifest.txt").write_text("\n".join(lines) + "\n")
    print("  all match")
    return 0


def do_blind(qs_map: dict[str, str]) -> int:
    ps = prep(qs_map, "WHU")
    lines = ["# Lean test: blinded answers, sha256 manifest (prepare_lean.py blind)",
             "# sha256  question  system  record  chars  sentences  samplable  with-marker  references  beyond"]
    rc = 0
    for q in qs_map:
        r = ps.blind_one(q, "WHU")
        d = RUN_ROOT / "blinded" / q
        for ext in ("blind.txt", "sentences.jsonl", "refs.json"):
            shutil.copyfile(d / ("whu." + ext), d / ("%s.%s" % (SYSTEM.lower(), ext)))
            (d / ("whu." + ext)).unlink()
        lines.append("%s  %s  %-8s  %-22s %6d  %4d  %4d  %4d  %3d  %d" % (
            r["blinded_sha256"], q, SYSTEM, r["record"], r["blinded_chars"], r["sentences"], r["samplable"],
            r["with_marker"], r["references"], r["markers_outside_reference_list"]))
        print(lines[-1][66:])
        rc |= 1 if r["markers_outside_reference_list"] else 0
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "blinded_manifest.txt").write_text("\n".join(lines) + "\n")
    return rc


def seed_from_round1(ps) -> tuple[int, int]:
    """Copy round 1's manifest row and stored files for every cited address round 1
    holds: the same address (its row, held or not), or the same work by DOI, PMID
    or PMCID (a row that holds text), re-keyed to the cited address. As
    results/perplexity/prepare_perplexity.py seed_from_study does."""
    pp = _load("prepare_perplexity_lean", STUDY / "results" / "perplexity" / "prepare_perplexity.py")
    run = RUN_ROOT / "m1"
    items = json.loads((run / "items.json").read_text(encoding="utf-8"))
    urls = {c["url"] for it in items for c in it["citations"] if c.get("url")}
    by_url, by_id = {}, {}
    for r in json.loads((R1_RUN / "m1" / "sources" / "manifest.json").read_text()):
        if r.get("reused_from"):
            continue
        by_url.setdefault(r["url"], r)
        i = pp.ident(r["url"])
        if i and r["extent"] != "unreachable":
            by_id.setdefault(i, r)
    mf = run / "sources" / "manifest.json"
    mine = json.loads(mf.read_text()) if mf.exists() else []
    have = {r["url"] for r in mine}
    copied = 0
    (run / "sources").mkdir(parents=True, exist_ok=True)
    for u in sorted(urls - have):
        how, r = ("url", by_url[u]) if u in by_url else (None, None)
        if r is None and pp.ident(u) in by_id:
            r, how = by_id[pp.ident(u)], pp.ident(u).split(":")[0]
        if r is None:
            continue
        for ext in (".raw", ".txt"):
            src = R1_RUN / "m1" / "sources" / (r["source_id"] + ext)
            if src.exists():
                shutil.copy2(src, run / "sources" / src.name)
        mine.append(dict(r, url=u, reused_from={"run": "scoring/quarterly/round1", "matched_by": how, "url": r["url"]}))
        copied += 1
    mf.write_text(json.dumps(mine, indent=1, ensure_ascii=False), encoding="utf-8")
    return copied, len(have)


def main() -> int:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""
    qs_map = questions(argv)
    print("  lean questions: %s" % (", ".join(qs_map) or "none"))
    if not qs_map and cmd not in ("routes", "ingest"):
        return 2
    if cmd == "verify":
        return do_verify(qs_map)
    if cmd in ("blind", "sample", "snapshot", "report", "cost"):
        rc = do_verify(qs_map)
        if rc:
            return rc
        if cmd == "blind":
            return do_blind(qs_map)
        ps = prep(qs_map, SYSTEM)
        if cmd == "sample":
            return ps.do_sample(A())
        if cmd == "snapshot":
            c, h = seed_from_round1(ps)
            print("  snapshots: %d taken from round 1's run, %d already here" % (c, h))
            return ps.do_snapshot(A())
        return {"report": ps.snapshot_report, "cost": lambda: ps.do_cost(A())}[cmd]()
    if cmd == "routes":
        rs = _load("retrieve_sources_lean", SCRIPTS / "retrieve_sources.py")
        rs.RUN = RUN_ROOT / "m1"
        rows = json.loads((rs.RUN / "sources" / "manifest.json").read_text())
        ids = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else \
            ",".join(r["source_id"] for r in rows if r["extent"] == "unreachable")
        if not ids:
            print("  no unreachable source")
            return 0
        sys.argv = ["retrieve_sources.py", "--only", ids]
        return rs.main()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
