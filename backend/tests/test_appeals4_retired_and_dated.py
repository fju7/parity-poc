"""APPEALS-4 (2026-09-19): the gates that ship with the removals.

ITEM 2  appeal_strength is retired from the provider appeal: the prompt does not
        ask for it, the router does not store or return it, and nothing renders it.
        (The Signal denial-playbook's same-named strong/moderate/weak field is a
        different subsystem and is out of this gate's scope.)
ITEM 3  the provider letter's date is the date the letter is produced, from one
        source, in both the letter body (the __LETTER_DATE__ token) and the PDF.
ITEM 1  the provider prompt no longer instructs the model to say a document is
        attached; enclosure claims are refused at the response boundary.
ITEM 4  a coded descriptor the model supplied that binds to nothing held does not
        pass the provider gate as an asserted descriptor.

These tests read the source and the policy table, not a model, so they hold
without a network and would have FAILED against the pre-removal code (shown in the
APPEALS-4 report).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

PROVIDER = BACKEND / "routers" / "provider_appeals.py"
FRONTEND = [ROOT / "frontend" / "src" / "ProviderApp.jsx",
            ROOT / "frontend" / "src" / "components" / "ProviderAuditReport.jsx"]


def _code_lines(path: Path) -> str:
    """Source with comment lines dropped, so a comment recording the retirement
    cannot satisfy a gate meant for code."""
    keep = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("{/*") or stripped.startswith("*"):
            continue
        keep.append(line)
    return "\n".join(keep)


# ---------------------------------------------------------------- ITEM 2
def test_provider_prompt_does_not_ask_for_appeal_strength():
    from routers.provider_appeals import APPEAL_SYSTEM_PROMPT
    assert "appeal_strength" not in APPEAL_SYSTEM_PROMPT
    assert "high|medium|low" not in APPEAL_SYSTEM_PROMPT


def test_provider_router_neither_stores_nor_returns_appeal_strength():
    src = _code_lines(PROVIDER)
    assert "appeal_strength" not in src, "provider_appeals.py still reads or writes appeal_strength"


def test_nothing_in_the_provider_ui_renders_appeal_strength():
    for f in FRONTEND:
        src = _code_lines(f)
        assert "appeal_strength" not in src, f"{f.name} still renders appeal_strength"
        assert "Appeal Strength" not in src, f"{f.name} still renders an Appeal Strength badge"


# ---------------------------------------------------------------- ITEM 3
def test_provider_prompt_uses_the_letter_date_token():
    from routers.provider_appeals import APPEAL_SYSTEM_PROMPT, _LETTER_DATE_TOKEN
    assert _LETTER_DATE_TOKEN == "__LETTER_DATE__"
    assert APPEAL_SYSTEM_PROMPT.count(_LETTER_DATE_TOKEN) >= 1
    header = APPEAL_SYSTEM_PROMPT.split("HEADER BLOCK")[1].split("2. OPENING")[0]
    assert "Date: __LETTER_DATE__" in header, "the letterhead date line is the token"
    assert "Never write the date of service, or any other date, as the letter's date" in header


def test_letter_date_is_stamped_from_one_local_source_in_text_and_html():
    from routers import provider_appeals as pa
    result = {"letter_text": "__LETTER_DATE__\n\nRE: Appeal", "letter_html": "<p>Date: __LETTER_DATE__</p>"}
    today = pa._stamp_letter_date(result)
    assert re.fullmatch(r"[A-Z][a-z]+ \d{1,2}, \d{4}", today)
    assert "__LETTER_DATE__" not in result["letter_text"] and "__LETTER_DATE__" not in result["letter_html"]
    assert today in result["letter_text"] and today in result["letter_html"]
    assert result["letter_date"] == today


def test_pdf_does_not_read_its_own_clock():
    src = PROVIDER.read_text()
    body = src.split("def _generate_appeal_pdf(", 1)[1].split("\ndef ", 1)[0]
    assert "datetime.now(" not in body and "date.today(" not in body, \
        "the PDF must print the letter_date it is handed, not the server clock"
    assert "letter_date" in body.split(")", 1)[0], "_generate_appeal_pdf must take letter_date"


# ---------------------------------------------------------------- ITEM 1
def test_provider_prompt_does_not_instruct_attached():
    from routers.provider_appeals import APPEAL_SYSTEM_PROMPT
    low = APPEAL_SYSTEM_PROMPT.lower()
    assert "say it is attached" not in low
    assert "-- attached, or already on the claim" not in low
    for phrase in ("attach_documentation",):
        assert phrase in low   # the practice's own list survives; the letter's claim does not


def test_enclosure_claims_are_refused_on_both_letter_surfaces():
    from verify.extract import AssertionClass
    from verify.policy import POLICY, Tier, check, held_for_prompt
    for surface in ("routers.provider_appeals::_gated_letter", "routers.health_analyze::_generate_appeal_result"):
        assert POLICY[surface].tiers[AssertionClass.ENCLOSURE] is Tier.GATE, surface
    held = held_for_prompt("system", {})
    v = check("routers.provider_appeals::_gated_letter",
              {"letter_text": "The operative note is attached. Please find enclosed the EOB.", "letter_html": "", "cms_references": [], "attach_documentation": "operative note"},
              held)
    kinds = sorted(f.kind for f in v.refusals if f.cls is AssertionClass.ENCLOSURE)
    assert kinds == ["attached", "find_included"], kinds
    ok = check("routers.provider_appeals::_gated_letter",
               {"letter_text": "The operative note in the practice's record for the date of service records the separate site; the claim is on file with the payer.",
                "letter_html": "", "cms_references": [], "attach_documentation": "operative note"},
               held)
    assert not [f for f in ok.refusals if f.cls is AssertionClass.ENCLOSURE]


# ---------------------------------------------------------------- ITEM 4
def test_unchecked_coded_descriptor_does_not_pass_the_provider_gate():
    from routers import provider_appeals as pa
    from verify.policy import check, held_for_prompt
    held = held_for_prompt(pa.APPEAL_SYSTEM_PROMPT, {"cpt_code": "99214"})
    v = check(pa.SURFACE, {"letter_text": "This appeal concerns CPT 99214 (office visit, established patient, moderate complexity).",
                           "letter_html": "", "cms_references": [], "attach_documentation": ""}, held)
    assert v.evidence_verified, "precondition: the policy verdict itself leaves an unbound descriptor UNCHECKED"
    assert not pa._descriptors_verified(v), "an unbound descriptor must not pass as asserted"
    clean = check(pa.SURFACE, {"letter_text": "This appeal concerns CPT 99214.", "letter_html": "", "cms_references": [], "attach_documentation": ""}, held)
    assert pa._descriptors_verified(clean)
