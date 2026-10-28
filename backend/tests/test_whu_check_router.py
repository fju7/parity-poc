"""The "check an AI answer" preview API (routers/whu_check.py), offline.

401 without the code, 503 with WHU_CHECK_CODE unset, 402 over the cap (no call), the origin
guard, the limits, and one full job on the recorded answer and source of
test_whu_check_pilot.py. No network, no model, and the real ledger is never read or written:
the ledger and caps are replaced per test."""
import os
import sys
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
sys.path.insert(0, os.path.dirname(__file__))

from routers import whu_check as W  # noqa: E402
import test_whu_check_pilot as T  # noqa: E402

CODE = "test-code-not-real"
ANSWER = (T.FIX / "answer_claude_sources.md").read_text(encoding="utf-8")


@pytest.fixture
def ledger(monkeypatch):
    """A fake ledger and caps: {'lines': [...]} the test can fill."""
    S = W.pipeline().S
    state = {"lines": [], "caps": {"per_issue": {W.ISSUE: 20}, "per_issue_per_day": {W.ISSUE: 10}, "default_per_day": 25}}
    monkeypatch.setattr(S, "entries", lambda: list(state["lines"]))
    monkeypatch.setattr(S, "caps", lambda: state["caps"])
    monkeypatch.setattr(S, "unpriced", lambda issue=None, since=None: [])
    monkeypatch.setattr(S, "spent", lambda issue=None, since=None: sum(
        float(e.get("usd") or 0) for e in state["lines"] if issue is None or e.get("issue") == issue))
    monkeypatch.setattr(S, "check_day_cap", lambda about_to_spend=0.0: None)
    return state


@pytest.fixture
def app(monkeypatch, tmp_path, ledger):
    monkeypatch.setenv("WHU_CHECK_CODE", CODE)
    monkeypatch.setattr(W, "JOBS_LOG", tmp_path / "jobs.jsonl")
    monkeypatch.setattr(W, "LICENCE_FN", T.fake_licence)
    monkeypatch.setattr(W, "RETRIEVE_FN", T.fake_retrieve)
    fake = T.client()
    monkeypatch.setattr(W, "_clients", lambda: (fake, T.count))
    monkeypatch.setattr(W, "_running", None)
    W._jobs.clear()
    a = FastAPI()
    a.include_router(W.router)
    a.add_middleware(W.OriginGuard)
    a.state.fake = fake
    return a


def post(c, code=CODE, answer=ANSWER, **kw):
    h = {"X-Check-Code": code} if code is not None else {}
    h.update(kw.pop("headers", {}))
    return c.post("/api/whu/check", json={"answer": answer}, headers=h)


def wait(c, job_id, code=CODE):
    for _ in range(200):
        r = c.get("/api/whu/check/" + job_id, headers={"X-Check-Code": code})
        if r.json().get("status") not in ("queued", "running"):
            return r
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_no_code_is_401(app):
    c = TestClient(app)
    assert post(c, code=None).status_code == 401
    assert post(c, code="wrong").status_code == 401
    assert c.get("/api/whu/check/abc").status_code == 401
    assert app.state.fake.messages.calls == []


def test_env_var_unset_is_503_for_every_request(app, monkeypatch):
    monkeypatch.delenv("WHU_CHECK_CODE")
    c = TestClient(app)
    assert post(c).status_code == 503
    assert post(c, code=None).status_code == 503
    assert c.get("/api/whu/check/abc", headers={"X-Check-Code": CODE}).status_code == 503
    monkeypatch.setenv("WHU_CHECK_CODE", "")
    assert post(c, code="").status_code == 503


def test_over_the_total_cap_is_402_and_no_call(app, ledger):
    ledger["lines"].append({"issue": W.ISSUE, "usd": 20.0, "at": "2026-01-01T00:00:00+00:00"})
    c = TestClient(app)
    r = post(c)
    assert r.status_code == 402 and "cap" in r.json()["detail"]
    assert app.state.fake.messages.calls == [] and W._jobs == {}


def test_over_the_day_cap_is_402_and_no_call(app, ledger):
    from datetime import datetime, timezone
    ledger["lines"].append({"issue": W.ISSUE, "usd": 10.0, "at": datetime.now(timezone.utc).isoformat()})
    r = post(TestClient(app))
    assert r.status_code == 402 and "daily" in r.json()["detail"]
    assert app.state.fake.messages.calls == []


def test_a_job_whose_estimate_passes_the_cap_stops_before_any_call(app, ledger):
    ledger["lines"].append({"issue": W.ISSUE, "usd": 19.999, "at": "2026-01-01T00:00:00+00:00"})
    c = TestClient(app)
    r = post(c)
    assert r.status_code == 200
    g = wait(c, r.json()["id"])
    assert g.status_code == 402 and g.json()["status"] == "over_cap"
    assert app.state.fake.messages.calls == []


def test_one_full_job_on_recorded_sources(app, tmp_path, monkeypatch):
    made = []
    real = W.tempfile.mkdtemp
    monkeypatch.setattr(W.tempfile, "mkdtemp", lambda *a, **kw: made.append(real(*a, **kw)) or made[-1])
    c = TestClient(app)
    r = post(c, headers={"Origin": "https://whatholdsup.org"})
    assert r.status_code == 200, r.text
    assert r.headers["access-control-allow-origin"] == "https://whatholdsup.org"
    assert r.json()["claims"] == 4
    g = wait(c, r.json()["id"])
    assert g.status_code == 200 and g.json()["status"] == "done", g.json()
    res = g.json()["result"]
    labels = sorted(x["label"] for x in res["claims"])
    assert labels == sorted([W.pipeline().BACKED, W.pipeline().NOT_BACKED, W.pipeline().NO_SOURCE,
                             W.pipeline().COULDNT])
    assert all(x["reason"] for x in res["claims"])
    backed = next(x for x in res["claims"] if x["label"] == "BACKED")
    assert backed["sources"][0]["url"] == T.SOURCE_URL and backed["sources"][0]["licence"] == "cc by"
    assert res["totals"]["claims"] == 4
    # the operator log has counts and a hash, never the text
    log = (tmp_path / "jobs.jsonl").read_text()
    assert "input_sha256" in log and "network meta-analysis" not in log and "BACKED" in log
    # the job's working files (the answer and its sources) are gone
    assert made and not any(Path(m).exists() for m in made)


def test_limits(app):
    c = TestClient(app)
    assert post(c, answer="x" * (W.MAX_CHARS + 1)).status_code == 413
    many = "## Report\n\n" + "\n\n".join("Claim number %d says that 12 of 40 trials found an effect here." % i
                                         for i in range(W.MAX_CLAIMS + 1))
    r = post(c, answer=many)
    assert r.status_code == 422 and "40 claims" in r.json()["detail"]
    assert post(c, answer="   ").status_code == 422


def test_one_job_at_a_time(app, monkeypatch):
    monkeypatch.setattr(W, "_running", "someone-else")
    assert post(TestClient(app)).status_code == 409


def test_other_origins_are_refused(app):
    c = TestClient(app)
    r = post(c, headers={"Origin": "https://civicscale.ai"})
    assert r.status_code == 403
    pre = c.options("/api/whu/check", headers={"Origin": "https://whatholdsup.org",
                                               "Access-Control-Request-Method": "POST",
                                               "Access-Control-Request-Headers": "content-type,x-check-code"})
    assert pre.status_code == 200 and pre.headers["access-control-allow-origin"] == "https://whatholdsup.org"
    assert "x-check-code" in pre.headers["access-control-allow-headers"].lower()


def test_the_router_is_mounted_in_the_app():
    import main
    paths = {getattr(r, "path", "") for r in main.app.routes}
    assert "/api/whu/check" in paths and "/api/whu/check/{job_id}" in paths
