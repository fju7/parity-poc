"""SUBJECT_BOUND -- the binding that was missing (verify/subject.py).

Refusals first. Then the discovering test: every claim of the frozen record,
re-levelled offline through gate_claim, has a SUBJECT binding on every
surviving link, and the level follows the binding both ways -- so the check
cannot silently skip a claim. Then the 24 claims the operator withheld by hand
on 2026-09-15, put through the gate with the register switched off: SUBJECT
must refuse every one without being told about any of them.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify import publish as P, relevel as R  # noqa: E402
from verify.subject import bind_subject, extract_terms, named_terms  # noqa: E402
from verify.types import Document, Identifier  # noqa: E402

NOTICE = Document(Identifier("doi", "10.1016/s0140-6736(10)60175-4"), "", (
    "Retraction—Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children. "
    "Following the judgment of the UK General Medical Council's Fitness to Practise Panel on Jan 28, 2010, it has become clear that "
    "several elements of the 1998 paper by Wakefield et al are incorrect, contrary to the findings of an earlier investigation. In "
    "particular, the claims in the original paper that children were \"consecutively referred\" and that investigations were \"approved\" "
    "by the local ethics committee have been proven to be false. Therefore we fully retract this paper from the published record."))
SRC = {"retraction", "ileal", "lymphoid", "nodular", "hyperplasia", "colitis", "pervasive", "developmental", "disorder", "children", "lancet"}
TOPIC = {"autism", "vaccine", "mmr", "found", "between", "cohort"}
SUBJECT = {"autism", "vaccine"}


# ---------------------------------------------------------------- refusals

def test_refuses_the_claim_the_operator_found_on_the_live_page():
    claim = ("The UK General Medical Council found that the Wakefield et al. research involved undisclosed financial conflicts of interest, "
             "ethical violations in the treatment of child subjects (including invasive procedures without ethical approval), data manipulation, "
             "and dishonesty — constituting serious professional misconduct.")
    b = bind_subject(claim, NOTICE, SRC, TOPIC, subject_terms=SUBJECT)
    assert not b.ok
    for w in ("financial", "manipulation", "dishonesty"):
        assert w in b.reason, b.reason


def test_refuses_when_the_document_never_mentions_the_subject():
    ema = Document(Identifier("url", "ema"), "", "M-M-RVaxPro | European Medicines Agency. Marketing authorisation. EPAR. CHMP. " * 40)
    b = bind_subject("The EMA's EPAR notes that the original Wakefield hypothesis was not substantiated by subsequent epidemiological studies of autism.",
                     ema, {"european", "medicines", "agency", "vaxpro"}, TOPIC, subject_terms=SUBJECT)
    assert not b.ok and b.reason.startswith("the document never mentions the claim's subject: autism")


def test_refuses_a_named_body_the_document_does_not_mention():
    b = bind_subject("The Institute of Medicine concluded that the retraction was warranted.", NOTICE, SRC, TOPIC, subject_terms=SUBJECT)
    assert not b.ok and "Institute Medicine" in b.reason


def test_refuses_a_prose_quantity_the_document_does_not_carry():
    b = bind_subject("The retraction rested on millions of records across multiple countries.", NOTICE, SRC, TOPIC, subject_terms=SUBJECT)
    assert not b.ok and "millions" in b.reason and "multiple" in b.reason


def test_refuses_a_distinguishing_word_absent_from_the_document():
    freq = {"preterm": 1, "weight": 2}
    hviid = Document(Identifier("doi", "10.7326/m18-2101"), "", "Nationwide cohort study. Subgroups defined according to sibling history of autism and autism risk factors. MMR vaccination does not increase the risk for autism.")
    b = bind_subject("The Danish cohort study found no increased risk of autism in children with siblings with autism, preterm birth, or low birth weight.",
                     hviid, {"measles", "mumps", "rubella", "vaccination", "autism", "nationwide", "cohort"}, TOPIC, claim_frequency=freq, subject_terms=SUBJECT)
    assert not b.ok and "preterm" in b.reason


def test_half_of_a_two_word_assertion_is_not_a_match():
    b = bind_subject("The retraction removed the primary published basis for the MMR-autism hypothesis.", NOTICE, SRC, TOPIC, subject_terms=SUBJECT)
    assert not b.ok and "basis" in b.reason


def test_unchecked_text_layer_is_never_a_pass():
    scan = Document(Identifier("url", "x"), "", "", text_layer="UNEXTRACTED")
    assert not bind_subject("Anything at all about autism.", scan, set(), TOPIC, subject_terms=SUBJECT).ok


# ------------------------------------------------------------------- passes

def test_binds_when_the_claims_terms_are_in_the_text():
    b = bind_subject("The Lancet fully retracted the Wakefield paper after the General Medical Council panel's judgment found its ethics approval claim false.",
                     NOTICE, SRC, TOPIC, subject_terms=SUBJECT)
    assert b.ok, b.reason


def test_a_claim_that_restates_its_sources_own_subject_binds():
    doc = Document(Identifier("doi", "x"), "", "Measles, mumps, and rubella vaccination and bowel problems or developmental regression in children with autism: population study. No association was found.")
    b = bind_subject("The Taylor et al. (2002) study found no association between MMR vaccination and developmental regression in children with autism.",
                     doc, {"measles", "mumps", "rubella", "vaccination", "bowel", "problems", "developmental", "regression", "children", "autism", "taylor"}, TOPIC, subject_terms=SUBJECT)
    assert b.ok, b.reason


def test_named_terms_are_phrases_minus_the_furniture():
    assert named_terms("The UK General Medical Council found that the Wakefield et al. research was flawed.") == ["General Medical Council", "Wakefield"]
    assert named_terms("The CDC's Advisory Committee on Immunization Practices (ACIP) concluded, citing the IOM's conclusion.") == ["CDC Advisory Committee Immunization Practices", "ACIP", "IOM"]
    assert "MMR-autism" not in named_terms("The MMR-autism hypothesis was advanced by Wakefield.")
    t = extract_terms("Anti-vaccine advocates conflated concerns about thimerosal with the separate MMR-autism hypothesis advanced by Wakefield.", set(), TOPIC, {"conflated": 1, "advocates": 1})
    assert "Wakefield" in t["named"] and {"conflated", "advocates"} <= set(t["distinguishing"])


# ------------------------------------------- the discovering test, both ways

REC = Path(BACKEND) / "data" / "verify" / "published" / "mmr-vaccine-autism" / "latest.json"


@pytest.fixture(scope="module")
def relevelled():
    rec = json.loads(REC.read_text())
    return rec, R.relevel(rec)


def test_every_claim_is_levelled_by_subject_and_the_level_follows_the_binding(relevelled):
    rec, new = relevelled
    assert len(new) == len(rec["claims"]) == 128
    for c in new:
        if c.get("withheld_reason", "").startswith("OPERATOR_WITHHELD"):
            continue
        surviving = [p for p in c["per_source"] if p.get("source_survives") and p.get("level") is not None]
        for p in surviving:
            kinds = [b["kind"] for b in p["bindings"]]
            if any(b["kind"] == "CHRONOLOGY" and not b["ok"] for b in p["bindings"]) or any(b["kind"] == "STATUS_AT_PUBLISH" and not b["ok"] for b in p["bindings"]) \
                    or any(b["kind"] == "ERRATUM" and not b["ok"] for b in p["bindings"]):
                continue                                   # refused before SUBJECT ran: nothing to level
            assert "SUBJECT" in kinds, (c["claim_id"], p["source_id"], kinds)   # one way: no link escapes the check
            subj = next(b for b in p["bindings"] if b["kind"] == "SUBJECT")
            if p["level"] == "SUBJECT_BOUND":
                assert subj["ok"] and not any(b["kind"] in ("FIGURE", "SPAN") and b["ok"] for b in p["bindings"])
            if p["level"] == "IDENTITY_ONLY":
                assert not subj["ok"], (c["claim_id"], p["source_id"])    # the other way: a passing SUBJECT never leaves IDENTITY_ONLY
        assert (c["support"] in P.SHOWN) == bool(c["supported_by"])


def test_identity_only_is_not_a_shown_state(relevelled):
    rec, new = relevelled
    row = P.publication_row({**rec, "claims": new})
    shown = set(row["supported_claim_ids"])
    for c in new:
        assert (c["claim_id"] in shown) == (c["support"] in P.SHOWN)
        if c["support"] == "IDENTITY_ONLY":
            assert c["claim_id"] not in shown


def test_the_24_operator_withholds_are_refused_by_subject_unaided():
    """The test of the check: the claims a person withheld by reading, put
    through the gate with the register switched off. None may be shown."""
    rec = json.loads(REC.read_text())
    reg = json.loads(P.WITHHELD_CLAIMS.read_text())["claims"]
    assert len(reg) >= 24
    new = {c["claim_id"]: c for c in R.relevel(rec, without_register=True)}
    shown = [k for k in reg if new[k]["support"] in P.SHOWN]
    assert shown == [], [(k[:8], new[k]["support"]) for k in shown]
    for k in reg:
        assert not new[k].get("withheld_reason", "").startswith("OPERATOR_WITHHELD")   # the register really was off


def test_the_stored_record_was_produced_by_the_subject_gate():
    """Fails until the next republish carries SUBJECT; skipped only while the
    record is one that predates the binding, and says so."""
    rec = json.loads(REC.read_text())
    if "SUBJECT" not in (rec.get("gate_version") or {}).get("bindings", []):
        pytest.skip(f"record {rec['publish_id']} predates SUBJECT; republish to close this")
    for c in rec["claims"]:
        if c.get("withheld_reason", "").startswith("OPERATOR_WITHHELD"):
            continue
        for p in c["per_source"]:
            if p.get("level") not in (None, "UNSUPPORTED"):
                assert any(b["kind"] == "SUBJECT" for b in p["bindings"]), (c["claim_id"], p["source_id"])
        assert c["support"] != "IDENTITY_ONLY" or c["claim_id"] not in set(P.publication_row(rec)["supported_claim_ids"])
