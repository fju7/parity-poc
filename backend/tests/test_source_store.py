"""We hold the document, or we do not say we read it.

On 2026-09-01 the ledger for issue two read: 24 sources, 3 opened by a person,
8 resting on nothing but "whatever the search tool returned for this URL". All
three that had been opened were opened by the operator, and every one produced
a correction. The read rate and the error rate were the same number.

There was no store. Every role did its own retrieval, took a fragment, used it
and discarded it; the next role searched again. A fragment cannot be re-read,
cannot be diffed against next year's version, and cannot tell you what it did
NOT contain -- which is how the Shaaban paper's own "29 blocks with block size
of four" was deleted from the page as our arithmetic.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    sp = importlib.util.spec_from_file_location(
        name, ROOT / "backend" / "scripts" / "whatholdsup" / (name + ".py"))
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


store = _load("source_store")
ledger = _load("source_ledger")


@pytest.fixture
def issue(tmp_path, monkeypatch):
    case = tmp_path / "issues" / "WHU-999-t"
    case.mkdir(parents=True)
    (case / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "url": "https://example.org/a",
         "title": "Ribociclib overall survival MONALEESA trial",
         "access": {"state": "fragment_only"}},
        {"id": "S002", "url": "https://example.org/b",
         "title": "Palbociclib letrozole PALOMA advanced breast cancer",
         "access": {"state": "full_text_held"}},
    ]}), encoding="utf-8")
    monkeypatch.setattr(store, "CASES", tmp_path / "issues")
    monkeypatch.setattr(store, "LIB", tmp_path / "library")
    return tmp_path


# --- the states -------------------------------------------------------------

def test_fragment_only_is_not_a_read_state():
    """The whole change. machine_read sat in READ_STATES and licensed
    characterisation and adverse claims on the evidence that a URL had once
    appeared in a gate report's citation list."""
    assert ledger.FRAGMENT_ONLY not in ledger.READ_STATES
    assert ledger.FULL_TEXT_HELD in ledger.READ_STATES
    assert ledger.HUMAN_READ in ledger.READ_STATES
    assert "machine_read" not in ledger.STATES


def test_fragment_only_licenses_no_characterisation():
    permit = ledger.PERMITS[ledger.FRAGMENT_ONLY]
    assert "NO characterisation" in permit
    assert "nobody holds the document" in permit


# --- the store --------------------------------------------------------------

def test_a_stored_document_is_hashed_and_findable(issue):
    row = store.put("t", "S002", b"%PDF-1.4 hello", url="https://example.org/b",
                    via="test", content_type="application/pdf")
    assert row["file"].startswith("docs/")
    assert row["sha256"] == hashlib.sha256(b"%PDF-1.4 hello").hexdigest()
    assert store.held("t")["S002"]["bytes"] == 14
    intact, broken = store.verify("t")
    assert intact == ["S002"] and not broken


def test_a_manifest_row_whose_bytes_changed_is_reported(issue):
    store.put("t", "S002", b"%PDF-1.4 hello", url="u", via="v",
              content_type="application/pdf")
    (store.LIB / store.held("t")["S002"]["file"]).write_bytes(b"%PDF-1.4 tampered")
    _intact, broken = store.verify("t")
    assert broken and "does not match its recorded hash" in broken[0]


def test_a_manifest_row_with_no_file_is_reported(issue):
    store.put("t", "S002", b"%PDF-1.4 hello", url="u", via="v",
              content_type="application/pdf")
    (store.LIB / store.held("t")["S002"]["file"]).unlink()
    _intact, broken = store.verify("t")
    assert broken and "is not in the library" in broken[0]


def test_claiming_full_text_held_without_the_bytes_blocks(issue):
    """A field asserting a read that did not happen -- one level up from the
    failure the state was created to end."""
    rows = {n: (s, d) for n, s, d in store.preflight_rows("t")}
    state, detail = rows["library matches the ledger"]
    assert state == "BLOCKED"
    assert "S002" in detail and "did not happen" in detail


def test_it_passes_once_the_document_is_actually_held(issue):
    store.put("t", "S002", b"%PDF-1.4 hello", url="u", via="v",
              content_type="application/pdf")
    rows = {n: (s, d) for n, s, d in store.preflight_rows("t")}
    assert rows["library matches the ledger"][0] == "ok"
    assert "1 of 2" in rows["sources we hold"][1]
    assert "S001" in rows["sources that are only a fragment"][1]


# --- what acquisition must refuse ------------------------------------------

SRC = {"id": "S002", "url": "https://doi.org/10.1056/NEJMoa1607303",
       "title": "Palbociclib letrozole PALOMA advanced breast cancer"}


def test_a_document_is_accepted_because_it_identifies_itself():
    body = ("<html><body>%s Palbociclib and letrozole in PALOMA-2, advanced breast "
            "cancer</body>" % ("x" * 3000)).encode()
    ok, why = store.identifies(body, SRC, "text/html")
    assert ok and "title words" in why


def test_a_cookie_wall_is_refused_although_no_blocklist_names_it():
    """This is the case that got through. Within an hour of a blocklist being
    written, acquisition stored two PubMed cookie-consent pages as full text and
    promoted both to full_text_held, because "cookies required" was not a phrase
    anyone had been caught by yet. A blocklist can only refuse what has already
    gone wrong once."""
    wall = ("<html><body>%s This site requires cookies to continue. Please enable "
            "cookies in your browser.</body>" % ("x" * 3000)).encode()
    ok, why = store.identifies(wall, SRC, "text/html")
    assert not ok
    assert "identifies" in why


def test_an_identifier_alone_is_enough():
    body = b"<html><body>" + b"x" * 3000 + b" NCT01740427 " + b"</body>"
    ok, why = store.identifies(body, {"id": "S", "url": "", "title": "",
                                      "also_called": ["NCT01740427"]}, "text/html")
    assert ok and "NCT01740427" in why


def test_a_tiny_response_is_never_a_document():
    assert not store.identifies(b"nope", SRC, "text/html")[0]


def test_an_unreadable_pdf_says_so_rather_than_calling_it_wrong():
    """Refusing a real document is the safer error and is still an error. The
    first version of this test rejected two genuine FDA labels reporting
    "1 of 4 title words", because a PDF's text is compressed."""
    fake = b"%PDF-1.4" + bytes(4000)
    ok, why = store.identifies(fake, SRC, "application/pdf")
    assert not ok
    assert "could not be checked either way" in why


def test_a_new_format_is_also_held_not_superseded(issue):
    """Conflating them destroys the reason for keeping old bytes at all.

    The Shaaban paper arrived twice on 2026-09-01 -- Europe PMC full-text XML
    from acquisition, and the published PDF the operator supplied. The first
    version of this recorded the XML as superseded BY the PDF. They are the same
    paper in two representations, and a later diff of one against the other
    would report that everything had changed: worse than useless, misleading on
    exactly the question the history exists to answer.
    """
    store.put("t", "S002", b"<xml>" + b"x" * 3000 + b"Palbociclib letrozole PALOMA</xml>",
              url="u1", via="v", content_type="text/xml")
    store.put("t", "S002", b"%PDF-1.4" + b"x" * 3000, url="u2", via="v",
              content_type="application/pdf")
    row = store.held("t")["S002"]
    assert row["file"].endswith(".pdf")
    assert len(row["also_held"]) == 1 and row["also_held"][0]["file"].endswith(".xml")
    assert row["superseded"] == []


def test_the_same_format_with_different_bytes_is_superseded(issue):
    """A corrected paper, a new guideline version, a registry record updated
    after we published. That is a real diff and a real changelog event."""
    store.put("t", "S002", b"%PDF-1.4" + b"a" * 3000, url="u", via="v",
              content_type="application/pdf")
    first = store.held("t")["S002"]["sha256"]
    store.put("t", "S002", b"%PDF-1.4" + b"b" * 3000, url="u", via="v",
              content_type="application/pdf")
    row = store.held("t")["S002"]
    assert row["sha256"] != first
    assert [v["sha256"] for v in row["superseded"]] == [first]
    assert row["also_held"] == []
    # and the old bytes are still there to diff against
    assert (store.LIB / row["superseded"][0]["file"]).exists()


def test_pdftotext_is_found_where_PATH_will_not_look(monkeypatch, tmp_path):
    """launchd starts jobs with a minimal PATH that excludes /opt/homebrew/bin.

    shutil.which() then returns nothing on a Mac where poppler is installed and
    working, acquisition reports "pdftotext is not installed", refuses every PDF
    it fetched, and is believed. A tool reporting an absence it was not in a
    position to observe -- the fifth time this repository has recorded that
    shape.
    """
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _n: None)
    fake = tmp_path / "pdftotext"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setattr(store, "Path", store.Path)
    real_exists = store.Path.exists

    def exists(self):
        if str(self) == "/opt/homebrew/bin/pdftotext":
            return True
        return real_exists(self)
    monkeypatch.setattr(store.Path, "exists", exists)
    assert store.pdftotext_path() == "/opt/homebrew/bin/pdftotext"


# --- identity is not substance ---------------------------------------------

FULL = ("<html><body>%s Introduction. Methods. Results. Discussion. "
        "References: Smith et al. 2019.</body>" % ("word " * 2000)).encode()
ABSTRACT_PAGE = ("<html><body>%s Abstract Background: the phase III study "
                 "demonstrated prolonged survival.</body>" % ("word " * 2000)).encode()
LANDING = b"<html><body>Research Explorer. Overall Survival With Ribociclib. DOI 10.1056/x</body>"


def test_a_landing_page_is_refused_although_it_identifies_itself():
    """A page ABOUT a paper carries the paper's title and DOI, so it passes the
    identity test. Two were stored as full text on 2026-09-01 before this
    existed: the Edinburgh landing page for MONALEESA-2's survival paper, and
    the repository abstract page for its updated results."""
    kind, why = store.substance(LANDING, "text/html")
    assert kind == "landing"
    assert "ABOUT the document" in why


def test_an_abstract_page_is_recognised_as_an_abstract():
    kind, why = store.substance(ABSTRACT_PAGE, "text/html")
    assert kind == "abstract"
    assert "not the paper" in why


def test_a_full_text_is_recognised_by_its_reference_list():
    kind, why = store.substance(FULL, "text/html")
    assert kind == "full_text"
    assert "reference list" in why


def test_html_markup_is_not_counted_as_prose():
    """Measuring raw HTML counted navigation chrome as prose and menu labels as
    sections: a 5,559-character landing page scored 26,946 characters and two
    sections it did not have."""
    navvy = (b"<html><head><style>.introduction{}</style></head><body>"
             + b"<nav>Discussion Forum References Home</nav>"
             + b"<p>short</p></body></html>")
    kind, _why = store.substance(navvy, "text/html")
    assert kind == "landing"


def test_abstract_held_licenses_the_abstract_and_not_the_paper():
    permit = ledger.PERMITS[ledger.ABSTRACT_HELD]
    assert "NOT what the study found" in permit
    assert ledger.ABSTRACT_HELD in ledger.READ_STATES


# --- the question only applies where it is the question ---------------------

REGISTRY = json.dumps({"protocolSection": {
    "identificationModule": {"nctId": "NCT01958021",
                             "briefTitle": "Ribociclib overall survival MONALEESA trial"},
    "outcomesModule": {"primaryOutcomes": [{"measure": "Progression-free survival"}]},
}}).encode()


def test_a_registry_posting_is_not_a_landing_page(issue, monkeypatch):
    """substance() reads an ARTICLE's furniture -- reference list, discussion,
    introduction. Run over a ClinicalTrials.gov results posting or a drug label
    it answers "landing" with full confidence, and the answer looks exactly
    like the right one. A first pass at the 2026-09-01 backfill labelled the
    KISQALI prescribing information, the IBRANCE warnings section and all four
    registry postings as pages ABOUT documents we hold in full; one of them was
    221,525 characters long."""
    srcs = json.loads((issue / "issues" / "WHU-999-t" / "sources.json").read_text())
    srcs["sources"][0]["type"] = "registry"
    (issue / "issues" / "WHU-999-t" / "sources.json").write_text(json.dumps(srcs))

    alone, _why = store.substance(REGISTRY, "application/json")
    assert alone == "landing", "the article test, asked out of turn, says landing"

    kind, why = store.classify("t", "S001", REGISTRY, "application/json")
    assert kind == "document"
    assert "does not apply" in why


def test_an_article_is_still_held_to_the_article_test(issue):
    kind, _why = store.classify("t", "S001", LANDING, "text/html")
    assert kind == "landing", "no type given, so the article test governs"


def test_every_route_into_the_library_records_what_kind_it_holds(issue):
    """substance() existed for three hours before put() called it, and in that
    gap the CLI add path -- the one a human uses -- stored three documents with
    identity confirmed and substance never asked."""
    row = store.put("t", "S002", FULL, url="https://example.org/b",
                    via="test", content_type="text/html")
    assert row["kind"] == "full_text"
    assert store.held("t")["S002"]["kind"] == "full_text"
    assert "reference list" in store.held("t")["S002"]["kind_why"]


# --- the gap list is derived, not maintained --------------------------------

def test_the_gap_list_is_generated_from_the_library(issue):
    before = store.gaps_markdown("t")
    assert "### S002" in before, "S002 is not held yet, so it is a gap"
    store.put("t", "S002", FULL, url="https://example.org/b",
              via="test", content_type="text/html")
    after = store.gaps_markdown("t")
    assert "### S002" not in after, "held in full, so no longer a gap"
    assert "### S001" in after


def test_a_document_the_licence_forbids_is_not_listed_as_one_nobody_got(issue):
    """The hand-written file listed the NCCN guideline among documents we could
    not get. A person had read it and answered ten questions from it. The
    licence is why it is not in the library, and saying so is the point."""
    path = issue / "issues" / "WHU-999-t" / "sources.json"
    srcs = json.loads(path.read_text())
    srcs["sources"][0]["licence_forbids_machine_reading"] = True
    path.write_text(json.dumps(srcs))
    md = store.gaps_markdown("t")
    head, lic = md.split("## The licence forbids machine reading", 1)
    assert "### S001" in lic
    assert "### S001" not in head


def test_the_gap_list_says_when_we_hold_only_part_of_a_document(issue):
    store.put("t", "S002", ABSTRACT_PAGE, url="https://example.org/b",
              via="test", content_type="text/html")
    md = store.gaps_markdown("t")
    part = md.split("## In the library, but not the whole document", 1)[1]
    assert "### S002" in part
    assert "abstract" in part


# --- a check must not fire where its premise does not hold -------------------

def test_holding_an_abstract_does_not_contradict_not_having_read_the_methods():
    """inaccessibility_claims exists because the page said it could not open
    PALMARES-2 while the ledger said the source had been read. For one day it
    used READ_STATES, which contains ABSTRACT_HELD, and on 2026-09-01 it
    stopped the publish over three sentences saying MONALEESA-2's updated
    results had a statistical section we could not open -- while the ledger
    said abstract_held. Those agree. Holding an abstract is the usual REASON
    for not having reached the methods."""
    assert ledger.ABSTRACT_HELD in ledger.READ_STATES
    assert ledger.ABSTRACT_HELD not in ledger.HOLDS_WHOLE_DOCUMENT

    src = {"id": "S004", "title": "MONALEESA-2 updated results",
           "also_called": ["MONALEESA-2"],
           "access": {"state": ledger.ABSTRACT_HELD}}
    page = ("<p>The spending schedule is in a statistical section of "
            "MONALEESA-2 that we could not open.</p>")
    assert ledger.inaccessibility_claims(page, [src]) == []

    src["access"]["state"] = ledger.FULL_TEXT_HELD
    assert len(ledger.inaccessibility_claims(page, [src])) == 1
