"""PH: de-identify the four direct patient identifiers before the model call, and
re-identify them server-side after generation.

Deterministic, offline: no live model, no network, no DB. Uses the same sentinel
identifier values as the search PHI-leak test.
"""

import json
import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import (  # noqa: E402
    _deidentify_for_model,
    _validate_letter,
    IDENTIFIER_TOKENS,
)

SENTINELS = {
    "patient_name": "Jane A. Doe",
    "member_id": "MEMBER-TEST-001",
    "claim_number": "CLAIM-TEST-0340U",
    "patient_address": "123 Main St, Wesley Chapel, FL 33543",
}


def _da():
    # Include non-identifier fields that must survive to the model unchanged.
    return {
        **SENTINELS,
        "patient_diagnosis": "stage 3 colon cancer",
        "state": "FL",
        "payer_name": "Cigna",
        "cpt_codes": ["0340U"],
    }


# 6.1 — NO-LEAK (critical): none of the four real values reach the model; tokens do.
def test_no_identifier_leaks_to_model():
    da_model, _ = _deidentify_for_model(_da())
    blob = json.dumps(da_model)
    for field, real in SENTINELS.items():
        assert real not in blob, f"real {field} leaked into model payload"
    for token in IDENTIFIER_TOKENS.values():
        assert token in blob, f"token {token} missing from model payload"
    # Non-identifier fields still present for the model.
    assert "stage 3 colon cancer" in blob and "Cigna" in blob and "FL" in blob


# 6.2 — SIDE-DOOR: an identifier embedded in a free-text field is scrubbed too.
def test_side_door_scrub_in_free_text():
    da = _da()
    da["weakness"] = "The denial for Jane A. Doe (MEMBER-TEST-001) is not supported."
    da_model, _ = _deidentify_for_model(da)
    assert "Jane A. Doe" not in da_model["weakness"]
    assert "MEMBER-TEST-001" not in da_model["weakness"]
    assert "__PATIENT_NAME__" in da_model["weakness"]
    assert "__MEMBER_ID__" in da_model["weakness"]


# 6.3 — REAL da UNTOUCHED: only a copy is de-identified.
def test_real_da_untouched():
    da = _da()
    da["weakness"] = "The denial for Jane A. Doe is weak."
    _deidentify_for_model(da)
    assert da["patient_name"] == "Jane A. Doe"
    assert da["member_id"] == "MEMBER-TEST-001"
    assert da["claim_number"] == "CLAIM-TEST-0340U"
    assert da["patient_address"] == "123 Main St, Wesley Chapel, FL 33543"
    assert da["weakness"] == "The denial for Jane A. Doe is weak."   # free-text unchanged too


# 6.4 — ROUND-TRIP: tokens in a letter are restored to real values, none left.
def test_round_trip_restores_real_values():
    da = _da()
    letter = ("__LETTER_DATE__\n"
              "RE: Appeal of Claim __CLAIM_NUMBER__, Member ID __MEMBER_ID__\n"
              "__PATIENT_NAME__\n__PATIENT_ADDRESS__\n\n"
              "Submitted on behalf of __PATIENT_NAME__.")
    out = _validate_letter(letter, da)["letter_text"]
    for real in SENTINELS.values():
        assert real in out
    for token in IDENTIFIER_TOKENS.values():
        assert token not in out          # no literal token remains


# 6.5 — EMPTY FIELD: an absent identifier leaves no literal token visible.
def test_empty_identifier_leaves_no_token():
    da = _da()
    da["member_id"] = None               # absent / empty
    letter = "Member ID: __MEMBER_ID__\n__PATIENT_NAME__"
    out = _validate_letter(letter, da)["letter_text"]
    assert "__MEMBER_ID__" not in out    # token gone even though value was empty
    assert "Jane A. Doe" in out          # present identifier still restored
