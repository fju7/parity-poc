"""Honest appeal letter: show ALL appeal addresses labeled (never auto-select),
truthful enclosure language (provider docs submitted separately), and appeal
rights faithful to the denial.

The letter body is model-generated, so the prose behavior is verified end-to-end
in the UI/live check. These deterministic offline tests guard what we CAN assert:
the alt_address resolver mapping and the prompt-content instructions.
"""

import os
import sys

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import _resolve_placeholder, APPEAL_SYSTEM_PROMPT  # noqa: E402


# -- Task 1.2: alt_address resolver (ADDED; existing .address mapping intact) --
def test_alt_address_resolver_added_primary_unchanged():
    da = {"appeal_submission": {"address": "eviCore, PO Box 5620",
                                "alt_address": "Cigna NAO, PO Box 188011"}}
    assert _resolve_placeholder("appeal address", da) == "eviCore, PO Box 5620"        # unchanged
    assert _resolve_placeholder("mailing address", da) == "eviCore, PO Box 5620"        # unchanged
    assert _resolve_placeholder("alternate appeal address", da) == "Cigna NAO, PO Box 188011"
    assert _resolve_placeholder("secondary appeal address", da) == "Cigna NAO, PO Box 188011"
    # No alt_address present -> None (never falls back to the primary).
    assert _resolve_placeholder("alternate appeal address", {"appeal_submission": {"address": "A"}}) is None


# -- Task 1.1: prompt presents ALL addresses, labeled, and never picks one --
def test_prompt_shows_all_addresses_never_selects():
    p = APPEAL_SYSTEM_PROMPT
    assert "appeal_submission.address and appeal_submission.alt_address" in p
    assert "Do NOT choose a single address on the patient's behalf" in p
    assert "send your appeal to both addresses" in p
    assert "do NOT omit any address the denial provided" in p


# -- Task 2: honest enclosure / supporting-documentation language --
def test_prompt_honest_enclosure_language():
    p = APPEAL_SYSTEM_PROMPT
    assert "Handle supporting documentation HONESTLY" in p
    assert "Never claim to enclose" in p
    assert "do NOT claim to physically enclose journal articles or PDFs" in p
    assert "already on file with the insurer" in p
    assert "submitted SEPARATELY by the ordering provider" in p
    assert "__CLAIM_NUMBER__" in p          # provider separate submission references the claim number


# -- Task 3: appeal-rights faithful to the denial, no plan-type logic --
def test_prompt_appeal_rights_faithful():
    p = APPEAL_SYSTEM_PROMPT
    assert "State the patient's appeal rights using ONLY the rights and external-review options named in the denial analysis" in p
    assert "do not invent rights" in p
    assert "Do not characterize which rights apply based on the patient's plan type." in p
