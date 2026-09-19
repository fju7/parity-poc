"""The policy is attached where the output leaves: each wired surface, driven
through its real endpoint code with a stubbed model, fed a known-bad, refuses
or withholds -- and UNCHECKED reaches the response and the stored record.

Offline: Supabase and the model wrapper are stubbed; nothing touches the network.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest
from fastapi import HTTPException

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

GOLDEN_LAW = json.load(open(os.path.join(BACKEND, "tests", "verify", "golden_law.json")))
OHIO_3901_1_54 = next(r["cite"] for r in GOLDEN_LAW["negatives"] if "3901-1-54" in r["cite"])


# ---------------------------------------------------------------------------
# P1 provider letter: a citation in escalation_path (a field the old gate never saw)
# ---------------------------------------------------------------------------
def test_provider_letter_refuses_a_citation_hidden_in_escalation_path(monkeypatch):
    import routers.provider_appeals as pa
    drafts = iter([
        {"letter_text": "Dear Payer, pay the claim within 30 calendar days.", "letter_html": "<p>x</p>",
         "escalation_path": f"Escalate under {OHIO_3901_1_54} to the state Department of Insurance.",
         "appeal_strength_reason": "high", "attach_documentation": "operative notes", "cms_references": []},
        {"letter_text": "Dear Payer, pay the claim within 30 calendar days.", "letter_html": "<p>x</p>",
         "escalation_path": f"Escalate under {OHIO_3901_1_54}.",
         "appeal_strength_reason": "high", "attach_documentation": "operative notes", "cms_references": []},
    ])
    calls = []
    def fake(**kw):
        calls.append(kw["user_content"]); return next(drafts)
    monkeypatch.setattr(pa, "_call_claude", fake)
    data = json.dumps({"claim_id": "C1", "denial_code": "CO-16", "cpt_code": "99213", "billed_amount": 120.0,
                       "payer_name": "Aetna", "date_of_service": "2025-01-05", "practice_name": "P",
                       "practice_address": "1 Main St, Columbus, OH 43215", "billing_contact": "B", "npi": "1234567890",
                       "patient_name": "X", "contracted_rate_info": None})
    assert pa._gated_letter(data) is None          # both drafts refused -> no letter
    assert len(calls) == 2 and "3901-1-54" in calls[1]   # the regeneration named the violation


def test_provider_letter_passes_and_carries_a_verification_record(monkeypatch):
    import routers.provider_appeals as pa
    monkeypatch.setattr(pa, "_call_claude", lambda **kw: {
        # APPEALS-3: the passing fixture argues on the record and asks; the old fixture
        # ("we demand ... prompt-pay ... Department of Insurance") is now a refusal by design.
        "letter_text": "Dear Payer, this is a first-level appeal of Claim C1 under CO-16. The information the denial "
                       "lists as missing is on the corrected claim as submitted, and the claim can be adjudicated with it. We ask that the claim be "
                       "reprocessed and $120.00 paid, and that you send the written criteria you applied. Please respond by 30 calendar days from the date of this letter.",
        "letter_html": "<p>x</p>", "attach_documentation": "operative notes", "cms_references": []})
    data = json.dumps({"claim_id": "C1", "denial_code": "CO-16", "cpt_code": "99213", "billed_amount": 120.0,
                       "payer_name": "Aetna", "date_of_service": "2025-01-05", "practice_name": "P",
                       "practice_address": "1 Main St", "billing_contact": "B", "npi": "1234567890",
                       "patient_name": "X", "contracted_rate_info": None})
    out = pa._gated_letter(data)
    assert out and out["verification"]["ok"] and out["verification"]["surface"] == "routers.provider_appeals::_gated_letter"


# ---------------------------------------------------------------------------
# K3 broker letter: model cites 1185i -> template; template sabotaged -> 502
# ---------------------------------------------------------------------------
class _Q:
    def __init__(s, data): s.data = data
    def select(s, *a, **k): return s
    def eq(s, *a, **k): return s
    def execute(s): return s
class _SB:
    def table(s, n): return _Q([{"company_name": "Midwest Mfg", "carrier": "Anthem", "state": "OH",
                                 "employee_count_range": "251-500", "renewal_month": "2026-12-01", "industry": "Mfg"}])


@pytest.fixture
def broker(monkeypatch):
    import routers.broker as b
    monkeypatch.setattr(b, "_require_broker", lambda auth: ({"email": "p@x", "full_name": "PB", "company": {"name": "PBF"}}, _SB()))
    return b


def test_broker_model_letter_citing_1185i_is_refused_and_the_template_serves(broker, monkeypatch):
    monkeypatch.setattr(broker, "_call_claude", lambda **k: {"letter": "Pursuant to 29 U.S.C. § 1185i, send the data."})
    r = asyncio.run(broker.generate_caa_letter("c@x", authorization="x"))
    assert r["source"] == "template" and r["verification"]["ok"]
    assert "1185i" not in r["letter"]


def test_broker_template_that_cites_is_refused_outright(broker, monkeypatch):
    monkeypatch.setattr(broker, "_call_claude", lambda **k: None)
    orig = broker._caa_template
    monkeypatch.setattr(broker, "_caa_template", lambda *a: orig(*a) + "\nSee EBSA Field Assistance Bulletin 2021-04.")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(broker.generate_caa_letter("c@x", authorization="x"))
    assert exc.value.status_code == 502


# ---------------------------------------------------------------------------
# H4 health letter: needs_revision marks the JSON and withholds the PDF
# ---------------------------------------------------------------------------
def _health_stub(monkeypatch, body_text):
    import routers.health_analyze as h
    class Block: text = body_text
    class Resp: content = [Block()]
    class Client:
        messages = None
        def __init__(s): s.messages = s
        def create(s, **kw): return Resp()
    monkeypatch.setattr(h, "_get_client", lambda: Client())
    monkeypatch.setattr(h, "retrieve_evidence", lambda da: {"pubmed": [], "cms": [], "fda": [], "gaps": []})
    monkeypatch.setattr(h, "get_health_user", lambda auth, sb: {"id": "u"})
    monkeypatch.setattr(h, "_get_supabase", lambda: None)
    return h


def _req(h):
    return h.AppealGenerateRequest(denial_analysis={
        "denial_reason_plain": "not medically necessary", "specific_criterion": "policy MOL.CU.117",
        "appeal_rights": ["Independent external reviews"], "cpt_codes": ["0340U"], "procedure_terms": ["Signatera"],
        "payer_name": "Cigna", "provider_name": "Smith", "state": "OH", "billed_amount": 3500,
    })


def test_health_letter_asserting_erisa_and_fda_status_is_marked_and_the_pdf_withheld(monkeypatch):
    h = _health_stub(monkeypatch, "__LETTER_DATE__\n\nDear Cigna,\n\nUnder ERISA the plan must cover this FDA-approved test, "
                                  "which 94% of oncologists use.\n\nSincerely,\n__PATIENT_NAME__")
    out = h._generate_appeal_result(_req(h))
    assert out["needs_revision"] and out["sendable"] is False
    kinds = {f["kind"] for f in out["verification"]["refused"]}
    assert {"erisa", "fda_status"} <= kinds, kinds
    assert any("94" in r for r in out["withheld_reasons"])
    with pytest.raises(HTTPException) as exc:
        h.generate_appeal_pdf(_req(h), authorization="Bearer x")
    assert exc.value.status_code == 422 and exc.value.detail["error"] == "letter_needs_revision"


def test_health_letter_within_its_material_is_sendable(monkeypatch):
    h = _health_stub(monkeypatch, "__LETTER_DATE__\n\nDear Cigna,\n\nThe patient appeals the denial under policy MOL.CU.117 "
                                  "of the Signatera test (0340U), billed at $3,500. The denial grants Independent external reviews.\n\n"
                                  "Sincerely,\n__PATIENT_NAME__")
    out = h._generate_appeal_result(_req(h))
    assert out["sendable"] is True and out["verification"]["ok"], out["withheld_reasons"]


# ---------------------------------------------------------------------------
# P2 extraction: text binds and prunes; image is UNCHECKED in the response
# ---------------------------------------------------------------------------
def test_fee_schedule_text_prunes_a_rate_not_in_the_source(monkeypatch):
    import routers.provider_audit as pa
    monkeypatch.setattr(pa, "_call_claude", lambda **kw: {"payer_name": "Aetna", "effective_date": "", "rates": [
        {"cpt": "99213", "rate": 95.5, "description": "Office visit"},
        {"cpt": "99215", "rate": 210.0, "description": "Office visit, level 5"}]})
    req = pa.ExtractFeeScheduleTextRequest(text="99213 Office visit 95.50\n99214 Office visit 135.00")
    out = asyncio.run(pa.extract_fee_schedule_text(req))
    assert [r["cpt"] for r in out["rates"]] == ["99213"]
    assert out["rows_removed_not_in_source"] == 1 and out["verification"]["refused"]


def test_fee_schedule_image_is_unchecked_in_the_response(monkeypatch):
    import routers.provider_audit as pa
    monkeypatch.setattr(pa, "_call_claude", lambda **kw: {"payer_name": "Aetna", "effective_date": "", "rates": [
        {"cpt": "99213", "rate": 95.5, "description": "Office visit"}]})
    class F:
        filename = "sched.png"; content_type = "image/png"
        async def read(self): return b"\x89PNG\r\n\x1a\n" + b"0" * 100
    out = asyncio.run(pa.extract_fee_schedule_image(F()))
    v = out["verification"]
    assert out["rates"] and v["ok"] and v["verified"] is False and v["unchecked"]
    assert "no text layer" in v["unchecked"][0]["reason"]


# ---------------------------------------------------------------------------
# E1 benchmark narrative: an invented number drops the narrative, not the numbers
# ---------------------------------------------------------------------------
def test_benchmark_narrative_with_an_invented_figure_is_dropped(monkeypatch):
    import routers.employer_benchmark as eb
    monkeypatch.setattr(eb, "_call_claude", lambda **kw: {
        "narrative": "Your PEPM sits above the median; peers typically save $9,999 per employee.",
        "talking_points": ["Ask your broker: \"why?\""]})
    class _NoSB:
        def table(self, n): raise RuntimeError("no db in test")
    monkeypatch.setattr(eb, "_get_supabase", lambda: _NoSB())
    monkeypatch.setattr(eb, "check_rate_limit", lambda request, max_requests=30: None)
    req = eb.BenchmarkRequest(email="t@x", industry="Manufacturing", company_size="50-199", state="OH", pepm_input=650.0)
    out = asyncio.run(eb.employer_benchmark(req, request=None))
    assert out["narrative"] is None and out["talking_points"] is None
    assert any("9,999" in f["text"] or "9999" in f["text"] for f in out["verification"]["refused"])
    assert out["input"]["pepm_input"] == 650.0      # the computed numbers are untouched


# ---------------------------------------------------------------------------
# S1 Q&A: a DOI not in the context withholds the answer
# ---------------------------------------------------------------------------
def test_qa_answer_citing_an_unheld_doi_is_withheld(monkeypatch):
    import routers.signal_qa as qa
    async def _user(req): return type("U", (), {"id": "u1"})()
    monkeypatch.setattr(qa, "_get_authenticated_user", _user)
    monkeypatch.setattr(qa, "_check_qa_limit", lambda uid: None, raising=False)
    monkeypatch.setattr(qa, "_build_context", lambda issue_id: "Topic: GLP-1. Claim: weight loss 15% (doi:10.1056/nejmoa2032183).")
    class Block: text = "As doi:10.1001/jama.2024.2525 shows, weight regain is universal."
    class Resp: content = [Block()]
    class Client:
        def __init__(s): s.messages = s
        def create(s, **kw): return Resp()
    import anthropic as _anthropic
    monkeypatch.setattr(_anthropic, "Anthropic", lambda api_key=None: Client())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    body = qa.QARequest(issue_id="i1", question="Does weight come back?")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(qa.ask_question(body, request=None))
    assert exc.value.status_code == 502 and "withheld" in exc.value.detail


# ---------------------------------------------------------------------------
# P1 storage: a letter whose record (and verdict) cannot be stored is not returned
# ---------------------------------------------------------------------------
def test_provider_letter_is_not_returned_when_its_record_cannot_be_stored(monkeypatch):
    import routers.provider_appeals as pa
    monkeypatch.setattr(pa, "_get_authenticated_user", lambda request: type("U", (), {"id": "u1"})())
    monkeypatch.setattr(pa, "_fetch_provider_context", lambda uid: {"practice_name": "P", "npi": "1", "practice_address": "1 Main St", "billing_contact": "B", "contracts": {}})
    monkeypatch.setattr(pa, "_call_claude", lambda **kw: {"letter_text": "Dear Payer, pay $120.00 within 30 calendar days.", "letter_html": "<p>x</p>",
                                                          "attach_documentation": "notes", "cms_references": []})
    class _Ins:
        def insert(self, rec):
            assert "verification" in rec and rec["verification"]["surface"] == "routers.provider_appeals::_gated_letter"
            class E:
                def execute(self_inner): raise RuntimeError("PGRST204 column missing")
            return E()
    class _SB:
        def table(self, name): return _Ins()
    monkeypatch.setattr(pa, "_get_supabase", lambda: _SB())
    req = pa.GenerateAppealRequest(claim_id="C1", denial_code="CO-16", cpt_code="99213", billed_amount=120.0,
                                   payer_name="Aetna", date_of_service="2025-01-05")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(pa.generate_appeal(req, request=None))
    assert exc.value.status_code == 500 and "could not be recorded" in exc.value.detail
