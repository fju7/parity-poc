"""Tests never run git against the real repository (2026-11-02).

Run inside the whatholdsup pre-commit hook, git's exported GIT_DIR /
GIT_INDEX_FILE sent the tests' `git -C <tmp>` commits into the real repo.
tests/conftest.py scrubs GIT_* for the session and guards the real repo;
tests/git_isolation.tmp_git runs git only in a temp repo with a clean env.
"""
import os
import subprocess

import pytest

from tests import conftest
from tests.git_isolation import REAL_ROOT, tmp_git


def test_no_git_variable_reaches_a_test():
    assert not [k for k in os.environ if k.startswith("GIT_")]


def test_tmp_git_refuses_the_real_repository():
    with pytest.raises(AssertionError):
        tmp_git(REAL_ROOT)
    with pytest.raises(AssertionError):
        tmp_git(REAL_ROOT / "backend")


def test_tmp_git_ignores_an_exported_git_dir(tmp_path, monkeypatch):
    decoy, repo = tmp_path / "decoy", tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(decoy)], check=True)
    monkeypatch.setenv("GIT_DIR", str(decoy / ".git"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(decoy / ".git" / "index"))
    repo.mkdir()
    git = tmp_git(repo)
    git("init", "-q")
    git("config", "user.name", "t")
    git("config", "user.email", "t@e.com")
    (repo / "a.md").write_text("a\n")
    git("add", "a.md")
    git("commit", "-q", "-m", "in the temp repo")
    assert (repo / ".git" / "config").read_text().count("t@e.com") == 1
    assert "t@e.com" not in (decoy / ".git" / "config").read_text()
    assert not (decoy / ".git" / "logs" / "HEAD").exists()


def test_tmp_git_does_not_walk_up_into_an_enclosing_repository(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    inner = tmp_path / "not-a-repo"
    inner.mkdir()
    with pytest.raises(subprocess.CalledProcessError):
        tmp_git(inner)("status")


def test_the_session_guard_sees_a_stray_commit(tmp_path, monkeypatch):
    git = tmp_git(tmp_path)
    git("init", "-q")
    git("config", "user.name", "t")
    git("config", "user.email", "t@e.com")
    git("commit", "-q", "--allow-empty", "-m", "one")
    monkeypatch.setattr(conftest, "REPO_ROOT", tmp_path)
    before = conftest.real_repo_state()
    git("commit", "-q", "--allow-empty", "-m", "stray")
    assert conftest.real_repo_state() != before
    before = conftest.real_repo_state()
    git("config", "user.name", "someone else")
    assert conftest.real_repo_state() != before
