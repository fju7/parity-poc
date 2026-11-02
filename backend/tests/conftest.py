"""
Shared pytest fixtures for CivicScale backend API tests.

All tests hit the production Render backend at BASE_URL.
No local server is started — these are pure integration tests against the live API.
"""

import hashlib
import os
from pathlib import Path

import pytest
import httpx

# ---------------------------------------------------------------------------
# Git isolation (2026-11-02)
# ---------------------------------------------------------------------------
# Inside a git hook, git exports GIT_DIR, GIT_INDEX_FILE, GIT_WORK_TREE, ... to
# the hook's process. Every `git` a test -- or the code under test -- then ran
# acted on THE REAL REPOSITORY, whatever `-C <tmp>` it passed: three
# "acceptance" commits landed on the real main and user.name / user.email
# were written into its .git/config. So every GIT_* variable is removed for the
# whole session, before any test module is imported, and the session fails if
# the real repository's HEAD, branch, reflog or config changed underneath it.
GIT_ENV_SCRUBBED = sorted(k for k in os.environ if k.startswith("GIT_"))
for _k in GIT_ENV_SCRUBBED:
    del os.environ[_k]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_dirs(root: Path):
    """(gitdir, commondir) for a checkout or a linked worktree; None if not a repo."""
    dot = root / ".git"
    if dot.is_dir():
        return dot, dot
    if dot.is_file():
        gd = Path(dot.read_text().split("gitdir:", 1)[1].strip())
        gd = gd if gd.is_absolute() else (root / gd).resolve()
        cd = gd / "commondir"
        common = (gd / cd.read_text().strip()).resolve() if cd.exists() else gd
        return gd, common
    return None


def real_repo_state():
    """A fingerprint of what a stray `git commit` / `git config` would change."""
    dirs = _git_dirs(REPO_ROOT)
    if not dirs:
        return None
    gd, common = dirs
    head = (gd / "HEAD").read_text() if (gd / "HEAD").exists() else ""
    parts = [head]
    if head.startswith("ref: "):
        ref = common / head[5:].strip()
        parts.append(ref.read_text() if ref.exists() else "")
    for f in (gd / "logs" / "HEAD", common / "config", common / "packed-refs"):
        parts.append(hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else "-")
    return parts


def pytest_sessionstart(session):
    session.config._real_repo_state = real_repo_state()


def pytest_sessionfinish(session, exitstatus):
    before = getattr(session.config, "_real_repo_state", None)
    if before is not None and real_repo_state() != before:
        print("\n\nTHE TEST SESSION CHANGED THE REAL REPOSITORY (%s): HEAD, branch, reflog "
              "or .git/config differ from the start of the run. A test ran git outside "
              "its temp repo." % REPO_ROOT)
        session.exitstatus = 1

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get(
    "CIVICSCALE_API_URL", "https://parity-poc-api.onrender.com"
)
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co"
)
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

TEST_ADMIN_EMAIL = "test-admin@civicscale-testing.internal"
TEST_ANALYST_EMAIL = "test-analyst@civicscale-testing.internal"

# Timeout for individual HTTP requests (seconds)
REQUEST_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url():
    """Production API base URL."""
    return BASE_URL


@pytest.fixture(scope="session")
def supabase_url():
    """Production Supabase URL."""
    return SUPABASE_URL


@pytest.fixture(scope="session")
def supabase_key():
    """Supabase service role key for direct DB access (TEST-2)."""
    return SUPABASE_SERVICE_ROLE_KEY


@pytest.fixture(scope="session")
def client():
    """
    Shared httpx client for the entire test session.
    No auth headers — individual tests add them as needed.
    """
    with httpx.Client(base_url=BASE_URL, timeout=REQUEST_TIMEOUT) as c:
        yield c


@pytest.fixture(scope="session")
def supabase_rest_headers():
    """Headers for direct Supabase REST/PostgREST calls."""
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


@pytest.fixture(scope="session")
def supabase_client():
    """
    Direct httpx client pointed at the Supabase PostgREST endpoint.
    Used for read-only schema verification in TEST-2.
    """
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    with httpx.Client(
        base_url=f"{SUPABASE_URL}/rest/v1/",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    ) as c:
        yield c


@pytest.fixture(scope="session")
def supabase_rpc_client():
    """
    Direct httpx client for Supabase RPC (SQL execution via pg_catalog).
    Used for schema introspection in TEST-2.
    """
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    with httpx.Client(
        base_url=f"{SUPABASE_URL}/rest/v1/",
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    ) as c:
        yield c


@pytest.fixture(scope="session")
def admin_email():
    return TEST_ADMIN_EMAIL


@pytest.fixture(scope="session")
def analyst_email():
    return TEST_ANALYST_EMAIL
