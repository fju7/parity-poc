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
    assert not r.admitted and r.status == "REFUSED_HEADING" and "Nationwide Cohort Study" in r.reason
    # the title line alone scores 0.71 (5 of 7); the head of the text, where the
    # abstract's "cohort" lives, scores 0.86 -- and the head gets containment only
    assert "ratio 0.86" in r.reason


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


# ------------------------------------------------ permanent negative controls
# Two real documents Fred fetched by hand on 2026-09-15 that support nothing on
# mmr-vaccine-autism. Better than a synthetic wrong document: they fail the
# way a wrong document fails in practice.
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "supplied")
WARNER = os.path.join(FIXTURES, "warner-v-hhs-20-225V-fees-2024-01-23.pdf")
D1678 = os.path.join(FIXTURES, "bmj-d1678-correction-2011-03-15.pdf")
LANCET_RETRACTION = "10.1016/s0140-6736(10)60175-4"
GODLEE = "10.1136/bmj.c7452"
REGISTRY[LANCET_RETRACTION] = ("Retraction—Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children", 2010, "The Editors of The Lancet")
REGISTRY[GODLEE] = ("Wakefield's article linking MMR vaccine and autism was fraudulent", 2011, "Godlee")


def test_negative_control_warner_v_hhs_is_a_real_court_decision_that_matches_no_claim():
    """Warner v HHS, No. 20-225V, Special Master Horner, decision on attorneys'
    fees, filed 2024-01-23: the right court (Court of Federal Claims, Office of
    Special Masters), vaccines, autism in passing -- and nothing to do with the
    Omnibus Autism Proceeding or Cedillo. Offered for the Lancet retraction's
    DOI it is refused on HEADING; offered for what it is, there is no registry."""
    r = supplied.supply(WARNER, "https://www.govinfo.gov/", "Fred Ugast", LANCET_RETRACTION, store=False)
    assert not r.admitted and r.status == "REFUSED_HEADING" and "Ileal-lymphoid" in r.reason
    assert "20-225V" in r.document.text if r.document else True
    r2 = supplied.supply(WARNER, "https://www.govinfo.gov/", "Fred Ugast", "No. 20-225V", store=False)
    assert not r2.admitted and r2.status == "REFUSED_REGISTRY"


def test_negative_control_bmj_d1678_is_the_correction_not_the_editorial():
    """bmj.d1678 (15 March 2011) is the BMJ's competing-interests correction
    to Godlee's editorial c7452 and carries the editorial's exact title. A
    title check alone admits it as the editorial; the document's own head
    says doi: 10.1136/bmj.d1678, and that refuses it. 'elaborate fraud' is
    not in it, so even admitted it would have bound nothing."""
    r = supplied.supply(D1678, "https://www.bmj.com/content/342/bmj.d1678", "Fred Ugast", GODLEE, store=False)
    assert not r.admitted and r.status == "REFUSED_HEADING"
    assert "names a different DOI as its own" in r.reason and "10.1136/bmj.d1678" in r.reason
    from verify.law import _pdftotext
    assert "elaborate fraud" not in (_pdftotext(open(D1678, "rb").read()) or "")


def test_a_single_quoted_span_binds_and_a_possessive_does_not():
    from verify.bind import bind_span, _QUOTE
    from verify.types import Document, Identifier
    claim = "The BMJ formally characterized the 1998 Lancet paper by Wakefield as 'an elaborate fraud' in an editorial by editor Fiona Godlee."
    assert [m.group(1) or m.group(2) for m in _QUOTE.finditer(claim)] == ["an elaborate fraud"]
    assert not _QUOTE.search("Wakefield's data alterations in the 1998 Lancet paper included changing the children's diagnoses.")
    doc = Document(Identifier("doi", GODLEE), "", "science, to show that the paper was in fact an elaborate fraud.")
    assert bind_span(claim, doc).ok
    assert not bind_span(claim, Document(Identifier("doi", GODLEE), "", "the paper was a fraud.")).ok


def test_refused_a_same_topic_paper_as_a_wrapped_pdf(tmp_path):
    """The PDF form of the near-miss: pdftotext wraps the abstract into short
    lines; a wrapped abstract line joined to its neighbour would carry six of
    Hviid's seven title words. Sentence lines are never title candidates."""
    f = _file(tmp_path, "madsen.pdf", _pdf(MADSEN_TEXT))
    r = supplied.supply(f, "https://example.org/madsen.pdf", "Fred Ugast", HVIID)
    assert not r.admitted and r.status == "REFUSED_HEADING", r.reason


def test_a_browser_print_with_page_chrome_above_a_wrapped_title_is_admitted(tmp_path):
    """The Lancet notice as printed from a browser on 2026-09-15: three lines
    of chrome, then the title wrapped over two lines. Refused at first (ratio
    0.75 against the first 200 characters); the wrapped pair is the title."""
    text = ("LeapSpace\nSearch for...\nCOMMENT ∙ Volume 375, Issue 9713, P445, February 06, 2010\nDownload Full Issue\n"
            "Retraction—Ileal-lymphoid-nodular hyperplasia, non-specific colitis,\nand pervasive developmental disorder in children\n"
            "The Editors of The Lancet a\nAffiliations & Notes\n"
            "Following the judgment of the UK General Medical Council's Fitness to Practise Panel on Jan 28, 2010, it has become clear that several elements of the 1998 paper by Wakefield et al are incorrect.")
    f = _file(tmp_path, "notice.txt", text.encode())
    r = supplied.supply(f, "https://www.thelancet.com/", "Fred Ugast", LANCET_RETRACTION, store=False)
    assert r.admitted, r.reason
