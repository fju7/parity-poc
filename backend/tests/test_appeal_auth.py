"""PH-4b auth gate: POST /api/health/generate-appeal now requires a valid Health
token (get_health_user). Offline test — a fake Supabase client makes the session
lookup return "no session" for any token, so both the no-token and invalid-token
paths raise 401 with no network/DB. The valid-token happy path calls the live
model + evidence retrieval, so per the brief it is verified end-to-end (Task 5 /
UI), not faked here."""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers import health_analyze  # noqa: E402


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    # get_health_user chains .select().eq().eq().gt().execute(); return no rows.
    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gt(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def execute(self):
        return _Resp([])          # no matching session -> get_health_user raises 401


class _FakeSB:
    def table(self, name):
        return _Query()


@pytest.fixture
def client(monkeypatch):
    # Fake the Supabase client so the session lookup runs offline for any token.
    monkeypatch.setattr(health_analyze, "_get_supabase", lambda: _FakeSB())
    app = FastAPI()
    app.include_router(health_analyze.router)
    return TestClient(app)


# Valid request body (denial_analysis is required) so the auth check is reached
# rather than a 422 body-validation error.
_BODY = {"denial_analysis": {}}


def test_no_authorization_header_returns_401(client):
    r = client.post("/api/health/generate-appeal", json=_BODY)
    assert r.status_code == 401, r.text


def test_invalid_token_returns_401(client):
    r = client.post(
        "/api/health/generate-appeal",
        json=_BODY,
        headers={"Authorization": "Bearer not-a-real-session-token"},
    )
    assert r.status_code == 401, r.text
