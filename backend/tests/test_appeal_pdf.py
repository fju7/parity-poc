"""PH-4b-1: POST /api/health/generate-appeal-pdf renders the appeal letter to a
clean PDF and streams it back, requiring the SAME auth as generate-appeal and
storing nothing.

Offline/deterministic: a fake Supabase client drives the auth gate (no-token /
invalid-token -> 401 with no network). The happy path mocks get_health_user (to
pass) AND _generate_appeal_result (to return a fixed letter_text) so the live model
and evidence retrieval are never hit; we then assert real PDF bytes are produced.
A separate test asserts the PDF renderer does NOT inject a second letterhead.
"""

import inspect
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
    # get_health_user chains .select().eq().eq().gt().execute(); return no rows -> 401.
    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gt(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def execute(self):
        return _Resp([])


class _FakeSB:
    def table(self, name):
        return _Query()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(health_analyze, "_get_supabase", lambda: _FakeSB())
    app = FastAPI()
    app.include_router(health_analyze.router)
    return TestClient(app)


_BODY = {"denial_analysis": {}}


# -- 4.1a: same auth gate as generate-appeal --
def test_pdf_no_authorization_header_returns_401(client):
    r = client.post("/api/health/generate-appeal-pdf", json=_BODY)
    assert r.status_code == 401, r.text


def test_pdf_invalid_token_returns_401(client):
    r = client.post(
        "/api/health/generate-appeal-pdf",
        json=_BODY,
        headers={"Authorization": "Bearer not-a-real-session-token"},
    )
    assert r.status_code == 401, r.text


# -- 4.1b: valid session -> application/pdf whose body starts with %PDF --
def test_pdf_happy_path_returns_pdf_bytes(monkeypatch):
    # Pass auth without a DB/session, and stub generation so no live model/network.
    monkeypatch.setattr(health_analyze, "get_health_user", lambda *a, **k: {"id": "u1"})
    monkeypatch.setattr(
        health_analyze, "_generate_appeal_result",
        lambda req: {"letter_text": "RE: FORMAL APPEAL\n\nDear Reviewer:\n\n- A point.\n\nSincerely,\nJane"},
    )
    app = FastAPI()
    app.include_router(health_analyze.router)
    c = TestClient(app)

    r = c.post(
        "/api/health/generate-appeal-pdf",
        json=_BODY,
        headers={"Authorization": "Bearer valid"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert 'filename="appeal-letter.pdf"' in r.headers.get("content-disposition", "")
    assert r.content[:4] == b"%PDF", "response body is not a PDF"
    assert len(r.content) > 1000


# -- 4.2: the renderer does NOT prepend a duplicate letterhead / Re: / Date block --
def test_renderer_does_not_prepend_second_letterhead():
    src = inspect.getsource(health_analyze._render_appeal_letter_pdf)
    # None of the Provider builder's letterhead-prepend constructs may appear here.
    assert "Re: Appeal" not in src
    assert "practice_name" not in src
    assert 'f"Date:' not in src and 'f"Re:' not in src
    # And it still renders a letter that ALREADY has its own RE:/date without error.
    letter = "__DATE__\nJane A. Doe\n\nRE: FORMAL APPEAL OF CLAIM DENIAL\n\nDear Reviewer:\n\nBody & text.\n"
    pdf = health_analyze._render_appeal_letter_pdf(letter)
    assert pdf[:4] == b"%PDF" and len(pdf) > 500
