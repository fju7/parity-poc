"""A packet must quote the piece, not an older version of the piece.

WHAT WENT WRONG, 2026-09-04
---------------------------
Binding rows are keyed by the fingerprint of the sentence they bind, and
`bindings.scan()` sets `on_page` from that key. It does not rewrite the row's
`sentence` field, because rows are created once and only their verdicts change
afterwards. So a row can be correctly matched to a sentence that IS on the page
while the text stored beside it is an older, shorter version of that sentence.

One row on the melanoma page had drifted that way. Its stored text ended

    "... Neither reading appears in any of the general"

and the sentence on the page ends

    "... Neither reading appears in any of the general coverage we hold."

The three missing words are the entire scope of the claim. Appendix A of the
outside-review packet prints the stored text, so the packet built that morning
asked an independent reviewer to judge an unscoped universal negative that the
piece does not make. A reviewer who found the obvious counterexample would have
been right about our packet and wrong about our page, and we would have spent a
review -- the most expensive check we run, and the only one that can see what
our machinery cannot -- on an artefact of our own storage.

Nothing detected it. The drift is invisible to every span check (the spans were
fine), to the gate (it reads the page, not the bindings), and to the packet
builder (it printed what it was given). The only reason it was found at all is
that the sentence stopped mid-clause on a rendered page and looked wrong.

THE TWO TESTS
-------------
1. Stored sentences must hash to their own keys, for every issue. This catches
   the drift at the source, in the data, whichever consumer would have printed
   it.
2. The packet builder must take its text from the PAGE by key and must refuse
   to build when a row claims to be on a page it is not on. A builder that
   trusts the stored field reintroduces the bug the moment a row drifts again.
"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
ISSUES = {"melanoma": "issues/WHU-001-melanoma",
          "cdk46": "issues/WHU-002-cdk46",
          "deskilling": "issues/WHU-003-deskilling"}


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


def fingerprint(sent: str) -> str:
    """bindings.fingerprint, restated so the test does not import the thing it
    is testing the output of."""
    return hashlib.sha256(" ".join(sent.split()).encode("utf-8")).hexdigest()[:16]


@pytest.mark.parametrize("slug,case", sorted(ISSUES.items()))
def test_stored_sentence_hashes_to_its_own_key(slug, case):
    """A row's text and a row's identity must be the same sentence."""
    path = ROOT / case / "bindings.json"
    if not path.exists():
        pytest.skip("no bindings for %s" % slug)
    rows = json.loads(path.read_text(encoding="utf-8"))["bindings"]
    drifted = {k: " ".join((v.get("sentence") or "").split())
               for k, v in rows.items()
               if v.get("on_page") and fingerprint(v.get("sentence") or "") != k}
    assert not drifted, (
        "%d on-page row(s) in %s store text that is not the sentence they are "
        "keyed by. Anything that prints the stored field -- Appendix A of the "
        "review packet above all -- will quote a sentence the page does not "
        "contain:\n%s"
        % (len(drifted), slug,
           "\n".join("  %s  ...%s" % (k, t[-70:]) for k, t in drifted.items())))


def test_packet_takes_appendix_a_text_from_the_page():
    """Not from the stored field, which is allowed to drift."""
    RP = _load("review_packet")
    B = _load("bindings")
    live = {fingerprint(s) for s in B.page_sentences(RP.SLUG)}
    rows = RP.inferences()
    assert rows, "no inferences found; the test proves nothing"
    for r in rows:
        assert fingerprint(r["sentence"]) in live, (
            "Appendix A entry J%02d quotes a sentence that is not on the page:\n"
            "  %s" % (r["n"], r["sentence"][:200]))


def test_packet_refuses_to_build_on_a_row_that_is_not_on_the_page():
    """A row marked on_page whose key is not among the page's sentences is a
    defect in the data. The builder must stop, not print its best guess."""
    RP = _load("review_packet")
    # patch the bindings module RP ITSELF imported. _load builds a fresh module
    # object each call, so patching a separately-loaded copy patches nothing --
    # which is how the first version of this test passed by doing nothing.
    B = RP.B
    real = B.load

    ghost = "This sentence is not on the page and never was, 12345."
    doc = real(RP.SLUG)
    doc = json.loads(json.dumps(doc))          # don't mutate the cached one
    doc["bindings"][fingerprint(ghost)] = {
        "sentence": ghost, "on_page": True, "bucket": "judgement",
        "premises": [], "step": "none",
    }
    B.load = lambda slug: doc
    try:
        with pytest.raises(SystemExit) as e:
            RP.inferences()
        assert "REFUSING TO BUILD" in str(e.value)
    finally:
        B.load = real
