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
