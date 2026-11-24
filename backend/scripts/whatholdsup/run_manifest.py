"""Run provenance manifests (advisor's ruling after the lean-page check, 2026-11-24).

The lean test's bindings.json files are excluded by their folders' .gitignore and the library is not in git, so a
scored run's evidence lived only on one machine, in its final state. Now, for every scored or to-be-scored run (the
lean test's Q1-01c, Q1-02b, Q1-03b, Q1-04c; every orchestrated run from 2026-11-24):

  * a MANIFEST is committed in the run's folder: the bindings file, the library's issue index and every stored
    document of the issue (path, sha256, size, mtime; a document the holdings record blocks is listed with its
    holding, "not used") -- hashes and paths only, never text;
  * those FILES are copied into the private study folder (~/Projects/whu-study-private/run_provenance/<slug>/),
    never into the public repo, since held documents contain publisher text; every copy is re-hashed;
  * `check()` (tests/test_whu_run_manifests.py) fails if a run reported as a result has no committed manifest.

    run_manifest.py build SLUG      write the manifest and the private copy
    run_manifest.py check           list result runs without a committed manifest (exit 1 if any)
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

MANIFEST = "provenance_manifest.json"                  # lean runs: in the run folder
ORCH_MANIFEST = "orchestrator/provenance_manifest.json"  # orchestrated runs: the orchestrator's own folder
# The lean test's runs reported as results (scored) or to be scored (Q1-04c).
LEAN_RESULT_RUNS = ("whu-lean-q1-01c", "whu-lean-q1-02b", "whu-lean-q1-03b", "whu-lean-q1-04c")
# The bindings version in place when each scored run's M1 / M2 judging and analysis ran (advisor's request
# 2026-11-24; established from timestamps and commits, deviations.md P076). Judging: ledger issue
# whu-reliability-judging-lean, 2026-11-06T16:11:30Z (first M2 row) .. 16:45:59Z (last M1 row); analysis committed
# e390fd1 at 16:47:06Z. Q1-04c was not scored.
_JUDGED = ("judging 2026-11-06T16:11:30Z-16:45:59Z (ledger whu-reliability-judging-lean), analysis e390fd1 "
           "16:47:06Z; the file was last written %s, before judging began, and not written since")
SCORED_BINDINGS = {
    "whu-lean-q1-01c": {"sha256": "fbf174d2ea83251b024868e2e0063dc3220cd5e7c72a3ddd25b57c0a0c0cde1c",
                        "basis": _JUDGED % "2026-11-05T22:46:51Z (= the 22:53:30Z archive's sha256)"},
    "whu-lean-q1-02b": {"sha256": "9da2a2bf98e38edf1b835e39c4e8b29037b7b8b1b6d158a1e7617bd551d61823",
                        "basis": _JUDGED % "2026-11-06T00:36:08Z (= the 00:40:14Z archive's sha256)"},
    "whu-lean-q1-03b": {"sha256": "a8a8f524ad94fd0269db8e66c6bc0993459fd7a1991afa157ade295ba0c77f13",
                        "basis": _JUDGED % ("2026-11-06T16:07:11Z, by the binding fix (code 9863fb2 16:00:33Z; "
                                            "de7fc35 16:08:57Z \"Q1-03b Ready again after the binding fix\"); "
                                            "the 11:54:14Z archive (25a196ff...) predates the fix and is not the "
                                            "scored state")},
}


def private_root() -> Path:
    return Path(os.environ.get("WHU_PRIVATE_ROOT") or (Path.home() / "Projects" / "whu-study-private"))


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _entry(role: str, p: Path, label: str, **extra) -> dict:
    st = p.stat()
    return dict({"role": role, "path": label, "sha256": _sha(p), "size": st.st_size,
                 "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")},
                **extra)


def manifest_path(case: Path) -> Path:
    return case / (ORCH_MANIFEST if (case / "orchestrator").is_dir() else MANIFEST)


def _inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def build(slug: str, copy: bool = True) -> dict:
    """Write the run's manifest (returned) and, with COPY, its files into the private study folder."""
    import holdings as HD
    import source_store as store
    case = store.case_dir(slug)
    lib = Path(store.LIB)
    files = []
    b = case / "bindings.json"
    if b.exists():
        files.append((_entry("bindings", b, str(b.relative_to(ROOT))), b))
    ix = Path(store.issue_index_path(slug))
    if ix.exists():
        files.append((_entry("library_index", ix, "library:" + str(ix.relative_to(lib))), ix))
    rec = HD.record(slug) if (case / "sources.json").exists() else {}
    for sid, row in sorted(store.library_held(slug).items()):
        holding = (rec.get(sid) or {}).get("holding", HD.HELD)
        for r in [row] + list(row.get("also_held") or []):
            f = lib / (r.get("file") or "")
            if not r.get("file") or not f.exists():
                files.append(({"role": "document", "source_id": sid, "path": "library:" + str(r.get("file")),
                               "missing": True, "holding": holding}, None))
                continue
            e = _entry("document", f, "library:" + str(f.relative_to(lib)), source_id=sid, holding=holding,
                       used=holding == HD.HELD, recorded_sha256=r.get("sha256"))
            files.append((e, f))
    dest = private_root() / "run_provenance" / slug
    if _inside(dest, ROOT):
        raise SystemExit("refusing: the private copy %s is inside the public repo" % dest)
    man = {"_what_this_is": ("Run provenance manifest: the bindings file and every stored document this run's "
                             "issue holds, by hash (advisor's ruling 2026-11-24). The files themselves are copied "
                             "to the private study folder, never to this repo (held documents carry publisher "
                             "text)."),
           "slug": slug, "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "library_root": str(lib.relative_to(ROOT)) if _inside(lib, ROOT) else str(lib),
           "private_copy": "~/" + str(dest.relative_to(Path.home())) if _inside(dest, Path.home()) else str(dest),
           "files": [e for e, _ in files]}
    sc = SCORED_BINDINGS.get(slug)
    if sc:
        for e, _ in files:
            if e["role"] == "bindings":
                e["scored"] = e["sha256"] == sc["sha256"]
        man["scored_bindings"] = dict(sc, status="scored")
    arch = archived_bindings(case)
    if arch:
        cur = next((e["sha256"] for e, _ in files if e["role"] == "bindings"), None)
        man["bindings_at_archive"] = dict(arch, matches_current=arch["sha256"] == cur)
    if copy:
        for e, src in files:
            if src is None:
                continue
            rel = e["path"].replace("library:", "library/", 1)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
            if _sha(out) != e["sha256"]:
                raise SystemExit("private copy of %s does not match its hash" % e["path"])
        man["copied"] = sum(1 for _e, src in files if src is not None)
    p = manifest_path(case)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return man


def archived_bindings(case: Path) -> dict | None:
    """The bindings.json sha256 the run folder's committed private_manifest.txt (the lean test's archive) records,
    with the archive folder it names; None if there is none."""
    p = case / "private_manifest.txt"
    if not p.exists():
        return None
    lines = p.read_text(encoding="utf-8").splitlines()
    where = next((ln.split("archived to ", 1)[1].split(" (")[0] for ln in lines if "archived to " in ln), None)
    for ln in lines:
        parts = ln.split()
        if len(parts) == 2 and parts[1].endswith("/bindings.json"):
            return {"sha256": parts[0], "archive": where, "recorded_in": str(p.relative_to(ROOT))}
    return None


def result_runs(root: Path = ROOT) -> list[tuple[str, Path]]:
    """(slug, case) of every run reported as a result: the lean test's four, and every orchestrated run whose
    run_paid.json says Ready."""
    out = []
    for issue in sorted((root / "issues").glob("*/issue.json")):
        case = issue.parent
        try:
            slug = json.loads(issue.read_text(encoding="utf-8")).get("slug")
        except ValueError:
            continue
        rp = case / "orchestrator" / "run_paid.json"
        ready = False
        if rp.exists():
            try:
                ready = json.loads(rp.read_text(encoding="utf-8")).get("result") == "Ready."
            except ValueError:
                ready = False
        if slug in LEAN_RESULT_RUNS or ready:
            out.append((slug, case))
    return out


def _committed(p: Path, root: Path) -> bool:
    """Tracked by git with no change since it was staged: committed, or staged in the commit being made (the
    pre-commit hook runs this check before that commit exists)."""
    rel = str(p.relative_to(root))
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True).returncode
    clean = subprocess.run(["git", "diff", "--quiet", "--", rel], cwd=root).returncode
    return tracked == 0 and clean == 0


def check(root: Path = ROOT) -> list[str]:
    """Each run reported as a result that has no committed manifest (or one with no documents)."""
    bad = []
    for slug, case in result_runs(root):
        p = manifest_path(case)
        if not p.exists():
            bad.append("%s: no manifest (%s)" % (slug, p.relative_to(root)))
        elif not _committed(p, root):
            bad.append("%s: manifest not committed (%s)" % (slug, p.relative_to(root)))
        else:
            man = json.loads(p.read_text(encoding="utf-8"))
            if not [f for f in man.get("files") or [] if f.get("role") == "document" and not f.get("missing")]:
                bad.append("%s: manifest lists no held document" % slug)
    return bad


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("slug")
    sub.add_parser("check")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        man = build(a.slug)
        print(json.dumps({"slug": a.slug, "files": len(man["files"]), "copied": man.get("copied"),
                          "private_copy": man["private_copy"]}, indent=1))
        return 0
    bad = check()
    for x in bad:
        print("  MISSING  " + x)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
