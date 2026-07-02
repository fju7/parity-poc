"""Appeal letter: require a focused clinical-management-impact argument (the core of
rebutting an Experimental/Investigational/Unproven denial), paired with a guard against
fabricating this patient's specific clinical facts that applies on BOTH the evidence and
no-evidence paths (i.e. it lives in the always-present base system prompt).

Deterministic prompt-content assertions only. No live model, network, or DB.
"""

import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import (  # noqa: E402
    APPEAL_SYSTEM_PROMPT,
    APPEAL_EVIDENCE_INSTRUCTIONS,
)


# -- Task 1: the treatment-impact / clinical-management requirement is in the base prompt --
def test_base_prompt_requires_clinical_management_impact_argument():
    p = APPEAL_SYSTEM_PROMPT
    assert "focused argument on clinical management impact" in p
    assert '"experimental, investigational, or unproven" (EIU) grounds' in p
    assert "will change or inform the patient's clinical management" in p
    # frames to the provided diagnosis (not fabricated), at the test-class level
    assert "frame this argument in the context of that condition" in p
    assert "what this class of test does and the diagnosis you were actually given" in p


# -- Task 2.1: the fabrication guard is in the ALWAYS-PRESENT base prompt (both paths) --
def test_fabrication_guard_is_in_always_present_base_prompt():
    # Asserted against the base constant directly, NOT the evidence-appended version,
    # so it applies whether or not retrieved evidence exists.
    p = APPEAL_SYSTEM_PROMPT
    assert "do NOT fabricate this patient's specific clinical facts" in p
    assert "the exact management decision at stake" in p
    assert "Do NOT state as fact any specific prior treatment, response, staging detail, or management decision that is not given in the denial analysis" in p
    # It must NOT be dependent on the evidence block being appended: the guard text is
    # present in the base prompt itself, independent of APPEAL_EVIDENCE_INSTRUCTIONS.
    assert "do NOT fabricate this patient's specific clinical facts" not in APPEAL_EVIDENCE_INSTRUCTIONS


# -- Task 1.2: the guard reinforces (does not contradict) enclosure honesty by deferring
#    patient-specific detail to the provider's SEPARATELY submitted medical-necessity letter --
def test_guard_defers_specifics_to_providers_separate_letter():
    p = APPEAL_SYSTEM_PROMPT
    assert "the ordering provider's separately submitted letter of medical necessity will document the specific clinical rationale" in p
    assert "defers patient-specific specifics to the provider" in p
    # consistent with the existing enclosure-honesty rule
    assert "submitted SEPARATELY by the ordering provider" in p


# -- Task 2.2: the evidence-block indication discipline is unchanged and still present --
def test_evidence_block_indication_discipline_unchanged():
    e = APPEAL_EVIDENCE_INSTRUCTIONS
    assert "Argue the general validity of the test, and do not fabricate a diagnosis-specific link." in e
    assert "do NOT claim the studies are specific to the patient's condition" in e


# -- Task 3.1: preserved honesty rules still present (representative checks) --
def test_preserved_honesty_rules_intact():
    p = APPEAL_SYSTEM_PROMPT
    assert "The patient reserves all other appeal and external-review rights available under applicable federal and state law." in p
    assert "Never assume the provider is a physician." in p
    assert 'never turn "72 hours" into "3 days"' in p
    assert "Use __LETTER_DATE__ exactly once" in p
    assert "Never claim to enclose, attach, or submit-herewith" in p
    assert "Do not use em-dashes" in p


# -- Task 3.2: the ADDED requirement/guard text itself contains no em/en dashes --
def test_added_text_has_no_em_or_en_dashes():
    p = APPEAL_SYSTEM_PROMPT
    # Isolate the two added bullets (between the requirement start and the enclosure bullet).
    start = p.index("- Include a focused argument on clinical management impact.")
    end = p.index("- Handle supporting documentation HONESTLY.")
    added = p[start:end]
    assert "focused argument on clinical management impact" in added  # sanity: region captured
    assert "—" not in added and "–" not in added
