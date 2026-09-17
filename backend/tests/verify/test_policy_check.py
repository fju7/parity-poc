"""Acceptance for the shared assertion policy: each gated surface is fed its
class's known-bad from the frozen controls and refuses.

Controls (all read-only, all already in the repo):
  - the 12 wrong Ohio provisions ......... tests/verify/golden_law.json  -> negatives
  - the 59 fabricated DOIs ............... scripts/signal/output/verify_sources_2026-09-14.json
  - MONALEESA-7's wrong PMID ............. tests/verify/golden_literature.json -> known_bad
  - 29 U.S.C. § 1185i (broker, 2026-09-15) resolved to the provider-directory section
No network: everything here is string comparison against held material.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify.policy import check, check_prompt_payload, Held, POLICY, Tier, AssertionClass as A  # noqa: E402
from verify.types import Document, Identifier  # noqa: E402

GOLDEN_LAW = json.load(open(os.path.join(BACKEND, "tests", "verify", "golden_law.json")))
GOLDEN_LIT = json.load(open(os.path.join(BACKEND, "tests", "verify", "golden_literature.json")))
VERIFY_SOURCES = json.load(open(os.path.join(BACKEND, "scripts", "signal", "output", "verify_sources_2026-09-14.json")))

OHIO_NEGATIVES = [r["cite"] for r in GOLDEN_LAW["negatives"]]
FABRICATED_DOIS = [r["identifier"].split("doi:", 1)[1] for r in VERIFY_SOURCES if r["verdict"] == "FABRICATED_IDENTIFIER"]
MONALEESA_PMID = [r for r in GOLDEN_LIT["known_bad"] if "MONALEESA" in r["ours"]][0]["id"].split("pmid:")[1]
USC_1185I = "29 U.S.C. § 1185i"


def _doc(text, layer="DECLARED_SOUND"):
    return Document(Identifier("url", "held"), "sha", text, text_layer=layer)


# ---------------------------------------------------------------------------
# LEGAL_PROVISION -- the 12 Ohio negatives and 1185i, on every letter surface
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cite", OHIO_NEGATIVES + [USC_1185I])
def test_provider_letter_refuses_each_known_bad_provision_in_every_field(cite):
    assert len(OHIO_NEGATIVES) == 12
    out = {"letter_text": f"Under {cite}, the payer must pay within thirty days.",
           "letter_html": "<p>ok</p>",
           "escalation_path": f"Escalate under {cite} to the Department of Insurance.",
           "cms_references": [cite]}
    v = check("routers.provider_appeals::_gated_letter", out, Held())
    assert not v.ok
    from utils.citation_gate import find_citations
    if find_citations(cite):
        refused_fields = {f.field for f in v.refusals if f.cls is A.LEGAL_PROVISION}
        assert {"letter_text", "escalation_path", "cms_references[0]"} <= refused_fields, refused_fields
    else:
        # one golden negative names a regulator without a number ("the Ohio
        # Department of Insurance's claims processing regulations"): that is
        # the NAMED_SOURCE class, withheld from this surface
        assert any(f.cls is A.NAMED_SOURCE and f.kind == "doi_state" for f in v.refusals), v.note()


@pytest.mark.parametrize("cite", OHIO_NEGATIVES + [USC_1185I])
def test_broker_letter_refuses_each_known_bad_provision(cite):
    v = check("routers.broker::generate_caa_letter",
              {"letter": f"Pursuant to {cite} we request the plan's claims data."},
              Held(named_ok={"caa"}))
    assert not v.ok and any(f.cls in (A.LEGAL_PROVISION, A.NAMED_SOURCE) for f in v.refusals)


@pytest.mark.parametrize("cite", OHIO_NEGATIVES + [USC_1185I])
def test_health_letter_refuses_each_known_bad_provision(cite):
    v = check("routers.health_analyze::_generate_appeal_result",
              {"letter_text": f"The plan is bound by {cite} to cover this test."}, Held())
    assert not v.ok and any(f.cls in (A.LEGAL_PROVISION, A.NAMED_SOURCE) for f in v.refusals)


def test_a_letter_that_cites_nothing_passes_the_legal_gate():
    v = check("routers.broker::generate_caa_letter",
              {"letter": "Under the transparency provisions of the Consolidated Appropriations Act, 2021, we request the data within 30 business days."},
              Held(named_ok={"caa"}, inputs={"deadline_business_days": 30}))
    assert v.ok, v.note()


# ---------------------------------------------------------------------------
# IDENTIFIER -- the 59 fabricated DOIs and the MONALEESA-7 PMID
# ---------------------------------------------------------------------------
def test_the_control_set_is_the_frozen_one():
    assert len(FABRICATED_DOIS) == 59
    assert MONALEESA_PMID == "31562796"


@pytest.mark.parametrize("doi", FABRICATED_DOIS)
def test_qa_answer_refuses_a_doi_it_was_not_handed(doi):
    ctx = "Sources: doi:10.1056/nejmoa2032183 (a real one the context carried)."
    v = check("routers.signal_qa::ask_question",
              {"answer": f"As shown in doi:{doi}, the effect is large."},
              Held(identifiers={"10.1056/nejmoa2032183"}, documents=[_doc(ctx)]))
    assert not v.ok
    assert any(f.cls is A.IDENTIFIER and f.kind == "doi" for f in v.refusals)


def test_qa_answer_binds_a_doi_it_was_handed():
    v = check("routers.signal_qa::ask_question", {"answer": "See doi:10.1056/nejmoa2032183."},
              Held(identifiers={"10.1056/nejmoa2032183"}, documents=[_doc("doi:10.1056/nejmoa2032183")]))
    assert v.ok, v.note()


@pytest.mark.parametrize("doi", FABRICATED_DOIS[:5])
def test_health_letter_verifies_identifiers_a_fabricated_doi_in_the_body_is_refused_or_unverified(doi):
    """APPEALS-3: identifiers are VERIFIED by lookup, not withheld. A fabricated DOI is
    refused when the Handle registry answers; when it does not, the citation is UNVERIFIED
    and the letter is not `verified` either -- silence is never a pass."""
    v = check("routers.health_analyze::_generate_appeal_result",
              {"letter_text": f"Published evidence (doi:{doi}) supports this test."}, Held())
    assert not v.verified
    idf = [f for f in v.findings if f.cls is A.IDENTIFIER and f.kind == "doi"]
    assert idf and idf[0].mode == "bound" and idf[0].ok in (False, None)
    if idf[0].ok is False:
        assert "does not exist" in idf[0].reason


def test_health_letter_refuses_the_monaleesa_pmid_and_a_bare_one():
    v = check("routers.health_analyze::_generate_appeal_result",
              {"letter_text": f"See PMID {MONALEESA_PMID}. A later report ({MONALEESA_PMID}) agrees."}, Held())
    kinds = {f.kind for f in v.refusals if f.cls is A.IDENTIFIER}
    assert {"pmid", "bare_pmid"} <= kinds, kinds


def test_provider_letter_flags_but_does_not_refuse_a_bare_8_digit_claim_id():
    v = check("routers.provider_appeals::_gated_letter", {"letter_text": "Claim 12345678 was denied."}, Held())
    assert v.ok and any(f.kind == "bare_pmid" for f in v.flags)


def test_prompt_payload_check_catches_an_identifier_handed_to_a_withheld_surface():
    # APPEALS-3 moved the health letter's IDENTIFIER tier to GATE (verified by lookup); the
    # denial-analysis narrative still withholds identifiers, so it carries this check now.
    fs = check_prompt_payload("routers.provider_audit::analyze_denials",
                              {"evidence": "[E1] Peer-reviewed study: MRD detection (2023). PMID 31562796."})
    assert fs and fs[0].reason.startswith("withheld class present in the PROMPT PAYLOAD")


# ---------------------------------------------------------------------------
# NAMED_SOURCE -- Health's appeal_rights failure mode
# ---------------------------------------------------------------------------
def test_relabelled_appeal_right_is_refused_and_the_verbatim_one_binds():
    denial = "You may request Independent external reviews within 4 months."
    v = check("routers.health_analyze::analyze_denial",
              {"appeal_rights": ["ACA independent external review"]}, Held(documents=[_doc(denial)]))
    names = {(f.kind, f.ok) for f in v.findings if f.cls is A.NAMED_SOURCE}
    assert ("aca", False) in names and ("external_review", True) in names, names
    assert not v.ok


def test_regulatory_status_not_in_evidence_is_refused_in_the_health_letter():
    v = check("routers.health_analyze::_generate_appeal_result",
              {"letter_text": "This FDA-approved, NCCN guideline recommended test is standard of care."},
              Held(documents=[_doc("[E1] Peer-reviewed study: circulating tumor DNA in colon cancer (2022).")]))
    kinds = {f.kind for f in v.refusals if f.cls is A.NAMED_SOURCE}
    assert {"fda_status", "nccn", "guideline_status"} <= kinds, kinds


# ---------------------------------------------------------------------------
# FIGURE -- restated and extracted; UNCHECKED when the source has no text layer
# ---------------------------------------------------------------------------
def test_benchmark_narrative_refuses_a_number_the_input_did_not_contain():
    inputs = {"pepm": 512.4, "percentile": 71.2, "gap_annual": 1840.0}
    v = check("routers.employer_benchmark::employer_benchmark",
              {"narrative": "Your PEPM of $512.40 sits at the 71st percentile; peers save $2,600 per employee."},
              Held(inputs=inputs))
    refused = {f.text for f in v.refusals if f.cls is A.FIGURE}
    assert "$2,600" in refused or "2,600" in refused, v.note()
    assert not any(f.text.startswith("512") and f.ok is False for f in v.findings)


def test_benchmark_narrative_binds_at_stated_precision():
    v = check("routers.employer_benchmark::employer_benchmark",
              {"narrative": "PEPM is about $512 at roughly the 71st percentile."},
              Held(inputs={"pepm": 512.4, "percentile": 71.2}))
    assert v.ok, v.note()


def test_fee_schedule_from_an_image_is_unchecked_never_ok_verified():
    v = check("routers.provider_audit::extract_fee_schedule_image",
              {"rates": [{"cpt": "99213", "rate": 95.5}]},
              Held(documents=[_doc("", layer="UNEXTRACTED")]))
    assert v.ok and not v.verified
    assert v.unchecked and "no text layer" in v.unchecked[0].reason
    d = v.to_dict()
    assert d["verified"] is False and d["unchecked"]


def test_fee_schedule_from_text_binds_or_refuses_each_rate():
    src = "99213 Office visit est 95.50\n99214 Office visit est 135.00"
    v = check("routers.provider_audit::extract_fee_schedule_text",
              {"rates": [{"cpt": "99213", "rate": "95.50"}, {"cpt": "99215", "rate": "210.00"}]},
              Held(documents=[_doc(src)]))
    assert not v.ok
    refused = {f.text for f in v.refusals}
    assert "210.00" in refused and "99215" in refused and "95.50" not in refused, refused


# ---------------------------------------------------------------------------
# CODED_DESCRIPTOR
# ---------------------------------------------------------------------------
def test_coded_descriptor_binds_refuses_or_is_unchecked():
    held = Held(tables={"CPT": {"99213": "Office or other outpatient visit, established patient, low complexity"}},
                inputs={"x": 1})
    surf = "routers.provider_audit::analyze_denials"
    ok = check(surf, {"plain_language": "CPT 99213 — office visit, established patient"}, held)
    assert all(f.ok for f in ok.findings if f.cls is A.CODED_DESCRIPTOR)
    bad = check(surf, {"plain_language": "CPT 99213 — colonoscopy with biopsy"}, held)
    assert any(f.cls is A.CODED_DESCRIPTOR and f.ok is False for f in bad.refusals)
    unk = check(surf, {"plain_language": "CPT 45380 — colonoscopy with biopsy"}, held)
    assert any(f.cls is A.CODED_DESCRIPTOR and f.ok is None for f in unk.unchecked)


# ---------------------------------------------------------------------------
# table hygiene
# ---------------------------------------------------------------------------
def test_every_surface_assigns_every_class():
    for k, p in POLICY.items():
        assert set(p.tiers) == set(A), f"{k} does not assign every class"


def test_unknown_surface_is_refused_by_check():
    with pytest.raises(KeyError):
        check("routers.nowhere::nothing", {"x": "y"})
