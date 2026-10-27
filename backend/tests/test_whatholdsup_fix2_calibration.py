"""Fix 2, step 5: an added sentence keeps its source's hedges and grades
(post-study, 2026-10-27). docs/whu-fix2-omission-rulings-design.md, section 2."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import bindings as B    # noqa: E402

SPAN = "Investment in public transport can further support a shift to less intensive modes (high confidence)."


def _row(sentence, span=SPAN, origin=B.OMISSION_ADD):
    return {"sentence": sentence, "source_id": "S003", "span": span, "origin": origin}


def _sev(findings):
    return [(f["check"], B.CALIBRATION_SEVERITY[f["verdict"]]) for f in findings]


def test_an_added_sentence_that_keeps_the_grade_passes():
    r = _row("The assessment finds, with high confidence, that investment in public transport can further "
             "support a shift to less intensive modes.")
    assert B.b25_grade_carried(r) == [] and B.b19_hedge_dropped(r) == []


def test_an_added_sentence_that_drops_the_grade_stops():
    r = _row("The assessment finds that investment in public transport supports a shift to less intensive modes.")
    assert ("B25", B.BAD) in _sev(B.b25_grade_carried(r))


def test_an_added_sentence_that_raises_the_grade_warns():
    r = _row("The assessment finds, with high confidence and robust evidence, that X.",
             span="X is supported (medium evidence, high agreement).")
    got = B.b25_grade_carried(r)
    assert ("B25", B.BAD) in _sev(got)                         # medium evidence dropped
    assert any(f["verdict"] == B.GRADE_RAISED for f in got)    # robust > medium
    assert B.CALIBRATION_SEVERITY[B.GRADE_RAISED] == B.WARN


def test_a_dropped_hedge_stops_an_added_sentence_and_only_warns_otherwise():
    span = "Investment in public transport may support a shift to less intensive modes."
    sent = "Investment in public transport supports a shift to less intensive modes."
    assert _sev(B.b19_hedge_dropped(_row(sent, span))) == [("B19", B.BAD)]
    assert _sev(B.b19_hedge_dropped(_row(sent, span, origin=None))) == [("B19", B.WARN)]


def test_b25_reads_only_added_sentences():
    assert B.b25_grade_carried(_row("Investment supports a shift.", origin=None)) == []
    assert "B25" in B.CALIBRATION_CHECKS


def test_grade_terms_reads_grade_and_ipcc_language():
    t = B.grade_terms("high-certainty evidence (GRADE); (high confidence); medium evidence, high agreement; "
                      "the certainty of the evidence was very low")
    assert t == {"certainty": ["high", "very low"], "confidence": ["high"], "evidence": ["medium"],
                 "agreement": ["high"]}


def test_replay_s07_add_without_its_confidence_term_stops():
    import ruling as R
    import omissions as O
    import source_advocate as SA
    import json
    slug = "urban-form-transport-emissions"
    briefs = sorted((ROOT / "issues").glob("WHU-S07-*/advocate/*-briefs.json"))
    if not briefs:
        pytest.skip("the study's advocate briefs are private and not here")
    held = R.held_texts(slug).get("S003")
    if not held:
        pytest.skip("the held text is not here")
    n, quote = 0, None
    for b in json.loads(briefs[0].read_text()):
        for o in b.get("objections") or []:
            n += 1
            if "%s-%02d" % (b["source"], n) == "S003-13":
                quote = o["source_says"]
    at = O.locate(quote, held)
    finding = held[at[0]:at[1]]
    first = finding.split("). ")[0] + ")."          # its first sentence, with its confidence term
    assert B.grade_terms(first).get("confidence")
    kept = _row("The IPCC finds that " + first[0].lower() + first[1:], span=first)
    dropped = _row("The IPCC finds that " + first.split(" (")[0][0].lower() + first.split(" (")[0][1:] + ".",
                   span=first)
    assert B.b25_grade_carried(kept) == []
    assert ("B25", B.BAD) in _sev(B.b25_grade_carried(dropped))
