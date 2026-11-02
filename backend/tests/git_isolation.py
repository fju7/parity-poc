"""git for tests: only inside a temp repo, never with an inherited GIT_* variable.

tests/conftest.py already scrubs GIT_* for the session; this makes each helper
safe on its own as well, refuses a path inside the real repository, and sets
GIT_CEILING_DIRECTORIES so a missing temp repo is an error, not a walk up into
whatever repository encloses it.
"""
import os
import subprocess
from pathlib import Path

REAL_ROOT = Path(__file__).resolve().parents[2]


def tmp_git(repo):
    repo = Path(repo).resolve()
    assert repo != REAL_ROOT and REAL_ROOT not in repo.parents, (
        "test git must run in a temp repo, not inside %s" % REAL_ROOT)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CEILING_DIRECTORIES"] = str(repo.parent)

    def git(*a):
        return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, env=env)
    return git
