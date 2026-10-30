"""The Google runners' paid-tier preflight (advisor ruling 2026-10-30, after the free-tier incident in
study/whu-reliability/next_phase/deviations.md). Offline: no Google or Anthropic call is made."""
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NEXT = ROOT / "study" / "whu-reliability" / "next_phase"
sys.path.insert(0, str(NEXT))
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "scripts"))
pytest.importorskip("google.genai")
import judge_google as G  # noqa: E402
from google.genai import errors  # noqa: E402

FREE = {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota",
                  "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                      {"description": "Generate content requests per day limit exceeded on Free Tier.",
                       "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}


class FakeModels:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def generate_content(self, model, contents, config=None):
        self.calls.append(("generate_content", contents))
        if self.fail:
            raise self.fail
        u = types.SimpleNamespace(prompt_token_count=8, candidates_token_count=1, thoughts_token_count=20,
                                  cached_content_token_count=0)
        return types.SimpleNamespace(usage_metadata=u, model_version=G.MODEL, text="ok")

    def count_tokens(self, *a, **k):
        self.calls.append(("count_tokens", None))
        raise AssertionError("count_tokens must never be called")


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    G._checked.clear()
    rec = []
    monkeypatch.setattr(G.S, "record", lambda **k: rec.append(k))
    return rec


def gc(fail=None):
    return types.SimpleNamespace(models=FakeModels(fail))


def test_a_free_tier_quota_error_is_a_stop_and_nothing_else_is_called():
    c = gc(errors.ClientError(429, FREE))
    with pytest.raises(G.Stop, match="Free Tier"):
        G.preflight(c)
    assert c.models.calls == [("generate_content", G.PREFLIGHT_TEXT)]


def test_any_other_error_is_also_a_stop():
    with pytest.raises(G.Stop, match="cannot confirm"):
        G.preflight(gc(errors.ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "x"}})))


def test_a_success_is_one_tiny_call_carrying_no_study_content_and_is_recorded(fresh):
    c = gc()
    out = G.preflight(c)
    assert c.models.calls == [("generate_content", G.PREFLIGHT_TEXT)] and len(G.PREFLIGHT_TEXT) < 40
    assert out["usd"] < 0.001 and fresh and fresh[0]["role"] == "google-preflight"
    G.preflight(c)                                              # once per process
    assert len(c.models.calls) == 1


def test_client_runs_the_preflight_before_returning(monkeypatch):
    made = gc(errors.ClientError(429, FREE))
    fake_genai = types.SimpleNamespace(Client=lambda api_key: made)
    monkeypatch.setitem(sys.modules, "google.genai", types.SimpleNamespace(**{**vars(sys.modules["google.genai"]),
                                                                              "Client": fake_genai.Client}))
    monkeypatch.setattr(G.J1, "env_keys", lambda: {"GEMINI_API_KEY": "x"})
    import google
    monkeypatch.setattr(google, "genai", sys.modules["google.genai"], raising=False)
    with pytest.raises(G.Stop):
        G.client()
    assert made.models.calls == [("generate_content", G.PREFLIGHT_TEXT)]


def test_no_runner_calls_googles_count_tokens_or_makes_its_own_client():
    for f in NEXT.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        assert not re.search(r"\.models\.count_tokens\(", src), f.name
        if f.name != "judge_google.py":
            assert "genai.Client(" not in src, f.name


def test_the_estimate_is_a_labelled_approximation_that_errs_high():
    assert G.approx_tokens("") == 0
    assert G.approx_tokens("x" * 300) == 100
    # Google's own counts on 2026-10-30 ranged 3.30-4.64 characters a token; 3.0 gives more tokens than any of them
    assert all(G.approx_tokens("x" * 1000) >= 1000 / r for r in (3.30, 3.71, 4.11, 4.14, 4.57, 4.64))
