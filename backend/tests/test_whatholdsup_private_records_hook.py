"""The pre-commit hook refuses a staged rulings/omissions.jsonl or retrieval.jsonl (advisor's ruling 5 on the P187
fork, 2026-11-27): the repository is public and those hold source quotations / private run records. $0, offline."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "backend" / "scripts" / "whatholdsup" / "hooks" / "pre-commit"


def _repo(tmp_path):
    if not shutil.which("git"):
        pytest.skip("git not installed")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, env=env)
    hooks = tmp_path / ".git" / "hooks"
    shutil.copy(HOOK, hooks / "pre-commit")
    (hooks / "pre-commit").chmod(0o755)
    return env


def _commit(tmp_path, env, rel, text="x\n"):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    subprocess.run(["git", "add", "-f", rel], cwd=tmp_path, check=True, env=env)
    return subprocess.run(["git", "commit", "-q", "-m", "m"], cwd=tmp_path, env=env, capture_output=True, text=True)


@pytest.mark.parametrize("rel", ["issues/WHU-X/rulings/omissions.jsonl", "issues/WHU-X/audit/20261127T000000Z/retrieval.jsonl"])
def test_a_private_record_is_refused(tmp_path, rel):
    env = _repo(tmp_path)
    r = _commit(tmp_path, env, rel)
    assert r.returncode != 0 and "COMMIT REFUSED" in (r.stdout + r.stderr) and rel in (r.stdout + r.stderr)


def test_an_ordinary_file_and_a_removal_are_allowed(tmp_path):
    env = _repo(tmp_path)
    assert _commit(tmp_path, env, "notes/readme.txt").returncode == 0
    assert _commit(tmp_path, env, "issues/WHU-X/omissions.json").returncode == 0      # the public record is fine


def test_the_installed_hook_is_the_tracked_one():
    installed = ROOT / ".git" / "hooks" / "pre-commit"
    if not installed.exists():
        pytest.skip("no installed hook (a checkout without one)")
    assert installed.read_bytes() == HOOK.read_bytes()


def test_omissions_jsonl_is_ignored_and_none_is_tracked():
    assert "issues/*/rulings/omissions.jsonl" in (ROOT / ".gitignore").read_text()
    out = subprocess.run(["git", "ls-files", "issues/*/rulings/omissions.jsonl"], cwd=ROOT, capture_output=True,
                         text=True).stdout.split()
    assert out == []
