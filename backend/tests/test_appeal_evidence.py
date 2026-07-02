"""
PH-4a — evidence-into-letter integration tests.

Deterministic suite (default, offline — NO network, NO DB, NO model call):
  * code-built reference block (stable keys, FDA-specific indication, guideline
    rendered reference-only);
  * the anti-fabrication citation guard (THE load-bearing safety gate);
  * reviewer checklist + gap surfacing.
Live eval (@pytest.mark.eval): full generate_appeal end-to-end on the Signatera
fixture (extraction -> retrieve_evidence live -> letter -> guard), asserting the
letter cites only real evidence with no raw citation detail in the prose.

Deterministic: python3 -m pytest backend/tests/test_appeal_evidence.py -v
Eval:          python3 -m pytest backend/tests/test_appeal_evidence.py -m eval -v -s
"""

import json
import os
import sys

import pytest

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import (  # noqa: E402
    _build_evidence_block,
    _format_reference,
    _validate_evidence_claims,
    _build_reviewer_checklist,
    _validate_letter,
    generate_appeal,
    AppealGenerateRequest,
)

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_FIX = os.path.join(_REPO, "test-data", "appeals", "signatera_cigna")


def _pack():
    with open(os.path.join(_FIX, "expected_evidence.json")) as f:
        return json.load(f)


def _denial():
    with open(os.path.join(_FIX, "expected_extraction.json")) as f:
        return json.load(f)


# ===========================================================================
# Deterministic — code-built reference block (Task 2)
# ===========================================================================

class TestEvidenceBlock:
    def test_stable_e_keying_pubmed_then_cms_then_fda(self):
        ev = _build_evidence_block(_pack())
        keys = list(ev["keys"].keys())
        assert keys == [f"E{i}" for i in range(1, len(keys) + 1)]   # E1..En contiguous
        assert ev["keys"]["E1"]["source"] == "pubmed"              # pubmed first
        assert ev["keys"][keys[-1]]["source"] == "fda"            # fda last

    def test_fda_reference_states_specific_indication(self):
        ev = _build_evidence_block(_pack())
        fda_item = next(it for it in ev["keys"].values() if it["source"] == "fda")
        low = _format_reference(fda_item).lower()
        assert "muscle" in low and "bladder" in low            # specific indication, not bare "FDA-approved"
        assert "atezolizumab" in low
        # the reference names the indication, not a bare "FDA-approved" with no scope
        assert "companion diagnostic" in low

    def test_guideline_rendered_reference_only(self):
        ev = _build_evidence_block(_pack())
        g_key = next(k for k, it in ev["keys"].items() if it.get("study_type") == "guideline")
        ref = _format_reference(ev["keys"][g_key]).lower()
        assert "pmid" in ref and "pubmed" in ref                 # reference form
        # No expanded recommendation text (only title/journal/year/url are stored).
        for word in ("recommend", "first-line", "should receive", "we suggest"):
            assert word not in ref

    def test_cms_reference_has_policy_id_and_title(self):
        ev = _build_evidence_block(_pack())
        cms_key = next(k for k, it in ev["keys"].items() if it["source"] in ("cms_moldx", "cms_ncd_lcd"))
        ref = _format_reference(ev["keys"][cms_key])
        assert ref.startswith("CMS ")
        assert ev["keys"][cms_key]["source_uid"] in ref          # states the specific doc id


# ===========================================================================
# Deterministic — anti-fabrication guard (Task 5) — CRITICAL
# ===========================================================================

class TestAntiFabricationGuard:
    KEYS = {"E1": {}, "E2": {}, "E3": {}}

    def test_valid_keys_no_raw_citations_ok(self):
        letter = ("We rely on peer-reviewed support [E1] and Medicare coverage [E3]. "
                  "The assay is analytically validated.")
        r = _validate_evidence_claims(letter, self.KEYS)
        assert r["citations_ok"] is True
        assert r["hard_failures"] == []
        assert r["used_keys"] == ["E1", "E3"]

    def test_unknown_key_hard_fail(self):
        r = _validate_evidence_claims("As shown [E9], the test is valid.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("unknown evidence key E9" in f for f in r["hard_failures"])

    def test_bare_pmid_hard_fail(self):
        r = _validate_evidence_claims("See PMID 12345678 for evidence.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("PubMed ID" in f for f in r["hard_failures"])

    def test_pma_number_hard_fail(self):
        r = _validate_evidence_claims("The device (P260004) is approved.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("PMA" in f for f in r["hard_failures"])

    def test_doi_hard_fail(self):
        r = _validate_evidence_claims("Per doi 10.1200/JCO.22.01690 the data is clear.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("DOI" in f for f in r["hard_failures"])

    def test_et_al_hard_fail(self):
        r = _validate_evidence_claims("Nakamura et al. reported durable responses.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("et al" in f.lower() for f in r["hard_failures"])

    def test_statistic_is_soft_flag_not_hard_fail(self):
        letter = "The approach improved detection by 42% in the study population."
        r = _validate_evidence_claims(letter, self.KEYS)
        assert r["citations_ok"] is True                          # NOT a hard fail
        assert r["hard_failures"] == []
        assert any(fl["figure"] == "42%" for fl in r["review_flags"])
        assert any("42%" in fl["sentence"] for fl in r["review_flags"])


# ===========================================================================
# Deterministic — reviewer checklist + gaps (Task 6)
# ===========================================================================

class TestReviewerChecklist:
    def test_status_always_draft_and_missing_icd_action(self):
        pack = _pack()
        assert _denial()["icd_codes"] == []                      # Signatera fixture has no ICD
        ev = _build_evidence_block(pack)
        val = _validate_evidence_claims("Support [E11] applies.", ev["keys"])
        checklist = _build_reviewer_checklist(ev, val)
        assert checklist["status"] == "draft — human review required before sending"
        # missing-ICD gap surfaced as an actionable regenerate prompt
        assert any(i["type"] == "gap" and "No diagnosis (ICD) code was provided" in i["action"]
                   and "regenerate" in i["action"] for i in checklist["items"])
        # cited item carries key + one-line reference + stated indication + confirm prompt
        cited = [i for i in checklist["items"] if i["type"] == "confirm_indication"]
        assert cited and cited[0]["key"] == "E11"
        assert "muscle" in (cited[0]["reference"] or "").lower()
        assert "matches the patient's diagnosis" in cited[0]["prompt"]

    def test_soft_flag_becomes_verify_item(self):
        ev = _build_evidence_block(_pack())
        val = _validate_evidence_claims("Detection improved 42% overall.", ev["keys"])
        checklist = _build_reviewer_checklist(ev, val)
        assert any(i["type"] == "verify_statistic" and i["figure"] == "42%" for i in checklist["items"])


# ===========================================================================
# Deterministic — PH-1 validator still passes unchanged (Task 7)
# ===========================================================================

class TestPh1Unchanged:
    def test_letter_date_token_still_stamps(self):
        da = _denial()
        out = _validate_letter("__LETTER_DATE__\n\nDear Appeals,", da)
        assert "__LETTER_DATE__" not in out["letter_text"]
        assert any(e.get("action") == "stamped" for e in out["validation_log"])

    def test_no_bracket_placeholders_leak(self):
        da = _denial()
        out = _validate_letter("[Patient Name]\n[Claim Number]\n__LETTER_DATE__", da)
        import re
        assert not re.search(r"\[[^\]]+\]", out["letter_text"])


# ===========================================================================
# Live eval (marked) — full generate_appeal end-to-end on the Signatera fixture
# ===========================================================================

@pytest.mark.eval
def test_live_appeal_generation_eval():
    """extraction fixture -> retrieve_evidence (live) -> letter -> guard.
    Asserts the letter cites only real evidence with no raw citation detail in
    the prose, and surfaces the missing-ICD gap. Prints letter + checklist."""
    da = _denial()
    req = AppealGenerateRequest(denial_analysis=da)
    result = generate_appeal(req)

    letter = result["letter_text"]
    ev_val = result["evidence_validation"]
    checklist = result["reviewer_checklist"]

    # Split the trusted References section from the model-written body.
    if "\nReferences\n" in letter:
        body, references = letter.split("\nReferences\n", 1)
    else:
        body, references = letter, ""

    # 1) No hard failures — the guard passed on the body.
    assert ev_val["citations_ok"] is True, ev_val["hard_failures"]

    # 2) Every [E#] used maps to a retrieved item.
    #    (rebuild the pack keys the same way generate_appeal did)
    import re
    used = re.findall(r"\[(E\d+)\]", body)
    # references section must list the retrieved items with indications
    assert references, "References section should be appended"
    assert ("muscle" in references.lower() and "bladder" in references.lower()), \
        "FDA reference must state its specific indication"

    # 3) No raw citation detail invented in the prose.
    assert not re.search(r"(?<!\d)\d{7,8}(?!\d)", body), "bare PMID in body"
    assert not re.search(r"\bP\d{6}\b", body), "PMA number in body"
    assert not re.search(r"\b10\.\d{4,}/\S+", body), "DOI in body"
    assert not re.search(r"\bet al\.", body, re.I), "'et al.' in body"

    # 4) Checklist carries the missing-ICD gap and the mandatory draft status.
    assert checklist["status"] == "draft — human review required before sending"
    assert any("No diagnosis (ICD) code was provided" in i.get("action", "")
               for i in checklist["items"] if i["type"] == "gap")

    print("\n================= GENERATED LETTER =================\n")
    print(letter)
    print("\n================= REVIEWER CHECKLIST =================\n")
    print(json.dumps(checklist, indent=2))
    print("\n================= EVIDENCE VALIDATION =================\n")
    print(json.dumps({k: v for k, v in ev_val.items()}, indent=2))
    print(f"\nused [E#] keys in body: {used}")
    print(f"needs_revision: {result['needs_revision']}  status: {result['status']}")
