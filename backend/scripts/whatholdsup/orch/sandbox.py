"""A scratch copy of the repository for trial and replay runs (post-test item 2; docs/whu-orchestrator.md §4-5).

Every WHU module finds the repository from its own file path, so a run from a copy of backend/scripts writes
only into the copy: the case folder, the library record and the spend ledger are all the copy's. The copy holds
no backend/.env, so no model key exists inside it either (its .env
holds none). It is deleted at the end, by rule; nothing from it is
kept alongside results except the counts and hashes the caller chooses to write.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LIB = ROOT / "backend" / "data" / "whatholdsup" / "library"
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


class Sandbox:
    def __init__(self, slug: str, base: Path | None = None):
        self.slug = slug
        self.base = Path(base) if base else None
        self.root: Path | None = None

    def __enter__(self) -> "Sandbox":
        self.root = Path(tempfile.mkdtemp(prefix="whu-orch-", dir=str(self.base) if self.base else None))
        r = self.root
        # GIT HISTORY, READ-ONLY: the preflight reads earlier versions of the page (the first draft, the
        # protected sentences, the reading records). A local clone shares the repository's immutable objects
        # by hard link and has its own refs and index, so nothing done here reaches the real repository.
        import subprocess
        subprocess.run(["git", "clone", "-q", "--local", "--no-checkout", str(ROOT), str(r / ".clone")], check=True)
        (r / ".clone" / ".git").rename(r / ".git")
        (r / ".clone").rmdir()
        shutil.copytree(ROOT / "backend" / "scripts", r / "backend" / "scripts", ignore=SKIP)
        (r / "backend" / "venv").symlink_to(ROOT / "backend" / "venv")
        for name in ("spend", "signal", "verify"):
            src = ROOT / "backend" / "data" / name
            if src.exists():
                shutil.copytree(src, r / "backend" / "data" / name, ignore=SKIP)
        wd = ROOT / "backend" / "data" / "whatholdsup"
        for p in wd.iterdir():
            if p.name == "library":
                continue
            (shutil.copytree(p, r / "backend/data/whatholdsup" / p.name, ignore=SKIP) if p.is_dir()
             else (r / "backend/data/whatholdsup").mkdir(parents=True, exist_ok=True) or
             shutil.copy2(p, r / "backend/data/whatholdsup" / p.name))
        lib = r / "backend/data/whatholdsup/library"
        shutil.copytree(LIB, lib, ignore=shutil.ignore_patterns("docs", "__pycache__"))
        # A fresh issue has no library record until `acquire` writes one.
        rp = LIB / "issues" / ("%s.json" % self.slug)
        rec = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
        files = set()
        for s in (rec.get("sources") or {}).values():
            for x in [s] + list(s.get("superseded") or []):
                if isinstance(x, dict) and x.get("file"):
                    files.add(x["file"])
        for f in sorted(files):
            (lib / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LIB / f, lib / f)
        # Every case folder: the preflight's homepage row reads the published issues' records too.
        shutil.copytree(ROOT / "issues", r / "issues", ignore=SKIP)
        shutil.copytree(ROOT / "docs", r / "docs", ignore=SKIP)
        # The preflight compares the study's frozen files and the homepage's dates with the record.
        shutil.copytree(ROOT / "study", r / "study", ignore=SKIP)
        if (ROOT / "site" / "whatholdsup").exists():
            shutil.copytree(ROOT / "site" / "whatholdsup", r / "site" / "whatholdsup", ignore=SKIP)
        for f in ("CLAUDE.md",):
            if (ROOT / f).exists():
                shutil.copy2(ROOT / f, r / f)
        # An .env with no key in it: stages that read the file at start find it, and find no key.
        (r / "backend" / ".env").write_text("# scratch copy for a trial or replay run: no model key, by rule\n")
        assert "KEY" not in (r / "backend" / ".env").read_text()
        return self

    def case(self) -> Path:
        return next((self.root / "issues").glob("WHU-*-%s" % self.slug))

    def __exit__(self, *exc):
        if self.root and self.root.exists():
            shutil.rmtree(self.root)
        return False
