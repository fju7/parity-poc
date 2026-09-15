"""Provenance.OPERATOR_SUPPLIED -- a hand-fetched document enters the corpus
without weakening anything (verify/supplied.py).

The operator supplies the DOCUMENT, never the conclusion. Refusals first,
then the pass. Offline: the registry is a table of three real DOIs and their
Crossref titles; the files are built in the test (a text page, a PDF with a
text layer, a PDF with none). publish's storage is redirected to tmp_path.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import sys

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify import literature, generic, publish, supplied  # noqa: E402
from verify.types import Exists, Provenance, Resolution  # noqa: E402

MADSEN = "10.1056/nejmoa021134"
HVIID = "10.7326/m18-2101"
WAKEFIELD = "10.1016/s0140-6736(97)11096-0"
REGISTRY = {
    MADSEN: ("A population-based study of measles, mumps, and rubella vaccination and autism", 2002, "Madsen"),
    HVIID: ("Measles, Mumps, Rubella Vaccination and Autism: A Nationwide Cohort Study", 2019, "Hviid"),
    WAKEFIELD: ("RETRACTED: Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children", 1998, "Wakefield"),
}
MADSEN_TEXT = (
    "A Population-Based Study of Measles, Mumps, and Rubella Vaccination and Autism\n"
    "Kreesten Meldgaard Madsen, Anders Hviid, et al. N Engl J Med 2002;347:1477-1482\n"
    "Background: It has been suggested that vaccination against measles, mumps, and rubella (MMR) is a cause of autism. "
    "Methods: We conducted a retrospective cohort study of all children born in Denmark from January 1991 through December 1998. "
    "Results: Of the 537,303 children in the cohort, 440,655 (82.0 percent) had received the MMR vaccine. "
    "The relative risk of autistic disorder in the group of vaccinated children, as compared with the unvaccinated group, "
    "was 0.92 (95 percent confidence interval, 0.68 to 1.24). Conclusions: This study provides strong evidence against the hypothesis."
)
CLAIM_RIGHT = "The relative risk of autistic disorder in MMR-vaccinated children compared to unvaccinated children was 0.92 (95% CI, 0.68–1.24)."
CLAIM_WRONG = "The relative risk of autistic disorder in MMR-vaccinated children compared to unvaccinated children was 0.92 (95% CI, 0.68–1.26)."


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    """A registry that answers from the table; storage under tmp_path; no machine fetch."""
    def resolve(ident):
        t = REGISTRY.get(ident.value)
        if not t:
            return Resolution(ident, Exists.NONEXISTENT, registry="handle", checked_at="t")
        return Resolution(ident, Exists.EXISTS, heading=t[0], canonical="https://doi.org/" + ident.value, registry="crossref",
                          registry_id=ident.value, checked_at="t", extra={"year": t[1], "first_author": t[2], "published": [t[1]]})
    monkeypatch.setattr(literature, "resolve", resolve)
    monkeypatch.setattr(literature, "fetch", lambda res: None)                       # the machine route gets nothing
    monkeypatch.setattr(generic, "resolve", lambda i: Resolution(i, Exists.UNCHECKED, registry="generic_fetch", extra={"http": 403}))
    monkeypatch.setattr(generic, "fetch", lambda g: None)
    monkeypatch.setattr(publish, "BACKEND", tmp_path)
    monkeypatch.setattr(publish, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(supplied, "BACKEND", tmp_path)
    monkeypatch.setattr(supplied, "SUPPLIED", tmp_path / "supplied")
    monkeypatch.setattr(supplied, "INDEX", tmp_path / "supplied" / "index.json")
    monkeypatch.setattr(publish, "status_check", lambda ident: type("S", (), {"verdict": "unchanged", "registry": "crossref", "detail": "", "checked_at": "t", "events": []})())
    publish._run_cache.clear()
    yield
    publish._run_cache.clear()


def _file(tmp_path, name, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def _pdf(text: str | None) -> bytes:
    """A one-page PDF: with the text drawn (a text layer), or with only a
    filled rectangle (the shape of a scanned image, no text layer)."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    if text is None:
        c.rect(72, 72, 400, 600, fill=1)
    else:
        y = 750
        for line in text.split("\n"):
            for i in range(0, len(line), 95):
                c.drawString(40, y, line[i:i + 95]); y -= 14
    c.showPage(); c.save()
    return buf.getvalue()


# ---------------------------------------------------------------- refusals

def test_refused_the_same_document_offered_under_a_different_doi(tmp_path):
    """The Madsen abstract offered as Wakefield 1998: the registry says what
    that DOI is, and the file is not it. Nothing is stored."""
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    r = supplied.supply(f, "https://example.org/madsen", "Fred Ugast", WAKEFIELD)
    assert not r.admitted and r.status == "REFUSED_HEADING"
    assert "does not match the registry's title" in r.reason and "Ileal-lymphoid" in r.reason
    assert not (tmp_path / "supplied").exists() and not (tmp_path / "docs").exists()   # nothing entered
    assert supplied.lookup(r.identifier) is None


def test_refused_a_same_topic_paper_with_a_similar_title(tmp_path):
    """Madsen 2002 offered as Hviid 2019: five of seven distinctive title words
    are shared (measles, mumps, rubella, vaccination, autism), ratio 0.71,
    under the 0.80 line. And the abstract's "cohort" must not be allowed to
    make up the sixth: only the document's own title lines get the ratio rule,
    the head of the text gets containment only. Pinned so neither drifts."""
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    r = supplied.supply(f, "https://example.org/madsen", "Fred Ugast", HVIID)
    assert not r.admitted and r.status == "REFUSED_HEADING" and "ratio 0.71" in r.reason


def test_refused_when_the_registry_holds_no_such_identifier(tmp_path):
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    r = supplied.supply(f, "https://example.org/madsen", "Fred Ugast", "10.1001/jama.2015.1534")
    assert not r.admitted and r.status == "REFUSED_NONEXISTENT"


def test_refused_when_the_registry_does_not_answer(monkeypatch, tmp_path):
    """No registry title, nothing to check the file against: refused, not
    admitted on the operator's word. Retry when the registry answers."""
    monkeypatch.setattr(literature, "resolve", lambda ident: Resolution(ident, Exists.UNCHECKED, checked_at="t", extra={"registry_unavailable": {"handle": "HTTP 429 after 4 attempts"}}))
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    r = supplied.supply(f, "https://example.org/madsen", "Fred Ugast", MADSEN)
    assert not r.admitted and r.status == "REFUSED_REGISTRY" and "HTTP 429" in r.reason


def test_refused_an_identifier_no_registry_answers_for(tmp_path):
    f = _file(tmp_path, "x.txt", b"anything")
    r = supplied.supply(f, "https://example.org/x", "Fred Ugast", "https://www.gmc-uk.org/some/page")
    assert not r.admitted and r.status == "REFUSED_REGISTRY"


def test_a_pdf_with_no_text_layer_is_unchecked_never_a_pass_and_the_claim_stays_withheld(tmp_path):
    f = _file(tmp_path, "scan.pdf", _pdf(None))
    r = supplied.supply(f, "https://example.org/scan.pdf", "Fred Ugast", MADSEN)
    assert not r.admitted and r.status == "UNCHECKED_NO_TEXT_LAYER"
    assert r.document is not None and r.document.text_layer == "UNEXTRACTED"
    assert r.record["status"] == "UNCHECKED_NO_TEXT_LAYER" and r.record["heading"]["ok"] is None
    assert supplied.lookup(r.identifier) is None                        # recorded as supplied, never as evidence
    row = publish.gate_source({"id": "s1", "title": "Madsen 2002", "url": "https://doi.org/" + MADSEN, "source_type": "journal"})
    assert row["survives"] is False                                     # the claim cannot recover on it


def test_a_document_whose_text_lacks_the_claims_figure_enters_and_figure_refuses(tmp_path):
    """The right paper, hand-fetched, admitted -- and a claim it does not
    support is still withheld. bind is unchanged by provenance."""
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    r = supplied.supply(f, "https://example.org/madsen", "Fred Ugast", MADSEN)
    assert r.admitted
    row = publish.gate_source({"id": "s1", "title": "A Population-Based Study of Measles, Mumps, and Rubella Vaccination and Autism", "url": "https://doi.org/" + MADSEN, "source_type": "journal"})
    assert row["survives"] is True and row["document"]["provenance"] == "OPERATOR_SUPPLIED"
    c = publish.gate_claim({"id": "c1", "claim_text": CLAIM_WRONG, "category": "x"}, [{"claim_id": "c1", "source_id": "s1", "source_context": None}], {"s1": row})
    assert c["support"] == "UNSUPPORTED"
    fig = next(b for b in c["per_source"][0]["bindings"] if b["kind"] == "FIGURE")
    assert fig["ok"] is False and "1.26" in fig["reason"]


# -------------------------------------------------------------------- the pass

def test_a_correct_document_for_a_known_doi_enters_binds_and_the_claim_recovers(tmp_path):
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    r = supplied.supply(f, "https://www.nejm.org/doi/full/10.1056/NEJMoa021134", "Fred Ugast", MADSEN)
    assert r.admitted and r.status == "ADMITTED" and r.heading.ok and not r.heading.abstained
    assert r.sha256 == hashlib.sha256(MADSEN_TEXT.encode()).hexdigest()
    assert r.identifier.provenance is Provenance.OPERATOR_SUPPLIED
    # the supply record
    rec = json.loads((tmp_path / "supplied" / f"{r.sha256}.json").read_text())
    assert rec["provenance"] == "OPERATOR_SUPPLIED" and rec["supplied_by"] == "Fred Ugast"
    assert rec["source_url"].startswith("https://www.nejm.org/") and rec["retrieved_at"] and rec["text_layer"] == "DECLARED_SOUND"
    assert rec["registry_heading"] == REGISTRY[MADSEN][0] and rec["heading"]["ok"] is True
    # the bytes, content-addressed beside the machine-fetched documents
    assert gzip.open(tmp_path / "docs" / r.sha256[:2] / (r.sha256 + ".txt.gz"), "rt").read().startswith("A Population-Based Study")
    # publish uses it only because the machine route got nothing, and says so
    row = publish.gate_source({"id": "s1", "title": "A Population-Based Study of Measles, Mumps, and Rubella Vaccination and Autism", "url": "https://doi.org/" + MADSEN, "source_type": "journal"})
    assert row["survives"] is True
    assert row["document"]["provenance"] == "OPERATOR_SUPPLIED" and row["document"]["supplied_by"] == "Fred Ugast"
    assert row["document"]["sha256"] == r.sha256 and row["document"]["route"] == "operator_supplied"
    assert row["resolution"]["fallback"]["route"] == "operator_supplied" and row["resolution"]["fallback"]["sha256"] == r.sha256
    c = publish.gate_claim({"id": "c1", "claim_text": CLAIM_RIGHT, "category": "x"}, [{"claim_id": "c1", "source_id": "s1", "source_context": None}], {"s1": row})
    assert c["support"] == "FIGURE_BOUND"


def test_a_pdf_with_a_text_layer_is_admitted_the_same_way(tmp_path):
    f = _file(tmp_path, "madsen.pdf", _pdf(MADSEN_TEXT))
    r = supplied.supply(f, "https://www.nejm.org/doi/pdf/10.1056/NEJMoa021134", "Fred Ugast", MADSEN)
    assert r.admitted, r.reason
    assert r.record["text_layer"] == "DECLARED_SOUND" and r.record["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()
    row = publish.gate_source({"id": "s1", "title": "A Population-Based Study of Measles, Mumps, and Rubella Vaccination and Autism", "url": "https://doi.org/" + MADSEN, "source_type": "journal"})
    c = publish.gate_claim({"id": "c1", "claim_text": CLAIM_RIGHT, "category": "x"}, [{"claim_id": "c1", "source_id": "s1", "source_context": None}], {"s1": row})
    assert c["support"] == "FIGURE_BOUND" and row["document"]["provenance"] == "OPERATOR_SUPPLIED"


def test_a_machine_fetch_is_preferred_and_is_marked_machine(monkeypatch, tmp_path):
    """The supplied copy is the last route, never the first."""
    from verify.types import Document, Identifier
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    assert supplied.supply(f, "https://example.org/madsen", "Fred Ugast", MADSEN).admitted
    machine = Document(Identifier("doi", MADSEN), "m" * 64, MADSEN_TEXT, "text/plain", "t", None, "europepmc_abstract", "abstract")
    monkeypatch.setattr(literature, "fetch", lambda res: machine)
    row = publish.gate_source({"id": "s1", "title": "A Population-Based Study of Measles, Mumps, and Rubella Vaccination and Autism", "url": "https://doi.org/" + MADSEN, "source_type": "journal"})
    assert row["document"]["provenance"] == "MACHINE_FETCH" and row["document"]["route"] == "europepmc_abstract" and "fallback" not in row["resolution"]


def test_check_mode_stores_nothing(tmp_path):
    f = _file(tmp_path, "madsen.txt", MADSEN_TEXT.encode())
    r = supplied.supply(f, "https://example.org/madsen", "Fred Ugast", MADSEN, store=False)
    assert r.admitted and not (tmp_path / "supplied").exists() and supplied.lookup(r.identifier) is None
