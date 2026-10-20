"""Enclosing quote marks around a quotation are not part of it (2026-10-20).

A reader or the source advocate often wraps what it quotes in quote marks the
document does not carry. The verbatim check removes a pair ENCLOSING the
quotation and nothing else; the interior must still match exactly.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("audit_stage_qm_t", WHU / "audit_stage.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

DOC = "Background. Each 10% increment in intake was associated with a 12% higher risk. More text."


@pytest.mark.parametrize("q,ok", [
    ('"Each 10% increment in intake was associated with a 12% higher risk."', True),
    ("“Each 10% increment in intake was associated with a 12% higher risk.”", True),
    ("'Each 10% increment in intake'", True),
    ('"\'Each 10% increment in intake\'"', True),                       # nested pair
    ('"Each 10% increment in intake was associated with a 15% higher risk."', False),  # interior differs
    ('"Each 10% increment in intake was linked to a 12% higher risk."', False),        # paraphrase
    ('"Each 10% increment in intake', False),                           # an unpaired mark is not removed
    ('""', False),
])
def test_enclosing_quote_marks_are_removed_and_the_interior_must_match(q, ok):
    assert A.quoted_in(q, DOC) is ok


def test_the_audit_verbatim_check_accepts_an_enclosed_quotation():
    v = {"verdict": "holds", "evidence": [{"source": "S1", "quote": '"associated with a 12% higher risk"'}]}
    assert A.bad_quotes(v, {"S1": DOC}, {}, None) == []
    v["evidence"][0]["quote"] = '"associated with a 13% higher risk"'
    assert len(A.bad_quotes(v, {"S1": DOC}, {}, None)) == 1


def test_the_real_cases_s004_08_and_s010_14():
    """WHU-P02's advocate quotations, only where the private files exist."""
    import ruling as R
    # The 2026-10-20 briefs: in place, or moved aside by the clean re-run's
    # supersession (advocate/superseded/, each brief stamped, order kept), or
    # in the private archive. All private; none is committed.
    adv = WHU.parents[2] / "issues" / "WHU-P02-ultra-processed-foods" / "advocate"
    arch = Path.home() / "Projects" / "whu-study-private" / "WHU-P02-ultra-processed-foods"
    found = ([adv / "2026-10-20-briefs.json"] + sorted(adv.glob("superseded/*-2026-10-20-briefs.json")) +
             sorted(arch.glob("*/issues/WHU-P02-ultra-processed-foods/advocate/2026-10-20-briefs.json")))
    case = next((c for c in found if c.exists()), None)
    if case is None:
        pytest.skip("WHU-P02's advocate briefs are not here")
    items, n = {}, 0
    for b in json.loads(case.read_text()):
        for o in b.get("objections") or []:
            n += 1
            items["%s-%02d" % (b["source"], n)] = (b["source"], o.get("source_says") or "")
    held = R.held_texts("ultra-processed-foods")
    for head in ("S004-08", "S010-14"):
        sid, says = items[head]
        if sid not in held:
            pytest.skip("%s is not held here" % sid)
        assert A.norm(says) not in A.norm(held[sid])        # as written, with its quote marks: not found
        assert R._in_held(says, held[sid])                  # its interior: word for word in the source
