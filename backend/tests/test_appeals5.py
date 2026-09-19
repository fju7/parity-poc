"""APPEALS-5 (2026-09-19): the gates that ship with the rename and the record.

ITEM 1  signal_denial_playbook's claim-count band is named for what it measures; the old name
        must not return in the writer, the reader or the response.
ALSO    the enclosure rule is exercised through the PRODUCTION call paths (_gated_letter and
        _generate_appeal_result), not only the extractor.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests" / "verify"))


def _code(path: Path) -> str:
    return "\n".join(l for l in path.read_text().splitlines() if not l.strip().startswith(("#", "--")))


def test_signal_playbook_field_is_named_for_what_it_measures():
    for f in ("routers/signal_intelligence.py", "routers/provider_audit.py"):
        src = _code(BACKEND / f)
        assert "appeal_strength" not in src, f"{f}: the old name is back"
    src = _code(BACKEND / "routers/signal_intelligence.py")
    assert "signal_claim_count_band" in src and "challenging_claim_count" in src and "high_score_challenging_count" in src
    for band in ("0_claims", "1_2_claims", "3_plus_claims"):
        assert band in src
    mig = (BACKEND / "migrations/093_signal_denial_playbook_claim_count_band.sql").read_text()
    assert "RENAME COLUMN appeal_strength TO signal_claim_count_band" in mig and "LEFT UNAPPLIED" in mig


def test_retired_letter_grade_column_is_commented_not_dropped():
    mig = (BACKEND / "migrations/094_provider_appeals_appeal_strength_retired_comment.sql").read_text()
    assert "COMMENT ON COLUMN public.provider_appeals.appeal_strength" in mig
    assert "DROP" not in mig.upper().replace("NOT DROPPED", "").replace("NO DROP", "") and "LEFT UNAPPLIED" in mig


# ---- production call paths for the enclosure rule ------------------------------------------
_DATA = json.dumps({"claim_id": "C1", "denial_code": "CO-16", "cpt_code": "99213", "billed_amount": 120.0,
                    "payer_name": "Aetna", "date_of_service": "2025-01-05", "practice_name": "P",
                    "practice_address": "1 Main St, Columbus, OH 43215", "billing_contact": "B", "npi": "1234567890",
                    "patient_name": "X", "contracted_rate_info": None})


def test_provider_gated_letter_refuses_an_enclosure_claim_on_both_drafts(monkeypatch):
    import routers.provider_appeals as pa
    calls = []
    def fake(**kw):
        calls.append(kw["user_content"])
        return {"letter_text": "Dear Payer, this is a first-level appeal of Claim C1 under CO-16. The operative note is attached. "
                               "We ask that the claim be reprocessed and $120.00 paid. Please respond by 30 calendar days from the date of this letter.",
                "letter_html": "<p>x</p>", "attach_documentation": "operative note", "cms_references": []}
    monkeypatch.setattr(pa, "_call_claude", fake)
    assert pa._gated_letter(_DATA) is None                 # refused twice -> no letter
    assert len(calls) == 2 and "enclosed or attached" in calls[1]   # the regeneration named the rule


def test_provider_gated_letter_passes_a_document_named_as_in_the_record(monkeypatch):
    import routers.provider_appeals as pa
    monkeypatch.setattr(pa, "_call_claude", lambda **kw: {
        "letter_text": "Dear Payer, this is a first-level appeal of Claim C1 under CO-16. The information the denial lists as missing "
                       "is on the corrected claim as submitted, and the claim can be adjudicated with it. We ask that the claim be "
                       "reprocessed and $120.00 paid. Please respond by 30 calendar days from the date of this letter.",
        "letter_html": "<p>x</p>", "attach_documentation": "corrected claim", "cms_references": []})
    out = pa._gated_letter(_DATA)
    assert out and out["verification"]["ok"]


def test_health_generate_appeal_result_refuses_an_enclosure_claim(monkeypatch):
    from test_policy_wiring import _health_stub, _req
    h = _health_stub(monkeypatch, "__LETTER_DATE__\n\nDear Cigna,\n\nThe patient appeals the denial under policy MOL.CU.117 "
                                  "of the Signatera test (0340U), billed at $3,500. Please find enclosed the ordering provider's "
                                  "letter of medical necessity.\n\nSincerely,\n__PATIENT_NAME__")
    out = h._generate_appeal_result(_req(h))
    assert out["needs_revision"] and out["sendable"] is False
    assert "find_included" in {f["kind"] for f in out["verification"]["refused"]}


def test_no_code_file_uses_the_name_appeal_strength():
    """APPEALS-6 ITEM 4: the NAME must not return anywhere in code. Migrations (history) and the
    retired-fields register are the only places it may appear. Comments are stripped;
    `appeal_strength_reason` (also retired) is caught as well."""
    import re
    rx = re.compile(r"\bappeal_strength\b")
    roots = [BACKEND / "routers", BACKEND / "verify", BACKEND / "scripts", BACKEND / "utils", ROOT / "frontend" / "src"]
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.suffix not in (".py", ".js", ".jsx", ".ts", ".tsx") or "node_modules" in f.parts or "venv" in f.parts:
                continue
            for n, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                code = line.split("#", 1)[0] if f.suffix == ".py" else line.split("//", 1)[0]
                if rx.search(code):
                    hits.append(f"{f.relative_to(ROOT)}:{n}")
    assert not hits, "the retired name is back in code: " + ", ".join(hits)
