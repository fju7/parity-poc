"""Phase 2: the allow-list and the inverted gate.

Starts empty and must behave exactly like the blocklist while it is. A
reviewed row makes its provision citable -- and only for sentences whose
numbers are in the provision's text. Replayed from the recorded fixtures.

Run: python3 -m pytest backend/tests/verify/test_allowlist.py -q
"""
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("VERIFY_CACHE_DIR", str(Path(__file__).parent / "fixtures" / "http"))
from verify import http  # noqa: E402
http.CACHE_DIR = Path(os.environ["VERIFY_CACHE_DIR"])
from verify import allowlist  # noqa: E402
from utils.citation_gate import check_letter  # noqa: E402

LETTER_CITING_381 = ("Under Ohio Revised Code § 3901.381, a third-party payer shall pay or deny a clean claim "
                     "not later than thirty days after receipt. We demand reprocessing within that period.")
LETTER_CITING_381_WRONG_NUMBER = ("Under Ohio Revised Code § 3901.381, a clean claim must be paid within ninety days. "
                                  "We demand reprocessing.")
LETTER_CITING_38 = "Under Ohio Revised Code § 3901.38, clean claims must be paid within thirty days."


def test_every_row_today_is_a_draft_so_every_allowlist_is_empty():
    rows = json.loads(allowlist.CANDIDATES.read_text())["rows"]
    assert rows and all(r["reviewed_by"] is None for r in rows)
    for r in rows:
        allowed, _ = allowlist.build(r["state"], r["payer_type"], r["denial_code"])
        assert allowed == []


def test_empty_allowlist_is_the_blocklist():
    assert [c.text for c in check_letter(LETTER_CITING_381, [])] == ["Revised Code § 3901.381"]
    assert [c.text for c in check_letter(LETTER_CITING_381, None)] == ["Revised Code § 3901.381"]


def test_every_draft_row_would_bind_if_reviewed():
    """A row that could not bind should not be sitting in the table unflagged."""
    rows = json.loads(allowlist.CANDIDATES.read_text())["rows"]
    seen = set()
    for r in rows:
        key = (r["state"], r["payer_type"], r["denial_code"])
        if key in seen:
            continue
        seen.add(key)
        allowed, rejected = allowlist.build(*key, include_drafts=True)
        assert not rejected, [(x.row["cite"], x.reason) for x in rejected]
        assert allowed


def test_a_reviewed_row_admits_its_provision_and_only_for_true_numbers():
    allowed, rejected = allowlist.build("OH", "commercial", "CO-16", include_drafts=True)
    assert allowed and not rejected
    assert check_letter(LETTER_CITING_381, allowed) == []
    bad = check_letter(LETTER_CITING_381_WRONG_NUMBER, allowed)
    assert len(bad) == 1 and "not in the document: 90" in bad[0].text
    # A different section of the same chapter is not on the list.
    assert [c.text for c in check_letter(LETTER_CITING_38, allowed)] == ["Revised Code § 3901.38"]


def test_prompt_injection_path_is_gone():
    """APPEALS-3 (2026-09-17): no statutory text reaches a model from the allow-list, and no
    letter surface imports the module."""
    assert not hasattr(allowlist, "prompt_block")
    import routers.provider_appeals as pa
    assert not hasattr(pa, "build_allowlist") and not hasattr(pa, "prompt_block")
    src = open(pa.__file__, encoding="utf-8").read()
    assert "PERMITTED CITATIONS" not in src


def test_an_unsupported_state_gets_nothing():
    allowed, rejected = allowlist.build("TX", "commercial", "CO-16", include_drafts=True)
    assert allowed == [] and rejected == []
