"""PH-4b-2: patient instruction sheet PDF + copy-paste provider email.

The sheet and email are DATA-ONLY (no AI model, no evidence search) and STORE NOTHING.
These deterministic offline tests cover: the endpoint auth gate + PDF magic bytes (no
live model/network), the provider-email composition (claim/service/name + graceful
degradation), and the sheet-content assembly (medical-necessity prioritization, omit
absent peer-to-peer/alt-address, never a visible null).
"""

import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers import health_analyze  # noqa: E402
from routers.health_analyze import (  # noqa: E402
    _build_provider_email,
    _build_patient_sheet_content,
    _render_patient_sheet_pdf,
)


# ---- auth-gate fake Supabase (session lookup returns no rows -> 401) ----
class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
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

_FIXTURE_DA = {
    "patient_name": "Jane A. Doe",
    "provider_name": "Sample Provider",
    "claim_number": "CLAIM-TEST-0340U",
    "payer_name": "Cigna",
    "procedure_terms": ["Signatera", "ctDNA MRD"],
    "cpt_codes": ["0340U"],
    "appeal_submission": {
        "address": "eviCore Healthcare\nPO Box 5620",
        "alt_address": "Cigna NAO\nPO Box 188011",
        "fax": "800-555-1212",
        "phone": "800-555-3434",
    },
    "appeal_deadline_hint": "72 hours",
    "deadline_days_standard": 180,
    "peer_to_peer_contact": "800-555-9999",
    "supporting_documentation": [
        "Recent office notes",
        "Letter of medical necessity from your provider",
        "Prior test results",
    ],
}


# -- 7.1: sheet endpoint auth + PDF bytes --
def test_sheet_no_auth_returns_401(client):
    r = client.post("/api/health/generate-patient-sheet-pdf", json=_BODY)
    assert r.status_code == 401, r.text


def test_sheet_invalid_token_returns_401(client):
    r = client.post("/api/health/generate-patient-sheet-pdf", json=_BODY,
                    headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401, r.text


def test_sheet_happy_path_returns_pdf(monkeypatch):
    # Pass auth WITHOUT a session/DB; no model is ever involved for the sheet.
    monkeypatch.setattr(health_analyze, "get_health_user", lambda *a, **k: {"id": "u1"})
    app = FastAPI()
    app.include_router(health_analyze.router)
    c = TestClient(app)
    r = c.post("/api/health/generate-patient-sheet-pdf",
               json={"denial_analysis": _FIXTURE_DA},
               headers={"Authorization": "Bearer valid"})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert 'filename="patient-instructions.pdf"' in r.headers.get("content-disposition", "")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 1000


def test_provider_email_endpoint_returns_text(monkeypatch):
    monkeypatch.setattr(health_analyze, "get_health_user", lambda *a, **k: {"id": "u1"})
    app = FastAPI()
    app.include_router(health_analyze.router)
    c = TestClient(app)
    r = c.post("/api/health/provider-email",
               json={"denial_analysis": _FIXTURE_DA},
               headers={"Authorization": "Bearer valid"})
    assert r.status_code == 200, r.text
    assert "CLAIM-TEST-0340U" in r.json()["email"]


# -- 7.2: provider email composition + graceful degradation --
def test_provider_email_includes_claim_service_and_name():
    em = _build_provider_email(_FIXTURE_DA)
    assert "Dear Sample Provider," in em            # addressed by name, no invented title
    assert "CLAIM-TEST-0340U" in em                 # claim number present
    assert "Signatera" in em and "0340U" in em      # service present
    assert "Cigna" in em                            # payer present


def test_provider_email_degrades_without_provider_or_payer():
    da = {"claim_number": "C1"}                      # no provider, no payer, no service, no name
    em = _build_provider_email(da)
    assert "Dear ordering provider's office," in em  # neutral recipient
    assert "to my insurer" in em                     # neutral payer phrasing
    assert "[Your name]" in em                       # graceful missing patient name
    assert "None" not in em and "null" not in em.lower()  # no blank/None tokens


# -- sheet content assembly: the concise "What You Need to Do" section replaced the old
# "What To Gather" checklist; the sheet no longer reads supporting_documentation. --
def test_sheet_what_you_need_to_do_present_and_worded():
    c = _build_patient_sheet_content(_FIXTURE_DA)
    assert "gather" not in c and "gather_note" not in c       # old checklist keys removed
    w = c["what_you_need_to_do"]
    assert "letter of medical necessity" in w and "medical records" in w
    assert "appeal letter already" in w                       # evidence-already-in-letter framing
    assert "Sample Provider" in w                             # provider name when present
    assert "CLAIM-TEST-0340U" in w                            # claim number when present
    assert "section below" in w                               # points down to the email section


def test_sheet_what_you_need_to_do_degrades_gracefully():
    c = _build_patient_sheet_content({"supporting_documentation": ["X"]})  # no provider, no claim
    w = c["what_you_need_to_do"]
    assert "ask your provider for a letter of medical necessity" in w      # neutral, no parenthetical
    assert "referencing claim number" not in w                            # no claim clause
    assert "()" not in w and "None" not in w


def test_sheet_omits_absent_fields_and_no_visible_null():
    da = {"claim_number": "C1", "supporting_documentation": ["Office notes"],
          "appeal_submission": {"address": "Only Addr"}}
    c = _build_patient_sheet_content(da)
    assert c["where"]["guidance"] is None            # no alt_address -> no "which applies" line
    assert c["where"]["alt_address"] is None
    assert c["deadlines"] == []                       # no deadline fields, no peer-to-peer line
    # No user-visible string contains a literal None/null.
    visible = [c["intro"], c["what_you_need_to_do"], c["provider_email"], c["provider_email_intro"]]
    visible += c["deadlines"] + c["next_steps"]
    visible += [v for v in (c["where"]["address"],) if v]
    blob = " ".join(visible)
    assert "None" not in blob and "null" not in blob.lower()


def test_sheet_uses_deadline_hint_verbatim_no_conversion():
    c = _build_patient_sheet_content(_FIXTURE_DA)
    joined = " ".join(c["deadlines"])
    assert "72 hours" in joined          # literal wording, not converted to days
    assert "3 days" not in joined
    assert "180 days" in joined          # day-integer standard deadline in plain language


# -- Next Steps wording fix: the email section renders ABOVE Next Steps, so step 3
# must point "above", not "below". --
def test_next_steps_step3_points_above():
    c = _build_patient_sheet_content(_FIXTURE_DA)
    step3 = c["next_steps"][2]
    assert "using the text above" in step3
    assert "using the text below" not in step3
