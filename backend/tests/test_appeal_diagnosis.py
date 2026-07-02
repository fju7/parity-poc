"""Condition-neutral diagnosis intake + generalized FDA-indication extraction.

Offline tests (no live model, no network, no DB):
  * the appeal request model accepts patient_diagnosis / patient_icd_code;
  * the handler merges patient_diagnosis into da["patient_diagnosis"] and
    patient_icd_code into da's icd_codes list (deduped);
  * _extract_fda_indication now captures a NON-cancer indication (removing the old
    "Cancer" hardcode) while still capturing the existing cancer indication.
"""

import json
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers import health_analyze  # noqa: E402
from utils.evidence_retrieval import _extract_fda_indication  # noqa: E402

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_FIX = os.path.join(_REPO, "test-data", "appeals", "signatera_cigna")


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

def test_request_model_accepts_diagnosis_fields():
    req = health_analyze.AppealGenerateRequest(
        denial_analysis={}, patient_diagnosis="chronic migraine", patient_icd_code="G43.909"
    )
    assert req.patient_diagnosis == "chronic migraine"
    assert req.patient_icd_code == "G43.909"


# ---------------------------------------------------------------------------
# Handler merge into da — halt right after the merge (before model/network)
# ---------------------------------------------------------------------------

@pytest.fixture
def merge_client(monkeypatch):
    """A TestClient wired so a request reaches the diagnosis merge, then halts in a
    faked _apply_pregen_validators that records the merged `da`. No auth, model,
    network, or DB is exercised."""
    captured = {}

    def _fake_pregen(da, claim_number=None):
        captured["da"] = da
        raise RuntimeError("STOP_AFTER_MERGE")     # halt before retrieve_evidence / model

    monkeypatch.setattr(health_analyze, "get_health_user", lambda *a, **k: {"email": "test"})  # bypass auth
    monkeypatch.setattr(health_analyze, "_get_supabase", lambda: None)
    monkeypatch.setattr(health_analyze, "_get_client", lambda: object())   # avoid 503 (no ANTHROPIC key)
    monkeypatch.setattr(health_analyze, "_apply_pregen_validators", _fake_pregen)

    app = FastAPI()
    app.include_router(health_analyze.router)
    client = TestClient(app, raise_server_exceptions=False)
    return client, captured


def test_patient_diagnosis_lands_in_da(merge_client):
    client, captured = merge_client
    client.post("/api/health/generate-appeal", json={
        "denial_analysis": {"icd_codes": []},
        "patient_diagnosis": "stage 3 colon cancer",
        "patient_icd_code": None,
    }, headers={"Authorization": "Bearer x"})
    assert captured["da"]["patient_diagnosis"] == "stage 3 colon cancer"


def test_patient_icd_code_appended_to_icd_codes(merge_client):
    client, captured = merge_client
    client.post("/api/health/generate-appeal", json={
        "denial_analysis": {"icd_codes": ["C18.9"]},
        "patient_icd_code": "G43.909",
    }, headers={"Authorization": "Bearer x"})
    icd = captured["da"]["icd_codes"]
    assert "G43.909" in icd and "C18.9" in icd          # appended, existing preserved


def test_patient_icd_code_not_duplicated(merge_client):
    client, captured = merge_client
    client.post("/api/health/generate-appeal", json={
        "denial_analysis": {"icd_codes": ["G43.909"]},
        "patient_icd_code": "G43.909",
    }, headers={"Authorization": "Bearer x"})
    assert captured["da"]["icd_codes"].count("G43.909") == 1   # deduped


# ---------------------------------------------------------------------------
# Generalized FDA indication extractor (condition-agnostic)
# ---------------------------------------------------------------------------

# Realistic non-cancer companion-Dx approval-order statement (cystic fibrosis),
# mirroring the real "Indicated Use and Associated Therapy" table shape.
_NONCANCER_AO = (
    "TheraCF CDx is an assay that detects a biomarker. TheraCF CDx is intended to "
    "identify patients. Table 1: TheraCF CDx Indicated Use and Associated Therapy"
    "Biomarker\tIndication \tTherapyCFTR mutation\tCystic Fibrosis (CF)\tKALYDECO® (ivacaftor)"
)


def test_fda_extractor_captures_noncancer_indication():
    out = _extract_fda_indication(_NONCANCER_AO)
    assert "cystic fibrosis" in (out.get("disease") or "").lower()   # captured, not dropped
    assert out.get("therapy") == "ivacaftor"


def test_fda_extractor_still_captures_cancer_indication():
    # Regression: the real Signatera statement (read from the frozen fixture,
    # not modified) must still yield the muscle-invasive bladder cancer indication.
    gold = json.load(open(os.path.join(_FIX, "expected_evidence.json")))
    ao = next(it["metadata"]["ao_statement"] for it in gold["fda"])
    out = _extract_fda_indication(ao)
    assert out.get("disease") == "Muscle Invasive Bladder Cancer (MIBC)"
    assert out.get("therapy") == "atezolizumab"


def test_fda_extractor_returns_empty_when_undeterminable():
    assert _extract_fda_indication("") == {}
    assert _extract_fda_indication("This device is indicated for general use in adults.") == {}
