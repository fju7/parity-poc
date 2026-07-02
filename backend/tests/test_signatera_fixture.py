"""
PH-2 — Signatera baseline eval harness.

Two layers:
  * Deterministic suite (default, CI-safe, NO model call): exercises the PH-1-B
    pre-generation validators and the PH-1-C letter validator directly.
  * Live extraction eval (@pytest.mark.eval, on-demand): calls the deployed
    analyze-denial extraction and scores each locked field against the fixture,
    isolating model drift from CI.

Fixture: test-data/appeals/signatera_cigna/
Deterministic run: python3 -m pytest backend/tests/test_signatera_fixture.py -v
Eval run:          python3 -m pytest backend/tests/test_signatera_fixture.py -m eval -v -s
"""

import json
import os
import re
import sys
import urllib.request

import pytest

# Deployed API for the live eval; override with CIVICSCALE_API_URL. Kept self-contained
# (no conftest dependency) so the eval is reproducible in a clean checkout.
_API_BASE = os.environ.get("CIVICSCALE_API_URL", "https://parity-poc-api.onrender.com")

# Make backend/ importable so `routers...` resolves regardless of invocation dir.
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import (  # noqa: E402
    _apply_pregen_validators,
    _validate_letter,
    _today_local,
    _ACTION_REQUIRED_SIGNATURE,
)

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_FIX = os.path.join(_REPO, "test-data", "appeals", "signatera_cigna")

# Pinned production extraction model (see health_analyze.py analyze_denial).
PROD_MODEL = "claude-sonnet-4-6"

# Structured extraction fields locked for scoring (free-text fields excluded).
LOCKED_FIELDS = [
    "cpt_codes", "icd_codes", "denial_category", "pre_service",
    "carc_rarc_code", "payer_guideline_id", "billed_amount",
    "deadline_days_expedited", "deadline_days_standard",
    "peer_to_peer_contact", "state",
]


def _load_expected():
    with open(os.path.join(_FIX, "expected_extraction.json")) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Deterministic — PH-1-B pre-generation validators
# ---------------------------------------------------------------------------

class TestPregenValidators:
    def test_claim_number_not_denial_or_guideline(self):
        da = _load_expected()
        da["claim_number"] = da["payer_guideline_id"]  # the classic PH-1 bug
        _apply_pregen_validators(da)
        assert da["claim_number"] != da["payer_guideline_id"]
        assert da["claim_number"] != (da.get("denial_reason_code") or da.get("carc_rarc_code"))

    def test_valid_claim_number_preserved(self):
        da = _load_expected()
        da["claim_number"] = "CLAIM-TEST-0340U"
        _apply_pregen_validators(da)
        assert da["claim_number"] == "CLAIM-TEST-0340U"

    def test_cpt_codes_deduplicated(self):
        da = _load_expected()
        da["cpt_codes"] = ["0340U", "0340U"]
        _apply_pregen_validators(da)
        assert da["cpt_codes"] == ["0340U"]

    def test_state_derived_from_address(self):
        da = _load_expected()
        da["state"] = None
        da["patient_address"] = "123 Main St, Wesley Chapel, FL 33543"
        _apply_pregen_validators(da)
        assert da["state"] == "FL"


# ---------------------------------------------------------------------------
# Deterministic — PH-1-C letter validator
# ---------------------------------------------------------------------------

class TestValidateLetter:
    def test_letter_date_token_and_bracket(self):
        da = _load_expected()
        letter = ("__LETTER_DATE__\n\nInvoice dated [Date].\n"
                  "We reference your denial dated June 22, 2026.")
        out = _validate_letter(letter, da)
        today = _today_local()
        assert out["letter_text"].split("\n")[0] == today            # token -> today (local tz)
        assert f"dated {today}" in out["letter_text"]                # [Date] -> today
        assert "denial dated June 22, 2026" in out["letter_text"]    # mid-sentence date preserved
        assert any(e.get("action") == "stamped" and e.get("value") == today
                   for e in out["validation_log"])

    def test_letter_date_fallback_when_token_absent(self):
        da = _load_expected()
        letter = ("June 22, 2026\n\nDear Appeals,\n"
                  "We reference your denial dated June 22, 2026.")
        out = _validate_letter(letter, da)
        today = _today_local()
        assert out["letter_text"].split("\n")[0] == today            # solely-date line stamped
        assert "denial dated June 22, 2026" in out["letter_text"]    # mid-sentence date preserved

    def test_signature_named_when_patient_known(self):
        da = _load_expected()
        out = _validate_letter("Sincerely,\n[Signature]", da)
        assert f"Submitted on behalf of {da['patient_name']}" in out["letter_text"]
        assert not re.search(r"\[[^\]]+\]", out["letter_text"])

    def test_must_have_no_data_shows_action_required(self):
        da = _load_expected()
        da["patient_name"] = None  # must-have signature with no data
        out = _validate_letter("Sincerely,\n[Advocate/Provider Name and Title]", da)
        assert _ACTION_REQUIRED_SIGNATURE in out["letter_text"]                 # visible marker
        assert "[Advocate/Provider Name and Title]" not in out["letter_text"]   # NOT silently removed
        assert any(e.get("action") == "action_required" for e in out["validation_log"])

    def test_nonessential_missing_placeholder_line_removed(self):
        da = _load_expected()
        da["date_of_service"] = None
        letter = "Service date: [Date of Service]\nKeep me."
        out = _validate_letter(letter, da)
        assert "[Date of Service]" not in out["letter_text"]
        assert "Service date:" not in out["letter_text"]  # whole sentence/line removed
        assert "Keep me." in out["letter_text"]

    def test_no_leaked_brackets_for_available_fields(self):
        da = _load_expected()
        letter = ("[Patient Name]\n[Address]\n[Claim Number]\n"
                  "[Cigna/EviCore Mailing Address]\n__LETTER_DATE__")
        out = _validate_letter(letter, da)
        assert not re.search(r"\[[^\]]+\]", out["letter_text"])

    def test_validation_log_has_no_phi_values(self):
        da = _load_expected()
        letter = ("[Patient Name]\n[Address]\n[Member ID]\n[Claim Number]\n"
                  "Sincerely,\n[Signature]\n__LETTER_DATE__")
        out = _validate_letter(letter, da)
        blob = json.dumps(out["validation_log"])
        for field in ("patient_name", "patient_address", "member_id", "claim_number"):
            val = da.get(field)
            if val:
                assert val not in blob, f"PHI value for {field} leaked into validation_log"


# ---------------------------------------------------------------------------
# Live extraction eval (marked; excluded from default runs)
# ---------------------------------------------------------------------------

@pytest.mark.eval
def test_live_extraction_eval():
    """Score the deployed analyze-denial extraction against the locked fixture.

    Self-contained (stdlib urllib, no conftest dependency) so it is reproducible in a
    clean checkout; override the target with CIVICSCALE_API_URL. Prints a per-field
    pass/fail table and asserts a perfect score on the locked (structured) fields.
    Free-text/cosmetic fields are intentionally not scored.
    """
    raw = open(os.path.join(_FIX, "denial_source.txt")).read()
    denial_text = raw.split("---\nNOTE (fixture)")[0].strip()

    req = urllib.request.Request(
        _API_BASE + "/api/health/analyze-denial",
        data=json.dumps({"text": denial_text}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        ext = json.loads(resp.read().decode())
    expected = _load_expected()

    def matched(field):
        if field == "appeal_submission.fax":
            return (ext.get("appeal_submission") or {}).get("fax") == "866-889-8061"
        if field == "procedure_terms~Signatera":
            return "signatera" in [str(x).strip().lower() for x in (ext.get("procedure_terms") or [])]
        return ext.get(field) == expected.get(field)

    def got_value(field):
        if field == "appeal_submission.fax":
            return (ext.get("appeal_submission") or {}).get("fax")
        if field == "procedure_terms~Signatera":
            return ext.get("procedure_terms")
        return ext.get(field)

    fields = LOCKED_FIELDS + ["appeal_submission.fax", "procedure_terms~Signatera"]
    results = {f: matched(f) for f in fields}
    n_match = sum(1 for v in results.values() if v)
    score = n_match / len(fields)

    print(f"\n[eval] Signatera extraction score = {n_match}/{len(fields)} = {score:.2f}  "
          f"(model={PROD_MODEL})")
    print(f"  {'field':<26} {'result':<7} got")
    for f in fields:
        print(f"  {f:<26} {'PASS' if results[f] else 'FAIL':<7} {json.dumps(got_value(f))}")

    failures = [f for f in fields if not results[f]]
    assert score == 1.0, f"locked-field score {score:.2f} < 1.0; failing fields: {failures}"
