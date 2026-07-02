"""
Shared pytest fixtures for CivicScale backend API tests.

All tests hit the production Render backend at BASE_URL.
No local server is started — these are pure integration tests against the live API.
"""

import os
import pytest
import httpx

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
